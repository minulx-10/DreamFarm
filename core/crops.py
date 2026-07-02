"""작물 정의 — 작물마다 목표, 버튼 이름, 밭의 성질이 달라진다.

게임 로직은 FarmScene 하나를 공유하고, 이 설정값이 차이를 만든다:
- labels        : 행동 버튼에 보이는 이름 (내부 행동 키는 공통)
- moist_lo/hi   : '평온한 밭'으로 치는 수분 구간 (벼는 물이 흥건해야 산다)
- drain_mult    : 턴마다 수분이 마르는 속도 배율
- pressure_mult : 잡초·해충이 불어나는 속도 배율
- water_mult    : 물 주기 효과 배율
- fragile       : 건강이 깎이는 피해 배율 (나무는 튼튼, 어린 벼는 여림)
"""

from core.game_state import game_state

CROPS = {
    "carrot": {
        "name": "당근",
        "family": "뿌리채소",
        "desc": "아버지의 밭, 그 처음. 균형 잡힌 기본 작물.",
        "food": "당근",
        "growth_goal": 20,
        "labels": {},
        "moist_lo": 30, "moist_hi": 72,
        "drain_mult": 1.0, "pressure_mult": 1.0,
        "water_mult": 1.0, "fragile": 1.0,
        "tint": None,
    },
    "apple": {
        "name": "사과나무",
        "family": "나무류",
        "desc": "더디지만 단단하다. 가지를 치고, 오래 기다려야 한다.",
        "food": "사과",
        "growth_goal": 26,
        "labels": {"잡초 뽑기": "가지치기", "흙 북돋기": "거름 주기"},
        "moist_lo": 26, "moist_hi": 68,
        "drain_mult": 0.8, "pressure_mult": 0.9,
        "water_mult": 1.0, "fragile": 0.75,
        "tint": (200, 60, 50),
    },
    "potato": {
        "name": "감자",
        "family": "구황작물",
        "desc": "메마른 해에도 사람을 살리던 작물. 거칠어도 잘 버틴다.",
        "food": "감자",
        "growth_goal": 18,
        "labels": {"해충 살피기": "굼벵이 잡기"},
        "moist_lo": 24, "moist_hi": 66,
        "drain_mult": 0.9, "pressure_mult": 1.25,
        "water_mult": 1.0, "fragile": 0.85,
        "tint": (205, 170, 90),
    },
    "rice": {
        "name": "벼",
        "family": "벼",
        "desc": "물 위에서 자라는 한 해의 주식. 물꼬 관리가 전부다.",
        "food": "쌀밥",
        "growth_goal": 22,
        "labels": {"물 주기": "물 대기", "배수로 정리": "물꼬 트기"},
        "moist_lo": 50, "moist_hi": 86,
        "drain_mult": 1.5, "pressure_mult": 1.0,
        "water_mult": 1.35, "fragile": 1.15,
        "tint": (215, 200, 110),
    },
}


def current_crop():
    return CROPS.get(game_state.crop, CROPS["carrot"])


# ── 조사(을/를 등)까지 맞춰 작물 이름을 갈아 끼우는 헬퍼 ──

_JOSA_PAIRS = [("을", "를"), ("이", "가"), ("은", "는"), ("과", "와")]


def _has_batchim(word):
    ch = word[-1]
    return ord("가") <= ord(ch) <= ord("힣") and (ord(ch) - ord("가")) % 28 > 0


def swap_crop_word(text, word):
    """본문 속 '당근'을 지금 작물 이름으로 바꾸되, 뒤따르는 조사도 맞춘다."""
    if word == "당근":
        return text
    out = []
    i = 0
    while i < len(text):
        if text.startswith("당근", i):
            out.append(word)
            i += 2
            if i < len(text):
                nxt = text[i]
                for with_b, without_b in _JOSA_PAIRS:
                    if nxt in (with_b, without_b):
                        out.append(with_b if _has_batchim(word) else without_b)
                        i += 1
                        break
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


# ── 악)몽중농원 — 진엔딩 해금 모드 ──

NIGHTMARE_INTRO = (
    "여느 밤과 같은 꿈인 줄 알았다.\n\n"
    "그런데 하늘이 검붉다. 흙에서 탄내가 난다.\n"
    "밭 한가운데, 낯익은 접시들이 쌓여 있다 —\n"
    "여태 내가 남긴 음식들이다.\n\n"
    "어디선가 낮은 목소리가 울린다.\n"
    "'남긴 것은 여기서 다 먹어야 한다.\n"
    "먹으려면, 다시 길러야지.'\n\n"
    "이 검붉은 밭에서 작물을 끝까지 길러 수확해야\n"
    "꿈에서 깨어날 수 있다."
)

# 악몽 밭 배율 — 모든 것이 더 빨리 마르고, 더 빨리 들끓는다.
NIGHTMARE_MODS = {
    "drain_mult": 1.35,
    "pressure_mult": 1.35,
    "fragile": 1.2,
}


def apply_nightmare(cfg):
    """작물 설정에 악몽 배율을 얹은 사본을 돌려준다."""
    out = dict(cfg)
    for key, mult in NIGHTMARE_MODS.items():
        out[key] = cfg[key] * mult
    return out


def farm_config():
    """지금 회차(작물 + 악몽 여부)에 맞는 최종 밭 설정."""
    cfg = current_crop()
    if game_state.nightmare:
        cfg = apply_nightmare(cfg)
    return cfg
