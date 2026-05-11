import random


class GameState:
    def __init__(self):
        self.player_name = "지후"
        self.understanding = 0
        self.score = 0
        self.timer = 0
        self.current_scene = "name_input"
        self.running = True

        self.transition_text = ""
        self.transition_next = ""
        self.is_clear_transition = False
        self.return_scene = "farm"

        self.memory_title = ""
        self.memory_text = ""
        self.memory_next = "farm"

        self.final_health = 100
        self.farm_mistakes = 0

        # Weather system
        self.weather = "맑음"
        self.weather_turns_left = 3
        self.next_weather = "흐림"

        # Journal system
        self.journal_entries = []

        # Epiphany system
        self.epiphanies_seen = set()
        self.pending_epiphany = None

        # Action echo
        self.action_echo = ""

        # Story choice
        self.choice_data = None


game_state = GameState()


# --- Josa helper ---
def append_josa(text, josa_type):
    if not text:
        return text
    last_char = text[-1]
    if ord('가') <= ord(last_char) <= ord('힣'):
        has_batchim = (ord(last_char) - ord('가')) % 28 > 0
        if josa_type == "은/는":
            return text + ("은" if has_batchim else "는")
        if josa_type == "이/가":
            return text + ("이" if has_batchim else "가")
        if josa_type == "을/를":
            return text + ("을" if has_batchim else "를")

    if josa_type == "은/는":
        return text + "는(은)"
    if josa_type == "이/가":
        return text + "가(이)"
    if josa_type == "을/를":
        return text + "를(을)"
    return text


# --- Understanding stage system ---
UNDERSTANDING_STAGES = [
    (0, "낯선 흙냄새", 0),
    (16, "물 주는 이유", 1),
    (31, "기다림의 무게", 2),
    (46, "손등의 온기", 3),
    (56, "한 조각의 시간", 4),
]

EPIPHANY_THRESHOLDS = {
    15: "흙은 차갑지만, 씨앗은 따뜻했다.",
    30: "물을 기다리는 시간이 가장 긴 시간이다.",
    45: "밀어낸 것을 다시 돌려놓을 수 있을까.",
    55: "아버지의 하루가, 내 한 끼였다.",
}

ACTION_ECHOES = {
    "물 주기": {
        "low": ["이 흙에 왜 물을 줘야 하는 거지?", "당근이 이 정도 물을 원하는 건가?"],
        "mid": ["아버지도 이 새벽에 물을 주었을까.", "하루에 몇 번이나 이걸 했을까."],
        "high": ["물소리가 자장가 같다.", "이 흙이 마르지 않게, 매일 이렇게."],
    },
    "잡초 뽑기": {
        "low": ["잡초가 이렇게 빨리 자라나?", "이거 끝이 있기는 한 건가."],
        "mid": ["손이 아프다. 매일 이걸 했다니.", "뽑아도 뽑아도 자라는구나."],
        "high": ["이것도 농사의 일부였구나.", "잡초와 싸우는 게 아니라, 당근을 지키는 거였어."],
    },
    "해충 살피기": {
        "low": ["벌레가 이렇게 많다고?", "이런 걸 맨손으로?"],
        "mid": ["잎 하나하나 뒤집어 보는 게 이런 거였구나.", "작은 것도 그냥 지나치면 안 되는 거구나."],
        "high": ["지키는 일은 늘 조용하고 반복적이다.", "아버지의 손이 거칠었던 이유를 알 것 같다."],
    },
    "배수로 정리": {
        "low": ["물길도 관리해야 하는 거야?", "농사가 이렇게 복잡한 건가."],
        "mid": ["물이 빠질 곳이 없으면 뿌리가 썩는구나.", "보이지 않는 곳까지 신경 써야 하다니."],
        "high": ["물 한 줄기도 흘러갈 곳이 필요하다.", "정성이란 이런 거였구나."],
    },
    "흙 북돋기": {
        "low": ["흙을 왜 또 만져야 하지?", "이게 뭐가 달라지는 건지 모르겠다."],
        "mid": ["흙을 다독이는 일이 이렇게 조용한 일이었구나.", "손끝에 흙이 묻는 감각이 익숙해진다."],
        "high": ["이 흙 아래에 기다림이 묻혀 있다.", "아버지의 하루는 이런 조용함으로 가득했겠지."],
    },
    "기다리기": {
        "low": ["그냥 기다리면 되는 건가?", "아무것도 안 해도 괜찮을까."],
        "mid": ["기다린다는 건, 믿는다는 뜻이었구나.", "조급함을 참는 것도 일의 일부구나."],
        "high": ["기다림 속에서 자라는 건 당근만이 아니었다.", "아버지도 이렇게 기다렸겠지, 매일."],
    },
}

FAILURE_ECHOES = {
    "물 주기": "아버지의 말이 떠오른다. '물이 많다고 좋은 게 아니란다.'",
    "잡초 뽑기": "'필요한 것과 필요 없는 것, 구분이 쉽지 않지.'",
    "해충 살피기": "'서두르면 놓치는 법이다. 천천히 봐라.'",
    "배수로 정리": "'지금 당장 급한 것만 보면, 나중에 더 큰 일이 생긴단다.'",
    "흙 북돋기": "'흙도 쉴 때가 있어야 한다.'",
    "기다리기": "'기다려도 되는 때와 안 되는 때가 있단다.'",
}

WEATHER_DATA = {
    "맑음": {"moisture": -2, "stress": -3, "desc": "하늘이 맑다."},
    "흐림": {"moisture": 0, "stress": 0, "desc": "구름이 끼어 있다."},
    "비": {"moisture": 10, "drainage": -3, "desc": "빗방울이 떨어진다."},
    "가뭄": {"moisture": -8, "health": -3, "desc": "땅이 갈라지고 있다."},
    "강풍": {"pests": -5, "stress": 5, "desc": "바람이 세차게 분다."},
}

STORY_EVENTS = [
    {
        "title": "이웃 밭의 물난리",
        "text": "이웃 밭에서 물이 넘쳐 흘러오고 있다.\n우리 밭도 위험할 수 있다.\n어떻게 해야 할까?",
        "choice_a": ("우리 밭 배수로를 먼저 지킨다", {"understanding": 0, "result_text": "우리 밭은 안전하지만, 이웃 밭이 걱정된다."}),
        "choice_b": ("이웃 밭의 물길을 함께 막는다", {"understanding": 8, "result_text": "함께 막으니 오히려 물길이 잘 잡혔다. 혼자가 아니었다."}),
    },
    {
        "title": "쓰러진 허수아비",
        "text": "강풍에 허수아비가 쓰러졌다.\n새들이 모여들기 시작한다.\n시간이 많지 않다.",
        "choice_a": ("허수아비를 급히 다시 세운다", {"understanding": 2, "result_text": "허수아비를 세웠지만, 대충 세워서 금방 또 쓰러질 것 같다."}),
        "choice_b": ("단단히 고정할 수 있게 돌을 모은다", {"understanding": 6, "result_text": "시간은 걸렸지만 튼튼해졌다. 급할수록 돌아가라는 말이 떠오른다."}),
    },
    {
        "title": "길 잃은 벌",
        "text": "꽃밭을 찾지 못하는 벌 한 마리가\n당근 잎 위에서 힘없이 쉬고 있다.\n해충은 아닌 것 같다.",
        "choice_a": ("내버려 두고 밭일을 계속한다", {"understanding": 1, "result_text": "밭일은 진행되었지만, 자꾸 벌이 신경 쓰인다."}),
        "choice_b": ("근처 꽃밭 쪽으로 조심히 옮겨 준다", {"understanding": 7, "result_text": "벌이 날아간 뒤, 밭 위로 따뜻한 바람이 불었다."}),
    },
]


def get_understanding_stage(value):
    stage = UNDERSTANDING_STAGES[0]
    for threshold, name, phase in UNDERSTANDING_STAGES:
        if value >= threshold:
            stage = (threshold, name, phase)
    return stage


def get_understanding_tier(value):
    if value < 18:
        return "low"
    elif value < 45:
        return "mid"
    else:
        return "high"


def pick_action_echo(action):
    tier = get_understanding_tier(game_state.understanding)
    echoes = ACTION_ECHOES.get(action, {}).get(tier, [])
    if echoes:
        return random.choice(echoes)
    return ""


def pick_failure_echo(action):
    return FAILURE_ECHOES.get(action, "")


def advance_weather():
    weathers = list(WEATHER_DATA.keys())
    game_state.weather = game_state.next_weather
    candidates = [w for w in weathers if w != game_state.weather]
    game_state.next_weather = random.choice(candidates)
    game_state.weather_turns_left = random.randint(3, 5)


def check_epiphany():
    """Check if understanding crossed a threshold. Returns True if epiphany triggered."""
    u = game_state.understanding
    for threshold, text in EPIPHANY_THRESHOLDS.items():
        if u >= threshold and threshold not in game_state.epiphanies_seen:
            game_state.epiphanies_seen.add(threshold)
            game_state.pending_epiphany = text
            return True
    return False
