import math
import pygame
from core.game_state import game_state, FATHER_DAY_NARRATIONS
from core.assets import BLACK, WHITE, get_font
from core.pixelfx import pixelate, glow_sprite, blit_glow
from core.ui import wrap_text, draw_centered_lines, draw_story_backdrop
from core import audio
from core import i18n
from core.ui_utils import Typewriter


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
        self.typewriter = Typewriter(0.075)  # Slightly slower for weight
        self.text_to_print = self._prepare(self.pages[0])
        self.typewriter.set_text(self.text_to_print)

        # Phases: fade_in → narration → fade_to_farm
        self.phase = "fade_in"
        self.fade_alpha = 255
        self.transition_timer = 0

    def _find_threshold(self):
        # 방금 넘긴(=가장 높은) 임계값의 서사를 보여준다. 오름차순으로 '처음 만난 seen'을
        # 돌려주면 두 번째 아버지의 날부터 영영 첫(40) 서사만 반복된다.
        for t in sorted(FATHER_DAY_NARRATIONS.keys(), reverse=True):
            if t in game_state.father_day_seen:
                return t
        return list(FATHER_DAY_NARRATIONS.keys())[0]

    def _prepare(self, text):
        # 통짜 블록을 '먼저' 번역한다 — 카탈로그 키가 블록 전체라, \n 으로 조각내 렌더하면
        # 각 줄이 카탈로그와 안 맞아 번역이 안 된다(HANDOFF 팁 #5). 한국어에선 i18n.t 가 원문
        # 그대로라 동작 무변화.
        text = i18n.t(text)
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
                if not self.typewriter.finished:
                    self.typewriter.skip()
                elif self.page_index < len(self.pages) - 1:
                    self.page_index += 1
                    self.text_to_print = self._prepare(self.pages[self.page_index])
                    self.typewriter.set_text(self.text_to_print)
                else:
                    self.phase = "fade_to_farm"
                    self.transition_timer = 0

    def update(self, dt):
        fast_ff = getattr(game_state, "fast_forward", False)
        effective_dt = dt * 6.0 if fast_ff else dt
        self.glow_timer += effective_dt

        if self.phase == "fade_in":
            self.fade_alpha = max(0, self.fade_alpha - 150 * effective_dt)
            if self.fade_alpha <= 0:
                self.phase = "narration"

        elif self.phase == "narration":
            self.typewriter.update(dt, fast_ff)

        elif self.phase == "fade_to_farm":
            self.transition_timer += effective_dt
            self.fade_alpha = min(255, self.transition_timer * 200)
            if self.fade_alpha >= 255:
                # #10: Activate dad mode in farm
                game_state.dad_mode = True
                game_state.dad_mode_turns = 2
                game_state.transition_text = (
                    "[아버지의 밭]\n"
                    "아버지의 손으로, 같은 밭을 돌본다.\n"
                    "매일 새벽, 혼자서."
                )
                game_state.transition_next = "farm"
                game_state.is_clear_transition = False
                game_state.current_scene = "transition"

    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")

        # Warm amber glow in center — '계단 알파' 도트 글로우(캐시).
        # 예전 코드는 알파식이 뒤집혀 중앙이 비는 링이었다 → 중앙이 밝은 글로우로 복원.
        pulse = 0.8 + 0.2 * math.sin(self.glow_timer * 1.2)
        glow_r = (int(160 * pulse) // 8) * 8
        blit_glow(screen, glow_sprite(glow_r, (200, 150, 60), px=5, steps=(6, 12, 19)), (400, 300))

        if self.phase in ("narration", "fade_to_farm"):
            # Title
            title = self.font_title.render("아버지의 하루", True, (180, 150, 90))
            screen.blit(title, (400 - title.get_width() // 2, 60))

            # Divider
            pygame.draw.line(screen, (100, 80, 50), (200, 105), (600, 105), 2)

            # Narration text
            lines = self.typewriter.printed_text.split("\n")
            draw_centered_lines(screen, lines, self.font, (200, 180, 130), 400, 140, line_gap=8)

            # Page indicator
            if len(self.pages) > 1:
                pg = self.font_small.render(
                    f"{self.page_index + 1}/{len(self.pages)}", True, (80, 70, 50))
                screen.blit(pg, (700, 540))

            # Prompt
            if self.typewriter.finished:
                label = "다음으로" if self.page_index < len(self.pages) - 1 else "아버지의 밭으로"
                prompt = self.font_small.render(i18n.tf("{label} ▸ 클릭하거나 스페이스바", label=i18n.t(label)), True, (172, 148, 106))
                screen.blit(prompt, (400 - prompt.get_width() // 2, 520))

        # Fade overlay
        if self.fade_alpha > 0:
            from core.ui import draw_full_veil
            draw_full_veil(screen, (0, 0, 0, int(min(255, self.fade_alpha))))
