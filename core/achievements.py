"""업적(도전과제) — 마인크래프트 도전과제 느낌의 잠금 해제식 업적.

save 메타(save_system)에 해제 목록을 남기고, 해제되는 순간 화면 맨 위에
토스트로 슬쩍 알린다. 메인 루프가 매 프레임 update()/draw()를 불러 준다.
"""

import pygame

from core.assets import get_font, WHITE, TEXT_DARK, TEXT_MUTED
from core.pixelfx import pixel_rect, CHAMFER
from core import audio, save_system
from core import i18n


# 등급(브론즈/실버/골드/플래티넘)별 메달 색과 이름
TIER_COLORS = {
    "bronze": (196, 130, 78),
    "silver": (192, 198, 208),
    "gold": (232, 194, 92),
    "platinum": (150, 220, 224),
}
TIER_LABELS = {
    "bronze": "브론즈",
    "silver": "실버",
    "gold": "골드",
    "platinum": "플래티넘",
}
TIER_ORDER = ["bronze", "silver", "gold", "platinum"]

ACHIEVEMENTS = [
    {"id": "first_harvest", "title": "첫 결실", "desc": "작물을 처음 끝까지 길러 냈다.", "tier": "bronze"},
    {"id": "grow_carrot", "title": "흙을 아는 손", "desc": "당근을 수확했다.", "tier": "bronze"},
    {"id": "grow_potato", "title": "메마른 해의 버팀목", "desc": "감자를 캐냈다.", "tier": "bronze"},
    {"id": "grow_rice", "title": "물꼬를 쥔 농부", "desc": "벼를 길러 쌀을 얻었다.", "tier": "silver"},
    {"id": "grow_apple", "title": "오래 기다린 자", "desc": "사과나무를 끝까지 길러 열매를 땄다.", "tier": "silver"},
    {"id": "perfect_harvest", "title": "완벽주의자", "desc": "실수 없이 완벽하게만 수확했다.", "tier": "silver"},
    {"id": "veteran", "title": "열 번의 결실", "desc": "작물을 통틀어 열 번 길러 거두었다.", "tier": "gold"},
    {"id": "all_crops", "title": "사대(四大)를 아우르다", "desc": "네 작물을 모두 수확했다.", "tier": "gold"},
    {"id": "true_ending", "title": "마주 앉은 아침", "desc": "진엔딩에 이르렀다.", "tier": "gold"},
    {"id": "nightmare_clear", "title": "악몽에서 깨어나", "desc": "악)몽중농원을 끝까지 버텨 수확했다.", "tier": "platinum"},

    # 히든 업적 (hidden: True)
    {"id": "hundred_clears", "title": "백전노장", "desc": "작물을 통틀어 백 번 길러 거두었다.", "tier": "platinum", "hidden": True},
    {"id": "nightmare_ending", "title": "붉은 새벽을 걷다", "desc": "악)몽중농원 전용 엔딩을 마주했다.", "tier": "platinum", "hidden": True},
    {"id": "developer_secret", "title": "창조주의 악수", "desc": "개발자의 이름을 기입하여 경의를 표했다.", "tier": "platinum", "hidden": True},
]

_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}

# 화면에 띄울 토스트 대기열 (각 항목: {"a": 업적, "t": 경과시간})
_toasts = []
_TOAST_DUR = 4.2


def unlock(aid):
    """업적을 처음 해제할 때만 기록하고 토스트를 띄운다."""
    ach = _BY_ID.get(aid)
    if not ach:
        return
    if save_system.is_achievement_unlocked(aid):
        return
    save_system.record_achievement(aid)
    _toasts.append({"a": ach, "t": 0.0})
    # 스팀 도전과제도 함께 해제 (스팀 연동이 없으면 무해한 no-op).
    try:
        from core import steam
        steam.unlock_achievement(aid)
    except Exception:
        pass
    try:
        audio.play("epiphany")
    except Exception:
        pass


# ------------------------------------------------------------------ 트리거
_CROP_ACH = {"carrot": "grow_carrot", "apple": "grow_apple",
             "potato": "grow_potato", "rice": "grow_rice"}


def on_harvest(crop, perfects, attempts):
    """작물 수확을 마쳤을 때 (수확 성공 시에만) 호출."""
    from core.game_state import game_state
    unlock("first_harvest")
    unlock(_CROP_ACH.get(crop, ""))
    clears = save_system.crop_clears()
    if all(clears.get(c, 0) > 0 for c in ("carrot", "apple", "potato", "rice")):
        unlock("all_crops")
    
    total_clears = sum(clears.values())
    if total_clears >= 10:
        unlock("veteran")
    if total_clears >= 100:
        unlock("hundred_clears")
        
    if perfects > 0 and attempts <= perfects:
        unlock("perfect_harvest")
    if getattr(game_state, "nightmare", False):
        unlock("nightmare_clear")


def on_ending(ending_type):
    """엔딩에 도달했을 때 (갤러리 감상이 아닌 실제 플레이에서만) 호출."""
    if ending_type == "true":
        unlock("true_ending")
    elif ending_type == "nightmare":
        unlock("nightmare_ending")


# 개발자 이름 이스터에그
_DEV_NAMES = {"서태양", "김민욱", "박서현"}


def on_name(name):
    """플레이어 이름이 개발자 이름이면 히든 업적 해제 및 환영 토스트를 띄운다."""
    if name in _DEV_NAMES:
        # 히든 업적 잠금해제 처리
        unlock("developer_secret")
        # 추가 인사 토스트를 대기열에 삽입
        _toasts.append({"a": {"title": i18n.tf("개발자 {name}, 등장!", name=name), "tier": "legend"}, "t": 0.0})
        try:
            audio.play("epiphany")
        except Exception:
            pass


# ------------------------------------------------------------------ 토스트
def update(dt):
    for t in _toasts:
        t["t"] += dt
    while _toasts and _toasts[0]["t"] > _TOAST_DUR:
        _toasts.pop(0)


def _draw_medal(screen, cx, cy, tier, r=17):
    """등급 메달 — 절반 해상도로 그린 뒤 최근접 2배 확대해 '도트' 느낌을 준다(등급색 유지,
    날씨·톱니 등 픽셀 아이콘과 톤 통일)."""
    import math
    col = TIER_COLORS.get(tier, (176, 168, 150))
    px = 2
    rr = max(3, r // px)
    pad = 2
    surf = pygame.Surface(((rr + pad) * 2, (rr + pad) * 2 + 1), pygame.SRCALPHA)
    scx, scy = surf.get_width() // 2, rr + pad
    pygame.draw.circle(surf, (30, 26, 22, 255), (scx, scy + 1), rr + 1)   # 그림자
    pygame.draw.circle(surf, col, (scx, scy), rr)                          # 원판
    pygame.draw.circle(surf, WHITE, (scx, scy), rr, 1)                     # 테두리
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = rr * 0.6 if i % 2 == 0 else rr * 0.26
        pts.append((scx + rad * math.cos(ang), scy + rad * math.sin(ang)))
    pygame.draw.polygon(surf, (255, 244, 214), pts)                        # 가운데 별
    scaled = pygame.transform.scale(surf, (surf.get_width() * px, surf.get_height() * px))
    screen.blit(scaled, (cx - scaled.get_width() // 2, cy - (rr + pad) * px))


def draw(screen):
    """맨 위에서 살짝 내려왔다 올라가는 업적 토스트 (한 번에 하나)."""
    if not _toasts:
        return
    t = _toasts[0]
    a = t["a"]
    elapsed = t["t"]

    W, H = 344, 60
    x = (800 - W) // 2
    rest_y = 12
    if elapsed < 0.35:
        k = elapsed / 0.35
        y = -H + (rest_y + H) * (1 - (1 - k) * (1 - k))   # ease-out
    elif elapsed > _TOAST_DUR - 0.4:
        k = max(0.0, (_TOAST_DUR - elapsed) / 0.4)
        y = -H + (rest_y + H) * k
    else:
        y = rest_y

    y = int(y)
    panel = pygame.Surface((W, H), pygame.SRCALPHA)
    pixel_rect(panel, (40, 34, 28, 236), (0, 0, W, H), chamfer=CHAMFER)
    tier_col = TIER_COLORS.get(a.get("tier"), (176, 168, 150))
    pixel_rect(panel, (*tier_col, 255), (0, 0, W, H), width=2, chamfer=CHAMFER)
    screen.blit(panel, (x, y))

    _draw_medal(screen, x + 32, y + H // 2, a.get("tier"))

    head = get_font(12).render("업적 달성!", True, (240, 206, 120))
    screen.blit(head, (x + 60, y + 9))
    title = get_font(17).render(a["title"], True, WHITE)
    screen.blit(title, (x + 60, y + 27))


def has_any_hidden_unlocked():
    """히든 업적 중 하나라도 해제되었는지 여부 확인."""
    unlocked = set(save_system.achievements_unlocked())
    hidden_ids = {"hundred_clears", "nightmare_ending", "developer_secret"}
    return any(hid in unlocked for hid in hidden_ids)


def all_with_state():
    """갤러리 표시용 — 일반 업적 (업적, 해제여부) 목록."""
    unlocked = set(save_system.achievements_unlocked())
    return [(a, a["id"] in unlocked) for a in ACHIEVEMENTS if not a.get("hidden")]


def hidden_with_state():
    """갤러리 표시용 — 히든 업적 (업적, 해제여부) 목록."""
    unlocked = set(save_system.achievements_unlocked())
    return [(a, a["id"] in unlocked) for a in ACHIEVEMENTS if a.get("hidden")]
