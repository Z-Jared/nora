# TASK-180A/TASK-180B Review — Pencil Pet Room Design Restoration

**Status: APPROVED**

## Summary

TASK-180A adds Pencil-derived design shell, canvas, hero image with CSS fallback, status chips, and name/role display. TASK-180B adds 5 deterministic evals and 6 smoke tests. Implementation materially improves visual fidelity while preserving all existing Pet Room features.

## Findings

### 1. Material Improvement (Not Just Markers)

The implementation adds:
- **Design shell** (`pet-room-design-shell`): 880px frame with correct colors (#F5F3EE background, #D8D1C8 border, 12px radius)
- **Canvas** (`pet-room-canvas`): Wall (#F1EEE7, 340px) + floor (#DDD5CA, 260px) composition
- **Hero image** (`pet-room-hero-image`): Local `nora-01-hero.jpg` with CSS ceramic fallback on error
- **Status chips**: Mood, Presence, Energy, Bond with Pencil-specified colors
- **Name/Role**: Centered below hero, updated from identity data
- **Action buttons**: Restyled with hints, warm brown primary color (#8F5A3C)

All Pencil contract colors are present in CSS. `renderPet()` extended to update design markers.

### 2. Design Contract and Asset

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Contract document | ✅ | `NORA_PET_ROOM_FRONTEND_CONTRACT.md` with colors, typography, markers, restore checklist |
| Local asset | ✅ | `mini_agent/static/nora-01-hero.jpg` exists, referenced as `/static/nora-01-hero.jpg` |
| No external URLs | ✅ | `eval_pet_room_design_local_asset_only` verifies no http/https in hero section |
| PM asset correction | ✅ | Source .png contains JPEG bytes → integrated as .jpg (documented in contract) |
| CSS fallback | ✅ | `onerror` handler hides img, shows ceramic-body placeholder |

### 3. Existing Features Preserved

`renderPet()` extended (not replaced) to update:
- `pet-room-name` from `identity.name`
- `pet-room-role` from `identity.relationship_role`
- Status chip values from `expressionFromState()`, `presenceFromState()`, and state fields

All existing Pet Room features remain: food/status, identity editor, speech bubble/consent, expression/presence, greeting/reaction, skill shelf, diary/memory/actions.

### 4. Eval Coverage (5 evals)

| Eval | What it locks |
|------|---------------|
| `pencil_design_contract_present` | Contract doc references source Pencil file, canvas dimensions, all 4 colors, asset paths, 4 markers |
| `pet_room_design_markers_present` | Web UI contains design-shell, canvas, hero-image, status-chip markers |
| `pet_room_design_tokens_match_pencil` | All 4 Pencil colors present in index.html |
| `pet_room_design_local_asset_only` | Local .jpg file exists, referenced in HTML, no external http/https in hero section |
| `pet_room_design_no_scope_drift_copy` | No marketplace/voice/recording/3D/VRM/PWA/billing copy |

### 5. Smoke Tests (6 tests)

- DOM markers (design shell, canvas, hero image, chips)
- Status chips (all 8 elements: chip + value for mood/presence/energy/bond)
- Name/role markers
- Hero image uses local asset, no external URLs
- Ceramic fallback exists with onerror handler
- renderPet updates design markers (name, role, chip values)

### 6. Scope Compliance

- ✅ No external image URLs
- ✅ No voice/audio/recording
- ✅ No marketplace/payment
- ✅ No service worker/notification/native
- ✅ No plugin execution
- ✅ No 3D/VRM
- ✅ Frontend architecture plan is separate planning doc, not implementation

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 378 tests OK
python3 evals/run_evals.py → 719 passed, 0 failed, 0 skipped
git diff --check → clean
rg forbidden-copy → only negative safety assertions
```
