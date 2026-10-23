"""Fail-closed inference for common Unix epoch timestamp units."""
from __future__ import annotations


def infer_epoch_unit(magnitude: float) -> str:
    """Return pandas' epoch unit for a positive median magnitude.

    Expected common ranges: seconds 1e8+, milliseconds 1e11+,
    microseconds 1e14+, nanoseconds 1e17+. Values below the seconds
    threshold are ambiguous and rejected rather than guessed.
    """
    if magnitude != magnitude or magnitude <= 0 or magnitude == float("inf"):
        raise ValueError("Timestamp magnitude must be positive and finite")
    if magnitude >= 1e17:
        return "ns"
    if magnitude >= 1e14:
        return "us"
    if magnitude >= 1e11:
        return "ms"
    if magnitude >= 1e8:
        return "s"
    raise ValueError("Ambiguous numeric timestamp scale")
