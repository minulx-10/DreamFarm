import math
import pygame
from core.game_state import game_state
from core.assets import BLACK, get_font

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

    def handle_events(self, events):
        for event in events:
            if self.phase == "hold" and self.hold_timer > 1.5:
                if event.type == pygame.MOUSEBUTTONDOWN or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
                ):
                    self.phase = "fade_out"

    def update(self, dt):
        self.glow_timer += dt

        if self.phase == "fade_in":
            self.alpha = min(255, self.alpha + 120 * dt)
            if self.alpha >= 255:
                self.alpha = 255
                self.phase = "hold"
        elif self.phase == "hold":
            self.hold_timer += dt
        elif self.phase == "fade_out":
            self.alpha = max(0, self.alpha - 200 * dt)
            if self.alpha <= 0:
                game_state.pending_epiphany = None
                game_state.current_scene = "farm"

    def draw(self, screen):
        screen.fill(BLACK)

        if self.alpha <= 0:
            return

        ratio = self.alpha / 255.0

        # Warm golden glow in center
        glow_pulse = 0.85 + 0.15 * math.sin(self.glow_timer * 1.5)
        glow_radius = int(200 * glow_pulse)
        glow_surf = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        for r in range(glow_radius, 0, -3):
            a = int((r / glow_radius) * 30 * ratio)
            pygame.draw.circle(glow_surf, (255, 200, 80, a), (glow_radius, glow_radius), r)
        screen.blit(glow_surf, (400 - glow_radius, 300 - glow_radius))

        # Main text with alpha
        color = (
            int(255 * ratio),
            int(220 * ratio),
            int(130 * ratio),
        )
        text_surf = self.font.render(self.text, True, color)
        screen.blit(text_surf, (400 - text_surf.get_width() // 2, 290))

        # Prompt after delay
        if self.phase == "hold" and self.hold_timer > 1.5:
            blink = int(abs(math.sin(self.hold_timer * 2)) * 150 * ratio)
            prompt_color = (blink, blink - 10, blink - 30)
            prompt_color = tuple(max(0, c) for c in prompt_color)
            prompt = self.font_small.render("클릭하거나 스페이스바를 누르세요", True, prompt_color)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 400))
