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
