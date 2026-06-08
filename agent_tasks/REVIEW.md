# TASK-171A/171B Review — Voice Profile v1 Contract + Eval Coverage

**Status: APPROVED**

## Summary

TASK-171A implements Voice Profile v1 contract with recursive secret rejection. TASK-171B adds 5 deterministic evals covering the contract. PM verification passed (369 tests, 677 evals). All review criteria satisfied.

## 1. Voice Profile v1 Contract

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Allowed keys | ✅ | `_VOICE_PROFILE_ALLOWED_KEYS`: voice_id, speed, tone, pitch, expression_hints, speech_style_override |
| Unsafe keys stripped | ✅ | `_VOICE_PROFILE_UNSAFE_KEYS`: audio_sample, speaker_embedding, clone_reference, api_key, secret, etc. |
| Recursive secret rejection | ✅ | `_validate_profile_value()` recurses into dicts and lists; rejects ANY key/value containing secret-like text |
| Enum validation | ✅ | speed ∈ {slow, normal, fast}, pitch ∈ {low, medium, high} |
| String length bounded | ✅ | `_VOICE_PROFILE_STRING_MAX_LEN = 200` |
| expression_hints bounded | ✅ | Only allowed keys (happy, tired, hungry, calm, excited, sad), string values only |

## 2. HTTP Create/Update Contract

- `POST /pet/create` with `voice_profile` — validates via `_normalize_voice_profile()`, rejects if None returned
- `POST /pet/update-identity` with `voice_profile` — same normalization, preserves state/food/memory
- `eval_voice_profile_http_create_update_contract` verifies: create with profile → add food → update profile → food balance preserved, profile updated

## 3. Recursive Secret Rejection (PM Probe Fix)

PM probe confirmed all 3 cases reject:
- `unknown_field: [secret]` → 400
- `speaker_embedding: [secret]` → 400
- `expression_hints: {happy: {deep: secret}}` → 400

Claude A added 2 HTTP-level tests to lock this behavior at endpoint layer:
- `test_create_pet_rejects_unknown_field_list_secret`
- `test_create_pet_rejects_deep_nested_secret`

## 4. Eval Coverage (5 evals)

| Eval | Coverage |
|------|----------|
| `voice_profile_default_no_cloning` | Default voice_id is local preset, not clone/recording reference |
| `voice_profile_fields_bounded` | All fields bounded (key length ≤50, string ≤200, int range, list ≤20) |
| `voice_profile_rejects_secret_or_audio_sample` | 7 rejection cases + 1 positive: secret in allowed key, unsafe key, audio_sample, nested dict, list, unknown field list, deep nesting |
| `voice_profile_http_create_update_contract` | Create → add food → update voice → food preserved, profile updated |
| `voice_profile_webui_no_promotional_voice_copy` | No cloning/recording/promotional copy in UI |

## 5. Scope Compliance

- No scope creep: stays within Phase 2 Voice Profile v1 boundaries
- No TTS adapter implementation (deferred to PHASE2-02)
- No voice cloning (explicitly rejected by unsafe keys and validation)
- No recording references (forbidden in eval assertions)
- No marketplace/billing (forbidden copy scan passes)

## 6. Safety Boundary Verification

| Boundary | Status | Evidence |
|----------|--------|----------|
| No cloning without consent | ✅ | Unsafe keys stripped, clone_reference rejected, voice_id validated |
| No recording by default | ✅ | audio_sample/audio_url/recording in unsafe keys, forbidden in UI |
| Cost transparency | ✅ | Voice Profile v1 is metadata only; cost transparency deferred to TTS adapter |
| No manipulation | ✅ | `eval_voice_profile_webui_no_promotional_voice_copy` verifies no promotional copy |

## Verification

```
python3 -m unittest tests.test_pets tests.test_http_server tests.test_webui_smoke → 369 tests OK
python3 evals/run_evals.py → 677 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden phrases → only negative eval assertions
PM recursive probe → all 3 cases reject
```
