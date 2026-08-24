"""Unit Test Suite for Data Processor Module (Hero Flow 2 Demo Seed)."""

import pytest
from data_processor import calculate_moving_average, calculate_summary, filter_outliers


def test_calculate_summary():
    """Verify statistical summary computation."""
    data = [10.0, 20.0, 30.0]
    summary = calculate_summary(data)
    assert summary["count"] == 3.0
    assert summary["mean"] == 20.0
    assert summary["min"] == 10.0
    assert summary["max"] == 30.0


def test_empty_input():
    """Verify empty input handling."""
    summary = calculate_summary([])
    assert summary["count"] == 0.0
    assert summary["mean"] == 0.0
    assert calculate_moving_average([], 3) == []
    assert filter_outliers([], 100.0) == []


def test_filter_outliers():
    """Verify outlier threshold filtering."""
    data = [5.0, 15.0, 25.0, 100.0, 2.0]
    filtered = filter_outliers(data, max_val=30.0)
    assert filtered == [5.0, 15.0, 25.0, 2.0]


def test_calculate_moving_average():
    """Verify moving average calculation with window size 2."""
    data = [10.0, 20.0, 30.0, 40.0]
    # For window=2:
    # index 1 (window [10, 20]) -> avg = 15.0
    # index 2 (window [20, 30]) -> avg = 25.0
    # index 3 (window [30, 40]) -> avg = 35.0
    result = calculate_moving_average(data, window=2)
    assert result == [15.0, 25.0, 35.0]
