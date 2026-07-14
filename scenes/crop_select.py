import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE, GOLD, PANEL_WARM, PANEL_EDGE
from core.ui import draw_light_panel, draw_story_backdrop, draw_button, wrap_text, mix_color, draw_panel
from core import audio
from core import save_system
from core import i18n
from core.crops import CROPS

class CropSelectScene:
    def __init__(self):
        self.font_title = get_font(28)
        self.font_name = get_font(20)
        self.font_desc = get_font(13)
        self.font_btn = get_font(18)
        
        self.selected_crop = game_state.crop or "carrot"
        # 달 이스터에그 등으로 악몽 모드가 켜져 있으면 체크박스도 기본으로 켜 둔다.
        self.nightmare_mode = game_state.nightmare
        
        # 4개 작물 카드 Rect 정의
        # 800x600 화면에 가로로 4장 정렬 (간격 20, 좌우 여백 40, 너비 160, 높이 230)
        self.cards = {
            "carrot": pygame.Rect(40, 150, 160, 230),
            "apple": pygame.Rect(220, 150, 160, 230),
            "potato": pygame.Rect(400, 150, 160, 230),
            "rice": pygame.Rect(580, 150, 160, 230)
        }
        
        # 악몽 체크박스 Rect (라벨이 길어 넉넉히, 화면 중앙 정렬)
        self.nightmare_rect = pygame.Rect(200, 406, 400, 40)
        
        # 확인 버튼 Rect
        self.confirm_btn = pygame.Rect(300, 500, 200, 48)

        # 뒤로가기 버튼 (좌상단)
        self.back_btn = pygame.Rect(24, 22, 104, 34)

        self.hovered_card = None
        self.hovered_nightmare = False
        self.hovered_confirm = False
        self.hovered_back = False

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        
        # 호버 갱신
        self.hovered_card = None
        for key, rect in self.cards.items():
            if rect.collidepoint(mouse_pos):
                self.hovered_card = key
                break
                
        self.hovered_nightmare = self.nightmare_rect.collidepoint(mouse_pos)
        self.hovered_confirm = self.confirm_btn.collidepoint(mouse_pos)
        self.hovered_back = self.back_btn.collidepoint(mouse_pos)

        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                audio.play("click")
                game_state.current_scene = "title"
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 뒤로가기 → 타이틀
                if self.hovered_back:
                    audio.play("click")
                    game_state.current_scene = "title"
                    return
                # 카드 클릭
                if self.hovered_card:
                    audio.play("click")
                    self.selected_crop = self.hovered_card
                # 악몽 체크박스 클릭 (진엔딩 달성시에만 해금)
                elif self.hovered_nightmare and (save_system.nightmare_unlocked() or self.nightmare_mode):
                    audio.play("click")
                    self.nightmare_mode = not self.nightmare_mode
                # 확인 버튼 클릭
                elif self.hovered_confirm:
                    audio.play("success")
                    game_state.crop = self.selected_crop
                    game_state.nightmare = self.nightmare_mode
                    game_state.current_scene = "name_input"

    def update(self, dt):
        pass

    def draw(self, screen):
        # 1. 배경 (밤하늘 / 악몽 모드 활성화 시 악몽 하늘)
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")
        
        # 2. 안내 문구 — 우측 상단의 달/태양(이스터에그)을 전혀 가리지 않도록 2줄로 나누어 컴팩트하게 배치
        line1 = get_font(18).render("회차마다 다른 작물을 길러", True, WHITE)
        line2 = get_font(18).render("아버지의 시간을 깊이 들여다보세요", True, (255, 230, 180)) # 가독성 좋은 따뜻한 오프화이트/금빛 강조
        screen.blit(line1, (400 - line1.get_width() // 2, 64))
        screen.blit(line2, (400 - line2.get_width() // 2, 90))
        
        # 3. 작물 카드 그리기
        clears = save_system.crop_clears()
        for key, rect in self.cards.items():
            info = CROPS[key]
            is_selected = (self.selected_crop == key)
            is_hovered = (self.hovered_card == key)

            # 각 작물 카드 위에 클리어(수확 성공) 횟수 배지
            cnt = clears.get(key, 0)
            badge_font = get_font(12)
            if cnt > 0:
                btxt = badge_font.render(i18n.tf("클리어 {cnt}회", cnt=cnt), True, (74, 52, 34))
                bg = (232, 205, 130)
                bw, bh = btxt.get_width() + 16, btxt.get_height() + 6
            else:
                btxt = badge_font.render("미클리어", True, (150, 145, 135))
                bg = (222, 216, 206)
                bw, bh = btxt.get_width() + 16, btxt.get_height() + 6
            badge = pygame.Rect(rect.centerx - bw // 2, rect.y - bh - 6, bw, bh)
            draw_panel(screen, badge, fill=bg, border=mix_color(bg, (0, 0, 0), 0.25), radius=8, shadow=False)
            screen.blit(btxt, (badge.centerx - btxt.get_width() // 2, badge.centery - btxt.get_height() // 2))
            
            # 카드 배경 & 테두리 색상 분기
            if is_selected:
                fill_color = (255, 236, 188)
                border_color = (212, 140, 60)
            elif is_hovered:
                fill_color = mix_color(PANEL_WARM, WHITE, 0.2)
                border_color = PANEL_EDGE
            else:
                fill_color = PANEL_WARM
                border_color = PANEL_EDGE
                
            draw_panel(screen, rect, fill=fill_color, border=border_color, radius=10, shadow=is_hovered or is_selected)
            
            # 작물 이름
            name_surf = self.font_name.render(info["name"], True, TEXT_DARK)
            screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2, rect.y + 18))
            
            # 구분선
            pygame.draw.line(screen, (180, 160, 130), (rect.x + 20, rect.y + 45), (rect.right - 20, rect.y + 45), 1)
            
            # 작물 설명 줄바꿈 렌더링
            desc_lines = wrap_text(info["desc"], self.font_desc, rect.w - 24)
            y = rect.y + 60
            for line in desc_lines:
                line_surf = self.font_desc.render(line, True, TEXT_DARK)
                screen.blit(line_surf, (rect.x + 12, y))
                y += 20
                
            # 작물 유형 정보 표기 (하단 배치)
            fam_surf = get_font(12).render(i18n.tf("분류: {family}", family=i18n.t(info['family'])), True, TEXT_MUTED)
            screen.blit(fam_surf, (rect.centerx - fam_surf.get_width() // 2, rect.bottom - 22))

        # 4. [악)몽중농원] 모드 체크박스 (진엔딩 해금 또는 달 이스터에그로 켜졌을 때 표시)
        if save_system.nightmare_unlocked() or self.nightmare_mode:
            box_color = (255, 230, 220) if self.hovered_nightmare else (240, 210, 200)
            border_color = (200, 50, 50) if self.nightmare_mode else (130, 80, 80)
            
            draw_panel(screen, self.nightmare_rect, fill=box_color, border=border_color, radius=6, shadow=self.hovered_nightmare)

            # 체크 박스 + 라벨을 하나의 묶음으로 박스 안에서 가운데 정렬 (텍스트 잘림 방지)
            r = self.nightmare_rect
            label_font = get_font(16)
            check_char = "✓" if self.nightmare_mode else "□"
            check_surf = label_font.render(check_char, True, (200, 30, 30))
            label_surf = label_font.render("[악)몽중농원] 활성화 (지옥 모드)",
                                           True, (139, 30, 30) if self.nightmare_mode else TEXT_DARK)
            gap = 8
            total_w = check_surf.get_width() + gap + label_surf.get_width()
            start_x = r.centerx - total_w // 2
            cy = r.centery
            screen.blit(check_surf, (start_x, cy - check_surf.get_height() // 2))
            screen.blit(label_surf, (start_x + check_surf.get_width() + gap, cy - label_surf.get_height() // 2))
            
            # 설명구
            warn_text = "음식을 남기면 지옥에서 다 먹어야 합니다. 검붉은 밭에서 시작합니다."
            warn_surf = get_font(13).render(warn_text, True, (200, 100, 100))
            screen.blit(warn_surf, (400 - warn_surf.get_width() // 2, 452))
        else:
            # 진엔딩 미해금 안내
            lock_surf = get_font(13).render("(진엔딩 클리어 시 악)몽중농원 지옥 모드가 개방됩니다)", True, TEXT_MUTED)
            screen.blit(lock_surf, (400 - lock_surf.get_width() // 2, 430))

        # 5. 확인 버튼
        draw_button(screen, self.confirm_btn, "선택 완료", self.font_btn, hovered=self.hovered_confirm)

        # 6. 뒤로가기 버튼 (좌상단)
        draw_button(screen, self.back_btn, "돌아가기", get_font(15), hovered=self.hovered_back)
