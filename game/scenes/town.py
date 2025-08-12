import pygame
from typing import Dict, Any

from game.config import Config
from game.core.scene import BaseScene
from game.scripts_common import spawn_player_from_json
from game.systems.movement import move_player
from game.systems.interaction import handle_interaction
from game.systems.render import draw_world, draw_prompt
from game.util.serialization import load_json


class TownScene(BaseScene):
    def __init__(self, manager):
        super().__init__(manager)
        self.data = None
        self.roads = []
        self.buildings = []
        self.fences = []
        self._building_defs = []  # keep tags for marking home
        self._label_font = None

    def load(self):
        self.data = load_json(f"{Config.SCENES_DIR}/town.json")
        b = self.data["bounds"]
        self.bounds = pygame.Rect(b[0], b[1], b[2], b[3])
        self.camera.set_bounds(self.bounds)
        # Roads/paths (non-colliding visuals)
        self.roads = [pygame.Rect(*r["rect"]) for r in self.data.get("roads", [])]
        # Colliders (buildings etc.)
        self._building_defs = [{**c, "rect": pygame.Rect(*c["rect"])} for c in self.data.get("colliders", [])]
        self.world_colliders = [c["rect"] for c in self._building_defs]
        self.buildings = [c["rect"] for c in self._building_defs]
        # Interactables
        self.interactables = [{**i, "rect": pygame.Rect(*i["rect"])} for i in self.data.get("interactables", [])]
        # Triggers
        self.triggers = [{**t, "rect": pygame.Rect(*t["rect"])} for t in self.data.get("triggers", [])]

    def enter(self, payload: Dict[str, Any] | None = None):
        spawns = self.data.get("spawns", {})
        spawn_name = (payload or {}).get("spawn") or "start"
        self.player = spawn_player_from_json(spawns, spawn_name)

    def update(self, dt: float, input_sys):
        # Movement and collisions
        move_player(self.player, input_sys, dt, self.world_colliders)

        # Triggers (on_enter only for MVP)
        for t in self.triggers:
            if self.player["rect"].colliderect(t["rect"]):
                on_enter = t.get("on_enter")
                if on_enter and on_enter.get("type") == "scene_change":
                    self.events.publish("scene.change", {
                        "target": on_enter.get("target"),
                        "spawn": on_enter.get("spawn")
                    })
                    return

        # Interaction
        self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # Camera follow
        self.camera.follow(self.player["rect"])

        input_sys.end_frame()

    def draw(self, surface: pygame.Surface):
        draw_world(surface, self.camera, Config.COLORS["ground_town"], self.roads, self.buildings, [], self.player)

        # Draw visual door for player's home (based on interactable tag)
        door_color = Config.COLORS.get("door", (200, 80, 40))
        for it in self.interactables:
            if it.get("tag") == "door.home":
                pygame.draw.rect(surface, door_color, self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)
                break

        # Highlight the player's home building with an outline and label
        home_marker = Config.COLORS.get("home_marker", (255, 215, 0))
        home_rect = None
        for b in self._building_defs:
            if str(b.get("tag", "")) == "building.home":
                home_rect = b["rect"]
                break
        if home_rect is not None:
            applied = self.camera.apply(home_rect)
            pygame.draw.rect(surface, home_marker, applied, 3)
            # Label "Home" above the building
            if self._label_font is None:
                self._label_font = pygame.font.SysFont("arial", 16)
            label = self._label_font.render("Home", True, home_marker)
            label_pos = (applied.centerx - label.get_width() // 2, max(0, applied.top - label.get_height() - 4))
            # add a subtle shadow for readability
            shadow = self._label_font.render("Home", True, (0, 0, 0))
            surface.blit(shadow, (label_pos[0] + 1, label_pos[1] + 1))
            surface.blit(label, label_pos)

        # draw prompt last
        draw_prompt(surface, self.prompt_text)
