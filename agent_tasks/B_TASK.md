# Claude B Task

Owner: Claude B
Status: assigned

## Goal

Design and implement the first context compiler vertical slice.

## Instructions

Implement only context compiler groundwork. Do not replace the existing RAG system and do not make broad controller changes.

Required:

- Add a deterministic context pack builder that compiles task-specific project context from explicit sources, not only vector/RAG search.
- It should be able to include:
  - git status summary
  - changed file list
  - selected file outlines/symbols for Python files
  - relevant README/knowledge excerpts when requested
  - optional RAG snippets as one section, clearly labeled auxiliary
- The output must be a structured Markdown pack with source paths and line references where available.
- Keep the pack bounded by a max character budget and include a short omitted/truncated note.
- Expose it through a read-only tool or CLI command consistent with existing project patterns.
- Add focused tests using a temporary repo/workspace.

Non-goals:

- Do not build embeddings.
- Do not add a new database dependency.
- Do not auto-inject this into every model call yet.

Suggested files:

- new `mini_agent/context_compiler.py`
- `mini_agent/tools.py` or relevant toolkit registration file
- `mini_agent/symbols.py` only if a small helper is needed
- `tests/test_context_compiler.py`
- README only if you add a user-visible tool/CLI command
- `agent_tasks/B_DONE.md`

## Current PM Note

Traditional vector RAG should remain auxiliary. Nora's main code-understanding path should become explicit context compilation: diffs, symbols, files, tests, memory, and prior traces assembled into a reproducible pack.

## Completion Report

Update `agent_tasks/B_DONE.md` with:

- Summary of context compiler behavior.
- Diff stat.
- Exact tests/checks run.
- Any known limitations or missing source type.
