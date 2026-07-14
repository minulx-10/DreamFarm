"""언어(로케일) 전환 — 한국어(기본) ↔ 영어(+향후 언어). 스팀 글로벌 출시 대비 현지화 기반.

번역은 **원문(한국어) → 대상 언어 사전**이며, **렌더 계층에서 자동 적용**한다:
  - `get_font()`가 돌려주는 폰트의 `render()`/`size()`가 문자열을 `t()`로 번역해서 그린다
    (호출부를 고치지 않아도 대부분의 라벨·짧은 문장이 자동 번역된다).
  - `wrap_text()`는 줄바꿈 '전에' 원문을 통째로 번역한다(긴 대사도 대상 언어 기준으로 줄바꿈).
  - 변수와 합쳐지는 **동적 문자열**은 `tf`/`tnar`로 처리한다.

**번역 소스:**
  1. `core/i18n_data.EN` — 파이썬 베이스라인(항상 임포트 가능, 번들 실패 위험 없음).
  2. `core/locales/<lang>.json` — 커뮤니티 번역 파일(GitHub PR로 기여). 있으면 베이스라인 위에 덮어써
     번역을 갱신·확장한다(en 외 언어는 이 JSON만으로 추가된다). `tools/i18n_export.py`·`LOCALIZATION.md` 참고.

로직 키(요일·작물·기억 제목 등)는 저장·비교에 원문 그대로 쓰이고 '표시'만 번역되므로,
**세이브 호환성과 게임 로직은 영향받지 않는다.** 번역이 없는 문자열은 한국어 원문으로 표시(폴백).
"""

import os
import json

_LANGS = ("ko", "en")           # 지원 UI 토글 언어(현재). locales/<lang>.json만 추가하면 확장 가능.
_lang = "ko"
_catalogs = {}                  # lang -> {원문(ko): 번역} (지연 적재·캐시)


def _load_lang(lang):
    """대상 언어 카탈로그를 만든다: 파이썬 베이스라인 + locales/<lang>.json(있으면 덮어씀)."""
    if lang in _catalogs:
        return _catalogs[lang]
    cat = {}
    # 1) 파이썬 베이스라인 (현재는 영어만 코드에 내장)
    if lang == "en":
        try:
            from core import i18n_data
            cat.update(getattr(i18n_data, "EN", {}) or {})
        except Exception:
            pass
    # 2) 커뮤니티 번역 JSON (core/locales/<lang>.json) — 있으면 우선
    try:
        from core.assets import resource_path
        p = resource_path(os.path.join("locales", lang + ".json"))
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cat.update({k: v for k, v in data.items() if isinstance(v, str) and v})
    except Exception:
        pass
    _catalogs[lang] = cat
    return cat


def _target_catalog():
    """번역 조회용 카탈로그 — ko 모드에선 커버리지 확인용으로 en을 본다."""
    return _load_lang("en" if _lang == "ko" else _lang)


def set_language(lang):
    global _lang
    if lang in _LANGS:
        _lang = lang


def get_language():
    return _lang


def toggle():
    set_language("en" if _lang == "ko" else "ko")
    return _lang


def init(lang=None):
    """카탈로그를 적재하고 초기 언어를 세팅한다 (게임 시작 시 1회)."""
    _load_lang("en")
    if lang in _LANGS:
        set_language(lang)


def t(s):
    """원문 문자열을 현재 언어로 번역. 번역이 있으면 대상 언어, 없으면 원문 그대로(폴백)."""
    if _lang == "ko" or not isinstance(s, str) or not s:
        return s
    cat = _load_lang(_lang)
    hit = cat.get(s)
    if hit is not None:
        return hit
    # 렌더 문자열에 앞뒤 공백이 붙는 경우를 위한 보정 (예: " 시작 ")
    stripped = s.strip()
    if stripped is not s:
        hit = cat.get(stripped)
        if hit is not None:
            # 원문의 앞뒤 공백을 보존해 배치가 흐트러지지 않게 한다
            lead = s[:len(s) - len(s.lstrip())]
            trail = s[len(s.rstrip()):]
            return lead + hit + trail
    return s


def tf(template, **kwargs):
    """동적 문자열용 — 템플릿(원문)을 먼저 번역한 뒤 변수to 채운다.

    예) i18n.tf("물 뿌리기: {n}회", n=count)
      - ko 모드: "물 뿌리기: {n}회".format(n=count)
      - en 모드: 카탈로그의 "물 뿌리기: {n}회" → "Watered {n}×" 를 format
    번역 카탈로그에는 **중괄호 자리표시자를 포함한 원문 템플릿**을 키로 넣어야 한다.
    번역이 없으면 원문 템플릿을 그대로 format 한다(폴백)."""
    tmpl = t(template)
    try:
        return tmpl.format(**kwargs)
    except Exception:
        # 자리표시자 불일치 등으로 실패하면 원문 템플릿으로 안전 폴백
        try:
            return template.format(**kwargs)
        except Exception:
            return template


# 서사(내러티브)용 — 작물 키(carrot/apple/potato/rice)별 영어 단어. EN 템플릿의 {crop}/{food}/{field}를 채운다.
_EN_CROP = {
    "carrot": {"crop": "carrot", "food": "carrot", "field": "field", "utensil": "chopsticks"},
    "apple":  {"crop": "apple", "food": "apple", "field": "orchard", "utensil": "a fork"},
    "potato": {"crop": "potato", "food": "potato", "field": "field", "utensil": "chopsticks"},
    "rice":   {"crop": "rice", "food": "rice", "field": "paddy", "utensil": "a spoon"},
}


def tnar(ko_template, crop_key=None, **kw):
    """서사 문자열 번역 — 이름 조사(name_eun 등)와 작물 치환을 언어별로 처리.

    - KO: 템플릿을 format(조사 자리표시자 채움)한 뒤 `swap_crop_word`로 '당근'을 현재 작물로 치환.
    - EN: 카탈로그의 영어 템플릿을 가져와 {name}/{crop}/{food}/{field} 등 자리표시자를 채운다
      (작물 영어 단어는 crop_key로 자동 주입). 번역이 없으면 KO 경로로 폴백.

    호출부는 KO 원문 템플릿을 그대로 키로 넘긴다. KO 템플릿엔 `{name_eun}` 등 조사 자리표시자와
    '당근' 리터럴을, EN 템플릿엔 `{name}`·`{crop}` 등 영어 자리표시자를 쓴다(서로 달라도 무방)."""
    if _lang == "en":
        s = t(ko_template)
        if s == ko_template and not has(ko_template):
            # 번역 없음 → KO 경로로 폴백(최소한 작물/조사는 맞춘다)
            return _tnar_ko(ko_template, crop_key, kw)
        inj = dict(_EN_CROP.get(crop_key, _EN_CROP["carrot"])) if crop_key else {}
        inj.update(kw)
        try:
            return s.format(**inj)
        except Exception:
            return s
    return _tnar_ko(ko_template, crop_key, kw)


def _tnar_ko(ko_template, crop_key, kw):
    try:
        s = ko_template.format(**kw)
    except Exception:
        s = ko_template
    if crop_key:
        try:
            from core.crops import CROPS, swap_crop_word
            ko_word = CROPS.get(crop_key, CROPS["carrot"])["name"]
            s = swap_crop_word(s, ko_word)
        except Exception:
            pass
    return s


def has(s):
    """번역이 존재하는지 (테스트/커버리지 확인용)."""
    cat = _target_catalog()
    return isinstance(s, str) and (s in cat or s.strip() in cat)
