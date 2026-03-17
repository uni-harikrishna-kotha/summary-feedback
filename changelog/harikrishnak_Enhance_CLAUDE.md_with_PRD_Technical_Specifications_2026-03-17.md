# Enhance CLAUDE.md with PRD Technical Specifications

**Author:** harikrishnak
**Date:** 2026-03-17

## Changes
- Added Project Purpose section summarizing the on-demand call summary quality scoring tool
- Expanded Project Structure with full directory tree (api/, services/, models/, components/, services/)
- Added System Architecture section with ASCII diagram from PRD §5
- Added API Contract section with full request/response schemas for POST /v1/scoring/run and GET /v1/scoring/run/{job_id}
- Added Backend Implementation Guide covering FastAPI setup, JWT validation, gRPC conversation fetching, and LLM scoring details
- Added Judge LLM Prompt Contract with exact system prompt and user prompt template from PRD §6
- Added Scoring Rules covering composite score formula, no-summary handling, LLM failure handling, and overall tenant score logic
- Added Frontend Implementation Guide covering Angular form fields, results table columns, expandable rows, and overall score display
- Added Key Edge Cases table with all 11 edge cases and their expected behaviors from PRD §8
- Added Non-Functional Requirements table from PRD §9 (90s SLA, 15s LLM timeout, no JWT/transcript persistence, stateless service)
- Added Environment Variables reference (OPENAI_API_KEY, OPENAI_MODEL, CONVERSATIONS_GRPC_HOST, CONVERSATIONS_GRPC_PORT)
