import pytest
from app.services.aggregation_service import compute_overall
from app.models.responses import CallScoreResult


def _scored(score: float, call_id: str = "c1") -> CallScoreResult:
    return CallScoreResult(
        call_id=call_id,
        summary_present=True,
        composite_score=score,
        status="scored",
    )


def _no_summary(call_id: str = "c1") -> CallScoreResult:
    return CallScoreResult(
        call_id=call_id,
        summary_present=False,
        composite_score=0.0,
        status="no_summary",
    )


def _unscored(call_id: str = "c1") -> CallScoreResult:
    return CallScoreResult(
        call_id=call_id,
        summary_present=True,
        composite_score=None,
        status="unscored",
    )


def test_three_scored_calls():
    results = [_scored(8.0, "c1"), _scored(6.0, "c2"), _scored(7.0, "c3")]
    assert compute_overall(results) == 7.0


def test_scored_plus_no_summary():
    results = [_scored(8.0, "c1"), _no_summary("c2")]
    assert compute_overall(results) == 4.0


def test_scored_plus_unscored():
    results = [_scored(8.0, "c1"), _unscored("c2")]
    assert compute_overall(results) == 8.0


def test_empty_list():
    assert compute_overall([]) is None


def test_mixed_calls():
    results = [
        _scored(9.0, "c1"),
        _scored(6.0, "c2"),
        _no_summary("c3"),
        _unscored("c4"),
    ]
    # mean of [9.0, 6.0, 0.0] = 5.0
    assert compute_overall(results) == 5.0
