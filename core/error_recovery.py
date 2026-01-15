"""Error recovery system with exponential backoff retry mechanism.

This module provides a robust error recovery system that can retry failed
operations with configurable exponential backoff, jitter, and retry policies.
"""

import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(Enum):
    """Enumeration of available retry strategies."""

    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts. Default is 3.
        base_delay: Base delay in seconds between retries. Default is 1.0.
        max_delay: Maximum delay in seconds between retries. Default is 60.0.
        exponential_base: Base for exponential backoff calculation. Default is 2.
        jitter: Whether to add random jitter to delays. Default is True.
        jitter_factor: Factor for jitter calculation (0-1). Default is 0.1.
        strategy: Retry strategy to use. Default is EXPONENTIAL.
        retryable_exceptions: Tuple of exception types that should trigger retry.
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: int = 2
    jitter: bool = True
    jitter_factor: float = 0.1
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: (Exception,)
    )

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if not 0 <= self.jitter_factor <= 1:
            raise ValueError("jitter_factor must be between 0 and 1")


@dataclass
class RetryResult:
    """Result of a retry operation.

    Attributes:
        success: Whether the operation succeeded.
        result: The result of the operation if successful.
        attempts: Number of attempts made.
        total_delay: Total delay time in seconds.
        last_exception: The last exception raised if failed.
    """

    success: bool
    result: Any = None
    attempts: int = 0
    total_delay: float = 0.0
    last_exception: Optional[Exception] = None


class ErrorRecoverySystem:
    """Error recovery system with configurable retry mechanisms.

    This class provides methods to retry failed operations with various
    backoff strategies including exponential, linear, and constant delays.

    Example:
        >>> recovery = ErrorRecoverySystem()
        >>> config = RetryConfig(max_retries=3, base_delay=1.0)
        >>> result = recovery.execute_with_retry(my_function, config, arg1, arg2)
    """

    def __init__(self, default_config: Optional[RetryConfig] = None) -> None:
        """Initialize the error recovery system.

        Args:
            default_config: Default retry configuration to use when none is provided.
        """
        self._default_config = default_config or RetryConfig()
        self._retry_count = 0
        self._total_retries = 0

    @property
    def default_config(self) -> RetryConfig:
        """Get the default retry configuration."""
        return self._default_config

    @property
    def total_retries(self) -> int:
        """Get the total number of retries performed."""
        return self._total_retries

    def calculate_delay(
        self, attempt: int, config: Optional[RetryConfig] = None
    ) -> float:
        """Calculate the delay for a given attempt number.

        Args:
            attempt: The current attempt number (0-indexed).
            config: Retry configuration to use. Uses default if not provided.

        Returns:
            The calculated delay in seconds.
        """
        config = config or self._default_config

        if config.strategy == RetryStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.exponential_base ** attempt)
        elif config.strategy == RetryStrategy.LINEAR:
            delay = config.base_delay * (attempt + 1)
        else:  # CONSTANT
            delay = config.base_delay

        # Apply max delay cap
        delay = min(delay, config.max_delay)

        # Apply jitter if enabled
        if config.jitter:
            jitter_range = delay * config.jitter_factor
            delay = delay + random.uniform(-jitter_range, jitter_range)
            delay = max(0, delay)  # Ensure non-negative

        return delay

    def execute_with_retry(
        self,
        func: Callable[..., T],
        config: Optional[RetryConfig] = None,
        *args: Any,
        **kwargs: Any,
    ) -> RetryResult:
        """Execute a function with retry logic.

        Args:
            func: The function to execute.
            config: Retry configuration. Uses default if not provided.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.

        Returns:
            RetryResult containing the outcome of the operation.
        """
        config = config or self._default_config
        last_exception: Optional[Exception] = None
        total_delay = 0.0

        for attempt in range(config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                return RetryResult(
                    success=True,
                    result=result,
                    attempts=attempt + 1,
                    total_delay=total_delay,
                )
            except config.retryable_exceptions as e:
                last_exception = e
                self._total_retries += 1

                if attempt < config.max_retries:
                    delay = self.calculate_delay(attempt, config)
                    total_delay += delay
                    logger.warning(
                        f"Attempt {attempt + 1} failed with {type(e).__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {config.max_retries + 1} attempts failed. "
                        f"Last error: {type(e).__name__}: {e}"
                    )

        return RetryResult(
            success=False,
            attempts=config.max_retries + 1,
            total_delay=total_delay,
            last_exception=last_exception,
        )

    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self._total_retries = 0


def retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: int = 2,
    jitter: bool = True,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for adding retry logic to functions.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds between retries.
        max_delay: Maximum delay in seconds between retries.
        exponential_base: Base for exponential backoff calculation.
        jitter: Whether to add random jitter to delays.
        strategy: Retry strategy to use.
        retryable_exceptions: Tuple of exception types that should trigger retry.

    Returns:
        Decorated function with retry logic.

    Example:
        >>> @retry(max_retries=3, base_delay=1.0)
        ... def unreliable_function():
        ...     # Some operation that might fail
        ...     pass
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        strategy=strategy,
        retryable_exceptions=retryable_exceptions,
    )
    recovery_system = ErrorRecoverySystem(config)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            result = recovery_system.execute_with_retry(func, config, *args, **kwargs)
            if result.success:
                return result.result
            raise result.last_exception or RuntimeError(
                "Retry failed without exception"
            )

        return wrapper

    return decorator


# Convenience function for one-off retries
def retry_operation(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    **kwargs: Any,
) -> T:
    """Execute a function with retry logic (convenience function).

    Args:
        func: The function to execute.
        *args: Positional arguments to pass to the function.
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds between retries.
        retryable_exceptions: Tuple of exception types that should trigger retry.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        The result of the function if successful.

    Raises:
        The last exception if all retries fail.
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        retryable_exceptions=retryable_exceptions,
    )
    recovery_system = ErrorRecoverySystem(config)
    result = recovery_system.execute_with_retry(func, config, *args, **kwargs)

    if result.success:
        return result.result

    if result.last_exception:
        raise result.last_exception

    raise RuntimeError("Retry operation failed without exception")
