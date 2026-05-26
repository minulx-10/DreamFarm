import pygame
from core.game_state import game_state
from core.assets import TEXT_DARK, TEXT_MUTED, WOOD_LIGHT, get_font
from core.ui import draw_light_panel, draw_story_backdrop, wrap_text


class MemoryScene:
    """Memory/flashback scene with fade-to-monochrome transition effect."""

    def __init__(self):
        self.font_title = get_font(26)
        self.font = get_font(20)
        self.font_small = get_font(18)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.065
        self.finished = False
        self.text_to_print = self.prepare_text(game_state.memory_text)
        # Transition effect
        self.phase = "fade_in"
        self.transition_alpha = 255
        self.exit_flash = 0

    def prepare_text(self, text):
        lines = []
        for paragraph in text.split("\n"):
            if not paragraph:
                lines.append("")
            else:
                lines.extend(wrap_text(paragraph, self.font, 560))
        return "\n".join(lines)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            ):
                if not self.finished:
                    self.printed_text = self.text_to_print
                    self.char_idx = len(self.text_to_print)
                    self.finished = True
                elif self.phase != "fade_out":
                    self.phase = "fade_out"
                    self.exit_flash = 180

    def update(self, dt):
        if self.phase == "fade_in":
            self.transition_alpha = max(0, self.transition_alpha - 280 * dt)
            if self.transition_alpha <= 0:
                self.transition_alpha = 0
                self.phase = "show"
        elif self.phase == "fade_out":
            self.exit_flash = max(0, self.exit_flash - 300 * dt)
            self.transition_alpha = min(255, self.transition_alpha + 200 * dt)
            if self.transition_alpha >= 255:
                game_state.current_scene = game_state.memory_next
            return

        if self.finished:
            return

        self.char_timer += dt
        if self.char_timer >= self.char_delay:
            self.char_timer = 0
            if self.char_idx < len(self.text_to_print):
                self.printed_text += self.text_to_print[self.char_idx]
                self.char_idx += 1
            else:
                self.finished = True

    def draw(self, screen):
        draw_story_backdrop(screen, "night")

        panel = pygame.Rect(70, 85, 660, 430)
        draw_light_panel(screen, panel)

        title = game_state.memory_title or "짧은 회상"
        title_surf = self.font_title.render(title, True, TEXT_DARK)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 130))

        line = pygame.Rect(120, 170, 560, 3)
        pygame.draw.rect(screen, WOOD_LIGHT, line)

        y = 205
        for text_line in self.printed_text.split("\n"):
            surf = self.font.render(text_line, True, TEXT_DARK)
            screen.blit(surf, (120, y))
            y += 29

        if self.finished:
            prompt = self.font_small.render("계속하려면 클릭하거나 스페이스바를 누르세요", True, TEXT_MUTED)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 470))

        # Fade overlay
        if self.transition_alpha > 0:
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(self.transition_alpha)))
            screen.blit(overlay, (0, 0))

        # Exit flash (brief white flash when leaving memory)
        if self.exit_flash > 0:
            flash = pygame.Surface((800, 600), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(self.exit_flash)))
            screen.blit(flash, (0, 0))
