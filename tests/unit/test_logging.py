import logging
from backend.app.core.logging import setup_logging

def test_logging_initialization():
    setup_logging()
    logger = logging.getLogger("test_logger")
    assert logger is not None
    # Verify no exception on logging
    logger.info("Phase 0 logging test message")
