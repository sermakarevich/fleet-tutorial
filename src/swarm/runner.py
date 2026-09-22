"""Parallel loop plus one supervisor tick: claim, spawn, reap, merge, close."""

import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from swarm import queue, retry, worker, worktree

LEASE_TTL = 60.0
BEAT_EVERY = 1.0
SETTLE_EVERY = 0.05


@dataclass
class Lease:
    task: queue.Task
    heartbeat: float
    alive: bool = True


def _spawn(
    run_task: Callable[..., str],
    title: str,
    workdir: Path | None,
    meta: Mapping[str, str] | None,
) -> str:
    try:
        return run_task(title, workdir=workdir, meta=meta)
    except TypeError:
        try:
            return run_task(title, workdir=workdir)
        except TypeError:
            return run_task(title)


def _retry(task: queue.Task, kind: retry.Kind, failures: dict[str, list[retry.Kind]]) -> None:
    history = failures.setdefault(task.bead_id, [])
    history.append(kind)
    if retry.should_retry(history):
        queue.reopen(task)
    else:
        queue.block(task, retry.block_reason(kind, len(history)))


def supervise(
    run_task: Callable[..., str] = worker.run_task,
    repo: Path | None = None,
    base: str = "main",
    failures: dict[str, list[retry.Kind]] | None = None,
    meta_for: Callable[[queue.Task], Mapping[str, str] | None] | None = None,
) -> str | None:
    """Claim one bead, run it in a worktree, merge it, close or requeue it.

    One tick does bounded work and exits: None when the queue is empty or
    the bead needs another tick (retry, repair), the result when the bead
    closed. Pass one `failures` dict across ticks so retries count up to
    the block limit instead of restarting each tick.
    """
    owned: dict[str, list[retry.Kind]] = failures if failures is not None else {}
    task = queue.claim_next()
    if task is None:
        return None
    meta = meta_for(task) if meta_for else None
    worker.resolve(meta)
    if repo is None:
        try:
            result = _spawn(run_task, task.title, None, meta)
        except Exception as exc:
            _retry(task, retry.classify_error(exc), owned)
            return None
        kind = retry.kind_of_text(result)
        if kind is not None:
            _retry(task, kind, owned)
            return None
        queue.close(task)
        return result
    path, branch = worktree.create(repo, task.bead_id, base)
    merged = False
    try:
        try:
            result = _spawn(run_task, task.title, path, meta)
        except Exception as exc:
            _retry(task, retry.classify_error(exc), owned)
            return None
        kind = retry.kind_of_text(result)
        if kind is not None:
            _retry(task, kind, owned)
            return None
        try:
            worktree.commit(path, task.title)
        except subprocess.CalledProcessError:
            pass
        merged = worktree.merge_back(repo, branch, base)
        if merged:
            queue.close(task)
            return result
        queue.reopen(task)
        return None
    finally:
        worktree.remove(repo, path, branch if merged else None)


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

    Failures retry with a small backoff up to the retry limit; a bead that
    fails past the limit blocks with a reason instead of retrying forever.
    With `repo` set, each bead builds in its own worktree and its branch
    merges back; a bead whose merge clashes stays claimed till the run
    ends, then reopens for repair instead of closing.
    """
    leases: dict[str, Lease] = {}
    failures: dict[str, list[retry.Kind]] = {}
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

    def note_failure(task: queue.Task, kind: retry.Kind) -> None:
        history = failures.setdefault(task.bead_id, [])
        history.append(kind)
        if retry.should_retry(history):
            time.sleep(retry.backoff_for(retry.consecutive(history, kind)))
            mark_done(task.bead_id, crashed=True)
        else:
            mark_done(task.bead_id, crashed=False)
            queue.block(task, retry.block_reason(kind, len(history)))

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
            history = failures.get(bead_id, [])
            try:
                if history and not retry.should_retry(history):
                    queue.block(lease.task, retry.block_reason(history[-1], len(history)))
                else:
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
                    except Exception as exc:
                        note_failure(task, retry.classify_error(exc))
                    else:
                        kind = retry.kind_of_text(result)
                        if kind is not None:
                            note_failure(task, kind)
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
