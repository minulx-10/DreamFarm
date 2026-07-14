import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, GOLD
from core.ui import draw_story_backdrop, draw_light_panel, draw_button
from core import audio


class CreditsScene:
    """제작진(크레딧) 화면 — 타이틀 '제작진' 버튼으로 언제든 볼 수 있다.

    엔딩에도 크레딧 롤이 있지만 그건 게임을 끝까지 해야 나오므로, 여기서 상시 접근용
    정적 크레딧을 한 화면에 보여 준다. (폰트 라이선스 표기는 SIL OFL 준수용으로 필수.)"""

    def __init__(self):
        self.font_title = get_font(40)
        self.font_head = get_font(19)
        self.font_body = get_font(16)
        self.font_small = get_font(13)
        self.back_btn = pygame.Rect(24, 22, 104, 34)
        self.hovered_back = False

    def _to_title(self):
        audio.play("click")
        game_state.current_scene = "title"

    def handle_events(self, events):
        self.hovered_back = self.back_btn.collidepoint(pygame.mouse.get_pos())
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_btn.collidepoint(event.pos):
                    self._to_title()
            elif event.type == pygame.KEYDOWN and event.key in (
                    pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE):
                self._to_title()

    def update(self, dt):
        pass

    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")
        draw_button(screen, self.back_btn, "돌아가기", self.font_body, hovered=self.hovered_back)

        panel = pygame.Rect(160, 66, 480, 476)
        draw_light_panel(screen, panel)
        cx = panel.centerx

        def centered(surf, yy):
            screen.blit(surf, (cx - surf.get_width() // 2, yy))

        y = panel.y + 26
        centered(self.font_title.render("몽중농원", True, GOLD), y); y += 54
        centered(self.font_small.render("당근 한 뿌리의 시간", True, TEXT_MUTED), y); y += 40

        def head(txt, yy):
            centered(self.font_head.render(txt, True, (150, 110, 60)), yy)
            return yy + 30

        def body(txt, yy, col=TEXT_DARK):
            centered(self.font_body.render(txt, True, col), yy)
            return yy + 26

        # 만든 사람들 — 삼광(三光) 팀. 학번+이름은 중앙 거터 왼쪽, 역할은 오른쪽으로 정렬해
        # 세 사람이 표처럼 가지런히 읽히게 한다.
        def roster(who, role, yy):
            name_surf = self.font_body.render(who, True, TEXT_DARK)
            role_surf = self.font_body.render(role, True, TEXT_MUTED)
            screen.blit(name_surf, (cx - 14 - name_surf.get_width(), yy))
            screen.blit(role_surf, (cx + 14, yy))
            return yy + 28

        y = head("삼광 (三光)", y)
        y = roster("1302 김민욱", "팀장 · 개발", y)
        y = roster("1303 박서현", "기획 · 스토리", y)
        y = roster("1305 서태양", "기획 · 디자인", y)
        y += 22

        y = head("사용 폰트", y)
        y = body("갈무리11 (Galmuri11) — 달고나(Dalgona)", y)
        y = body("SIL Open Font License 1.1", y, TEXT_MUTED)
        y += 22
        y = body("함께 해 주셔서 고맙습니다.", y, TEXT_MUTED)

        # 저작권 (연도·제작팀 명시)
        centered(self.font_small.render("© 2026 삼광 (三光). All Rights Reserved.", True, TEXT_MUTED),
                 panel.bottom - 32)
