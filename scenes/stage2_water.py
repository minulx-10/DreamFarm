import pygame
from core.game_state import game_state
from core.assets import *
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel

class Stage2Scene:
    def __init__(self):
        game_state.timer = 20.0
        game_state.score = 0
        self.attempts = 0
        self.max_attempts = 3
        
        self.gauge_x = 200
        self.gauge_y = 350
        self.gauge_w = 400
        self.gauge_h = 40
        self.target_zone = pygame.Rect(self.gauge_x + 150, self.gauge_y, 100, self.gauge_h)
        
        self.cursor_pos = 0.0
        self.cursor_speed = 500.0
        self.cursor_dir = 1
        
        self.stage_clear = False
        self.clear_timer = 2.0
        
        self.status_msg = "게이지가 초록색 영역에 올 때 스페이스바 또는 클릭하세요!"
        self.stopped = False
        self.stop_timer = 0

    def handle_events(self, events):
        if self.stage_clear or self.stopped: return
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                self.stopped = True
                self.stop_timer = 1.0
                self.attempts += 1
                
                cursor_rect = pygame.Rect(self.gauge_x + self.cursor_pos - 5, self.gauge_y - 10, 10, self.gauge_h + 20)
                if cursor_rect.colliderect(self.target_zone):
                    game_state.score += 200
                    self.status_msg = f"성공! (현재 성공: {self.attempts}/{self.max_attempts})"
                else:
                    self.status_msg = f"실패... 물이 빗나갔습니다. (현재 시도: {self.attempts}/{self.max_attempts})"

    def update(self, dt):
        if self.stage_clear:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                bonus = 0
                if game_state.score >= 500: bonus = 20
                elif game_state.score >= 200: bonus = 10
                elif game_state.score >= 100: bonus = 5
                
                game_state.understanding += bonus
                game_state.transition_text = f"미니게임 완료!\n\n획득 점수: {game_state.score}점\n추가 이해도 보너스: +{bonus}"
                game_state.transition_next = game_state.return_scene
                game_state.is_clear_transition = True
                game_state.current_scene = "transition"
            return

        if self.stopped:
            self.stop_timer -= dt
            if self.stop_timer <= 0:
                self.stopped = False
                self.cursor_pos = 0
                if self.attempts >= self.max_attempts:
                    self.stage_clear = True
            return

        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.stage_clear = True

        self.cursor_pos += self.cursor_speed * self.cursor_dir * dt
        if self.cursor_pos >= self.gauge_w:
            self.cursor_pos = self.gauge_w
            self.cursor_dir = -1
        elif self.cursor_pos <= 0:
            self.cursor_pos = 0
            self.cursor_dir = 1

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        
        # Carrot sprouts
        for i in range(5):
            x = 200 + i * 80
            y = 200
            pygame.draw.rect(screen, DIRT_WET if self.attempts > 0 else DIRT_DARK, (x-30, y-10, 60, 40))
            screen.blit(sprites['sprout1'], (x-15, y-30))
        
        # Gauge background
        panel = pygame.Rect(self.gauge_x - 10, self.gauge_y - 10, self.gauge_w + 20, self.gauge_h + 20)
        draw_wood_panel(screen, panel)
        
        # Gauge bar
        pygame.draw.rect(screen, BLACK, (self.gauge_x, self.gauge_y, self.gauge_w, self.gauge_h))
        pygame.draw.rect(screen, GRASS_COLOR, self.target_zone)
        
        # Cursor (Water drop styled)
        cursor_rect = pygame.Rect(self.gauge_x + self.cursor_pos - 10, self.gauge_y - 15, 20, self.gauge_h + 30)
        pygame.draw.rect(screen, (100, 200, 255), cursor_rect)
        pygame.draw.rect(screen, WHITE, cursor_rect, 2)
        
        draw_top_bar(screen)
        
        if self.stage_clear:
            font = get_font(30)
            clear_text = font.render("물 주기 완료!", True, (200, 100, 0))
            panel_clear = pygame.Rect(400 - 150, 250 - 30, 300, 60)
            draw_wood_panel(screen, panel_clear)
            screen.blit(clear_text, (400 - clear_text.get_width()//2, 250 - clear_text.get_height()//2))
            draw_bottom_bar(screen, "결과", f"얻은 점수: {game_state.score}")
        else:
            draw_bottom_bar(screen, "물 주기", self.status_msg)
