import random
import json
import os


class GameState:
    def __init__(self):
        self.player_name = "지후"
        self.understanding = 0
        self.score = 0
        self.timer = 0
        self.current_scene = "title"
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
        self.journal_closed = False   # 엔딩별 '마지막 장'을 한 번만 더하기 위한 플래그
        self.crop_failed = False      # 작물이 끝내 시들어 수확 못 하고 끝났는가('시듦' 엔딩)

        # Epiphany system
        self.epiphanies_seen = set()
        self.pending_epiphany = None

        # Action echo
        self.action_echo = ""

        # 최근 보여준 '속마음' 줄 — 같은 말이 연달아 또 나오지 않게 거르는 데 쓴다.
        self.recent_lines = []

        # Story choice
        self.choice_data = None

        # Ending credits run records
        self.water_count = 0
        self.weed_count = 0
        self.pest_count = 0
        self.choice_impacts = []

        # ===== NEW SYSTEMS =====

        # #11 Attitude tracking
        self.patience_score = 0
        self.care_score = 0
        self.empathy_choices = 0
        self.recovery_count = 0
        self.rush_count = 0
        self.last_failure_action = ""

        # #5 Dad lessons learned
        self.dad_lessons = {}

        # #12 Silent gifts
        self.gifts_revealed = 0

        # #15 Sensory memory
        self.current_sense = "낯선 흙냄새가 코끝을 스친다."

        # #10 Father perspective
        self.dad_mode = False
        self.dad_mode_turns = 0
        self.dad_mode_triggered = False

        # #1 Father day interludes seen
        self.father_day_seen = set()

        # #14 2nd playthrough
        self.is_second_run = False
        self.prev_ending = ""
        self.prev_understanding = 0

        # #13 Wait animation state
        self.wait_active = False
        self.wait_timer = 0.0

        # Ending type for save
        self.last_ending = ""
        
        # 플레이 시간 측정용 변수 (초 단위)
        self.play_time = 0.0

    def reset(self):
        """새 플레이를 위해 상태를 초기화한다.
        __init__을 다시 호출하되, 플레이어 정체성·이전 회차 기록(2회차 판정용)은 보존한다.
        (필드를 손으로 나열하던 방식은 __init__과 어긋나 누락 버그를 만들기 쉬웠다.)"""
        preserved = {
            "player_name": self.player_name,
            "is_second_run": self.is_second_run,
            "prev_ending": self.prev_ending,
            "prev_understanding": self.prev_understanding,
        }
        self.__init__()
        for key, value in preserved.items():
            setattr(self, key, value)


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
        "low": ["이 흙에 왜 물을 줘야 하는 거지?", "당근이 이 정도 물을 원하는 건가?",
                "물 한 바가지가 이렇게 무거웠나."],
        "mid": ["아버지도 이 새벽에 물을 주었을까.", "하루에 몇 번이나 이걸 했을까.",
                "흙이 물을 머금는 데에도 시간이 걸리는구나."],
        "high": ["물소리가 자장가 같다.", "이 흙이 마르지 않게, 매일 이렇게.",
                 "물을 준다는 건 내일을 믿는 일이었다."],
    },
    "잡초 뽑기": {
        "low": ["잡초가 이렇게 빨리 자라나?", "이거 끝이 있기는 한 건가.",
                "뿌리가 생각보다 깊게 박혀 있다."],
        "mid": ["손이 아프다. 매일 이걸 했다니.", "뽑아도 뽑아도 자라는구나.",
                "그냥 두면 당근 몫까지 빼앗아 간다."],
        "high": ["이것도 농사의 일부였구나.", "잡초와 싸우는 게 아니라, 당근을 지키는 거였어.",
                 "쓸 것과 버릴 것을 가리는 일은 늘 손이 많이 간다."],
    },
    "해충 살피기": {
        "low": ["벌레가 이렇게 많다고?", "이런 걸 맨손으로?",
                "잎 뒤는 들여다본 적도 없었는데."],
        "mid": ["잎 하나하나 뒤집어 보는 게 이런 거였구나.", "작은 것도 그냥 지나치면 안 되는 거구나.",
                "눈에 안 띄는 것이 더 무섭다."],
        "high": ["지키는 일은 늘 조용하고 반복적이다.", "아버지의 손이 거칠었던 이유를 알 것 같다.",
                 "매일 살피는 마음, 그게 사랑이었구나."],
    },
    "배수로 정리": {
        "low": ["물길도 관리해야 하는 거야?", "농사가 이렇게 복잡한 건가.",
                "땅 밑까지 신경 쓸 줄은 몰랐다."],
        "mid": ["물이 빠질 곳이 없으면 뿌리가 썩는구나.", "보이지 않는 곳까지 신경 써야 하다니.",
                "비가 오기 전에 미리 해 둬야 하는 일이었다."],
        "high": ["물 한 줄기도 흘러갈 곳이 필요하다.", "정성이란 이런 거였구나.",
                 "보이지 않는 곳을 돌보는 게 진짜 손길이었다."],
    },
    "흙 북돋기": {
        "low": ["흙을 왜 또 만져야 하지?", "이게 뭐가 달라지는 건지 모르겠다.",
                "흙도 손이 가야 하는 거였나."],
        "mid": ["흙을 다독이는 일이 이렇게 조용한 일이었구나.", "손끝에 흙이 묻는 감각이 익숙해진다.",
                "딱딱해진 흙을 풀어 주면 숨통이 트인다."],
        "high": ["이 흙 아래에 기다림이 묻혀 있다.", "아버지의 하루는 이런 조용함으로 가득했겠지.",
                 "흙을 만지는 손이, 어느새 아버지를 닮아 간다."],
    },
    "기다리기": {
        "low": ["그냥 기다리면 되는 건가?", "아무것도 안 해도 괜찮을까.",
                "이 시간이 가장 견디기 어렵다."],
        "mid": ["기다린다는 건, 믿는다는 뜻이었구나.", "조급함을 참는 것도 일의 일부구나.",
                "재촉한다고 빨리 자라는 게 아니었다."],
        "high": ["기다림 속에서 자라는 건 당근만이 아니었다.", "아버지도 이렇게 기다렸겠지, 매일.",
                 "고요를 견디는 법을, 흙이 가르쳐 준다."],
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

# #10 Father perspective echoes (when playing as dad)
FATHER_ECHOES = {
    "물 주기": ["아이가 먹을 당근이니까.", "오늘도 안 먹겠지. 그래도."],
    "잡초 뽑기": ["이 밭만큼은 깨끗하게.", "아이는 모르겠지만, 이것도 사랑이다."],
    "해충 살피기": ["잎 하나도 함부로 놔둘 수 없다.", "내가 지키지 않으면 누가 지키겠나."],
    "배수로 정리": ["비가 오기 전에 해야 한다.", "준비하는 사람은 늘 보이지 않는 법이지."],
    "흙 북돋기": ["이 흙에 내 시간이 쌓인다.", "아이가 언젠가 이 흙을 만져볼까."],
    "기다리기": ["조급해하면 안 된다. 당근도, 아이도.", "기다릴 줄 아는 게 농부의 일이다."],
    "살펴보기": ["오늘도 무사히 자라고 있구나.", "이 밭이 내 하루의 전부다."],
}

# #6 Weather wisdom
WEATHER_WISDOM = {
    "맑음": "맑은 날이 오래가면 오히려 조심해야 한단다.",
    "흐림": "구름은 비를 데려오기도, 막아주기도 한다.",
    "비": "비가 오면 쉬어야 할 것 같지만, 배수로는 비 올 때 정리해야 한단다.",
    "가뭄": "메마른 땅도 기다림을 안다. 급한 마음이 더 해롭다.",
    "강풍": "바람은 약한 뿌리를 먼저 시험한다.",
}

WEATHER_DATA = {
    "맑음": {"moisture": -2, "stress": -3, "desc": "하늘이 맑다."},
    "흐림": {"moisture": 0, "stress": 0, "desc": "구름이 끼어 있다."},
    "비": {"moisture": 10, "drainage": -3, "desc": "빗방울이 떨어진다."},
    "가뭄": {"moisture": -8, "health": -3, "desc": "땅이 갈라지고 있다."},
    "강풍": {"pests": -5, "stress": 5, "desc": "바람이 세차게 분다."},
}

# #12 Silent gifts (revealed every 5 turns)
SILENT_GIFTS = [
    "밭 옆에 물통이 미리 채워져 있다.",
    "흙 위에 장갑이 놓여 있다. 내 사이즈다.",
    "삽 손잡이에 테이프가 감겨 있다. 손이 안 아프게.",
    "그늘에 도시락이 놓여 있다. 아직 따뜻하다.",
    "밭 가장자리에 돌이 치워져 있다. 누가 했을까.",
    "이 밭의 이랑이 유난히 반듯하다. 오래된 손길.",
    "호미 옆에 작은 쪽지. '힘들면 쉬어라.'",
]

# #15 Sensory memory (per action, per tier) — 각 슬롯 여러 줄, 반복 없이 골라 쓴다
SENSORY_DATA = {
    "low": {
        "물 주기": ["차가운 물이 손등을 적신다.", "물뿌리개가 묵직하게 기운다."],
        "잡초 뽑기": ["풀 냄새가 손에 밴다.", "잎 끝이 손바닥을 스친다."],
        "해충 살피기": ["잎 뒤에서 뭔가 꿈틀거린다.", "작은 다리들이 잎맥을 따라 움직인다."],
        "배수로 정리": ["진흙이 장화에 달라붙는다.", "삽 끝에 물기가 무겁게 묻어난다."],
        "흙 북돋기": ["흙이 손톱 사이로 들어온다.", "마른 흙덩이가 손안에서 부서진다."],
        "기다리기": ["바람 소리만 들린다.", "해가 조금씩 기울어 간다."],
    },
    "mid": {
        "물 주기": ["물이 흙에 스며드는 소리가 조용하다.", "젖은 흙에서 비 온 뒤 같은 냄새가 난다."],
        "잡초 뽑기": ["뿌리가 끊어지는 감각이 손끝에 남는다.", "한 움큼 뽑고 나니 이랑이 한결 넓어 보인다."],
        "해충 살피기": ["잎의 뒷면은 생각보다 부드럽다.", "한 잎 한 잎 넘기는 손이 차분해진다."],
        "배수로 정리": ["물길이 잡히자 흙 냄새가 달라진다.", "고였던 물이 천천히 빠져나간다."],
        "흙 북돋기": ["차가운 흙 사이로 따뜻한 게 올라온다.", "북돋운 흙이 폭신하게 부푼다."],
        "기다리기": ["흙 속에서 아주 작은 소리가 나는 것 같다.", "숨을 고르자 밭 전체가 눈에 들어온다."],
    },
    "high": {
        "물 주기": ["이 물소리는 아버지의 작업복에서 맡았던 냄새와 닮았다.", "물줄기 끝에서 새벽의 아버지가 보이는 듯하다."],
        "잡초 뽑기": ["손이 거칠어진다. 아버지의 손등이 떠오른다.", "이 자리를 매일 지킨 손이 있었다."],
        "해충 살피기": ["조용히 지키는 일. 이게 매일의 사랑이었구나.", "아무도 보지 않는 곳에서의 돌봄이었다."],
        "배수로 정리": ["보이지 않는 곳을 돌보는 손길의 온기.", "비를 미리 헤아리는 마음이 여기 있었다."],
        "흙 북돋기": ["이 흙에는 누군가의 시간이 켜켜이 쌓여 있다.", "흙을 다독이는 손에 아버지의 하루가 겹쳐진다."],
        "기다리기": ["고요 속에서 자라는 것은 당근만이 아니다.", "기다림의 무게를, 이제 조금 알 것 같다."],
    },
}

# #1 Father day narration pages
FATHER_DAY_NARRATIONS = {
    30: [
        "새벽 4시.\n아직 어두운 하늘 아래, 아버지는 장화를 신었다.\n오늘도 아이는 당근을 먹지 않겠지.\n그래도 물은 줘야 한다.\n이 흙이 기다리니까.",
        "밭에 도착하면 먼저 하는 일.\n이랑 사이를 걸으며 어젯밤 사이 달라진 것을 살핀다.\n무릎이 아프다.\n하지만 이 당근은 아이의 식탁에 올라갈 것이다.\n그것만으로 충분하다.",
    ],
    50: [
        "오늘은 비가 올 것 같다.\n아버지는 배수로를 미리 정리하고,\n아이가 쓸 장갑을 밭 옆에 놓아 둔다.\n혹시나 하는 마음으로.\n아이는 모르겠지만, 괜찮다.\n알아주길 바라고 한 일이 아니니까.",
    ],
}

# 엔딩별 일지 '마지막 장' — 결말에 따라 일지의 닫는 글이 달라진다.
ENDING_JOURNAL_CLOSINGS = {
    "true": ("[마지막 장 · 수확의 날]\n흙을 처음 만지던 날이 떠오른다. 그땐 아무것도 몰랐다.\n이제는 안다 — 이 밭의 모든 새벽이 누군가의 사랑이었다는 걸.\n내일 새벽, 아버지 곁에서 다시 흙을 만질 것이다."),
    "happy": ("[마지막 장 · 수확의 날]\n당근은 달았다. 기다린 만큼, 꼭 그만큼.\n서툴렀지만 마음만은 흙을 따라 한 뼘 자랐다."),
    "growth": ("[마지막 장 · 수확의 날]\n실수투성이였다. 그래도 매번 다시 흙을 만졌다.\n서툰 손도 매일이면 단단해진다는 걸, 이 밭이 가르쳐 줬다."),
    "skill": ("[마지막 장 · 수확의 날]\n밭일은 익혔고 수확도 넉넉했다.\n그런데 식탁 앞에서 왜 멈칫했을까. 아직 못 배운 것이 남아 있다."),
    "rush": ("[마지막 장 · 수확의 날]\n급히 뽑은 당근은 어딘가 설었다.\n기다리는 법을, 나는 아직 배우지 못했다."),
    "normal": ("[마지막 장 · 수확의 날]\n잘한 것도 못한 것도 있던 하루였다.\n조금은 알 것 같은, 그런 마음으로 밭을 나선다."),
    "bad": ("[마지막 장 · 수확의 날]\n끝내 입에 넣지 못한 당근.\n그래도 예전처럼 밀어내지는 않았다. 그거면, 시작은 된 셈이다."),
    "wither": ("[마지막 장 · 시든 밭]\n수확은 없었다. 흙만 남았다.\n아버지가 매일 무엇과 싸웠는지, 이제야 조금 안다.\n다음 새벽엔, 조금 다르게 해볼 수 있을 것 같다."),
}


def append_ending_journal():
    """엔딩에 도달했을 때, 그 결말에 맞는 '마지막 장'을 일지에 딱 한 번 더한다."""
    if game_state.journal_closed:
        return
    text = ENDING_JOURNAL_CLOSINGS.get(game_state.last_ending)
    if text:
        game_state.journal_entries.append(text)
        game_state.journal_closed = True


# #8 Journal retrospective lines
JOURNAL_RETROSPECTIVES = {
    "이걸 왜 해야 하는지 아직 모르겠다.": "→ 지금은 안다. 그때의 '모르겠다'가 시작이었다.",
    "조금씩 알 것 같기도 하다.": "→ 알 것 같다는 느낌이 맞았다.",
    "이 일의 무게가 느껴진다.": "→ 그 무게는 사랑의 무게였다.",
    "실수가 잦았다. 아직 모르는 것이 많다.": "→ 서툴렀지만, 포기하지 않았다.",
    "당근이 많이 힘들어 보였다.": "→ 힘들어 보이는 것도 볼 줄 알게 되었다.",
    "수분은 적당했다.": "→ '적당함'을 아는 것이 농부의 눈이다.",
    "오늘 물을 너무 많이 줬다.": "→ 넘치는 것도 부족한 것만큼 해롭다는 걸 배웠다.",
    "흙이 바짝 말라 있었다.": "→ 마른 흙을 기억하기에, 물의 소중함을 안다.",
}

STORY_EVENTS = [
    {
        "title": "이웃 밭의 물난리",
        "text": "이웃 밭에서 물이 넘쳐 흘러오고 있다.\n우리 밭도 위험할 수 있다.\n어떻게 해야 할까?",
        "choice_a": ("우리 밭 배수로를 먼저 지킨다", {
            "understanding": 0,
            "result_text": "우리 밭은 안전하지만, 이웃 밭이 걱정된다.",
            "impact_text": "이웃 밭의 어린 싹 몇 줄기는 끝내 물에 잠겼다.",
        }),
        "choice_b": ("이웃 밭의 물길을 함께 막는다", {
            "understanding": 8,
            "result_text": "함께 막으니 오히려 물길이 잘 잡혔다. 혼자가 아니었다.",
            "impact_text": "함께 막은 물길 덕분에 이웃 밭도 장마를 버텼다.",
        }),
    },
    {
        "title": "쓰러진 허수아비",
        "text": "강풍에 허수아비가 쓰러졌다.\n새들이 모여들기 시작한다.\n시간이 많지 않다.",
        "choice_a": ("허수아비를 급히 다시 세운다", {
            "understanding": 2,
            "result_text": "허수아비를 세웠지만, 대충 세워서 금방 또 쓰러질 것 같다.",
            "impact_text": "급히 세운 허수아비는 다시 쓰러졌고, 새들이 밭을 훑고 갔다.",
        }),
        "choice_b": ("단단히 고정할 수 있게 돌을 모은다", {
            "understanding": 6,
            "result_text": "시간은 걸렸지만 튼튼해졌다. 급할수록 돌아가라는 말이 떠오른다.",
            "impact_text": "돌로 고정한 허수아비는 강풍 뒤에도 밭을 지켰다.",
        }),
    },
    {
        "title": "길 잃은 벌",
        "text": "꽃밭을 찾지 못하는 벌 한 마리가\n당근 잎 위에서 힘없이 쉬고 있다.\n해충은 아닌 것 같다.",
        "choice_a": ("내버려 두고 밭일을 계속한다", {
            "understanding": 1,
            "result_text": "밭일은 진행되었지만, 자꾸 벌이 신경 쓰인다.",
            "impact_text": "길 잃은 벌은 꽃밭을 찾지 못했고, 밭가의 꽃도 조용히 시들었다.",
        }),
        "choice_b": ("근처 꽃밭 쪽으로 조심히 옮겨 준다", {
            "understanding": 7,
            "result_text": "벌이 날아간 뒤, 밭 위로 따뜻한 바람이 불었다.",
            "impact_text": "옮겨 준 벌은 꽃밭을 찾아갔고, 밭가에는 작은 열매가 맺혔다.",
        }),
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


def pick_fresh(options):
    """후보 중 최근에 보여준 줄을 피해 하나 고른다 — 같은 말이 연달아 반복되지 않게."""
    if not options:
        return ""
    fresh = [o for o in options if o not in game_state.recent_lines]
    if not fresh:
        # 풀을 다 봤으면, 적어도 '바로 직전 줄'만은 피해 같은 말이 연속되지 않게 한다.
        last = game_state.recent_lines[-1] if game_state.recent_lines else None
        fresh = [o for o in options if o != last] or list(options)
    choice = random.choice(fresh)
    game_state.recent_lines.append(choice)
    if len(game_state.recent_lines) > 6:
        game_state.recent_lines.pop(0)
    return choice


def pick_action_echo(action):
    # In dad mode, use father echoes
    if game_state.dad_mode:
        return pick_fresh(FATHER_ECHOES.get(action, []))
    tier = get_understanding_tier(game_state.understanding)
    return pick_fresh(ACTION_ECHOES.get(action, {}).get(tier, []))


def pick_failure_echo(action):
    echo = FAILURE_ECHOES.get(action, "")
    # #5 Record lesson
    if echo and action not in game_state.dad_lessons:
        game_state.dad_lessons[action] = echo
    return echo


def pick_sensory(action):
    """#15 Pick a sensory description based on action and understanding tier."""
    tier = get_understanding_tier(game_state.understanding)
    return pick_fresh(SENSORY_DATA.get(tier, {}).get(action, []))


def get_silent_gift():
    """#12 Get the next silent gift text, or None if all revealed."""
    idx = game_state.gifts_revealed
    if idx < len(SILENT_GIFTS):
        return SILENT_GIFTS[idx]
    return None


def reveal_gift():
    """#12 Mark next gift as revealed."""
    game_state.gifts_revealed = min(game_state.gifts_revealed + 1, len(SILENT_GIFTS))


def check_recovery(action, is_fail):
    """#5 Check if player recovered from a previous failure."""
    if not is_fail and game_state.last_failure_action == action:
        game_state.recovery_count += 1
        game_state.last_failure_action = ""
        lesson = game_state.dad_lessons.get(action, "")
        if lesson:
            return f"그때 아버지가 한 말이 맞았다. 이번에는 달랐다."
    if is_fail:
        game_state.last_failure_action = action
    return ""


def track_attitude(action, is_fail, is_good_turn):
    """#11 Track player attitude based on actions."""
    if action == "기다리기" and not is_fail:
        game_state.patience_score += 1
    if action == "기다리기" and is_fail:
        game_state.rush_count += 1
    if action == "살펴보기" and is_good_turn:
        game_state.care_score += 1


def get_season(growth, growth_goal):
    """#7 Get current season based on growth progress."""
    ratio = growth / max(1, growth_goal)
    if ratio < 0.22:
        return "이른 봄"
    elif ratio < 0.50:
        return "봄"
    elif ratio < 0.78:
        return "여름"
    else:
        return "가을"


def get_season_colors(growth, growth_goal):
    """#7 Get palette colors based on season."""
    season = get_season(growth, growth_goal)
    if season == "이른 봄":
        return {
            "grass": (75, 130, 70), "grass_dark": (55, 105, 50),
            "dirt": (130, 85, 55), "dirt_dark": (105, 68, 42),
            "sky_tint": (180, 195, 210),
        }
    elif season == "봄":
        return {
            "grass": (90, 160, 70), "grass_dark": (70, 130, 50),
            "dirt": (145, 95, 60), "dirt_dark": (120, 75, 45),
            "sky_tint": (210, 225, 200),
        }
    elif season == "여름":
        return {
            "grass": (60, 145, 55), "grass_dark": (45, 115, 40),
            "dirt": (140, 90, 55), "dirt_dark": (115, 72, 42),
            "sky_tint": (200, 220, 180),
        }
    else:  # 가을
        return {
            "grass": (140, 155, 60), "grass_dark": (110, 125, 45),
            "dirt": (150, 100, 60), "dirt_dark": (125, 80, 48),
            "sky_tint": (230, 200, 140),
        }


def advance_weather():
    weathers = list(WEATHER_DATA.keys())
    game_state.weather = game_state.next_weather
    candidates = [w for w in weathers if w != game_state.weather]
    game_state.next_weather = random.choice(candidates)
    game_state.weather_turns_left = random.randint(2, 3)


def check_epiphany():
    """Check if understanding crossed a threshold. Returns True if epiphany triggered."""
    u = game_state.understanding
    for threshold, text in EPIPHANY_THRESHOLDS.items():
        if u >= threshold and threshold not in game_state.epiphanies_seen:
            game_state.epiphanies_seen.add(threshold)
            game_state.pending_epiphany = text
            return True
    return False


def check_father_day():
    """#1 Check if father day interlude should trigger."""
    u = game_state.understanding
    for threshold in FATHER_DAY_NARRATIONS:
        if u >= threshold and threshold not in game_state.father_day_seen:
            game_state.father_day_seen.add(threshold)
            return threshold
    return None


def get_attitude_ending():
    """#11 Determine ending type based on attitude, not just scores."""
    p = game_state.patience_score
    c = game_state.care_score
    e = game_state.empathy_choices
    r = game_state.recovery_count
    rush = game_state.rush_count
    u = game_state.understanding
    h = game_state.final_health
    m = game_state.farm_mistakes

    # 진엔딩: 솜씨·이해·인내·공감이 모두 무르익고 실수도 적음
    if u >= 40 and e >= 2 and p >= 3 and h >= 55 and m < 3:
        return "true"
    # 해피: 따뜻한 성공 — 마음의 흔적(공감 또는 인내)이 하나라도 있음
    if h >= 65 and u >= 30 and m < 4 and (e >= 1 or p >= 2):
        return "happy"
    # 기술: 잘 길렀지만 마음은 헤아리지 못함 (공감 0 · 거의 안 기다림)
    if h >= 60 and u >= 25 and e == 0 and p <= 1:
        return "skill"
    # 성장: 실수가 많았지만 다시 일어선 손
    if r >= 2 and u >= 18:
        return "growth"
    # 조급함: 끝내 기다리지 못함
    if rush >= 4:
        return "rush"
    # 노멀
    if h >= 45 and u >= 15:
        return "normal"
    # 배드
    return "bad"


# #14 Save/Load for 2nd playthrough
SAVE_PATH = os.path.join(os.path.dirname(__file__), "save_data.json")


def save_progress():
    data = {
        "completed": True,
        "ending": game_state.last_ending,
        "understanding": game_state.understanding,
        "empathy_choices": game_state.empathy_choices,
        "patience_score": game_state.patience_score,
    }
    try:
        with open(SAVE_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


def load_progress():
    try:
        if os.path.exists(SAVE_PATH):
            with open(SAVE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def apply_second_run():
    """#14 Apply 2nd playthrough state."""
    data = load_progress()
    if data and data.get("completed"):
        game_state.is_second_run = True
        game_state.prev_ending = data.get("ending", "")
        game_state.prev_understanding = data.get("understanding", 0)
