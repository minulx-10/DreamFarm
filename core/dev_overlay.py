"""개발자/테스트 모드 오버레이.

F9로 열고 닫는다. 씬 점프·작물 변경·성장/이해도 조정·이벤트 강제 실행 등으로
특정 부분만 빠르게 테스트할 수 있다. 릴리스 빌드에서도 숨은 기능으로 남겨 둔다.
main 루프가 settings_overlay와 같은 방식으로 handle_events/draw를 불러 준다.
"""

import pygame

from core import audio
from core import i18n
from core.assets import get_font, WHITE, TEXT_DARK
from core.ui import draw_panel, mix_color
from core.game_state import game_state, STORY_EVENTS


class DevOverlay:
    def __init__(self):
        self.open = False
        self.panel = pygame.Rect(150, 60, 500, 480)
        self._buttons = []   # (rect, label, action)
        self.msg = ""

    # ------------------------------------------------------------------ 입력
    def handle_events(self, events, farm_scene=None):
        consumed = False
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                self.open = not self.open
                self.msg = ""
                consumed = True
                continue
            if not self.open:
                continue
            consumed = True
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.open = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, _label, action in self._buttons:
                    if rect.collidepoint(event.pos):
                        audio.play("click")
                        action(farm_scene)
                        break
        return consumed

    # ------------------------------------------------------------------ 동작
    def _set_crop(self, crop):
        def act(farm):
            game_state.crop = crop
            game_state.dev_new_farm = True   # main이 밭을 새로 만들고 farm으로 이동
            self.msg = i18n.tf("작물 → {crop} (새 밭)", crop=crop)
        return act

    def _goto(self, scene, setup=None):
        def act(farm):
            if setup:
                setup(farm)
            game_state.current_scene = scene
            self.msg = i18n.tf("이동 → {scene}", scene=scene)
        return act

    def _grow(self, amount):
        def act(farm):
            if farm is not None and getattr(farm, "sim", None) is not None:
                farm.sim.growth = max(0, min(farm.sim.growth_goal, farm.sim.growth + amount))
                self.msg = i18n.tf("성장 {a}/{b}", a=farm.sim.growth, b=farm.sim.growth_goal)
        return act

    def _harvest_ready(self, farm):
        if farm is not None and getattr(farm, "sim", None) is not None:
            farm.sim.growth = farm.sim.growth_goal
            self.msg = "수확 가능 상태로"

    def _und(self, amount):
        def act(farm):
            game_state.understanding = max(0, game_state.understanding + amount)
            self.msg = i18n.tf("이해도 {n}", n=game_state.understanding)
        return act

    def _toggle_nightmare(self, farm):
        game_state.nightmare = not game_state.nightmare
        self.msg = i18n.tf("악몽 {state}", state='ON' if game_state.nightmare else 'OFF')

    def _force_story(self, farm):
        import random
        game_state.choice_data = random.choice(STORY_EVENTS)
        game_state.current_scene = "story_choice"
        self.msg = "선택형 이벤트 강제"

    def _force_epiphany(self, farm):
        game_state.pending_epiphany = "…무언가 마음에 스친다."
        game_state.current_scene = "epiphany"

    def _goto_harvest(self, farm):
        game_state.timer = 30
        game_state.score = 0
        game_state.current_scene = "stage4"

    def _goto_star(self, farm):
        game_state.return_scene = "farm"
        game_state.current_scene = "star_connect"

    # ------------------------------------------------------------------ 그리기
    def draw(self, screen):
        if not self.open:
            return
        veil = pygame.Surface((800, 600), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        screen.blit(veil, (0, 0))
        draw_panel(screen, self.panel, fill=(34, 40, 46), border=(120, 200, 150), radius=10)
        title = get_font(20).render("개발자 모드  (F9로 닫기)", True, (150, 230, 170))
        screen.blit(title, (self.panel.centerx - title.get_width() // 2, self.panel.y + 14))

        rows = [
            ("작물", [("당근", self._set_crop("carrot")), ("사과나무", self._set_crop("apple")),
                     ("감자", self._set_crop("potato")), ("벼", self._set_crop("rice"))]),
            ("성장", [("성장 +5", self._grow(5)), ("성장 -5", self._grow(-5)),
                     ("수확가능", self._harvest_ready), ("이해도 +10", self._und(10))]),
            ("모드", [("악몽 토글", self._toggle_nightmare), ("이해도 +30", self._und(30))]),
            ("씬 점프", [("밭", self._goto("farm")), ("수확", self._goto_harvest),
                       ("엔딩", self._goto("ending")), ("갤러리", self._goto("gallery"))]),
            ("이벤트", [("별잇기", self._goto_star), ("선택이벤트", self._force_story),
                      ("아버지날", self._goto("father_day")), ("깨달음", self._force_epiphany)]),
        ]

        self._buttons = []
        font = get_font(15)
        y = self.panel.y + 52
        for label, btns in rows:
            lab = get_font(13).render(label, True, (170, 200, 180))
            screen.blit(lab, (self.panel.x + 20, y + 8))
            bx = self.panel.x + 96
            for text, action in btns:
                rect = pygame.Rect(bx, y, 92, 34)
                hov = rect.collidepoint(pygame.mouse.get_pos())
                fill = (86, 120, 96) if hov else (58, 74, 66)
                draw_panel(screen, rect, fill=fill, border=(120, 170, 140), radius=7, shadow=False)
                # 라벨이 길면(영어 등) 버튼 폭에 맞춰 폰트 축소
                bf = font
                for sz in (15, 13, 11, 10):
                    bf = get_font(sz)
                    if bf.size(text)[0] <= rect.width - 6:
                        break
                ts = bf.render(text, True, WHITE)
                screen.blit(ts, (rect.centerx - ts.get_width() // 2, rect.centery - ts.get_height() // 2))
                self._buttons.append((rect, text, action))
                bx += 98
            y += 44

        if self.msg:
            m = get_font(14).render(self.msg, True, (230, 220, 160))
            screen.blit(m, (self.panel.centerx - m.get_width() // 2, self.panel.bottom - 30))
