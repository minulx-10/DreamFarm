import pygame
from core.game_state import game_state
from core.assets import get_font, BLACK, WHITE, YELLOW

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
                self.ime_text = event.text
            elif event.type == pygame.TEXTINPUT:
                if len(self.input_text) + len(event.text) <= 10:
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
        screen.fill(BLACK)
        
        prompt = self.font_large.render("꿈속 밭에 남길 이름은?", True, WHITE)
        screen.blit(prompt, (400 - prompt.get_width()//2, 200))
        
        input_rect = pygame.Rect(250, 280, 300, 50)
        pygame.draw.rect(screen, WHITE, input_rect, 2)
        
        # Cursor blink
        display_text = self.input_text + self.ime_text
        if pygame.time.get_ticks() % 1000 < 500:
            display_text += "_"
            
        name_surf = self.font_large.render(display_text, True, YELLOW)
        screen.blit(name_surf, (input_rect.x + 10, input_rect.y + 5))
        
        desc = self.font_small.render("이름을 입력하고 Enter를 누르세요", True, (150, 150, 150))
        screen.blit(desc, (400 - desc.get_width()//2, 400))
