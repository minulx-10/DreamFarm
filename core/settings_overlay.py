"""화면 어디서든 부를 수 있는 소리 및 게임 설정 오버레이.

오른쪽 위 톱니바퀴 버튼을 누르면 배경음·효과음 음량을 슬라이더로 조절하고
자동 저장 설정, 저장하기, 불러오기, 세이브 삭제, 메인 화면 이동을 수행할 수 있는 모달 창이 열린다.
"""

import pygame
import math

from core import audio
from core.assets import get_font, WHITE, TEXT_DARK, TEXT_MUTED
from core.ui import draw_panel, mix_color
from core.game_state import game_state
from core.platform import IS_ANDROID
from core import save_system


class SettingsOverlay:
    def __init__(self):
        self.open = False
        self._drag = None  # None | "bgm" | "sfx"

        # 오른쪽 위 고정 버튼
        self.button = pygame.Rect(746, 27, 28, 28)

        # 가운데 모달 패널 (전체화면·언어 토글 행이 들어가 세로로 늘림: 360x500)
        self.panel = pygame.Rect(220, 46, 360, 500)
        pad = 26
        self._track_w = 160
        track_x = self.panel.x + pad + 72
        
        self._bgm_track = pygame.Rect(track_x, self.panel.y + 76, self._track_w, 8)
        self._sfx_track = pygame.Rect(track_x, self.panel.y + 120, self._track_w, 8)
        
        self._mute_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 164, 140, 36)
        self._autosave_btn = pygame.Rect(self.panel.right - pad - 140, self.panel.y + 164, 140, 36)
        
        self._save_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 224, 140, 36)
        self._load_btn = pygame.Rect(self.panel.right - pad - 140, self.panel.y + 224, 140, 36)
        
        self._delete_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 284, 140, 36)
        self._main_btn = pygame.Rect(self.panel.right - pad - 140, self.panel.y + 284, 140, 36)

        # 완전 초기화 — 슬롯 + 메타 기록 전체 삭제 (전체폭)
        self._reset_all_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 340, self.panel.width - 2 * pad, 34)

        # 하단 2×2 토글 그리드: [전체화면][언어] / [버전 표시][닫기]
        self._fullscreen_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 388, 140, 36)
        self._lang_btn = pygame.Rect(self.panel.right - pad - 140, self.panel.y + 388, 140, 36)
        self._version_btn = pygame.Rect(self.panel.x + pad, self.panel.y + 432, 140, 36)
        self._close_btn = pygame.Rect(self.panel.right - pad - 140, self.panel.y + 432, 140, 36)

        self.show_message = ""
        self.message_timer = 0.0

        # 확인 모달 상태 ("delete_save" | "go_main" | "reset_all" | ... | None)
        self._confirm_action = None
        self._reset_confirm_text = ""   # 완전 초기화 확정용 입력(확정된 글자) — 데스크톱
        self._reset_ime = ""            # 한글 조합 중인 미확정 글자
        self._reset_armed = False       # 안드로이드: '예'를 한 번 눌러 무장된 상태(두 번째 눌러야 실행)
        self._confirm_yes = pygame.Rect(self.panel.centerx - 80, self.panel.y + 350, 65, 32)
        self._confirm_no = pygame.Rect(self.panel.centerx + 15, self.panel.y + 350, 65, 32)

    def update(self, dt):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.show_message = ""

    # ------------------------------------------------------------------ 입력
    def handle_events(self, events, farm_scene=None):
        """오버레이가 이 프레임의 입력을 소비했으면 True를 반환."""
        consumed = False
        for event in events:
            if not self.open:
                if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                        and self.button.collidepoint(event.pos)):
                    self.open = True
                    consumed = True
                    self.show_message = ""
                    self._confirm_action = None
                continue

            # --- 창이 열려 있을 때: 모든 입력을 소비 ---
            consumed = True

            # 확인 모달이 뜬 상태에서는 확인/취소만 처리
            if self._confirm_action is not None:
                # 완전 초기화는 실수 방지 장치가 있다.
                #  - 데스크톱: '초기화'라고 직접 입력해야 확정.
                #  - 안드로이드: 키보드가 화면을 가려 타이핑이 불편하므로, '예'를 두 번 눌러 확정
                #    (첫 탭=무장, 둘째 탭=실행). 키보드 없이도 같은 수준의 실수 방지.
                need_type = (self._confirm_action == "reset_all")
                type_ok = (self._reset_confirm_text.strip() == "초기화")

                def _yes():
                    if need_type and not IS_ANDROID and not type_ok:
                        audio.play("break")
                    elif need_type and IS_ANDROID and not self._reset_armed:
                        self._reset_armed = True
                        audio.play("break")   # 경고음 — 한 번 더 눌러야 실행
                    else:
                        audio.play("click")
                        self._execute_confirm(farm_scene)

                if event.type == pygame.TEXTEDITING and need_type and not IS_ANDROID:
                    # 한글은 조합이 끝나야 TEXTINPUT으로 확정된다. 조합 중(미확정) 글자를
                    # 실시간으로 보여줘야 '초'가 안 뜨고 한 글자씩 밀려 보이던 문제가 사라진다.
                    self._reset_ime = event.text
                elif event.type == pygame.TEXTINPUT and need_type and not IS_ANDROID:
                    if len(self._reset_confirm_text) < 8:
                        self._reset_confirm_text += event.text
                    self._reset_ime = ""
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._confirm_yes.collidepoint(event.pos):
                        _yes()
                    elif self._confirm_no.collidepoint(event.pos):
                        audio.play("click")
                        self._close_confirm()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self._close_confirm()
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_BACKSPACE and need_type and not IS_ANDROID:
                    self._reset_confirm_text = self._reset_confirm_text[:-1]
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    _yes()
                continue

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.open = False
                    self._drag = None
                elif event.key == pygame.K_m:
                    audio.toggle_mute()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._on_press(event.pos, farm_scene)
            elif event.type == pygame.MOUSEMOTION and self._drag:
                self._set_from_mouse(event.pos[0])
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self._drag == "sfx":
                    audio.play("hover")
                self._drag = None
        return consumed

    def _close_confirm(self):
        """확인 모달을 닫는다 (완전 초기화 입력 상태도 정리)."""
        self._confirm_action = None
        self._reset_confirm_text = ""
        self._reset_ime = ""
        self._reset_armed = False
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass

    def _execute_confirm(self, farm_scene=None):
        if self._confirm_action == "delete_save":
            if save_system.delete_save():
                audio.play("success")
                self.show_message = "세이브 파일이 삭제되었습니다."
            else:
                audio.play("break")
                self.show_message = "삭제할 세이브가 없습니다."
            self.message_timer = 2.0
        elif self._confirm_action == "go_main":
            audio.play("click")
            game_state.current_scene = "title"
            self.open = False
        elif self._confirm_action == "save_game":
            if farm_scene is not None and save_system.save_game(farm_scene):
                audio.play("success")
                self.show_message = "게임이 저장되었습니다."
            else:
                audio.play("break")
                self.show_message = "저장에 실패했습니다."
            self.message_timer = 2.0
        elif self._confirm_action == "load_game":
            audio.play("success")
            game_state.request_load = True
            self.open = False
        elif self._confirm_action == "reset_all":
            save_system.reset_all()
            audio.play("success")
            self.show_message = "모든 기록이 초기화되었습니다."
            self.message_timer = 2.0
            # 태초로 — 악몽 모드(달 이스터에그 등)와 회차 기록까지 완전 초기화
            game_state.reset()
            game_state.nightmare = False
            game_state.is_second_run = False
            game_state.player_name = "지후"
            game_state.current_scene = "title"
            self.open = False
        self._confirm_action = None
        self._reset_confirm_text = ""
        self._reset_ime = ""
        self._reset_armed = False
        try:
            pygame.key.stop_text_input()
        except Exception:
            pass

    def _on_press(self, pos, farm_scene=None):
        if self._bgm_track.inflate(24, 22).collidepoint(pos):
            self._drag = "bgm"
            self._set_from_mouse(pos[0])
        elif self._sfx_track.inflate(24, 22).collidepoint(pos):
            self._drag = "sfx"
            self._set_from_mouse(pos[0])
            audio.play("hover")
        elif self._mute_btn.collidepoint(pos):
            audio.toggle_mute()
        elif self._autosave_btn.collidepoint(pos):
            current_autosave = save_system.get_setting("autosave")
            save_system.set_setting("autosave", not current_autosave)
            audio.play("click")
        elif self._save_btn.collidepoint(pos):
            # 실수로 덮어쓰지 않도록 저장 전 확인 절차를 한 번 거친다.
            if game_state.current_scene == "farm" and farm_scene is not None:
                self._confirm_action = "save_game"
            else:
                audio.play("break")
                self.show_message = "인게임 내에서만 저장 가능합니다."
                self.message_timer = 2.0
        elif self._load_btn.collidepoint(pos):
            # 현재 진행이 날아가므로 불러오기 전 확인 절차를 거친다.
            if save_system.has_save():
                self._confirm_action = "load_game"
            else:
                audio.play("break")
                self.show_message = "저장된 게임이 없습니다."
                self.message_timer = 2.0
        elif self._delete_btn.collidepoint(pos):
            if save_system.has_save():
                self._confirm_action = "delete_save"
            else:
                audio.play("break")
                self.show_message = "삭제할 세이브가 없습니다."
                self.message_timer = 2.0
        elif self._main_btn.collidepoint(pos):
            self._confirm_action = "go_main"
        elif self._reset_all_btn.collidepoint(pos):
            self._confirm_action = "reset_all"
            self._reset_confirm_text = ""
            self._reset_armed = False
            # 안드로이드는 소프트 키보드 없이 '예 두 번'으로 확정하므로 텍스트 입력을 켜지 않는다.
            if not IS_ANDROID:
                try:
                    pygame.key.start_text_input()
                except Exception:
                    pass
        elif not IS_ANDROID and self._fullscreen_btn.collidepoint(pos):
            # 실제 전환은 game_main 루프가 처리(F11과 동일 경로). 설정창은 열어 둔 채 즉시 반영.
            game_state.request_fullscreen_toggle = True
            audio.play("click")
        elif self._lang_btn.collidepoint(pos):
            from core import i18n
            new_lang = i18n.toggle()
            save_system.set_setting("language", new_lang)
            audio.play("click")
        elif self._version_btn.collidepoint(pos):
            current_show = save_system.get_setting("show_version")
            save_system.set_setting("show_version", not current_show)
            audio.play("click")
        elif self._close_btn.collidepoint(pos) or self.button.collidepoint(pos):
            self.open = False
        elif not self.panel.collidepoint(pos):
            self.open = False

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
        self._draw_gear_icon(screen, b.centerx, b.centery, bg)

    @staticmethod
    def _draw_gear_icon(screen, cx, cy, bg_color):
        """톱니바퀴 아이콘 — 픽셀 스프라이트(작물·날씨 아이콘과 톤 통일)."""
        from core.assets import sprites
        spr = sprites.get('icon_gear')
        if spr is None:
            return
        s = 22
        scaled = pygame.transform.scale(spr, (s, s))
        screen.blit(scaled, (cx - s // 2, cy - s // 2))

    def _draw_panel(self, screen):
        # 뒤를 살짝 어둡게
        veil = pygame.Surface((800, 600), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 110))
        screen.blit(veil, (0, 0))

        draw_panel(screen, self.panel, radius=12)

        title = get_font(20).render("설정 및 저장", True, TEXT_DARK)
        screen.blit(title, (self.panel.centerx - title.get_width() // 2, self.panel.y + 20))

        self._draw_slider_row(screen, "배경음", self._bgm_track, audio.get_bgm_volume())
        self._draw_slider_row(screen, "효과음", self._sfx_track, audio.get_sfx_volume())

        # 음소거 토글
        muted = audio.is_muted()
        self._draw_text_button(screen, self._mute_btn,
                               "소리 켜기" if muted else "음소거",
                               active=muted)
        
        # 자동 저장 토글
        autosave = save_system.get_setting("autosave")
        self._draw_text_button(screen, self._autosave_btn,
                               f"자동저장: {'ON' if autosave else 'OFF'}",
                               active=autosave)

        # 구분선
        sep_y = self.panel.y + 214
        pygame.draw.line(screen, (190, 175, 155), (self.panel.x + 26, sep_y), (self.panel.right - 26, sep_y), 1)

        # 저장하기 (인게임에서만 활성화 비주얼)
        in_farm = (game_state.current_scene == "farm")
        self._draw_text_button(screen, self._save_btn, "저장하기", active=False, disabled=not in_farm)

        # 불러오기 (저장본이 있을 때만 활성화 비주얼)
        has_save = save_system.has_save()
        self._draw_text_button(screen, self._load_btn, "불러오기", active=False, disabled=not has_save)

        # 구분선
        sep_y2 = self.panel.y + 274
        pygame.draw.line(screen, (190, 175, 155), (self.panel.x + 26, sep_y2), (self.panel.right - 26, sep_y2), 1)

        # 세이브 삭제 (저장본이 있을 때만 활성화 비주얼)
        self._draw_text_button(screen, self._delete_btn, "세이브 삭제", active=False, disabled=not has_save,
                               danger=True)

        # 메인으로 돌아가기
        self._draw_text_button(screen, self._main_btn, "메인으로", active=False)

        # 완전 초기화 (되돌릴 수 없는 파괴적 동작 → danger 스타일)
        self._draw_text_button(screen, self._reset_all_btn, "완전 초기화 (태초부터)", active=False, danger=True)

        # 하단 2×2 토글: [전체화면][언어] / [버전 표시][닫기]
        if not IS_ANDROID:
            fs = game_state.is_fullscreen
            self._draw_text_button(screen, self._fullscreen_btn,
                                   f"전체화면: {'ON' if fs else 'OFF'}", active=fs)
        # 언어 토글 — 현재 언어를 그 언어로 표기 (누르면 다른 언어로 전환)
        from core import i18n
        is_en = (i18n.get_language() == "en")
        lang_label = "Language: English" if is_en else "언어: 한국어"
        self._draw_text_button(screen, self._lang_btn, lang_label, active=is_en)

        show_ver = save_system.get_setting("show_version")
        self._draw_text_button(screen, self._version_btn, f"버전 표시: {'ON' if show_ver else 'OFF'}", active=show_ver)
        self._draw_text_button(screen, self._close_btn, "닫기", active=False)

        # 알림 메시지 출력
        if self.show_message:
            msg_surf = get_font(14).render(self.show_message, True, (139, 69, 19))
            screen.blit(msg_surf, (self.panel.centerx - msg_surf.get_width() // 2, self.panel.y + 476))

        if not audio.is_enabled():
            warn = get_font(13).render("(이 기기에서는 소리를 낼 수 없어요)", True, TEXT_MUTED)
            screen.blit(warn, (self.panel.centerx - warn.get_width() // 2, self.panel.bottom - 20))

        # 확인 모달 (세이브 삭제 / 메인 이동)
        if self._confirm_action is not None:
            self._draw_confirm_modal(screen)

    def _draw_confirm_modal(self, screen):
        # 반투명 덮개
        veil = pygame.Surface((self.panel.w, self.panel.h), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 140))
        screen.blit(veil, (self.panel.x, self.panel.y))

        # 모달 폭을 넓혀 문구가 상자 밖으로 삐져나오지 않게 한다 (좌우 여백 확보).
        modal = pygame.Rect(0, 0, 324, 124)
        modal.center = (self.panel.centerx, self.panel.y + 340)
        draw_panel(screen, modal, radius=10)

        info = {
            "delete_save": ("세이브를 삭제하시겠습니까?", "이 기록은 되돌릴 수 없습니다."),
            "go_main": ("메인 화면으로 돌아가시겠습니까?", "저장하지 않은 진행은 사라집니다."),
            "save_game": ("현재 상태를 저장하시겠습니까?",
                          "기존 저장을 덮어씁니다." if save_system.has_save() else "새 저장을 만듭니다."),
            "load_game": ("저장된 게임을 불러오시겠습니까?", "저장하지 않은 진행은 사라집니다."),
            "reset_all": ("완전 초기화 하시겠습니까?", "모든 엔딩·업적·이야기 기록이 사라집니다."),
        }
        msg, sub = info.get(self._confirm_action, ("진행하시겠습니까?", ""))

        msg_surf = get_font(15).render(msg, True, TEXT_DARK)
        screen.blit(msg_surf, (modal.centerx - msg_surf.get_width() // 2, modal.y + 20))

        yes_disabled = False
        yes_label = "예"
        if self._confirm_action == "reset_all" and IS_ANDROID:
            # 안드로이드: 키보드 없이 '예'를 두 번 눌러 확정한다.
            if self._reset_armed:
                warn = get_font(13).render("다시 '예'를 누르면 모두 삭제됩니다", True, (200, 70, 60))
                yes_label = "정말 삭제"
            else:
                warn = get_font(13).render("'예'를 두 번 눌러 확정하세요", True, TEXT_MUTED)
            screen.blit(warn, (modal.centerx - warn.get_width() // 2, modal.y + 50))
        elif self._confirm_action == "reset_all":
            # 데스크톱: 실수 방지 — '초기화'라고 직접 입력해야 '예'가 활성화된다.
            ok = (self._reset_confirm_text.strip() == "초기화")   # 판정은 확정된 글자만
            typed = self._reset_confirm_text + self._reset_ime    # 표시는 조합 중 글자까지
            label = get_font(13).render("확인하려면 '초기화' 입력:", True, TEXT_MUTED)
            box_w = 76
            total = label.get_width() + 8 + box_w
            lx = modal.centerx - total // 2
            screen.blit(label, (lx, modal.y + 50))
            ib = pygame.Rect(lx + label.get_width() + 8, modal.y + 47, box_w, 22)
            pygame.draw.rect(screen, (255, 249, 230), ib, border_radius=4)
            pygame.draw.rect(screen, (60, 150, 70) if ok else (170, 120, 80), ib, 2, border_radius=4)
            tt = get_font(14).render(typed, True, (50, 140, 60) if ok else TEXT_DARK)
            screen.blit(tt, (ib.x + 6, ib.centery - tt.get_height() // 2))
            yes_disabled = not ok
        elif sub:
            sub_surf = get_font(12).render(sub, True, TEXT_MUTED)
            screen.blit(sub_surf, (modal.centerx - sub_surf.get_width() // 2, modal.y + 48))

        self._draw_text_button(screen, self._confirm_yes, yes_label, active=False, disabled=yes_disabled,
                               danger=(self._confirm_action == "reset_all" and self._reset_armed))
        self._draw_text_button(screen, self._confirm_no, "아니오", active=False)

    def _draw_slider_row(self, screen, label, track, value):
        font = get_font(16)
        lab = font.render(label, True, TEXT_DARK)
        screen.blit(lab, (self.panel.x + 26, track.y - 7))

        muted = audio.is_muted()
        pygame.draw.rect(screen, (206, 188, 158), track, border_radius=4)
        fill_col = (150, 158, 150) if muted else (104, 164, 118)
        fill_w = int(track.w * value)
        if fill_w > 0:
            pygame.draw.rect(screen, fill_col, (track.x, track.y, fill_w, track.h), border_radius=4)
        
        kx = track.x + int(track.w * value)
        ky = track.centery
        pygame.draw.circle(screen, (121, 94, 68), (kx, ky), 9)
        pygame.draw.circle(screen, WHITE if not muted else (224, 218, 206), (kx, ky), 6)
        
        pct = get_font(14).render(f"{int(round(value * 100))}%", True, TEXT_MUTED)
        screen.blit(pct, (track.right + 14, track.y - 6))

    @staticmethod
    def _draw_text_button(screen, rect, text, active, disabled=False, danger=False):
        if disabled:
            base = (210, 205, 195)
            edge = (160, 155, 145)
            text_color = (140, 135, 125)
        elif danger:
            base = (245, 210, 210)
            edge = (180, 80, 80)
            text_color = (160, 50, 50)
        else:
            base = (113, 154, 120) if active else (255, 236, 188)
            edge = (61, 100, 76) if active else (123, 92, 65)
            text_color = WHITE if active else TEXT_DARK

        if not disabled and rect.collidepoint(pygame.mouse.get_pos()):
            base = mix_color(base, WHITE, 0.16)
        draw_panel(screen, rect, fill=base, border=edge, radius=8, shadow=not disabled)
        
        font = get_font(15)
        surf = font.render(text, True, text_color)
        screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                           rect.centery - surf.get_height() // 2))
