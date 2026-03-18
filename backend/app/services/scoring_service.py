import json
import logging
from datetime import datetime, timezone

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models.responses import CallScoreResult
from app.services.conversation_fetcher import ConversationData

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert quality evaluator for AI-generated call summaries.
You will be given a call transcript, an AI-generated summary, and a summary template
that defines the expected structure and content of a high-quality summary.

Evaluate the summary on three dimensions:
1. Accuracy (0-10): Does the summary correctly reflect facts from the transcript?
2. Information Capture (0-10): Does the summary include all key information from the transcript?
3. Context Adherence (0-10): Does the summary follow the structure and requirements of the template?

Return ONLY valid JSON in the following format:
{
  "accuracy": { "score": <0-10>, "rationale": "<one sentence>" },
  "information_capture": { "score": <0-10>, "rationale": "<one sentence>" },
  "context_adherence": { "score": <0-10>, "rationale": "<one sentence>" },
  "composite_score": <arithmetic mean, rounded to 2 decimal places>
}"""


def _build_user_prompt(template: str, transcript: str, summary: str) -> str:
    return f"""## Summary Template
{template}

## Call Transcript
{transcript}

## Generated Summary
{summary}

Evaluate the Generated Summary against the Transcript using the Summary Template as the quality standard."""


def _ns_to_iso(ns: int) -> str:
    if ns == 0:
        return None
    ts = ns / 1e9
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


async def score_call(conv: ConversationData, template: str, settings=None) -> CallScoreResult:
    call_end_time = _ns_to_iso(conv.end_timestamp_ns)

    # Extract summary — already parsed from app_metadata by the fetcher
    summary = conv.generated_summary

    if not summary:
        return CallScoreResult(
            call_id=conv.conversation_id,
            call_end_time=call_end_time,
            summary_present=False,
            composite_score=0.0,
            status="no_summary",
        )

    # Build transcript
    sorted_turns = sorted(conv.transcript_turns, key=lambda t: t.get("order", 0))
    transcript_lines = [
        f"[{t.get('participant_type', 'UNKNOWN')}]: {t.get('words', '')}"
        for t in sorted_turns
    ]
    transcript = "\n".join(transcript_lines).strip()

    if not transcript:
        return CallScoreResult(
            call_id=conv.conversation_id,
            call_end_time=call_end_time,
            summary_present=True,
            composite_score=None,
            status="empty_transcript",
        )

    # Score with LLM
    openai_model = "gpt-4o"
    if settings:
        openai_model = settings.openai_model

    api_key = ""
    if settings:
        api_key = settings.openai_api_key

    client = openai.AsyncOpenAI(api_key=api_key)

    try:
        result = await _call_llm_with_retry(
            client=client,
            model=openai_model,
            template=template,
            transcript=transcript,
            summary=summary,
        )
    except Exception:
        logger.exception("LLM scoring failed for call %s after all retries", conv.conversation_id)
        return CallScoreResult(
            call_id=conv.conversation_id,
            call_end_time=call_end_time,
            summary_present=True,
            composite_score=None,
            status="unscored",
        )

    accuracy = result["accuracy"]["score"]
    info_capture = result["information_capture"]["score"]
    ctx_adherence = result["context_adherence"]["score"]
    composite = round((accuracy + info_capture + ctx_adherence) / 3, 2)

    return CallScoreResult(
        call_id=conv.conversation_id,
        call_end_time=call_end_time,
        summary_present=True,
        accuracy=accuracy,
        information_capture=info_capture,
        context_adherence=ctx_adherence,
        composite_score=composite,
        status="scored",
        rationale={
            "accuracy": result["accuracy"]["rationale"],
            "information_capture": result["information_capture"]["rationale"],
            "context_adherence": result["context_adherence"]["rationale"],
        },
    )


@retry(
    retry=retry_if_exception_type(
        (openai.RateLimitError, openai.APITimeoutError, json.JSONDecodeError)
    ),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    reraise=True,
)
async def _call_llm_with_retry(
    client: openai.AsyncOpenAI,
    model: str,
    template: str,
    transcript: str,
    summary: str,
) -> dict:
    user_prompt = _build_user_prompt(template, transcript, summary)
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        timeout=15,
    )
    logger.info("OpenAI request %s", response.id)
    content = response.choices[0].message.content
    return json.loads(content)
