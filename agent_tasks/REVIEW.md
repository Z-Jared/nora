# TASK-186A/186B Review — Pet Room Skill Shelf native module extraction

**Status: APPROVED**

## Summary

TASK-186A extracts Pet Room skill shelf into `skill-shelf.js` as a native ES module. TASK-186B adds 6 evals and fixes 4 stale TASK-179 evals. Implementation correctly preserves all UI behavior, DOM markers, filtering rules, and read-only safety boundaries.

## Findings

### 1. skill-shelf.js Boundary — PASS

Module exports two functions:
- `skillCardsFromIdentity(identity, state)` — derives skill cards from pet identity
- `renderSkillShelf(identity, state)` — renders skill cards into DOM

The module:
- Uses `escapeHtml` for all dynamic content (icon, name)
- No direct `fetch()`, no `PetAPI`, no `petAction`, no `/pet/` endpoints, no tool/plugin execution
- Comments explicitly list non-goals (line 9)
- Read-only eval strips comments before scanning forbidden patterns

### 2. DOM Markers / Filtering / Safety — PASS

- **Icon mapping**: 24 skills → emoji, default ⚡ for unknown skills
- **Secret-like filtering**: `SECRET_PATTERNS` (sk-, bearer, api_key, token, secret, password, credential, private_key, auth) + `isSecretLike()` function
- **Stale cleanup**: `renderSkillShelf` clears `innerHTML` before returning on empty cards
- **Input sanitization**: non-string, empty, overlong (>50 chars), special-character labels filtered
- **DOM markers preserved**: `pet-skill-shelf`, `pet-skill-list`, `pet-skill-empty`, `pet-skill-card`, `skill-icon`, `skill-name`, `data-skill-count`

### 3. index.html Extraction — PASS

- Import: `import { skillCardsFromIdentity, renderSkillShelf } from '/static/components/skill-shelf.js'`
- Removed inline: `SKILL_ICONS`, `SECRET_PATTERNS`, `isSecretLike`, `skillCardsFromIdentity`, `renderSkillShelf`
- `renderPet()` call to `renderSkillShelf(id, st)` unchanged
- Test harness updated with skill shelf functions for test isolation

### 4. Eval Coverage — PASS

**6 new evals** (`skill_shelf_module_*`):
- `skill_shelf_module_file_present` — file exists, has ES exports, no build tooling
- `skill_shelf_module_wired` — index.html references skill-shelf with module import
- `skill_shelf_module_markers_preserved` — 7 required markers present across HTML/JS
- `skill_shelf_module_read_only_no_tool_execution` — strips comments, scans for forbidden patterns (fetch, petapi, petaction, /pet/, tool_call, execute_tool, run_tool, install, runtimetool, capabilityrouter)
- `skill_shelf_module_secret_filtering_and_stale_cleanup` — secret filtering, stale card cleanup, empty/malformed fallback
- `skill_shelf_module_no_marketplace_or_scope_drift` — no external URLs, build system markers, marketplace/payment/voice/PWA/3D drift

**4 fixed TASK-179 evals** — use `_read_skill_shelf_surface()` helper to read combined `index.html` + `skill-shelf.js`:
- `pet_skill_shelf_markers_present`
- `skill_shelf_mapping_rules`
- `skill_shelf_no_stale_content_on_empty`
- `skill_shelf_rejects_secret_like_skills`

### 5. Scope Drift — PASS

No evidence of:
- React/Vite/TypeScript/npm/build step
- External URLs in skill-shelf.js
- Marketplace/payment/premium skill
- Voice/native/PWA/3D/VRM

## Verification

```
python3 -m unittest tests.test_webui_smoke tests.test_http_server → 411 tests OK
python3 evals/run_evals.py → 750 passed, 0 failed, 0 skipped
git diff --check → clean
rg scan → skill-shelf.js only hits negative safety comment
```
