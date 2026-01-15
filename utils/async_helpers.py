"""Async helper utilities for proper async/await handling.

This module provides utilities to ensure proper async/await handling
and prevent 'coroutine was never awaited' warnings.
"""

import asyncio
import functools
from typing import Any, Callable, Coroutine, TypeVar, Optional

T = TypeVar('T')


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine synchronously.
    
    This helper function properly handles running async coroutines
    in a synchronous context without causing warnings.
    
    Args:
        coro: The coroutine to run.
        
    Returns:
        The result of the coroutine.
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def async_to_sync(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., T]:
    """Decorator to convert an async function to a sync function.
    
    This decorator wraps an async function to make it callable
    from synchronous code without causing coroutine warnings.
    
    Args:
        func: The async function to wrap.
        
    Returns:
        A synchronous wrapper function.
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        return run_async(func(*args, **kwargs))
    return wrapper


async def ensure_awaited(coro: Optional[Coroutine[Any, Any, T]]) -> Optional[T]:
    """Ensure a coroutine is properly awaited.
    
    This helper ensures that optional coroutines are properly
    awaited when they exist.
    
    Args:
        coro: The optional coroutine to await.
        
    Returns:
        The result of the coroutine, or None if no coroutine provided.
    """
    if coro is not None:
        return await coro
    return None


class AsyncContextManager:
    """Base class for async context managers.
    
    Provides a template for creating async context managers
    with proper resource handling.
    """
    
    async def __aenter__(self) -> 'AsyncContextManager':
        """Enter the async context."""
        return self
    
    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any
    ) -> bool:
        """Exit the async context."""
        return False
