# 2D RPG (Pygame) — Initial Scope & Extensible Architecture

## Goal
Build a minimal, working 2D RPG skeleton in Pygame with three explorable screens (town, player home interior, northern farmland). Graphics use simple shapes/placeholders. Code is structured for easy extension (scenes, entities, triggers, events). Controls: Arrow keys/WASD to move, Space to interact.

## Tech & Targets
- **Python:** 3.10+
- **Pygame:** 2.5+
- **Window:** 960×540 (16:9), resizeable later
- **Target FPS:** 60

## High-Level Features (MVP)
1. **Town (default start)**  
   - Ground plane, roads/paths as colored rects.  
   - Simple rectangular buildings (e.g., shop, inn, player home).  
   - Collision with building footprints.  
   - **North edge transition** to Farmland scene.

2. **Player Home (interior)**  
   - Enter from Town via the home’s door trigger.  
   - Exit back to Town via interior door trigger.  
   - Minimal layout (floor, a couple placeholder rectangles for furniture; no interaction required yet).

3. **Farmland (north of town)**  
   - Open area with different ground color/tiling, simple fence rows/fields as rects.  
   - Collision only with fences/edge bounds.  
   - **South edge transition** returns to Town.

4. **Player movement**  
   - WASD or Arrow keys (both).  
   - Diagonals allowed; normalized movement so speed is consistent.  
   - Speed: 120–160 px/sec (config-driven).  
   - Space = “Interact” to trigger nearby action (door, sign, etc.).  
   - Optional (nice-to-have): Shift = Run.

5. **Camera & World**  
   - Scene-local camera follows player; clamps to map bounds.  
   - Scenes larger than the viewport are scrollable; smaller scenes are centered.

6. **Triggers & Interactions**  
   - Axis-aligned rectangular trigger zones with tags & payloads (e.g., `{type:"scene_change", target:"home_interior", spawn:"door_in"}`).  
   - Space bar checks for an “interactable” within a small radius/cone and fires its action.  
   - Debug overlay can draw trigger rects when enabled.

7. **Extensibility First**  
   - Scene Manager abstraction.  
   - Entity system with simple Components (lightweight).  
   - Event bus (lightweight) for decoupling interactions.  
   - Data-driven scene JSON for collision shapes, triggers, spawns.  
   - Single source of truth for constants & colors.

---

## Project Structure
simple_rpg/
README.md
requirements.txt
run_game.py
game/
init.py
config.py
assets.py
core/
scene.py
entity.py
events.py
input.py
camera.py
ui_debug.py
timings.py
scenes/
town.py
home_interior.py
farmland.py
data/
scenes/
town.json
home_interior.json
farmland.json
systems/
movement.py
collision.py
interaction.py
render.py
util/
math2d.py
serialization.py

## Core Architecture Notes

### Scenes
- `BaseScene` contract:
  - `load()` (read JSON map, create entities, triggers)
  - `enter(payload)` (spawn player at named spawn)
  - `update(dt)` / `draw(surface)`
  - `unload()`
- `SceneManager.push(name, payload)` / `replace(name, payload)` / `pop()`.
- Named spawns: `"town.spawn_player"`, `"home.spawn_interior"`, etc.

### Entities & Components
- `Entity(id, pos, components: dict, tags: set)`
- Minimal components:
  - `Transform`
  - `Collider`
  - `Renderable`
  - `PlayerControl`
  - `Interactable`
  - `Trigger`
- Systems iterate over entities by component presence.

### Event Bus
- Publish strings/enums + payload dicts:
  - `"scene.change"`, payload `{target, spawn}`
  - `"ui.debug.toggle"`
  - `"player.interact"`

### Input
- Action map for:
  - `MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT`
  - `INTERACT` (Space)
  - `DEBUG_TOGGLE` (F1)
- Both arrow keys & WASD.

### Camera
- Follow player; clamp to bounds.

### Data-Driven Scenes (JSON)
Example `town.json`:
```json
{
  "name": "town",
  "bounds": [0, 0, 2000, 1200],
  "spawns": {
    "start": [480, 270],
    "from_home": [600, 420],
    "from_farm": [960, 50]
  },
  "colliders": [
    {"rect": [550, 350, 200, 160], "tag": "building.home"},
    {"rect": [900, 300, 220, 180], "tag": "building.inn"}
  ],
  "interactables": [
    {
      "rect": [640, 380, 20, 40],
      "tag": "door.home",
      "prompt": "Home (Space)",
      "action": {"type": "scene_change", "target": "home_interior", "spawn": "door_in"}
    }
  ],
  "triggers": [
    {
      "rect": [0, -10, 2000, 10],
      "tag": "north_exit",
      "on_enter": {"type": "scene_change", "target": "farmland", "spawn": "south_entry"}
    }
  ]
}

Concrete Scene Rules
Town
Buildings: at least 3 rectangles: inn, shop, player home.

Collisions: solid building footprints.

Door (Home): Interactable → home_interior.

North Boundary: trigger to farmland.

Home Interior
Small room, floor rectangle, placeholder furniture.

Door: returns to town.

Farmland
Fields as alternating colored strips.

Fences as colliders.

South Boundary: returns to town.

Rendering Order
Ground/tiles

Static props/buildings

Player/entities

UI/prompts

Interaction UX
Prompt shown when in range of Interactable.

Space triggers action.

Only closest fires per press.

Configurability (config.py)
Window size, FPS

Colors

Movement speeds

Key bindings

Debug flags

Minimal Systems Behavior
MovementSystem

Normalized diagonals, collision resolution.

CollisionSystem

Static world collisions only.

InteractionSystem

Finds nearest interactable, handles Space.

RenderSystem

Draw shapes with camera transform.

Debug Tools
F1 toggles overlay (FPS, scene name, position).

Can draw colliders/triggers.

Save/Load (Skeleton Only)
save_game.json with {scene, spawn, player_pos}.

Tasks for the Agent
Scaffolding — create structure, requirements.txt with pygame>=2.5.

Core engine — scenes, entities, input, camera, events.

Systems — movement, collision, interaction, render, debug.

Data-driven scenes — create JSONs for 3 scenes.

Scene implementation — Town, HomeInterior, Farmland.

Prompts — on-screen prompt for interactables.

Config/extensibility — constants, docstrings, hooks.

Acceptance Criteria
Movement & collisions work.

Town ↔ Home door works.

Town ↔ Farmland transitions work.

Camera follows player.

Prompts show/hide correctly.

Debug overlay works.

Code is clean & extensible.

Future Add-Ons
Tilemaps via Tiled.

NPCs & dialogue.

Inventory & pickups.

Save/load slots.

Controller support.

Audio.

Player state machine.

Controls:

Move: WASD / Arrows

Interact: Space

Debug: F1

Dev Tips:

Scene JSONs in game/data/scenes/.

To add a new area: create JSON, add Scene class, register in SceneManager, add transitions.