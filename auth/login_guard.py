"""In-process login rate limiting / temporary lockout.

Dev-friendly defaults; tune via LOGIN_MAX_ATTEMPTS and LOGIN_LOCKOUT_SECONDS.
Keyed by username + client IP so one attacker cannot lock every account from
one IP without also being limited per-username.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict

from config import LOGIN_LOCKOUT_SECONDS, LOGIN_MAX_ATTEMPTS, LOGIN_WINDOW_SECONDS


@dataclass(frozen=True)
class LockoutStatus:
    locked: bool
    retry_after_seconds: int = 0
    failure_count: int = 0


class LoginGuard:
    """Sliding-window failure tracker with optional lockout."""

    def __init__(
        self,
        *,
        max_attempts: int = LOGIN_MAX_ATTEMPTS,
        window_seconds: int = LOGIN_WINDOW_SECONDS,
        lockout_seconds: int = LOGIN_LOCKOUT_SECONDS,
    ) -> None:
        self.max_attempts = max(1, int(max_attempts))
        self.window_seconds = max(1, int(window_seconds))
        self.lockout_seconds = max(1, int(lockout_seconds))
        self._failures: Dict[str, Deque[float]] = defaultdict(deque)
        self._locked_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> None:
        q = self._failures.get(key)
        if not q:
            return
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            self._failures.pop(key, None)

    def status(self, key: str) -> LockoutStatus:
        now = time.monotonic()
        with self._lock:
            until = self._locked_until.get(key)
            if until is not None:
                if until > now:
                    return LockoutStatus(
                        locked=True,
                        retry_after_seconds=max(1, int(until - now)),
                        failure_count=self.max_attempts,
                    )
                self._locked_until.pop(key, None)
            self._prune(key, now)
            count = len(self._failures.get(key, ()))
            return LockoutStatus(locked=False, failure_count=count)

    def record_failure(self, key: str) -> LockoutStatus:
        now = time.monotonic()
        with self._lock:
            self._prune(key, now)
            self._failures[key].append(now)
            count = len(self._failures[key])
            if count >= self.max_attempts:
                self._locked_until[key] = now + self.lockout_seconds
                self._failures.pop(key, None)
                return LockoutStatus(
                    locked=True,
                    retry_after_seconds=self.lockout_seconds,
                    failure_count=self.max_attempts,
                )
            return LockoutStatus(locked=False, failure_count=count)

    def clear(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)
            self._locked_until.pop(key, None)


def client_key(username: str, client_ip: str) -> str:
    user = (username or "").strip().lower() or "-"
    ip = (client_ip or "").strip() or "-"
    return f"{user}|{ip}"


# Process-wide guard used by portal (and optionally shop) login routes.
login_guard = LoginGuard()
