# -*- coding: utf-8 -*-
"""
Injectable time provider for deterministic timeout testing.

Allows tests to control time without actual sleeping.

Usage:
    # In tests
    fake_time = FakeTimeProvider()
    set_time_provider(fake_time)
    
    # Advance time
    fake_time.advance(5000)  # Advance 5 seconds
    
    # Test timeout
    async with with_timeout(some_coro(), timeout_ms=3000) as result:
        ...  # Will timeout if fake_time.now_ms() > start + 3000
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable, Optional, TypeVar

T = TypeVar("T")


class TimeoutExceeded(Exception):
    """Raised when an operation exceeds its timeout budget."""
    
    def __init__(self, timeout_ms: int, elapsed_ms: int, operation: str = ""):
        self.timeout_ms = timeout_ms
        self.elapsed_ms = elapsed_ms
        self.operation = operation
        super().__init__(
            f"Timeout exceeded: {elapsed_ms}ms > {timeout_ms}ms"
            + (f" in {operation}" if operation else "")
        )


class TimeProvider(ABC):
    """Abstract time provider interface."""
    
    @abstractmethod
    def now_ms(self) -> int:
        """Get current time in milliseconds."""
        pass
    
    @abstractmethod
    async def sleep(self, ms: int) -> None:
        """Sleep for the given milliseconds."""
        pass
    
    @abstractmethod
    def is_fake(self) -> bool:
        """Return True if this is a fake time provider."""
        pass


class RealTimeProvider(TimeProvider):
    """Real time provider using system clock."""
    
    def __init__(self):
        self._start = time.monotonic()
    
    def now_ms(self) -> int:
        """Get current time in milliseconds since start."""
        return int((time.monotonic() - self._start) * 1000)
    
    async def sleep(self, ms: int) -> None:
        """Actually sleep."""
        await asyncio.sleep(ms / 1000.0)
    
    def is_fake(self) -> bool:
        return False


class FakeTimeProvider(TimeProvider):
    """
    Fake time provider for testing.
    
    Time only advances when explicitly told to.
    """
    
    def __init__(self, start_ms: int = 0):
        self._current_ms = start_ms
        self._waiters: list[tuple[int, asyncio.Event]] = []
    
    def now_ms(self) -> int:
        """Get current fake time."""
        return self._current_ms
    
    async def sleep(self, ms: int) -> None:
        """
        Fake sleep - returns immediately but registers a waiter.
        
        The test must call advance() to wake up waiters.
        """
        if ms <= 0:
            return
        
        wake_time = self._current_ms + ms
        event = asyncio.Event()
        self._waiters.append((wake_time, event))
        
        # Wait for the event (will be set by advance())
        await event.wait()
    
    def advance(self, ms: int) -> int:
        """
        Advance fake time and wake up any waiters whose time has come.
        
        Returns number of waiters woken.
        """
        self._current_ms += ms
        woken = 0
        
        # Wake up waiters whose time has passed
        remaining = []
        for wake_time, event in self._waiters:
            if self._current_ms >= wake_time:
                event.set()
                woken += 1
            else:
                remaining.append((wake_time, event))
        
        self._waiters = remaining
        return woken
    
    def set(self, ms: int) -> None:
        """Set the current time (for absolute positioning)."""
        self._current_ms = ms
    
    def is_fake(self) -> bool:
        return True
    
    def pending_waiters(self) -> int:
        """Get number of pending sleep waiters."""
        return len(self._waiters)


# Global time provider
_time_provider: TimeProvider = RealTimeProvider()


def get_time_provider() -> TimeProvider:
    """Get the current time provider."""
    return _time_provider


def set_time_provider(provider: TimeProvider) -> TimeProvider:
    """
    Set the time provider.
    
    Returns the previous provider.
    """
    global _time_provider
    old = _time_provider
    _time_provider = provider
    return old


async def with_timeout(
    coro: Awaitable[T],
    timeout_ms: int,
    *,
    on_timeout: Optional[Callable[[], T]] = None,
    operation: str = "",
) -> T:
    """
    Execute coroutine with a timeout.
    
    Uses the global time provider, so works with FakeTimeProvider in tests.
    
    Args:
        coro: The coroutine to execute
        timeout_ms: Timeout in milliseconds
        on_timeout: Optional callback to return a value on timeout
        operation: Optional name for error messages
    
    Returns:
        The result of the coroutine
    
    Raises:
        TimeoutExceeded: If timeout exceeded and no on_timeout provided
    """
    provider = get_time_provider()
    start_ms = provider.now_ms()
    
    if provider.is_fake():
        # For fake time, we need to handle this differently
        # The coroutine must check time periodically or use provider.sleep()
        try:
            result = await coro
            elapsed = provider.now_ms() - start_ms
            if elapsed > timeout_ms:
                if on_timeout:
                    return on_timeout()
                raise TimeoutExceeded(timeout_ms, elapsed, operation)
            return result
        except TimeoutExceeded:
            if on_timeout:
                return on_timeout()
            raise
    else:
        # Real time: use asyncio.wait_for
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_ms / 1000.0)
            return result
        except asyncio.TimeoutError:
            elapsed = provider.now_ms() - start_ms
            if on_timeout:
                return on_timeout()
            raise TimeoutExceeded(timeout_ms, elapsed, operation)


async def check_timeout(
    start_ms: int,
    timeout_ms: int,
    operation: str = "",
) -> None:
    """
    Check if timeout has been exceeded.
    
    Call this periodically in long-running operations.
    
    Raises:
        TimeoutExceeded: If timeout exceeded
    """
    elapsed = get_time_provider().now_ms() - start_ms
    if elapsed > timeout_ms:
        raise TimeoutExceeded(timeout_ms, elapsed, operation)
