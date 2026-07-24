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
