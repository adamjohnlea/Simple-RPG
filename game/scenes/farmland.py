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
        # Farming
        self.plots = []  # list of dicts: {id, rect, state, planted_minutes}
        self._closest_plot = None
        self._growth_minutes_required = 300.0  # 5 in-game hours (~60s real at 5 min/sec)

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
        # Plots
        self.plots = []
        for p in self.data.get("plots", []):
            self.plots.append({
                "id": p.get("id"),
                "rect": pygame.Rect(*p["rect"]),
                "state": "untilled",  # untilled|tilled|planted|ready
                "planted_minutes": None,
            })

    def enter(self, payload: Dict[str, Any] | None = None):
        spawns = self.data.get("spawns", {})
        spawn_name = (payload or {}).get("spawn") or "south_entry"
        self.player = spawn_player_from_json(spawns, spawn_name)

    def _update_growth(self):
        try:
            from game.util.time_of_day import TimeOfDay
        except Exception:
            return
        now = TimeOfDay.minutes
        for plot in self.plots:
            if plot["state"] == "planted" and plot["planted_minutes"] is not None:
                elapsed = (now - plot["planted_minutes"]) % (24 * 60)
                if elapsed >= self._growth_minutes_required:
                    plot["state"] = "ready"

    def _find_player_plot(self):
        pr: pygame.Rect = self.player["rect"]
        closest = None
        best_d2 = (64 + 1) ** 2
        for plot in self.plots:
            r = plot["rect"]
            # proximity by center distance
            dx = r.centerx - pr.centerx
            dy = r.centery - pr.centery
            d2 = dx * dx + dy * dy
            if d2 < best_d2:
                best_d2 = d2
                closest = plot
        self._closest_plot = closest
        return closest

    def update(self, dt: float, input_sys):
        move_player(self.player, input_sys, dt, self.world_colliders)

        # Scene transitions
        for t in self.triggers:
            if self.player["rect"].colliderect(t["rect"]):
                on_enter = t.get("on_enter")
                if on_enter and on_enter.get("type") == "scene_change":
                    self.events.publish("scene.change", {
                        "target": on_enter.get("target"),
                        "spawn": on_enter.get("spawn")
                    })
                    return

        # Farming logic
        self._update_growth()
        plot = self._find_player_plot()
        self.prompt_text = None
        if plot is not None:
            state = plot["state"]
            # Set contextual prompt and handle inputs
            try:
                from game.util.state import GameState
                from game.util.time_of_day import TimeOfDay  # noqa: F401 only to ensure module present
            except Exception:
                GameState = None  # type: ignore
            if state == "untilled":
                self.prompt_text = "Till (E)"
                if input_sys.was_pressed("TILL"):
                    plot["state"] = "tilled"
            elif state == "tilled":
                have_seeds = (GameState is None) or (GameState.has_item("seeds", 1))
                if have_seeds:
                    self.prompt_text = "Plant (P)"
                    if input_sys.was_pressed("PLANT"):
                        if GameState is None or GameState.remove_item("seeds", 1):
                            # record in-game time at planting
                            from game.util.time_of_day import TimeOfDay
                            plot["state"] = "planted"
                            plot["planted_minutes"] = TimeOfDay.minutes
                else:
                    self.prompt_text = "Need Seeds"
            elif state == "planted":
                # Show progress bar; no special input
                self.prompt_text = "Growing..."
            elif state == "ready":
                self.prompt_text = "Harvest (Space)"
                if input_sys.was_pressed("INTERACT"):
                    # harvest gives 1 carrot, plot becomes tilled again
                    if GameState is not None:
                        GameState.add_item("carrot", 1)
                    plot["state"] = "tilled"
                    plot["planted_minutes"] = None

        # Basic interactables (none for now)
        _ = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # Camera
        self.camera.follow(self.player["rect"])

        input_sys.end_frame()

    def _draw_plots(self, surface: pygame.Surface):
        # Simple colors inline to avoid config churn
        soil = (130, 105, 70)
        tilled = (110, 85, 55)
        planted = (60, 130, 60)
        ready = (200, 170, 60)
        for plot in self.plots:
            r = self.camera.apply(plot["rect"])
            state = plot["state"]
            if state == "untilled":
                color = soil
            elif state == "tilled":
                color = tilled
            elif state == "planted":
                color = planted
            else:
                color = ready
            pygame.draw.rect(surface, color, r)
            pygame.draw.rect(surface, (0, 0, 0), r, 1)
            # Growth bar for planted
            if state == "planted":
                try:
                    from game.util.time_of_day import TimeOfDay
                    elapsed = (TimeOfDay.minutes - (plot["planted_minutes"] or 0)) % (24 * 60)
                except Exception:
                    elapsed = 0
                pct = max(0.0, min(1.0, float(elapsed) / float(self._growth_minutes_required)))
                bar_w = max(2, int(r.width * pct))
                bar = pygame.Rect(r.left, r.top - 6, bar_w, 4)
                pygame.draw.rect(surface, (50, 200, 50), bar)
                pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(r.left, r.top - 6, r.width, 4), 1)

    def draw(self, surface: pygame.Surface):
        # Draw ground and player, but not fences yet
        draw_world(surface, self.camera, Config.COLORS["ground_farm"], [], [], [], self.player)
        # Draw plots on top of ground, then fences, then UI
        self._draw_plots(surface)
        # Draw fences on top of plots
        for f in self.fences:
            pygame.draw.rect(surface, Config.COLORS["fence"], self.camera.apply(f))
        draw_prompt(surface, self.prompt_text)
        draw_day_night_tint(surface)
        draw_clock(surface)
