# B DONE - TASK-170B

Status: Complete

## Summary

Created the Phase 2 safety, eval, and worker-scaling sections for `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md`.

## Sections Written

### Safety Policy for Voice/TTS/Presence

- Voice cloning: default off, explicit consent required for any future cloning path, no silent cloning, no real-person prompts.
- Recording: no recording by default, no hidden background listening, transparent microphone state.
- Cost: estimate before speak, no surprise charges, voice cost in food-status.
- Emotional safety: no pressure, no dependency framing, no purchase manipulation.
- Presence: no always-on surveillance, transparent data flow, local-first default.

### Deterministic Eval Plan

- Voice profile contract evals for no cloning, bounded fields, visible cost estimate, and deterministic cost.
- No-secret/no-recording/no-cloning copy scans.
- Web/PWA presence smoke tests for state sync, mic indicator, and no auto-start.
- Cost transparency checks for voice/TTS food status and insufficient balance handling.

### Worker Scaling Plan

- Recommendation: keep Claude A/B only at Phase 2 start; do not open Claude C/D yet.
- Reasoning: initial Voice/Profile/Presence work shares core files, so C/D would increase merge conflicts before boundaries stabilize.
- File boundaries: Claude A owns implementation; Claude B owns evals/tests/safety docs.

### Approval Criteria

- Phase 1 exit gate complete.
- Safety/eval/scaling plan reviewed and approved.
- Phase 2 start conditions recorded: cloning off, recording off, passive listening off, cost transparency shipped before voice output is user-visible.

## Verification

```text
git diff --check
clean

rg -n "voice clone|clone voice|record by default|background listening|checkout now|subscribe now|marketplace" docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md
2 hits, both negative boundary statements:
- "No hidden background listening"
- "voice cloning" in an eval description checking absence of promotional cloning copy
```

## Coordination Notes

- Claude B owns safety/eval/scaling sections.
- Claude A owns product/technical path sections.
- PM reviews and approves before Phase 2 starts.
- No push performed.
- Known issues: none.
