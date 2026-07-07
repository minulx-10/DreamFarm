import pygame
import random
import math
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE
from core.ui import draw_story_backdrop, draw_button
from core import audio
from core import save_system
from core.ui_utils import FireflyEmitter

class TitleScene:
    def __init__(self):
        self.font_title = get_font(44)
        self.font_subtitle = get_font(20)
        self.font_button = get_font(20)
        
        # 엔딩 해금 여부에 따라 갤러리 노출 여부 결정
        self.show_gallery = save_system.crops_unlocked()
        
        button_y = 240
        self.start_btn = pygame.Rect(280, button_y, 240, 40)
        self.load_btn = pygame.Rect(280, button_y + 50, 240, 40)
        
        current_y = button_y + 100
        if self.show_gallery:
            self.gallery_btn = pygame.Rect(280, current_y, 240, 40)
            current_y += 50
            
        self.settings_btn = pygame.Rect(280, current_y, 240, 40)
        self.quit_btn = pygame.Rect(280, current_y + 50, 240, 40)
        
        self.hovered_start = False
        self.hovered_load = False
        self.hovered_gallery = False
        self.hovered_settings = False
        self.hovered_quit = False

        # 이스터에그: 달을 네 번 두드리면 악)몽중농원 모드가 켜지고 배경·음악이 검붉게 바뀐다.
        self.moon_rect = pygame.Rect(648 - 42, 90 - 42, 84, 84)
        self.moon_clicks = 0
        
        # 타이틀 화면의 반딧불이(꿈 입자) 리스트 생성
        self.firefly_emitter = FireflyEmitter(16)

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        
        # 호버 상태 갱신
        h_start = self.start_btn.collidepoint(mouse_pos)
        h_load = self.load_btn.collidepoint(mouse_pos)
        h_gallery = self.gallery_btn.collidepoint(mouse_pos) if self.show_gallery else False
        h_settings = self.settings_btn.collidepoint(mouse_pos)
        h_quit = self.quit_btn.collidepoint(mouse_pos)
        
        # 호버 시 사운드 피드백
        any_new_hover = (h_start and not self.hovered_start) or \
                         (h_load and not self.hovered_load) or \
                         (h_gallery and not self.hovered_gallery) or \
                         (h_settings and not self.hovered_settings) or \
                         (h_quit and not self.hovered_quit)
                         
        self.hovered_start = h_start
        self.hovered_load = h_load
        self.hovered_gallery = h_gallery
        self.hovered_settings = h_settings
        self.hovered_quit = h_quit
        
        if any_new_hover:
            audio.play("hover")
                
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 이스터에그: 달 4연타 → 악)몽중농원 토글
                if self.moon_rect.collidepoint(event.pos):
                    self.moon_clicks += 1
                    audio.play("pop")
                    if self.moon_clicks >= 4:
                        self.moon_clicks = 0
                        game_state.nightmare = not game_state.nightmare
                        audio.play("epiphany")
                    continue
                # 시작하기
                if self.hovered_start:
                    audio.play("click")
                    if save_system.crops_unlocked():
                        game_state.current_scene = "crop_select"
                    else:
                        game_state.crop = "carrot"
                        game_state.nightmare = False
                        game_state.current_scene = "name_input"
                # 불러오기
                elif self.hovered_load:
                    if save_system.has_save():
                        audio.play("success")
                        game_state.request_load = True
                    else:
                        audio.play("break")
                # 갤러리
                elif self.hovered_gallery and self.show_gallery:
                    audio.play("click")
                    game_state.current_scene = "gallery"
                # 설정
                elif self.hovered_settings:
                    audio.play("click")
                    game_state.request_settings = True
                # 끝내기
                elif self.hovered_quit:
                    audio.play("click")
                    game_state.request_quit = True
            elif event.type == pygame.KEYDOWN:
                # Enter 또는 Space 누르면 시작하기 작동
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    audio.play("click")
                    if save_system.crops_unlocked():
                        game_state.current_scene = "crop_select"
                    else:
                        game_state.crop = "carrot"
                        game_state.nightmare = False
                        game_state.current_scene = "name_input"

    def update(self, dt):
        self.firefly_emitter.update(dt)

    def draw(self, screen):
        # 1. 배경 (달 이스터에그로 악몽 모드가 켜지면 검붉게)
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")
        
        # 2. 반딧불이 그리기
        self.firefly_emitter.draw(screen)
            
        # 3. 제목 및 부제 그리기 (달 이스터에그로 악몽 모드면 제목도 '악)몽중농원')
        title_text = "악)몽중농원" if game_state.nightmare else "몽중농원"
        title_col = (255, 150, 140) if game_state.nightmare else (255, 240, 206)
        title_surf = self.font_title.render(title_text, True, title_col)
        title_shadow = self.font_title.render(title_text, True, (38, 32, 34))
        screen.blit(title_shadow, (400 - title_surf.get_width() // 2 + 3, 93))
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 90))
        
        subtitle_surf = self.font_subtitle.render("당근 한 뿌리의 시간", True, (213, 180, 140))
        subtitle_shadow = self.font_subtitle.render("당근 한 뿌리의 시간", True, (38, 32, 34))
        screen.blit(subtitle_shadow, (400 - subtitle_surf.get_width() // 2 + 2, 147))
        screen.blit(subtitle_surf, (400 - subtitle_surf.get_width() // 2, 145))
        
        # 4. 버튼들 그리기
        draw_button(screen, self.start_btn, "새 게임 시작", self.font_button, hovered=self.hovered_start)
        
        # 불러오기 버튼 (저장 데이터 여부에 따라 비활성화 묘사)
        has_save = save_system.has_save()
        if has_save:
            draw_button(screen, self.load_btn, "이어 하기", self.font_button, hovered=self.hovered_load)
        else:
            # 비활성화된 모양 그리기
            pygame.draw.rect(screen, (70, 70, 70), self.load_btn, border_radius=8)
            pygame.draw.rect(screen, (100, 100, 100), self.load_btn, 1, border_radius=8)
            label = self.font_button.render("이어 하기", True, (130, 130, 130))
            screen.blit(label, (self.load_btn.centerx - label.get_width() // 2, self.load_btn.centery - label.get_height() // 2))
            
        if self.show_gallery:
            draw_button(screen, self.gallery_btn, "추억 갤러리", self.font_button, hovered=self.hovered_gallery)
            
        draw_button(screen, self.settings_btn, "소리 및 설정", self.font_button, hovered=self.hovered_settings)
        draw_button(screen, self.quit_btn, "게임 끝내기", self.font_button, hovered=self.hovered_quit)
