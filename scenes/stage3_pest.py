import pygame
import random
from core.game_state import game_state
from core.assets import *
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel

class Bug:
    def __init__(self):
        self.x = random.randint(100, 700)
        self.y = random.randint(150, 450)
        self.sprite = sprites['bug']
        self.size = self.sprite.get_width()
        self.rect = pygame.Rect(self.x, self.y, self.size, self.size)
        self.dx = random.choice([-3, -2, 2, 3])
        self.dy = random.choice([-3, -2, 2, 3])
        self.alive = True

    def update(self):
        self.x += self.dx
        self.y += self.dy
        if self.x < 50 or self.x > 750: self.dx *= -1
        if self.y < 100 or self.y > 500: self.dy *= -1
        self.rect.topleft = (self.x, self.y)

    def draw(self, screen):
        if self.alive:
            screen.blit(self.sprite, self.rect)

class Stage3Scene:
    def __init__(self):
        game_state.timer = 15.0
        game_state.score = 0
        self.bugs = [Bug() for _ in range(12)]
        self.stage_clear = False
        self.clear_timer = 2.0

    def handle_events(self, events):
        if self.stage_clear: return
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for bug in self.bugs:
                    if bug.alive and bug.rect.collidepoint(event.pos):
                        bug.alive = False
                        game_state.score += 50
                        break

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

        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.stage_clear = True
            
        alive_count = sum(1 for b in self.bugs if b.alive)
        if alive_count == 0:
            self.stage_clear = True

        for bug in self.bugs:
            if bug.alive: bug.update()

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        
        for i in range(6):
            x = 150 + i * 100
            pygame.draw.rect(screen, DIRT_WET, (x-20, 260, 60, 40))
            screen.blit(sprites['carrot'], (x-5, 200))

        for bug in self.bugs: bug.draw(screen)

        draw_top_bar(screen)

        if self.stage_clear:
            font = get_font(30)
            clear_text = font.render("해충 퇴치 완료!", True, (200, 100, 0))
            panel = pygame.Rect(400 - 150, 200 - 30, 300, 60)
            draw_wood_panel(screen, panel)
            screen.blit(clear_text, (400 - clear_text.get_width()//2, 200 - clear_text.get_height()//2))
            draw_bottom_bar(screen, "결과", f"얻은 점수: {game_state.score}")
        else:
            draw_bottom_bar(screen, "해충 제거", "돌아다니는 벌레를 클릭해서 빠르게 제거하세요!")
