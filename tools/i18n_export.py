# -*- coding: utf-8 -*-
"""Crowdin 소스/번역 JSON 내보내기.

`core/i18n_data.EN`(파이썬 베이스라인)에서 두 파일을 만든다:
  - core/locales/ko.json : Crowdin **소스** 파일. {원문(한국어): 원문(한국어)}
                           (Crowdin이 값으로 보여줄 '번역할 문자열' = 한국어)
  - core/locales/en.json : 현재 영어 번역. {원문(한국어): 영어}

사용:  python tools/i18n_export.py

이후 흐름:
  1) `crowdin upload sources`  → ko.json 업로드 (한국어 원문이 소스)
  2) (선택) `crowdin upload translations -l en` → en.json 기존 번역 선반영
  3) 번역가가 Crowdin에서 en(및 향후 ja/zh 등) 번역
  4) `crowdin download`        → core/locales/en.json(및 <lang>.json) 갱신
  게임은 실행 시 core/locales/<lang>.json 을 자동으로 읽는다(코드 재생성 불필요).
"""
import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES = os.path.join(ROOT, "core", "locales")


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "i18n_data", os.path.join(ROOT, "core", "i18n_data.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    en = dict(getattr(mod, "EN", {}))

    os.makedirs(LOCALES, exist_ok=True)

    # 소스(ko): 키=값=한국어 원문. Crowdin이 이 값을 번역 대상으로 노출한다. (항상 전체 재생성)
    ko = {k: k for k in en.keys()}
    with open(os.path.join(LOCALES, "ko.json"), "w", encoding="utf-8") as f:
        json.dump(ko, f, ensure_ascii=False, indent=1, sort_keys=True)

    # en.json: Crowdin이 소유하는 파일이므로 **덮어쓰지 않고 병합**한다.
    #   - 기존 값(=Crowdin 번역)은 보존
    #   - i18n_data 에 새로 생긴 키만 베이스라인 영어로 추가
    #   - i18n_data 에서 사라진 키는 제거(소스와 동기화)
    en_path = os.path.join(LOCALES, "en.json")
    existing = {}
    if os.path.exists(en_path):
        try:
            with open(en_path, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}
    merged = {}
    added = 0
    for k, baseline in en.items():
        if k in existing and isinstance(existing[k], str) and existing[k]:
            merged[k] = existing[k]        # Crowdin 번역 보존
        else:
            merged[k] = baseline           # 새 키 → 베이스라인 영어
            added += 1
    removed = sum(1 for k in existing if k not in en)
    with open(en_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=1, sort_keys=True)
    print(f"ko.json: {len(ko)} source keys | en.json: {len(merged)} keys "
          f"({added} new/baseline, {removed} removed)")


if __name__ == "__main__":
    main()
