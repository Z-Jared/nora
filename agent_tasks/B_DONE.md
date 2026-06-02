# Claude B Completion Report — TASK-071

Status: approved by Codex review

## Summary

Added 15 deterministic offline eval cases for worker workspace change export tools (TASK-070 runtime): `summarize_worker_workspace_changes` and `export_worker_workspace_patch`.

Only `evals/run_evals.py` runtime/eval code was edited. No TASK-070 runtime bugs discovered.

## Evals Added

### Change Summary Evals

1. **workspace_change_summary_basics** — classifies created, modified, and same files correctly; returns metadata only.
2. **workspace_change_summary_max_files_bounded** — `max_files` bounds returned file count.
3. **workspace_change_summary_sandbox_sensitive** — sensitive files/dirs and workspace symlink escapes are filtered out.
4. **workspace_change_summary_safety_no_leak** — summary output does not leak task goal, steps, secrets, or raw file content sentinels.
5. **workspace_change_summary_no_mutation** — success calls do not mutate project root, worker workspace, task state, or worker state.

### Patch Export Evals

6. **workspace_patch_export_basics** — created files diff from `/dev/null`, modified files show `-`/`+` lines, same files are excluded.
7. **workspace_patch_export_single_file** — single-file same/created/modified/missing behavior.
8. **workspace_patch_export_bounded** — `context_lines`, `max_files`, binary files, oversized worker/project files, and single-file patch size are bounded.
9. **workspace_patch_export_sandbox_sensitive** — traversal, absolute escape, sensitive paths, and workspace symlinks are rejected/skipped.
10. **workspace_patch_export_safety_no_leak** — patch export does not leak task goal, steps, or secret sentinels outside expected changed-file patch content.
11. **workspace_patch_export_no_mutation** — success and error calls do not mutate project root, worker workspace, task state, or worker state.

### Shared Change Export Evals

12. **workspace_change_export_validation_errors** — unknown worker, no lease, task mismatch, offline worker, and idle worker rejected for both tools.
13. **workspace_change_export_project_symlink_sensitive** — project-root symlink-to-sensitive-file is skipped/rejected without leaking target contents.
14. **workspace_patch_export_budget_limits** — single-file and multi-file patch output stay under the workspace byte budget.
15. **workspace_change_export_compatibility** — change export tools do not break worker/task registry, workspace lease, sandbox guard, file inspection, write tools, claim, or dispatch.

## Diff

```
 evals/run_evals.py | 723 +++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 723 insertions(+)
```

## Verification

```
python3 evals/run_evals.py
260 passed, 0 failed

python3 -m unittest tests.test_durable_workers tests.test_workspace tests.test_workspace_extra tests.test_mini_agent
Ran 401 tests in 6.944s — OK

git diff --check
clean
```

## Notes

- No runtime code changed.
- Codex PM review fixes added validation-error, project-root symlink-to-sensitive-file, and patch-budget eval coverage.
- No push performed.
