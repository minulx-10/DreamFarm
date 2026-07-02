import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE, GOLD, PANEL_WARM, PANEL_EDGE
from core.ui import draw_light_panel, draw_story_backdrop, draw_button, wrap_text, mix_color, draw_panel
from core import audio
from core import save_system
from core.crops import CROPS

class CropSelectScene:
    def __init__(self):
        self.font_title = get_font(28)
        self.font_name = get_font(20)
        self.font_desc = get_font(13)
        self.font_btn = get_font(18)
        
        self.selected_crop = game_state.crop or "carrot"
        self.nightmare_mode = False
        
        # 4개 작물 카드 Rect 정의
        # 800x600 화면에 가로로 4장 정렬 (간격 20, 좌우 여백 40, 너비 160, 높이 230)
        self.cards = {
            "carrot": pygame.Rect(40, 150, 160, 230),
            "apple": pygame.Rect(220, 150, 160, 230),
            "potato": pygame.Rect(400, 150, 160, 230),
            "rice": pygame.Rect(580, 150, 160, 230)
        }
        
        # 악몽 체크박스 Rect
        self.nightmare_rect = pygame.Rect(280, 410, 240, 36)
        
        # 확인 버튼 Rect
        self.confirm_btn = pygame.Rect(300, 500, 200, 48)
        
        self.hovered_card = None
        self.hovered_nightmare = False
        self.hovered_confirm = False

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
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 카드 클릭
                if self.hovered_card:
                    audio.play("click")
                    self.selected_crop = self.hovered_card
                # 악몽 체크박스 클릭 (진엔딩 달성시에만 해금)
                elif self.hovered_nightmare and save_system.nightmare_unlocked():
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
        # 1. 배경 (밤하늘)
        draw_story_backdrop(screen, "night")
        
        # 2. 타이틀 텍스트
        title_surf = self.font_title.render("기르고자 하는 작물 선택", True, WHITE)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 60))
        
        desc_top = get_font(15).render("회차마다 다른 작물을 길러 아버지의 시간을 깊이 들여다보세요.", True, TEXT_MUTED)
        screen.blit(desc_top, (400 - desc_top.get_width() // 2, 105))
        
        # 3. 작물 카드 그리기
        for key, rect in self.cards.items():
            info = CROPS[key]
            is_selected = (self.selected_crop == key)
            is_hovered = (self.hovered_card == key)
            
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
            fam_surf = get_font(12).render(f"분류: {info['family']}", True, TEXT_MUTED)
            screen.blit(fam_surf, (rect.centerx - fam_surf.get_width() // 2, rect.bottom - 22))

        # 4. [악)몽중농원] 모드 체크박스 (진엔딩 해금시에만 표시)
        if save_system.nightmare_unlocked():
            box_color = (255, 230, 220) if self.hovered_nightmare else (240, 210, 200)
            border_color = (200, 50, 50) if self.nightmare_mode else (130, 80, 80)
            
            draw_panel(screen, self.nightmare_rect, fill=box_color, border=border_color, radius=6, shadow=self.hovered_nightmare)
            
            # 체크 여부에 따른 표시
            check_char = "✓" if self.nightmare_mode else " "
            check_surf = self.font_name.render(check_char, True, (200, 30, 30))
            screen.blit(check_surf, (self.nightmare_rect.x + 10, self.nightmare_rect.y + 5))
            
            label_surf = self.font_btn.render("[악)몽중농원] 활성화 (지옥 모드)", True, (139, 30, 30) if self.nightmare_mode else TEXT_DARK)
            screen.blit(label_surf, (self.nightmare_rect.x + 36, self.nightmare_rect.y + 8))
            
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
