import pygame
from typing import List, Tuple, Callable, Optional

from game.config import Config


class DialogueUI:
    """
    Tiny reusable dialogue/choice helper for scenes.
    Usage from a Scene:
      self.dialog = DialogueUI(self.events)
      self.dialog.start_dialog([...], on_complete=cb, on_confirm_alt=alt)
      self.dialog.start_choice("Prompt", [("Yes", cb1), ("No", cb2)])
      if self.dialog.update(input_sys, self.camera, self.player["rect"]):
          return  # consumed this frame
      ... later in draw(): self.dialog.draw(surface)
    """
    def __init__(self, events):
        self._events = events
        # dialog state
        self._dialog_lines: Optional[List[str]] = None
        self._on_complete: Optional[Callable[[], None]] = None
        self._on_alt: Optional[Callable[[], None]] = None
        # choice state
        self._choice: Optional[dict] = None  # {prompt:str, options: List[(label, cb)]}
        # font cache
        self._font: Optional[pygame.font.Font] = None

    # API
    def start_dialog(self, lines: List[str], on_complete: Callable[[], None] | None = None,
                     on_confirm_alt: Callable[[], None] | None = None):
        try:
            self._dialog_lines = list(lines or [])
        except Exception:
            self._dialog_lines = []
        self._on_complete = on_complete
        self._on_alt = on_confirm_alt
        # closing any active choice when starting a dialog
        self._choice = None

    def cancel_dialog(self):
        self._dialog_lines = None
        self._on_complete = None
        self._on_alt = None

    def start_choice(self, prompt: str, options: List[Tuple[str, Optional[Callable[[], None]]]]):
        # take only first two options; rest ignored for MVP
        opts = []
        try:
            opts = list(options or [])
        except Exception:
            pass
        self._choice = {"prompt": str(prompt or ""), "options": opts[:2]}
        # close any ongoing dialog
        self._dialog_lines = None
        self._on_complete = None
        self._on_alt = None

    # Update returns True if it handled the frame (scene should early-return)
    def update(self, input_sys, camera, follow_rect: pygame.Rect) -> bool:
        # Choice mode has precedence
        if self._choice is not None:
            if input_sys.was_pressed("CANCEL"):
                self._choice = None
            elif input_sys.was_pressed("INTERACT"):
                try:
                    _label, cb = self._choice.get("options", [])[0]
                except Exception:
                    cb = None
                self._choice = None
                if cb:
                    cb()
            elif input_sys.was_pressed("CONFIRM_ALT"):
                opts = self._choice.get("options", [])
                if len(opts) > 1:
                    _label, cb = opts[1]
                    self._choice = None
                    if cb:
                        cb()
            camera.follow(follow_rect)
            input_sys.end_frame()
            return True
        # Dialog mode
        if self._dialog_lines is not None:
            if input_sys.was_pressed("CANCEL"):
                self.cancel_dialog()
            elif input_sys.was_pressed("CONFIRM_ALT") and self._on_alt:
                cb = self._on_alt
                # clear first to prevent reentry
                self._dialog_lines = None
                self._on_complete = None
                self._on_alt = None
                cb()
            elif input_sys.was_pressed("INTERACT"):
                # advance one line; if finished, run completion
                if self._dialog_lines:
                    self._dialog_lines.pop(0)
                if not self._dialog_lines:
                    cb = self._on_complete
                    self._dialog_lines = None
                    self._on_complete = None
                    self._on_alt = None
                    if cb:
                        cb()
            camera.follow(follow_rect)
            input_sys.end_frame()
            return True
        return False

    def draw(self, surface: pygame.Surface):
        # draw dialog (single-line) panel
        if self._font is None:
            self._font = pygame.font.SysFont("arial", 18)
        if self._dialog_lines:
            panel_w = int(surface.get_width() * 0.8)
            panel_h = 100
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill(Config.COLORS.get("dialog_bg", (0, 0, 0, 180)))
            px = (surface.get_width() - panel_w) // 2
            py = surface.get_height() - panel_h - 40
            surface.blit(panel, (px, py))
            text_line = str(self._dialog_lines[0])
            txt = self._font.render(text_line, True, Config.COLORS.get("dialog_text", (255, 255, 255)))
            surface.blit(txt, (px + 12, py + 12))
            hint = self._font.render("(Space=Next/Confirm, Esc=Cancel)", True, (220, 220, 220))
            surface.blit(hint, (px + panel_w - hint.get_width() - 12, py + panel_h - hint.get_height() - 8))
        # draw choice panel
        if self._choice is not None:
            panel_w = int(surface.get_width() * 0.8)
            panel_h = 120
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel.fill(Config.COLORS.get("dialog_bg", (0, 0, 0, 180)))
            px = (surface.get_width() - panel_w) // 2
            py = surface.get_height() - panel_h - 40
            surface.blit(panel, (px, py))
            prompt = str(self._choice.get("prompt", ""))
            txt = self._font.render(prompt, True, Config.COLORS.get("dialog_text", (255, 255, 255)))
            surface.blit(txt, (px + 12, py + 12))
            opts = self._choice.get("options", [])
            if len(opts) == 0:
                opt_text = "(Esc: Cancel)"
            elif len(opts) == 1:
                opt_text = f"(Space: {opts[0][0]}  |  Esc: Cancel)"
            else:
                opt_text = f"(Space: {opts[0][0]}  |  A: {opts[1][0]}  |  Esc: Cancel)"
            hint = self._font.render(opt_text, True, (220, 220, 220))
            surface.blit(hint, (px + panel_w - hint.get_width() - 12, py + panel_h - hint.get_height() - 8))
