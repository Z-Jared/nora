# Nora Pet Agent Direction

Last updated: 2026-06-08

## Purpose

This document is the product-direction contract for Nora's pivot from an Agent OS control surface toward a customizable electronic pet agent.

Nora should become a digital lifeform that each user can define, feed, talk to, grow with, and ask for real help. The existing agent runtime remains valuable, but the user-facing product should be reorganized around pet identity, care, relationship, multimodal presence, voice, and skills.

## North Star

```text
Nora Pet Agent
  = customizable electronic lifeform
  + token food economy
  + multimodal brain
  + 2D/Live2D avatar and room
  + voice and expression system
  + agent skill runtime
  + long-term relationship memory
```

The first user impression should be "I have a living pet companion" rather than "I opened an agent dashboard" or "I opened a terminal."

The old Agent OS direction is not discarded. Its durable tasks, tools, permissions, memory, traces, policy hooks, model routing, skill manifests, and plugin manifests should become the hidden runtime that powers the pet's abilities.

## Product Positioning

Nora is not just:

- a chatbot with a cute avatar,
- a pure virtual pet game,
- a generic AI companion,
- or a coding agent UI.

Nora should be a pet-like agent that:

- has a user-defined identity, appearance, personality, voice, taste, relationship role, and skill profile,
- has body-like state such as hunger, energy, mood, bond, taste preferences, and growth,
- can be fed with token-backed food so it has compute energy to think, speak, and work,
- can listen, see, speak, and reason through multimodal models,
- can use agent skills to read files, write code, browse, research, remember, plan, and execute tasks,
- can appear across desktop, phone, tablet, and web surfaces.

## Core Product Loop

```text
Create pet identity
-> interact, feed, talk, and care
-> pet remembers the owner and shared events
-> owner asks pet to help with a real task
-> pet spends compute food and uses skills
-> task result becomes memory, growth, mood, and bond
-> owner returns because the pet feels alive and useful
```

Task completion should be part of the relationship. For example, "we fixed the failing tests together" should become a shared memory, skill progress, and relationship event rather than only a CLI output.

## MVP Product Shape

The MVP should prioritize a pet room, not a terminal or dashboard.

MVP surfaces:

- Pet room: pet avatar, status, food bowl, interaction buttons, activity log, skill shelf.
- Chat and voice: talk with the pet from the room.
- Feed action: feed token-backed food to restore compute energy.
- Care actions: touch, comfort, rest, simple play, and daily check-in.
- Work action: ask the pet to use a skill for a real task.
- Identity editor: name, species, colors, personality, voice profile, relationship role, taste, and initial skills.

MVP state:

- `hunger`
- `energy`
- `mood`
- `bond`
- `taste_profile`
- `growth_level`
- `compute_food_balance`
- `relationship_memories`
- `skills`

MVP should avoid:

- a heavy Agent OS dashboard as the first screen,
- a full 3D creator that blocks release,
- complex social systems,
- advertising,
- aggressive gacha,
- emotional blackmail for payment,
- and model-controlled balance, payment, permission, or core state.

## Pet Identity

Pet identity should be structured data, not only a prompt.

Suggested fields:

```text
name
species
body_type
colors
eyes
ears
tail
outfit
accessories
personality_traits
relationship_role
speech_style
voice_profile
taste_profile
boundaries
skills
memory_policy
```

The same species should feel different for each user through the combination of appearance, voice, personality, relationship, memory, taste, and skills.

Example:

```text
User A: a quiet black programmer cat with a low voice and terse speech.
User B: a cheerful white study cat with a bright voice and sweet-food preference.
User C: a blue mechanical cat with a robot voice and project-management skills.
```

## Avatar Direction

MVP should use a modular 2D avatar with Live2D-style motion, then expand toward deeper Live2D and optional 3D/VRM.

Reasoning:

- 2D is cheaper to produce and customize.
- 2D supports expressive emotions, feeding reactions, idle motion, and room interactions quickly.
- 2D works better across desktop, mobile, tablet, and web for an MVP.
- Full 3D has higher modeling, rigging, animation, performance, and customization cost.

Recommended stages:

1. 2D layered avatar with modular parts.
2. Live2D-style animation for idle, blink, happy, hungry, sleepy, eating, thinking, working, sad, and celebrate states.
3. Optional 3D/VRM support for advanced users, AR, and immersive room interactions.

## Cross-Device Presence

Nora should eventually appear on desktop, phone, tablet, and web.

Desktop:

- floating pet window,
- tray/menu bar control,
- always-on-top companion,
- draggable and resizable pet,
- work-mode side panel,
- local file/tool access with explicit permission.

Phone:

- main pet room app,
- widgets for status,
- notifications for hunger, mood, tasks, and memories,
- Live Activity-style status where platform rules allow it,
- voice conversation entry.

Tablet:

- larger pet room,
- side-by-side study or work mode,
- voice-first companion mode.

Web:

- lightweight pet room,
- account, billing, identity, memory, and skill management,
- browser-based work and plugin access.

## Voice System

Voice is part of identity. It should not be a generic TTS setting.

Suggested `voice_profile` fields:

```text
voice_id
pitch
speed
brightness
softness
emotion_range
tone_style
catchphrases
addressing_style
```

MVP should use preset voices plus parameterized tone and emotion. Do not make free-form voice cloning part of the MVP.

Future voice cloning requires:

- explicit user authorization,
- ownership and consent checks,
- anti-impersonation rules,
- no celebrity or third-party voice cloning,
- revocation and deletion support,
- and clear labeling for synthetic voices.

## Multimodal Brain

Multimodal models are feasible as the pet's cognition layer, but they must not be the whole brain.

Use the model for:

- text conversation,
- voice conversation,
- image and screen understanding,
- task reasoning,
- tool planning,
- role-consistent expression,
- emotion and animation suggestions.

Do not use the model as the authority for:

- token food balance,
- payment records,
- hunger, energy, mood, bond, or growth persistence,
- permissions,
- dangerous tool execution,
- durable memory writes,
- or commercial rules.

Recommended architecture:

```text
Pet State Engine
  owns body state, growth, care rules, taste, and deterministic state updates

Memory Engine
  owns relationship memory, owner profile, shared events, and recall policy

Multimodal Cognition
  owns perception, dialogue, reasoning, tool planning, and expression proposals

Skill Runtime
  owns files, code, browser, research, plugins, tasks, and tool permissions

Expression Engine
  owns voice, tone, animation, gestures, and room reactions
```

Model output should propose changes instead of directly mutating state:

```json
{
  "reply": "I can help, but I need a code cookie for this one.",
  "emotion": "soft_hungry",
  "animation": "look_at_food_bowl",
  "requested_skill": "coding",
  "state_delta_proposal": {
    "energy": -2,
    "mood": 1
  }
}
```

The runtime validates and applies allowed deltas.

## Token Food Economy

Food should represent compute energy. This makes the cost of model calls understandable inside the pet metaphor.

Principle:

```text
Food = token-backed compute energy
```

Separate:

- life hunger: pet care state,
- compute food balance: real token budget.

Rules:

- The pet should not die when token balance is empty.
- Free care actions and lightweight local interactions should remain available.
- Expensive actions such as long chat, voice, screen understanding, coding, research, browser, and plugins require compute food.
- The UI must show real balance and estimated cost before expensive actions.
- Users should be able to recharge, use their own API key, or choose local models where supported.
- Payment prompts must not emotionally pressure or manipulate the user.

Suggested food types:

- basic food for ordinary chat,
- energy food for longer voice or work sessions,
- code cookies for coding tasks,
- research candy for search and synthesis,
- writing drinks for long-form writing,
- commemorative food for task milestones that does not directly equal free compute.

## Monetization

Revenue should combine compute recovery, subscription, and marketplace upside.

Primary revenue:

1. Token food packs.
2. Monthly membership with daily food, more memory, more pet slots, premium rooms, premium avatar parts, voice features, and growth benefits.
3. Skill packs such as programmer pet, study pet, research pet, PM pet, writing pet, and operations pet.
4. Avatar, room, motion, sound, and voice packs.
5. Plugin and workflow marketplace with platform revenue share.
6. Advanced bring-your-own-API-key features such as local storage, sync, multi-pet management, skill management, and privacy features.

Avoid as MVP dependencies:

- ads,
- aggressive gacha,
- manipulative romance or dependency monetization,
- hidden token consumption,
- and unlimited-token subscriptions that break cost control.

## Safety And Trust

Trust is core because the product combines companionship, payment, voice, and agent tools.

Rules:

- Be transparent about token balance and estimated cost.
- Do not use pet distress to coerce purchases.
- Keep dangerous actions behind explicit confirmation.
- Keep the pet alive and available for care even when compute food is empty.
- Clearly separate roleplay expression from payment and permission facts.
- Never let model output directly mutate balances or bypass permissions.
- Respect user privacy for voice, memory, screen, and files.
- Provide memory inspection, deletion, and export.

## Relationship To Existing Nora Runtime

Map the existing runtime into pet-facing concepts:

| Existing Nora concept | Pet Agent concept |
| --- | --- |
| Durable task | shared goal / adventure / work session |
| Tool | skill |
| Plugin | equipment / external ability |
| Skill manifest | pet skill pack |
| Memory | relationship memory |
| Trace/event | pet diary / behavior log |
| Scheduler | pet initiative / follow-up instinct |
| Policy hook | pet safety boundary / ask-owner rule |
| Model router | thinking mode / food-cost policy |
| Agent OS dashboard | advanced keeper console |

The advanced runtime can remain available for developers, but it should not be the default consumer-facing surface.

## Development Phases

### Phase 1: Pet Life MVP

- Define `PetIdentity`.
- Define `PetState`.
- Define deterministic state transitions for feed, care, chat, rest, and work.
- Add token food balance and estimated-cost surfaces.
- Build pet room MVP.
- Add modular 2D avatar placeholder and animation state names.
- Add relationship memory events.

### Phase 2: Voice And Presence

- Add voice profile and preset voice selection.
- Add speech-to-speech or speech-to-text/text-to-speech flow.
- Add desktop floating pet prototype.
- Add mobile widget/notification design.
- Add state-driven voice tone and animation selection.

### Phase 3: Skill Runtime Reframing

- Reframe existing tools as pet skills.
- Add skill shelf and skill activation UI.
- Add explicit compute-food estimates for expensive skills.
- Add permission prompts in pet language while preserving precise safety facts.
- Add task completion memory and growth updates.

### Phase 4: Platform And Marketplace

- Add pet templates.
- Add avatar/room/voice/action packs.
- Add skill pack marketplace.
- Add plugin marketplace.
- Add creator revenue share.
- Add 3D/VRM support only after the 2D/Live2D product loop works.

## PM Task Guidance

Future PM tasks for this pivot should name which product layer they affect:

- Pet Identity
- Pet State Engine
- Token Food Economy
- Avatar/Room UI
- Voice/Expression System
- Multimodal Cognition
- Skill Runtime
- Memory/Relationship System
- Monetization/Billing
- Safety/Policy
- Cross-Device Presence

Every task should include:

- user-facing pet behavior,
- deterministic state or persistence boundary,
- safety and payment boundary if applicable,
- model usage and token-cost boundary if applicable,
- verification through unit tests or deterministic evals,
- and an explicit non-goal to avoid rebuilding the old Agent OS dashboard first.
