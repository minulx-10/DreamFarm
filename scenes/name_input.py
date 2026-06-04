import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, GOLD, WHITE
from core.ui import draw_light_panel, draw_story_backdrop

class NameInputScene:
    def __init__(self):
        self.font_large = get_font(36)
        self.font_small = get_font(24)
        self.input_text = ""
        self.ime_text = ""
        pygame.key.start_text_input()
        pygame.key.set_text_input_rect(pygame.Rect(250, 280, 300, 50))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.TEXTEDITING:
                if len(self.input_text) + len(event.text) <= 8:
                    self.ime_text = event.text
                else:
                    self.ime_text = event.text[:max(0, 8 - len(self.input_text))]
            elif event.type == pygame.TEXTINPUT:
                if len(self.input_text) + len(event.text) <= 8:
                    self.input_text += event.text
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if len(self.input_text.strip()) > 0 and len(self.ime_text) == 0:
                        game_state.player_name = self.input_text.strip()
                        game_state.current_scene = "intro"
                        pygame.key.stop_text_input()
                elif event.key == pygame.K_BACKSPACE:
                    if len(self.ime_text) == 0:
                        self.input_text = self.input_text[:-1]

    def update(self, dt):
        pass

    def draw(self, screen):
        draw_story_backdrop(screen, "night")

        card = pygame.Rect(160, 150, 480, 300)
        draw_light_panel(screen, card)

        prompt = self.font_large.render("꿈속 밭에 남길 이름은?", True, TEXT_DARK)
        screen.blit(prompt, (400 - prompt.get_width()//2, 196))

        input_rect = pygame.Rect(230, 275, 340, 58)
        pygame.draw.rect(screen, (255, 249, 230), input_rect, border_radius=8)
        pygame.draw.rect(screen, (109, 84, 60), input_rect, 2, border_radius=8)
        
        display_text = self.input_text + self.ime_text
        if not display_text:
            name_surf = self.font_large.render("이름", True, TEXT_MUTED)
            screen.blit(name_surf, (input_rect.x + 14, input_rect.y + 8))
            cursor_x = input_rect.x + 14
        else:
            name_surf = self.font_large.render(display_text, True, GOLD)
            screen.blit(name_surf, (input_rect.x + 14, input_rect.y + 8))
            cursor_x = input_rect.x + 14 + self.font_large.size(display_text)[0]

        # Draw smooth vertical line cursor instead of appending text characters
        if pygame.time.get_ticks() % 1000 < 500:
            pygame.draw.line(screen, (109, 84, 60), (cursor_x, input_rect.y + 12), (cursor_x, input_rect.bottom - 12), 2)

        desc = self.font_small.render("입력 후 Enter", True, TEXT_MUTED)
        screen.blit(desc, (400 - desc.get_width()//2, 378))

        shine = self.font_small.render("몽중농원", True, WHITE)
        screen.blit(shine, (400 - shine.get_width() // 2, 92))
