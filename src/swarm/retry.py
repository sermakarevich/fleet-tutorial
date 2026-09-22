"""Retry policy: which failures retry, when a bead blocks for a human."""

from enum import StrEnum
from pathlib import Path

from swarm import checkpoint


class Kind(StrEnum):
    CRASH = "crash"
    STALL = "stall"
    PARTIAL = "partial"


MAX_RETRIES = 3
BACKOFF = (0.01, 0.05, 0.2)
PARTIAL_PREFIX = "PARTIAL:"
TIMEOUT_MARK = "TimeoutError"
TIMED_OUT_MARK = "timed out"


def classify_error(exc: BaseException) -> Kind:
    """Failure kind for a raised error: timeouts stall, the rest crash."""
    return Kind.STALL if isinstance(exc, TimeoutError) else Kind.CRASH


def kind_of_text(text: str) -> Kind | None:
    """Failure kind named inside attempt output, or None on success."""
    head = text.strip()
    if head.startswith(PARTIAL_PREFIX):
        return Kind.PARTIAL
    if TIMEOUT_MARK in text or TIMED_OUT_MARK in text.lower():
        return Kind.STALL
    if "Traceback" in text or "Error:" in text:
        return Kind.CRASH
    return None


def consecutive(history: list[Kind], kind: Kind) -> int:
    """Length of the trailing run of `kind` in the attempt history."""
    run = 0
    for past in reversed(history):
        if past != kind:
            break
        run += 1
    return run


def should_retry(history: list[Kind]) -> bool:
    """True while the latest failure streak is still within the limit."""
    if not history:
        return True
    return consecutive(history, history[-1]) <= MAX_RETRIES


def backoff_for(streak: int) -> float:
    """Seconds to wait before retrying a streak this long."""
    return BACKOFF[min(max(streak, 1), len(BACKOFF)) - 1]


def block_reason(kind: Kind, streak: int) -> str:
    """Human-readable reason parked on a bead that used up its retries."""
    return f"{kind} failed {streak} times in a row, needs a human to look"


def kinds_from_logs(task_folder: Path) -> list[Kind]:
    """Trailing failure streak read from attempt logs, oldest first."""
    folder = task_folder / checkpoint.ATTEMPTS_DIR
    if not folder.is_dir():
        return []
    kinds = [kind_of_text(log.read_text()) for log in sorted(folder.glob("*.log"))]
    streak: list[Kind] = []
    for kind in reversed(kinds):
        if kind is None:
            break
        streak.append(kind)
    return list(reversed(streak))
