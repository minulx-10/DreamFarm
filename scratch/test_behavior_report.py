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
