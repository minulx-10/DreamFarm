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

        # 기르는 작물 (core/crops.py의 키) — 엔딩을 한 번 보면 다른 작물이 열린다
        self.crop = "carrot"
        # 악)몽중농원 모드 (진엔딩 해금)
        self.nightmare = False

        # main 루프에 보내는 요청 플래그 (씬에서 직접 처리할 수 없는 일)
        self.request_load = False       # 슬롯 불러오기
        self.request_settings = False   # 설정 오버레이 열기
        self.request_quit = False       # 게임 종료 확인 모달 열기
        self.request_fullscreen_toggle = False  # 전체화면/창모드 전환 (설정창·F11 공용)
        self.is_fullscreen = False      # 현재 전체화면 여부(설정창 표시용) — game_main이 갱신

        # 갤러리에서 특정 엔딩을 감상용으로 강제 지정 (EndingScene이 소비 후 비운다)
        self.forced_ending = None

    def reset(self):
        """새 플레이를 위해 상태를 초기화한다.
        __init__을 다시 호출하되, 플레이어 정체성·이전 회차 기록(2회차 판정용)은 보존한다.
        (필드를 손으로 나열하던 방식은 __init__과 어긋나 누락 버그를 만들기 쉬웠다.)"""
        preserved = {
            "player_name": self.player_name,
            "is_second_run": self.is_second_run,
            "prev_ending": self.prev_ending,
            "prev_understanding": self.prev_understanding,
            "crop": self.crop,
            "nightmare": self.nightmare,
        }
        self.__init__()
        for key, value in preserved.items():
            setattr(self, key, value)


game_state = GameState()


# --- Josa helper ---
def has_batchim(text):
    """주어진 텍스트의 마지막 글자에 종성(받침)이 있는지 판정한다.
    한글 받침 분석 및 영어 알파벳 발음 heuristic을 적용한다."""
    if not text:
        return False
    last_char = text[-1]
    
    # 1. 한글 판정
    if ord('가') <= ord(last_char) <= ord('힣'):
        return (ord(last_char) - ord('가')) % 28 > 0
    # 2. 영어 알파벳 판정 (발음 기호 기준 받침 유무 추정)
    if last_char.isalpha():
        lc = last_char.lower()
        # 모음(aeiou) 및 반모음(y), 복합음(w), 스/즈 발음(s,z,x)은 받침이 없는 소리로 취급
        return lc not in "aeiouywszx"
    # 3. 기타 문자 (기본값)
    return False


def append_josa(text, josa_type):
    if not text:
        return text
    batchim = has_batchim(text)
    if josa_type == "은/는":
        return text + ("은" if batchim else "는")
    if josa_type == "이/가":
        return text + ("이" if batchim else "가")
    if josa_type == "을/를":
        return text + ("을" if batchim else "를")
    return text


# --- Understanding stage system & Narrative redirects ---
from core import narrative_data

UNDERSTANDING_STAGES = narrative_data.UNDERSTANDING_STAGES
EPIPHANY_THRESHOLDS = narrative_data.EPIPHANY_THRESHOLDS
ACTION_ECHOES = narrative_data.ACTION_ECHOES
FAILURE_ECHOES = narrative_data.FAILURE_ECHOES
FATHER_ECHOES = narrative_data.FATHER_ECHOES
WEATHER_WISDOM = narrative_data.WEATHER_WISDOM
WEATHER_DATA = narrative_data.WEATHER_DATA
SILENT_GIFTS = narrative_data.SILENT_GIFTS
SENSORY_DATA = narrative_data.SENSORY_DATA
FATHER_DAY_NARRATIONS = narrative_data.FATHER_DAY_NARRATIONS
ENDING_JOURNAL_CLOSINGS = narrative_data.ENDING_JOURNAL_CLOSINGS
JOURNAL_RETROSPECTIVES = narrative_data.JOURNAL_RETROSPECTIVES
STORY_EVENTS = narrative_data.STORY_EVENTS

get_understanding_stage = narrative_data.get_understanding_stage
get_understanding_tier = narrative_data.get_understanding_tier
pick_fresh = narrative_data.pick_fresh
pick_action_echo = narrative_data.pick_action_echo
pick_failure_echo = narrative_data.pick_failure_echo
pick_sensory = narrative_data.pick_sensory
get_silent_gift = narrative_data.get_silent_gift
reveal_gift = narrative_data.reveal_gift
check_recovery = narrative_data.check_recovery
track_attitude = narrative_data.track_attitude
get_season = narrative_data.get_season
get_season_colors = narrative_data.get_season_colors
advance_weather = narrative_data.advance_weather
check_epiphany = narrative_data.check_epiphany
check_father_day = narrative_data.check_father_day
get_attitude_ending = narrative_data.get_attitude_ending
append_ending_journal = narrative_data.append_ending_journal


# #14 Save/Load for 2nd playthrough — 실제 파일 경로는 core/save_system.py가 관리한다.


def save_progress():
    # 갤러리 해금 기록(endings_seen 등)을 지우지 않도록 병합 저장한다.
    from core import save_system
    save_system.update_meta(
        completed=True,
        ending=game_state.last_ending,
        understanding=game_state.understanding,
        empathy_choices=game_state.empathy_choices,
        patience_score=game_state.patience_score,
        crop=game_state.crop, # 마지막으로 키웠던 작물 정보를 갤러리를 위해 함께 기록
        player_name=game_state.player_name, # 이스터에그 이름을 유지하기 위해 플레이어 이름 기록
    )


def load_progress():
    # 저장 경로 결정은 save_system이 전담한다 (exe/개발 환경 모두 동일 파일을 보게).
    from core import save_system
    try:
        if os.path.exists(save_system.META_PATH):
            with open(save_system.META_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return None


def apply_second_run():
    """#14 Apply 2nd playthrough state."""
    data = load_progress()
    if data:
        if data.get("completed"):
            game_state.is_second_run = True
            game_state.prev_ending = data.get("ending", "")
            game_state.prev_understanding = data.get("understanding", 0)
        if "player_name" in data:
            game_state.player_name = data["player_name"]
            
    # 이어하기 슬롯 파일(save_slot.json)이 존재할 경우 해당 슬롯에 기록된 이름을 우선하여 복구
    from core import save_system
    slot = save_system.load_slot()
    if slot and "game_state" in slot and "player_name" in slot["game_state"]:
        game_state.player_name = slot["game_state"]["player_name"]
