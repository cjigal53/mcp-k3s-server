"""Tests for the error recovery system."""

import time
from unittest.mock import MagicMock, patch

import pytest

from core.error_recovery import (
    ErrorRecoverySystem,
    RetryConfig,
    RetryResult,
    RetryStrategy,
    retry,
    retry_operation,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2
        assert config.jitter is True
        assert config.jitter_factor == 0.1
        assert config.strategy == RetryStrategy.EXPONENTIAL

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3,
            jitter=False,
            jitter_factor=0.2,
            strategy=RetryStrategy.LINEAR,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3
        assert config.jitter is False
        assert config.jitter_factor == 0.2
        assert config.strategy == RetryStrategy.LINEAR

    def test_invalid_max_retries(self) -> None:
        """Test that negative max_retries raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            RetryConfig(max_retries=-1)

    def test_invalid_base_delay(self) -> None:
        """Test that negative base_delay raises ValueError."""
        with pytest.raises(ValueError, match="base_delay must be non-negative"):
            RetryConfig(base_delay=-1.0)

    def test_invalid_max_delay(self) -> None:
        """Test that max_delay < base_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay must be >= base_delay"):
            RetryConfig(base_delay=10.0, max_delay=5.0)

    def test_invalid_jitter_factor(self) -> None:
        """Test that jitter_factor outside 0-1 raises ValueError."""
        with pytest.raises(ValueError, match="jitter_factor must be between 0 and 1"):
            RetryConfig(jitter_factor=1.5)


class TestRetryResult:
    """Tests for RetryResult dataclass."""

    def test_success_result(self) -> None:
        """Test successful retry result."""
        result = RetryResult(
            success=True,
            result="test_value",
            attempts=1,
            total_delay=0.0,
        )
        assert result.success is True
        assert result.result == "test_value"
        assert result.attempts == 1
        assert result.total_delay == 0.0
        assert result.last_exception is None

    def test_failure_result(self) -> None:
        """Test failed retry result."""
        exception = ValueError("test error")
        result = RetryResult(
            success=False,
            attempts=4,
            total_delay=7.0,
            last_exception=exception,
        )
        assert result.success is False
        assert result.result is None
        assert result.attempts == 4
        assert result.total_delay == 7.0
        assert result.last_exception is exception


class TestErrorRecoverySystem:
    """Tests for ErrorRecoverySystem class."""

    def test_init_default_config(self) -> None:
        """Test initialization with default config."""
        recovery = ErrorRecoverySystem()
        assert recovery.default_config.max_retries == 3

    def test_init_custom_config(self) -> None:
        """Test initialization with custom config."""
        config = RetryConfig(max_retries=5)
        recovery = ErrorRecoverySystem(config)
        assert recovery.default_config.max_retries == 5

    def test_calculate_delay_exponential(self) -> None:
        """Test exponential backoff delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2,
            jitter=False,
            strategy=RetryStrategy.EXPONENTIAL,
        )
        recovery = ErrorRecoverySystem(config)

        assert recovery.calculate_delay(0, config) == 1.0  # 1 * 2^0
        assert recovery.calculate_delay(1, config) == 2.0  # 1 * 2^1
        assert recovery.calculate_delay(2, config) == 4.0  # 1 * 2^2
        assert recovery.calculate_delay(3, config) == 8.0  # 1 * 2^3

    def test_calculate_delay_linear(self) -> None:
        """Test linear backoff delay calculation."""
        config = RetryConfig(
            base_delay=2.0,
            jitter=False,
            strategy=RetryStrategy.LINEAR,
        )
        recovery = ErrorRecoverySystem(config)

        assert recovery.calculate_delay(0, config) == 2.0  # 2 * 1
        assert recovery.calculate_delay(1, config) == 4.0  # 2 * 2
        assert recovery.calculate_delay(2, config) == 6.0  # 2 * 3

    def test_calculate_delay_constant(self) -> None:
        """Test constant delay calculation."""
        config = RetryConfig(
            base_delay=5.0,
            jitter=False,
            strategy=RetryStrategy.CONSTANT,
        )
        recovery = ErrorRecoverySystem(config)

        assert recovery.calculate_delay(0, config) == 5.0
        assert recovery.calculate_delay(1, config) == 5.0
        assert recovery.calculate_delay(5, config) == 5.0

    def test_calculate_delay_respects_max_delay(self) -> None:
        """Test that delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2,
            jitter=False,
            strategy=RetryStrategy.EXPONENTIAL,
        )
        recovery = ErrorRecoverySystem(config)

        # 1 * 2^10 = 1024, but should be capped at 5.0
        assert recovery.calculate_delay(10, config) == 5.0

    def test_calculate_delay_with_jitter(self) -> None:
        """Test that jitter adds randomness to delay."""
        config = RetryConfig(
            base_delay=10.0,
            jitter=True,
            jitter_factor=0.1,
            strategy=RetryStrategy.CONSTANT,
        )
        recovery = ErrorRecoverySystem(config)

        delays = [recovery.calculate_delay(0, config) for _ in range(100)]
        # All delays should be within jitter range (9.0 to 11.0)
        assert all(9.0 <= d <= 11.0 for d in delays)
        # With 100 samples, we should have some variation
        assert len(set(delays)) > 1

    @patch("time.sleep")
    def test_execute_with_retry_success_first_attempt(self, mock_sleep: MagicMock) -> None:
        """Test successful execution on first attempt."""
        recovery = ErrorRecoverySystem()
        func = MagicMock(return_value="success")

        result = recovery.execute_with_retry(func)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 1
        assert result.total_delay == 0.0
        func.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_execute_with_retry_success_after_failures(
        self, mock_sleep: MagicMock
    ) -> None:
        """Test successful execution after some failures."""
        config = RetryConfig(max_retries=3, base_delay=1.0, jitter=False)
        recovery = ErrorRecoverySystem(config)
        func = MagicMock(side_effect=[ValueError, ValueError, "success"])

        result = recovery.execute_with_retry(func, config)

        assert result.success is True
        assert result.result == "success"
        assert result.attempts == 3
        assert func.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("time.sleep")
    def test_execute_with_retry_all_failures(self, mock_sleep: MagicMock) -> None:
        """Test execution when all attempts fail."""
        config = RetryConfig(max_retries=2, base_delay=1.0, jitter=False)
        recovery = ErrorRecoverySystem(config)
        exception = ValueError("test error")
        func = MagicMock(side_effect=exception)

        result = recovery.execute_with_retry(func, config)

        assert result.success is False
        assert result.attempts == 3  # Initial + 2 retries
        assert result.last_exception is exception
        assert func.call_count == 3

    @patch("time.sleep")
    def test_execute_with_retry_specific_exceptions(
        self, mock_sleep: MagicMock
    ) -> None:
        """Test retry only for specific exception types."""
        config = RetryConfig(
            max_retries=3,
            retryable_exceptions=(ValueError,),
        )
        recovery = ErrorRecoverySystem(config)
        func = MagicMock(side_effect=TypeError("not retryable"))

        with pytest.raises(TypeError):
            recovery.execute_with_retry(func, config)

        func.assert_called_once()

    @patch("time.sleep")
    def test_execute_with_retry_with_args_kwargs(
        self, mock_sleep: MagicMock
    ) -> None:
        """Test that args and kwargs are passed correctly."""
        recovery = ErrorRecoverySystem()
        func = MagicMock(return_value="result")

        result = recovery.execute_with_retry(
            func, None, "arg1", "arg2", key1="value1"
        )

        assert result.success is True
        func.assert_called_once_with("arg1", "arg2", key1="value1")

    def test_total_retries_tracking(self) -> None:
        """Test that total retries are tracked correctly."""
        config = RetryConfig(max_retries=2, base_delay=0.001, jitter=False)
        recovery = ErrorRecoverySystem(config)

        # First operation fails all attempts
        func1 = MagicMock(side_effect=ValueError())
        recovery.execute_with_retry(func1, config)

        # Second operation fails once then succeeds
        func2 = MagicMock(side_effect=[ValueError(), "success"])
        recovery.execute_with_retry(func2, config)

        # Total retries: 2 (from func1) + 1 (from func2) = 3
        assert recovery.total_retries == 3

    def test_reset_stats(self) -> None:
        """Test resetting retry statistics."""
        config = RetryConfig(max_retries=1, base_delay=0.001, jitter=False)
        recovery = ErrorRecoverySystem(config)
        func = MagicMock(side_effect=ValueError())

        recovery.execute_with_retry(func, config)
        assert recovery.total_retries > 0

        recovery.reset_stats()
        assert recovery.total_retries == 0


class TestRetryDecorator:
    """Tests for the retry decorator."""

    @patch("time.sleep")
    def test_decorator_success(self, mock_sleep: MagicMock) -> None:
        """Test decorator with successful function."""

        @retry(max_retries=3)
        def successful_func() -> str:
            return "success"

        result = successful_func()
        assert result == "success"
        mock_sleep.assert_not_called()

    @patch("time.sleep")
    def test_decorator_retry_then_success(self, mock_sleep: MagicMock) -> None:
        """Test decorator with function that fails then succeeds."""
        call_count = 0

        @retry(max_retries=3, base_delay=1.0, jitter=False)
        def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary error")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3

    @patch("time.sleep")
    def test_decorator_all_failures(self, mock_sleep: MagicMock) -> None:
        """Test decorator when all attempts fail."""

        @retry(max_retries=2, base_delay=0.001)
        def always_fails() -> None:
            raise ValueError("always fails")

        with pytest.raises(ValueError, match="always fails"):
            always_fails()

    @patch("time.sleep")
    def test_decorator_preserves_function_metadata(
        self, mock_sleep: MagicMock
    ) -> None:
        """Test that decorator preserves function metadata."""

        @retry()
        def documented_func() -> str:
            """This is a documented function."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "This is a documented function."

    @patch("time.sleep")
    def test_decorator_with_arguments(self, mock_sleep: MagicMock) -> None:
        """Test decorator passes arguments correctly."""

        @retry(max_retries=1)
        def func_with_args(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        result = func_with_args(1, 2, c=3)
        assert result == 6


class TestRetryOperation:
    """Tests for the retry_operation convenience function."""

    @patch("time.sleep")
    def test_retry_operation_success(self, mock_sleep: MagicMock) -> None:
        """Test successful retry operation."""
        func = MagicMock(return_value="success")

        result = retry_operation(func)

        assert result == "success"
        func.assert_called_once()

    @patch("time.sleep")
    def test_retry_operation_with_args(self, mock_sleep: MagicMock) -> None:
        """Test retry operation with arguments."""
        func = MagicMock(return_value="result")

        result = retry_operation(func, "arg1", key="value")

        assert result == "result"
        func.assert_called_once_with("arg1", key="value")

    @patch("time.sleep")
    def test_retry_operation_failure(self, mock_sleep: MagicMock) -> None:
        """Test retry operation that fails."""
        func = MagicMock(side_effect=ValueError("error"))

        with pytest.raises(ValueError, match="error"):
            retry_operation(func, max_retries=2, base_delay=0.001)


class TestIntegration:
    """Integration tests for the error recovery system."""

    def test_realistic_retry_scenario(self) -> None:
        """Test a realistic retry scenario with actual delays."""
        config = RetryConfig(
            max_retries=2,
            base_delay=0.01,  # Very short delays for testing
            jitter=False,
            strategy=RetryStrategy.EXPONENTIAL,
        )
        recovery = ErrorRecoverySystem(config)

        call_count = 0

        def unreliable_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("temporary failure")
            return "connected"

        start_time = time.time()
        result = recovery.execute_with_retry(unreliable_operation, config)
        elapsed_time = time.time() - start_time

        assert result.success is True
        assert result.result == "connected"
        assert result.attempts == 2
        assert elapsed_time >= 0.01  # At least one delay occurred

    def test_zero_retries_config(self) -> None:
        """Test with zero retries (no retry behavior)."""
        config = RetryConfig(max_retries=0)
        recovery = ErrorRecoverySystem(config)
        func = MagicMock(side_effect=ValueError("error"))

        result = recovery.execute_with_retry(func, config)

        assert result.success is False
        assert result.attempts == 1
        func.assert_called_once()
