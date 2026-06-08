# TASK-175A/175B CCB Review

**Status: APPROVED**

## Summary

TASK-175A adds CSS-only expression state mapping from pet state to robot avatar. TASK-175B adds 4 deterministic evals locking the expression state contract. All review criteria satisfied.

## Review Findings

### 1. CSS-Only Deterministic Expression Mapping

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Pure function | ✅ | `expressionFromState(st)` derives key/icon/label/detail from `{mood, energy, hunger}` — no side effects |
| Deterministic thresholds | ✅ | Fixed thresholds: hunger≥70→hungry, energy≤20→sleepy, energy≤40→low-energy, mood≥75+energy≥60→happy, mood≥55+energy≥50→focused, else→calm |
| Safe fallback | ✅ | Missing/null state defaults to 50 for mood/energy/hunger; final fallback is "calm" |
| CSS-only | ✅ | 6 expression classes with CSS rules only — no JS-driven animation or state mutation |

### 2. Stable DOM Markers and `data-expression`

| Marker | Type | Evidence |
|--------|------|----------|
| `#pet-expression-state` | Container | Line 462 in index.html |
| `#pet-expression-icon` | Emoji icon (✨💤🔴🔋🎯🌊) | Line 463 |
| `#pet-expression-label` | Text label (Happy/Sleepy/etc.) | Line 464 |
| `#pet-expression-detail` | Numeric detail (e.g., "Mood at 80/100") | Line 465 |
| `data-expression` | Attribute on `#pet-avatar` | Set by `applyExpression()` |

### 3. No Side Effects

| Check | Status | Evidence |
|-------|--------|----------|
| No fetch/network | ✅ | `eval_expression_state_read_only_no_fetch` scans function bodies for forbidden patterns |
| No food debit | ✅ | No `food_debit` or `add-food` references |
| No activity/memory mutation | ✅ | No `relationship-memory` or `activity` references |
| No voice-preview | ✅ | No `voice-preview` references |
| No provider/network | ✅ | No `microphone`, `camera`, `navigator.media`, `navigator.geolocation` references |
| No state mutation | ✅ | `applyExpression` only does classList, setAttribute, textContent |

### 4. Dynamic Text Escaping

All DOM updates use `textContent`, not `innerHTML`:
- `iconEl.textContent = expr.icon`
- `labelEl.textContent = expr.label`
- `detailEl.textContent = expr.detail`

`test_expression_detail_uses_dom_text` verifies textContent usage.

### 5. Eval Coverage (4 evals)

| Eval | What it locks |
|------|---------------|
| `pet_expression_markers_present` | All 10 required markers: 4 DOM IDs + data-expression + 6 CSS classes |
| `expression_state_mapping_rules` | `expressionFromState` references mood/energy/hunger, has fallback for missing state |
| `expression_state_read_only_no_fetch` | Function bodies contain no fetch/food_debit/pet-endpoints/microphone/camera/screen/location |
| `expression_state_no_voice_or_surveillance_copy` | No voice clone/recording/microphone/camera/screen/location/marketplace/3D/VRM copy |

### 6. No Phase 2 Scope Drift

✅ CSS-only, deterministic, read-only. No real audio, PWA/native, 3D/VRM, billing, marketplace, or new worker setup.

## Verification

- 297 unit tests OK
- 695 evals passed, 0 failed, 0 skipped
- git diff --check: clean
- Forbidden-copy scan: only negative safety assertions in evals
