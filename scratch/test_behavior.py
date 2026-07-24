"""core/behavior.py 단위 테스트 — 기록→집계→profile 왕복. 사용: python scratch/test_behavior.py"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 실제 저장 파일을 오염시키지 않도록 임시 경로로 우회 (smoke_test.py 패턴 + _DIR까지)
_tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_saves", "behavior_test")
shutil.rmtree(_tmp, ignore_errors=True)
os.makedirs(_tmp, exist_ok=True)
from core import save_system as _ss
_ss._DIR = _tmp
_ss.SLOT_PATH = os.path.join(_tmp, "save_slot.json")
_ss.META_PATH = os.path.join(_tmp, "save_data.json")
_ss.SETTINGS_PATH = os.path.join(_tmp, "user_settings.json")
_ss._meta_cache = None
_ss._settings_cache = None

from core import behavior
from core.game_state import game_state

# 1) start_run → 파일 생성 + run_start 기록
behavior.start_run("carrot", "평년", None)
assert game_state.behavior_run_file, "run 파일명이 game_state에 실려야 한다"
path = os.path.join(behavior._dir(), game_state.behavior_run_file)
assert os.path.exists(path), "런 JSONL 파일이 생겨야 한다"

# 2) log → 집계 + 파일 append
for day in (1, 2, 3, 4):
    behavior.log("action", kind="물 주기", day=day)
behavior.log("action", kind="기다리기", day=4)
behavior.log("minigame", stage="stage3", norm=1.0)
behavior.log("day_end", day=4, weeds=0)
lines = [json.loads(l) for l in open(path, encoding="utf-8")]
assert lines[0]["e"] == "run_start" and lines[0]["v"] == 1
assert sum(1 for l in lines if l["e"] == "action") == 5

# 3) profile — 4일 데이터, 매일 물: diligence 1.0, skill 1.0, reaction 1.0
p = behavior.profile()
assert p["diligence"] == 1.0, p
assert p["skill"] == 1.0, p
assert p["reaction"] == 1.0, p
assert 0.0 <= p["neglect"] <= 1.0, p

# 4) resume_run — 집계가 파일 재생으로 동일하게 복원
saved = game_state.behavior_run_file
behavior.resume_run(None)          # 초기화
assert behavior.profile() == behavior.NEUTRAL, "런 없으면 중립"
behavior.resume_run(saved)
assert behavior.profile() == p, "재생 후 profile 동일해야 한다"

# 5) 데이터 3일 미만이면 중립
behavior.start_run("apple", "가뭄해", None)
behavior.log("action", kind="물 주기", day=1)
assert behavior.profile() == behavior.NEUTRAL

# 6) event_weight/difficulty_factor 클램프 + 도전 모드 중립
game_state.challenge = "drought"
assert behavior.event_weight("story") == 1.0
assert behavior.difficulty_factor() == 1.0
game_state.challenge = None
for kind in ("story", "memory", "minigame", "unknown"):
    assert 0.5 <= behavior.event_weight(kind) <= 2.0
assert 0.9 <= behavior.difficulty_factor() <= 1.1

# 7) 기록 실패 내성 — _path가 None이어도 예외 없이 지나간다
behavior._path = None
behavior.log("action", kind="물 주기", day=9)

# 8) session — sessions.jsonl 별도 파일
behavior.session("start")
assert os.path.exists(os.path.join(behavior._dir(), "sessions.jsonl"))

# 9) client_id — 익명 UUID, 재호출 시 동일
cid = behavior.client_id()
assert len(cid) == 32 and cid == behavior.client_id()

# 10) run_timeline / lifetime_scan 스모크
behavior.resume_run(saved)
tl = behavior.run_timeline()
assert tl and tl[0][0] == 1, tl
scan = behavior.lifetime_scan()
assert scan["runs"] >= 2 and scan["actions"].get("물 주기", 0) >= 5, scan

# 11) 세이브 왕복 — behavior_run_file이 스냅샷에 실리고 복원 시 resume된다
assert "behavior_run_file" in _ss._GS_FIELDS
game_state.behavior_run_file = saved
snap = {"version": 1, "game_state": {k: getattr(game_state, k, None) for k in _ss._GS_FIELDS},
        "farm": {}}
game_state.behavior_run_file = None
behavior.resume_run(None)
_ss.restore_state(snap)
assert game_state.behavior_run_file == saved
assert behavior.profile() == p, "restore_state가 resume_run까지 해야 한다"

# 12) telemetry 설정 기본값 OFF
assert _ss.get_setting("telemetry") is False

print("BEHAVIOR OK")
