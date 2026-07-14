import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, GOLD, WHITE
from core.ui import draw_light_panel, draw_story_backdrop, draw_button
from core.platform import IS_ANDROID
from core import audio

class NameInputScene:
    def __init__(self):
        self.font_large = get_font(36)
        self.font_small = get_font(24)
        self.font_btn = get_font(20)
        self.input_text = ""
        self.ime_text = ""

        # 안드로이드는 '소프트 키보드가 떠 있을 때만' 상단 배치로 바꾼다. 키보드 뜨기 전에는 PC처럼
        # 가운데 카드로 보여 주고(상하대칭), 입력칸을 탭하면 키보드를 띄우며 상단 절반으로 재배치한다.
        # 데스크톱은 처음부터 키보드가 있는 것으로 간주(바로 타이핑).
        self.kb_shown = not IS_ANDROID
        self._apply_layout()

        self.hovered = False
        self.back_btn = pygame.Rect(24, 22, 104, 34)   # 뒤로가기 (좌상단)
        self.hovered_back = False
        self.warn_timer = 0.0                           # 빈 이름 경고

        if not IS_ANDROID:
            pygame.key.start_text_input()
            pygame.key.set_text_input_rect(self.input_rect)
        # 백스페이스 꾹 눌러 연속 삭제 (딜레이 450ms, 주기 50ms)
        pygame.key.set_repeat(450, 50)

    def _apply_layout(self):
        """키보드 상태에 맞춰 입력칸·버튼 위치를 잡는다."""
        if IS_ANDROID and self.kb_shown:
            # 키보드가 화면 아래 절반을 덮으므로 위쪽 절반(≈0~300)에 상하대칭으로 배치
            self.input_rect = pygame.Rect(230, 128, 340, 56)
            self.start_btn = pygame.Rect(300, 206, 200, 48)
        else:
            # 데스크톱 / (안드로이드 키보드 뜨기 전): PC식 가운데 카드
            self.input_rect = pygame.Rect(230, 260, 340, 58)
            self.start_btn = pygame.Rect(310, 355, 180, 44)

    def _show_keyboard(self):
        """(안드로이드) 입력칸 탭 → 소프트 키보드를 띄우고 상단 배치로 전환."""
        if IS_ANDROID and not self.kb_shown:
            self.kb_shown = True
            self._apply_layout()
            audio.play("click")
        pygame.key.start_text_input()
        pygame.key.set_text_input_rect(self.input_rect)

    def _try_start(self):
        """이름이 채워져 있으면 진행하고, 비어 있으면 경고를 띄운다."""
        if len(self.input_text.strip()) > 0 and len(self.ime_text) == 0:
            audio.play("success")
            game_state.player_name = self.input_text.strip()
            from core import achievements
            achievements.on_name(game_state.player_name)   # 개발자 이름 이스터에그
            game_state.current_scene = "intro"
            pygame.key.set_repeat(0)
            pygame.key.stop_text_input()
        else:
            audio.play("break")
            self.warn_timer = 2.2

    def _go_back(self):
        audio.play("click")
        pygame.key.set_repeat(0)
        pygame.key.stop_text_input()
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
                elif self.input_rect.collidepoint(event.pos):
                    # (안드로이드) 입력칸 탭 → 키보드 띄우고 상단으로 재배치
                    self._show_keyboard()
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

    def _fit_font(self, text, max_w):
        """번역문이 길면 폭에 맞는 가장 큰 폰트를 고른다(영어가 길어 카드를 넘치는 것 방지)."""
        for sz in (36, 30, 26, 22):
            f = get_font(sz)
            if f.size(text)[0] <= max_w:   # size()도 현재 언어로 번역해 측정
                return f
        return get_font(20)

    def update(self, dt):
        if self.warn_timer > 0:
            self.warn_timer -= dt

    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")
        draw_button(screen, self.back_btn, "돌아가기", self.font_btn, hovered=self.hovered_back)

        prompt_text = "꿈속 밭에 남길 이름은?"
        android_top = IS_ANDROID and self.kb_shown
        if not android_top:
            # 데스크톱 / 안드로이드 키보드 뜨기 전 — PC식 가운데 카드
            card = pygame.Rect(160, 140, 480, 310)
            draw_light_panel(screen, card)
            pf = self._fit_font(prompt_text, 440)   # 카드 안에 맞춰 자동 축소
            prompt = pf.render(prompt_text, True, TEXT_DARK)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 200 - prompt.get_height() // 2))
        else:
            # 안드로이드 키보드 상태 — 상단 절반에 안내(가운데 카드는 키보드에 가림)
            pf = self._fit_font(prompt_text, 720)
            prompt = pf.render(prompt_text, True, WHITE)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 80))

        input_rect = self.input_rect
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

        if pygame.time.get_ticks() % 1000 < 500:
            pygame.draw.line(screen, (109, 84, 60), (cursor_x, input_rect.y + 12), (cursor_x, input_rect.bottom - 12), 2)

        label = "시작" if IS_ANDROID else "시작하기"
        draw_button(screen, self.start_btn, label, self.font_btn, hovered=self.hovered)

        # 안내 / 경고
        if android_top:
            if self.warn_timer > 0:
                warn = self.font_small.render("이름을 입력해 주세요!", True, (240, 150, 140))
                screen.blit(warn, (400 - warn.get_width() // 2, 268))
        else:
            if self.warn_timer > 0:
                msg = self.font_small.render("이름을 입력해 주세요!", True, (206, 70, 60))
            elif IS_ANDROID:
                msg = self.font_small.render("입력칸을 탭하여 이름을 입력하세요", True, TEXT_MUTED)
            else:
                msg = self.font_small.render("Enter 키로도 입력 완료 가능", True, TEXT_MUTED)
            screen.blit(msg, (400 - msg.get_width() // 2, 412))
            shine = self.font_small.render("몽중농원", True, WHITE)
            screen.blit(shine, (400 - shine.get_width() // 2, 85))
