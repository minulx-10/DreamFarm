"""게임 종료 확인 모달 오버레이.

사용자가 Pygame 창을 닫거나 타이틀 화면에서 '끝내기'를 누를 때,
종료 의사를 확인하는 이중 안전 모달 오버레이를 제공합니다.
"""

import pygame
from core.game_state import game_state
from core.assets import get_font
from core.ui import draw_wood_panel, draw_light_panel
from core import audio


class QuitOverlay:
    def __init__(self):
        self.panel = pygame.Rect(400 - 150, 300 - 80, 300, 160)
        self.yes_btn = pygame.Rect(400 - 95, 300 + 15, 85, 35)
        self.no_btn = pygame.Rect(400 + 10, 300 + 15, 85, 35)
        self.yes_hover = False
        self.no_hover = False

    def handle_events(self, events):
        if not game_state.request_quit:
            return False

        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.yes_hover = self.yes_btn.collidepoint(event.pos)
                self.no_hover = self.no_btn.collidepoint(event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.yes_btn.collidepoint(event.pos):
                    audio.play("click")
                    game_state.running = False
                    return True
                elif self.no_btn.collidepoint(event.pos):
                    audio.play("click")
                    game_state.request_quit = False
                    self.yes_hover = False
                    self.no_hover = False
                    return True
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    audio.play("click")
                    game_state.request_quit = False
                    return True
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    audio.play("click")
                    game_state.running = False
                    return True
        return True

    def draw(self, screen):
        if not game_state.request_quit:
            return

        # 어두운 틴트 오버레이
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # 메인 패널
        draw_wood_panel(screen, self.panel)

        # 텍스트
        font_title = get_font(20)
        title_surf = font_title.render("정말 종료하시겠습니까?", True, (56, 33, 15))
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 300 - 45))

        # 예 버튼
        if self.yes_hover:
            pygame.draw.rect(screen, (246, 222, 169), self.yes_btn, border_radius=6)
            pygame.draw.rect(screen, (150, 100, 60), self.yes_btn, 2, border_radius=6)
        else:
            draw_light_panel(screen, self.yes_btn)
        font_btn = get_font(16)
        yes_surf = font_btn.render("예", True, (60, 30, 10))
        screen.blit(yes_surf, (self.yes_btn.centerx - yes_surf.get_width() // 2, self.yes_btn.centery - yes_surf.get_height() // 2))

        # 아니오 버튼
        if self.no_hover:
            pygame.draw.rect(screen, (246, 222, 169), self.no_btn, border_radius=6)
            pygame.draw.rect(screen, (150, 100, 60), self.no_btn, 2, border_radius=6)
        else:
            draw_light_panel(screen, self.no_btn)
        no_surf = font_btn.render("아니오", True, (60, 30, 10))
        screen.blit(no_surf, (self.no_btn.centerx - no_surf.get_width() // 2, self.no_btn.centery - no_surf.get_height() // 2))
