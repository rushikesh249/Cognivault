"""Unit tests for Observation Node Pytest Failure Parser (TRD Section 20.2)."""

import pytest
from backend.app.agent.nodes.observation import parse_pytest_failures


def test_parse_single_pytest_failure():
    """Verify single pytest failure extraction."""
    sample_stdout = """
============================= test session starts =============================
collected 4 items

test_data_processor.py ...F                                              [100%]

================================== FAILURES ===================================
________________________ test_calculate_moving_average ________________________

    def test_calculate_moving_average():
>       assert result == [15.0, 25.0, 35.0]
E       assert [0.0, 15.0, 25.0] == [15.0, 25.0, 35.0]
E         At index 0 diff: 0.0 != 15.0

test_data_processor.py:41: AssertionError
=========================== short test summary info ===========================
FAILED test_data_processor.py::test_calculate_moving_average - assert [0.0, 15.0, 25.0] == [15.0, 25.0, 35.0]
========================= 1 failed, 3 passed in 0.12s =========================
"""
    result = parse_pytest_failures(stdout=sample_stdout, stderr="")
    assert "test_data_processor.py::test_calculate_moving_average" in result["failing_tests"]
    assert "assert [0.0, 15.0, 25.0] == [15.0, 25.0, 35.0]" in result["error_summary"]


def test_parse_multiple_pytest_failures():
    """Verify multiple pytest failures extraction and deduplication."""
    sample_stdout = """
================================== FAILURES ===================================
________________________ test_func_one ________________________
E       ZeroDivisionError: division by zero
________________________ test_func_two ________________________
E       IndexError: list index out of range
=========================== short test summary info ===========================
FAILED tests/test_math.py::test_func_one
FAILED tests/test_math.py::test_func_two
========================= 2 failed in 0.05s =========================
"""
    result = parse_pytest_failures(stdout=sample_stdout, stderr="")
    assert len(result["failing_tests"]) == 2
    assert "tests/test_math.py::test_func_one" in result["failing_tests"]
    assert "tests/test_math.py::test_func_two" in result["failing_tests"]
    assert "ZeroDivisionError" in result["error_summary"]


def test_parse_unittest_format_failure():
    """Verify unittest format failure extraction."""
    sample_stdout = """
FAIL: test_aggregation (test_metrics.TestMetrics)
----------------------------------------------------------------------
AssertionError: 10 != 20
"""
    result = parse_pytest_failures(stdout=sample_stdout, stderr="")
    assert len(result["failing_tests"]) >= 1
    assert "test_aggregation" in result["failing_tests"][0]


def test_parse_non_standard_failure_fallback():
    """Verify fallback behavior when output has non-standard error text."""
    sample_stderr = "SyntaxError: invalid syntax on line 12"
    result = parse_pytest_failures(stdout="", stderr=sample_stderr)
    assert len(result["failing_tests"]) == 1
    assert "SyntaxError" in result["error_summary"]


def test_parse_exit_code_5_no_tests_collected():
    """exit_code=5 must be classified as a collection/no-tests problem, not an unknown failing test."""
    sample_stdout = (
        "============================= test session starts =============================\n"
        "collected 0 items\n"
        "============================ no tests ran in 0.01s =============================\n"
    )
    result = parse_pytest_failures(stdout=sample_stdout, stderr="", exit_code=5)
    assert result["failure_kind"] == "no_tests_collected"
    assert result["exit_code"] == 5
    assert "no_tests_collected" in result["failing_tests"]
    assert "unknown_test" not in result["failing_tests"]


def test_parse_exit_code_1_genuine_test_failure():
    """exit_code=1 with collected tests must be classified as a genuine test failure."""
    sample_stdout = (
        "collected 3 items\n"
        "test_factorial.py .F.\n"
        "E       assert 0 == 1\n"
        "FAILED test_factorial.py::test_factorial_zero - assert 0 == 1\n"
        "========================= 1 failed, 2 passed in 0.02s =========================\n"
    )
    result = parse_pytest_failures(stdout=sample_stdout, stderr="", exit_code=1)
    assert result["failure_kind"] == "test_failure"
    assert result["exit_code"] == 1
    assert "test_factorial.py::test_factorial_zero" in result["failing_tests"]
    assert "assert 0 == 1" in result["error_summary"]


def test_parse_exit_code_4_usage_error():
    """exit_code=4 must be classified as a pytest command-line usage error."""
    sample_stderr = "ERROR: unrecognized arguments: --bogus-flag"
    result = parse_pytest_failures(stdout="", stderr=sample_stderr, exit_code=4)
    assert result["failure_kind"] == "usage_error"
    assert result["exit_code"] == 4


def test_parse_exit_code_2_collection_error():
    """exit_code=2 with collection-time errors must be classified as collection_error."""
    sample_stdout = (
        "collected 0 items / 1 error\n"
        "=================================== ERRORS ====================================\n"
        "E   ModuleNotFoundError: No module named 'factorial'\n"
    )
    result = parse_pytest_failures(stdout=sample_stdout, stderr="", exit_code=2)
    assert result["failure_kind"] == "collection_error"
    assert result["exit_code"] == 2
    assert any("ModuleNotFoundError" in ce for ce in result["collection_errors"])


def test_parse_exit_code_0_passed():
    """exit_code=0 must be classified as passed."""
    sample_stdout = "collected 3 items\ntest_factorial.py ...\n========================= 3 passed in 0.01s ==========================\n"
    result = parse_pytest_failures(stdout=sample_stdout, stderr="", exit_code=0)
    assert result["failure_kind"] == "passed"
    assert result["exit_code"] == 0
