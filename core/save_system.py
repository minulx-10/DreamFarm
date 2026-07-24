"""게임 저장/불러오기 시스템.

세 개의 파일을 다룬다:
- save_slot.json    : '이어하기'용 진행 중 스냅샷 (게임 상태 + 밭 상태 전체)
- save_data.json    : 회차를 넘어 남는 기록 (클리어 여부, 본 엔딩/이야기 — 갤러리 해금)
- user_settings.json: 유저 설정 (자동 저장 On/Off 등)

FarmScene을 직접 import하지 않고 필드 이름 목록으로 직렬화한다
(순환 import 방지 + 씬 코드와 저장 코드의 결합 최소화).
"""

import json
import os
import sys

from core.game_state import game_state


def _save_dir():
    """저장 파일을 둘 폴더.
    - Android 환경(ANDROID_PRIVATE 환경변수 감지)에서는 Android 내부 전용 앱 저장 공간을 사용합니다.
    - 스팀 출시 및 권한 문제를 방지하기 위해 사용자 AppData 폴더(Windows) 또는 홈 디렉토리를 사용합니다.
    - 개발 중(frozen이 아닌 경우)에는 이전과 동일하게 core/ 폴더를 사용합니다.
    """
    if 'ANDROID_PRIVATE' in os.environ:
        path = os.path.join(os.environ['ANDROID_PRIVATE'], 'save_data')
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except Exception:
            pass

    if getattr(sys, "frozen", False):
        appdata = os.environ.get('APPDATA')
        if appdata:
            path = os.path.join(appdata, 'MongjungNongwon')
        else:
            path = os.path.join(os.path.expanduser('~'), '.mongjungnongwon')
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except Exception:
            # 폴더 생성 실패 시 안전 장치로 exe 폴더 반환
            return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


_DIR = _save_dir()
SLOT_PATH = os.path.join(_DIR, "save_slot.json")
META_PATH = os.path.join(_DIR, "save_data.json")
SETTINGS_PATH = os.path.join(_DIR, "user_settings.json")

_settings_cache = None
_meta_cache = None


def _read_json(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _write_json(path, data):
    global _settings_cache, _meta_cache
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        
        if os.path.exists(tmp_path):
            os.replace(tmp_path, path)
            
        # 성공적으로 기록된 경우 캐시 동기화
        if path == SETTINGS_PATH:
            _settings_cache = data
        elif path == META_PATH:
            _meta_cache = data
        return True
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        return False


# ────────────────────────────── 이어하기 슬롯 ──────────────────────────────

# game_state에서 그대로 JSON에 넣을 수 있는 필드
_GS_FIELDS = [
    "player_name", "understanding", "score", "timer",
    "final_health", "farm_mistakes",
    "weather", "weather_turns_left", "next_weather",
    "journal_entries", "journal_closed", "crop_failed",
    "action_echo", "recent_lines",
    "water_count", "weed_count", "pest_count", "choice_impacts",
    "patience_score", "care_score", "empathy_choices",
    "recovery_count", "rush_count", "last_failure_action",
    "dad_lessons", "gifts_revealed", "current_sense",
    "dad_mode", "dad_mode_turns", "dad_mode_triggered",
    "is_second_run", "prev_ending", "prev_understanding",
    "last_ending", "play_time",
    "crop", "nightmare",
    "year_seed", "run_stats", "challenge", "behavior_run_file",
]
# set → list 변환이 필요한 필드
_GS_SET_FIELDS = ["epiphanies_seen", "father_day_seen"]

# FarmScene에서 그대로 넣을 수 있는 필드
_FARM_FIELDS = [
    "day", "growth", "growth_goal",
    "moisture", "health", "weeds", "pests", "drainage", "stress",
    "actions_taken", "last_action", "message", "notice",
    "memory_cooldown", "minigame_cooldown", "weather_minigame_cooldown",
    "special_cooldown", "special_done",
    "withers", "weak_turns", "mistakes",
    "story_cooldown", "crop_offsets", "turns_since_wait",
    "last_season",
]
_FARM_SET_FIELDS = ["memories_seen", "stories_seen"]


def snapshot(farm):
    """현재 게임 전체 상태를 dict로 뜬다 (farm 씬 포함).
    밭 수치는 farm.sim(FarmSimulator)에 산다 — 삼분할 이후 씬은 컨트롤러일 뿐."""
    host = getattr(farm, "sim", farm)
    gs = {k: getattr(game_state, k, None) for k in _GS_FIELDS}
    for k in _GS_SET_FIELDS:
        gs[k] = sorted(getattr(game_state, k, set()))
    fm = {k: getattr(host, k, None) for k in _FARM_FIELDS}
    for k in _FARM_SET_FIELDS:
        fm[k] = sorted(getattr(host, k, set()))
    return {"version": 1, "game_state": gs, "farm": fm}


def restore_state(data):
    """스냅샷의 game_state 부분만 먼저 되살린다.
    FarmScene/FarmSimulator 생성이 crop·nightmare·challenge·year_seed를 읽으므로,
    씬을 만들기 '전에' 이걸 불러야 저장 당시 설정 그대로 밭이 구성된다."""
    gs = data.get("game_state", {})
    for k in _GS_FIELDS:
        if k in gs:
            setattr(game_state, k, gs[k])
    for k in _GS_SET_FIELDS:
        setattr(game_state, k, set(gs.get(k, [])))
    # 행동 로그 이어쓰기 — 집계는 파일 재생으로 복원된다 (순환 import 방지, 지연 import)
    from core import behavior
    behavior.resume_run(getattr(game_state, "behavior_run_file", None))


def restore(data, farm):
    """스냅샷을 game_state와 farm 씬에 되살린다."""
    host = getattr(farm, "sim", farm)
    gs = data.get("game_state", {})
    for k in _GS_FIELDS:
        if k in gs:
            setattr(game_state, k, gs[k])
    for k in _GS_SET_FIELDS:
        setattr(game_state, k, set(gs.get(k, [])))
    # 행동 로그 이어쓰기 — 집계는 파일 재생으로 복원된다 (순환 import 방지, 지연 import)
    from core import behavior
    behavior.resume_run(getattr(game_state, "behavior_run_file", None))
    fm = data.get("farm", {})
    for k in _FARM_FIELDS:
        if k in fm and fm[k] is not None:
            setattr(host, k, fm[k])
    for k in _FARM_SET_FIELDS:
        setattr(host, k, set(fm.get(k, [])))
    # 불러온 밭은 온보딩을 다시 보여주지 않는다
    farm.tutorial_active = False
    farm.rebuild_buttons()


def save_game(farm):
    """진행 중 게임을 슬롯에 저장. 성공 여부 반환."""
    return _write_json(SLOT_PATH, snapshot(farm))


def load_slot():
    return _read_json(SLOT_PATH)


def has_save():
    return _read_json(SLOT_PATH) is not None


def delete_save():
    """세이브 슬롯 파일을 삭제한다."""
    try:
        if os.path.exists(SLOT_PATH):
            os.remove(SLOT_PATH)
            return True
    except Exception:
        pass
    return False


def reset_all():
    """세이브 슬롯과 회차 기록(메타)을 모두 삭제 — 태초부터 다시 시작.
    엔딩 해금·작물별 클리어 횟수·업적·이야기/기억 기록이 전부 사라진다."""
    global _meta_cache
    ok = False
    for path in (SLOT_PATH, META_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
                ok = True
        except Exception:
            pass
    _meta_cache = None   # 파일만 지우고 캐시가 남으면 다음 저장 때 기록이 되살아난다
    return ok


# ────────────────────────────── 회차 기록(메타) ──────────────────────────────

def load_meta():
    global _meta_cache
    if _meta_cache is None:
        _meta_cache = _read_json(META_PATH) or {}
    return _meta_cache


def update_meta(**kwargs):
    meta = load_meta()
    meta.update(kwargs)
    _write_json(META_PATH, meta)
    return meta


def record_ending(ending_type):
    """본 엔딩을 갤러리 해금 목록에 남긴다."""
    meta = load_meta()
    seen = meta.get("endings_seen", [])
    if ending_type not in seen:
        seen.append(ending_type)
    meta["endings_seen"] = seen
    _write_json(META_PATH, meta)


def record_story(title):
    """겪은 선택형 이벤트를 갤러리에 남긴다."""
    meta = load_meta()
    seen = meta.get("stories_seen", [])
    if title not in seen:
        seen.append(title)
    meta["stories_seen"] = seen
    _write_json(META_PATH, meta)


def record_memory(title, text):
    """마주친 회상 조각을 갤러리에 남긴다. 같은 제목이면 최신 글로 갱신."""
    meta = load_meta()
    seen = meta.get("memories_seen", {})
    seen[title] = text
    meta["memories_seen"] = seen
    _write_json(META_PATH, meta)


def endings_seen():
    return load_meta().get("endings_seen", [])


def record_crop_clear(crop):
    """작물을 끝까지 길러 수확한 횟수를 작물별로 누적한다 (수확 성공 시에만 호출)."""
    meta = load_meta()
    clears = meta.get("crop_clears", {})
    clears[crop] = clears.get(crop, 0) + 1
    meta["crop_clears"] = clears
    _write_json(META_PATH, meta)


def crop_clears():
    """작물별 클리어(수확 성공) 횟수 사전."""
    return load_meta().get("crop_clears", {})


def record_run(crop, ending, days, seed, journal, stats):
    """완주한 회차를 아카이브에 남긴다 (창고 탭 '지난 회차' + 누적 통계).
    일지는 한국어 원문 그대로 저장하고 표시 시점에 번역한다(엔딩 일지와 동일 규칙)."""
    meta = load_meta()
    n = meta.get("runs_completed", 0) + 1
    runs = meta.get("run_archive", [])
    runs.append({
        "n": n, "crop": crop, "ending": ending, "days": days, "seed": seed,
        "challenge": getattr(game_state, "challenge", None),
        "journal": list(journal)[-24:],
    })
    meta["run_archive"] = runs[-20:]     # 최근 20회차만 보관
    meta["runs_completed"] = n
    life = meta.get("lifetime_stats", {})
    for k, v in (stats or {}).items():
        life[k] = life.get(k, 0) + v
    life["총 재배일"] = life.get("총 재배일", 0) + max(0, days)
    meta["lifetime_stats"] = life
    _write_json(META_PATH, meta)
    return n


def run_archive():
    return load_meta().get("run_archive", [])


def lifetime_stats():
    return load_meta().get("lifetime_stats", {})


def record_achievement(aid):
    """해제된 업적 id를 메타에 남긴다 (중복은 무시)."""
    meta = load_meta()
    got = meta.get("achievements", [])
    if aid not in got:
        got.append(aid)
    meta["achievements"] = got
    _write_json(META_PATH, meta)


def achievements_unlocked():
    return load_meta().get("achievements", [])


def is_achievement_unlocked(aid):
    return aid in load_meta().get("achievements", [])


def crops_unlocked():
    """아무 엔딩이든 한 번 보면 다른 작물이 열린다."""
    return bool(endings_seen())


def nightmare_unlocked():
    """진엔딩을 보면 '악)몽중농원'이 열린다."""
    return "true" in endings_seen()


def challenge_unlocked():
    """기본 엔딩(진·노멀·배드·시듦) 중 3종을 모으면 도전 규칙이 열린다."""
    return len({"true", "normal", "bad", "wither"} & set(endings_seen())) >= 3


def epilogue_unlocked():
    """진엔딩을 보면 에필로그 '아버지의 새벽'이 열린다."""
    return "true" in endings_seen()


# ────────────────────────────── 유저 설정 ──────────────────────────────

_DEFAULT_SETTINGS = {"autosave": True, "show_version": True, "language": "ko", "update_check": True,
                     "text_speed": "normal",   # 타자기 텍스트 속도: slow | normal | fast
                     "bgm_volume": 0.30, "sfx_volume": 0.55, "muted": False,
                     "telemetry": False}       # 행동 데이터 공유 (옵트인 — 기본 꺼짐)


def load_settings():
    global _settings_cache
    if _settings_cache is None:
        data = _read_json(SETTINGS_PATH)
        merged = dict(_DEFAULT_SETTINGS)
        if isinstance(data, dict):
            merged.update(data)
        _settings_cache = merged
    return _settings_cache


def get_setting(key):
    return load_settings().get(key, _DEFAULT_SETTINGS.get(key))


def set_setting(key, value):
    data = load_settings()
    data[key] = value
    _write_json(SETTINGS_PATH, data)
