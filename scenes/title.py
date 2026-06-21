import pygame
import random
import math
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE, sprites
from core.ui import draw_story_backdrop, draw_button
from core import audio

class TitleScene:
    def __init__(self):
        self.font_title = get_font(44)
        self.font_subtitle = get_font(20)
        self.font_button = get_font(22)
        
        # '시작하기' 버튼 영역 (800x600 화면의 중앙 하단 배치)
        self.start_btn = pygame.Rect(280, 420, 240, 52)
        self.hovered = False
        
        # 타이틀 화면을 꾸밀 둥둥 떠다니는 반딧불이(꿈 입자) 리스트 생성
        self.fireflies = []
        for _ in range(16):
            self.fireflies.append({
                'x': random.randint(30, 770),
                'y': random.randint(30, 390),
                'speed_x': random.uniform(-10.0, 10.0),
                'speed_y': random.uniform(-5.0, 5.0),
                'scale_timer': random.uniform(0.0, 6.28),
                'size': random.uniform(2.5, 5.0)
            })

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        new_hover = self.start_btn.collidepoint(mouse_pos)
        
        # 호버 상태 변화 시 효과음 재생
        if new_hover != self.hovered:
            self.hovered = new_hover
            if self.hovered:
                audio.play("hover")
                
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.hovered:
                    audio.play("click")
                    game_state.current_scene = "name_input"
            elif event.type == pygame.KEYDOWN:
                # Enter 또는 Space 누르면 즉시 다음 단계(이름 입력)로 진입
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    audio.play("click")
                    game_state.current_scene = "name_input"

    def update(self, dt):
        # 반딧불이 입자 위치 업데이트 및 벽 충돌 반사
        for f in self.fireflies:
            f['x'] += f['speed_x'] * dt
            f['y'] += f['speed_y'] * dt
            f['scale_timer'] += 2.0 * dt
            if f['x'] < 10 or f['x'] > 790:
                f['speed_x'] *= -1
            if f['y'] < 10 or f['y'] > 400:
                f['speed_y'] *= -1

    def draw(self, screen):
        # 1. 밤하늘 배경 그리기 (달빛/초승달 포함)
        draw_story_backdrop(screen, "night")
        
        # 2. 반딧불이 입자(꿈 속의 은은한 불빛) 그리기
        for f in self.fireflies:
            alpha = int(110 + 70 * math.sin(f['scale_timer']))
            alpha = max(0, min(255, alpha))
            
            glow_color = (255, 235, 140)
            glow_surf = pygame.Surface((int(f['size'] * 6), int(f['size'] * 6)), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (glow_color[0], glow_color[1], glow_color[2], int(alpha * 0.45)), (int(f['size'] * 3), int(f['size'] * 3)), int(f['size'] * 2.5))
            pygame.draw.circle(glow_surf, (255, 255, 200, alpha), (int(f['size'] * 3), int(f['size'] * 3)), int(f['size'] * 1.1))
            screen.blit(glow_surf, (int(f['x'] - f['size'] * 3), int(f['y'] - f['size'] * 3)))
            
        # 3. 아버님 실루엣 뒤에 은은하게 그리기
        dad = sprites['dad']
        shadow = dad.copy()
        shadow.set_alpha(65)
        # 타이틀 글자와 겹치지 않게 중앙 약간 하단에 배치
        screen.blit(shadow, (400 - dad.get_width() // 2 + 3, 243))
        screen.blit(dad, (400 - dad.get_width() // 2, 240))
        
        # 4. 게임 제목 ("몽중농원") 및 부제 그리기
        title_surf = self.font_title.render("몽중농원", True, (255, 240, 206))
        # 그림자 효과 추가로 입체감 부여
        title_shadow = self.font_title.render("몽중농원", True, (38, 32, 34))
        screen.blit(title_shadow, (400 - title_surf.get_width() // 2 + 3, 113))
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 110))
        
        subtitle_surf = self.font_subtitle.render("당근 한 뿌리의 시간", True, (213, 180, 140))
        subtitle_shadow = self.font_subtitle.render("당근 한 뿌리의 시간", True, (38, 32, 34))
        screen.blit(subtitle_shadow, (400 - subtitle_surf.get_width() // 2 + 2, 167))
        screen.blit(subtitle_surf, (400 - subtitle_surf.get_width() // 2, 165))
        
        # 5. 시작하기 버튼 그리기
        draw_button(screen, self.start_btn, "시작하기", self.font_button, hovered=self.hovered)
