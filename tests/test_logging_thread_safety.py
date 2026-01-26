import threading
from typing import Any, cast

from tests.test_template import TestTemplate


class TestLoggingThreadSafety(TestTemplate):
    def test_concurrent_setup_logging_initializes_once(self):
        """Test that concurrent calls to setup_logging() don't cause double-initialization."""
        import src.utils.logging_config as logging_module

        # Reset state
        logging_module._logging_initialized = False

        call_count = 0
        logger_any = cast(Any, logging_module.logger)
        original_remove = logger_any.remove

        def counting_remove(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_remove(*args, **kwargs)

        logger_any.remove = counting_remove

        barrier = threading.Barrier(10)
        errors = []

        def call_setup():
            try:
                barrier.wait(timeout=5)
                logging_module.setup_logging()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_setup) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Restore original
        logger_any.remove = original_remove

        assert not errors, f"Errors during concurrent setup: {errors}"
        assert call_count == 1, (
            f"logger.remove() called {call_count} times, expected exactly 1"
        )
        assert logging_module._logging_initialized is True
