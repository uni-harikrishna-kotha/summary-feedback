import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.config import Settings, get_settings
from app.dependencies import get_fetcher
from app.models.requests import ScoringRunRequest
from app.models.responses import ScoringJobResult, ScoringRunAccepted
from app.services import aggregation_service
from app.services.conversation_fetcher import ConversationFetcher
from app.services.job_store import job_store
from app.services import jwt_service, scoring_service
from app.services.jwt_service import AuthError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/scoring/run", response_model=ScoringRunAccepted, status_code=202)
async def run_scoring(
    request: ScoringRunRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    fetcher: ConversationFetcher = Depends(get_fetcher),
):
    try:
        jwt_service.validate_jwt(request.jwt_token, request.tenant_id)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))

    job_id = f"score_{uuid.uuid4().hex[:8]}"
    await job_store.create(job_id, request.tenant_id)

    background_tasks.add_task(
        _run_scoring_job,
        job_id=job_id,
        tenant_id=request.tenant_id,
        jwt_token=request.jwt_token,
        environment=request.environment,
        summary_template=request.summary_template,
        experience_id=request.experience_id,
        settings=settings,
        fetcher=fetcher,
    )

    return ScoringRunAccepted(
        job_id=job_id,
        status="processing",
        tenant_id=request.tenant_id,
    )


@router.get("/scoring/run/{job_id}", response_model=ScoringJobResult)
async def get_scoring_result(job_id: str):
    job = await job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


async def _run_scoring_job(
    job_id: str,
    tenant_id: str,
    jwt_token: str,
    environment: str,
    summary_template: str,
    experience_id: Optional[str],
    settings: Settings,
    fetcher: ConversationFetcher,
):
    try:
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=24)
        since_ns = int(since.timestamp() * 1e9)

        convs = await fetcher.fetch_recent(
            tenant_id, jwt_token, since_ns,
            environment=environment,
            experience_id=experience_id,
        )

        window_start = since.isoformat()
        window_end = now.isoformat()

        if not convs:
            await job_store.update(
                job_id,
                {
                    "status": "completed",
                    "overall_score": None,
                    "window_start": window_start,
                    "window_end": window_end,
                    "calls_scored": 0,
                    "calls_missing_summary": 0,
                    "calls_unscored": 0,
                    "computed_at": datetime.now(timezone.utc).isoformat(),
                    "calls": [],
                },
            )
            return

        results = await asyncio.gather(
            *[
                scoring_service.score_call(conv, summary_template, settings)
                for conv in convs
            ]
        )

        overall = aggregation_service.compute_overall(list(results))

        calls_scored = sum(1 for r in results if r.status == "scored")
        calls_missing_summary = sum(1 for r in results if r.status == "no_summary")
        calls_unscored = sum(
            1 for r in results if r.status in ("unscored", "empty_transcript")
        )

        await job_store.update(
            job_id,
            {
                "status": "completed",
                "overall_score": overall,
                "window_start": window_start,
                "window_end": window_end,
                "calls_scored": calls_scored,
                "calls_missing_summary": calls_missing_summary,
                "calls_unscored": calls_unscored,
                "computed_at": datetime.now(timezone.utc).isoformat(),
                "calls": [r.model_dump() for r in results],
            },
        )

    except Exception:
        logger.exception("Error in scoring job %s", job_id)
        await job_store.update(
            job_id,
            {
                "status": "failed",
                "error": "Internal error",
            },
        )
