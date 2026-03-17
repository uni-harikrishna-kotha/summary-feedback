from typing import Optional

from app.models.responses import CallScoreResult


def compute_overall(results: list[CallScoreResult]) -> Optional[float]:
    scores = [
        r.composite_score
        for r in results
        if r.status != "unscored" and r.status != "empty_transcript"
        and r.composite_score is not None
    ]
    if not scores:
        return None
    return round(sum(scores) / len(scores), 2)
