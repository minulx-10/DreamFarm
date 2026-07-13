import pygame
from core.game_state import game_state
from core.assets import TEXT_DARK, TEXT_MUTED, draw_tiled_background, get_font
from core.ui import draw_light_panel, draw_wood_panel
from core import audio
from core import i18n

class TransitionScene:
    def __init__(self):
        self.font = get_font(24)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                audio.play("click")
                game_state.current_scene = game_state.transition_next
            elif event.type == pygame.MOUSEBUTTONDOWN:
                audio.play("click")
                game_state.current_scene = game_state.transition_next

    def update(self, dt): pass

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        
        panel = pygame.Rect(100, 100, 600, 400)
        draw_light_panel(screen, panel)
        
        y_offset = 140
        # 전체 문구를 먼저 번역한 뒤 줄바꿈(통째로 번역해야 카탈로그 키와 매칭). 줄바꿈은 wrap_text로
        # (영어 단어가 줄 경계에서 잘리지 않도록 — 자체 줄바꿈은 단어 중간을 끊었음).
        from core.ui import wrap_text
        full_text = i18n.t(game_state.transition_text)
        for paragraph in full_text.split('\n'):
            if not paragraph:
                y_offset += 18
                continue
            for line in wrap_text(paragraph, self.font, 520):
                rendered = self.font.render(line, True, TEXT_DARK)
                screen.blit(rendered, (400 - rendered.get_width()//2, y_offset))
                y_offset += 32
            
        if game_state.is_clear_transition:
            score_text = self.font.render(i18n.tf("현재 누적 이해도: {n}", n=game_state.understanding), True, (160, 72, 0))
            screen.blit(score_text, (400 - score_text.get_width()//2, y_offset + 30))
            
        prompt = self.font.render("계속하려면 클릭하거나 스페이스바를 누르세요", True, TEXT_MUTED)
        screen.blit(prompt, (400 - prompt.get_width()//2, 440))
