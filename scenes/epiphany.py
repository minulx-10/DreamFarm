import math
import pygame
from core.game_state import game_state
from core.assets import BLACK, get_font
from core.pixelfx import pixelate, glow_sprite, blit_glow
from core.ui import wrap_text
from core import audio

class EpiphanyScene:
    """Fullscreen epiphany moment — dramatic text reveal when understanding crosses a threshold."""

    def __init__(self):
        self.font = get_font(28)
        self.font_small = get_font(16)
        self.text = game_state.pending_epiphany or ""
        self.alpha = 0
        self.phase = "fade_in"
        self.hold_timer = 0
        self.glow_timer = 0
        audio.play("epiphany")

    def handle_events(self, events):
        for event in events:
            if self.phase == "hold" and self.hold_timer > 1.5:
                if event.type == pygame.MOUSEBUTTONDOWN or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
                ):
                    self.phase = "fade_out"

    def update(self, dt):
        fast_ff = getattr(game_state, "fast_forward", False)
        effective_dt = dt * 6.0 if fast_ff else dt
        self.glow_timer += effective_dt

        if self.phase == "fade_in":
            self.alpha = min(255, self.alpha + 120 * effective_dt)
            if self.alpha >= 255:
                self.alpha = 255
                self.phase = "hold"
        elif self.phase == "hold":
            self.hold_timer += effective_dt
            # 배속 상태에서 꾹 누르고 있으면 대기시간을 바로 스킵하고 페이드아웃 페이즈로 전환
            if fast_ff and self.hold_timer > 0.4:
                self.phase = "fade_out"
        elif self.phase == "fade_out":
            self.alpha = max(0, self.alpha - 200 * effective_dt)
            if self.alpha <= 0:
                game_state.pending_epiphany = None
                game_state.current_scene = "farm"

    def draw(self, screen):
        screen.fill(BLACK)

        if self.alpha <= 0:
            return

        ratio = self.alpha / 255.0

        # Warm golden glow in center — '계단 알파' 도트 글로우(캐시).
        # 예전 코드는 알파식이 뒤집혀(작은 원일수록 옅게 덮어씀) 중앙이 비고 가장자리만
        # 밝은 링이었다 → 의도대로 중앙이 가장 밝은 글로우로 복원. 반경은 8px 양자화(캐시 상한).
        glow_pulse = 0.85 + 0.15 * math.sin(self.glow_timer * 1.5)
        glow_radius = (int(200 * glow_pulse) // 8) * 8
        blit_glow(screen, glow_sprite(glow_radius, (255, 200, 80), px=5, steps=(9, 18, 30)),
                  (400, 300), int(255 * ratio))

        # Main text with alpha — 긴 영어 문구는 한 줄 렌더로 화면(800px)을 넘어 잘린다 →
        # 폭에 맞춰 줄바꿈(wrap_text가 번역 후 감쌈)하고 세로 중앙 정렬
        color = (
            int(255 * ratio),
            int(220 * ratio),
            int(130 * ratio),
        )
        lines = wrap_text(self.text, self.font, 700) or [""]
        line_h = self.font.get_height() + 6
        y = 300 - (len(lines) * line_h) // 2
        for line in lines:
            text_surf = self.font.render(line, True, color)
            screen.blit(text_surf, (400 - text_surf.get_width() // 2, y))
            y += line_h

        # Prompt after delay
        if self.phase == "hold" and self.hold_timer > 1.5:
            blink = int(abs(math.sin(self.hold_timer * 2)) * 150 * ratio)
            prompt_color = (blink, blink - 10, blink - 30)
            prompt_color = tuple(max(0, c) for c in prompt_color)
            prompt = self.font_small.render("클릭하거나 스페이스바를 누르세요", True, prompt_color)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 400))
