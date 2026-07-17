# -*- coding: utf-8 -*-
"""픽셀 톤 드로잉 프리미티브 (곡선 없음).

큰-픽셀 미학에서는 매끈한 둥근 모서리(border_radius)와 안티에일리어싱된 원이 도드라진다.
이 모듈은 그 대체품을 제공한다:
  - pixel_rect : 모서리를 '계단식 픽셀 챔퍼'로 깎은 사각형(둥근 곡선 대신)
  - pixel_disc : 저해상도 원을 최근접 확대해 '큰 픽셀 블록'으로 계단화한 원

core.ui / core.assets 양쪽에서 import 한다(순환참조 방지를 위해 별도 모듈로 분리).
의존성은 pygame 뿐 — palette/game_state 등을 import 하지 않는다.
"""
import pygame

CHAMFER = 6           # 모서리를 대각선으로 깎는 크기(px). 픽셀 스텝으로 계단화됨.
CHAMFER_STEP = 3      # 계단 한 칸의 크기(px) — 6px 챔퍼 = 3px 스텝 2칸
CHAMFER_LG = 6        # 큰 모달도 동일 톤(과한 곡선 방지)
CHAMFER_SM = 3        # 작은 요소(미터바 등)


def _fill_chamfer(surface, color, rect, chamfer, step):
    """모서리를 계단식으로 깎은 사각형을 '채운다'. border_radius(둥근 곡선)의 픽셀 대체.
    surface.fill 은 SRCALPHA 서피스에서도 알파를 '덮어써서' 투명 클리어에도 쓸 수 있다."""
    rect = pygame.Rect(rect)
    c = min(chamfer, rect.w // 2, rect.h // 2)
    c = (c // step) * step                       # step 배수로 계단화
    if c <= 0:
        surface.fill(color, rect)
        return
    surface.fill(color, (rect.x, rect.y + c, rect.w, rect.h - 2 * c))   # 가운데 큰 블록
    y = 0
    while y < c:
        inset = c - (y // step) * step           # 가장자리→안쪽 계단
        h = min(step, c - y)
        w = rect.w - 2 * inset
        if w > 0:
            surface.fill(color, (rect.x + inset, rect.y + y, w, h))              # 위
            surface.fill(color, (rect.x + inset, rect.bottom - y - h, w, h))     # 아래
        y += h


def pixel_rect(surface, color, rect, width=0, chamfer=None, step=CHAMFER_STEP):
    """둥근 모서리(border_radius) 대신 '계단식 픽셀 챔퍼' 사각형을 그린다.
    width=0 이면 채움, width>0 이면 그 두께의 테두리(속을 투명 클리어한 링)."""
    rect = pygame.Rect(rect)
    ch = CHAMFER if chamfer is None else chamfer
    ch = min(ch, CHAMFER)                         # 과한 곡선(옛 radius=12/15)도 일관된 6px로 클램프
    if width <= 0:
        _fill_chamfer(surface, color, rect, ch, step)
        return
    tmp = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    _fill_chamfer(tmp, color, pygame.Rect(0, 0, rect.w, rect.h), ch, step)
    inner = pygame.Rect(width, width, rect.w - 2 * width, rect.h - 2 * width)
    if inner.w > 0 and inner.h > 0:
        _fill_chamfer(tmp, (0, 0, 0, 0), inner, max(0, ch - width), step)
    surface.blit(tmp, rect.topleft)


GLOW_PX = 5           # 글로우/그라데이션을 계단화할 '큰 픽셀' 블록 크기(가상 800x600 기준)


def pixelate(surf, block=GLOW_PX, smooth=True):
    """서피스를 block px 격자의 '큰 픽셀'로 스냅한다.

    smooth=True  : 평균 축소(smoothscale) 후 최근접 확대 — 연속 그라데이션 밴드용.
    smooth=False : 최근접 서브샘플(scale) 후 최근접 확대 — 선화/균일 알파 오브젝트용.
                   평균 축소는 경계색이 섞여 '모자이크 검열'처럼 뿌옇게 보인다 →
                   또렷한 도트가 필요한 아트는 반드시 이쪽을 쓴다."""
    w, h = surf.get_size()
    if block <= 1 or w < block or h < block:
        return surf
    scaler = pygame.transform.smoothscale if smooth else pygame.transform.scale
    small = scaler(surf, (max(1, w // block), max(1, h // block)))
    return pygame.transform.scale(small, (w, h))


# ─── 계단 알파 글로우 스프라이트 ─────────────────────────────────────────────
# 연속 falloff(원 수십 개)를 평균 축소하면 블록마다 알파가 미묘하게 달라 '모자이크 블러'로
# 보인다. 대신 뚜렷한 2~3단 알파 링으로 그린 도트 글로우를 캐시해 쓴다(매 프레임 재생성 방지).
_GLOW_CACHE = {}


def glow_sprite(radius, color, px=GLOW_PX, steps=(45, 95, 160), core=None):
    """반경 radius 의 '계단 알파' 도트 글로우 스프라이트(캐시).

    steps: 바깥→안 순서의 알파 단계(각 단계가 동심 링 하나). core=((r,g,b), alpha) 면
    중심 35% 반경에 더 밝은 심을 얹는다. 밝기 조절은 blit 직전 set_alpha(0~255)로.
    radius 는 int 로 캐시 키가 되므로, 맥동하는 글로우는 radius 를 몇 px 단위로
    양자화해 넘기면 캐시가 무한히 늘지 않는다(계단 맥동은 픽셀 톤과도 어울림)."""
    radius = max(2, int(radius))
    key = (radius, tuple(color[:3]), px, tuple(steps), core)
    got = _GLOW_CACHE.get(key)
    if got is not None:
        return got
    rr = max(2, round(radius / px))
    size = rr * 2 + 1
    small = pygame.Surface((size, size), pygame.SRCALPHA)
    n = len(steps)
    for i, a in enumerate(steps):          # 바깥 링부터 — 안쪽 원이 알파를 '덮어써' 단이 진다
        ri = max(1, round(rr * (n - i) / n))
        pygame.draw.circle(small, (color[0], color[1], color[2], a), (rr, rr), ri)
    if core:
        (cr, cg, cb), ca = core
        pygame.draw.circle(small, (cr, cg, cb, ca), (rr, rr), max(1, round(rr * 0.35)))
    big = pygame.transform.scale(small, (size * px, size * px))
    _GLOW_CACHE[key] = big
    return big


def blit_glow(surface, sprite, center, alpha=255):
    """글로우 스프라이트를 중심 좌표 기준으로 blit (set_alpha 로 밝기 조절)."""
    sprite.set_alpha(alpha)
    surface.blit(sprite, (int(center[0]) - sprite.get_width() // 2,
                          int(center[1]) - sprite.get_height() // 2))


def pixel_disc(surface, color, center, radius, px=None, width=0):
    """매끈한 원(pygame.draw.circle) 대신 '큰 픽셀 블록'으로 계단화된 원을 그린다.
    저해상도 원을 그린 뒤 최근접(nearest)으로 px배 확대 → 도트 원. 달·해·메달 등 또렷한 원에 사용.
    (먼 배경의 부드러운 헤일로/블룸은 이걸 쓰지 말고 그대로 소프트하게 둔다 = 분위기 블러 유지.)"""
    cx, cy = int(center[0]), int(center[1])
    radius = int(radius)
    if px is None:
        px = 3 if radius >= 12 else 2
    if radius < px * 2:
        pygame.draw.circle(surface, color, (cx, cy), radius, width)
        return
    rr = max(2, round(radius / px))
    size = rr * 2 + 1
    small = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(small, color, (rr, rr), rr, max(0, round(width / px)) if width else 0)
    big = pygame.transform.scale(small, (size * px, size * px))
    surface.blit(big, (cx - size * px // 2, cy - size * px // 2))
