# CLAUDE.md — summary-feedback

## Project Structure

```
summary-feedback/
├── backend/       # Python 3.12 backend
├── frontend/      # Angular frontend
└── changelog/     # Per-change markdown changelogs
```

## Tech Stack

| Layer    | Technology   |
|----------|--------------|
| Backend  | Python 3.12  |
| Frontend | Angular      |

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

## Fetching Conversations

To fetch conversations for a given tenant, use the `ListConversationsV2` gRPC API documented in [`list-conversations-v2.md`](./list-conversations-v2.md).

**Key details:**
- **gRPC service:** `ConversationsService`
- **Method:** `ListConversationsV2` (offset/token pagination) or `ListConversationsV2Cursor` (cursor-based, requires LaunchDarkly flag `IsEnableUsingLastSeenId`)
- **Required request fields:** `tenant_id`, `environment`, `group_filter`, `fields`
- **Pagination:** Pass `next_page_token` from the response back as `page_token` in the next request; empty token means no more pages
- **Auth:** JWT passed in gRPC metadata under the `authorization` header; `tenant` claim in JWT must match `tenant_id`
- **Max page size:** 500
- **Array fields** (alerts, policies, participants, etc.) must use `CONTAINS` / `CONTAINS_ANY` operators — `EQUAL` on array fields returns `INVALID_ARGUMENT`

See [`list-conversations-v2.md`](./list-conversations-v2.md) for the full field reference, filter examples, and pagination code samples.
