import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, GOLD, WHITE
from core.ui import draw_light_panel, draw_story_backdrop, draw_button
from core import audio

class NameInputScene:
    def __init__(self):
        self.font_large = get_font(36)
        self.font_small = get_font(24)
        self.font_btn = get_font(20)
        self.input_text = ""
        self.ime_text = ""

        # '시작하기' 입력 완료 버튼 Rect
        self.start_btn = pygame.Rect(310, 355, 180, 44)
        self.hovered = False
        # 뒤로가기 버튼 (좌상단) — 작물 선택으로 돌아간다
        self.back_btn = pygame.Rect(24, 22, 104, 34)
        self.hovered_back = False
        # 빈 이름으로 진행하려 할 때 잠깐 뜨는 경고
        self.warn_timer = 0.0

        pygame.key.start_text_input()
        pygame.key.set_text_input_rect(pygame.Rect(250, 280, 300, 50))
        # 백스페이스를 꾹 누르고 있을 때 연속 삭제가 지원되도록 키 반복 입력 활성화 (딜레이 450ms, 주기 50ms)
        pygame.key.set_repeat(450, 50)

    def _try_start(self):
        """이름이 채워져 있으면 진행하고, 비어 있으면 경고를 띄운다."""
        if len(self.input_text.strip()) > 0 and len(self.ime_text) == 0:
            audio.play("success")
            game_state.player_name = self.input_text.strip()
            from core import achievements
            achievements.on_name(game_state.player_name)   # 개발자 이름 이스터에그
            game_state.current_scene = "intro"
            pygame.key.set_repeat(0)         # 키 반복 입력 비활성화
            pygame.key.stop_text_input()
        else:
            audio.play("break")
            self.warn_timer = 2.2            # "이름을 입력해 주세요" 경고 표시

    def _go_back(self):
        audio.play("click")
        pygame.key.set_repeat(0)
        pygame.key.stop_text_input()
        # 첫 회차(작물 미해금)에는 타이틀에서 작물을 carrot으로 고정한 뒤 바로 여기로 온다.
        # 이 경우 작물 선택 화면이 없으므로 돌아가기는 타이틀로 보내야 한다.
        from core import save_system
        game_state.current_scene = "crop_select" if save_system.crops_unlocked() else "title"

    def handle_events(self, events):
        mouse_pos = pygame.mouse.get_pos()
        new_hover = self.start_btn.collidepoint(mouse_pos)
        if new_hover != self.hovered:
            self.hovered = new_hover
            if self.hovered:
                audio.play("hover")
        self.hovered_back = self.back_btn.collidepoint(mouse_pos)

        for event in events:
            if event.type == pygame.TEXTEDITING:
                if len(self.input_text) + len(event.text) <= 8:
                    self.ime_text = event.text
                else:
                    self.ime_text = event.text[:max(0, 8 - len(self.input_text))]
            elif event.type == pygame.TEXTINPUT:
                if len(self.input_text) + len(event.text) <= 8:
                    self.input_text += event.text
                    audio.type_tick(event.text)
                    self.warn_timer = 0.0
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_btn.collidepoint(event.pos):
                    self._go_back()
                elif self.start_btn.collidepoint(event.pos):
                    self._try_start()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self._try_start()
                elif event.key == pygame.K_ESCAPE:
                    self._go_back()
                elif event.key == pygame.K_BACKSPACE:
                    if len(self.ime_text) == 0:
                        if len(self.input_text) > 0:
                            self.input_text = self.input_text[:-1]
                            audio.play("click")

    def update(self, dt):
        if self.warn_timer > 0:
            self.warn_timer -= dt

    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")

        # 뒤로가기 버튼
        draw_button(screen, self.back_btn, "돌아가기", self.font_btn, hovered=self.hovered_back)

        card = pygame.Rect(160, 140, 480, 310)
        draw_light_panel(screen, card)

        prompt = self.font_large.render("꿈속 밭에 남길 이름은?", True, TEXT_DARK)
        screen.blit(prompt, (400 - prompt.get_width()//2, 185))

        input_rect = pygame.Rect(230, 260, 340, 58)
        pygame.draw.rect(screen, (255, 249, 230), input_rect, border_radius=8)
        pygame.draw.rect(screen, (109, 84, 60), input_rect, 2, border_radius=8)
        
        display_text = self.input_text + self.ime_text
        if not display_text:
            name_surf = self.font_large.render("이름", True, TEXT_MUTED)
            screen.blit(name_surf, (input_rect.x + 14, input_rect.y + 8))
            cursor_x = input_rect.x + 14
        else:
            name_surf = self.font_large.render(display_text, True, GOLD)
            screen.blit(name_surf, (input_rect.x + 14, input_rect.y + 8))
            cursor_x = input_rect.x + 14 + self.font_large.size(display_text)[0]

        # Draw smooth vertical line cursor instead of appending text characters
        if pygame.time.get_ticks() % 1000 < 500:
            pygame.draw.line(screen, (109, 84, 60), (cursor_x, input_rect.y + 12), (cursor_x, input_rect.bottom - 12), 2)

        # 시작하기 완료 버튼 그리기
        draw_button(screen, self.start_btn, "시작하기", self.font_btn, hovered=self.hovered)

        if self.warn_timer > 0:
            warn = self.font_small.render("이름을 입력해 주세요!", True, (206, 70, 60))
            screen.blit(warn, (400 - warn.get_width()//2, 412))
        else:
            desc = self.font_small.render("Enter 키로도 입력 완료 가능", True, TEXT_MUTED)
            screen.blit(desc, (400 - desc.get_width()//2, 412))

        shine = self.font_small.render("몽중농원", True, WHITE)
        screen.blit(shine, (400 - shine.get_width() // 2, 85))

