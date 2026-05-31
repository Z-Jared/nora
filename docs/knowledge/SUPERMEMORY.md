# Supermemory Integration

Supermemory is an **optional, external** long-term memory service. Nora works fully offline without it.

## Configuration

| Variable | Required | Default | Description |
|---|---|---|---|
| `SUPERMEMORY_API_KEY` | Yes (to enable) | — | Bearer token from [console.supermemory.ai](https://console.supermemory.ai) |
| `SUPERMEMORY_BASE_URL` | No | `https://api.supermemory.ai` | Override for self-hosted or proxied endpoints |
| `SUPERMEMORY_CONTAINER_TAG` | No | `nora` | Container tag for scoping memories to a project or environment |

When `SUPERMEMORY_API_KEY` is not set, the three Supermemory tools (`supermemory_save`, `supermemory_search`, `supermemory_profile`) are registered but return a clear JSON error on invocation. All other Nora tools and local memory continue to work normally.

**Production / multi-project:** Set `SUPERMEMORY_CONTAINER_TAG` to a project-specific value (e.g. `my_project` or `team_backend`) so that memories from different projects or environments do not overlap. The default `nora` tag is fine for single-project or personal use.

## Tools

- **`supermemory_save`** — Saves user-provided content to Supermemory scoped under the configured container tag.
- **`supermemory_search`** — Searches Supermemory for matching memories. Returns bounded summaries (max 20 results, truncated text, sanitized metadata).
- **`supermemory_profile`** — Fetches the auto-generated user/project profile for the configured container tag.

## Privacy Boundary

- Only content explicitly passed by the user to `supermemory_save` is uploaded.
- Prompts, tool outputs, diffs, files, env vars, secrets, shell output, and task traces are **never** automatically uploaded.
- Search and profile output is bounded and truncated to prevent large raw payloads. Metadata fields are sanitized: only JSON-safe scalars are kept, strings are capped at 300 characters, and at most 20 fields per result.
- Network/API failures return JSON errors and do not crash the agent loop.
