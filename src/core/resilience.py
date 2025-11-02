"""Production-grade resilience with circuit breakers and retry logic."""
import asyncio
from typing import Callable, Any, Optional, Dict
from functools import wraps
from datetime import datetime, timedelta
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ExchangeCircuitBreaker:
    """Circuit breaker for exchange API calls."""

    def __init__(
        self,
        fail_max: int = 5,
        timeout_duration: int = 60,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.

        Args:
            fail_max: Maximum failures before opening circuit
            timeout_duration: Seconds to wait before half-open state
            expected_exception: Exception type to catch
        """
        self.breaker = CircuitBreaker(
            fail_max=fail_max,
            timeout_duration=timeout_duration,
            expected_exception=expected_exception,
            name="ExchangeAPI"
        )

        self.breaker.add_listener(self._on_state_change)

    def _on_state_change(self, cb, old_state, new_state):
        """Log circuit breaker state changes."""
        logger.warning(
            f"Circuit breaker state changed: {old_state.name} -> {new_state.name}"
        )

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await self.breaker.call_async(func, *args, **kwargs)
            except CircuitBreakerError:
                logger.error(f"Circuit breaker open for {func.__name__}")
                raise

        return wrapper

    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self.breaker.current_state == 'open'

    @property
    def failure_count(self) -> int:
        """Get current failure count."""
        return self.breaker.fail_counter


class RetryableOperation:
    """Configurable retry logic for operations."""

    @staticmethod
    def with_exponential_backoff(
        max_attempts: int = 5,
        min_wait: int = 1,
        max_wait: int = 60,
        exceptions: tuple = (Exception,)
    ):
        """
        Create retry decorator with exponential backoff.

        Args:
            max_attempts: Maximum retry attempts
            min_wait: Minimum wait time in seconds
            max_wait: Maximum wait time in seconds
            exceptions: Tuple of exceptions to retry on

        Returns:
            Retry decorator
        """
        return retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=min_wait, max=max_wait),
            retry=retry_if_exception_type(exceptions),
            before_sleep=before_sleep_log(logger, logger.level),
            reraise=True
        )


# Pre-configured retry strategies

@RetryableOperation.with_exponential_backoff(
    max_attempts=5,
    min_wait=2,
    max_wait=60,
    exceptions=(ConnectionError, TimeoutError)
)
async def retry_on_connection_error(func: Callable, *args, **kwargs) -> Any:
    """Retry operation on connection errors."""
    return await func(*args, **kwargs)


@RetryableOperation.with_exponential_backoff(
    max_attempts=3,
    min_wait=1,
    max_wait=10,
    exceptions=(ValueError,)
)
async def retry_on_value_error(func: Callable, *args, **kwargs) -> Any:
    """Retry operation on value errors."""
    return await func(*args, **kwargs)


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, max_calls: int, time_window: int):
        """
        Initialize rate limiter.

        Args:
            max_calls: Maximum calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: list = []

    async def acquire(self) -> None:
        """Acquire rate limit slot, waiting if necessary."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.time_window)

        # Remove old calls
        self.calls = [call_time for call_time in self.calls if call_time > cutoff]

        # Wait if at limit
        if len(self.calls) >= self.max_calls:
            wait_time = (self.calls[0] - cutoff).total_seconds()
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time + 0.1)

            # Retry acquire
            return await self.acquire()

        # Record this call
        self.calls.append(now)

    def __call__(self, func: Callable) -> Callable:
        """Decorator for rate-limited functions."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            await self.acquire()
            return await func(*args, **kwargs)

        return wrapper


class TimeoutManager:
    """Timeout management for operations."""

    @staticmethod
    def with_timeout(timeout_seconds: int):
        """
        Create timeout decorator.

        Args:
            timeout_seconds: Timeout in seconds

        Returns:
            Timeout decorator
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    return await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=timeout_seconds
                    )
                except asyncio.TimeoutError:
                    logger.error(
                        f"Operation {func.__name__} timed out after {timeout_seconds}s"
                    )
                    raise

            return wrapper
        return decorator


class HealthCheck:
    """System health monitoring."""

    def __init__(self):
        """Initialize health check."""
        self.components: Dict[str, dict] = {}
        self.last_check = None

    def register_component(
        self,
        name: str,
        check_func: Callable,
        critical: bool = True
    ) -> None:
        """
        Register component for health checking.

        Args:
            name: Component name
            check_func: Function that returns True if healthy
            critical: Whether component is critical
        """
        self.components[name] = {
            'check': check_func,
            'critical': critical,
            'status': 'unknown',
            'last_check': None,
            'error': None
        }

    async def check_component(self, name: str) -> bool:
        """
        Check health of specific component.

        Args:
            name: Component name

        Returns:
            True if healthy
        """
        component = self.components.get(name)
        if not component:
            return False

        try:
            is_healthy = await component['check']()
            component['status'] = 'healthy' if is_healthy else 'unhealthy'
            component['last_check'] = datetime.utcnow()
            component['error'] = None
            return is_healthy
        except Exception as e:
            component['status'] = 'error'
            component['last_check'] = datetime.utcnow()
            component['error'] = str(e)
            logger.error(f"Health check failed for {name}: {e}")
            return False

    async def check_all(self) -> Dict[str, Any]:
        """
        Check all components.

        Returns:
            Health status of all components
        """
        results = {}
        critical_failure = False

        for name in self.components:
            is_healthy = await self.check_component(name)
            results[name] = {
                'healthy': is_healthy,
                'critical': self.components[name]['critical'],
                'status': self.components[name]['status'],
                'error': self.components[name]['error']
            }

            if not is_healthy and self.components[name]['critical']:
                critical_failure = True

        self.last_check = datetime.utcnow()

        return {
            'overall_healthy': not critical_failure,
            'components': results,
            'last_check': self.last_check
        }

    def get_status(self) -> Dict[str, Any]:
        """Get current health status."""
        return {
            'components': {
                name: {
                    'status': comp['status'],
                    'last_check': comp['last_check'],
                    'critical': comp['critical']
                }
                for name, comp in self.components.items()
            },
            'last_check': self.last_check
        }


class GracefulShutdown:
    """Handle graceful shutdown of the application."""

    def __init__(self):
        """Initialize shutdown manager."""
        self.shutdown_requested = False
        self.cleanup_tasks = []

    def request_shutdown(self) -> None:
        """Request application shutdown."""
        logger.warning("Graceful shutdown requested")
        self.shutdown_requested = True

    def register_cleanup(self, task: Callable) -> None:
        """
        Register cleanup task.

        Args:
            task: Async function to call on shutdown
        """
        self.cleanup_tasks.append(task)

    async def execute_cleanup(self) -> None:
        """Execute all cleanup tasks."""
        logger.info(f"Executing {len(self.cleanup_tasks)} cleanup tasks")

        for task in self.cleanup_tasks:
            try:
                await task()
            except Exception as e:
                logger.error(f"Cleanup task failed: {e}")

        logger.info("Cleanup completed")

    @property
    def should_shutdown(self) -> bool:
        """Check if shutdown was requested."""
        return self.shutdown_requested
