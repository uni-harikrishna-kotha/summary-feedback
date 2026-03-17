# PRD: Call Summary Quality Scoring System

**Version:** 1.1
**Date:** 2026-03-17
**Status:** Draft

---

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-03-17 | Initial draft with scheduled polling model |
| 1.1 | 2026-03-17 | Replaced polling with on-demand UI-triggered flow; added JWT auth input |

---

## 1. Overview

### 1.1 Problem Statement

Call summary quality across tenants is inconsistent and there is no automated mechanism to detect when summaries are inaccurate, incomplete, or fail to follow the defined summary template. Manual quality audits are slow, subjective, and do not scale.

### 1.2 Goal

Build an on-demand scoring tool where a user provides a Tenant ID and a JWT auth token via a UI. The system fetches the **last 10 calls** from the past 24 hours for that tenant and uses a Judge LLM (OpenAI) to score each call summary against its transcript and the tenant's summary template prompt. Results are displayed as per-call scores and a single overall tenant score.

### 1.3 Success Metrics

- Scoring results are returned to the UI within 90 seconds of submission for up to 10 calls.
- Tenants with no summaries consistently receive a score of 0.
- Overall tenant score is based on the last 10 calls from the past 24 hours only.
- Judge LLM scoring latency per call < 10 seconds (p95).
- Invalid or expired JWT tokens are rejected before any data fetch occurs.

---

## 2. Scope

### 2.1 In Scope

- UI form accepting Tenant ID and JWT auth token as inputs.
- On-demand fetch and scoring of exactly the **last 10 calls** (summaries + transcripts) within the past 24 hours for the provided tenant.
- JWT validation before any data is fetched or scored.
- Judge LLM scoring of each call summary against its transcript.
- Per-call scores and an aggregated tenant daily score displayed on the UI.
- Handling of missing summaries (score = 0).

### 2.2 Out of Scope

- Scheduled or background polling (removed in v1.1).
- Multi-day historical trending dashboards (future iteration).
- Tenant self-service configuration of scoring dimensions.
- Human-in-the-loop review workflows.
- Persisting scores across sessions (scores are computed fresh on each submission).

---

## 3. User Flow

```
1. User opens the Scoring Tool UI.
2. User enters:
     - Tenant ID
     - JWT Auth Token
3. User clicks "Run Scoring".
4. System validates the JWT token.
     - If invalid/expired → show error, stop.
5. System fetches the last 10 calls (past 24h) for the tenant
   using the provided JWT as the bearer token.
6. For each call:
     - If no summary → score = 0, skip LLM.
     - If summary present → send transcript + summary + template to Judge LLM.
7. UI displays:
     - Per-call score table (call ID, dimensions, composite score).
     - Overall tenant score (average of all composite scores).
```

---

## 4. Functional Requirements

### 4.1 UI — Input Form

| ID | Requirement |
|----|-------------|
| FR-01 | The UI MUST provide a text input field for **Tenant ID**. |
| FR-02 | The UI MUST provide a text input field for **JWT Auth Token** (masked/password type input). |
| FR-03 | The UI MUST provide a **Run Scoring** button that submits the form. |
| FR-04 | Both fields MUST be required; the form MUST NOT submit if either field is empty. |
| FR-05 | While scoring is in progress, the UI MUST show a loading state and disable the submit button to prevent duplicate submissions. |
| FR-06 | The UI MUST display a clear error message if the JWT is invalid, expired, or the tenant ID is not found. |

### 4.2 Authentication & Authorization

| ID | Requirement |
|----|-------------|
| FR-07 | The system MUST validate the provided JWT token before making any downstream API calls. |
| FR-08 | The JWT MUST be passed as a `Bearer` token in the `Authorization` header for all calls to the data-fetch API. |
| FR-09 | If the JWT is expired, malformed, or the tenant ID does not match the token's claims, the system MUST return an authentication error immediately and halt processing. |
| FR-10 | The JWT token MUST NOT be logged, persisted, or stored beyond the lifetime of the scoring request. |

### 4.3 Call Data Fetching

| ID | Requirement |
|----|-------------|
| FR-11 | Upon a valid submission, the system MUST fetch the **last 10 calls** for the tenant, ordered by call end time descending, limited to calls within the past 24 hours. |
| FR-12 | The system MUST score **only these 10 calls** — no additional calls beyond the top 10 MUST be fetched or scored. |
| FR-13 | For each call, the system MUST retrieve both the call transcript and the generated summary. |
| FR-14 | If the data fetch API returns an authorization error (401/403), the UI MUST display an appropriate error and stop. |

### 4.4 Judge LLM Scoring

| ID | Requirement |
|----|-------------|
| FR-15 | The system MUST use OpenAI (configurable model, default: `gpt-4o`) as the Judge LLM. |
| FR-16 | For each call, the Judge LLM MUST receive: the raw transcript, the generated summary, and the tenant's summary template prompt. |
| FR-17 | The Judge LLM MUST evaluate the summary on three dimensions: **Accuracy**, **Information Capture**, and **Context Adherence**. |
| FR-18 | Each dimension MUST be scored on a scale of **0–10** (0 = completely absent/wrong, 10 = perfect). |
| FR-19 | The Judge LLM MUST return a structured JSON response with per-dimension scores, a composite call score, and a brief rationale per dimension. |
| FR-20 | The composite call score MUST be the arithmetic mean of the three dimension scores, rounded to two decimal places. |
| FR-21 | If a call has no generated summary, its composite score MUST be **0** (Judge LLM is NOT invoked). |
| FR-22 | If the Judge LLM call fails (timeout, API error), that call MUST be marked as **unscored** and the UI MUST surface this explicitly alongside the results. |

### 4.5 Scoring Dimensions Definition

| Dimension | Description |
|-----------|-------------|
| **Accuracy** | Does the summary correctly represent facts, outcomes, and decisions from the transcript? Penalizes hallucinations and factual errors. |
| **Information Capture** | Does the summary include all key topics, entities, action items, and outcomes present in the transcript? Penalizes omissions. |
| **Context Adherence** | Does the summary follow the structure, tone, and content requirements defined in the tenant's summary template prompt? Penalizes deviation from expected format or missing required sections. |

### 4.6 Tenant Overall Score

| ID | Requirement |
|----|-------------|
| FR-23 | The overall tenant score MUST be the arithmetic mean of the composite scores of the **last 10 calls fetched** (no more, no less). |
| FR-24 | Calls with no summary MUST be included in the average with a score of 0. |
| FR-25 | Calls that are **unscored** due to a Judge LLM failure MUST be excluded from the average; the UI MUST note the exclusion. |
| FR-26 | If a tenant has zero calls in the past 24 hours, the overall score MUST be displayed as **N/A**. |

### 4.7 UI — Results Display

| ID | Requirement |
|----|-------------|
| FR-27 | The UI MUST display a **per-call score table** with columns: Call ID, Call End Time, Summary Present, Accuracy, Information Capture, Context Adherence, Composite Score. |
| FR-28 | For calls with no summary, the row MUST clearly indicate "No Summary — Score: 0". |
| FR-29 | For unscored calls (LLM failure), the row MUST display "Scoring Failed". |
| FR-30 | The UI MUST display the **overall tenant score** prominently above or below the table, labeled "Overall Score (Past 24h)". |
| FR-31 | Each scored call MUST allow the user to expand a row to view the per-dimension **rationale** returned by the Judge LLM. |
| FR-32 | The UI MUST display the scoring window (e.g., "Calls from 2026-03-16 17:00 UTC to 2026-03-17 17:00 UTC"). |

---

## 5. System Architecture

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
│  2. Call Data Fetch API (Bearer: JWT)                │
│     └─ GET last 10 calls (past 24h only) for tenant  │
│     └─ Score ONLY these 10 calls — no more           │
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

## 6. Judge LLM Prompt Contract

### 6.1 System Prompt (fixed)

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

### 6.2 User Prompt (per call, dynamic)

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

## 7. API Contract

### 7.1 Trigger Scoring Run

```
POST /v1/scoring/run
Authorization: (internal service auth — JWT is passed in the body, not as the service auth)
Body:
{
  "tenant_id": "acme-corp",
  "jwt_token": "<user-provided JWT>"
}

Response (202 Accepted):
{
  "job_id": "score_abc123",
  "status": "processing",
  "tenant_id": "acme-corp"
}
```

### 7.2 Get Scoring Results (poll or SSE)

```
GET /v1/scoring/run/{job_id}
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

## 8. Edge Cases & Handling

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

## 9. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | The end-to-end scoring pipeline (fetch + score 10 calls) MUST return results within **90 seconds** of submission. |
| NFR-02 | OpenAI API calls MUST use a timeout of 15 seconds per call with a retry budget of 2 retries (exponential backoff). |
| NFR-03 | The JWT token MUST NOT be logged, persisted to any database, or included in error messages. |
| NFR-04 | Raw transcripts and summaries MUST NOT be stored by the scoring service; they are used in-memory only for the duration of the request. |
| NFR-05 | All OpenAI API requests MUST be logged with a request ID for auditability (content excluded for PII). |
| NFR-06 | The scoring service MUST be stateless; each submission is an independent request with no dependency on prior runs. |
| NFR-07 | The UI MUST enforce HTTPS to protect the JWT token in transit. |

---

## 10. Open Questions

| # | Question | Owner | Target Resolution |
|---|----------|-------|-------------------|
| Q1 | What is the source API/service for fetching calls, transcripts, and summaries? | Engineering | Before implementation start |
| Q2 | What are the JWT claims structure — does `tenant_id` appear as a claim to validate against the input? | Engineering / Security | Before implementation start |
| Q3 | Is the summary template per-tenant or per-tenant-per-use-case? | Product | Sprint 1 |
| Q4 | Should scoring results be optionally exportable (CSV/JSON download) from the UI? | Product | Sprint 1 |
| Q5 | What OpenAI model tier is acceptable for cost vs. quality tradeoff? | Engineering / Finance | Before implementation start |
| Q6 | Are transcripts and summaries subject to PII masking before being sent to OpenAI? | Legal / Security | Before implementation start |
| Q7 | Should the UI support re-running scoring for the same tenant without re-entering the JWT? (session token caching) | Product / Security | Sprint 1 |

---

## 11. Milestones

| Milestone | Description |
|-----------|-------------|
| M1 | Data contract finalized: call fetch API, JWT claims structure, tenant summary template format |
| M2 | Judge LLM prompt validated on sample calls; scoring quality approved |
| M3 | Backend scoring API implemented (JWT validation → fetch → score → aggregate) |
| M4 | UI form and results display implemented and connected to backend |
| M5 | Edge case handling and error states complete |
| M6 | Security review: JWT handling, PII in transit, HTTPS enforcement |
