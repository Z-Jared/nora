# TASK-170A/B Review — Phase 2 Voice & Presence Plan

**Status: APPROVED**

## Summary

TASK-170A (Claude A: product/technical plan) and TASK-170B (Claude B: safety/eval/scaling plan) are well-scoped Phase 2 preparation documents. The combined plan at `docs/knowledge/PHASE_2_VOICE_PRESENCE_PLAN.md` complies with PM_LOOP.md gate protocols and maintains all safety boundaries.

## Review Findings

### 1. PM_LOOP.md Compliance

| Protocol | Status | Evidence |
|----------|--------|----------|
| Phase 1 Exit Gate §1 (no premature Phase 2 features) | ✅ | Plan explicitly scopes Phase 2 to Voice Profile v1, TTS adapter boundary, Web/PWA presence, CSS idle signals. No voice cloning, 3D/VRM, marketplace, billing, or native code. |
| Phase 1 Exit Gate §6 (Phase 2 tech plan) | ✅ | Voice Profile v1 data contract, TTS adapter boundary with text fallback, Web/PWA presence path, desktop prerequisites, safety policy, eval plan, task candidates all documented. |
| Phase 2 Worker Scaling §1 (default A/B) | ✅ | Plan recommends A/B only at Phase 2 start. |
| Phase 2 Worker Scaling §2 (3+ low-conflict workflows for C/D) | ✅ | "Do not open Claude C/D at Phase 2 start" with explicit conditions: 3+ independent workstreams, low file overlap, clean worktrees, PHASE_STATUS.md recording. |
| Phase 2 Worker Scaling §5 (no blind parallelism) | ✅ | "initial voice/profile/presence work shares core files and would likely increase merge conflict risk" |

### 2. Safety Boundaries

| Boundary | Status | Evidence |
|----------|--------|----------|
| No cloning without consent | ✅ | "default is no voice cloning", "must require explicit consent, clear disclosure, revocation" |
| No recording by default | ✅ | "No recording by default", "No hidden background listening" |
| Cost transparency | ✅ | "estimate before speak", "voice cost in food-status", "no surprise charges" |
| No manipulation | ✅ | "no pressure, no dependency framing, no purchase manipulation" |
| No background surveillance | ✅ | "no always-on surveillance", "transparent data flow", "local-first default" |
| Phase 2 starts with consent/fallback/cost | ✅ | "Phase 2 implementation must start with consent, fallback, and cost transparency foundations before any user-visible audio feature" |

`rg` scan confirms only negative boundary statements match forbidden phrases.

### 3. Phase 2 Task Candidates

**First wave (7 tasks):** All small (S/M), verifiable, and implementable without deep voice/native/marketplace work:
- PHASE2-01–05: Claude A product tasks (voice profile, TTS adapter, speech bubble, expression CSS, consent/cost)
- PHASE2-06–07: Claude B eval/safety tasks

**Later wave (3 tasks):** Properly blocked by prerequisites:
- PHASE2-08: PWA offline (blocked by Web presence loop stable)
- PHASE2-09: Desktop floating pet (blocked by Web/PWA presence reviewed)
- PHASE2-10: Real TTS provider (blocked by adapter protocol + consent UI + cost evals)

No task directly jumps to deep voice, native desktop, or marketplace. ✅

### 4. Worker Scaling Recommendation

**Start with A/B only — reasonable.** Initial voice/profile/presence work shares `pets.py`, `server.py`, `index.html`, and eval files. Opening C/D immediately would increase merge conflict risk before boundaries stabilize. The plan documents clear conditions for later C/D expansion.

### 5. No Misleading Claims or Boundary Violations

- No "already implemented" claims for Phase 2 features
- No hidden costs, promotional copy, or subscription pressure
- No real payment, marketplace, or billing language
- No voice cloning presented as default or easy
- All Phase 2 work framed as opt-in, consent-based, cost-transparent

## Verification

- 343 unit tests OK, 672 evals passed, 0 skipped
- `git diff --check` clean
- `rg` forbidden phrases: only negative boundary statements found

## Condition for Integration

After approval, PM should:
1. Update `PHASE_STATUS.md` to mark Phase 1 Exit Gate planning complete
2. Record Phase 2 worker plan (A/B only)
3. Add PHASE2-01 through PHASE2-07 to `BACKLOG.md`
4. Begin Phase 2 with PHASE2-01 (Voice Profile v1 validation)
