import math
import pygame
from core.game_state import game_state, FATHER_DAY_NARRATIONS
from core.assets import BLACK, WHITE, get_font
from core.ui import wrap_text, draw_centered_lines, draw_story_backdrop


class FatherDayScene:
    """#1 + #10: Non-interactive narration of father's daily life,
    then transitions to farm in dad_mode for playable father chapter."""

    def __init__(self):
        self.font = get_font(22)
        self.font_small = get_font(16)
        self.font_title = get_font(28)
        self.glow_timer = 0

        # Find which narration to show
        self.threshold = self._find_threshold()
        pages_raw = FATHER_DAY_NARRATIONS.get(self.threshold, ["..."])
        self.pages = pages_raw
        self.page_index = 0
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.075  # Slightly slower for weight
        self.finished = False
        self.text_to_print = self._prepare(self.pages[0])

        # Phases: fade_in → narration → fade_to_farm
        self.phase = "fade_in"
        self.fade_alpha = 255
        self.transition_timer = 0

    def _find_threshold(self):
        for t in sorted(FATHER_DAY_NARRATIONS.keys()):
            if t in game_state.father_day_seen:
                return t
        return list(FATHER_DAY_NARRATIONS.keys())[0]

    def _prepare(self, text):
        lines = []
        for p in text.split("\n"):
            if not p:
                lines.append("")
            else:
                lines.extend(wrap_text(p, self.font, 580))
        return "\n".join(lines)

    def handle_events(self, events):
        for event in events:
            click = (event.type == pygame.MOUSEBUTTONDOWN or
                     (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE))
            if not click:
                continue

            if self.phase == "narration":
                if not self.finished:
                    self.printed_text = self.text_to_print
                    self.char_idx = len(self.text_to_print)
                    self.finished = True
                elif self.page_index < len(self.pages) - 1:
                    self.page_index += 1
                    self.printed_text = ""
                    self.char_idx = 0
                    self.finished = False
                    self.text_to_print = self._prepare(self.pages[self.page_index])
                else:
                    self.phase = "fade_to_farm"
                    self.transition_timer = 0

    def update(self, dt):
        self.glow_timer += dt

        if self.phase == "fade_in":
            self.fade_alpha = max(0, self.fade_alpha - 150 * dt)
            if self.fade_alpha <= 0:
                self.phase = "narration"

        elif self.phase == "narration":
            if not self.finished:
                self.char_timer += dt
                if self.char_timer >= self.char_delay:
                    self.char_timer = 0
                    if self.char_idx < len(self.text_to_print):
                        self.printed_text += self.text_to_print[self.char_idx]
                        self.char_idx += 1
                    else:
                        self.finished = True

        elif self.phase == "fade_to_farm":
            self.transition_timer += dt
            self.fade_alpha = min(255, self.transition_timer * 200)
            if self.fade_alpha >= 255:
                # #10: Activate dad mode in farm
                game_state.dad_mode = True
                game_state.dad_mode_turns = 4
                game_state.transition_text = (
                    "[아버지의 밭]\n"
                    "아버지의 손으로, 같은 밭을 돌본다.\n"
                    "매일 새벽, 혼자서."
                )
                game_state.transition_next = "farm"
                game_state.is_clear_transition = False
                game_state.current_scene = "transition"

    def draw(self, screen):
        draw_story_backdrop(screen, "night")

        # Warm amber glow in center
        pulse = 0.8 + 0.2 * math.sin(self.glow_timer * 1.2)
        glow_r = int(160 * pulse)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        for r in range(glow_r, 0, -4):
            a = int((r / glow_r) * 18)
            pygame.draw.circle(glow_surf, (200, 150, 60, a), (glow_r, glow_r), r)
        screen.blit(glow_surf, (400 - glow_r, 300 - glow_r))

        if self.phase in ("narration", "fade_to_farm"):
            # Title
            title = self.font_title.render("아버지의 하루", True, (180, 150, 90))
            screen.blit(title, (400 - title.get_width() // 2, 60))

            # Divider
            pygame.draw.line(screen, (100, 80, 50), (200, 105), (600, 105), 2)

            # Narration text
            lines = self.printed_text.split("\n")
            draw_centered_lines(screen, lines, self.font, (200, 180, 130), 400, 140, line_gap=8)

            # Page indicator
            if len(self.pages) > 1:
                pg = self.font_small.render(
                    f"{self.page_index + 1}/{len(self.pages)}", True, (80, 70, 50))
                screen.blit(pg, (700, 540))

            # Prompt
            if self.finished:
                pt = "다음으로" if self.page_index < len(self.pages) - 1 else "아버지의 밭으로"
                prompt = self.font_small.render(pt, True, (120, 100, 70))
                screen.blit(prompt, (400 - prompt.get_width() // 2, 520))

        # Fade overlay
        if self.fade_alpha > 0:
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(min(255, self.fade_alpha))))
            screen.blit(overlay, (0, 0))
