import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import openai

from app.services.conversation_fetcher import ConversationData
from app.services.scoring_service import score_call
from app.config import Settings


@pytest.fixture
def settings():
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o",
        tenant_summary_template="Summarize key points.",
        summary_field_name="generated_summary",
    )


def _make_conv(summary=None, turns=None, conv_id="call_001", end_ns=1700000000000000000):
    app_meta = None
    if summary is not None:
        app_meta = json.dumps({"generated_summary": summary})
    return ConversationData(
        conversation_id=conv_id,
        end_timestamp_ns=end_ns,
        transcript_turns=turns or [
            {"order": 1, "words": "Hello, how can I help?", "participant_type": "AGENT"},
            {"order": 2, "words": "I need help with my account.", "participant_type": "CUSTOMER"},
        ],
        app_metadata=app_meta,
    )


VALID_LLM_RESPONSE = {
    "accuracy": {"score": 8.0, "rationale": "Summary correctly reflects key facts."},
    "information_capture": {"score": 7.0, "rationale": "Most info captured."},
    "context_adherence": {"score": 9.0, "rationale": "Follows template well."},
    "composite_score": 8.0,
}


@pytest.mark.asyncio
async def test_valid_llm_response(settings):
    conv = _make_conv(summary="Agent helped customer with account.")
    mock_response = MagicMock()
    mock_response.id = "req_test123"
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(VALID_LLM_RESPONSE)

    with patch("app.services.scoring_service.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await score_call(conv, "Summarize key points.", settings)

    assert result.status == "scored"
    assert result.accuracy == 8.0
    assert result.information_capture == 7.0
    assert result.context_adherence == 9.0
    assert result.composite_score == round((8.0 + 7.0 + 9.0) / 3, 2)
    assert result.summary_present is True


@pytest.mark.asyncio
async def test_missing_summary_skips_llm(settings):
    conv = _make_conv(summary=None)
    with patch("app.services.scoring_service.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        result = await score_call(conv, "Summarize key points.", settings)
        mock_client.chat.completions.create.assert_not_called()

    assert result.status == "no_summary"
    assert result.composite_score == 0.0
    assert result.summary_present is False


@pytest.mark.asyncio
async def test_all_retries_fail_returns_unscored(settings):
    conv = _make_conv(summary="Some summary.")

    with patch("app.services.scoring_service.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.completions.create = AsyncMock(
            side_effect=openai.APITimeoutError(request=MagicMock())
        )

        result = await score_call(conv, "Summarize key points.", settings)

    assert result.status == "unscored"
    assert result.composite_score is None


@pytest.mark.asyncio
async def test_malformed_json_retried_then_succeeds(settings):
    conv = _make_conv(summary="Some summary.")

    good_response = MagicMock()
    good_response.id = "req_good"
    good_response.choices = [MagicMock()]
    good_response.choices[0].message.content = json.dumps(VALID_LLM_RESPONSE)

    bad_response = MagicMock()
    bad_response.id = "req_bad"
    bad_response.choices = [MagicMock()]
    bad_response.choices[0].message.content = "not valid json {"

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return bad_response
        return good_response

    with patch("app.services.scoring_service.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.completions.create = side_effect

        result = await score_call(conv, "Summarize key points.", settings)

    assert result.status == "scored"
    assert call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_retried_then_succeeds(settings):
    conv = _make_conv(summary="Some summary.")

    good_response = MagicMock()
    good_response.id = "req_good"
    good_response.choices = [MagicMock()]
    good_response.choices[0].message.content = json.dumps(VALID_LLM_RESPONSE)

    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise openai.RateLimitError(
                message="Rate limited",
                response=MagicMock(),
                body={},
            )
        return good_response

    with patch("app.services.scoring_service.openai.AsyncOpenAI") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.chat.completions.create = side_effect

        result = await score_call(conv, "Summarize key points.", settings)

    assert result.status == "scored"
    assert call_count == 2
