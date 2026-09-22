"""Parallel loop: keep N workers busy, reclaim leases from dead workers."""

import threading
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass

from swarm import queue, worker

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
) -> list[str]:
    """Claim beads up to `count` at a time, reap each result, retry dead leases."""
    leases: dict[str, Lease] = {}
    lock = threading.Lock()
    results: list[str] = []

    def touch(bead_id: str, stop: threading.Event) -> None:
        while not stop.wait(beat_every):
            with lock:
                lease = leases.get(bead_id)
                if lease is None or not lease.alive:
                    return
                lease.heartbeat = clock()

    def serve(task: queue.Task) -> str:
        stop = threading.Event()
        beat = threading.Thread(target=touch, args=(task.bead_id, stop), daemon=True)
        beat.start()
        try:
            return run_task(task.title)
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
        pending: dict[Future[str], queue.Task] = {}
        while True:
            sweep(clock())
            while len(pending) < count:
                with lock:
                    task = queue.claim_next()
                if task is None:
                    break
                with lock:
                    leases[task.bead_id] = Lease(task=task, heartbeat=clock())
                pending[pool.submit(serve, task)] = task
            if not pending:
                with lock:
                    waiting = bool(leases)
                if not waiting:
                    return results
                time.sleep(SETTLE_EVERY)
                continue
            done, _ = wait(list(pending), timeout=beat_every, return_when=FIRST_COMPLETED)
            for future in done:
                task = pending.pop(future)
                try:
                    results.append(future.result())
                except Exception:
                    mark_done(task.bead_id, crashed=True)
                else:
                    mark_done(task.bead_id, crashed=False)
                    queue.close(task)
    return results
