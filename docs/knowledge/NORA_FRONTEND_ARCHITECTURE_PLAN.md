# Nora Frontend Architecture Plan

Last updated: 2026-06-09

## Decision

Nora should not jump directly from the current single-file Web UI to a full React/Vite rewrite.

The best next frontend architecture is a staged, low-risk migration:

```text
Single index.html
-> design tokens + native ES modules
-> small local Web Components / component modules
-> optional Vite + React + TypeScript only after component boundaries are stable
```

This keeps Nora local-first, preserves the Python runtime, avoids a premature Node build chain, and still fixes the current maintainability and design-restoration problem.

## Why This Is Better Than Immediate React

The current product risk is not lack of a frontend framework. The current risk is that the Pet Room UI, design source, and product interaction model are not yet stable enough.

Immediate React/Vite would add:

- a Node build toolchain,
- new package management,
- dev/build integration in the Python server,
- migration churn across tests and evals,
- and likely merge conflicts with the active Pencil Pet Room restoration work.

Native ES modules and Web Components are enough for the next step because Nora's Web UI is still a local, single-page surface served by Python. The first priority is to make the Pet Room visually faithful, modular, and testable without changing the backend runtime.

## Non-Goals

Do not use this plan as permission to add:

- real voice/TTS/audio provider integration,
- microphone, camera, screen, or location access,
- PWA service workers, notifications, or native desktop shell,
- billing/payment/marketplace/premium skill packs,
- real plugin installation or skill execution changes,
- 3D/VRM/Live2D runtime,
- a broad backend rewrite,
- or a full React migration before the migration gates below pass.

## Target Static Structure

After the first migration slice, the static UI should look like:

```text
mini_agent/static/
  index.html
  app.js
  api.js
  styles/
    tokens.css
    pet-room.css
  components/
    pet-room-canvas.js
    status-chips.js
    food-panel.js
    skill-shelf.js
    voice-preview.js
    memory-diary.js
    identity-editor.js
```

This is a target structure, not a one-shot rewrite requirement. Each file should be introduced only when the corresponding behavior is migrated and covered.

## Design Token Contract

The first architectural extraction should be tokens, not components.

Create `mini_agent/static/styles/tokens.css` with stable variables for:

- Pet Room canvas size and responsive max width.
- Pencil colors from `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md`.
- Typography scale for pet name, role, chip labels, body text, and compact panels.
- Radius, border, shadow, and z-index rules.
- Asset path variables or documented local asset references.

The active Pencil contract remains the source of truth for visual values. Tokens are the implementation layer, not a separate design source.

## Migration Steps

### Step 0: Finish Current Pencil Restoration

Complete and integrate `TASK-180A` and `TASK-180B` first.

Acceptance:

- `docs/knowledge/NORA_PET_ROOM_FRONTEND_CONTRACT.md` exists.
- Pet Room exposes `pet-room-design-shell`, `pet-room-canvas`, `pet-room-hero-image`, and `pet-room-status-chip`.
- Local Nora-01 hero asset is used; no external image URL.
- Existing Pet Room features still work.
- `python3 -m unittest tests.test_webui_smoke tests.test_http_server` passes.
- `python3 evals/run_evals.py` passes.
- `git diff --check` passes.

### Step 1: Extract Design Tokens And CSS Modules

Move design constants from inline style blocks in `index.html` into:

- `mini_agent/static/styles/tokens.css`
- `mini_agent/static/styles/pet-room.css`

Keep DOM structure and JS behavior stable.

Acceptance:

- Existing DOM markers remain unchanged.
- Pencil token evals still pass.
- No functional behavior changes.
- No build step required.

### Step 2: Extract API Boundary

Create `mini_agent/static/api.js` for existing Pet Room fetch calls.

The module should wrap the current endpoints without changing server behavior:

- `/pet/current`
- `/pet/create`
- `/pet/add-food`
- `/pet/feed`
- `/pet/care`
- `/pet/activity`
- `/pet/food-status`
- `/pet/update-identity`
- `/pet/relationship-memory`
- `/pet/voice-preview`

Acceptance:

- Request and response shapes remain compatible with current tests.
- Auth token handling remains centralized and unchanged from the user's perspective.
- No new endpoint is introduced.
- No hidden network call or external URL is introduced.

### Step 3: Extract Pet Room Canvas

Create `mini_agent/static/components/pet-room-canvas.js`.

This component owns only the first-screen visual room:

- wall,
- floor,
- Nora-01 hero image,
- ground shadow,
- name and role,
- Mood/Presence/Energy/Bond chip placement,
- design markers required by the Pencil contract.

It must not own food mutation, voice preview fetches, relationship memory writes, or skill execution.

Acceptance:

- The component can render from bounded pet state and identity data.
- It uses DOM text APIs for dynamic labels.
- It preserves the design markers and local asset path.
- It does not call fetch directly.

### Step 4: Extract Functional Panels One At A Time

Migrate in this order:

1. `status-chips.js`
2. `food-panel.js`
3. `skill-shelf.js`
4. `voice-preview.js`
5. `memory-diary.js`
6. `identity-editor.js`

Each extraction must preserve current markers and tests before the next component starts.

Acceptance for every component:

- No public API shape changes.
- Existing smoke tests pass.
- Existing deterministic evals pass.
- Dynamic user or pet text is escaped or assigned with DOM text APIs.
- No forbidden scope drift is introduced.

### Step 5: Add Visual Regression Workflow

After the UI is modular, add a lightweight visual check path.

Preferred first step:

- deterministic screenshot export of the Pet Room at a fixed viewport,
- compare against the Pencil reference manually during PM review,
- keep evals focused on tokens, markers, local assets, and forbidden copy.

Avoid adding Playwright dependency churn unless it is already available and the check is stable in local CI.

### Step 6: Decide Whether React Is Needed

Move to `frontend/` with Vite + React + TypeScript only if at least two of these are true:

- Identity Editor becomes a multi-step creator/customizer.
- Pet Room state coordination becomes hard to maintain with modules.
- There are multiple routes or app shells.
- Components need shared typed props and state management.
- Visual QA requires a richer frontend test stack.
- The native module approach causes repeated bugs or slows development.

If React is adopted, Python should remain the backend/runtime owner and serve the built frontend assets.

## React/Vite Migration Gate

If the gate is reached, use:

```text
frontend/
  package.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api/pet.ts
    components/
      PetRoomCanvas.tsx
      StatusChips.tsx
      FoodPanel.tsx
      SkillShelf.tsx
      VoicePreview.tsx
      MemoryDiary.tsx
      IdentityEditor.tsx
    styles/
      tokens.css
      pet-room.css
```

Rules:

- Python remains the source of truth for Pet State, Token Food, memory, auth, and skill safety.
- React owns UI composition only.
- API types must mirror existing HTTP contracts.
- The built output must be served by `nora-serve`.
- Existing eval names and DOM markers should remain stable or be intentionally migrated with compatibility tests.

## PM Task Sequence

Use this sequence after `TASK-180A/B` integrates:

1. `TASK-181A`: Extract Pet Room design tokens and CSS modules.
2. `TASK-181B`: Add eval/smoke coverage for token extraction and marker preservation.
3. `TASK-182A`: Extract `api.js` without endpoint changes.
4. `TASK-182B`: Add API boundary contract tests for current Pet Room calls.
5. `TASK-183A`: Extract `pet-room-canvas.js`.
6. `TASK-183B`: Add canvas component marker/local-asset/design-token coverage.
7. Continue one component pair at a time: food, skill shelf, voice preview, memory diary, identity editor.

Do not dispatch React/Vite work until the React/Vite migration gate is met and recorded in `agent_tasks/PHASE_STATUS.md`.

## Reviewer Checklist

Reviewers should reject frontend architecture patches that:

- rewrite unrelated Pet Room behavior while extracting structure,
- remove existing DOM markers without replacement coverage,
- introduce external image URLs,
- introduce real audio, recording, PWA, native, marketplace, billing, or 3D behavior,
- move state authority from Python to the browser,
- weaken auth token handling,
- or turn the Pet Room into a dashboard, table view, generic chatbot, or landing page.

## Current Recommendation

The immediate next action is still to finish `TASK-180A/B`.

After that, begin the native modular frontend migration with tokens and CSS extraction. This is the lowest-risk path that improves developer experience, preserves local-first packaging, and makes Pencil-to-frontend restoration verifiable.
