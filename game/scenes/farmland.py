import pygame
from typing import Dict, Any

from game.config import Config
from game.core.scene import BaseScene
from game.scripts_common import spawn_player_from_json
from game.systems.movement import move_player
from game.systems.interaction import handle_interaction
from game.systems.render import draw_world, draw_prompt, draw_day_night_tint, draw_clock
from game.util.serialization import load_json


class FarmlandScene(BaseScene):
    def __init__(self, manager):
        super().__init__(manager)
        self.data = None
        self.fences = []

    def load(self):
        self.data = load_json(f"{Config.SCENES_DIR}/farmland.json")
        b = self.data["bounds"]
        self.bounds = pygame.Rect(*b)
        self.camera.set_bounds(self.bounds)
        # Colliders (fences/edges)
        self.world_colliders = [pygame.Rect(*c["rect"]) for c in self.data.get("colliders", [])]
        self.fences = [pygame.Rect(*c["rect"]) for c in self.data.get("colliders", [])]
        # Interactables (none for MVP)
        self.interactables = [{**i, "rect": pygame.Rect(*i["rect"])} for i in self.data.get("interactables", [])]
        # Triggers (south edge back to town)
        self.triggers = [{**t, "rect": pygame.Rect(*t["rect"])} for t in self.data.get("triggers", [])]

    def enter(self, payload: Dict[str, Any] | None = None):
        spawns = self.data.get("spawns", {})
        spawn_name = (payload or {}).get("spawn") or "south_entry"
        self.player = spawn_player_from_json(spawns, spawn_name)

    def update(self, dt: float, input_sys):
        move_player(self.player, input_sys, dt, self.world_colliders)

        # South trigger back to town
        for t in self.triggers:
            if self.player["rect"].colliderect(t["rect"]):
                on_enter = t.get("on_enter")
                if on_enter and on_enter.get("type") == "scene_change":
                    self.events.publish("scene.change", {
                        "target": on_enter.get("target"),
                        "spawn": on_enter.get("spawn")
                    })
                    return

        # Interaction (none expected)
        self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # Camera
        self.camera.follow(self.player["rect"])

        input_sys.end_frame()

    def draw(self, surface: pygame.Surface):
        draw_world(surface, self.camera, Config.COLORS["ground_farm"], [], [], self.fences, self.player)
        draw_prompt(surface, self.prompt_text)
        draw_day_night_tint(surface)
        draw_clock(surface)
