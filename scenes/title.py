import pygame
import random
import math
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE
from core.ui import draw_story_backdrop, draw_button
from core.pixelfx import pixel_rect, CHAMFER, CHAMFER_SM
from core import audio
from core import save_system
from core import i18n, updater
from core import version as _version
from core.ui_utils import FireflyEmitter

class TitleScene:
    def __init__(self):
        self.font_title = get_font(44)
        self.font_subtitle = get_font(20)
        self.font_button = get_font(20)
        self.font_util = get_font(16)   # 하단 보조 버튼(설정·제작진·끝내기)용 작은 폰트

        # 엔딩 해금 여부에 따라 갤러리 노출 여부 결정
        self.show_gallery = save_system.crops_unlocked()

        # 위쪽: 실제 '플레이' 동작만 큰 버튼으로 (새 게임 · 이어하기 · 갤러리)
        play_w = 240
        play_x = (800 - play_w) // 2
        button_y = 250
        self.start_btn = pygame.Rect(play_x, button_y, play_w, 44)
        self.load_btn = pygame.Rect(play_x, button_y + 54, play_w, 44)

        current_y = button_y + 108
        if self.show_gallery:
            self.gallery_btn = pygame.Rect(play_x, current_y, play_w, 44)
            current_y += 54

        # 에필로그 '아버지의 새벽' — 진엔딩을 본 뒤 열린다
        self.show_epilogue = save_system.epilogue_unlocked() and not _version.DEMO
        if self.show_epilogue:
            self.epilogue_btn = pygame.Rect(play_x, current_y, play_w, 44)
            current_y += 54

        # 아래쪽: 보조 기능(설정·제작진·끝내기)은 작은 버튼 한 줄로 묶어 정리
        util_w, util_h, gap = 148, 36, 16
        row_w = util_w * 3 + gap * 2
        util_x = (800 - row_w) // 2
        util_y = current_y + 22
        self.settings_btn = pygame.Rect(util_x, util_y, util_w, util_h)
        self.credits_btn = pygame.Rect(util_x + util_w + gap, util_y, util_w, util_h)
        self.quit_btn = pygame.Rect(util_x + 2 * (util_w + gap), util_y, util_w, util_h)

        self.hovered_start = False
        self.hovered_load = False
        self.hovered_gallery = False
        self.hovered_epilogue = False
        self.hovered_settings = False
        self.hovered_credits = False
        self.hovered_quit = False

        # 이스터에그: 달을 네 번 두드리면 악)몽중농원 모드가 켜지고 배경·음악이 검붉게 바뀐다.
        self.moon_rect = pygame.Rect(648 - 42, 90 - 42, 84, 84)
        self.moon_clicks = 0
        
        # 타이틀 화면의 반딧불이(꿈 입자) 리스트 생성
        self.firefly_emitter = FireflyEmitter(16)
        self._update_rect = None   # 업데이트 알림 클릭 영역(있을 때만)

        # 이따금 밤하늘을 가르는 유성 (도트 꼬리)
        self.shoot_timer = random.uniform(4.0, 9.0)
        self.shoot = None

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        
        # 호버 상태 갱신
        h_start = self.start_btn.collidepoint(mouse_pos)
        h_load = self.load_btn.collidepoint(mouse_pos)
        h_gallery = self.gallery_btn.collidepoint(mouse_pos) if self.show_gallery else False
        h_epilogue = self.epilogue_btn.collidepoint(mouse_pos) if self.show_epilogue else False
        h_settings = self.settings_btn.collidepoint(mouse_pos)
        h_credits = self.credits_btn.collidepoint(mouse_pos)
        h_quit = self.quit_btn.collidepoint(mouse_pos)

        # 호버 시 사운드 피드백
        any_new_hover = (h_start and not self.hovered_start) or \
                         (h_load and not self.hovered_load) or \
                         (h_gallery and not self.hovered_gallery) or \
                         (h_epilogue and not getattr(self, "hovered_epilogue", False)) or \
                         (h_settings and not self.hovered_settings) or \
                         (h_credits and not self.hovered_credits) or \
                         (h_quit and not self.hovered_quit)

        self.hovered_start = h_start
        self.hovered_load = h_load
        self.hovered_gallery = h_gallery
        self.hovered_epilogue = h_epilogue
        self.hovered_settings = h_settings
        self.hovered_credits = h_credits
        self.hovered_quit = h_quit
        
        if any_new_hover:
            audio.play("hover")
                
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 업데이트 알림 클릭 → 다운로드(릴리스) 페이지 열기
                if self._update_rect and self._update_rect.collidepoint(event.pos):
                    audio.play("click")
                    updater.open_download_page()
                    continue
                # 이스터에그: 달 4연타 → 악)몽중농원 토글
                if self.moon_rect.collidepoint(event.pos) and not _version.DEMO:
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
                    if _version.DEMO:
                        game_state.crop = "carrot"
                        game_state.nightmare = False
                        game_state.challenge = None
                        game_state.current_scene = "name_input"
                    elif save_system.crops_unlocked():
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
                # 에필로그 — 아버지의 새벽
                elif getattr(self, "hovered_epilogue", False) and self.show_epilogue:
                    audio.play("epiphany")
                    game_state.current_scene = "epilogue"
                # 설정
                elif self.hovered_settings:
                    audio.play("click")
                    game_state.request_settings = True
                # 제작진(크레딧)
                elif self.hovered_credits:
                    audio.play("click")
                    game_state.current_scene = "credits"
                # 끝내기
                elif self.hovered_quit:
                    audio.play("click")
                    game_state.request_quit = True
            elif event.type == pygame.KEYDOWN:
                # Enter/Space: 세이브가 있으면 '이어하기'(진행 보호 — 실수로 새 게임을 시작해
                # 자동저장이 기존 밭을 덮는 사고 방지), 없으면 '새 게임 시작'.
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if save_system.has_save():
                        audio.play("success")
                        game_state.request_load = True
                    else:
                        audio.play("click")
                        if _version.DEMO:
                            game_state.crop = "carrot"
                            game_state.nightmare = False
                            game_state.challenge = None
                            game_state.current_scene = "name_input"
                        elif save_system.crops_unlocked():
                            game_state.current_scene = "crop_select"
                        else:
                            game_state.crop = "carrot"
                            game_state.nightmare = False
                            game_state.current_scene = "name_input"

    def update(self, dt):
        self.firefly_emitter.update(dt)

        # 유성 — 6~14초에 한 번, 하늘 위쪽을 비스듬히 가른다
        if self.shoot is None:
            self.shoot_timer -= dt
            if self.shoot_timer <= 0:
                self.shoot = {"x": random.uniform(60, 520), "y": random.uniform(26, 110),
                              "vx": random.uniform(210, 300), "vy": random.uniform(70, 110),
                              "life": 0.9}
        else:
            s = self.shoot
            s["x"] += s["vx"] * dt
            s["y"] += s["vy"] * dt
            s["life"] -= dt
            if s["life"] <= 0 or s["x"] > 820 or s["y"] > 240:
                self.shoot = None
                self.shoot_timer = random.uniform(6.0, 14.0)

    def draw(self, screen):
        # 1. 배경 (달 이스터에그로 악몽 모드가 켜지면 검붉게)
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")
        
        # 2. 반딧불이 그리기
        self.firefly_emitter.draw(screen)

        # 2-1. 유성 — 진행 반대 방향으로 점점 작고 어두워지는 도트 꼬리 (어두운 하늘 위라 알파 불필요)
        if self.shoot:
            s = self.shoot
            col = (255, 120, 110) if game_state.nightmare else (255, 244, 214)
            fade = max(0.0, min(1.0, s["life"] / 0.9))
            for i in range(6):
                t = i / 6.0
                bx = int(s["x"] - s["vx"] * 0.085 * i)
                by = int(s["y"] - s["vy"] * 0.085 * i)
                k = fade * (1.0 - t)
                c = (int(col[0] * k), int(col[1] * k), int(col[2] * k))
                sz = 3 if i < 2 else 2
                pygame.draw.rect(screen, c, (bx, by, sz, sz))
            
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

        # 업데이트 알림 — 새 버전이 있으면 작은 알림(클릭하면 다운로드 페이지가 열린다)
        self._update_rect = None
        if updater.available:
            un = get_font(14).render(i18n.tf("새 버전 {v} · 다운로드", v=updater.available), True, (255, 236, 176))
            rect = pygame.Rect(0, 0, un.get_width() + 22, un.get_height() + 8)
            rect.center = (400, 202)
            self._update_rect = rect
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            bg = pygame.Surface(rect.size, pygame.SRCALPHA)
            # 챔퍼 6은 이 높이(26px)에선 과해서 1px 테두리 세로변이 '[ ]'처럼 떨어져 보였다
            pixel_rect(bg, (44, 78, 60, 235) if hovered else (32, 56, 46, 215), bg.get_rect(), chamfer=CHAMFER_SM)
            pixel_rect(bg, (150, 210, 170, 235), bg.get_rect(), width=1, chamfer=CHAMFER_SM)
            screen.blit(bg, rect.topleft)
            screen.blit(un, (rect.x + 11, rect.y + 4))

        # 4. 버튼들 그리기
        draw_button(screen, self.start_btn, "새 게임 시작", self.font_button, hovered=self.hovered_start)
        
        # 불러오기 버튼 (저장 데이터 여부에 따라 비활성화 묘사)
        has_save = save_system.has_save()
        if has_save:
            draw_button(screen, self.load_btn, "이어하기", self.font_button, hovered=self.hovered_load)
        else:
            # 비활성화된 모양 — 무채색 회색은 웜톤 팔레트에서 겉돌아 따뜻한 저채도 갈색으로
            pixel_rect(screen, (88, 80, 70), self.load_btn, chamfer=CHAMFER)
            pixel_rect(screen, (122, 110, 94), self.load_btn, width=1, chamfer=CHAMFER)
            label = self.font_button.render("이어하기", True, (156, 144, 128))
            screen.blit(label, (self.load_btn.centerx - label.get_width() // 2, self.load_btn.centery - label.get_height() // 2))
            
        if self.show_gallery:
            draw_button(screen, self.gallery_btn, "추억 갤러리", self.font_button, hovered=self.hovered_gallery)

        if self.show_epilogue:
            draw_button(screen, self.epilogue_btn, "아버지의 새벽", self.font_button,
                        hovered=getattr(self, "hovered_epilogue", False))

        # 보조 기능은 작은 버튼 한 줄로 (설정 · 제작진 · 끝내기)
        draw_button(screen, self.settings_btn, "설정", self.font_util, hovered=self.hovered_settings)
        draw_button(screen, self.credits_btn, "제작진", self.font_util, hovered=self.hovered_credits)
        draw_button(screen, self.quit_btn, "끝내기", self.font_util, hovered=self.hovered_quit)

        # 5. 체험판 안내 (데모 빌드에서만)
        if _version.DEMO:
            demo_surf = get_font(14).render(
                "체험판 — 정식판에는 세 가지 작물과 아버지의 새벽이 더 기다립니다", True, (255, 226, 180))
            screen.blit(demo_surf, (400 - demo_surf.get_width() // 2, 548))

        # 6. 저작권 표시 — 연도·제작팀 명시. 어두운 배경 위 저대비 + 지형 라인이 글자를 관통해
        # 안 읽히던 것 → 밝기 올리고 얇은 그림자를 깔아 분리한다
        cr_font = get_font(13)
        cr_col = (168, 158, 146) if game_state.nightmare else (188, 178, 160)
        cr_text = "© 2026 삼광 (三光). All Rights Reserved."
        cr_sh = cr_font.render(cr_text, True, (24, 22, 26))
        cr_surf = cr_font.render(cr_text, True, cr_col)
        screen.blit(cr_sh, (400 - cr_surf.get_width() // 2 + 1, 575))
        screen.blit(cr_surf, (400 - cr_surf.get_width() // 2, 574))
