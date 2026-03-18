from pydantic import BaseModel
from typing import Optional


class ScoringRunAccepted(BaseModel):
    job_id: str
    status: str
    tenant_id: str


class CallScoreResult(BaseModel):
    call_id: str
    call_end_time: Optional[str] = None
    summary_present: bool
    accuracy: Optional[float] = None
    information_capture: Optional[float] = None
    context_adherence: Optional[float] = None
    composite_score: Optional[float] = None
    status: str  # "scored" | "no_summary" | "unscored" | "empty_transcript"
    rationale: Optional[dict] = None


class ScoringJobResult(BaseModel):
    job_id: str
    tenant_id: str
    status: str
    overall_score: Optional[float] = None
    window_start: Optional[str] = None
    window_end: Optional[str] = None
    calls_scored: int = 0
    calls_missing_summary: int = 0
    calls_unscored: int = 0
    computed_at: Optional[str] = None
    calls: list[CallScoreResult] = []
    error: Optional[str] = None
