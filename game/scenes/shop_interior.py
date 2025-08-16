import pygame
from typing import Dict, Any

from game.config import Config
from game.core.scene import BaseScene
from game.scripts_common import spawn_player_from_json
from game.systems.movement import move_player
from game.systems.interaction import handle_interaction
from game.systems.render import draw_world, draw_prompt, draw_day_night_tint, draw_clock
from game.util.serialization import load_json


class ShopInteriorScene(BaseScene):
    def __init__(self, manager):
        super().__init__(manager)
        self.data = None
        self.furniture = []
        # tiny dialog state for shopkeeper
        self._dialog_lines = None
        self._on_dialog_complete = None
        self._on_dialog_alt = None
        self._dialog_font = None

    def load(self):
        self.data = load_json(f"{Config.SCENES_DIR}/shop_interior.json")
        b = self.data["bounds"]
        self.bounds = pygame.Rect(*b)
        self.camera.set_bounds(self.bounds)
        self.world_colliders = [pygame.Rect(*c["rect"]) for c in self.data.get("colliders", [])]
        self.furniture = [pygame.Rect(*c["rect"]) for c in self.data.get("colliders", [])]
        self.interactables = [{**i, "rect": pygame.Rect(*i["rect"])} for i in self.data.get("interactables", [])]
        self.triggers = [{**t, "rect": pygame.Rect(*t["rect"])} for t in self.data.get("triggers", [])]

    def enter(self, payload: Dict[str, Any] | None = None):
        spawns = self.data.get("spawns", {})
        spawn_name = (payload or {}).get("spawn") or "door_in"
        self.player = spawn_player_from_json(spawns, spawn_name)

    def _start_dialog(self, lines, on_complete=None, on_confirm_alt=None):
        self._dialog_lines = list(lines)
        self._on_dialog_complete = on_complete
        self._on_dialog_alt = on_confirm_alt

    def _advance_dialog(self):
        if not self._dialog_lines:
            return
        self._dialog_lines.pop(0)
        if not self._dialog_lines:
            cb = self._on_dialog_complete
            self._dialog_lines = None
            self._on_dialog_complete = None
            self._on_dialog_alt = None
            if cb:
                cb()

    def _cancel_dialog(self):
        # Cancel without invoking completion callback
        self._dialog_lines = None
        self._on_dialog_complete = None
        self._on_dialog_alt = None

    def _handle_shopkeeper(self):
        from game.util.state import GameState
        from game.util.time_of_day import TimeOfDay
        if not TimeOfDay.is_shop_open():
            self._start_dialog(["Shopkeeper: Sorry, we're closed. Please come back during the day."], on_complete=None)
            return
        # If player has carrots, offer a repeated sell loop: Space sells one, A sells all, Esc cancels
        if GameState.has_item("carrot", 1):
            def _sell_once():
                if GameState.remove_item("carrot", 1):
                    GameState.coins += 3
                    # Notifications
                    try:
                        self.events.publish("ui.notify", {"text": "-1 Carrot"})
                        self.events.publish("ui.notify", {"text": "+3 Coins"})
                    except Exception:
                        pass
                    # Continue offering if more remain
                    if GameState.has_item("carrot", 1):
                        self._start_dialog(["Sell crops: +3 coins each. Space: one  |  A: all  |  Esc: cancel"], on_complete=_sell_once, on_confirm_alt=_sell_all)
                    else:
                        self._start_dialog(["Shopkeeper: You have no crops."])
                else:
                    self._start_dialog(["Shopkeeper: You have no crops."])
            def _sell_all():
                have = int(GameState.inventory.get("carrot", 0))
                if have > 0:
                    coins = have * 3
                    # remove all carrots
                    GameState.remove_item("carrot", have)
                    GameState.coins += coins
                    try:
                        self.events.publish("ui.notify", {"text": f"-{have} Carrot(s)"})
                        self.events.publish("ui.notify", {"text": f"+{coins} Coins"})
                    except Exception:
                        pass
                    self._start_dialog(["Shopkeeper: Thanks for the crops!"], on_complete=None)
                else:
                    self._start_dialog(["Shopkeeper: You have no crops."], on_complete=None)
            self._start_dialog(["Sell crops: +3 coins each. Space: one  |  A: all  |  Esc: cancel"], on_complete=_sell_once, on_confirm_alt=_sell_all)
            return
        # Otherwise offer Seeds for 5 coins
        def _buy():
            if GameState.coins >= 5:
                GameState.coins -= 5
                GameState.add_item("seeds", 1)
                # Notifications
                try:
                    self.events.publish("ui.notify", {"text": "-5 Coins"})
                    self.events.publish("ui.notify", {"text": "+1 Seeds"})
                except Exception:
                    pass
                self._start_dialog(["Shopkeeper: Here you go, one bag of seeds!"], on_complete=None)
            else:
                self._start_dialog(["Shopkeeper: Sorry, you don't have enough coins."], on_complete=None)
        self._start_dialog(["Shopkeeper: Seeds cost 5 coins. Press Space to confirm."], on_complete=_buy)

    def update(self, dt: float, input_sys):
        # Dialog mode
        if self._dialog_lines is not None:
            if input_sys.was_pressed("CANCEL"):
                self._cancel_dialog()
            elif input_sys.was_pressed("CONFIRM_ALT") and self._on_dialog_alt:
                # Invoke alternate confirm without advancing line by line
                cb = self._on_dialog_alt
                # clear dialog first to prevent reentry
                self._dialog_lines = None
                self._on_dialog_complete = None
                self._on_dialog_alt = None
                cb()
            elif input_sys.was_pressed("INTERACT"):
                self._advance_dialog()
            self.camera.follow(self.player["rect"])  # keep camera stable
            input_sys.end_frame()
            return

        move_player(self.player, input_sys, dt, self.world_colliders)

        # Basic interactables (door back)
        self.prompt_text = handle_interaction(self.player, self.interactables, input_sys, self.events)

        # Shopkeeper proximity check
        if input_sys.was_pressed("INTERACT"):
            pr = self.player["rect"]
            closest = None
            best_d2 = (48 + 1) ** 2
            for item in self.interactables:
                if str(item.get("tag", "")) != "npc.shopkeeper":
                    continue
                ir = item["rect"]
                dx = ir.centerx - pr.centerx
                dy = ir.centery - pr.centery
                d2 = dx * dx + dy * dy
                if d2 < best_d2:
                    best_d2 = d2
                    closest = item
            if closest is not None:
                self._handle_shopkeeper()

        self.camera.follow(self.player["rect"]) 
        input_sys.end_frame()

    def draw(self, surface: pygame.Surface):
        draw_world(surface, self.camera, Config.COLORS["ground_home"], [], self.furniture, [], self.player)
        # Draw door visual
        door_color = Config.COLORS.get("door", (200, 80, 40))
        for it in self.interactables:
            if it.get("tag") == "door.exit":
                pygame.draw.rect(surface, door_color, self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)
        # Draw shopkeeper marker
        for it in self.interactables:
            if it.get("tag") == "npc.shopkeeper":
                pygame.draw.rect(surface, (90, 160, 255), self.camera.apply(it["rect"]))
                pygame.draw.rect(surface, (0, 0, 0), self.camera.apply(it["rect"]), 1)
        draw_prompt(surface, self.prompt_text)
        draw_day_night_tint(surface)
        draw_clock(surface)

        # Dialog panel if active
        if self._dialog_lines:
            if self._dialog_font is None:
                self._dialog_font = pygame.font.SysFont("arial", 18)
            panel_w = int(surface.get_width() * 0.8)
            panel_h = 100
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill(Config.COLORS.get("dialog_bg", (0, 0, 0, 180)))
            px = (surface.get_width() - panel_w) // 2
            py = surface.get_height() - panel_h - 40
            surface.blit(panel, (px, py))
            text_line = self._dialog_lines[0]
            txt = self._dialog_font.render(text_line, True, Config.COLORS.get("dialog_text", (255, 255, 255)))
            surface.blit(txt, (px + 12, py + 12))
            hint = self._dialog_font.render("(Space=Confirm, Esc=Cancel)", True, (220, 220, 220))
            surface.blit(hint, (px + panel_w - hint.get_width() - 12, py + panel_h - hint.get_height() - 8))
