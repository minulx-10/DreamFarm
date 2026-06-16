"""화면 어디서든 부를 수 있는 소리 설정 오버레이.

오른쪽 위 스피커 버튼을 누르면 배경음·효과음 음량을 슬라이더로 조절하고
음소거를 켜고 끌 수 있는 작은 창이 열린다. main 루프가 매 프레임
handle_events()/draw()를 호출하며, 창이 열려 있는 동안에는 입력을 가로채
밑에 깔린 씬이 반응하지 않게 한다.
"""

import pygame

from core import audio
from core.assets import get_font, WHITE, TEXT_DARK, TEXT_MUTED
from core.ui import draw_panel, mix_color


class SettingsOverlay:
    def __init__(self):
        self.open = False
        self._drag = None  # None | "bgm" | "sfx"

        # 오른쪽 위 고정 버튼 (점수 박스 오른쪽, 상단 바 안쪽 자리)
        self.button = pygame.Rect(746, 27, 28, 28)

        # 가운데 모달 패널
        self.panel = pygame.Rect(232, 166, 336, 272)
        pad = 26
        self._track_w = 160
        track_x = self.panel.x + pad + 72
        self._bgm_track = pygame.Rect(track_x, self.panel.y + 84, self._track_w, 8)
        self._sfx_track = pygame.Rect(track_x, self.panel.y + 136, self._track_w, 8)
        self._mute_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 188, 140, 40)
        self._close_btn = pygame.Rect(self.panel.right - pad - 120, self.panel.y + 188, 120, 40)

    # ------------------------------------------------------------------ 입력
    def handle_events(self, events):
        """오버레이가 이 프레임의 입력을 소비했으면 True를 반환(씬으로 안 넘김)."""
        consumed = False
        for event in events:
            if not self.open:
                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                        and self.button.collidepoint(event.pos)):
                    self.open = True
                    consumed = True
                continue

            # --- 창이 열려 있을 때: 모든 입력을 소비 ---
            consumed = True
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_m):
                self.open = False
                self._drag = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_press(event.pos)
            elif event.type == pygame.MOUSEMOTION and self._drag:
                self._set_from_mouse(event.pos[0])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._drag == "sfx":
                    audio.play("hover")  # 놓는 순간 최종 음량을 한 번 들려준다
                self._drag = None
        return consumed

    def _on_press(self, pos):
        if self._bgm_track.inflate(24, 22).collidepoint(pos):
            self._drag = "bgm"
            self._set_from_mouse(pos[0])
        elif self._sfx_track.inflate(24, 22).collidepoint(pos):
            self._drag = "sfx"
            self._set_from_mouse(pos[0])
            audio.play("hover")
        elif self._mute_btn.collidepoint(pos):
            audio.toggle_mute()
        elif self._close_btn.collidepoint(pos) or self.button.collidepoint(pos):
            self.open = False
        elif not self.panel.collidepoint(pos):
            self.open = False  # 바깥을 누르면 닫힘

    def _set_from_mouse(self, mx):
        track = self._bgm_track if self._drag == "bgm" else self._sfx_track
        ratio = max(0.0, min(1.0, (mx - track.x) / track.w))
        if self._drag == "bgm":
            audio.set_bgm_volume(ratio)
            if audio.is_muted() and ratio > 0:
                audio.set_muted(False)
        else:
            audio.set_sfx_volume(ratio)
            if audio.is_muted() and ratio > 0:
                audio.set_muted(False)

    # ------------------------------------------------------------------ 그리기
    def draw(self, screen):
        self._draw_button(screen)
        if self.open:
            self._draw_panel(screen)

    def _draw_button(self, screen):
        b = self.button
        hovered = b.collidepoint(pygame.mouse.get_pos())
        bg = (60, 74, 74) if not self.open else (96, 120, 110)
        if hovered:
            bg = mix_color(bg, WHITE, 0.2)
        pygame.draw.rect(screen, bg, b, border_radius=7)
        pygame.draw.rect(screen, (229, 192, 124), b, 1, border_radius=7)
        self._draw_speaker_icon(screen, b.x + 6, b.y + 6,
                                muted=audio.is_muted() or not audio.is_enabled())

    @staticmethod
    def _draw_speaker_icon(screen, x, y, muted):
        col = (210, 216, 208) if not muted else (150, 138, 132)
        pygame.draw.rect(screen, col, (x, y + 4, 5, 7))
        pygame.draw.polygon(screen, col, [(x + 5, y + 4), (x + 11, y), (x + 11, y + 15), (x + 5, y + 11)])
        if muted:
            pygame.draw.line(screen, (214, 96, 84), (x + 12, y + 1), (x + 14, y + 14), 2)
        else:
            pygame.draw.arc(screen, col, (x + 10, y + 1, 7, 13), -0.9, 0.9, 2)

    def _draw_panel(self, screen):
        # 뒤를 살짝 어둡게
        veil = pygame.Surface((800, 600), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 110))
        screen.blit(veil, (0, 0))

        draw_panel(screen, self.panel, radius=12)

        title = get_font(20).render("소리 설정", True, TEXT_DARK)
        screen.blit(title, (self.panel.centerx - title.get_width() // 2, self.panel.y + 22))

        self._draw_slider_row(screen, "배경음", self._bgm_track, audio.get_bgm_volume())
        self._draw_slider_row(screen, "효과음", self._sfx_track, audio.get_sfx_volume())

        # 음소거 토글
        muted = audio.is_muted()
        self._draw_text_button(screen, self._mute_btn,
                               "소리 켜기" if muted else "음소거",
                               active=muted)
        # 닫기
        self._draw_text_button(screen, self._close_btn, "닫기", active=False)

        if not audio.is_enabled():
            warn = get_font(13).render("(이 기기에서는 소리를 낼 수 없어요)", True, TEXT_MUTED)
            screen.blit(warn, (self.panel.centerx - warn.get_width() // 2, self.panel.bottom - 26))

    def _draw_slider_row(self, screen, label, track, value):
        font = get_font(16)
        lab = font.render(label, True, TEXT_DARK)
        screen.blit(lab, (self.panel.x + 26, track.y - 7))

        muted = audio.is_muted()
        # 트랙
        pygame.draw.rect(screen, (206, 188, 158), track, border_radius=4)
        fill_col = (150, 158, 150) if muted else (104, 164, 118)
        fill_w = int(track.w * value)
        if fill_w > 0:
            pygame.draw.rect(screen, fill_col, (track.x, track.y, fill_w, track.h), border_radius=4)
        # 손잡이
        kx = track.x + int(track.w * value)
        ky = track.centery
        pygame.draw.circle(screen, (121, 94, 68), (kx, ky), 9)
        pygame.draw.circle(screen, WHITE if not muted else (224, 218, 206), (kx, ky), 6)
        # 퍼센트
        pct = get_font(14).render(f"{int(round(value * 100))}%", True, TEXT_MUTED)
        screen.blit(pct, (track.right + 14, track.y - 6))

    @staticmethod
    def _draw_text_button(screen, rect, text, active):
        base = (113, 154, 120) if active else (255, 236, 188)
        edge = (61, 100, 76) if active else (123, 92, 65)
        if rect.collidepoint(pygame.mouse.get_pos()):
            base = mix_color(base, WHITE, 0.16)
        draw_panel(screen, rect, fill=base, border=edge, radius=8)
        font = get_font(17)
        surf = font.render(text, True, WHITE if active else TEXT_DARK)
        screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                           rect.centery - surf.get_height() // 2))
