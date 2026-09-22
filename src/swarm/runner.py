"""Parallel loop: keep N workers busy, reclaim leases from dead workers."""

import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from swarm import queue, worker, worktree

LEASE_TTL = 60.0
BEAT_EVERY = 1.0
SETTLE_EVERY = 0.05


@dataclass
class Lease:
    task: queue.Task
    heartbeat: float
    alive: bool = True


def run_parallel(
    count: int = 3,
    run_task: Callable[..., str] = worker.run_task,
    clock: Callable[[], float] = time.monotonic,
    lease_ttl: float = LEASE_TTL,
    beat_every: float = BEAT_EVERY,
    repo: Path | None = None,
    base: str = "main",
) -> list[str]:
    """Claim beads up to `count` at a time, reap each result, retry dead leases.

    With `repo` set, each bead builds in its own worktree and its branch
    merges back; a bead whose merge clashes stays claimed till the run
    ends, then reopens for repair instead of closing.
    """
    leases: dict[str, Lease] = {}
    lock = threading.Lock()
    git_lock = threading.Lock()
    results: list[str] = []

    def touch(bead_id: str, stop: threading.Event) -> None:
        while not stop.wait(beat_every):
            with lock:
                lease = leases.get(bead_id)
                if lease is None or not lease.alive:
                    return
                lease.heartbeat = clock()

    def serve(task: queue.Task) -> tuple[str, bool]:
        stop = threading.Event()
        beat = threading.Thread(target=touch, args=(task.bead_id, stop), daemon=True)
        beat.start()
        try:
            if repo is None:
                return run_task(task.title), True
            with git_lock:
                path, branch = worktree.create(repo, task.bead_id, base)
            merged = False
            try:
                try:
                    result = run_task(task.title, workdir=path)
                except TypeError:
                    result = run_task(task.title)
                with git_lock:
                    merged = worktree.merge_back(repo, branch, base)
                return result, merged
            finally:
                with git_lock:
                    worktree.remove(repo, path, branch if merged else None)
        finally:
            stop.set()
            beat.join()

    def sweep(now: float) -> None:
        with lock:
            dead = [
                bead_id
                for bead_id, lease in leases.items()
                if not lease.alive and now - lease.heartbeat > lease_ttl
            ]
        for bead_id in dead:
            with lock:
                lease = leases.pop(bead_id, None)
            if lease is None:
                continue
            try:
                queue.reopen(lease.task)
            except Exception:
                with lock:
                    leases[bead_id] = lease

    def mark_done(bead_id: str, crashed: bool) -> None:
        with lock:
            if crashed:
                if bead_id in leases:
                    leases[bead_id].alive = False
            else:
                leases.pop(bead_id, None)

    with ThreadPoolExecutor(max_workers=count, thread_name_prefix="swarm") as pool:
        pending: dict[Future[tuple[str, bool]], queue.Task] = {}
        clashed: set[str] = set()
        held: dict[str, queue.Task] = {}
        try:
            while True:
                sweep(clock())
                while len(pending) < count:
                    with lock:
                        task = queue.claim_next()
                    if task is None:
                        break
                    if task.bead_id in clashed:
                        held[task.bead_id] = task
                        continue
                    with lock:
                        leases[task.bead_id] = Lease(task=task, heartbeat=clock())
                    pending[pool.submit(serve, task)] = task
                if not pending:
                    with lock:
                        waiting = bool(leases)
                    if not waiting:
                        break
                    time.sleep(SETTLE_EVERY)
                    continue
                done, _ = wait(list(pending), timeout=beat_every, return_when=FIRST_COMPLETED)
                for future in done:
                    task = pending.pop(future)
                    try:
                        result, merged = future.result()
                    except Exception:
                        mark_done(task.bead_id, crashed=True)
                    else:
                        mark_done(task.bead_id, crashed=False)
                        if merged:
                            results.append(result)
                            queue.close(task)
                        else:
                            clashed.add(task.bead_id)
                            held[task.bead_id] = task
        finally:
            for task in held.values():
                try:
                    queue.reopen(task)
                except Exception:
                    pass
    return results
