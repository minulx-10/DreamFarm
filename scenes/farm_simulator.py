import random
import pygame
from core.game_state import (
    append_josa, game_state, pick_action_echo, pick_failure_echo,
    check_epiphany, advance_weather, get_understanding_stage,
    WEATHER_DATA, STORY_EVENTS, WEATHER_WISDOM, SILENT_GIFTS,
    pick_sensory, get_silent_gift, reveal_gift, check_recovery,
    track_attitude, get_season_colors, get_season,
    check_father_day,
)
from core.narrative_data import YEAR_SEEDS, roll_year_seed
from core import audio
from core import save_system
from core import i18n
from core import behavior
from core.crops import farm_config, swap_crop_word, current_crop

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

# '밭 정리' 돌발 상황 진입 문구
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

# ── 회상 조각 — 이해도 구간별 공용 풀 (key, 제목, 본문) ────────────────────────
# 본문은 tnar 로 이름 조사({name_eun}·{name_ga})와 작물 치환이 적용된다.
# key 는 회차 안 중복 방지용 — 'first'/'second'는 구간이 올라도 같은 슬롯(식탁 서사)이라
# 회차당 하나만 나온다(의도).
MEMORY_POOLS = {
    "low": [
        (
            "first",
            "희미한 식탁",
            "식탁 위에 당근 반찬이 놓여 있다.\n{name_eun} 젓가락으로 그릇을 밀어냈고, 아버지는 잠깐 말을 멈췄다.\n그때는 그 침묵이 왜 길게 느껴졌는지 몰랐다.",
        ),
        (
            "low_market",
            "장바구니 소리",
            "비닐봉지가 문고리에 부딪히는 소리가 난다.\n아버지는 흙 묻은 당근을 꺼내며 '오늘 건 달다'고 말했다.\n{name_eun} 대답 대신 물컵만 만지작거렸다.",
        ),
        (
            "second",
            "남긴 접시",
            "싱크대 옆에 남은 반찬 그릇이 보인다.\n작은 주황색 조각들이 물에 젖어 천천히 가라앉는다.\n어쩐지 꿈속의 흙냄새가 더 짙어진다.",
        ),
    ],
    "mid": [
        (
            "first",
            "다시 보이는 식탁",
            "당근 반찬을 밀어내던 손이 떠오른다.\n{name_eun} 그때 아버지의 표정보다 자기 입맛만 먼저 생각했다는 걸 알아차린다.",
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
    ],
    "high": [
        (
            "first",
            "따뜻한 식탁",
            "식탁 위의 당근 반찬이 떠오른다.\n이번에는 밀어내고 싶다는 생각보다, 한 번쯤 제대로 맛보고 싶다는 마음이 먼저 든다.",
        ),
        (
            "high_field",
            "손등의 흙",
            "아버지가 웃으며 손등의 흙을 털어낸다.\n그 모습은 무겁기보다 다정하다.\n꿈속의 밭도 조금은 덜 낯설게 느껴진다.",
        ),
        (
            "second",
            "짧은 고개 끄덕임",
            "{name_ga} 말없이 고개를 끄덕인다.\n무언가를 완전히 알게 된 건 아니지만, 이제 외면하고 싶지는 않다.",
        ),
    ],
}

# ── 작물 서사 팩 — 작물별 고유 회상 (그 작물을 기를 때만 풀에 섞인다) ─────────────
CROP_MEMORY_POOLS = {
    "apple": {
        "low": [(
            "apple_low",
            "심긴 지 오래된 나무",
            "이 나무는 내가 태어나기 전부터 있었다고 했다.\n아버지는 나무 나이를 셀 때 꼭 내 나이를 같이 셌다.\n그때는 그게 무슨 뜻인지 몰랐다.",
        )],
        "mid": [(
            "apple_mid",
            "그늘의 크기",
            "사과나무 그늘이 해마다 조금씩 넓어졌다고 했다.\n{name_eun} 그 그늘 아래서 낮잠만 잤다.\n그늘을 키운 시간은 생각하지 못했다.",
        )],
        "high": [(
            "apple_high",
            "기다림의 나이테",
            "열매는 심은 해에 열리지 않는다.\n몇 해를 그냥 물만 주는 시간이 있다.\n아버지의 기다림도 그런 것이었을까.",
        )],
    },
    "potato": {
        "low": [(
            "potato_low",
            "흙 속의 일",
            "감자밭은 겉보기엔 아무 일도 없어 보였다.\n{name_ga} 왜 매일 나가느냐고 물으면, 아버지는 웃기만 했다.",
        )],
        "mid": [(
            "potato_mid",
            "보이지 않는 성실",
            "흙 위로는 잎만 보인다.\n정작 굵어지는 것은 보이지 않는 곳에 있다.\n아버지의 하루도 그랬다.",
        )],
        "high": [(
            "potato_high",
            "캐 보기 전에는",
            "캐 보기 전에는 모른다고, 아버지가 말했다.\n믿고 북돋는 수밖에 없다고.\n그 말이 감자 얘기만은 아니었음을 이제 안다.",
        )],
    },
    "rice": {
        "low": [(
            "rice_low",
            "물 대는 소리",
            "새벽마다 물꼬 트는 소리가 났다.\n{name_eun} 그 소리를 자장가처럼 들으며 다시 잠들었다.",
        )],
        "mid": [(
            "rice_mid",
            "이웃의 논",
            "논일은 혼자 하는 일이 아니라고 했다.\n물은 위 논에서 아래 논으로 흐르니까.\n아버지가 이웃 어른들과 나누던 인사가 떠오른다.",
        )],
        "high": [(
            "rice_high",
            "밥 한 공기",
            "밥 한 공기가 되기까지 아흔아홉 번 손이 간다고 했다.\n남긴 밥알을 보던 아버지의 눈을,\n이제 조금은 마주할 수 있을 것 같다.",
        )],
    },
}


def all_memory_titles():
    """갤러리 '기억' 컬럼에 보일 전체 회상 제목 (공용 + 작물 팩, 정의 순서대로)."""
    titles = [t for tier in ("low", "mid", "high") for _, t, _ in MEMORY_POOLS[tier]]
    for crop_pools in CROP_MEMORY_POOLS.values():
        for tier in ("low", "mid", "high"):
            titles += [t for _, t, _ in crop_pools.get(tier, [])]
    return titles


class FarmSimulator:
    def __init__(self):
        self.crop_cfg = farm_config()
        self.is_tree = self.crop_cfg.get("family") == "나무류"
        self.no_weeds = self.crop_cfg.get("no_weeds", False)
        self.day = 1
        self.growth = 0
        self.growth_goal = self.crop_cfg["growth_goal"]
        
        # 벼(논)는 처음부터 물을 가득 대어 심는다 — 실제 무논처럼 물이 찰랑이는 상태로 시작.
        self.moisture = 80 if game_state.crop == "rice" else 44
        self.health = 66
        self.weeds = 0 if self.no_weeds else 25
        self.pests = 14
        self.drainage = 55
        self.stress = 0
        self.actions_taken = 0
        self.last_action = ""
        self.message = self._cropify("낯선 밭에서 눈을 떴다.")
        self.notice = self._cropify("밭의 상태부터 천천히 살펴보자.")

        # '해의 성격' — 이 회차의 날씨 기질. 평년이 아니면 첫 안내로 귀띔한다.
        game_state.year_seed = roll_year_seed()
        game_state.run_stats = {}
        if game_state.year_seed != "평년":
            self.notice = YEAR_SEEDS[game_state.year_seed]["desc"]

        # 도전 규칙 (crop_select 에서 선택 — 없으면 None)
        ch = getattr(game_state, "challenge", None)
        if ch == "drought":
            game_state.year_seed = "가뭄해"
            game_state.weather = "가뭄"
            game_state.next_weather = "가뭄"
            self.notice = "한발 — 이 해엔 가뭄이 걷히지 않는다. 물이 곧 생명이다."
        elif ch == "seven_days":
            self.growth_goal = max(10, int(self.growth_goal * 0.55))
            self.notice = "이레 — 여드레 안에 수확까지 마쳐야 한다."
        elif ch == "no_journal":
            self.notice = "무일지 — 밭의 상태는 손끝의 감으로만 읽어야 한다."

        # 행동 데이터 — 새 회차 로그 시작 (도전 규칙 반영 뒤의 최종 seed로)
        behavior.start_run(game_state.crop, game_state.year_seed, ch)

        # 계절 전환 배너 상태
        self.last_season = get_season(self.growth, self.growth_goal)
        self.season_banner = ""
        self.season_banner_timer = 0.0
        self.memory_cooldown = 1
        self.minigame_cooldown = 3       # '밭 정리' 돌발 상황 사이의 최소 간격
        self.weather_minigame_cooldown = 2  # 날씨 미니게임 쿨다운 (2턴 후부터 발동 가능)
        self.special_cooldown = random.randint(3, 5)   # 특별 이벤트('별 잇기')까지 남은 턴
        self.special_done = False                       # 특별 이벤트는 한 게임에 한 번만
        self.withers = 0                 # 작물이 완전히 시든 횟수 (3이면 끝내 시듦 — 배드엔딩)
        self.weak_turns = 0              # 비실비실(저체력)하게 흘려보낸 턴 — 오래 가면 끝내 시든다
        self.mistakes = 0
        self.memories_seen = set()
        
        # 기다림 시스템: 마지막 '기다리기' 이후 흐른 턴 — 5턴을 넘기면 밭이 강제로 손을 멈추게 한다
        self.turns_since_wait = 0
        
        # 통합 '속마음' 표시 채널
        self.thought_text = ""
        self.thought_timer = 0.0
        self.thought_queue = []
        
        # Individual crop growth offsets (randomized per plot)
        self.crop_offsets = [random.randint(-2, 2) for _ in range(6)]
        
        # #10 Dad mode turn counter
        self.dad_turns_done = 0
        self.stories_seen = set()
        self.story_cooldown = 2

    def action_label(self, action):
        """작물에 따라 같은 행동도 다른 이름으로 보인다 (벼: 물 대기, 사과나무: 가지치기)."""
        return self.crop_cfg["labels"].get(action, action)

    def _cropify(self, text):
        """밭 텍스트 속 '당근'을 지금 기르는 작물 이름으로 (조사까지) 바꾼다."""
        return swap_crop_word(text, self.crop_cfg.get("food", "당근"))

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

        if self.is_tree:
            fillers = ["흙 북돋기", "물 주기", "해충 살피기"]
        else:
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

    def push_thought(self, text, dur=4.5):
        if not text:
            return
        self.thought_queue.append((text, dur))
        if len(self.thought_queue) > 2:
            self.thought_queue = self.thought_queue[-2:]

    def do_action(self, action, farm_scene):
        if action == "수확하기":
            if self.is_harvest_ready():
                audio.play("click")
                behavior.log("action", kind="수확하기", day=self.day)
                game_state.understanding += 12
                game_state.final_health = self.health
                game_state.farm_mistakes = self.mistakes
                game_state.final_day = self.day   # 회차 아카이브용 (며칠 만에 수확했나)
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
                self.message = self._cropify("아직 덜 자랐다. 성급하면 다 망친다.")
                self.notice = self._cropify("밭부터 돌보며 더 기다리자.")
            return

        from scenes.farm import TACTILE_INTERACTIONS
        if (action in TACTILE_INTERACTIONS and farm_scene.interactions_enabled
                and not farm_scene.tutorial_active):
            farm_scene.interaction = TACTILE_INTERACTIONS[action](farm_scene)
            farm_scene.interaction_action = action
            return

        self._run_action(action, farm_scene)

    def _run_action(self, action, farm_scene, quality=None):
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
        # 손길 통계 (창고 탭 누적 통계의 원천)
        game_state.run_stats[action] = game_state.run_stats.get(action, 0) + 1
        behavior.log("action", kind=action, day=self.day)
        difficulty = 1 + self.growth // 6
        result, is_fail = self.apply_action(action, difficulty, quality)
        self.apply_field_pressure(difficulty, farm_scene)
        self.apply_weather_effects()

        track_attitude(action, is_fail, self.is_good_turn())

        if self.health <= 20:
            self.mistakes += 1
            result += " 당근이 버티지 못하고 시든다."
        elif self.health < 38:
            if not is_fail and action not in ("살펴보기", "기다리기"):
                if action == "흙 북돋기":
                    result += (" 아직 기운이 없어 자라진 못하지만, 거름을 주니 조금씩 살아난다." if self.is_tree
                               else " 아직 기운이 없어 자라진 못하지만, 흙을 북돋우니 조금씩 살아난다.")
                else:
                    result += (" 아직 기운이 없어 자라지는 못한다. 거름을 주어 기운부터 채우자." if self.is_tree
                               else " 아직 기운이 없어 자라지는 못한다. 흙을 북돋아 기운부터 채우자.")
        else:
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

        recovery_msg = check_recovery(action, is_fail)
        thought = ""
        if is_fail:
            thought = pick_failure_echo(action)
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

        self.message = self._cropify(result)
        self.notice = self._cropify(self.build_notice())
        self.clamp_stats()

        if self.health < 38:
            self.weak_turns += 1
        elif self.health >= 45:
            self.weak_turns = 0

        farm_scene.season_colors = get_season_colors(self.growth, self.growth_goal)

        # 계절이 넘어가는 턴 — 잔잔한 전환 배너 (모든 계절 이름이 받침으로 끝나 '이'로 고정)
        cur_season = get_season(self.growth, self.growth_goal)
        if cur_season != self.last_season:
            self.last_season = cur_season
            self.season_banner = cur_season
            self.season_banner_timer = 3.2
            audio.play("page")

        if self.day % 5 == 0:
            self._write_journal()

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
            self.try_trigger_minigame(action, farm_scene)
        farm_scene.rebuild_buttons()

        if save_system.get_setting("autosave"):
            save_system.save_game(farm_scene)

    def apply_action(self, action, difficulty, quality=None):
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
            # 체력이 낮을수록 회복을 크게 준다 — 안 그러면 잡초·해충 압박(같은 턴에 적용)에 상쇄돼
            # '흙 북돋기를 해도 살아나지 않는' 죽음의 소용돌이가 생긴다. 잘 해내면 압박을 넘어 회복.
            base = 15 if self.health < 40 else 8
            if quality is not None:
                frac = quality.get("cleared_frac", 1.0)
                self.health += max(5, int(base * frac))
                self.stress = max(0, self.stress - max(2, int(10 * frac)))
                self.drainage += int(4 * frac)
                if frac >= 0.85:
                    return ("거름을 골고루 주니 한결 생기가 돈다." if self.is_tree
                            else "흙을 두둑이 북돋우니 한결 생기가 돈다."), False
                if frac >= 0.45:
                    return ("거름을 어느 정도 주었다." if self.is_tree
                            else "흙을 어느 정도 다독였다."), False
                return ("거름이 부족해 뿌리가 아직 허전하다." if self.is_tree
                        else "북돋다 말아 뿌리가 아직 허전하다."), False
            if self.health < 65 or self.stress > 24:
                self.health += base
                self.stress = max(0, self.stress - 10)
                self.drainage += 4
                return ("거름을 주니 한결 생기가 돈다." if self.is_tree
                        else "흙을 다독이니 한결 생기가 돈다."), False
            self.health += 2
            self.moisture -= 4
            return ("거름을 조금 주었지만 큰 변화는 없다." if self.is_tree
                    else "흙을 만졌지만 큰 변화는 없다."), False

        if action == "기다리기":
            if self.is_good_turn():
                self.moisture -= 8
                return "조용히 기다린다. 당근이 제 속도로 자란다.", False
            self.health -= 8 + difficulty
            self.stress += 8
            self.mistakes += 1
            return "기다리기엔 밭이 너무 불안하다.", True

        return "...", False

    def apply_field_pressure(self, difficulty, farm_scene):
        # 행동 데이터 — 하루 마감 시점의 밭 상태 (지난 하루의 마감 수치)
        behavior.log("day_end", day=self.day,
                     growth=self.growth,
                     moisture=self.moisture,
                     health=self.health,
                     weeds=self.weeds,
                     drainage=self.drainage)
        self.day += 1
        # 도전 '이레' — 여드레를 넘기면 밭이 계절을 놓친다 (시듦 엔딩)
        if (getattr(game_state, "challenge", None) == "seven_days"
                and self.day > 8 and not self.is_harvest_ready()):
            game_state.crop_failed = True
            game_state.final_health = max(0, self.health)
            game_state.farm_mistakes = self.mistakes
            game_state.final_day = self.day
            game_state.transition_text = (
                "[여드레가 지났다]\n\n"
                "짧은 해는 기다려 주지 않았다.\n"
                "다음에는 더 빠르고, 더 정확해야 한다."
            )
            game_state.transition_next = "ending"
            game_state.is_clear_transition = False
            game_state.current_scene = "transition"
            return
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
        if self.health < 28:
            neglected = self.weeds > 52 or self.pests > 46
            dmg = int(dmg * (0.9 if neglected else 0.45))
        self.health -= dmg
        if random.random() < 0.18 + difficulty * 0.04:
            self.drainage -= random.randint(4, 10)

        game_state.weather_turns_left -= 1
        if game_state.weather_turns_left <= 0:
            old_weather = game_state.weather
            advance_weather()
            new_weather = game_state.weather
            if new_weather != old_weather and new_weather in WEATHER_WISDOM:
                self.push_thought(WEATHER_WISDOM[new_weather], dur=5.0)

        # 행동 성향 문구 — 습관이 뚜렷해지면 이따금 밭이 알은체한다
        if self.day % 4 == 0 and random.random() < 0.25:
            from core.narrative_data import pick_behavior_echo
            echo = pick_behavior_echo(behavior.profile())
            if echo:
                self.push_thought(echo, dur=5.0)

    def apply_weather_effects(self):
        w = WEATHER_DATA.get(game_state.weather, {})
        self.moisture += w.get("moisture", 0)
        self.stress += w.get("stress", 0)
        self.drainage += w.get("drainage", 0)
        self.health += w.get("health", 0)
        self.pests += w.get("pests", 0)

    def try_trigger_story(self):
        seen = len(self.stories_seen)
        forced = (self.growth >= 5 and seen == 0) or (self.growth >= 11 and seen < 2)
        if not forced:
            if self.story_cooldown > 0:
                self.story_cooldown -= 1
                return
            if random.random() > 0.32 * behavior.event_weight("story"):
                return
        # 작물 전용 이벤트("crop" 키)는 그 작물을 기를 때만, "not_crop"은 그 작물이 아닐 때만
        available = [e for i, e in enumerate(STORY_EVENTS)
                     if i not in self.stories_seen
                     and e.get("crop") in (None, game_state.crop)
                     and e.get("not_crop") != game_state.crop]
        if not available:
            return
        # 회차 간 비반복 — 지난 회차들(갤러리 기록)에서 아직 안 겪은 이벤트를 우선한다
        meta_seen = set(save_system.load_meta().get("stories_seen", []))
        fresh = [e for e in available
                 if e["title"] not in meta_seen and self._cropify(e["title"]) not in meta_seen]
        event = random.choice(fresh or available)
        self.stories_seen.add(STORY_EVENTS.index(event))
        self.story_cooldown = 4
        game_state.choice_data = event
        behavior.log("event_seen", kind="story", title=event["title"], day=self.day)
        game_state.current_scene = "story_choice"

    def _write_journal(self):
        season = get_season(self.growth, self.growth_goal)
        # 일지는 한국어 원문으로 저장하고 '표시 시점'에 현재 언어로 번역한다(엔딩에서 언어를 바꿔도
        # 즉시 반영되도록 — ending._localize_journal_line 참고).
        lines = [f"[{self.day}일째 · {season} · {game_state.weather}]"]
        if not game_state.journal_entries and game_state.year_seed != "평년":
            # 첫 장에는 그 해의 기질을 적어 둔다 (가뭄해·장마해 …)
            lines.append(YEAR_SEEDS[game_state.year_seed]["desc"])
        if self.moisture > 75:
            lines.append("오늘 물을 너무 많이 줬다.")
        elif self.moisture < 25:
            lines.append("흙이 바짝 말라 있었다.")
        else:
            lines.append("수분은 적당했다.")
        
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
        
        if self.health < 45:
            lines.append("당근이 많이 힘들어 보였다.")
        elif self.health >= 78:
            lines.append("당근 잎에 윤기가 돌기 시작했다.")
        
        if self.mistakes > 3:
            lines.append("실수가 잦았다. 아직 모르는 것이 많다.")
        
        prog = int(min(1.0, self.growth / self.growth_goal) * 100)
        lines.append(f"여기까지 성장 {prog}%. 수확이 가까워진다." if prog >= 60
                     else f"여기까지 성장 {prog}%.")
        
        u = game_state.understanding
        if u < 20:
            lines.append("이걸 왜 해야 하는지 아직 모르겠다.")
        elif u < 40:
            lines.append("조금씩 알 것 같기도 하다.")
        else:
            lines.append("이 일의 무게가 느껴진다.")
        # 정본(당근·밭 원문)으로 저장한다 — 여기서 작물 치환까지 해 버리면 비당근 회차의 일지가
        # EN 카탈로그 키와 안 맞아 영어로 영영 번역되지 않는다. 치환은 표시 시점
        # (_localize_journal_line)에서 언어별로 한다.
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
        # 도전 '무일지' — 정밀 진단이 없다. 감으로 읽으라는 안내만.
        if getattr(game_state, "challenge", None) == "no_journal":
            return "밭이 무슨 말을 하는지, 오늘은 손끝의 감으로 읽어야 한다."
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

        weather_tips = {
            "맑음": "맑은 날엔 수분이 천천히 마른다.",
            "흐림": "흐린 날은 큰 영향이 없다.",
            "비": "비엔 수분이 크게 오른다 — 과습 주의.",
            "가뭄": "가뭄엔 수분이 뚝 떨어진다.",
            "강풍": "강풍은 해충을 날리지만 밭을 들쑤신다.",
        }
        tip = i18n.t(weather_tips.get(game_state.weather, ""))
        status_str = ", ".join(i18n.t(w) for w in warnings[:3]) if warnings else i18n.t("밭이 안정적이다")
        return i18n.tf("자세히 보니 — {status}. {tip}", status=status_str, tip=tip)

    def build_notice(self):
        if self.is_harvest_ready():
            return "다 자랐다. 이제 수확할 때다."
        if self.health < 45:
            if self.is_tree:
                return "당근이 축 처져 기운이 없다. 거름을 주어 기운을 끌어올려 주자."
            return "당근이 축 처져 기운이 없다. 흙을 북돋아 기운을 끌어올려 주자."
        if game_state.crop == "rice":
            if self.moisture < 34:
                return "논바닥이 드러날 만큼 물이 말랐다. 물을 대주자."
            if self.moisture > 92:
                return "논물이 너무 넘친다. 물꼬를 터 물을 빼자."
        else:
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
        chance *= behavior.event_weight("memory")
        # 첫인상 밀도 보장 — 3일째까지 회상을 한 번도 못 만났으면 반드시 한 편을 띄운다
        first_due = (not self.memories_seen) and self.day >= 3
        if forced_key is None and not first_due and random.random() >= chance:
            return

        memory = self.pick_memory(forced_key)
        if not memory:
            return

        key, title, text = memory
        self.memories_seen.add(key)
        self.memory_cooldown = 4 if u < 25 else 6 if u < 50 else 8
        pname = game_state.player_name
        game_state.memory_title = self._cropify(title)   # 제목: 작물 치환(EN은 렌더에서 번역)
        game_state.memory_text = i18n.tnar(text, crop_key=game_state.crop, name=pname,
                                           name_eun=append_josa(pname, "은/는"),
                                           name_ga=append_josa(pname, "이/가"))
        game_state.memory_next = "farm"
        behavior.log("event_seen", kind="memory", day=self.day)
        game_state.current_scene = "memory"

    def pick_memory(self, forced_key):
        u = game_state.understanding
        tier = "low" if u < 18 else "mid" if u < 45 else "high"
        memories = list(MEMORY_POOLS[tier])
        # 작물 서사 팩 — 지금 기르는 작물의 고유 회상이 같은 구간 풀에 섞인다
        memories += CROP_MEMORY_POOLS.get(game_state.crop, {}).get(tier, [])

        if forced_key:
            for memory in memories:
                if memory[0] == forced_key:
                    return memory

        candidates = [memory for memory in memories if memory[0] not in self.memories_seen]
        return random.choice(candidates or memories)

    def try_trigger_minigame(self, action, farm_scene):
        if action in ("살펴보기", "수확하기"):
            return

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
                behavior.log("event_seen", kind="minigame", day=self.day)
                return

        from scenes.tending import WEATHER_MINIGAMES
        if self.weather_minigame_cooldown > 0:
            self.weather_minigame_cooldown -= 1
        elif game_state.weather in WEATHER_MINIGAMES and random.random() < 0.35 * behavior.event_weight("minigame"):
            farm_scene.interaction = WEATHER_MINIGAMES[game_state.weather](farm_scene)
            farm_scene.interaction_action = "__weather__"
            self.weather_minigame_cooldown = 3
            behavior.log("event_seen", kind="minigame", day=self.day)
            return

        if self.minigame_cooldown > 0:
            self.minigame_cooldown -= 1
            return

        if self.weeds < 48 and self.drainage > 38:
            return
        if random.random() >= 0.14:
            return

        game_state.transition_text = random.choice(MINIGAME_INTROS["stage1"])
        game_state.current_scene = "transition"
        game_state.is_clear_transition = False
        game_state.transition_next = "stage1"
        game_state.return_scene = "farm"
        self.minigame_cooldown = 6
        behavior.log("event_seen", kind="minigame", day=self.day)

    def _wilt(self, farm_scene):
        self.withers += 1
        self.weak_turns = 0
        if self.withers >= 3:
            game_state.crop_failed = True
            game_state.final_health = 0
            game_state.farm_mistakes = self.mistakes + 3
            game_state.final_day = self.day
            game_state.transition_text = (
                "[밭이 시들어 버렸다]\n\n"
                "아무리 다독여도 당근은 다시 일어서지 못했다.\n"
                "흙만 남은 두둑을 한참 바라보았다."
            )
            game_state.transition_next = "ending"
            game_state.is_clear_transition = False
            game_state.current_scene = "transition"
            return
        self.health = max(self.health, 28 - self.withers * 6)
        self.stress = 45
        self.mistakes += 2
        game_state.understanding = max(0, game_state.understanding - 8)
        warn = ("이대로면 밭을 잃는다. 한 번만 더 시들면 손쓸 수 없다."
                if self.withers == 2 else "다시 흙부터 천천히 다독여야 한다.")
        self.message = self._cropify("당근이 크게 시들어 버렸다. ") + warn
        self.push_thought("처음부터, 천천히.")
        farm_scene.rebuild_buttons()
