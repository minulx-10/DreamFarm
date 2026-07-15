import pygame
import random
from core.game_state import game_state, get_season_colors
from core.assets import get_font
from core import audio
from core import save_system
from core import i18n
from core.ui import draw_button
from scenes.tending import WaterPour, WeedPull, PestTap, SoilMound

# 행동 -> 손맛 인터랙션 클래스
TACTILE_INTERACTIONS = {
    "물 주기": WaterPour,
    "잡초 뽑기": WeedPull,
    "해충 살피기": PestTap,
    "흙 북돋기": SoilMound,
}


class Button:
    def __init__(self, x, y, w, h, text, value, font_size=20, kind="normal"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.value = value
        self.font = get_font(font_size)
        self.hovered = False
        self.kind = kind

    def draw(self, screen):
        if self.kind == "close":
            base = (86, 78, 70) if not self.hovered else (110, 100, 90)
            r = self.rect
            pygame.draw.rect(screen, base, r, border_radius=r.height // 2)
            pygame.draw.rect(screen, (150, 138, 126), r, 1, border_radius=r.height // 2)
            surf = self.font.render("✕ " + self.text, True, (236, 228, 214))
            screen.blit(surf, (r.centerx - surf.get_width() // 2,
                               r.centery - surf.get_height() // 2))
            return
        draw_button(screen, self.rect, self.text, self.font, hovered=self.hovered)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class FarmScene:
    TUTORIAL_PAGES = [
        ("꿈속의 밭에 도착했습니다",
         "오른쪽의 여섯 스탯으로 밭의 상태를 읽으세요. "
         "수분·건강·잡초·해충·배수·스트레스 — 이 모든 것이 당근의 건강을 좌우합니다."),
        ("밭일은 직접 손으로",
         "'행동하기'에서 할 일을 고르면, 물 주기·잡초·해충은 밭에서 직접 합니다. "
         "물은 꾹 눌러 붓고, 잡초는 잡아 쭉 끌어내고, 벌레는 톡톡 쳐서 잡으세요. "
         "그때그때 화면이 방법을 알려줍니다."),
        ("정답은 알려주지 않습니다",
         "아래 '농장 일지'는 밭의 증상만 알려줄 뿐, 무엇을 할지는 직접 판단해야 합니다. "
         "막막하면 '살펴보기'로 정밀 진단과 날씨 예보를 받을 수 있어요."),
        ("서두르지 마세요",
         "작물은 제대로 된 돌봄과, 밭이 평온할 때의 '기다리기'에서 자랍니다. "
         "조급함은 당근을 상하게 합니다.  (M 키: 음소거)"),
    ]

    def __init__(self):
        from scenes.farm_simulator import FarmSimulator
        from scenes.farm_renderer import FarmRenderer
        
        self.sim = FarmSimulator()
        self.renderer = FarmRenderer()
        
        # UI 및 반딧불이 애니메이션용 설정
        self.season_colors = get_season_colors(self.sim.growth, self.sim.growth_goal)
        self.buttons = []
        self.action_menu_open = False
        self.action_scroll = 0
        self.scrollbar_dragging = False
        
        self.interaction = None
        self.interaction_action = None
        self.interactions_enabled = True
        
        self.forced_wait_active = False
        self.forced_wait_timer = 0.0
        
        self.fireflies = []
        for _ in range(18):
            self.fireflies.append({
                'x': random.randint(10, 790),
                'y': random.randint(20, 160),
                'speed_x': random.uniform(-12.0, 12.0),
                'speed_y': random.uniform(-6.0, 6.0),
                'scale_timer': random.uniform(0.0, 6.28),
                'size': random.uniform(2.0, 4.5)
            })

        self.tutorial_step = 0
        self.tutorial_active = not game_state.is_second_run
        self.last_hover_value = None
        
        self.rebuild_buttons()

    def rebuild_buttons(self):
        self.buttons = []
        start_x = 440
        start_y = 330
        if self.sim.is_harvest_ready():
            self.buttons.append(Button(start_x, start_y, 300, 126, "수확하기", "수확하기", font_size=30))
            return

        if self.sim.turns_since_wait >= 5:
            self.buttons.append(Button(start_x, start_y, 300, 126, "강제 기다리기 (돌발 상황 해결)", "__forced_wait__", font_size=24))
            return

        if not self.action_menu_open:
            self.buttons.append(Button(start_x, start_y, 300, 80, "행동하기", "__open_actions__", font_size=28))
            self.buttons.append(Button(start_x, start_y + 86, 300, 40, "기다리기", "기다리기", font_size=20))
            return

        actions = self.sim.get_action_choices()
        max_scroll = max(0, len(actions) - 4)
        self.action_scroll = max(0, min(self.action_scroll, max_scroll))
        for i, action in enumerate(actions[self.action_scroll:self.action_scroll + 4]):
            by = start_y + i * 31
            self.buttons.append(Button(start_x, by, 284, 28, self.sim.action_label(action), action, font_size=17))

        self.buttons.append(Button(start_x + 90, start_y + 126, 120, 22,
                                   "닫기", "__close_actions__", font_size=14, kind="close"))

    def drag_scrollbar(self, mouse_y):
        actions = self.sim.get_action_choices()
        if len(actions) <= 4:
            return
        track_y = 330
        track_h = 121
        thumb_h = max(22, int(track_h * 4 / len(actions)))
        max_scroll = max(1, len(actions) - 4)
        relative_y = mouse_y - track_y - thumb_h / 2
        ratio = max(0.0, min(1.0, relative_y / (track_h - thumb_h)))
        self.action_scroll = int(ratio * max_scroll)
        self.rebuild_buttons()

    def handle_events(self, events):
        if self.interaction:
            for event in events:
                self.interaction.handle(event)
            return

        if self.tutorial_active:
            for event in events:
                advance = (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (
                    event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN))
                if advance:
                    audio.play("page")
                    self.tutorial_step += 1
                    if self.tutorial_step >= len(self.TUTORIAL_PAGES):
                        self.tutorial_active = False
            return

        for event in events:
            # 좁은 화면 '밭 수첩' 상단 팝업 토글 — 다른 처리보다 먼저 소비(넓은 화면엔 버튼 없음)
            if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                    and not getattr(self, "_dash_wide", True)):
                from scenes.farm_renderer import DASH_BTN
                if DASH_BTN.collidepoint(event.pos):
                    game_state.dashboard_open = not getattr(game_state, "dashboard_open", False)
                    audio.play("click")
                    continue

            if event.type == pygame.MOUSEWHEEL and self.action_menu_open:
                max_scroll = max(0, len(self.sim.get_action_choices()) - 4)
                self.action_scroll = max(0, min(max_scroll, self.action_scroll - event.y))
                self.rebuild_buttons()
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.action_menu_open:
                    track_rect_clickable = pygame.Rect(722, 330, 24, 121)
                    if track_rect_clickable.collidepoint(event.pos):
                        self.scrollbar_dragging = True
                        self.drag_scrollbar(event.pos[1])
                        continue

                clicked = False
                for btn in self.buttons:
                    if btn.is_clicked(event.pos):
                        clicked = True
                        if btn.value == "__open_actions__":
                            audio.play("click")
                            self.action_menu_open = True
                            self.action_scroll = 0
                            self.rebuild_buttons()
                        elif btn.value == "__close_actions__":
                            audio.play("click")
                            self.action_menu_open = False
                            self.rebuild_buttons()
                        elif btn.value == "__forced_wait__":
                            audio.play("click")
                            self.forced_wait_active = True
                            self.forced_wait_timer = 30.0
                            self.interaction_action = random.choice(["물 주기", "잡초 뽑기", "해충 살피기", "흙 북돋기"])
                            self.interaction = TACTILE_INTERACTIONS[self.interaction_action](self)
                            self.rebuild_buttons()
                        else:
                            self.action_menu_open = False
                            self.sim.do_action(btn.value, self)
                        break
                if self.action_menu_open and not clicked:
                    self.action_menu_open = False
                    self.rebuild_buttons()

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.scrollbar_dragging = False

            elif event.type == pygame.MOUSEMOTION:
                if self.scrollbar_dragging and self.action_menu_open:
                    self.drag_scrollbar(event.pos[1])

            elif event.type == pygame.MOUSEBUTTONDOWN and self.action_menu_open and event.button in (4, 5):
                max_scroll = max(0, len(self.sim.get_action_choices()) - 4)
                delta = -1 if event.button == 4 else 1
                self.action_scroll = max(0, min(max_scroll, self.action_scroll + delta))
                self.rebuild_buttons()

    def update(self, dt):
        if self.forced_wait_active:
            self.forced_wait_timer -= dt
            if self.forced_wait_timer <= 0:
                self.forced_wait_timer = 0.0
                self.forced_wait_active = False
                self.interaction = None
                audio.play("break")
                self.sim.health = max(0, self.sim.health - 15)
                self.sim.stress = min(100, self.sim.stress + 20)
                self.sim.mistakes += 1
                self.sim.turns_since_wait = 0
                self.sim.message = "돌발 상황을 제시간에 해결하지 못해 작물이 큰 충격을 받았습니다."
                self.sim.notice = "기다려야 할 때는 서두르지 말고 밭의 부름에 집중합시다."
                self.rebuild_buttons()
                if save_system.get_setting("autosave"):
                    save_system.save_game(self)
                return

        if self.interaction:
            self.interaction.update(dt)
            if self.interaction.done:
                result = self.interaction.result
                action = self.interaction_action
                self.interaction = None
                
                if self.forced_wait_active:
                    self.forced_wait_active = False
                    self.sim.turns_since_wait = 0
                    self.sim._run_action(action, self, result)
                    self.sim.message = i18n.tf("돌발 상황({action})을 30초 내에 무사히 해결했습니다!", action=i18n.t(action))
                    self.sim.notice = "기다림이 작물을 더 튼튼하게 만듭니다."
                    game_state.patience_score += 1
                    game_state.understanding += 4
                    if save_system.get_setting("autosave"):
                        save_system.save_game(self)
                elif result and "weather_bonus" in result:
                    bonus = result["weather_bonus"]
                    for stat, val in bonus.items():
                        cur = getattr(self.sim, stat, None)
                        if cur is not None:
                            setattr(self.sim, stat, cur + val)
                    self.sim.clamp_stats()
                    self.rebuild_buttons()
                else:
                    self.sim._run_action(action, self, result)
            return

        if not self.tutorial_active:
            mouse_pos = pygame.mouse.get_pos()
            new_hover = None
            for btn in self.buttons:
                btn.hovered = btn.rect.collidepoint(mouse_pos)
                if btn.hovered:
                    new_hover = btn.value
            if new_hover != self.last_hover_value:
                if new_hover is not None:
                    audio.play("hover")
                self.last_hover_value = new_hover

        for f in self.fireflies:
            f['x'] += f['speed_x'] * dt
            f['y'] += f['speed_y'] * dt
            f['scale_timer'] += 2.2 * dt
            if f['x'] < 10 or f['x'] > 790:
                f['speed_x'] *= -1
            if f['y'] < 20 or f['y'] > 160:
                f['speed_y'] *= -1

        if self.sim.thought_timer > 0:
            self.sim.thought_timer -= dt
            if self.sim.thought_timer <= 0:
                self.sim.thought_text = ""
        if not self.sim.thought_text and self.sim.thought_queue:
            self.sim.thought_text, dur = self.sim.thought_queue.pop(0)
            self.sim.thought_timer = dur

        if self.sim.health <= 0 or self.sim.weak_turns >= 7:
            self.sim._wilt(self)

    def draw(self, screen):
        self.renderer.draw(screen, self)

    def crop_positions(self):
        return self.renderer.crop_positions()
