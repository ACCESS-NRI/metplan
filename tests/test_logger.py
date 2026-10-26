import metplan.utils.logger as ml
import logging

def test_set_level_outside():
    """Test setting the level outside of getting a logger."""
    level = "CRITICAL"
    level_num = logging.getLevelNamesMapping()[level]
    ml.set_log_level(level)
    assert ml.get_logger().getEffectiveLevel() == level_num
    # Unset the level for future tests.
    ml.get_logger().setLevel(logging.NOTSET)

def test_get_logger():
    """Test get_logger."""
    assert isinstance(ml.get_logger(), logging.Logger)
    # Unset the level for future tests.
    ml.get_logger().setLevel(logging.NOTSET)

def test_explicit_level():
    """Test get_logger with explicit level."""
    level = "DEBUG"
    logger = ml.get_logger(level=level)
    level_num = logging.getLevelNamesMapping()[level]
    assert logger.getEffectiveLevel() == level_num
    # Unset the level for future tests.
    ml.get_logger().setLevel(logging.NOTSET)