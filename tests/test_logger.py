import logging

import pytest

import metplan.utils.logger as ml


@pytest.fixture(params=["CRITICAL", "DEBUG"])
def log_level(request):
    """Provide a level, resetting the logger before and after each test."""
    ml.get_logger().setLevel(logging.NOTSET)
    yield request.param
    ml.get_logger().setLevel(logging.NOTSET)


def test_set_level_outside(log_level):
    """Test setting the level outside of getting a logger."""
    level_num = logging.getLevelNamesMapping()[log_level]
    ml.set_log_level(log_level)
    assert ml.get_logger().getEffectiveLevel() == level_num


def test_get_logger(log_level):
    """Test get_logger the most common way it is accessed."""
    assert isinstance(ml.get_logger(), logging.Logger)


def test_explicit_level(log_level):
    """Test get_logger with explicit level."""
    logger = ml.get_logger(level=log_level)
    level_num = logging.getLevelNamesMapping()[log_level]
    assert logger.getEffectiveLevel() == level_num
