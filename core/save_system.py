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
    - exe(PyInstaller)로 실행 중이면 exe가 있는 폴더 (임시 _MEIPASS는 종료 시 사라지므로 안 됨)
    - 개발 중이면 core/ 폴더
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(__file__)


_DIR = _save_dir()
SLOT_PATH = os.path.join(_DIR, "save_slot.json")
META_PATH = os.path.join(_DIR, "save_data.json")
SETTINGS_PATH = os.path.join(_DIR, "user_settings.json")


def _read_json(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _write_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception:
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
]
_FARM_SET_FIELDS = ["memories_seen", "stories_seen"]


def snapshot(farm):
    """현재 게임 전체 상태를 dict로 뜬다 (farm 씬 포함)."""
    gs = {k: getattr(game_state, k, None) for k in _GS_FIELDS}
    for k in _GS_SET_FIELDS:
        gs[k] = sorted(getattr(game_state, k, set()))
    fm = {k: getattr(farm, k, None) for k in _FARM_FIELDS}
    for k in _FARM_SET_FIELDS:
        fm[k] = sorted(getattr(farm, k, set()))
    return {"version": 1, "game_state": gs, "farm": fm}


def restore(data, farm):
    """스냅샷을 game_state와 farm 씬에 되살린다."""
    gs = data.get("game_state", {})
    for k in _GS_FIELDS:
        if k in gs:
            setattr(game_state, k, gs[k])
    for k in _GS_SET_FIELDS:
        setattr(game_state, k, set(gs.get(k, [])))
    fm = data.get("farm", {})
    for k in _FARM_FIELDS:
        if k in fm and fm[k] is not None:
            setattr(farm, k, fm[k])
    for k in _FARM_SET_FIELDS:
        setattr(farm, k, set(fm.get(k, [])))
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
    ok = False
    for path in (SLOT_PATH, META_PATH):
        try:
            if os.path.exists(path):
                os.remove(path)
                ok = True
        except Exception:
            pass
    return ok


# ────────────────────────────── 회차 기록(메타) ──────────────────────────────

def load_meta():
    return _read_json(META_PATH) or {}


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


# ────────────────────────────── 유저 설정 ──────────────────────────────

_DEFAULT_SETTINGS = {"autosave": True}


def load_settings():
    data = _read_json(SETTINGS_PATH)
    merged = dict(_DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)
    return merged


def get_setting(key):
    return load_settings().get(key, _DEFAULT_SETTINGS.get(key))


def set_setting(key, value):
    data = load_settings()
    data[key] = value
    _write_json(SETTINGS_PATH, data)
