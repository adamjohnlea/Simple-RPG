import pygame
from typing import Dict, Any

from game.config import Config
from game.core.scene import BaseScene
from game.scripts_common import spawn_player_from_json
from game.systems.movement import move_player
from game.systems.interaction import handle_interaction, get_closest_interactable
from game.systems.render import draw_world, draw_prompt, draw_day_night_tint, draw_clock
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
        # Dialog state
        self._dialog_lines = None  # list[str] or None
        self._on_dialog_complete = None  # callable or None
        self._dialog_font = None

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

    def _start_dialog(self, lines, on_complete=None):
        self._dialog_lines = list(lines)
        self._on_dialog_complete = on_complete

    def _advance_dialog(self):
        if not self._dialog_lines:
            return
        self._dialog_lines.pop(0)
        if not self._dialog_lines:
            cb = self._on_dialog_complete
            self._dialog_lines = None
            self._on_dialog_complete = None
            if cb:
                cb()

    def _cancel_dialog(self):
        # Cancel without invoking completion callback (e.g., back out from shop confirm)
        self._dialog_lines = None
        self._on_dialog_complete = None

    def _handle_npc_interaction(self, closest):
        from game.util.state import GameState
        tag = str(closest.get("tag", ""))
        # Farmer quest logic
        if tag == "npc.farmer":
            if not GameState.flags.get("quest_started"):
                self._start_dialog([
                    "Farmer: Hey there! Could you bring me a bag of seeds from the shop?",
                    "Farmer: I will make it worth your while!",
                ], on_complete=lambda: GameState.flags.__setitem__("quest_started", True))
            elif not GameState.flags.get("quest_completed"):
                if GameState.has_item("seeds", 1):
                    def _reward():
                        GameState.remove_item("seeds", 1)
                        GameState.upgrades["boots"] = True
                        GameState.coins += 5
                        GameState.flags["quest_completed"] = True
                    self._start_dialog([
                        "Farmer: You got the seeds! Thank you!",
                        "Farmer: Take these Boots and some coins as thanks.",
                        "(Shift to sprint is now available.)",
                    ], on_complete=_reward)
                else:
                    self._start_dialog([
                        "Farmer: Still waiting on those seeds from the shop.",
                    ])
            else:
                self._start_dialog(["Farmer: Thanks again! Those boots suit you."])
        # Shopkeeper simple shop
        elif tag == "npc.shopkeeper":
            def _buy():
                if GameState.coins >= 5:
                    GameState.coins -= 5
                    GameState.add_item("seeds", 1)
                    self._start_dialog(["Shopkeeper: Here you go, one bag of seeds!"], on_complete=None)
                else:
                    self._start_dialog(["Shopkeeper: Sorry, you don't have enough coins."], on_complete=None)
            # A tiny prompt dialog; pressing again after this line will attempt to buy
            self._start_dialog([
                "Shopkeeper: Seeds cost 5 coins. Press Space to confirm.",
            ], on_complete=_buy)

    def enter(self, payload: Dict[str, Any] | None = None):
        spawns = self.data.get("spawns", {})
        spawn_name = (payload or {}).get("spawn") or "start"
        self.player = spawn_player_from_json(spawns, spawn_name)

    def update(self, dt: float, input_sys):
        # If dialog active, allow Esc to cancel or Space to advance; skip movement/interactions
        if self._dialog_lines is not None:
            if input_sys.was_pressed("CANCEL"):
                self._cancel_dialog()
            elif input_sys.was_pressed("INTERACT"):
                self._advance_dialog()
            # Still update camera to keep UI stable
            self.camera.follow(self.player["rect"])
            input_sys.end_frame()
            return

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

        # Interaction (doors handled via action; NPCs handled here)
        # Special-case: block entering shop when closed; change prompt instead
        closest_any = get_closest_interactable(self.player, self.interactables)
        if closest_any is not None and str(closest_any.get("tag", "")) == "door.shop":
            try:
                from game.util.time_of_day import TimeOfDay
                if not TimeOfDay.is_shop_open():
                    # Show closed message and do not allow entering
                    self.prompt_text = "Shop is closed (Open 8:00 AM–8:00 PM)"
                else:
                    self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)
            except Exception:
                # If time system unavailable, fallback to default behavior
                self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)
        else:
            self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # If Space pressed near an NPC, start NPC logic
        if input_sys.was_pressed("INTERACT"):
            # Find closest interactable (same approach as in interaction system)
            pr = self.player["rect"]
            closest = None
            best_d2 = (48 + 1) ** 2
            for item in self.interactables:
                tag = str(item.get("tag", ""))
                if not tag.startswith("npc.") and not tag.startswith("shop"):
                    continue
                ir = item["rect"]
                dx = ir.centerx - pr.centerx
                dy = ir.centery - pr.centery
                d2 = dx * dx + dy * dy
                if d2 < best_d2:
                    best_d2 = d2
                    closest = item
            if closest is not None:
                self._handle_npc_interaction(closest)

        # Camera follow
        self.camera.follow(self.player["rect"])

        input_sys.end_frame()

    def draw(self, surface: pygame.Surface):
        draw_world(surface, self.camera, Config.COLORS["ground_town"], self.roads, self.buildings, [], self.player)

        # Draw visual doors for clarity
        door_color = Config.COLORS.get("door", (200, 80, 40))
        for it in self.interactables:
            if str(it.get("tag", "")).startswith("door."):
                pygame.draw.rect(surface, door_color, self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)

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

        # Draw NPC markers so they are visible
        for it in self.interactables:
            tag = str(it.get("tag", ""))
            if tag.startswith("npc."):
                pygame.draw.rect(surface, (90, 160, 255), self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)

        # draw prompt last
        draw_prompt(surface, self.prompt_text)
        # Day/Night tint and clock HUD
        draw_day_night_tint(surface)
        draw_clock(surface)

        # If dialog active, draw dialog box
        if self._dialog_lines is not None and len(self._dialog_lines) > 0:
            if self._dialog_font is None:
                self._dialog_font = pygame.font.SysFont("arial", 18)
            # Box
            text_line = self._dialog_lines[0]
            # create a semi-transparent bg panel
            panel_w = int(surface.get_width() * 0.8)
            panel_h = 100
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill(Config.COLORS.get("dialog_bg", (0, 0, 0, 180)))
            px = (surface.get_width() - panel_w) // 2
            py = surface.get_height() - panel_h - 40
            surface.blit(panel, (px, py))
            # Render text
            txt = self._dialog_font.render(text_line, True, Config.COLORS.get("dialog_text", (255, 255, 255)))
            surface.blit(txt, (px + 12, py + 12))
            hint = self._dialog_font.render("(Space=Next/Confirm, Esc=Cancel)", True, (220, 220, 220))
            surface.blit(hint, (px + panel_w - hint.get_width() - 12, py + panel_h - hint.get_height() - 8))
