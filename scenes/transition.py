import pygame
from core.game_state import game_state
from core.assets import get_font, draw_tiled_background, TEXT_BROWN
from core.ui import draw_wood_panel

class TransitionScene:
    def __init__(self):
        self.font = get_font(24)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                game_state.current_scene = game_state.transition_next
            elif event.type == pygame.MOUSEBUTTONDOWN:
                game_state.current_scene = game_state.transition_next

    def update(self, dt): pass

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        
        panel = pygame.Rect(100, 100, 600, 400)
        draw_wood_panel(screen, panel)
        
        y_offset = 140
        for paragraph in game_state.transition_text.split('\n'):
            if not paragraph:
                y_offset += 18
                continue
            lines = []
            current = ""
            for char in paragraph:
                test = current + char
                if self.font.size(test)[0] <= 520:
                    current = test
                else:
                    lines.append(current)
                    current = char
            if current:
                lines.append(current)
            for line in lines:
                rendered = self.font.render(line, True, TEXT_BROWN)
                screen.blit(rendered, (400 - rendered.get_width()//2, y_offset))
                y_offset += 32
            
        if game_state.is_clear_transition:
            score_text = self.font.render(f"현재 누적 이해도: {game_state.understanding}", True, (200, 100, 0))
            screen.blit(score_text, (400 - score_text.get_width()//2, y_offset + 30))
            
        prompt = self.font.render("계속하려면 클릭하거나 스페이스바를 누르세요", True, (120, 100, 80))
        screen.blit(prompt, (400 - prompt.get_width()//2, 440))
