# Memory Kernel — Structured Local Records

Nora has three memory layers, each with a distinct purpose:

| Layer | Module | Backend | Purpose |
|---|---|---|---|
| **Structured records** | `memory_records.py` | SQLite + JSONL | Typed, queryable records for decisions, preferences, facts, task learnings, risks |
| **Long-term memory** | `memory.py` | SQLite + JSONL | Free-text memory with tag-based search |
| **Supermemory** | `supermemory.py` | External API | Optional cloud-backed memory for cross-device/cross-project recall |

## Structured Records (`memory_records`)

Structured records are **local-first typed memory entries** stored in Nora's own database. They are designed for information that benefits from schema:

- **decision** — architectural or process choices and their rationale
- **preference** — user or team preferences (coding style, tool choices)
- **fact** — verified project facts (API endpoints, config values, team members)
- **task_learning** — lessons learned from completed tasks
- **risk** — known risks, anti-patterns, or pitfalls
- **note** — general structured notes that don't fit other categories

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `record_id` | string | auto | Prefixed ID (`mrec_1`, `mrec_2`, …) |
| `kind` | enum | yes | One of the 6 types above |
| `scope` | string | no | `project` (default), `user`, or `global` |
| `title` | string | yes | Short title |
| `content` | string | yes | Full content |
| `tags` | string | no | Comma-separated tags |
| `source` | string | no | Origin (e.g. `review`, `retro`) |
| `confidence` | float | no | 0.0–1.0 (default 1.0) |
| `related_task_id` | string | no | Link to a durable task |
| `created_at` | ISO 8601 | auto | Creation timestamp |
| `updated_at` | ISO 8601 | auto | Last update timestamp |

### Registry Tools

| Tool | Returns | Description |
|---|---|---|
| `save_memory_record` | Full record | Create a new record |
| `search_memory_records` | Summaries | Search by keywords; returns titles/metadata, not full content |
| `list_memory_records` | Summaries | List records with optional kind/scope filters |
| `get_memory_record` | Full record | Get a single record by ID |
| `delete_memory_record` | Confirmation | Delete a record by ID |

### Safety

- Sensitive content (API keys, tokens, secrets) is rejected on save via `is_sensitive_text()`.
- Search and list return **summaries** (no `content` field); only `get` returns full content.
- No automatic ingestion of prompts, diffs, shell output, traces, or env vars.

### Review-Memory Capture (`review_memory`)

An explicit capture layer that turns bounded review/task summaries into structured records.

| Tool | Returns | Description |
|---|---|---|
| `capture_review_memory` | Created/skipped IDs | Create records from a review summary |

**What it captures by status:**
- `approved` → `task_learning`, `decision`, `risk`, `fact` records
- `changes_requested` → `risk` only (if explicit risk provided)
- `blocked` → `risk` only (if explicit risk provided)

**Safety boundaries:**
- Rejects content containing diff markers, shell output, env vars, or prompt bodies.
- Rejects sensitive content (API keys, tokens) via `is_sensitive_text()`.
- Title/content lengths are bounded (200/2000 chars).
- Deterministic dedupe prevents repeated capture for the same task_id/status/title/kind.
- Accepts explicit summary fields only — never raw diffs, prompts, shell output, or full DONE/REVIEW files.

### When to Use Which Layer

- Use **structured records** when you need typed, filterable, project-scoped knowledge.
- Use **long-term memory** for quick free-text notes with tags.
- Use **Supermemory** (if configured) for cross-device or cloud-backed recall.
