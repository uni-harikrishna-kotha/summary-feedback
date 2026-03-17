# CLAUDE.md — summary-feedback

## Project Purpose

This is an on-demand call summary quality scoring tool. A user provides a Tenant ID and a JWT auth token via a UI. The backend validates the JWT, then fetches the last 10 calls from the past 24 hours for that tenant using the `ListConversationsV2` gRPC API. A Judge LLM (OpenAI `gpt-4o`) scores each call summary against its transcript and the tenant's summary template prompt across three dimensions. The UI displays per-call scores and a single overall tenant score for the past 24-hour window.

---

## Project Structure

```
summary-feedback/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI route handlers (POST /v1/scoring/run, GET /v1/scoring/run/{job_id})
│   │   ├── services/     # JWT validation, conversation fetching, LLM scoring, aggregation
│   │   └── models/       # Pydantic request/response models
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/app/
│   │   ├── components/   # ScoringForm, ResultsTable, ScoreCard
│   │   └── services/     # ScoringApiService
│   └── package.json
└── changelog/            # Per-change markdown changelogs
```

## Tech Stack

| Layer    | Technology   |
|----------|--------------|
| Backend  | Python 3.12 + FastAPI |
| Frontend | Angular      |
| LLM      | OpenAI gpt-4o (configurable) |
| Data API | ListConversationsV2 gRPC + Diana REST API |

---

## System Architecture

```
┌──────────────────────────────────────────────────────┐
│                   Scoring Tool UI                    │
│                                                      │
│  [ Tenant ID        ] [ JWT Auth Token (masked) ]    │
│  [          Run Scoring          ]                   │
└─────────────────────┬────────────────────────────────┘
                      │  POST /v1/scoring/run
                      │  { tenant_id, jwt_token }
                      ▼
┌──────────────────────────────────────────────────────┐
│              Scoring API (Backend)                   │
│                                                      │
│  1. Validate JWT token                               │
│  2. Step 1 — gRPC ListConversationsV2                │
│     └─ Fetch conversation IDs + end timestamps only  │
│     └─ Filter: last 24h, limit 10, order DESC        │
│  3. Step 2 — REST API (per conversation ID)          │
│     └─ GET /diana/v2/conversations/{tenant}/{id}     │
│     └─ Extract: transcript turns + genAiSummary      │
└─────────────────────┬────────────────────────────────┘
                      │
             For each call (up to 10)
                      │
                      ▼
┌──────────────────────────────────────────────────────┐
│              Summary Scorer Service                  │
│                                                      │
│  [No Summary?] ──► Score = 0, skip LLM              │
│                                                      │
│  [Has Summary] ──► Build Judge LLM Prompt            │
│                    (transcript + summary + template)  │
│                    ──► OpenAI API (gpt-4o)           │
│                    ──► Parse JSON response            │
└─────────────────────┬────────────────────────────────┘
                      │
                All calls scored
                      │
                      ▼
┌──────────────────────────────────────────────────────┐
│           Tenant Score Aggregator                    │
│  - Avg of composite scores (past 24h calls)          │
│  - Includes 0s for missing summaries                 │
│  - Excludes unscored (LLM failure) calls             │
│  - Returns results to UI                             │
└──────────────────────────────────────────────────────┘
```

---

## API Contract

### POST /v1/scoring/run

```
Body:
{
  "tenant_id": "acme-corp",
  "jwt_token": "<user-provided JWT>",
  "environment": "prod",            // default: "prod"
  "summary_template": "<template>", // required; the prompt used to generate summaries for this tenant
  "experience_id": "exp-123"        // optional; if set, only conversations with this experience ID are fetched
}

Response (202 Accepted):
{
  "job_id": "score_abc123",
  "status": "processing",
  "tenant_id": "acme-corp"
}
```

### GET /v1/scoring/run/{job_id}

```
Response (completed):
{
  "job_id": "score_abc123",
  "tenant_id": "acme-corp",
  "status": "completed",
  "overall_score": 7.42,
  "window_start": "2026-03-16T17:17:00Z",
  "window_end": "2026-03-17T17:17:00Z",
  "calls_scored": 8,
  "calls_missing_summary": 2,
  "calls_unscored": 0,
  "computed_at": "2026-03-17T17:17:30Z",
  "calls": [
    {
      "call_id": "call_001",
      "call_end_time": "2026-03-17T15:00:00Z",
      "summary_present": true,
      "accuracy": 8.0,
      "information_capture": 7.0,
      "context_adherence": 9.0,
      "composite_score": 8.0,
      "rationale": {
        "accuracy": "Summary correctly reflects all key facts.",
        "information_capture": "Missing one action item from the transcript.",
        "context_adherence": "Follows all required template sections."
      }
    },
    {
      "call_id": "call_002",
      "call_end_time": "2026-03-17T14:00:00Z",
      "summary_present": false,
      "composite_score": 0,
      "rationale": null
    }
  ]
}
```

---

## Backend Implementation Guide

- **Framework:** Python 3.12 + FastAPI
- **JWT validation:** Decode and verify the `tenant` claim matches the `tenant_id` input before any downstream calls. Reject with 401 if expired, malformed, or tenant claim mismatch.
- **Conversation fetching:** Use `ListConversationsV2` gRPC (see `list-conversations-v2.md`):
  - Filter: `END_TIMESTAMP >= now-24h`, ordered by `END_TIMESTAMP DESC`, `page_size=10`
  - Required fields: `CONVERSATION_ID`, `END_TIMESTAMP`, transcript fields, summary fields
  - JWT passed as Bearer token in gRPC `authorization` metadata header
- **LLM scoring:** OpenAI `gpt-4o` (configurable via `OPENAI_MODEL` env var)
  - 15s timeout per call, retry up to 2 times with exponential backoff
  - Parse structured JSON response; retry on malformed JSON (max 2 retries)
  - If all retries fail, mark call as `unscored`
- **Statefulness:** Scoring is stateless — no DB persistence; all state is in-memory per request
- **Security:** JWT MUST NOT be logged or persisted anywhere

---

## Judge LLM Prompt Contract

### System Prompt (fixed)

```
You are an expert quality evaluator for AI-generated call summaries.
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
}
```

### User Prompt (per call, dynamic)

```
## Summary Template
{tenant_summary_template_prompt}

## Call Transcript
{transcript}

## Generated Summary
{generated_summary}

Evaluate the Generated Summary against the Transcript using the Summary Template as the quality standard.
```

---

## Scoring Rules

- **Composite score** = arithmetic mean of `accuracy`, `information_capture`, `context_adherence` scores, rounded to 2 decimal places.
- **No summary** → `composite_score = 0`; LLM is NOT invoked.
- **LLM failure** after all retries → mark call as `unscored`; display "Scoring Failed" in the UI row.
- **Overall tenant score** = mean of composite scores of all fetched calls (0s for missing summaries are included; `unscored` calls are excluded).
- **0 calls in 24h** → overall score = `N/A`; UI shows "No calls found in the past 24 hours".

---

## Frontend Implementation Guide

- **Framework:** Angular
- **Two main views:** Scoring form + Results
- **Form fields:**
  - Tenant ID (text input, required)
  - JWT Auth Token (password/masked input, required)
  - Run Scoring button (disabled during in-progress run; shows loading state)
- **Results table columns:** Call ID, Call End Time, Summary Present, Accuracy, Information Capture, Context Adherence, Composite Score
  - Rows for missing summary: display "No Summary — Score: 0"
  - Rows for LLM failure: display "Scoring Failed"
  - Expandable rows for per-dimension rationale (scored calls only)
- **Overall score:** Displayed prominently above or below the table, labeled "Overall Score (Past 24h)"
- **Scoring window:** Display the time window (e.g., "Calls from 2026-03-16 17:00 UTC to 2026-03-17 17:00 UTC")

---

## Key Edge Cases

| Scenario | Behavior |
|----------|----------|
| JWT token is missing | Form validation error; submission blocked |
| JWT token is expired or invalid | API returns 401; UI shows "Invalid or expired token" |
| Tenant ID not found / not in JWT claims | API returns 404/403; UI shows appropriate error |
| Summary not generated for a call | Score = 0; no LLM call made; row labeled "No Summary" |
| Transcript is empty or unavailable | Mark call as unscored; surface in UI; exclude from average |
| OpenAI returns malformed JSON | Retry up to 2 times; mark as unscored if all retries fail |
| OpenAI rate limit / 429 | Retry with exponential backoff; mark remaining as unscored if timeout exceeded |
| Tenant has 0 calls in past 24h | Overall score = N/A; UI shows "No calls found in the past 24 hours" |
| Tenant has fewer than 10 calls in past 24h | Score all available calls; overall score is the average of those calls only |
| Tenant summary template is not configured | Scoring blocked; UI shows "No summary template configured for this tenant" |
| User submits while a scoring run is already in progress | Duplicate submission blocked via UI loading state |

---

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | End-to-end scoring pipeline (fetch + score 10 calls) MUST return results within **90 seconds** of submission. |
| NFR-02 | OpenAI API calls MUST use a 15s timeout per call with a retry budget of 2 retries (exponential backoff). |
| NFR-03 | JWT token MUST NOT be logged, persisted to any database, or included in error messages. |
| NFR-04 | Raw transcripts and summaries MUST NOT be stored; used in-memory only for the duration of the request. |
| NFR-05 | All OpenAI API requests MUST be logged with a request ID for auditability (content excluded for PII). |
| NFR-06 | The scoring service MUST be stateless; each submission is independent with no dependency on prior runs. |
| NFR-07 | The UI MUST enforce HTTPS to protect the JWT token in transit. |

---

## Environment Variables

```
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o          # default
CONVERSATIONS_GRPC_HOST=conversations-service
CONVERSATIONS_GRPC_PORT=50051
CONVERSATIONS_REST_BASE_URL=https://api.us.cloud.uniphorestaging.com
```

---

## Git Workflow

- **Never commit directly to `main`.**
- For every enhancement or feature, create a new branch off `main`. If a branch already exists for the current task, continue using it.
- Branch naming convention: `<user>/<short-description>` (e.g., `harikrishnak/add-scoring-api`)
- After the user signals they are done with changes:
  1. Create a changelog file at `changelog/<user>_<heading>_<date>.md` (date format: `YYYY-MM-DD`)
  2. Open a PR against `main` automatically with the changelog content as the PR body

### Changelog File Format

```markdown
# <Heading>

**Author:** <user>
**Date:** <YYYY-MM-DD>

## Changes
- <bullet list of changes>
```

---

## Fetching Conversations

Conversation data is fetched in two steps:

### Step 1 — gRPC: Get Conversation IDs

Use `ListConversationsV2` to retrieve **only** conversation IDs and end timestamps for the past 24h. See [`list-conversations-v2.md`](./list-conversations-v2.md) for the full API reference.

**Key details:**
- **gRPC service:** `ConversationsService`
- **Method:** `ListConversationsV2`
- **Requested fields:** `CONVERSATION_ID`, `END_TIMESTAMP` only (no transcript/metadata fields)
- **Base filter:** `END_TIMESTAMP >= now-24h`, ordered `DESC`, `page_size=10`
- **Optional filter:** `CONVERSATION_EXPERIENCE_ID == experience_id` (user-supplied; ANDed with the time filter using `GROUP_OPERATOR_AND` when present)
- **Auth:** JWT in gRPC `authorization` metadata header
- **Array fields** must use `CONTAINS` / `CONTAINS_ANY` operators

### Step 2 — REST: Get Full Conversation Details

For each conversation ID returned by gRPC, call the Diana REST API to fetch the transcript and generated summary.

**Endpoint:**
```
GET {CONVERSATIONS_REST_BASE_URL}/diana/v2/conversations/{tenant_id}/{conversation_id}?environment={env}
```

**Required headers:**
```
X-Source: service
X-Tenant-Id: {tenant_id}
Authorization: Bearer {jwt_token}
```

**Used response fields:**
- `transcript.turns[].order` — turn ordering
- `transcript.turns[].participantType` — speaker type (e.g. `AGENT`, `CUSTOMER`)
- `transcript.turns[].words[].text` — individual word text; joined with spaces per turn to form the turn's spoken text
- `summary.genAiSummary.sections[].id` — section identifier
- `summary.genAiSummary.sections[].text` — section content; sections are joined as `"{id}: {text}"` per line to form the generated summary

**Environment variable:** `CONVERSATIONS_REST_BASE_URL` (default: `https://api.us.cloud.uniphorestaging.com`)
