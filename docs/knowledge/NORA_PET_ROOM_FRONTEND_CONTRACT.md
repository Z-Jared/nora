# Nora Pet Room Frontend Contract

Last updated: 2026-06-09

## Source Of Truth

- Pencil file: `designs/nora_pet_web_ui.pen`
- Node: `P7UnVG` / `Room canvas`
- Reference export: `.nora_design_exports/nora_pet_web_ui_screen.png`
- Source image asset: `designs/images/generated-1780975241297.png`
- Web static copy: `mini_agent/static/nora-01-hero.jpg`

Note: the source image path uses a `.png` extension, but the file bytes are JPEG. The Web UI serves the controlled static copy as `.jpg`.

## Frame

- Width: 880px
- Height: 850px
- Fill: `#F5F3EE`
- Stroke: `#D8D1C8`
- Radius: 12px
- Effect: soft outer shadow

## Back Wall

- Fill: `#F1EEE7`
- Width: 880px
- Height: 550px
- Radius: top 12px

## Soft Floor

- Fill: `#DDD5CA`
- Width: 880px
- Height: 300px
- Position: y=550
- Radius: bottom 12px

## Pet Ground Shadow

- Fill: `#B9AA993D`
- Size: 390 x 56
- Position: x=244, y=654

## Hero Image

- Source asset: `designs/images/generated-1780975241297.png`
- Static asset: `mini_agent/static/nora-01-hero.jpg`
- Intended Pencil size: 410 x 530
- Intended Pencil position: x=235, y=122
- Fallback: CSS-only ceramic placeholder if the static asset cannot render

## Name And Role

- Name text: `Nora-01`
- Name type: Inter 40px / 800, centered
- Name position: x=276, y=720, width 328
- Role text: `ceramic desktop pet agent`
- Role type: Inter 15px / 600, centered
- Role position: x=255, y=768, width 370

## Status Chips

| Chip | Fill | Position | Size | Label | Example Value |
| --- | --- | --- | --- | --- | --- |
| Mood | `#F6DDC6` | x=92, y=78 | 150 x 54 | Mood | focused |
| Presence | `#DDE6DC` | x=610, y=116 | 150 x 54 | Presence | waiting with you |
| Energy | `#ECE3D6` | x=104, y=500 | 150 x 54 | Energy | 72 |
| Bond | `#E8DED4` | x=632, y=502 | 150 x 54 | Bond | 41 |

## Typography

- Family: Inter, then system sans-serif fallback
- Name: 40px, weight 800
- Role: 15px, weight 600
- Chip label: 11px, weight 800, uppercase
- Chip value: 14px, weight 700

## Implementation Markers

- `pet-room-design-shell`: outer Pencil-derived frame
- `pet-room-canvas`: wall and floor room canvas
- `pet-room-hero-image`: hero image and fallback container
- `pet-room-status-chip`: repeated status chip marker

## Responsive Adaptation

- Preserve the warm wall/floor room composition on all widths.
- At narrow widths, status chips may wrap below the hero instead of using exact absolute Pencil positions.
- Hero image may scale down, but must remain the first visual focus in the Pet Room.
- Dynamic text must use DOM text APIs or explicit HTML escaping.

## Restore Checklist

1. Canvas frame uses `#F5F3EE`, `#D8D1C8`, and 12px radius.
2. Wall and floor colors stay `#F1EEE7` and `#DDD5CA`.
3. Hero uses a local static copy of the Nora-01 asset, with no external image URL.
4. Name and role are centered below the hero.
5. Mood, Presence, Energy, and Bond chips render with the Pencil colors.
6. Existing Pet Room features remain visible: food, identity editor, speech preview, consent panel, expression, presence, greeting, reaction, skill shelf, diary, memory, and actions.
7. No marketplace, billing pressure, real audio, recording, PWA/native, plugin execution, or 3D/VRM scope drift appears in UI copy or code.
