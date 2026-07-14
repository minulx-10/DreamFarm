# -*- coding: utf-8 -*-
"""번역 JSON 동기화 도구 — GitHub PR 기반 번역 워크플로용.

정본(single source of truth)은 `core/i18n_data.py`의 `EN` 딕셔너리(한국어 원문 → 영어)다.
이 도구는 거기서 `core/locales/*.json`을 만들고 원문 목록과 동기화한다.

  - core/locales/ko.json      : 소스 문자열 목록 {한국어원문: 한국어원문}  ← 번역할 문자열의 정본 목록
  - core/locales/en.json      : 영어 번역        {한국어원문: English}      ← 베이스라인(기존 값 보존 병합)
  - core/locales/<lang>.json  : 기타 언어(ja/zh …). 새 키는 영어 값을 참고용으로 채워 넣고,
                                없어진 키는 지우며, 이미 번역된 값은 보존한다.

게임은 실행 시 `core/locales/<lang>.json`을 `i18n_data` 위에 병합해 읽는다(코드 재생성 불필요).
빈 문자열("") 값은 로더가 건너뛰므로, 미번역 키는 자동으로 **영어 베이스라인으로 폴백**된다.

사용:
  python tools/i18n_export.py            # ko/en + 기존 locales/*.json 을 원문과 동기화
  python tools/i18n_export.py --add ja   # 새 언어(ja) 파일을 영어 값으로 스캐폴드 생성
  python tools/i18n_export.py --check     # (CI) JSON 유효성·유령 키 검사 + 언어별 커버리지 리포트
                                          #      깨진 JSON이나 원문에 없는 키가 있으면 종료코드 1
"""
import os
import sys
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES = os.path.join(ROOT, "core", "locales")


def _load_baseline():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "i18n_data", os.path.join(ROOT, "core", "i18n_data.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return dict(getattr(mod, "EN", {}))


def _read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)


def _lang_files():
    if not os.path.isdir(LOCALES):
        return []
    return sorted(
        os.path.splitext(f)[0] for f in os.listdir(LOCALES)
        if f.endswith(".json") and os.path.splitext(f)[0] not in ("ko", "en"))


def sync(en):
    """ko.json/en.json 재생성 + 기타 언어 파일을 원문 키 집합과 맞춘다."""
    os.makedirs(LOCALES, exist_ok=True)
    keys = list(en.keys())

    # ko.json — 소스 목록(항상 전체 재생성)
    _write_json(os.path.join(LOCALES, "ko.json"), {k: k for k in keys})

    # en.json — 베이스라인. 기존 영어 값은 보존, 새 키만 채우고, 없어진 키는 제거.
    existing_en = _read_json(os.path.join(LOCALES, "en.json"))
    merged_en, added = {}, 0
    for k, base in en.items():
        v = existing_en.get(k)
        if isinstance(v, str) and v:
            merged_en[k] = v
        else:
            merged_en[k] = base
            added += 1
    _write_json(os.path.join(LOCALES, "en.json"), merged_en)
    print(f"ko.json: {len(keys)} keys | en.json: {len(merged_en)} keys ({added} new/baseline)")

    # 기타 언어 — 번역 보존, 새 키는 영어 참고값으로, 없어진 키는 제거.
    for lang in _lang_files():
        path = os.path.join(LOCALES, lang + ".json")
        cur = _read_json(path)
        out, new = {}, 0
        for k in keys:
            v = cur.get(k)
            if isinstance(v, str) and v:
                out[k] = v
            else:
                out[k] = en[k]   # 참고용 영어. 번역가가 덮어씀. (안 고치면 게임은 영어로 표시)
                new += 1
        _write_json(path, out)
        done = sum(1 for k in keys if out[k] != en[k])
        print(f"{lang}.json: {len(out)} keys | 번역됨 {done}/{len(keys)} ({new} 미번역/신규)")


def add_lang(en, code):
    path = os.path.join(LOCALES, code + ".json")
    if os.path.exists(path):
        print(f"이미 있음: {path} — 대신 sync로 갱신하세요.")
        return 1
    os.makedirs(LOCALES, exist_ok=True)
    _write_json(path, dict(en))   # 영어 값으로 시작 → 번역가가 값만 바꾸면 됨
    print(f"생성: core/locales/{code}.json ({len(en)} keys, 영어로 프리필)")
    print(f"→ core/i18n.py 의 _LANGS 에 '{code}' 추가하면 설정에서 전환 가능.")
    return 0


def check(en):
    """CI 게이트: JSON 유효성 + 원문에 없는 '유령 키' 검사, 커버리지 리포트."""
    keys = set(en.keys())
    problems = 0
    for lang in ["en"] + _lang_files():
        path = os.path.join(LOCALES, lang + ".json")
        try:
            data = _read_json(path)
        except Exception as e:
            print(f"❌ {lang}.json: JSON 파싱 실패 — {e}")
            problems += 1
            continue
        ghost = [k for k in data if k not in keys]
        nonstr = [k for k, v in data.items() if not isinstance(v, str)]
        translated = sum(1 for k in keys if isinstance(data.get(k), str) and data[k]
                         and (lang == "en" or data[k] != en[k]))
        pct = round(translated / len(keys) * 100) if keys else 0
        flag = ""
        if ghost:
            flag += f"  ⚠ 원문에 없는 키 {len(ghost)}개: {ghost[:3]}{'…' if len(ghost) > 3 else ''}"
            problems += 1
        if nonstr:
            flag += f"  ⚠ 문자열이 아닌 값 {len(nonstr)}개"
            problems += 1
        print(f"{lang}.json: 번역 {translated}/{len(keys)} ({pct}%){flag}")
    if problems:
        print(f"\n검사 실패 — 문제 {problems}건. (깨진 JSON 또는 원문에 없는 키)")
        return 1
    print("\n검사 통과 ✅")
    return 0


def main(argv):
    en = _load_baseline()
    if "--check" in argv:
        return check(en)
    if "--add" in argv:
        i = argv.index("--add")
        if i + 1 >= len(argv):
            print("사용: python tools/i18n_export.py --add <lang_code>")
            return 2
        return add_lang(en, argv[i + 1])
    sync(en)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
