import pygame
import random
import datetime
from core.game_state import (
    append_josa, game_state, pick_action_echo, pick_failure_echo,
    check_epiphany, advance_weather, get_understanding_stage,
    WEATHER_DATA, STORY_EVENTS, WEATHER_WISDOM, SILENT_GIFTS,
    pick_sensory, get_silent_gift, reveal_gift, check_recovery,
    track_attitude, get_season_colors, get_season,
    check_father_day,
)
from core.assets import *
from core import audio
from core import save_system
from core.crops import farm_config, swap_crop_word
from core.ui import (
    draw_light_panel, draw_panel, draw_wood_panel, draw_top_bar,
    draw_bottom_bar, draw_understanding_badge, draw_button, draw_meter_bar,
    wrap_text, mix_color,
)
from scenes.tending import WaterPour, WeedPull, PestTap, SoilMound, WEATHER_MINIGAMES

# 행동 → 손맛 인터랙션 클래스 (없는 행동은 즉시 적용)
TACTILE_INTERACTIONS = {
    "물 주기": WaterPour,
    "잡초 뽑기": WeedPull,
    "해충 살피기": PestTap,
    "흙 북돋기": SoilMound,
}

# 행동별 효과음 매핑
ACTION_SFX = {
    "물 주기": "water",
    "잡초 뽑기": "soil",
    "흙 북돋기": "soil",
    "배수로 정리": "water",
    "해충 살피기": "click",
    "살펴보기": "page",
    "기다리기": "page",
    "수확하기": "harvest",
}

# '밭 정리' 돌발 상황 진입 문구 — 또 만나도 다른 결로 읽히도록 변주.
# (물·해충 미니게임은 인라인 손맛으로 대체되어 폐지됨)
MINIGAME_INTROS = {
    "stage1": [
        "[돌발 상황]\n\n밭에 씨앗과 잡동사니가 뒤섞였다.\n아버지는 이걸 매일 새벽, 혼자 골라냈다.\n이번에는 내 손으로 가려 본다.",
        "[돌발 상황]\n\n간밤의 바람이 밭을 헤집어 놓았다.\n쓸 것과 버릴 것이 뒤죽박죽이다.\n서두르면 씨앗까지 버리게 된다.",
    ],
}

# 한 게임에 한 번, 중반에 반드시 등장하는 특별 이벤트 '별 잇기' 진입 문구
STAR_CONNECT_INTROS = [
    "[꿈결 같은 새벽]\n\n밭 위로 별이 유난히 밝다.\n아버지는 저 별을 보고 새벽을 가늠했다고 했다.\n별과 별을 이어 본다.",
    "[고요한 새벽]\n\n잠 못 든 밤, 하늘에 북두칠성이 또렷하다.\n아버지가 늘 올려다보던 그 별이다.\n순서대로 이어 본다.",
]


class Button:
    def __init__(self, x, y, w, h, text, value, font_size=20, kind="normal"):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.value = value
        self.font = get_font(font_size)
        self.hovered = False
        self.kind = kind   # "normal" | "close" — 닫기 버튼은 다른 스타일로 그린다

    def draw(self, screen):
        if self.kind == "close":
            # 나무결 행동 버튼과 확연히 다르게 — 어두운 회색 알약형 '✕ 닫기'
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
    # 첫 플레이 온보딩 카드 (제목, 본문)
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
        # 작물(+악몽 여부)에 따른 밭 성질 — 목표치, 버튼 이름, 마름/들끓음 속도
        self.crop_cfg = farm_config()
        self.is_tree = self.crop_cfg.get("family") == "나무류"
        self.no_weeds = self.crop_cfg.get("no_weeds", False)
        self.day = 1
        self.growth = 0
        self.growth_goal = self.crop_cfg["growth_goal"]
        self.moisture = 44
        self.health = 66
        self.weeds = 0 if self.no_weeds else 25
        self.pests = 14
        self.drainage = 55
        self.stress = 0
        self.actions_taken = 0
        self.last_action = ""
        self.message = "낯선 밭에서 눈을 떴다."
        self.notice = "밭의 상태부터 천천히 살펴보자."
        self.memory_cooldown = 1
        self.minigame_cooldown = 3       # '밭 정리' 돌발 상황 사이의 최소 간격
        self.weather_minigame_cooldown = 2  # 날씨 미니게임 쿨다운 (2턴 후부터 발동 가능)
        self.special_cooldown = random.randint(3, 5)   # 특별 이벤트('별 잇기')까지 남은 턴
        self.special_done = False                       # 특별 이벤트는 한 게임에 한 번만
        self.withers = 0                 # 작물이 완전히 시든 횟수 (3이면 끝내 시듦 — 배드엔딩)
        self.weak_turns = 0              # 비실비실(저체력)하게 흘려보낸 턴 — 오래 가면 끝내 시든다
        self.mistakes = 0
        self.memories_seen = set()
        self.buttons = []
        self.action_menu_open = False
        self.action_scroll = 0
        # 손맛 인터랙션 (씬 전환 없이 밭 위 오버레이). 헤드리스/시뮬은 끄고 즉시 적용.
        self.interaction = None
        self.interaction_action = None
        self.interactions_enabled = True
        self.story_cooldown = 2
        self.stories_seen = set()
        # 기다림 시스템: 마지막 '기다리기' 이후 흐른 턴 — 5턴을 넘기면 밭이 강제로 손을 멈추게 한다
        self.turns_since_wait = 0
        self.forced_wait_active = False
        self.forced_wait_timer = 0.0
        # 통합 '속마음' 표시 채널 — 메아리/감각/선물/날씨지혜를 하나로 묶어
        # 겹치지 않는 한 곳에서 차례로 보여준다.
        self.thought_text = ""
        self.thought_timer = 0.0
        self.thought_queue = []
        # Individual crop growth offsets (randomized per plot)
        self.crop_offsets = [random.randint(-2, 2) for _ in range(6)]
        # #7 Seasonal colors cache
        self.season_colors = get_season_colors(self.growth, self.growth_goal)
        # #10 Dad mode turn counter
        self.dad_turns_done = 0
        
        # UI & Animation additions
        self.scrollbar_dragging = False
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

        # 밭 데코레이션 생성 (초록 풀싹, 흙/돌 알갱이 고정 좌표 지정)
        self.plot_decorations = []
        self.plot_decorations.append({'type': 'grass', 'x': 86, 'y': 180})
        self.plot_decorations.append({'type': 'grass', 'x': 150, 'y': 184})
        self.plot_decorations.append({'type': 'grass', 'x': 354, 'y': 180})
        self.plot_decorations.append({'type': 'grass', 'x': 324, 'y': 200})
        self.plot_decorations.append({'type': 'grass', 'x': 88, 'y': 295})
        self.plot_decorations.append({'type': 'grass', 'x': 360, 'y': 390})
        self.plot_decorations.append({'type': 'grass', 'x': 88, 'y': 410})
        self.plot_decorations.append({'type': 'grass', 'x': 206, 'y': 414})
        
        pebbles = [
            (95, 196), (158, 196), (164, 198), (105, 290), (350, 280),
            (88, 335), (242, 290), (145, 300), (324, 305), (148, 412),
            (232, 408), (238, 410), (320, 404), (325, 406), (356, 330)
        ]
        for px, py in pebbles:
            self.plot_decorations.append({'type': 'pebble', 'x': px, 'y': py})

        # 첫 플레이 온보딩 (재플레이 시 생략)
        self.tutorial_step = 0
        self.tutorial_active = not game_state.is_second_run
        self.last_hover_value = None

        self.rebuild_buttons()

    def action_label(self, action):
        """작물에 따라 같은 행동도 다른 이름으로 보인다 (벼: 물 대기, 사과나무: 가지치기)."""
        return self.crop_cfg["labels"].get(action, action)

    def _cropify(self, text):
        """밭 텍스트 속 '당근'을 지금 기르는 작물 이름으로 (조사까지) 바꾼다."""
        return swap_crop_word(text, self.crop_cfg.get("food", "당근"))

    def rebuild_buttons(self):
        self.buttons = []
        start_x = 440
        start_y = 330
        if self.is_harvest_ready():
            self.buttons.append(Button(start_x, start_y, 300, 126, "수확하기", "수확하기", font_size=30))
            return

        if self.turns_since_wait >= 5:
            # 5턴 동안 한 번도 안 쉰 경우 강제 기다리기 (줄바꿈은 draw_button이 폭에 맞춰 처리)
            self.buttons.append(Button(start_x, start_y, 300, 126, "강제 기다리기 (돌발 상황 해결)", "__forced_wait__", font_size=24))
            return

        if not self.action_menu_open:
            # '행동하기'와 '기다리기'는 별개의 마음가짐 — 버튼도 나눈다
            self.buttons.append(Button(start_x, start_y, 300, 80, "행동하기", "__open_actions__", font_size=28))
            self.buttons.append(Button(start_x, start_y + 86, 300, 40, "기다리기", "기다리기", font_size=20))
            return

        actions = self.get_action_choices()
        max_scroll = max(0, len(actions) - 4)
        self.action_scroll = max(0, min(self.action_scroll, max_scroll))
        for i, action in enumerate(actions[self.action_scroll:self.action_scroll + 4]):
            by = start_y + i * 31
            self.buttons.append(Button(start_x, by, 284, 28, self.action_label(action), action, font_size=17))

        # 행동 닫기 — 할일 버튼과 헷갈리지 않게 아래에 간격을 두고 다른 스타일(알약형)로
        self.buttons.append(Button(start_x + 90, start_y + 126, 120, 22,
                                   "닫기", "__close_actions__", font_size=14, kind="close"))

    def is_harvest_ready(self):
        return self.growth >= self.growth_goal

    def get_needed_actions(self):
        needs = []
        lo, hi = self.crop_cfg["moist_lo"], self.crop_cfg["moist_hi"]

        def add(action, score, order):
            if score > 0:
                needs.append((action, score, order))

        if self.moisture < lo + 5:
            add("물 주기", lo + 5 - self.moisture, 0)
        if self.moisture > hi or self.drainage < 35:
            add("배수로 정리", max(self.moisture - hi, 35 - self.drainage), 1)
        if not self.no_weeds and self.weeds > 20:
            weed_score = self.weeds - 20
            if self.weeds > 32:
                weed_score += 12
            add("잡초 뽑기", weed_score, 2)
        if self.pests > 18:
            pest_score = self.pests - 18
            if self.pests > 32:
                pest_score += 12
            add("해충 살피기", pest_score, 3)
        if self.health < 55 or self.stress > 35:
            add("흙 북돋기", max(55 - self.health, self.stress - 35), 4)

        needs.sort(key=lambda item: (-item[1], item[2]))
        return [action for action, _score, _order in needs]

    def get_action_choices(self):
        choices = ["살펴보기"]
        for action in self.get_needed_actions():
            if action not in choices:
                choices.append(action)

        # '기다리기'는 행동 목록에서 분리 — 밭 화면의 전용 버튼으로만 한다
        fillers = ["물 주기", "잡초 뽑기", "해충 살피기", "배수로 정리", "흙 북돋기"]
        if self.no_weeds:
            fillers.remove("잡초 뽑기")
        for action in fillers:
            if action not in choices:
                choices.append(action)

        return choices

    def get_available_actions(self):
        if self.is_harvest_ready():
            return ["수확하기"]
        return self.get_action_choices()

    def clamp_stats(self):
        self.moisture = max(0, min(100, self.moisture))
        self.health = max(0, min(100, self.health))
        self.weeds = max(0, min(100, self.weeds))
        self.pests = max(0, min(100, self.pests))
        self.drainage = max(0, min(100, self.drainage))
        self.stress = max(0, min(100, self.stress))

    def drag_scrollbar(self, mouse_y):
        actions = self.get_action_choices()
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
        # 손맛 인터랙션이 떠 있으면 입력은 전부 거기로 (다른 클릭 차단)
        if self.interaction:
            for event in events:
                self.interaction.handle(event)
            return

        # 온보딩이 떠 있는 동안에는 클릭/스페이스로 카드만 넘긴다 (게임 입력 차단)
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
            if event.type == pygame.MOUSEWHEEL and self.action_menu_open:
                max_scroll = max(0, len(self.get_action_choices()) - 4)
                self.action_scroll = max(0, min(max_scroll, self.action_scroll - event.y))
                self.rebuild_buttons()
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.action_menu_open:
                    # Scrollbar click & drag detection
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
                            self.do_action(btn.value)
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
                max_scroll = max(0, len(self.get_action_choices()) - 4)
                delta = -1 if event.button == 4 else 1
                self.action_scroll = max(0, min(max_scroll, self.action_scroll + delta))
                self.rebuild_buttons()

    def do_action(self, action):
        if action == "수확하기":
            if self.is_harvest_ready():
                audio.play("click")
                game_state.understanding += 12
                game_state.final_health = self.health
                game_state.farm_mistakes = self.mistakes
                # #4 Go to harvest minigame instead of directly to ending
                game_state.transition_text = (
                    "[수확의 시간]\n\n"
                    "이 한 뿌리를 위해 여기까지 왔다.\n"
                    "조심히, 천천히 뽑아 보자."
                )
                game_state.transition_next = "stage4"
                game_state.is_clear_transition = False
                game_state.return_scene = "farm"
                game_state.current_scene = "transition"
            else:
                audio.play("break")
                self.health -= 8
                self.stress += 10
                self.mistakes += 1
                self.message = "아직 덜 자랐다. 성급하면 다 망친다."
                self.notice = "밭부터 돌보며 더 기다리자."
            return

        # 손맛 행동(물/잡초/해충)은 밭 위에서 직접 하는 인터랙션으로 — 실행이 결과를 가른다.
        # (헤드리스/시뮬은 interactions_enabled=False라 즉시 상태기반 적용)
        if (action in TACTILE_INTERACTIONS and self.interactions_enabled
                and not self.tutorial_active):
            self.interaction = TACTILE_INTERACTIONS[action](self)
            self.interaction_action = action
            return

        self._run_action(action)

    def _run_action(self, action, quality=None):
        self.actions_taken += 1
        self.last_action = action
        audio.play(ACTION_SFX.get(action, "click"))
        if action == "기다리기":
            self.turns_since_wait = 0
        elif action != "살펴보기":
            self.turns_since_wait += 1
            
        if action == "물 주기":
            game_state.water_count += 1
        elif action == "잡초 뽑기":
            game_state.weed_count += 1
        difficulty = 1 + self.growth // 6
        result, is_fail = self.apply_action(action, difficulty, quality)
        self.apply_field_pressure(difficulty)
        self.apply_weather_effects()

        # #11 Attitude tracking
        track_attitude(action, is_fail, self.is_good_turn())

        if self.health <= 20:
            # 건강이 바닥이면 자라지 못하고 멈춘다(역행은 없음). 끝내 손쓰지 못하면 시들어 버린다.
            self.mistakes += 1
            result += " 당근이 버티지 못하고 시든다."
        elif self.health < 38:
            # 비실비실한 작물은 버티기만 할 뿐 자라지 못한다 — 먼저 건강을 끌어올려야 한 뼘이라도 자란다.
            # (못하는 플레이어가 비실대는 채 수확까지 끌려가지 않게 — 회복하거나, 끝내 시들거나.)
            if not is_fail and action not in ("살펴보기", "기다리기"):
                if action == "흙 북돋기":
                    result += " 아직 기운이 없어 자라진 못하지만, 흙을 북돋우니 조금씩 살아난다."
                else:
                    result += " 아직 기운이 없어 자라지는 못한다. 흙을 북돋아 기운부터 채우자."
        else:
            # 성장은 '제대로 된 돌봄'과 '안정된 상태에서의 기다림'에서만 일어난다.
            # 관찰(살펴보기)이나 실패한 행동으로는 자라지 않는다 → 살펴보기 남발 지배 전략 차단.
            if action == "살펴보기" or is_fail:
                gain = 0
            elif action == "기다리기":
                gain = 3 if self.is_good_turn() else 0
            else:
                gain = 2
            if gain > 0:
                self.growth += gain
                if self.is_good_turn():
                    game_state.understanding += 2

        # 한 턴에 '속마음' 하나만 — 우선순위로 골라 통합 채널로 보낸다.
        recovery_msg = check_recovery(action, is_fail)  # 항상 호출(회복 추적 + 실패 기록)
        thought = ""
        if is_fail:
            thought = pick_failure_echo(action)          # 실패 시 아버지의 말 (교훈)
        elif recovery_msg:
            thought = recovery_msg
        if not thought and self.day % 5 == 0:
            gift = get_silent_gift()
            if gift:
                reveal_gift()
                thought = gift
        if not thought and action != "살펴보기":
            ae = pick_action_echo(action)
            if ae and random.random() < 0.5:
                thought = ae
            else:
                sense = pick_sensory(action)
                if sense:
                    game_state.current_sense = sense
                    thought = sense
        self.push_thought(thought)

        self.message = result
        self.notice = self.build_notice()
        self.clamp_stats()

        # 비실비실(저체력)하게 흘려보낸 턴을 센다 — 건강을 끌어올리면 초기화, 오래 끌면 끝내 시든다.
        if self.health < 38:
            self.weak_turns += 1
        elif self.health >= 45:
            self.weak_turns = 0

        # #7 Update seasonal colors
        self.season_colors = get_season_colors(self.growth, self.growth_goal)

        # Journal every 5 turns
        if self.day % 5 == 0:
            self._write_journal()

        # #10 Dad mode turn tracking
        if game_state.dad_mode:
            self.dad_turns_done += 1
            if self.dad_turns_done >= game_state.dad_mode_turns:
                game_state.dad_mode = False
                self.dad_turns_done = 0
                game_state.understanding += 10
                game_state.transition_text = (
                    "...\n\n"
                    "아버지의 하루가 끝났다.\n"
                    "아이는 모를 것이다. 이 밭의 모든 이랑에\n"
                    "아버지의 시간이 묻혀 있다는 것을."
                )
                game_state.transition_next = "farm"
                game_state.is_clear_transition = True
                game_state.current_scene = "transition"
                return

        # Priority: father_day > epiphany > memory > story > minigame
        fd = check_father_day()
        if fd and not game_state.dad_mode:
            game_state.current_scene = "father_day"
        elif check_epiphany():
            game_state.current_scene = "epiphany"
        elif game_state.current_scene == "farm":
            self.try_trigger_memory()
        if game_state.current_scene == "farm":
            self.try_trigger_story()
        if game_state.current_scene == "farm":
            self.try_trigger_minigame(action)
        self.rebuild_buttons()

        # 자동 저장 기능
        if save_system.get_setting("autosave"):
            save_system.save_game(self)

    def push_thought(self, text, dur=4.5):
        """통합 '속마음' 채널에 한 줄 추가. 여러 개면 순서대로 표시(겹치지 않음)."""
        if not text:
            return
        self.thought_queue.append((text, dur))
        # 백로그가 길어지지 않도록 최근 2개만 유지
        if len(self.thought_queue) > 2:
            self.thought_queue = self.thought_queue[-2:]

    def apply_action(self, action, difficulty, quality=None):
        """행동을 적용하고 (짧은 결과 메시지, 실패 여부)를 돌려준다.
        quality: 손맛 인터랙션의 결과(dict). 있으면 플레이어 실행이 결과를 가른다."""
        if action == "살펴보기":
            game_state.understanding += 2
            self.stress = max(0, self.stress - 4)
            return self.inspect_message(), False

        lo, hi = self.crop_cfg["moist_lo"], self.crop_cfg["moist_hi"]
        w_mult = self.crop_cfg["water_mult"]

        if action == "물 주기":
            if quality is not None:
                add = int(quality["moisture_add"] * w_mult)
                self.moisture += add
                if quality["quality"] == "over":
                    # 실수는 따끔하되 회복 가능하게 — 손맛을 못해도 소프트락에 빠지지 않도록.
                    self.health -= 6
                    self.stress += 6
                    self.mistakes += 1
                    return "물이 흥건하다. 뿌리가 조금 답답해한다.", True
                if quality["quality"] == "under":
                    return "조금 모자란 듯, 흙이 아직 마르다.", False
                self.health += 4
                self.stress = max(0, self.stress - 6)
                return "딱 알맞게, 흙이 촉촉해졌다.", False
            if self.moisture < lo + 5:
                self.moisture += int(34 * w_mult)
                self.health += 4
                self.stress = max(0, self.stress - 6)
                return "흙이 촉촉해졌다.", False
            if self.moisture > hi - 2:
                self.moisture += int(18 * w_mult)
                self.health -= 12 + difficulty
                self.stress += 10
                self.mistakes += 1
                return "물이 너무 많았다. 뿌리가 숨을 못 쉰다.", True
            self.moisture += int(18 * w_mult)
            return "물을 주었다.", False

        if action == "잡초 뽑기":
            if quality is not None:
                frac = quality.get("cleared_frac", 1.0)
                self.weeds -= int(30 * frac) + 4
                if frac >= 0.85:
                    self.health += 3
                    return "잡초를 말끔히 걷어냈다.", False
                if frac >= 0.45:
                    return "잡초를 어느 정도 정리했다.", False
                self.stress += 3
                return "잡초가 아직 꽤 남았다.", False
            if self.weeds > 20:
                self.weeds -= 34
                self.health += 3
                return "잡초를 걷어냈다.", False
            self.health -= 5
            self.stress += 6
            self.mistakes += 1
            return "뽑을 잡초도 없는데 애꿎은 흙만 헤집었다.", True

        if action == "해충 살피기":
            if quality is not None:
                frac = quality.get("cleared_frac", 1.0)
                self.pests -= int(28 * frac) + 4
                if frac >= 0.85:
                    self.health += 3
                    return "잎 뒤의 벌레를 거의 다 잡았다.", False
                if frac >= 0.45:
                    return "벌레를 절반쯤 잡았다.", False
                self.stress += 2
                return "놓친 벌레가 많다.", False
            if self.pests > 18:
                self.pests -= 32
                self.health += 3
                return "잎 뒤의 벌레를 잡아냈다.", False
            self.stress = max(0, self.stress - 2)
            return "살펴보니 큰 벌레는 없다.", False

        if action == "배수로 정리":
            if self.moisture > 68 or self.drainage < 45:
                self.moisture -= 22
                self.drainage += 22
                self.health += 1
                return "물길을 터주니 물이 잘 빠진다.", False
            self.drainage += 8
            self.stress += 5
            self.mistakes += 1
            return "지금은 배수로를 손볼 때가 아니다.", True

        if action == "흙 북돋기":
            if quality is not None:
                # 손맛: 잘 덮을수록 효과가 크다. 못해도 소폭은 보장(소프트락 방지).
                frac = quality.get("cleared_frac", 1.0)
                self.health += max(2, int(8 * frac))
                self.stress = max(0, self.stress - max(2, int(10 * frac)))
                self.drainage += int(4 * frac)
                if frac >= 0.85:
                    return "흙을 두둑이 북돋우니 한결 생기가 돈다.", False
                if frac >= 0.45:
                    return "흙을 어느 정도 다독였다.", False
                return "북돋다 말아 뿌리가 아직 허전하다.", False
            if self.health < 65 or self.stress > 24:
                self.health += 8
                self.stress = max(0, self.stress - 10)
                self.drainage += 4
                return "흙을 다독이니 한결 생기가 돈다.", False
            self.health += 2
            self.moisture -= 4
            return "흙을 만졌지만 큰 변화는 없다.", False

        if action == "기다리기":
            if self.is_good_turn():
                self.moisture -= 8
                return "조용히 기다린다. 당근이 제 속도로 자란다.", False
            self.health -= 8 + difficulty
            self.stress += 8
            self.mistakes += 1
            return "기다리기엔 밭이 너무 불안하다.", True

        return "...", False

    def apply_field_pressure(self, difficulty):
        self.day += 1
        self.moisture -= random.randint(4, 7 + difficulty)
        if not self.no_weeds:
            self.weeds += random.randint(4, 7 + difficulty)
        self.pests += random.randint(2, 5 + difficulty)

        dmg = 0
        if self.moisture > 75:
            dmg += 5 + difficulty
            self.drainage -= 5
        if self.moisture < 22:
            dmg += 6 + difficulty
            self.stress += 5
        if self.weeds > 55:
            dmg += 5 + difficulty
        if self.pests > 48:
            dmg += 6 + difficulty
        # 건강이 바닥일 때 — '돌보려는' 손에겐 회복의 길을 열어 두되(소프트락 방지),
        # 잡초·해충을 손 놓고 방치한 밭은 봐주지 않는다. 끝내 시들어 수확 못 한 채 배드엔딩으로.
        if self.health < 28:
            neglected = self.weeds > 52 or self.pests > 46
            dmg = int(dmg * (0.9 if neglected else 0.45))
        self.health -= dmg
        if random.random() < 0.18 + difficulty * 0.04:
            self.drainage -= random.randint(4, 10)

        # Weather tick
        game_state.weather_turns_left -= 1
        if game_state.weather_turns_left <= 0:
            old_weather = game_state.weather
            advance_weather()
            # #6 Weather wisdom on change → 통합 속마음 채널로
            new_weather = game_state.weather
            if new_weather != old_weather and new_weather in WEATHER_WISDOM:
                self.push_thought(WEATHER_WISDOM[new_weather], dur=5.0)

    def apply_weather_effects(self):
        w = WEATHER_DATA.get(game_state.weather, {})
        self.moisture += w.get("moisture", 0)
        self.stress += w.get("stress", 0)
        self.drainage += w.get("drainage", 0)
        self.health += w.get("health", 0)
        self.pests += w.get("pests", 0)

    def try_trigger_story(self):
        # 성장 마일스톤에서 최소 2회는 보장 발생(쿨다운 무시) → 공감 선택 기회를 RNG에 맡기지 않는다.
        seen = len(self.stories_seen)
        forced = (self.growth >= 5 and seen == 0) or (self.growth >= 11 and seen < 2)
        if not forced:
            if self.story_cooldown > 0:
                self.story_cooldown -= 1
                return
            if random.random() > 0.32:
                return
        available = [e for i, e in enumerate(STORY_EVENTS) if i not in self.stories_seen]
        if not available:
            return
        event = random.choice(available)
        self.stories_seen.add(STORY_EVENTS.index(event))
        self.story_cooldown = 4
        game_state.choice_data = event
        game_state.current_scene = "story_choice"

    def _write_journal(self):
        season = get_season(self.growth, self.growth_goal)
        lines = [f"[{self.day}일째 · {season} · {game_state.weather}]"]
        # 수분 한 줄 (회고 키 문장 유지)
        if self.moisture > 75:
            lines.append("오늘 물을 너무 많이 줬다.")
        elif self.moisture < 25:
            lines.append("흙이 바짝 말라 있었다.")
        else:
            lines.append("수분은 적당했다.")
        # 밭의 다른 상태를 구체적으로 — 그날의 손길이 어디에 닿았는지
        detail = []
        if self.weeds > 45:
            detail.append("잡초가 자꾸 올라온다")
        if self.pests > 38:
            detail.append("잎 뒤로 벌레가 보인다")
        if self.drainage < 35:
            detail.append("물길이 막혀 물이 더디게 빠진다")
        if detail:
            lines.append(", ".join(detail) + ".")
        elif self.is_good_turn():
            lines.append("밭은 대체로 평온했다. 손이 갈 곳이 줄었다.")
        # 건강 (회고 키 문장 유지 + 호전 표현 추가)
        if self.health < 45:
            lines.append("당근이 많이 힘들어 보였다.")
        elif self.health >= 78:
            lines.append("당근 잎에 윤기가 돌기 시작했다.")
        # 실수 (회고 키 문장 유지)
        if self.mistakes > 3:
            lines.append("실수가 잦았다. 아직 모르는 것이 많다.")
        # 성장 진척
        prog = int(min(1.0, self.growth / self.growth_goal) * 100)
        lines.append(f"여기까지 성장 {prog}%. 수확이 가까워진다." if prog >= 60
                     else f"여기까지 성장 {prog}%.")
        # 이해 단계별 속마음 (회고 키 문장 유지)
        u = game_state.understanding
        if u < 20:
            lines.append("이걸 왜 해야 하는지 아직 모르겠다.")
        elif u < 40:
            lines.append("조금씩 알 것 같기도 하다.")
        else:
            lines.append("이 일의 무게가 느껴진다.")
        game_state.journal_entries.append("\n".join(lines))

    def is_good_turn(self):
        return (
            30 <= self.moisture <= 72
            and self.health >= 45
            and self.weeds <= 62
            and self.pests <= 58
            and self.stress <= 62
        )

    def inspect_message(self):
        warnings = []
        if self.moisture < 30:
            warnings.append("수분 부족")
        elif self.moisture > 72:
            warnings.append("수분 과다")
        if self.weeds > 45:
            warnings.append("잡초 많음")
        if self.pests > 38:
            warnings.append("해충 많음")
        if self.health < 50:
            warnings.append("건강 낮음")
        if self.drainage < 35:
            warnings.append("배수 낮음")

        # 날씨가 '무엇을 하는지'만 짚어 준다 (날씨 이름·예보·지속일은 상단 HUD에 이미 표시됨).
        weather_tips = {
            "맑음": "맑은 날엔 수분이 천천히 마른다.",
            "흐림": "흐린 날은 큰 영향이 없다.",
            "비": "비엔 수분이 크게 오른다 — 과습 주의.",
            "가뭄": "가뭄엔 수분이 뚝 떨어진다.",
            "강풍": "강풍은 해충을 날리지만 밭을 들쑤신다.",
        }
        tip = weather_tips.get(game_state.weather, "")
        status_str = ", ".join(warnings[:3]) if warnings else "밭이 안정적이다"
        return f"자세히 보니 — {status_str}. {tip}"

    def build_notice(self):
        # 정답을 떠먹여주는 대신 '증상'을 묘사한다 — 플레이어가 직접 읽고 판단하도록.
        # (정밀 진단과 날씨 예보는 '살펴보기'로만 얻을 수 있어 관찰 행동의 가치를 살린다.)
        if self.is_harvest_ready():
            return "다 자랐다. 이제 수확할 때다."
        if self.health < 45:
            return "당근이 축 처져 기운이 없다. 흙을 북돋아 기운을 끌어올려 주자."
        if self.moisture < 30:
            return "흙이 바짝 말라 손끝이 버석거린다."
        if self.moisture > 72:
            return "흙이 질척이고 물이 고여 있다."
        if self.drainage < 35:
            return "물길이 막혀 물이 잘 빠지지 않는다."
        if self.weeds > 50:
            return "잡초가 빼곡히 올라와 있다."
        if self.pests > 42:
            return "잎 뒤가 어쩐지 분주하다."
        if self.stress > 55:
            return "밭 전체가 예민하게 곤두서 있다."
        if self.is_good_turn():
            return "밭이 평온하다. 잠시 기다려도 좋겠다."
        return "딱히 급해 보이는 곳은 없다."

    def grade_text(self, value, low_bad=True):
        if low_bad:
            if value >= 70:
                return "좋음"
            if value >= 45:
                return "보통"
            return "위험"
        if value <= 30:
            return "낮음"
        if value <= 65:
            return "주의"
        return "높음"

    def try_trigger_memory(self):
        if self.memory_cooldown > 0:
            self.memory_cooldown -= 1
            return

        forced_key = None
        if self.growth >= 6 and "first" not in self.memories_seen:
            forced_key = "first"
        elif self.growth >= 12 and "second" not in self.memories_seen:
            forced_key = "second"

        u = game_state.understanding
        chance = 0.24 if u < 18 else 0.14 if u < 45 else 0.06
        if forced_key is None and random.random() >= chance:
            return

        memory = self.pick_memory(forced_key)
        if not memory:
            return

        key, title, text = memory
        self.memories_seen.add(key)
        self.memory_cooldown = 4 if u < 25 else 6 if u < 50 else 8
        game_state.memory_title = self._cropify(title)
        game_state.memory_text = self._cropify(text)
        game_state.memory_next = "farm"
        game_state.current_scene = "memory"

    def pick_memory(self, forced_key):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        name_ga = append_josa(name, "이/가")
        u = game_state.understanding

        if u < 18:
            memories = [
                (
                    "first",
                    "희미한 식탁",
                    f"식탁 위에 당근 반찬이 놓여 있다.\n{name_eun} 젓가락으로 그릇을 밀어냈고, 아버지는 잠깐 말을 멈췄다.\n그때는 그 침묵이 왜 길게 느껴졌는지 몰랐다.",
                ),
                (
                    "low_market",
                    "장바구니 소리",
                    f"비닐봉지가 문고리에 부딪히는 소리가 난다.\n아버지는 흙 묻은 당근을 꺼내며 '오늘 건 달다'고 말했다.\n{name_ga}는 대답 대신 물컵만 만지작거렸다.",
                ),
                (
                    "second",
                    "남긴 접시",
                    "싱크대 옆에 남은 반찬 그릇이 보인다.\n작은 주황색 조각들이 물에 젖어 천천히 가라앉는다.\n어쩐지 꿈속의 흙냄새가 더 짙어진다.",
                ),
            ]
        elif u < 45:
            memories = [
                (
                    "first",
                    "다시 보이는 식탁",
                    f"당근 반찬을 밀어내던 손이 떠오른다.\n{name_eun} 그때 아버지의 표정보다 자기 입맛만 먼저 생각했다는 걸 알아차린다.",
                ),
                (
                    "mid_field",
                    "이른 아침",
                    "아버지는 아직 어두운 시간에 밭으로 나갔다.\n흙을 털어내는 손등에는 잔금이 많았다.\n그 손이 식탁 위 반찬을 만들었다는 생각이 뒤늦게 따라온다.",
                ),
                (
                    "second",
                    "한 조각의 무게",
                    "젓가락 끝에 걸린 당근 한 조각이 이상하게 무겁다.\n맛보다 먼저 떠오르는 건, 누군가의 기다림이었다.",
                ),
            ]
        else:
            memories = [
                (
                    "first",
                    "따뜻한 식탁",
                    f"식탁 위의 당근 반찬이 떠오른다.\n이번에는 밀어내고 싶다는 생각보다, 한 번쯤 제대로 맛보고 싶다는 마음이 먼저 든다.",
                ),
                (
                    "high_field",
                    "손등의 흙",
                    "아버지가 웃으며 손등의 흙을 털어낸다.\n그 모습은 무겁기보다 다정하다.\n꿈속의 밭도 조금은 덜 낯설게 느껴진다.",
                ),
                (
                    "second",
                    "짧은 고개 끄덕임",
                    f"{name_ga} 말없이 고개를 끄덕인다.\n무언가를 완전히 알게 된 건 아니지만, 이제 외면하고 싶지는 않다.",
                ),
            ]

        if forced_key:
            for memory in memories:
                if memory[0] == forced_key:
                    return memory

        candidates = [memory for memory in memories if memory[0] not in self.memories_seen]
        return random.choice(candidates or memories)

    def try_trigger_minigame(self, action):
        # 물·잡초·해충은 이제 밭 위 '손맛' 인라인으로 직접 하므로, 같은 걸 또 시키는
        # 전체화면 미니게임(물·해충)은 흐름만 끊는 군더더기 → 폐지.
        # 고유 콘텐츠인 '밭 정리(stage1)'만, 밭이 어수선할 때 가끔 등장하는 돌발 상황으로 남긴다.
        if action in ("살펴보기", "수확하기"):
            return

        # ── 특별 이벤트 '별 잇기' — 한 게임에 한 번, 중반에 반드시 등장 ──
        # 예전 '씨앗 받기'는 ① 날씨 미니게임에 밀리고 ② 확률 게이트(0.6)까지 겹쳐
        # 거의 안 떠서 사실상 못 보던 콘텐츠였고, 메커니즘도 '빗물 받기'와 겹쳤다.
        # → 날씨 체크보다 먼저, 쿨다운이 다 되면 확정으로 띄운다.
        if not self.special_done:
            self.special_cooldown -= 1
            if self.special_cooldown <= 0:
                game_state.transition_text = random.choice(STAR_CONNECT_INTROS)
                game_state.current_scene = "transition"
                game_state.is_clear_transition = False
                game_state.transition_next = "star_connect"
                game_state.return_scene = "farm"
                self.special_done = True
                self.minigame_cooldown = max(self.minigame_cooldown, 4)
                return

        # ── 날씨 미니게임: 매 턴 확률적으로 발동 ──
        if self.weather_minigame_cooldown > 0:
            self.weather_minigame_cooldown -= 1
        elif game_state.weather in WEATHER_MINIGAMES and random.random() < 0.35:
            self.interaction = WEATHER_MINIGAMES[game_state.weather](self)
            self.interaction_action = "__weather__"
            self.weather_minigame_cooldown = 3
            return

        if self.minigame_cooldown > 0:
            self.minigame_cooldown -= 1
            return

        if self.weeds < 48 and self.drainage > 38:
            return  # 밭이 충분히 정돈돼 있으면 굳이 부르지 않음
        if random.random() >= 0.14:
            return

        game_state.transition_text = random.choice(MINIGAME_INTROS["stage1"])
        game_state.current_scene = "transition"
        game_state.is_clear_transition = False
        game_state.transition_next = "stage1"
        game_state.return_scene = "farm"
        self.minigame_cooldown = 6

    def update(self, dt):
        if self.forced_wait_active:
            self.forced_wait_timer -= dt
            if self.forced_wait_timer <= 0:
                self.forced_wait_timer = 0.0
                self.forced_wait_active = False
                self.interaction = None
                audio.play("break")
                self.health = max(0, self.health - 15)
                self.stress = min(100, self.stress + 20)
                self.mistakes += 1
                self.turns_since_wait = 0
                self.message = "돌발 상황을 제시간에 해결하지 못해 작물이 큰 충격을 받았습니다."
                self.notice = "기다려야 할 때는 서두르지 말고 밭의 부름에 집중합시다."
                self.rebuild_buttons()
                if save_system.get_setting("autosave"):
                    save_system.save_game(self)
                return

        # 손맛 인터랙션 진행 중에는 그것만 갱신 (나머지 밭은 잠시 멈춤)
        if self.interaction:
            self.interaction.update(dt)
            if self.interaction.done:
                result = self.interaction.result
                action = self.interaction_action
                self.interaction = None
                
                if self.forced_wait_active:
                    self.forced_wait_active = False
                    self.turns_since_wait = 0
                    self._run_action(action, result)
                    self.message = f"돌발 상황({action})을 30초 내에 무사히 해결했습니다!"
                    self.notice = "기다림이 작물을 더 튼튼하게 만듭니다."
                    game_state.patience_score += 1
                    game_state.understanding += 4
                    if save_system.get_setting("autosave"):
                        save_system.save_game(self)
                # 날씨 미니게임 결과 — 스탯 보너스 직접 적용
                elif result and "weather_bonus" in result:
                    bonus = result["weather_bonus"]
                    for stat, val in bonus.items():
                        cur = getattr(self, stat, None)
                        if cur is not None:
                            setattr(self, stat, cur + val)
                    self.clamp_stats()
                    self.rebuild_buttons()
                else:
                    self._run_action(action, result)
            return

        # 버튼 호버 상태 갱신 + 새로 올라탄 버튼에 호버 효과음
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

        # Update firefly particles
        for f in self.fireflies:
            f['x'] += f['speed_x'] * dt
            f['y'] += f['speed_y'] * dt
            f['scale_timer'] += 2.2 * dt
            if f['x'] < 10 or f['x'] > 790:
                f['speed_x'] *= -1
            if f['y'] < 20 or f['y'] > 160:
                f['speed_y'] *= -1

        # 통합 '속마음' 채널: 현재 문구 페이드 → 비면 큐에서 다음 문구 꺼내기
        if self.thought_timer > 0:
            self.thought_timer -= dt
            if self.thought_timer <= 0:
                self.thought_text = ""
        if not self.thought_text and self.thought_queue:
            self.thought_text, dur = self.thought_queue.pop(0)
            self.thought_timer = dur

        # 완전히 쓰러졌거나(체력 0), 비실비실하게 너무 오래 끌면(정체) 한 번 크게 시든다.
        if self.health <= 0 or self.weak_turns >= 7:
            self._wilt()

    def _wilt(self):
        """작물이 한 번 크게 시든다. 세 번째면 끝내 회복 못 하고 '시듦' 배드엔딩으로 종결.
        못 키우는 플레이를 무한정 끌지 않고 수확 못 한 채 깔끔히 마무리하는 안전판이기도 하다."""
        self.withers += 1
        self.weak_turns = 0
        if self.withers >= 3:
            # 세 번째로 완전히 시들면 손쓸 수 없다 — 수확 못 한 채 '시듦' 배드엔딩으로.
            game_state.crop_failed = True
            game_state.final_health = 0
            game_state.farm_mistakes = self.mistakes + 3
            game_state.transition_text = (
                "[밭이 시들어 버렸다]\n\n"
                "아무리 다독여도 당근은 다시 일어서지 못했다.\n"
                "흙만 남은 두둑을 한참 바라보았다."
            )
            game_state.transition_next = "ending"
            game_state.is_clear_transition = False
            game_state.current_scene = "transition"
            return
        # 시들 때마다 조금씩 기력을 돌려주되, 거듭될수록 회복이 야박해진다(스스로 일으켜 세워야 한다).
        self.health = max(self.health, 28 - self.withers * 6)
        self.stress = 45
        self.mistakes += 2
        game_state.understanding = max(0, game_state.understanding - 8)
        warn = ("이대로면 밭을 잃는다. 한 번만 더 시들면 손쓸 수 없다."
                if self.withers == 2 else "다시 흙부터 천천히 다독여야 한다.")
        self.message = "당근이 크게 시들어 버렸다. " + warn
        self.push_thought("처음부터, 천천히.")
        self.rebuild_buttons()

    def draw_compact_meter(self, screen, label, value, x, y, color):
        font = get_font(14)
        label_surf = font.render(label, True, TEXT_DARK)
        screen.blit(label_surf, (x, y - 1))
        # 막대 오른쪽 끝은 열마다 고정(정렬 유지)하되, 시작점은 라벨 실제 폭 뒤로 둔다.
        # '스트레스'처럼 긴 라벨이 막대에 덮여 잘리던 문제를 막는다.
        bar_right = x + 134
        bar_x = x + max(48, label_surf.get_width() + 6)
        bar = pygame.Rect(bar_x, y, bar_right - bar_x, 13)
        draw_meter_bar(screen, bar, value, 100, color)

    def draw_labeled_meter(self, screen, label, value, max_value, x, y, w, color):
        font = get_font(16)
        shown_value = max(0, min(value, max_value))
        label_surf = font.render(label, True, TEXT_DARK)
        value_surf = font.render(f"{shown_value}/{max_value}", True, TEXT_DARK)
        screen.blit(label_surf, (x, y - 1))
        screen.blit(value_surf, (x + w - value_surf.get_width(), y - 1))

        bar = pygame.Rect(x, y + 22, w, 15)
        draw_meter_bar(screen, bar, value, max_value, color)

        if label == "성장":
            fill_w = int(bar.w * (shown_value / max_value))
            carrot_x = max(bar.x, bar.x + fill_w - 3)
            # 현재 작물에 맞는 미니 아이콘을 가져와 세로 중앙 정렬하여 그린다
            crop_key = game_state.crop
            mini_spr = sprites.get(f"mini_{crop_key}", sprites["mini_carrot"])
            screen.blit(mini_spr, (carrot_x, bar.y + 7 - mini_spr.get_height() // 2))

    def draw_field_summary(self, screen):
        panel = pygame.Rect(430, 82, 320, 100)
        draw_light_panel(screen, panel)
        title_font = get_font(20)
        
        # 기르는 작물 종류에 맞게 이름과 접미사(나무/논/밭)를 조합해 타이틀을 출력
        crop_name = current_crop()["name"]
        if game_state.crop == "apple":
            suffix = "나무"
        elif game_state.crop == "rice":
            suffix = " 논"
        else:
            suffix = "밭"
        title_text = f"밭 상태 ({crop_name}{suffix})"
        
        title = title_font.render(title_text, True, TEXT_DARK)
        screen.blit(title, (450, 96))

        self.draw_labeled_meter(screen, "성장", self.growth, self.growth_goal, 450, 123, 116, (235, 150, 55))
        # Understanding badge (moon + stage name) instead of numeric bar
        draw_understanding_badge(screen, 600, 123, 130)

        status_font = get_font(16)
        health_text = status_font.render(f"건강 {self.grade_text(self.health)}", True, TEXT_DARK)
        screen.blit(health_text, (450, 162))

        if self.is_harvest_ready():
            ready = status_font.render("수확 가능", True, (145, 55, 0))
            screen.blit(ready, (640, 162))

    def draw_meters(self, screen):
        panel = pygame.Rect(430, 190, 320, 106)
        draw_light_panel(screen, panel)
        # 6개 스탯을 2열로 — 건강을 좌우하는 배수·스트레스까지 모두 노출
        c1, c2 = 450, 600
        self.draw_compact_meter(screen, "수분", self.moisture, c1, 205, (80, 170, 240))
        self.draw_compact_meter(screen, "건강", self.health, c2, 205, (90, 185, 95))
        self.draw_compact_meter(screen, "잡초", self.weeds, c1, 232, (150, 160, 60))
        self.draw_compact_meter(screen, "해충", self.pests, c2, 232, (210, 110, 60))
        self.draw_compact_meter(screen, "배수", self.drainage, c1, 259, (90, 160, 185))
        self.draw_compact_meter(screen, "스트레스", self.stress, c2, 259, (210, 95, 95))

    def draw_action_scrollbar(self, screen):
        actions = self.get_action_choices()
        if not self.action_menu_open or len(actions) <= 4:
            return

        track = pygame.Rect(732, 330, 8, 121)
        pygame.draw.rect(screen, (198, 166, 118), track, border_radius=4)
        thumb_h = max(22, int(track.h * 4 / len(actions)))
        max_scroll = max(1, len(actions) - 4)
        thumb_y = track.y + int((track.h - thumb_h) * self.action_scroll / max_scroll)
        thumb = pygame.Rect(track.x, thumb_y, track.w, thumb_h)
        pygame.draw.rect(screen, (123, 92, 65), thumb, border_radius=4)

    def crop_positions(self):
        # 밭 이미지(field_bed)의 6개 흙구덩이 중앙 픽셀 위치에 맞게 조율됨 (offset (44, 140) 기준)
        return [(126, 241), (223, 241), (322, 241), (126, 360), (223, 360), (322, 360)]

    def _draw_seeds(self, screen, x, y):
        """작물별 씨앗 그래픽. 밭 이미지의 기본(주황) 씨앗을 흙 패치로 가린 뒤 그 위에 그린다."""
        screen.blit(sprites["dirt_patch"], (x - 13, y - 12))
        draw_crop_seed(screen, x, y, game_state.crop)

    def _draw_plain_soil(self, screen, plot_rect):
        """나무류용 민 흙바닥 — 6구덩이 없이 한 덩이의 갈아 놓은 땅."""
        sc = self.season_colors
        inner = pygame.Rect(plot_rect.x + 22, plot_rect.y + 28, plot_rect.w - 44, plot_rect.h - 56)
        # 나무 테두리 틀
        frame = inner.inflate(16, 16)
        pygame.draw.rect(screen, (40, 30, 25), frame.move(0, 4), border_radius=18)
        pygame.draw.rect(screen, (132, 83, 48), frame, border_radius=18)
        pygame.draw.rect(screen, (185, 125, 80), frame, 3, border_radius=18)
        # 흙 (수분에 따라 색조)
        soil = (96, 62, 42) if self.moisture > 72 else (120, 82, 54) if self.moisture < 28 else sc["dirt"]
        pygame.draw.rect(screen, sc["dirt_dark"], inner.move(0, 3), border_radius=14)
        pygame.draw.rect(screen, soil, inner, border_radius=14)
        # 갈아 놓은 이랑 결(가로 줄) 몇 개
        for i in range(1, 5):
            ly = inner.y + inner.h * i // 5
            pygame.draw.line(screen, mix_color(soil, (0, 0, 0), 0.12),
                             (inner.x + 10, ly), (inner.right - 10, ly), 2)
        # 마른 땅이면 갈라짐 살짝
        if self.moisture < 28:
            cx, cy = inner.centerx, inner.centery
            pygame.draw.line(screen, (82, 53, 35), (cx - 40, cy + 30), (cx - 20, cy + 40), 2)
            pygame.draw.line(screen, (82, 53, 35), (cx + 24, cy - 34), (cx + 40, cy - 24), 2)

    def _draw_paddy_field(self, screen, plot_rect):
        """벼용 물이 자작한 논 (관개농업 연출) — 6구덩이 대신 물이 채워진 논바닥과 물결."""
        sc = self.season_colors
        inner = pygame.Rect(plot_rect.x + 22, plot_rect.y + 28, plot_rect.w - 44, plot_rect.h - 56)
        
        # 논둑 (dyke/frame)
        frame = inner.inflate(16, 16)
        pygame.draw.rect(screen, (35, 30, 25), frame.move(0, 4), border_radius=18) # 그림자
        pygame.draw.rect(screen, (100, 75, 55), frame, border_radius=18)          # 논둑 몸통 (흙둑)
        pygame.draw.rect(screen, (75, 55, 40), frame, 3, border_radius=18)         # 논둑 어두운 선
        
        # 논 물바닥 (진흙 기저 - 침울한 회색에서 밝고 비옥한 황토빛 진흙색으로 개선)
        pygame.draw.rect(screen, (92, 72, 52), inner, border_radius=14)
        
        # 자작하게 고인 물 (수분에 따라 물의 밝기와 비침이 달라짐 - 맑은 하늘빛 투사)
        water_alpha = min(160, max(50, int(self.moisture * 1.5)))
        water_surf = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        water_surf.fill((70, 155, 200, water_alpha))
        
        # 수면 위 햇살 반사광 (중앙부에 부드러운 하이라이트 추가)
        for r in range(140, 0, -10):
            alpha = int(24 * (1.0 - r / 140.0) * (water_alpha / 160.0))
            pygame.draw.ellipse(water_surf, (255, 255, 255, alpha), (inner.w // 2 - r, inner.h // 2 - int(r * 0.4), r * 2, int(r * 0.8)))
            
        screen.blit(water_surf, (inner.x, inner.y))
        
        # 물 반사광/하이라이트 (가로로 긴 맑은 물결선들 - 색상 한층 더 밝게 보정)
        for i in range(1, 4):
            ly = inner.y + inner.h * i // 4
            pygame.draw.ellipse(screen, (200, 235, 255, 140), (inner.x + 20, ly - 4, inner.w - 40, 8), 1)
            
        # 6개의 모내기 자리 주변에 자작한 물결(동심원 잔물결) 그리기
        for cx, cy in self.crop_positions():
            rx, ry = cx, cy + 8
            pygame.draw.ellipse(screen, (190, 230, 255, 200), (rx - 16, ry - 5, 32, 10), 1)
            pygame.draw.ellipse(screen, (190, 230, 255, 120), (rx - 26, ry - 8, 52, 16), 1)

    def _draw_tree(self, screen, ratio):
        """나무류 작물: 한 그루의 나무가 성장 비율(ratio)에 따라 자란다.
        어린 묘목 → 굵어지는 줄기와 우거지는 잎 → 수확기엔 열매가 맺힌다."""
        import math
        ratio = max(0.0, min(1.2, ratio))
        base_x, base_y = 225, 360          # 밭 한가운데 땅에 심긴 밑동
        trunk_h = int(24 + 96 * min(1.0, ratio))
        trunk_w = int(8 + 16 * min(1.0, ratio))
        canopy_r = int(16 + 62 * min(1.0, ratio))
        top_y = base_y - trunk_h

        # 밑동 그림자
        shadow = pygame.Surface((canopy_r * 2 + 20, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 60), shadow.get_rect())
        screen.blit(shadow, (base_x - canopy_r - 10, base_y - 6))

        # 줄기 (밑이 굵고 위가 가는 사다리꼴)
        trunk_pts = [
            (base_x - trunk_w // 2, base_y),
            (base_x + trunk_w // 2, base_y),
            (base_x + max(2, trunk_w // 4), top_y + canopy_r // 2),
            (base_x - max(2, trunk_w // 4), top_y + canopy_r // 2),
        ]
        pygame.draw.polygon(screen, (110, 74, 44), trunk_pts)
        pygame.draw.polygon(screen, (150, 104, 62), trunk_pts, 2)

        if ratio < 0.12:
            # 갓 심은 묘목: 줄기 끝에 작은 잎 두 장
            pygame.draw.circle(screen, (86, 160, 78), (base_x - 5, top_y + 6), 6)
            pygame.draw.circle(screen, (86, 160, 78), (base_x + 5, top_y + 6), 6)
            return

        # 잎 덮개 (여러 원을 겹쳐 뭉게뭉게)
        cx, cy = base_x, top_y
        dark = (46, 112, 60)
        mid = (66, 150, 78)
        light = (108, 190, 104)
        blobs = [
            (cx, cy, canopy_r), (cx - canopy_r // 2, cy + canopy_r // 4, int(canopy_r * 0.7)),
            (cx + canopy_r // 2, cy + canopy_r // 4, int(canopy_r * 0.7)),
            (cx, cy - canopy_r // 3, int(canopy_r * 0.72)),
        ]
        for bx, by, r in blobs:
            pygame.draw.circle(screen, dark, (bx, by + 3), r)
        for bx, by, r in blobs:
            pygame.draw.circle(screen, mid, (bx, by), r)
        pygame.draw.circle(screen, light, (cx - canopy_r // 3, cy - canopy_r // 3), max(4, canopy_r // 3))

        # 수확기: 잎 사이로 붉은 열매(사과 등) — 작물 색조 사용
        if ratio >= 0.7:
            fruit = self.crop_cfg.get("tint") or (200, 60, 50)
            import random as _r
            rng = _r.Random(7)   # 매 프레임 같은 자리에 맺히도록 고정 시드
            n = 4 if ratio < 1.0 else 7
            for _ in range(n):
                ang = rng.uniform(0, 6.28)
                dist = rng.uniform(0.2, 0.9) * canopy_r
                fx = int(cx + dist * math.cos(ang))
                fy = int(cy + dist * math.sin(ang) * 0.85)
                pygame.draw.circle(screen, fruit, (fx, fy), 5)
                pygame.draw.circle(screen, (255, 240, 220), (fx - 1, fy - 1), 1)

    def draw_crop(self, screen, x, y, growth_stage, crop_idx=0):
        # Individual growth variation per crop
        offset_val = self.crop_offsets[crop_idx] if crop_idx < len(self.crop_offsets) else 0
        adj_stage = max(0, growth_stage + offset_val)

        # 싹(stage >= 5)이 나기 전 — 씨앗 단계.
        # 당근은 밭 이미지에 구워진 주황 씨앗을 그대로 쓰고, 다른 작물은 전용 씨앗으로 갈아 그린다.
        if adj_stage < 5:
            if game_state.crop != "carrot":
                self._draw_seeds(screen, x, y)
            return

        # 싹이 돋아나면 밭 이미지의 주황색 씨앗 픽셀을 가리기 위해 흙 패치 마스킹 렌더링
        screen.blit(sprites["dirt_patch"], (x - 13, y - 12))

        if game_state.crop == "rice" and adj_stage < self.growth_goal:
            # 벼의 성장기: 일반 잎사귀 스프라이트 대신 뾰족하고 길게 서 자라는 벼 잎사귀 다발을 그린다
            if adj_stage < 10:
                pygame.draw.line(screen, (80, 160, 90), (x, y + 8), (x - 4, y - 1), 2)
                pygame.draw.line(screen, (90, 175, 100), (x, y + 8), (x, y - 6), 2)
                pygame.draw.line(screen, (80, 160, 90), (x, y + 8), (x + 4, y - 1), 2)
            elif adj_stage < 16:
                pygame.draw.line(screen, (70, 145, 80), (x, y + 8), (x - 7, y - 8), 2)
                pygame.draw.line(screen, (85, 165, 95), (x, y + 8), (x - 2, y - 14), 2)
                pygame.draw.line(screen, (85, 165, 95), (x, y + 8), (x + 2, y - 14), 2)
                pygame.draw.line(screen, (70, 145, 80), (x, y + 8), (x + 7, y - 8), 2)
            else:
                pygame.draw.line(screen, (60, 135, 70), (x, y + 8), (x - 12, y - 16), 2)
                pygame.draw.line(screen, (75, 150, 85), (x, y + 8), (x - 5, y - 24), 2)
                pygame.draw.line(screen, (85, 165, 95), (x, y + 8), (x - 1, y - 28), 2)
                pygame.draw.line(screen, (85, 165, 95), (x, y + 8), (x + 2, y - 28), 2)
                pygame.draw.line(screen, (75, 150, 85), (x, y + 8), (x + 6, y - 24), 2)
                pygame.draw.line(screen, (60, 135, 70), (x, y + 8), (x + 12, y - 16), 2)
            return

        if adj_stage < 10:
            sprite, offset = sprites["sprout1"], (-15, 9)
        elif adj_stage < 16:
            sprite, offset = sprites["sprout2"], (-20, -2)
        elif adj_stage < 23:
            sprite, offset = sprites["sprout3"], (-22, -12)
        elif adj_stage < self.growth_goal:
            sprite, offset = sprites["sprout4"], (-24, -18)
        else:
            if game_state.crop == "potato":
                # 감자: 감자가 다 자라면 잎이 누렇게 시들고 아래로 처짐
                orig_spr = sprites["sprout4"]
                withered = orig_spr.copy()
                tint = pygame.Surface(withered.get_size(), pygame.SRCALPHA)
                tint.fill((160, 150, 40, 95))
                withered.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                sh = withered.get_height()
                withered = pygame.transform.scale(withered, (withered.get_width(), int(sh * 0.85)))
                
                sprite, offset = withered, (-24, -18 + int(sh * 0.15))
                screen.blit(sprite, (x + offset[0], y + offset[1]))
                
                # 흙 아래 드러난 감자알들
                pygame.draw.ellipse(screen, (78, 52, 32), (x - 15, y - 1, 14, 9))
                pygame.draw.ellipse(screen, (150, 108, 66), (x - 14, y - 2, 12, 7))
                pygame.draw.ellipse(screen, (78, 52, 32), (x + 1, y + 2, 12, 8))
                pygame.draw.ellipse(screen, (150, 108, 66), (x + 2, y + 1, 10, 6))
                return
            elif game_state.crop == "rice":
                # 벼: 황금빛 벼 이삭과 노랗게 익은 벼잎 연출
                orig_spr = sprites["sprout4"]
                golden = orig_spr.copy()
                tint = pygame.Surface(golden.get_size(), pygame.SRCALPHA)
                tint.fill((210, 185, 45, 120))
                golden.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                
                sprite, offset = golden, (-24, -18)
                screen.blit(sprite, (x + offset[0], y + offset[1]))
                
                gold_dark = (190, 160, 40)
                gold_light = (245, 220, 95)
                pygame.draw.line(screen, gold_dark, (x, y - 5), (x - 14, y + 3), 2)
                for dx, dy in [(-8, -1), (-11, 1), (-14, 3)]:
                    pygame.draw.circle(screen, gold_light, (x + dx, y + dy), 2)
                pygame.draw.line(screen, gold_dark, (x, y - 8), (x + 14, y + 2), 2)
                for dx, dy in [(8, -3), (11, -1), (14, 2)]:
                    pygame.draw.circle(screen, gold_light, (x + dx, y + dy), 2)
                pygame.draw.line(screen, gold_dark, (x + 2, y - 12), (x - 4, y - 2), 2)
                for dx, dy in [(0, -9), (-2, -5), (-4, -2)]:
                    pygame.draw.circle(screen, gold_light, (x + dx, y + dy), 2)
                return
            else:
                sprite, offset = sprites["carrot"], (-24, -45)
        screen.blit(sprite, (x + offset[0], y + offset[1]))

    def draw_farm_plot(self, screen):
        plot_rect = pygame.Rect(44, 140, 362, 318)
        
        # Draw base panel backplate
        draw_light_panel(screen, plot_rect)

        # 1. Render field
        if self.is_tree:
            # 나무류는 6구덩이 밭 이미지 대신, 구덩이 없는 민 흙바닥에 한 그루만 심는다
            self._draw_plain_soil(screen, plot_rect)
        elif game_state.crop == "rice":
            # 벼는 관개농업(논)을 시각적으로 묘사한다
            self._draw_paddy_field(screen, plot_rect)
        elif "field_bed" in sprites:
            screen.blit(sprites["field_bed"], (plot_rect.x, plot_rect.y))
        else:
            # Fallback 3D-ish drawing in case file fails to load
            inner_plot = pygame.Rect(66, 168, 318, 256)
            sc = self.season_colors
            base_color = (110, 75, 45) if self.moisture > 72 else (135, 92, 60) if self.moisture < 28 else sc["dirt"]
            frame_rect = inner_plot.inflate(16, 16)
            pygame.draw.rect(screen, (40, 30, 25), frame_rect.move(0, 4), border_radius=18)
            pygame.draw.rect(screen, (132, 83, 48), frame_rect, border_radius=18)
            pygame.draw.rect(screen, (185, 125, 80), frame_rect, 3, border_radius=18)
            pygame.draw.rect(screen, (65, 42, 28), inner_plot.inflate(2, 2), 2, border_radius=14)
            bed_bg_color = (80, 52, 36) if self.moisture > 72 else (100, 66, 46) if self.moisture < 28 else sc["dirt_dark"]
            pygame.draw.rect(screen, bed_bg_color, inner_plot, border_radius=12)
            pw, ph = 88, 92
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x - pw // 2, y + 12 - ph // 2
                patch_rect = pygame.Rect(px, py, pw, ph)
                pygame.draw.rect(screen, sc["dirt_dark"], patch_rect.move(0, 3), border_radius=12)
                pygame.draw.rect(screen, base_color, patch_rect, border_radius=12)
                pygame.draw.rect(screen, mix_color(base_color, (255, 235, 180), 0.16), patch_rect, 2, border_radius=12)

        # 2. Draw moisture-specific visual clues over the patches (구덩이 밭에서만)
        if not self.is_tree and game_state.crop != "rice" and self.moisture < 28:
            # Draw tiny cracking lines in the soil patches
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x, y + 12
                pygame.draw.line(screen, (82, 53, 35), (px - 22, py - 14), (px - 10, py - 8), 2)
                pygame.draw.line(screen, (82, 53, 35), (px + 10, py + 14), (px + 22, py + 18), 2)
        elif not self.is_tree and game_state.crop != "rice" and self.moisture > 72:
            # Draw wet puddle reflections under crops
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x - 18, y + 36
                pygame.draw.ellipse(screen, (95, 130, 155), (px, py, 36, 6))

        # 3. Draw actual crop sprites
        growth_stage = max(0, min(self.growth, self.growth_goal))
        if self.is_tree:
            # 나무류(사과 등)는 밭 구덩이가 아니라 한 그루의 나무로 자란다
            self._draw_tree(screen, self.growth / max(1, self.growth_goal))
        else:
            for idx, (x, y) in enumerate(self.crop_positions()):
                self.draw_crop(screen, x, y, growth_stage, idx)

        # 4. Draw weeds & bugs on top of the scene
        # 손맛 인터랙션 중에는 배경 잡초/벌레를 숨긴다 — 뽑을/잡을 '대상'과 헷갈리지 않게.
        if self.interaction is None:
            if not self.no_weeds and self.weeds > 32:
                weed_count = 2 if self.weeds < 55 else 4
                weed_spots = [(86, 373), (258, 371), (348, 262), (166, 264)]
                for x, y in weed_spots[:weed_count]:
                    screen.blit(sprites["weed"], (x, y))

            if self.pests > 32:
                bug_count = 1 if self.pests < 55 else 3
                bug_spots = [(150, 228), (284, 336), (332, 220)]
                for x, y in bug_spots[:bug_count]:
                    screen.blit(sprites["bug"], (x, y))

    def draw(self, screen):
        # #7 Seasonal tiled background
        sc = self.season_colors
        draw_tiled_background(screen, 800, 600, sc["grass"], sc["grass_dark"],
                              sc["dirt"], sc["dirt_dark"])

        # Draw glowing fireflies (dream particles) in the sky
        import math
        for f in self.fireflies:
            # Alpha changes smoothly using Sine
            alpha = int(120 + 80 * math.sin(f['scale_timer']))
            alpha = max(0, min(255, alpha))
            
            glow_color = (255, 235, 140)
            glow_surf = pygame.Surface((int(f['size'] * 6), int(f['size'] * 6)), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (glow_color[0], glow_color[1], glow_color[2], int(alpha * 0.45)), (int(f['size'] * 3), int(f['size'] * 3)), int(f['size'] * 2.5))
            pygame.draw.circle(glow_surf, (255, 255, 200, alpha), (int(f['size'] * 3), int(f['size'] * 3)), int(f['size'] * 1.1))
            screen.blit(glow_surf, (int(f['x'] - f['size'] * 3), int(f['y'] - f['size'] * 3)))

        self.draw_farm_plot(screen)

        # Real-world time tint
        hour = datetime.datetime.now().hour
        tint = pygame.Surface((800, 600), pygame.SRCALPHA)
        if 4 <= hour <= 6:
            tint.fill((30, 20, 60, 70))
        elif 17 <= hour <= 19:
            tint.fill((100, 40, 0, 50))
        elif hour >= 20 or hour <= 3:
            tint.fill((10, 15, 30, 100))

        if hour < 7 or hour >= 17:
            screen.blit(tint, (0, 0))

        title_font = get_font(20)
        season_name = get_season(self.growth, self.growth_goal)
        # #10 Dad mode title
        if game_state.dad_mode:
            prefix = f"[{season_name}] 아버지의 밭 "
        else:
            prefix = f"[{season_name}] {self.day}일째 "
            
        prefix_surf = title_font.render(prefix, True, TEXT_DARK)
        weather_text = f"{game_state.weather} ({game_state.weather_turns_left}일간)"
        weather_surf = title_font.render(weather_text, True, TEXT_DARK)
        
        title_rect = pygame.Rect(50, 82, 350, 48)
        draw_wood_panel(screen, title_rect)
        
        total_w = prefix_surf.get_width() + 25 + weather_surf.get_width()
        tx = title_rect.centerx - total_w // 2
        ty = title_rect.centery - prefix_surf.get_height() // 2
        
        screen.blit(prefix_surf, (tx, ty))
        draw_weather_icon(screen, game_state.weather, tx + prefix_surf.get_width(), ty + 2, 20)
        screen.blit(weather_surf, (tx + prefix_surf.get_width() + 25, ty))

        self.draw_field_summary(screen)
        self.draw_meters(screen)
        # 액션 메뉴가 열렸을 땐 '닫기' 알약이 들어갈 자리만큼 패널을 조금 더 길게
        panel_h = 176 if self.action_menu_open else 164
        action_panel = pygame.Rect(430, 300, 320, panel_h)
        draw_light_panel(screen, action_panel)
        action_title = get_font(20).render("오늘 할 일", True, TEXT_DARK)
        screen.blit(action_title, (450, 306))

        # Weather forecast (drawn icon + text, no emoji)
        forecast_font = get_font(14)
        fc_text = f"예보: {game_state.next_weather} ({game_state.weather_turns_left}일 뒤)"
        fc = forecast_font.render(fc_text, True, TEXT_MUTED)
        fc_x = 738 - fc.get_width()
        screen.blit(fc, (fc_x, 308))
        draw_weather_icon(screen, game_state.next_weather, fc_x - 22, 306, 16)

        for btn in self.buttons:
            btn.draw(screen)
        self.draw_action_scrollbar(screen)

        draw_top_bar(screen, show_stats=False)

        # 통합 '속마음' 한 줄 — 밭과 하단바 사이 빈 공간에 겹치지 않게 표시
        if self.thought_text:
            tf = get_font(15)
            alpha = 1.0 if self.thought_timer > 1.0 else max(0.0, self.thought_timer)
            line = wrap_text(self._cropify(self.thought_text), tf, 330, max_lines=1)[0]
            ts = tf.render(line, True, (245, 232, 198))
            pad = 12
            pill_w = ts.get_width() + pad * 2
            pill_h = ts.get_height() + 8
            px = 225 - pill_w // 2
            py = 460
            pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
            pill.fill((28, 24, 20, int(205 * alpha)))
            pygame.draw.rect(pill, (150, 120, 80, int(220 * alpha)), (0, 0, pill_w, pill_h), 1, border_radius=8)
            screen.blit(pill, (px, py))
            ts.set_alpha(int(255 * alpha))
            screen.blit(ts, (px + pad, py + 4))

        # 하단바: 1줄 = 방금 일어난 일, 2줄 = 지금 밭의 증상 (작물명으로 치환)
        draw_bottom_bar(screen, "농장 일지", self._cropify(f"{self.message}\n{self.notice}"))

        # 강제 기다리기 돌발 상황 배너 및 타이머 표시
        if self.forced_wait_active:
            import math
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((200, 30, 30, int(20 + 20 * pulse)))
            screen.blit(overlay, (0, 0))
            
            # 상단 타이머 박스
            timer_box = pygame.Rect(220, 20, 360, 42)
            draw_panel(screen, timer_box, fill=(255, 230, 230), border=(200, 50, 50))
            
            timer_font = get_font(16)
            timer_text = f"돌발 상황 해결 중! 남은 시간: {self.forced_wait_timer:.1f}초"
            ts = timer_font.render(timer_text, True, (200, 30, 30))
            screen.blit(ts, (400 - ts.get_width() // 2, 31))

        # 손맛 인터랙션 오버레이 (모든 것 위에)
        if self.interaction:
            self.interaction.draw(screen)

        if self.tutorial_active:
            self.draw_tutorial(screen)

    def draw_tutorial(self, screen):
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((10, 12, 18, 185))
        screen.blit(overlay, (0, 0))

        title, body = self.TUTORIAL_PAGES[self.tutorial_step]
        title = self._cropify(title)
        body = self._cropify(body)
        card = pygame.Rect(150, 195, 500, 210)
        draw_light_panel(screen, card)

        title_surf = get_font(23).render(title, True, TEXT_DARK)
        screen.blit(title_surf, (card.centerx - title_surf.get_width() // 2, card.y + 26))
        pygame.draw.rect(screen, (221, 173, 96),
                         (card.centerx - 60, card.y + 58, 120, 3), border_radius=2)

        body_font = get_font(17)
        y = card.y + 78
        for line in wrap_text(body, body_font, card.w - 56):
            ls = body_font.render(line, True, TEXT_DARK)
            screen.blit(ls, (card.x + 28, y))
            y += body_font.get_height() + 7

        step_txt = f"{self.tutorial_step + 1} / {len(self.TUTORIAL_PAGES)}   ·   클릭하여 계속"
        ss = get_font(14).render(step_txt, True, TEXT_MUTED)
        screen.blit(ss, (card.centerx - ss.get_width() // 2, card.bottom - 32))
