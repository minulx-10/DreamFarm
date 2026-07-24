# 행동 데이터 시스템 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 플레이어 행동을 단일 이벤트 로그(JSONL)로 기록하고 그 위에 게임 내 기록 뷰·반응형 게임플레이·개발자 리포트·옵트인 텔레메트리 4종을 얹는다.

**Architecture:** `core/behavior.py` 단일 쓰기 경로. 모든 행동이 `behavior.log()` 하나를 거쳐 런당 JSONL 1파일 + 인메모리 집계로 남는다. 4개 소비자는 전부 파생(뷰=집계, 반응형=`profile()`, 리포트=파일 스캔, 텔레메트리=파일 배치 업로드). 스펙: `specs/2026-07-24-behavior-data-design.md`.

**Tech Stack:** Python 3 stdlib만 (pygame-ce 게임 본체). 텔레메트리 서버는 Cloudflare Worker + D1 (JS). HTTP는 `urllib.request` (Android 빌드에 requests 없음 — buildozer.spec `requirements = python3,pygame-ce`).

## Global Constraints

- 행동 기록·업로드 실패는 **어떤 경우에도 게임 진행을 막지 않는다** — behavior/telemetry 공개 함수는 전부 예외를 삼킨다.
- 플레이어 자유 텍스트(`player_name` 등)는 **절대 로그에 넣지 않는다** (PII 차단).
- 텔레메트리는 **옵트인, 기본 OFF** (`_DEFAULT_SETTINGS`에 `"telemetry": False`).
- 반응형 조정은 도전 규칙(`game_state.challenge` 진리값) 중엔 **비활성** (배수 1.0).
- 이벤트 가중치 클램프 [0.5, 2.0], 난이도 배수 클램프 [0.9, 1.1].
- HTTP는 stdlib `urllib.request`만. 타임아웃 3초, 업로드는 데몬 스레드.
- 테스트는 이 레포 관행대로: pytest 없음, `python scratch/<script>.py` + bare assert + SDL dummy 드라이버 + 저장 경로를 `scratch/_test_saves`로 우회 (scratch/smoke_test.py:18-24 패턴).
- i18n: 새 UI 문자열은 한국어 원문을 키로 `core/i18n_data.py` EN dict에 영어 번역 추가. f-string 조립 금지 — 통짜 템플릿을 `i18n.tf`로 (stage4_harvest.py:305 주석 참고).
- 게임 내 하루 = 행동 1회 (`apply_field_pressure`에서 `self.day += 1`). 아침/저녁 페이즈 개념 없음 — 이벤트에 `phase` 필드는 넣지 않는다 (스펙에서 이 부분만 현실에 맞게 축소).
- 커밋 메시지는 기존 컨벤션(한국어, `feat:`/`fix:`/`docs:` 접두), 끝에 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

## 파일 구조

| 파일 | 역할 |
|---|---|
| `core/behavior.py` | 신규 — 이벤트 로그·집계·profile()·event_weight()·difficulty_factor()·lifetime_scan() |
| `core/telemetry.py` | 신규 — 옵트인 업로더 (urllib, 스레드, 실패 큐) |
| `tools/behavior_report.py` | 신규 — JSONL → HTML 리포트 (stdlib) |
| `tools/telemetry-worker/` | 신규 — Cloudflare Worker (wrangler.toml, src/index.js, schema.sql, README.md) |
| `scratch/test_behavior.py`, `scratch/test_behavior_report.py` | 신규 — bare-assert 테스트 |
| `core/game_state.py`, `core/save_system.py` | 수정 — `behavior_run_file` 필드·복원 훅·설정 기본값 |
| `scenes/farm_simulator.py`, `scenes/story_choice.py`, `scenes/ending.py`, `scenes/stage1~4_*.py`, `game_main.py` | 수정 — log() 훅 |
| `scenes/gallery.py` | 수정 — '발자취' 탭 |
| `core/narrative_data.py`, `core/dev_overlay.py`, `core/settings_overlay.py`, `core/i18n_data.py` | 수정 — 반응 문구·성향 표시·텔레메트리 토글·번역 |

---

### Task 1: core/behavior.py 토대 + 테스트

**Files:**
- Create: `core/behavior.py`
- Test: `scratch/test_behavior.py`

**Interfaces:**
- Consumes: `core.save_system._DIR`(저장 폴더), `save_system.load_meta()/update_meta()`, `core.game_state.game_state` 싱글턴.
- Produces (이후 모든 태스크가 사용):
  - `behavior.start_run(crop: str, seed: str, challenge: str|None) -> None`
  - `behavior.resume_run(name: str|None) -> None`
  - `behavior.log(event: str, **fields) -> None`
  - `behavior.session(state: str) -> None` — behavior/sessions.jsonl에 별도 기록
  - `behavior.profile() -> dict` — keys `diligence/neglect/skill/reaction`, 값 0.0~1.0
  - `behavior.event_weight(kind: str) -> float` — 0.5~2.0
  - `behavior.difficulty_factor() -> float` — 0.9~1.1
  - `behavior.run_timeline(name=None) -> list[tuple[int,int]]` — (day, 행동수) 정렬 리스트
  - `behavior.lifetime_scan(limit=50) -> dict` — keys `runs/events/actions/water_days/days/best_minigame`
  - `behavior.client_id() -> str` — meta에 1회 생성되는 익명 UUID hex
  - `behavior._dir() -> str` — `<저장폴더>/behavior` (telemetry가 사용)
  - 이벤트 스키마 v1: `{"v":1,"t":epoch,"e":이벤트명,...}`; 이벤트명 `run_start/action/minigame/choice/day_end/event_seen/ending/session`

- [ ] **Step 1: 실패하는 테스트 작성**

`scratch/test_behavior.py` 생성 (smoke_test.py의 경로 우회 패턴을 그대로 따르되 pygame 불필요):

```python
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

print("BEHAVIOR OK")
```

- [ ] **Step 2: 실패 확인**

실행: `python scratch/test_behavior.py`
기대: `ModuleNotFoundError: No module named 'core.behavior'` 계열로 FAIL

- [ ] **Step 3: core/behavior.py 구현**

```python
"""행동 데이터 — 플레이어 행동 이벤트 로그 (설계: specs/2026-07-24-behavior-data-design.md)

모든 행동은 log() 하나를 거쳐 런당 JSONL 1파일 + 인메모리 집계로 남는다.
네 소비자(갤러리 '발자취'·반응형 profile()·tools/behavior_report.py·core/telemetry.py)는
전부 여기서 파생한다. 기록 실패는 게임을 절대 막지 않는다 — 공개 함수는 예외를 삼킨다.
플레이어 자유 텍스트(player_name 등)는 어떤 이벤트에도 싣지 않는다 (PII 차단).
"""
import json
import os
import time
import uuid

from core import save_system
from core.game_state import game_state

SCHEMA_VERSION = 1

# 성향 기본값 — 데이터가 3일치 미만이면 이 중립값을 쓴다
NEUTRAL = {"diligence": 0.5, "neglect": 0.5, "skill": 0.5, "reaction": 0.5}

_path = None      # 현재 런 JSONL 절대경로 (None이면 파일 기록 생략, 집계만)
_agg = None       # 인메모리 집계
_warned = False   # 기록 실패 경고는 1회만


def _dir():
    d = os.path.join(save_system._DIR, "behavior")
    os.makedirs(d, exist_ok=True)
    return d


def _new_agg():
    return {
        "events": {},         # 이벤트명 -> 횟수
        "actions": {},        # 행동명 -> 횟수
        "days": {},           # day -> 그날 행동 수
        "water_days": set(),  # 물 준 day 집합
        "minigames": [],      # (stage, 정규화 점수 0.0~1.0)
        "weeds_sum": 0.0, "weeds_n": 0,   # day_end 잡초 수치 평균용
    }


def _aggregate(rec):
    if _agg is None:
        return
    e = rec.get("e")
    _agg["events"][e] = _agg["events"].get(e, 0) + 1
    if e == "action":
        kind = rec.get("kind", "")
        day = rec.get("day", 0)
        _agg["actions"][kind] = _agg["actions"].get(kind, 0) + 1
        _agg["days"][day] = _agg["days"].get(day, 0) + 1
        if kind == "물 주기":
            _agg["water_days"].add(day)
    elif e == "minigame":
        try:
            _agg["minigames"].append((rec.get("stage", ""), float(rec.get("norm", 0.0))))
        except (TypeError, ValueError):
            pass
    elif e == "day_end":
        w = rec.get("weeds")
        if isinstance(w, (int, float)):
            _agg["weeds_sum"] += w
            _agg["weeds_n"] += 1


def log(event, **fields):
    """행동 이벤트 한 건. 실패해도 조용히 넘어간다 — 게임이 우선이다."""
    global _warned
    try:
        rec = {"v": SCHEMA_VERSION, "t": round(time.time(), 3), "e": event}
        rec.update(fields)
        _aggregate(rec)
        if _path:
            with open(_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        if not _warned:
            _warned = True
            print("[behavior] 기록 실패 — 이후 경고는 생략한다")


def start_run(crop, seed, challenge):
    """새 회차 — 새 JSONL 파일을 열고 run_start를 남긴다."""
    global _path, _agg
    try:
        _agg = _new_agg()
        name = "run_%d.jsonl" % int(time.time() * 1000)
        _path = os.path.join(_dir(), name)
        game_state.behavior_run_file = name
        log("run_start", crop=crop, seed=seed, challenge=challenge)
    except Exception:
        _path = None


def resume_run(name):
    """세이브 로드 후 기존 런 파일에 이어 쓴다. 집계는 파일 재생으로 복원."""
    global _path, _agg
    _agg = _new_agg()
    _path = None
    try:
        if not name:
            return
        p = os.path.join(_dir(), os.path.basename(name))
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        _aggregate(json.loads(line))
                    except Exception:
                        continue  # 모르는/깨진 줄은 건너뛴다 (전방 호환)
            _path = p
    except Exception:
        _path = None


def session(state):
    """앱 시작/종료 — 런과 무관하게 sessions.jsonl에 남는다."""
    try:
        rec = {"v": SCHEMA_VERSION, "t": round(time.time(), 3), "e": "session", "state": state}
        with open(os.path.join(_dir(), "sessions.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def client_id():
    """익명 클라이언트 UUID — meta에 1회 생성. 텔레메트리 배치에만 쓴다."""
    try:
        meta = save_system.load_meta()
        cid = meta.get("client_id")
        if not cid:
            cid = uuid.uuid4().hex
            save_system.update_meta(client_id=cid)
        return cid
    except Exception:
        return "unknown"


def _clamp01(x):
    return max(0.0, min(1.0, x))


def profile():
    """현재 런 성향 4종 (0.0~1.0). 데이터 3일치 미만이면 중립.
    저장하지 않는다 — 로그에서 항상 재계산 (세이브 호환성 무풍)."""
    try:
        days = len(_agg["days"]) if _agg else 0
        if not _agg or days < 3:
            return dict(NEUTRAL)
        total = sum(_agg["days"].values())
        dil = len(_agg["water_days"]) / days
        # 기다리기 비중 33%면 방치 1.0으로 본다 (x3 스케일)
        neg = _agg["actions"].get("기다리기", 0) / max(1, total) * 3.0
        recent = [n for _, n in _agg["minigames"][-8:]]
        skill = sum(recent) / len(recent) if recent else 0.5
        rea = (1.0 - (_agg["weeds_sum"] / _agg["weeds_n"]) / 100.0
               if _agg["weeds_n"] else 0.5)
        return {"diligence": _clamp01(dil), "neglect": _clamp01(neg),
                "skill": _clamp01(skill), "reaction": _clamp01(rea)}
    except Exception:
        return dict(NEUTRAL)


def event_weight(kind):
    """이벤트 추첨 확률 배수 (0.5~2.0). 도전 규칙 중·데이터 부족 시 1.0."""
    try:
        if getattr(game_state, "challenge", None):
            return 1.0
        p = profile()
        if kind == "story":
            w = 1.0 + (p["diligence"] - 0.5) * 0.6
        elif kind == "memory":
            w = 1.0 + (p["reaction"] - 0.5) * 0.6
        elif kind == "minigame":
            w = 1.0 + (p["skill"] - 0.5) * 0.6
        else:
            w = 1.0
        return max(0.5, min(2.0, w))
    except Exception:
        return 1.0


def difficulty_factor():
    """미니게임 난이도 배수 0.9~1.1 (skill 기반). 도전 규칙 중엔 1.0."""
    try:
        if getattr(game_state, "challenge", None):
            return 1.0
        return max(0.9, min(1.1, 1.0 + (profile()["skill"] - 0.5) * 0.2))
    except Exception:
        return 1.0


def run_timeline(name=None):
    """(day, 행동수) 정렬 리스트 — 갤러리 타임라인용.
    name 생략 시 현재 런 집계, 지정 시 그 파일을 읽는다."""
    try:
        if name is None:
            if not _agg:
                return []
            return sorted(_agg["days"].items())
        days = {}
        p = os.path.join(_dir(), os.path.basename(name))
        with open(p, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                if rec.get("e") == "action":
                    d = rec.get("day", 0)
                    days[d] = days.get(d, 0) + 1
        return sorted(days.items())
    except Exception:
        return []


def lifetime_scan(limit=50):
    """저장된 런 파일 최근 limit개를 훑어 평생 패턴 요약 (갤러리 진입 시 1회).
    ponytail: 파일 수가 수백을 넘으면 캐시 파일 도입 — 지금은 최근 50개 컷."""
    out = {"runs": 0, "events": 0, "actions": {}, "water_days": 0, "days": 0,
           "best_minigame": 0.0}
    try:
        d = _dir()
        files = sorted(f for f in os.listdir(d)
                       if f.startswith("run_") and f.endswith(".jsonl"))[-limit:]
        for fname in files:
            out["runs"] += 1
            seen_days, wet_days = set(), set()
            try:
                with open(os.path.join(d, fname), encoding="utf-8") as f:
                    for line in f:
                        try:
                            rec = json.loads(line)
                        except Exception:
                            continue
                        out["events"] += 1
                        if rec.get("e") == "action":
                            k = rec.get("kind", "")
                            out["actions"][k] = out["actions"].get(k, 0) + 1
                            seen_days.add(rec.get("day", 0))
                            if k == "물 주기":
                                wet_days.add(rec.get("day", 0))
                        elif rec.get("e") == "minigame":
                            try:
                                out["best_minigame"] = max(out["best_minigame"],
                                                           float(rec.get("norm", 0.0)))
                            except (TypeError, ValueError):
                                pass
            except OSError:
                continue
            out["days"] += len(seen_days)
            out["water_days"] += len(wet_days)
    except Exception:
        pass
    return out
```

- [ ] **Step 4: 통과 확인**

실행: `python scratch/test_behavior.py`
기대: `BEHAVIOR OK`

- [ ] **Step 5: 커밋**

```bash
git add core/behavior.py scratch/test_behavior.py
git commit -m "feat: 행동 데이터 토대 — core/behavior.py 이벤트 로그·집계·성향 파생"
```

---

### Task 2: 세이브 통합 — behavior_run_file 왕복

**Files:**
- Modify: `core/game_state.py` (run_stats 초기화 근처, :36), `core/save_system.py` (_GS_FIELDS :95-110, restore_state :141-150, _DEFAULT_SETTINGS :346)
- Test: `scratch/test_behavior.py` 확장

**Interfaces:**
- Consumes: Task 1의 `behavior.resume_run(name)`.
- Produces: `game_state.behavior_run_file: str|None` (스냅샷 왕복), 설정 키 `"telemetry": False` (Task 11이 사용).

- [ ] **Step 1: 실패하는 테스트 추가** — `scratch/test_behavior.py` 끝, `print("BEHAVIOR OK")` 앞에:

```python
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
```

- [ ] **Step 2: 실패 확인** — `python scratch/test_behavior.py` → `AssertionError` (behavior_run_file not in _GS_FIELDS)

- [ ] **Step 3: 구현**

`core/game_state.py` — `self.run_stats = {}` (line 36) 바로 아래에:

```python
        self.behavior_run_file = None   # 이번 회차 행동 로그 파일명 (core/behavior.py)
```

`core/save_system.py` — `_GS_FIELDS` 리스트의 `"year_seed", "run_stats", "challenge",` 줄을:

```python
    "year_seed", "run_stats", "challenge", "behavior_run_file",
```

`core/save_system.py` — `restore_state(data)` 함수 끝(필드 복원 루프 뒤)에:

```python
    # 행동 로그 이어쓰기 — 집계는 파일 재생으로 복원된다 (순환 import 방지, 지연 import)
    from core import behavior
    behavior.resume_run(getattr(game_state, "behavior_run_file", None))
```

주의: `restore()`가 `restore_state()`를 부르지 않고 필드 복원을 중복 구현했다면(153-171), 같은 두 줄을 `restore()`의 game_state 복원 직후에도 넣는다 — 실제 코드를 열어 두 경로 모두 커버되는지 확인할 것.

`core/save_system.py` — `_DEFAULT_SETTINGS`에 키 추가:

```python
_DEFAULT_SETTINGS = {"autosave": True, "show_version": True, "language": "ko", "update_check": True,
                     "text_speed": "normal",   # 타자기 텍스트 속도: slow | normal | fast
                     "bgm_volume": 0.30, "sfx_volume": 0.55, "muted": False,
                     "telemetry": False}       # 행동 데이터 공유 (옵트인 — 기본 꺼짐)
```

- [ ] **Step 4: 통과 확인** — `python scratch/test_behavior.py` → `BEHAVIOR OK`; 회귀: `python scratch/smoke_test.py` → `ALL SCENES OK`

- [ ] **Step 5: 커밋**

```bash
git add core/game_state.py core/save_system.py scratch/test_behavior.py
git commit -m "feat: 행동 로그 세이브 왕복 — behavior_run_file 스냅샷·복원 + telemetry 설정 기본값"
```

---

### Task 3: 농장 훅 — run_start·action·day_end·수확·event_seen

**Files:**
- Modify: `scenes/farm_simulator.py` (import부, :187-204 런 시작, :348-366 `_run_action`, :313-337 `do_action` 수확 분기, :595 `apply_field_pressure`, :652 `try_trigger_story`, :809 `try_trigger_memory`, :857 `try_trigger_minigame`)

**Interfaces:**
- Consumes: `behavior.start_run/log` (Task 1).
- Produces: 로그에 `run_start/action/day_end/event_seen` 이벤트가 실제로 쌓인다 (Task 5 뷰·Task 9 리포트의 데이터 원천).

- [ ] **Step 1: 훅 구현** (렌더 없는 로직 훅이라 테스트는 Step 2의 시뮬레이션 스크립트가 겸한다)

`scenes/farm_simulator.py` 상단 import에 `from core import behavior` 추가.

런 시작 — 도전 규칙 if/elif 체인(`elif ch == "no_journal":` 블록) **바로 뒤**에 (challenge가 year_seed를 덮은 뒤여야 최종값이 실린다):

```python
        # 행동 데이터 — 새 회차 로그 시작 (도전 규칙 반영 뒤의 최종 seed로)
        behavior.start_run(game_state.crop, game_state.year_seed, ch)
```

행동 관문 — `_run_action`의 `game_state.run_stats[action] = ...` 줄 바로 아래:

```python
        behavior.log("action", kind=action, day=self.day)
```

수확 — `do_action`(:313-337)의 수확 처리 분기(수확 씬으로 넘어가는 지점)에:

```python
            behavior.log("action", kind="수확하기", day=self.day)
```

하루 마감 — `apply_field_pressure`의 `self.day += 1` **바로 앞**에 (지난 하루의 마감 수치):

```python
        # 행동 데이터 — 하루 마감 시점의 밭 상태 (필드명은 _FARM_FIELDS 참고, 없으면 None)
        behavior.log("day_end", day=self.day,
                     growth=getattr(self, "growth", None),
                     moisture=getattr(self, "moisture", None),
                     health=getattr(self, "health", None),
                     weeds=getattr(self, "weeds", None),
                     drainage=getattr(self, "drainage", None))
```

구현 시 `core/save_system.py:115-124`의 `_FARM_FIELDS`를 열어 실제 속성명(weeds/drainage/moisture/health)을 확인하고 위 getattr 이름을 맞춘다. 존재하지 않는 이름은 None으로 실릴 뿐 죽지 않는다.

이벤트 목격 — `try_trigger_story`에서 `game_state.current_scene = "story_choice"` 직전:

```python
        behavior.log("event_seen", kind="story", title=event["title"], day=self.day)
```

`try_trigger_memory`에서 회상이 확정되어 씬 전환/표시되는 지점에 (pick_memory 결과 확정 후):

```python
        behavior.log("event_seen", kind="memory", day=self.day)
```

`try_trigger_minigame`에서 미니게임 씬으로 전환이 확정되는 각 지점에:

```python
            behavior.log("event_seen", kind="minigame", day=self.day)
```

- [ ] **Step 2: 검증 스크립트 실행**

기존 `scratch/playtest.py`(헤드리스 자동 플레이)가 있으면 그대로 실행, 없으면 아래 일회성 확인:

```bash
python - <<'EOF'
import os, sys, json
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame; pygame.init(); pygame.display.set_mode((800, 600))
from core import save_system as _ss
tmp = os.path.abspath("scratch/_test_saves/hook_test"); os.makedirs(tmp, exist_ok=True)
_ss._DIR = tmp; _ss.META_PATH = os.path.join(tmp, "save_data.json"); _ss._meta_cache = None
from core.game_state import game_state
from core import behavior
game_state.crop = "carrot"
from scenes.farm import FarmScene
farm = FarmScene()
sim = farm.sim
for _ in range(5):
    sim._run_action("물 주기", farm)
path = os.path.join(behavior._dir(), game_state.behavior_run_file)
events = [json.loads(l)["e"] for l in open(path, encoding="utf-8")]
assert "run_start" in events and events.count("action") >= 5 and "day_end" in events, events
print("HOOKS OK")
EOF
```

기대: `HOOKS OK`. (FarmScene 생성자 시그니처가 다르면 smoke_test.py가 FarmScene을 어떻게 띄우는지 보고 맞춘다.)

- [ ] **Step 3: 회귀** — `python scratch/smoke_test.py` → `ALL SCENES OK`

- [ ] **Step 4: 커밋**

```bash
git add scenes/farm_simulator.py
git commit -m "feat: 농장 행동 훅 — run_start·action·day_end·event_seen 로그"
```

---

### Task 4: 나머지 훅 — choice·ending·session·minigame

**Files:**
- Modify: `scenes/story_choice.py` (`_apply` :123-155, `_resolve_qte` :157~), `scenes/ending.py` (:199-208), `game_main.py` (:73-74 시작, :617-621 종료), `scenes/stage1_sort.py` (:159-179), `scenes/stage2_water.py` (:54-74), `scenes/stage3_pest.py` (:66-89), `scenes/stage4_harvest.py` (:294-312)

**Interfaces:**
- Consumes: `behavior.log/session` (Task 1).
- Produces: `choice/ending/minigame/session` 이벤트. minigame 이벤트의 `norm` 필드(0.0~1.0)는 Task 1 profile()의 skill 원천.

- [ ] **Step 1: 훅 구현**

`scenes/story_choice.py` — `_apply`의 `save_system.record_story(self.canon_title)` 바로 아래:

```python
            from core import behavior
            behavior.log("choice", title=self.canon_title,
                         picked="b" if choice == self.choice_b else "a")
```

`_resolve_qte`에도 record_story 하는 지점에 동일 패턴(선택지 변수명은 그 함수 것을 사용). 두 경로 모두 `if not replay:` 가드 안쪽에 넣는다 — 갤러리 다시보기는 기록하지 않는다.

`scenes/ending.py` — `achievements.on_run_recorded(days, ending_type)` (line 208) 바로 아래, 같은 들여쓰기:

```python
                from core import behavior
                behavior.log("ending", kind=ending_type, days=days)
```

`game_main.py` — `def main():` 안 `pygame.init()` 다음 줄에:

```python
    from core import behavior
    behavior.session("start")
```

종료부 `steam.shutdown()` 바로 앞에:

```python
    behavior.session("stop")
```

미니게임 4종 — 각 finalize 블록에서 `game_state.current_scene = "transition"` 직전에 (성적 정규화 0.0~1.0):

`stage1_sort.py`:
```python
                from core import behavior
                behavior.log("minigame", stage="stage1",
                             score=game_state.score,
                             norm=max(0.0, min(1.0, game_state.score / 500.0)))
```

`stage2_water.py` (timed_out/성공 분기 합류 뒤):
```python
                from core import behavior
                behavior.log("minigame", stage="stage2",
                             score=game_state.score,
                             norm=0.4 if self.timed_out else 1.0)
```

`stage3_pest.py`:
```python
                from core import behavior
                behavior.log("minigame", stage="stage3",
                             score=game_state.score,
                             norm=max(0.0, min(1.0, game_state.score / 500.0)))
```

`stage4_harvest.py` (perfects 계산 뒤):
```python
                from core import behavior
                behavior.log("minigame", stage="stage4",
                             score=perfects,
                             norm=perfects / max(1, self.max_attempts))
```

- [ ] **Step 2: 회귀** — `python scratch/smoke_test.py` → `ALL SCENES OK`; `python scratch/test_behavior.py` → `BEHAVIOR OK`

- [ ] **Step 3: 커밋**

```bash
git add scenes/story_choice.py scenes/ending.py game_main.py scenes/stage1_sort.py scenes/stage2_water.py scenes/stage3_pest.py scenes/stage4_harvest.py
git commit -m "feat: 행동 훅 확장 — 선택·엔딩·세션·미니게임 성적 로그"
```

---

### Task 5: 갤러리 '발자취' 탭

**Files:**
- Modify: `scenes/gallery.py` (`_update_tab_rects` :73-92, draw 분기 :256-265, handle_events 휠 :131-143, `__init__`), `core/i18n_data.py` (EN dict)

**Interfaces:**
- Consumes: `behavior.lifetime_scan()`, `behavior.run_timeline(name)`, `save_system.load_meta()` (최근 런 파일명은 `game_state.behavior_run_file` 또는 behavior 디렉토리 최신 파일).
- Produces: 갤러리 탭 id `"trace"` (한국어 라벨 "발자취").

- [ ] **Step 1: 구현**

`_update_tab_rects` — tabs 리스트에 `("trace", "발자취")`를 `("storehouse", "창고")` 뒤에 추가하고, 6탭까지 800px 안에 들어가게 폭 공식 수정:

```python
        n = len(tabs)
        gap = 8
        w = 150 if n <= 4 else (138 if n == 5 else 124)
        x = (800 - (w * n + gap * (n - 1))) // 2
```

draw 분기(:256-265)에 추가:

```python
        elif self.active_tab == "trace":
            self._draw_trace_tab(screen)
```

`__init__`에 스캔 1회 (갤러리는 FRESH_ON_ENTER — 진입마다 새 인스턴스라 여기서 계산해도 신선하다). gallery.py에 `from core.game_state import game_state` import가 없으면 추가:

```python
        # 발자취 탭 데이터 — 진입 시 1회 스캔
        from core import behavior
        self.trace_scan = behavior.lifetime_scan()
        latest = getattr(game_state, "behavior_run_file", None)
        if not latest:
            try:
                import os
                files = sorted(f for f in os.listdir(behavior._dir())
                               if f.startswith("run_") and f.endswith(".jsonl"))
                latest = files[-1] if files else None
            except Exception:
                latest = None
        self.trace_timeline = behavior.run_timeline(latest) if latest else []
```

`_draw_trace_tab` 신설 — 기존 `_draw_storehouse_tab`(:636-658)의 패널·폰트·행 렌더 문법을 그대로 따른다:

```python
    def _draw_trace_tab(self, screen):
        """발자취 — 행동 데이터 요약. 위: 최근 회차 일별 타임라인, 아래: 평생 패턴."""
        # 1) 최근 회차 타임라인 (일별 행동 수 막대)
        tl_area = pygame.Rect(90, 160, 620, 170)
        draw_light_panel(screen, tl_area)
        st = self.font_section.render(i18n.t("최근 회차의 하루하루"), True, TEXT_DARK)
        screen.blit(st, (tl_area.x + 16, tl_area.y + 8))
        if not self.trace_timeline:
            empty = self.font_small.render(i18n.t("아직 남은 발자취가 없다."), True, TEXT_MUTED)
            screen.blit(empty, (tl_area.x + 16, tl_area.y + 60))
        else:
            days = self.trace_timeline[-24:]                    # 최근 24일까지만
            peak = max(c for _, c in days) or 1
            bw = min(20, (tl_area.w - 32) // max(1, len(days)))
            x = tl_area.x + 16
            base = tl_area.bottom - 34
            for day, cnt in days:
                h = max(3, int(90 * cnt / peak))
                pygame.draw.rect(screen, (123, 92, 65), (x, base - h, bw - 3, h))
                ds = get_font(10).render(str(day), True, TEXT_MUTED)
                screen.blit(ds, (x, base + 4))
                x += bw
        # 2) 평생 패턴
        pat_area = pygame.Rect(90, 346, 620, 190)
        draw_light_panel(screen, pat_area)
        st2 = self.font_section.render(i18n.t("평생의 패턴"), True, TEXT_DARK)
        screen.blit(st2, (pat_area.x + 16, pat_area.y + 8))
        scan = self.trace_scan
        top_action = max(scan["actions"].items(), key=lambda kv: kv[1])[0] if scan["actions"] else "-"
        wet = int(100 * scan["water_days"] / scan["days"]) if scan["days"] else 0
        rows = [
            (i18n.t("기록된 회차"), str(scan["runs"])),
            (i18n.t("기록된 행동"), str(scan["events"])),
            (i18n.t("가장 자주 한 일"), i18n.t(top_action)),
            (i18n.tf("물 준 날의 비율: {p}%", p=wet), ""),
            (i18n.tf("미니게임 최고 기록: {p}%", p=int(scan["best_minigame"] * 100)), ""),
        ]
        y = pat_area.y + 44
        for label, val in rows:
            ls = self.font_small.render(label, True, TEXT_MUTED)
            screen.blit(ls, (pat_area.x + 16, y))
            if val:
                vs = self.font_small.render(val, True, TEXT_DARK)
                screen.blit(vs, (pat_area.right - 16 - vs.get_width(), y))
            y += 26
```

(파일 상단 import에 이미 있는 것 재사용: `draw_light_panel`, `get_font`, `TEXT_DARK`, `TEXT_MUTED`, `i18n`. 없으면 storehouse 탭이 쓰는 import를 확인해 맞춘다. 스크롤 불필요 — 콘텐츠 고정 높이.)

`core/i18n_data.py` EN dict에 (파일 내 `# ── scenes/gallery.py ──` 구획에) 추가:

```python
    "발자취": "Footprints",
    "최근 회차의 하루하루": "Day by day, last run",
    "아직 남은 발자취가 없다.": "No footprints left yet.",
    "평생의 패턴": "Lifetime patterns",
    "기록된 회차": "Runs recorded",
    "기록된 행동": "Actions recorded",
    "가장 자주 한 일": "Most frequent task",
    "물 준 날의 비율: {p}%": "Days watered: {p}%",
    "미니게임 최고 기록: {p}%": "Best minigame score: {p}%",
```

- [ ] **Step 2: 헤드리스 렌더 검증** — 기존 스크린샷 방식(HANDOFF.md 노하우) 재사용:

```bash
python - <<'EOF'
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame; pygame.init()
screen = pygame.display.set_mode((800, 600))
from scenes.gallery import GalleryScene
g = GalleryScene()
g.active_tab = "trace"
g.draw(screen)
pygame.image.save(screen, "scratch/qa/trace_tab.png")
print("TRACE TAB RENDER OK")
EOF
```

기대: `TRACE TAB RENDER OK` + `scratch/qa/trace_tab.png` 눈으로 확인 (레이아웃 겹침·글자 잘림).

- [ ] **Step 3: 회귀** — `python scratch/smoke_test.py` → `ALL SCENES OK`

- [ ] **Step 4: 커밋**

```bash
git add scenes/gallery.py core/i18n_data.py
git commit -m "feat: 갤러리 '발자취' 탭 — 회차 타임라인·평생 행동 패턴"
```

---

### Task 6: 반응형 ① 서사 — 성향 문구 + dev_overlay 표시

**Files:**
- Modify: `core/narrative_data.py` (ACTION_ECHOES 근처에 풀 추가 + 함수), `scenes/farm_simulator.py` (`apply_field_pressure`), `core/dev_overlay.py` (draw :149 근처), `core/i18n_data.py`

**Interfaces:**
- Consumes: `behavior.profile()` (Task 1), `pick_fresh()` (narrative_data.py:471), `push_thought` (farm_simulator 기존 메서드).
- Produces: `narrative_data.pick_behavior_echo(profile: dict) -> str|None`.

- [ ] **Step 1: 구현**

`core/narrative_data.py` — FATHER_ECHOES(:81-89) 아래에 풀과 선택 함수:

```python
# ── 행동 성향 문구 — 플레이어의 습관을 밭이 알아본다 (core/behavior.profile 기반) ──
BEHAVIOR_ECHOES = {
    "diligent": [   # diligence >= 0.75
        "너 새벽마다 물을 주더라. 아버지가 그랬듯이.",
        "하루도 거르지 않는 손이 있다. 흙은 그걸 기억한다.",
    ],
    "neglect": [    # neglect >= 0.75
        "밭은 기다림도 안다. 다만 너무 긴 기다림은 목마름이 된다.",
        "며칠 손이 뜸했다. 잎이 먼저 알아챘다.",
    ],
    "skilled": [    # skill >= 0.8
        "손끝이 야물어졌다. 처음 잡던 호미가 아니다.",
    ],
    "responsive": [ # reaction >= 0.8
        "잡초가 오래 버티지 못하는 밭이 됐다.",
    ],
}


def pick_behavior_echo(profile):
    """성향이 뚜렷할 때만 문구 하나 (없으면 None). 호출부가 빈도를 조절한다."""
    keys = []
    if profile.get("diligence", 0.5) >= 0.75:
        keys.append("diligent")
    if profile.get("neglect", 0.5) >= 0.75:
        keys.append("neglect")
    if profile.get("skill", 0.5) >= 0.8:
        keys.append("skilled")
    if profile.get("reaction", 0.5) >= 0.8:
        keys.append("responsive")
    if not keys:
        return None
    return pick_fresh(BEHAVIOR_ECHOES[random.choice(keys)])
```

`scenes/farm_simulator.py` — `apply_field_pressure`에서 `self.day += 1` 뒤, 4일마다 25% 확률로 (기존 push_thought 사용 예: :642):

```python
        # 행동 성향 문구 — 습관이 뚜렷해지면 이따금 밭이 알은체한다
        if self.day % 4 == 0 and random.random() < 0.25:
            from core.narrative_data import pick_behavior_echo
            echo = pick_behavior_echo(behavior.profile())
            if echo:
                self.push_thought(echo, dur=5.0)
```

`core/dev_overlay.py` — draw()의 `if self.msg:` (line 149) 바로 앞에:

```python
        # 행동 성향 실시간 표시 (개발용)
        from core import behavior
        p = behavior.profile()
        prof = get_font(13).render(
            "성향 성실%.2f 방치%.2f 숙련%.2f 대응%.2f" % (
                p["diligence"], p["neglect"], p["skill"], p["reaction"]),
            True, (170, 200, 180))
        screen.blit(prof, (self.panel.x + 20, self.panel.bottom - 56))
```

`core/i18n_data.py` — BEHAVIOR_ECHOES의 한국어 문구 6종 EN 번역 추가 (표시 계층에서 t() 자동 적용):

```python
    "너 새벽마다 물을 주더라. 아버지가 그랬듯이.": "You water at dawn, every day. Like father did.",
    "하루도 거르지 않는 손이 있다. 흙은 그걸 기억한다.": "A hand that never skips a day. The soil remembers.",
    "밭은 기다림도 안다. 다만 너무 긴 기다림은 목마름이 된다.": "The field knows patience too. But too long a wait becomes thirst.",
    "며칠 손이 뜸했다. 잎이 먼저 알아챘다.": "The hands have been away for days. The leaves noticed first.",
    "손끝이 야물어졌다. 처음 잡던 호미가 아니다.": "Your fingers have grown sure. Not the same hoe-grip as day one.",
    "잡초가 오래 버티지 못하는 밭이 됐다.": "Weeds don't last long in this field anymore.",
```

- [ ] **Step 2: 검증** — 극단 성향에서 문구가 나오는지:

```bash
python - <<'EOF'
import sys; sys.path.insert(0, ".")
from core.narrative_data import pick_behavior_echo
assert pick_behavior_echo({"diligence": 0.9, "neglect": 0.1, "skill": 0.5, "reaction": 0.5})
assert pick_behavior_echo({"diligence": 0.5, "neglect": 0.5, "skill": 0.5, "reaction": 0.5}) is None
print("ECHO OK")
EOF
```

- [ ] **Step 3: 회귀** — `python scratch/smoke_test.py` → `ALL SCENES OK`

- [ ] **Step 4: 커밋**

```bash
git add core/narrative_data.py scenes/farm_simulator.py core/dev_overlay.py core/i18n_data.py
git commit -m "feat: 반응형 서사 — 행동 성향 문구 + 개발 오버레이 성향 표시"
```

---

### Task 7: 반응형 ② 이벤트 풀 가중치

**Files:**
- Modify: `scenes/farm_simulator.py` (`try_trigger_story` :659, `try_trigger_memory` :820-824, `try_trigger_minigame` :857~)

**Interfaces:**
- Consumes: `behavior.event_weight(kind)` (Task 1 — 도전 모드·데이터 부족 시 1.0을 보장하므로 호출부는 무조건 곱해도 안전).

- [ ] **Step 1: 구현**

`try_trigger_story` — `if random.random() > 0.32:` 를:

```python
            if random.random() > 0.32 * behavior.event_weight("story"):
```

`try_trigger_memory` — `chance = 0.24 if u < 18 else 0.14 if u < 45 else 0.06` 바로 아래에:

```python
        chance *= behavior.event_weight("memory")
```

`try_trigger_minigame` — 날씨 미니게임 35% 확률 지점(`0.35` 리터럴)을:

```python
        0.35 * behavior.event_weight("minigame")
```

(실제 코드에서 0.35가 비교식 어느 쪽에 있는지 확인해 같은 의미로 곱한다. forced/보장 경로 — first_due, growth 강제 — 에는 **가중치를 곱하지 않는다**: 보장은 보장대로 둔다.)

- [ ] **Step 2: 검증** — 가중치 극단에서도 확률이 0이나 1로 붕괴하지 않는지 (0.32×2.0=0.64 < 1, 0.06×0.5=0.03 > 0 — 산술 확인이면 충분). 회귀: `python scratch/smoke_test.py` → `ALL SCENES OK`, `python scratch/qa_v24.py` (이벤트 시스템 통합 테스트) → 통과.

- [ ] **Step 3: 커밋**

```bash
git add scenes/farm_simulator.py
git commit -m "feat: 반응형 이벤트 가중치 — 성향이 이야기·회상·미니게임 빈도에 살며시 실린다"
```

---

### Task 8: 반응형 ③ 미니게임 난이도

**Files:**
- Modify: `scenes/stage1_sort.py` (:60), `scenes/stage2_water.py` (:17), `scenes/stage3_pest.py` (:48 + Bug 속도), `scenes/stage4_harvest.py` (:91-96)

**Interfaces:**
- Consumes: `behavior.difficulty_factor()` (0.9~1.1; 도전 모드 1.0 보장).

- [ ] **Step 1: 구현** — 숙련될수록(>1.0) 살짝 빡빡하게. 각 스테이지 `__init__`에서:

`stage1_sort.py` — `game_state.timer = 24.0` 을:

```python
        from core import behavior
        game_state.timer = 24.0 / behavior.difficulty_factor()   # 숙련자는 시간이 조금 짧다
```

주의: 나누기 방향 — factor 1.1(숙련)이면 timer 21.8로 **줄어든다**. 이하 동일 원칙.

`stage2_water.py` — `game_state.timer = 24.0` 동일 처리.

`stage3_pest.py` — `game_state.timer = 15.0` 동일 처리 + Bug 생성 후 속도 보정:

```python
        from core import behavior
        d = behavior.difficulty_factor()
        game_state.timer = 15.0 / d
        self.bugs = [Bug() for _ in range(12)]
        for b in self.bugs:
            b.dx *= d
            b.dy *= d
```

(기존 `self.bugs = [Bug() for _ in range(12)]` 줄을 위처럼 감싼다.)

`stage4_harvest.py` — `self.slide_speed = 32.0` 을:

```python
        from core import behavior
        self.slide_speed = 32.0 * behavior.difficulty_factor()   # 숙련자는 미끄러짐이 조금 빠르다
```

- [ ] **Step 2: 검증** — 도전 모드에서 순정 값 유지 확인:

```bash
python - <<'EOF'
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, ".")
import pygame; pygame.init(); pygame.display.set_mode((800, 600))
from core.game_state import game_state
game_state.challenge = "drought"
from scenes.stage3_pest import Stage3Scene
s = Stage3Scene()
assert abs(game_state.timer - 15.0) < 1e-9, game_state.timer
game_state.challenge = None
print("DIFFICULTY GUARD OK")
EOF
```

- [ ] **Step 3: 회귀** — `python scratch/smoke_test.py` → `ALL SCENES OK`

- [ ] **Step 4: 커밋**

```bash
git add scenes/stage1_sort.py scenes/stage2_water.py scenes/stage3_pest.py scenes/stage4_harvest.py
git commit -m "feat: 반응형 미니게임 난이도 — 숙련도 ±10% 보정, 도전 규칙 중 비활성"
```

---

### Task 9: 개발자 리포트 — tools/behavior_report.py

**Files:**
- Create: `tools/behavior_report.py`
- Test: `scratch/test_behavior_report.py`

**Interfaces:**
- Consumes: behavior JSONL 파일 (스키마 v1). `--dir` 미지정 시 `core.save_system._DIR/behavior`.
- Produces: 단일 HTML 파일 (기본 `scratch/behavior_report.html`), inline SVG 차트, 의존성 stdlib만.

- [ ] **Step 1: 실패하는 테스트 작성** — `scratch/test_behavior_report.py`:

```python
"""tools/behavior_report.py 스모크 — 샘플 JSONL → HTML. 사용: python scratch/test_behavior_report.py"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_test_saves", "report_test")
shutil.rmtree(tmp, ignore_errors=True)
os.makedirs(tmp, exist_ok=True)

sample = [
    {"v": 1, "t": 1.0, "e": "run_start", "crop": "carrot", "seed": "평년", "challenge": None},
    {"v": 1, "t": 2.0, "e": "action", "kind": "물 주기", "day": 1},
    {"v": 1, "t": 3.0, "e": "action", "kind": "잡초 뽑기", "day": 2},
    {"v": 1, "t": 4.0, "e": "minigame", "stage": "stage3", "score": 550, "norm": 1.0},
    {"v": 1, "t": 5.0, "e": "day_end", "day": 2, "weeds": 10},
    {"v": 1, "t": 6.0, "e": "ending", "kind": "정성", "days": 2},
    {"v": 99, "t": 7.0, "e": "future_event", "mystery": True},   # 전방 호환 — 죽으면 안 된다
]
with open(os.path.join(tmp, "run_1.jsonl"), "w", encoding="utf-8") as f:
    for rec in sample:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

out = os.path.join(tmp, "report.html")
from tools.behavior_report import build_report
build_report(tmp, out)
html = open(out, encoding="utf-8").read()
assert "<svg" in html, "SVG 차트가 있어야 한다"
assert "물 주기" in html, "행동 분포가 있어야 한다"
assert "run_1" in html, "런 목록이 있어야 한다"
print("REPORT OK")
```

- [ ] **Step 2: 실패 확인** — `python scratch/test_behavior_report.py` → `ModuleNotFoundError`/`ImportError` FAIL

- [ ] **Step 3: 구현** — `tools/behavior_report.py`:

```python
"""행동 데이터 리포트 — behavior JSONL 전체를 훑어 단일 HTML로 요약한다 (stdlib만).

사용: python tools/behavior_report.py [--dir 경로] [--out 경로]
기본 --dir: 게임 저장 폴더의 behavior/, 기본 --out: scratch/behavior_report.html
"""
import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _scan_run(path):
    """런 파일 하나 → 요약 dict. 모르는 이벤트는 세기만 하고 넘어간다 (전방 호환)."""
    s = {"file": os.path.basename(path), "crop": "-", "seed": "-", "challenge": None,
         "ending": "-", "days": 0, "events": 0, "actions": {}, "minigames": [],
         "weeds": []}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                s["events"] += 1
                e = rec.get("e")
                if e == "run_start":
                    s["crop"] = rec.get("crop", "-")
                    s["seed"] = rec.get("seed", "-")
                    s["challenge"] = rec.get("challenge")
                elif e == "action":
                    k = rec.get("kind", "?")
                    s["actions"][k] = s["actions"].get(k, 0) + 1
                    s["days"] = max(s["days"], rec.get("day", 0) or 0)
                elif e == "minigame":
                    try:
                        s["minigames"].append(float(rec.get("norm", 0.0)))
                    except (TypeError, ValueError):
                        pass
                elif e == "day_end":
                    if isinstance(rec.get("weeds"), (int, float)):
                        s["weeds"].append(rec["weeds"])
                elif e == "ending":
                    s["ending"] = rec.get("kind", "-")
    except OSError:
        pass
    return s


def _bar_chart(counts, width=640, row_h=24):
    """행동 분포 가로 막대 SVG."""
    if not counts:
        return "<p>데이터 없음</p>"
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    peak = items[0][1] or 1
    h = row_h * len(items) + 8
    parts = ['<svg width="%d" height="%d" xmlns="http://www.w3.org/2000/svg">' % (width, h)]
    for i, (k, v) in enumerate(items):
        y = 4 + i * row_h
        bw = int((width - 220) * v / peak)
        parts.append('<text x="4" y="%d" font-size="13">%s</text>' % (y + 15, html.escape(str(k))))
        parts.append('<rect x="150" y="%d" width="%d" height="%d" fill="#7b5c41"/>' % (y + 3, max(2, bw), row_h - 10))
        parts.append('<text x="%d" y="%d" font-size="12" fill="#555">%d</text>' % (156 + max(2, bw), y + 15, v))
    parts.append("</svg>")
    return "".join(parts)


def _trend_chart(values, width=640, height=120):
    """미니게임 성적 추이 폴리라인 SVG (0.0~1.0)."""
    if len(values) < 2:
        return "<p>미니게임 기록 %d건 — 추이 없음</p>" % len(values)
    step = (width - 40) / (len(values) - 1)
    pts = " ".join("%d,%d" % (20 + i * step, height - 15 - v * (height - 30))
                   for i, v in enumerate(values))
    return ('<svg width="%d" height="%d" xmlns="http://www.w3.org/2000/svg">'
            '<line x1="20" y1="%d" x2="%d" y2="%d" stroke="#ccc"/>'
            '<polyline points="%s" fill="none" stroke="#4a7b41" stroke-width="2"/>'
            "</svg>") % (width, height, height - 15, width - 20, height - 15, pts)


def build_report(src_dir, out_path):
    files = sorted(f for f in os.listdir(src_dir)
                   if f.startswith("run_") and f.endswith(".jsonl"))
    runs = [_scan_run(os.path.join(src_dir, f)) for f in files]
    all_actions, all_norms = {}, []
    for r in runs:
        for k, v in r["actions"].items():
            all_actions[k] = all_actions.get(k, 0) + v
        all_norms.extend(r["minigames"])
    rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td><td>%d</td><td>%.1f</td></tr>"
        % (html.escape(r["file"]), html.escape(str(r["crop"])), html.escape(str(r["seed"])),
           html.escape(str(r["ending"])), r["days"], r["events"],
           (sum(r["weeds"]) / len(r["weeds"])) if r["weeds"] else 0.0)
        for r in runs)
    doc = """<!doctype html><meta charset="utf-8"><title>몽중농원 행동 리포트</title>
<style>body{font-family:sans-serif;max-width:720px;margin:24px auto;padding:0 12px}
table{border-collapse:collapse;width:100%%}td,th{border:1px solid #ddd;padding:4px 8px;font-size:13px}
h2{margin-top:32px}</style>
<h1>몽중농원 행동 리포트</h1>
<p>런 %d개 · 이벤트 %d건</p>
<h2>런 목록</h2>
<table><tr><th>파일</th><th>작물</th><th>해</th><th>엔딩</th><th>일수</th><th>이벤트</th><th>평균 잡초</th></tr>%s</table>
<h2>행동 분포 (전체)</h2>%s
<h2>미니게임 성적 추이</h2>%s
""" % (len(runs), sum(r["events"] for r in runs), rows,
       _bar_chart(all_actions), _trend_chart(all_norms))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None)
    ap.add_argument("--out", default=os.path.join("scratch", "behavior_report.html"))
    args = ap.parse_args()
    src = args.dir
    if src is None:
        from core import save_system
        src = os.path.join(save_system._DIR, "behavior")
    if not os.path.isdir(src):
        print("behavior 폴더 없음:", src)
        return 1
    out = build_report(src, args.out)
    print("리포트 생성:", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: 통과 확인** — `python scratch/test_behavior_report.py` → `REPORT OK`

- [ ] **Step 5: 커밋**

```bash
git add tools/behavior_report.py scratch/test_behavior_report.py
git commit -m "feat: 행동 리포트 도구 — JSONL 스캔·SVG 차트 단일 HTML (stdlib)"
```

---

### Task 10: 텔레메트리 서버 — Cloudflare Worker + D1

**Files:**
- Create: `tools/telemetry-worker/wrangler.toml`, `tools/telemetry-worker/src/index.js`, `tools/telemetry-worker/schema.sql`, `tools/telemetry-worker/README.md`

**Interfaces:**
- Produces: `POST /v1/events` — body `{client_id, game_version, events: [...]}` (gzip 또는 평문 JSON), 응답 200 `ok` / 400 / 404. Task 11 클라이언트가 이 계약을 쓴다.

- [ ] **Step 1: 구현**

`tools/telemetry-worker/wrangler.toml`:

```toml
name = "dreamfarm-telemetry"
main = "src/index.js"
compatibility_date = "2026-07-01"

[[d1_databases]]
binding = "DB"
database_name = "dreamfarm-telemetry"
database_id = "REPLACE_ME"   # wrangler d1 create dreamfarm-telemetry 출력으로 교체
```

`tools/telemetry-worker/schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id TEXT NOT NULL,
  game_version TEXT,
  received_at INTEGER NOT NULL,
  payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_batches_client ON batches (client_id, received_at);
```

`tools/telemetry-worker/src/index.js`:

```js
// 몽중농원 텔레메트리 수신기 — POST /v1/events 배치를 D1에 그대로 쌓는다.
// 분석은 서버가 아니라 로컬(tools/behavior_report.py)에서 한다 — 여기는 수집만.
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method !== "POST" || url.pathname !== "/v1/events") {
      return new Response("not found", { status: 404 });
    }
    let body;
    try {
      const buf = await request.arrayBuffer();
      let text;
      if (request.headers.get("content-encoding") === "gzip") {
        const ds = new DecompressionStream("gzip");
        text = await new Response(new Response(buf).body.pipeThrough(ds)).text();
      } else {
        text = new TextDecoder().decode(buf);
      }
      body = JSON.parse(text);
    } catch (e) {
      return new Response("bad request", { status: 400 });
    }
    if (!body || typeof body.client_id !== "string" || !Array.isArray(body.events) ||
        body.events.length === 0 || body.events.length > 5000) {
      return new Response("bad request", { status: 400 });
    }
    const payload = JSON.stringify(body.events);
    if (payload.length > 1000000) {
      return new Response("too large", { status: 413 });
    }
    await env.DB.prepare(
      "INSERT INTO batches (client_id, game_version, received_at, payload) VALUES (?, ?, ?, ?)"
    ).bind(
      body.client_id.slice(0, 64),
      String(body.game_version || "").slice(0, 32),
      Date.now(),
      payload
    ).run();
    return new Response("ok");
  },
};
```

`tools/telemetry-worker/README.md`:

```markdown
# 몽중농원 텔레메트리 수신기

Cloudflare Worker + D1 (무료 티어). 수집만 한다 — 분석은 `tools/behavior_report.py`.

## 배포 (1회)

1. Cloudflare 계정 + `npm i -g wrangler` + `wrangler login`
2. `cd tools/telemetry-worker`
3. `wrangler d1 create dreamfarm-telemetry` → 출력된 `database_id`를 wrangler.toml의 REPLACE_ME에
4. `wrangler d1 execute dreamfarm-telemetry --remote --file=schema.sql`
5. `wrangler deploy` → 출력 URL(예: https://dreamfarm-telemetry.<계정>.workers.dev)
6. 게임 쪽 `core/telemetry.py`의 `URL`에 `<배포URL>/v1/events` 기입

## 데이터 확인

wrangler d1 execute dreamfarm-telemetry --remote --command "SELECT client_id, game_version, received_at, length(payload) FROM batches ORDER BY id DESC LIMIT 20"

## 계약

POST /v1/events — JSON(선택적 gzip, Content-Encoding: gzip):
{"client_id": "<uuid hex>", "game_version": "2.5.0", "events": [{...}, ...]}
이벤트 스키마는 specs/2026-07-24-behavior-data-design.md 참고. PII 없음(클라이언트가 보장).
```

- [ ] **Step 2: 검증** — 로컬 기동 확인 (wrangler 설치돼 있을 때만; 없으면 이 단계는 배포 시로 미룬다):

```bash
cd tools/telemetry-worker && wrangler dev --local
```

별도 셸: `curl -s -X POST http://localhost:8787/v1/events -d "{\"client_id\":\"abc\",\"game_version\":\"t\",\"events\":[{\"e\":\"x\"}]}"` → `ok`

- [ ] **Step 3: 커밋**

```bash
git add tools/telemetry-worker
git commit -m "feat: 텔레메트리 수신기 — Cloudflare Worker + D1 (수집 전용)"
```

---

### Task 11: 텔레메트리 클라이언트 + 설정 토글

**Files:**
- Create: `core/telemetry.py`
- Modify: `core/settings_overlay.py` (패널 :29, 버튼 Rect :52 근처, `_on_press` :279 근처, `_draw_panel` :407 근처), `scenes/ending.py` (Task 4 훅 아래), `game_main.py` (시작부), `core/i18n_data.py`
- Test: `scratch/test_behavior.py` 확장

**Interfaces:**
- Consumes: `behavior._dir()/client_id()`, `save_system.get_setting("telemetry")`, Task 10의 `POST /v1/events` 계약, `core.version.VERSION`.
- Produces: `telemetry.upload_run(name)`, `telemetry.retry_pending()`, `telemetry.enabled() -> bool`.

- [ ] **Step 1: 실패하는 테스트 추가** — `scratch/test_behavior.py`의 `print("BEHAVIOR OK")` 앞에:

```python
# 13) telemetry — URL 미설정이면 완전 비활성, 큐 왕복 동작
from core import telemetry
assert telemetry.enabled() is False          # URL 비어있음 + 설정 OFF
telemetry.upload_run(saved)                  # 비활성이어도 예외 없이 no-op
telemetry._queue(saved)
pending = json.load(open(telemetry._pending_path(), encoding="utf-8"))
assert saved in pending
telemetry._queue(saved)                      # 중복 삽입 방지
pending = json.load(open(telemetry._pending_path(), encoding="utf-8"))
assert pending.count(saved) == 1
```

- [ ] **Step 2: 실패 확인** — `python scratch/test_behavior.py` → `ModuleNotFoundError: core.telemetry` FAIL

- [ ] **Step 3: core/telemetry.py 구현**

```python
"""옵트인 텔레메트리 — 런 종료 시 행동 로그를 배치 업로드한다.

stdlib urllib만 쓴다 (Android 빌드에 requests 없음 — buildozer.spec 참고).
URL이 비어 있거나 설정(telemetry)이 꺼져 있으면 전부 no-op.
실패는 조용히 큐에 남겨 다음 세션 시작 때 재시도한다. 게임을 막는 일은 없다.
전송 내용 = 로컬 JSONL 그대로 (PII 없음 — behavior.py가 보장).
"""
import gzip
import json
import os
import threading
import urllib.request

from core import behavior, save_system
from core.version import VERSION

# 배포한 Worker 주소 (tools/telemetry-worker/README.md 절차 후 기입).
# 예: "https://dreamfarm-telemetry.<계정>.workers.dev/v1/events"
URL = ""
TIMEOUT = 3.0


def enabled():
    return bool(URL) and bool(save_system.get_setting("telemetry"))


def _pending_path():
    return os.path.join(behavior._dir(), "pending_upload.json")


def _load_pending():
    try:
        with open(_pending_path(), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _queue(name):
    """실패한 런 파일명을 재시도 큐에 남긴다 (중복 없이)."""
    try:
        pending = _load_pending()
        if name not in pending:
            pending.append(name)
        with open(_pending_path(), "w", encoding="utf-8") as f:
            json.dump(pending[-30:], f)   # 오래된 것부터 버린다
    except Exception:
        pass


def _unqueue(name):
    try:
        pending = [p for p in _load_pending() if p != name]
        with open(_pending_path(), "w", encoding="utf-8") as f:
            json.dump(pending, f)
    except Exception:
        pass


def _post(events):
    payload = json.dumps({"client_id": behavior.client_id(),
                          "game_version": VERSION,
                          "events": events}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        URL, data=gzip.compress(payload), method="POST",
        headers={"Content-Type": "application/json", "Content-Encoding": "gzip"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status == 200


def _upload_file(name):
    try:
        path = os.path.join(behavior._dir(), os.path.basename(name))
        events = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        if events and _post(events):
            _unqueue(name)
        else:
            _queue(name)
    except Exception:
        _queue(name)


def upload_run(name):
    """런 종료 시 호출 — 백그라운드 스레드로 업로드. 비활성이면 no-op."""
    if not name or not enabled():
        return
    threading.Thread(target=_upload_file, args=(name,), daemon=True).start()


def retry_pending():
    """세션 시작 시 호출 — 밀린 업로드 재시도."""
    if not enabled():
        return
    def _run():
        for name in list(_load_pending()):
            _upload_file(name)
    threading.Thread(target=_run, daemon=True).start()
```

- [ ] **Step 4: 훅 + 설정 토글**

`scenes/ending.py` — Task 4에서 넣은 `behavior.log("ending", ...)` 바로 아래:

```python
                from core import telemetry
                telemetry.upload_run(getattr(game_state, "behavior_run_file", None))
```

`game_main.py` — `behavior.session("start")` 아래:

```python
    from core import telemetry
    telemetry.retry_pending()
```

`core/settings_overlay.py` — 토글 1개, 기존 3부 패턴(:52 Rect, :279 클릭, :407 렌더) 그대로:

1. `__init__` — 패널 높이 536→566으로 키우고 (`pygame.Rect(220, 30, 360, 566)`, 화면 600 안: 30+566=596 OK), 버튼 Rect 추가:

```python
        self._telemetry_btn = pygame.Rect(self.panel.right - pad - 140, self.panel.y + 476, 140, 32)
```

기존 `_update_btn`/`_close_btn` 행이 y+476에 있으므로 실제 배치는 파일을 열어 충돌 없는 y(새 마지막 행 y+520 등)로 잡는다 — 원칙: 기존 버튼과 겹치지 않게 한 행 추가, 패널 바닥 여백 ≥14px.

2. `_on_press`:

```python
        elif self._telemetry_btn.collidepoint(pos):
            cur = save_system.get_setting("telemetry")
            save_system.set_setting("telemetry", not cur)
            audio.play("click")
```

3. `_draw_panel` (f-string 조립 대신 tf — i18n 규칙):

```python
        tele = save_system.get_setting("telemetry")
        self._draw_text_button(screen, self._telemetry_btn,
                               i18n.tf("데이터 공유: {onoff}", onoff="ON" if tele else "OFF"),
                               active=bool(tele))
        # 안내 한 줄 — 무엇이 공유되는지 명시 (옵트인 고지)
        note = get_font(11).render(i18n.t("익명 플레이 기록만 보냅니다. 이름·글은 보내지 않습니다."),
                                   True, TEXT_MUTED)
        screen.blit(note, (self.panel.x + 26, self._telemetry_btn.bottom + 6))
```

(`settings_overlay.py`에 i18n import가 없으면 추가. `get_font`/`TEXT_MUTED`는 이미 있음 — :12.)

`core/i18n_data.py`:

```python
    "데이터 공유: {onoff}": "Share data: {onoff}",
    "익명 플레이 기록만 보냅니다. 이름·글은 보내지 않습니다.": "Only anonymous play records are sent. Never your name or writing.",
```

- [ ] **Step 5: 통과 확인** — `python scratch/test_behavior.py` → `BEHAVIOR OK`; `python scratch/smoke_test.py` → `ALL SCENES OK`. 설정 화면 헤드리스 스크린샷으로 토글 배치 확인 (Task 5 Step 2와 같은 방식, settings_overlay를 열어 찍는다).

- [ ] **Step 6: 커밋**

```bash
git add core/telemetry.py core/settings_overlay.py scenes/ending.py game_main.py core/i18n_data.py scratch/test_behavior.py
git commit -m "feat: 옵트인 텔레메트리 — urllib 배치 업로더·실패 큐·설정 토글 (기본 OFF)"
```

---

### Task 12: 문서 갱신

**Files:**
- Modify: `CHANGELOG.md`, `HANDOFF.md`

- [ ] **Step 1: CHANGELOG.md** — 최상단에 미출시 섹션 (기존 버전 섹션 형식을 따른다):

```markdown
## 미출시

### 추가
- 행동 데이터 시스템: 모든 플레이 행동을 회차별 JSONL로 기록 (core/behavior.py, 스키마 v1)
- 갤러리 '발자취' 탭 — 회차 타임라인·평생 행동 패턴
- 반응형 게임플레이: 성향 문구(서사)·이벤트 빈도 가중치(0.5~2.0)·미니게임 난이도 ±10% (도전 규칙 중 비활성)
- 개발자 행동 리포트 tools/behavior_report.py (JSONL → HTML, stdlib)
- 옵트인 텔레메트리(기본 OFF): Cloudflare Worker 수신기(tools/telemetry-worker) + urllib 배치 업로더
```

- [ ] **Step 2: HANDOFF.md** — 기술 설계 노하우 섹션에 항목 추가:

```markdown
- **행동 데이터**: 모든 행동은 core/behavior.py `log()` 단일 관문 — JSONL(저장폴더/behavior/) + 인메모리 집계.
  성향(profile)은 저장하지 않고 로그에서 재계산(세이브 호환 무풍). 기록 실패는 전부 삼킨다 — 게임 우선.
  반응형 훅은 event_weight()/difficulty_factor()가 도전 모드·데이터 부족 시 1.0을 보장하므로 호출부는 무조건 곱한다.
  텔레메트리는 core/telemetry.py URL 상수가 비면 전체 no-op. 배포 절차는 tools/telemetry-worker/README.md.
  테스트: python scratch/test_behavior.py · scratch/test_behavior_report.py. 설계: specs/2026-07-24-behavior-data-design.md.
```

- [ ] **Step 3: 커밋**

```bash
git add CHANGELOG.md HANDOFF.md
git commit -m "docs: 행동 데이터 시스템 문서화 — CHANGELOG·HANDOFF"
```
