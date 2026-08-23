"""Data Processor Module for Telemetry Analysis (Hero Flow 2 Demo Seed).

NOTE: Contains exactly ONE intentional, recoverable logic defect for self-correction demo.
Defect: calculate_moving_average has an off-by-one slice error.
"""

from typing import Dict, List, Optional


def calculate_summary(values: List[float]) -> Dict[str, float]:
    """Calculate basic statistical summary of numeric telemetry data."""
    if not values:
        return {"count": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}
    return {
        "count": float(len(values)),
        "mean": sum(values) / len(values),
        "min": min(values),
        "max": max(values),
    }


def filter_outliers(values: List[float], max_val: float) -> List[float]:
    """Filter out values exceeding the upper threshold limit."""
    return [v for v in values if v <= max_val]


def calculate_moving_average(values: List[float], window: int) -> List[float]:
    """Calculate simple moving average with the specified window size.
    
    INJECTED DEFECT: Incorrect slicing `values[i - window : i]` instead of
    `values[i - window + 1 : i + 1]`.
    """
    if not values or window <= 0 or window > len(values):
        return []

    result: List[float] = []
    for i in range(window - 1, len(values)):
        # BUG: excludes current element i
        subset = values[i - window : i]
        avg = sum(subset) / float(window)
        result.append(round(avg, 2))

    return result
