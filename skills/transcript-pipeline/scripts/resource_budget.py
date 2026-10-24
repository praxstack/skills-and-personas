"""Cumulative limits for one enrichment job, including failed attempts."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
import signal
import threading
import time


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class JobBudget:
    max_resources: int = 100
    max_transfer: int = 256 * 1024 * 1024
    max_output: int = 256 * 1024 * 1024
    max_requests: int = 1000
    seconds: float = 600
    resources: int = 0
    transfer: int = 0
    output: int = 0
    requests: int = 0
    started: float = field(default_factory=time.monotonic)
    failure: str | None = None

    def check(self):
        if self.failure:
            raise BudgetExceeded(self.failure)
        if time.monotonic() - self.started >= self.seconds:
            self.fail("job wall-clock budget exhausted")

    def fail(self, message):
        self.failure = message
        raise BudgetExceeded(message)

    def charge(self, field, amount):
        self.check()
        if amount < 0:
            raise ValueError("budget charge must be non-negative")
        value = getattr(self, field) + amount
        # Charge bytes consumed even when the attempt fails. Exhaustion is sticky.
        setattr(self, field, value)
        if value > getattr(self, "max_" + field):
            self.fail(f"job {field} budget exhausted")

    def timeout(self, default):
        self.check()
        return min(default, max(0.001, self.seconds - (time.monotonic() - self.started)))


CURRENT = ContextVar("resource_job_budget", default=None)


def check():
    if (budget := CURRENT.get()) is not None:
        budget.check()


def charge(field, amount):
    if (budget := CURRENT.get()) is not None:
        budget.charge(field, amount)


def timeout(default):
    budget = CURRENT.get()
    return budget.timeout(default) if budget else default


@contextmanager
def job_scope(budget=None, *, hard_deadline=False):
    """Nested calls share the parent budget; CLI also interrupts blocking calls.

    This is not a browser process resource sandbox. A process supervisor must
    enforce descendant memory, CPU and temporary-disk limits separately.
    """
    if CURRENT.get() is not None:
        yield CURRENT.get()
        return
    budget = budget or JobBudget()
    token = CURRENT.set(budget)
    old_handler = None
    try:
        if hard_deadline:
            if threading.current_thread() is not threading.main_thread():
                raise RuntimeError("hard deadline requires the main thread")
            if not hasattr(signal, "setitimer") or signal.getitimer(signal.ITIMER_REAL)[0]:
                raise RuntimeError("hard deadline unavailable or already owned by the caller")
            old_handler = signal.getsignal(signal.SIGALRM)
            def expired(signum, frame):
                budget.fail("job wall-clock budget exhausted")
            signal.signal(signal.SIGALRM, expired)
            signal.setitimer(signal.ITIMER_REAL, budget.timeout(budget.seconds))
        yield budget
        budget.check()
    finally:
        if old_handler is not None:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        CURRENT.reset(token)
