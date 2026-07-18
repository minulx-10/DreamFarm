# -*- coding: utf-8 -*-
"""적응형 캔버스 레이아웃.

게임은 800x600(4:3) '안전영역(safe area)'에 맞춰 구성돼 있다. 화면 비율이 4:3이 아니면,
안전영역을 그대로 두고 **캔버스를 화면 비율에 맞게 키워** 안전영역을 가운데 두고 남는 가장자리는
배경으로 채운다(레터박스 검은 여백 제거). 씬은 여전히 800x600 좌표로 그리며(안전영역 서브서피스에
그린다), 배경 함수가 가장자리 여백을 이어 그린다(core.ui.bleed_edges 참고).

- `set_viewport(win_w, win_h)` : 실제 창 크기에서 캔버스 크기·안전영역 오프셋을 계산한다.
- `canvas_w/canvas_h`          : 이번 프레임 캔버스 크기(안전영역 + 여백).
- `safe_x/safe_y`              : 캔버스 안에서 안전영역(800x600)의 좌상단 오프셋.
"""

SAFE_W, SAFE_H = 800, 600
# 캔버스 폭/높이 상한 — 비정상적으로 길쭉한 창에서 캔버스가 무한정 커지는 것만 막는 안전판.
# 실기기 전부(32:9 5120x1440 → 2560, 폴더블 펼침 세로 1812x2176 → 1088)가 상한 안이라
# **어떤 화면에서도 레터박스 없이 꽉 찬다** — 정수 배율 스냅은 캔버스를 ceil(창/배율)로
# '오버스캔'해 채우므로(넘친 몇 px는 크롭), 상한이 이 오버스캔을 잘라먹지만 않으면 된다.
# (예전 1760x800 상한이 폴더블에서 212~576px 검은 띠의 원인이었다.)
MAX_W, MAX_H = 2600, 1500

canvas_w, canvas_h = SAFE_W, SAFE_H
safe_x, safe_y = 0, 0


def _place_safe():
    """안전영역은 항상 가운데 — 세로 확장 화면도 배경 연장 + 중앙 게임 블록(v2.2 방식)."""
    global safe_x, safe_y
    safe_x = (canvas_w - SAFE_W) // 2
    safe_y = max(0, canvas_h - SAFE_H) // 2


def set_viewport(win_w, win_h):
    """실제 창 비율에 맞춰 캔버스 크기와 안전영역 오프셋을 정한다."""
    global canvas_w, canvas_h
    if win_w <= 0 or win_h <= 0:
        return
    aspect = win_w / win_h
    if aspect >= SAFE_W / SAFE_H:          # 4:3보다 넓음 → 좌우로 확장
        canvas_h = SAFE_H
        canvas_w = max(SAFE_W, min(MAX_W, round(SAFE_H * aspect)))
    else:                                  # 4:3보다 김(세로) → 상하로 확장
        canvas_w = SAFE_W
        canvas_h = max(SAFE_H, min(MAX_H, round(SAFE_W / aspect)))
    _place_safe()


def set_canvas(cw, ch):
    """정수 배율 스냅용 — 캔버스 크기를 직접 지정하고 안전영역을 재배치한다.
    (game_main._apply_scaling 이 고해상도에서 정수배로 창을 꽉 채우려고 캔버스를 다시 키울 때 사용.)"""
    global canvas_w, canvas_h
    canvas_w, canvas_h = cw, ch
    _place_safe()


def safe_rect():
    import pygame
    return pygame.Rect(safe_x, safe_y, SAFE_W, SAFE_H)


def canvas_size():
    return (canvas_w, canvas_h)


# --- 여백(꿈) 연출용 상태 ---------------------------------------------------
_time = 0.0          # 떠다니는 빛 애니메이션용 시간(초). game_main 이 매 프레임 set_time 으로 갱신.
_MOTES = None        # 여백에 떠다니는 빛 입자 목록(1회 생성)
_MOTE_GLOW = {}      # size -> 미리 만든 빛 스프라이트(매 프레임 재생성 방지, 모바일 성능)


def set_time(t):
    global _time
    _time = t


def _init_motes():
    global _MOTES
    import pygame
    import random
    r = random.Random(20260714)
    _MOTES = []
    for i in range(30):
        _MOTES.append({
            "fx": r.uniform(0.06, 0.94), "fy": r.uniform(0.04, 0.96),
            "size": r.choice([1, 1, 2, 2, 3]), "phase": r.uniform(0, 6.283),
            "speed": r.uniform(0.12, 0.5), "amp": r.uniform(6, 22),
            "bright": r.uniform(0.4, 1.0), "side": i % 2,
        })
    from core.pixelfx import glow_sprite
    for rr in (1, 2, 3):                     # 빛 스프라이트 1회 생성(기준 밝기 150) → blit 시 set_alpha 로 조절
        # '계단 알파' 도트 글로우 — 평균축소 pixelate 는 모자이크 블러로 보였다
        _MOTE_GLOW[rr] = glow_sprite(rr * 3, (255, 238, 188), px=3,
                                     steps=(50,), core=((255, 246, 212), 150))


def _blur(surf, f):
    import pygame
    w, h = surf.get_size()
    if w < f or h < f:
        return surf
    small = pygame.transform.smoothscale(surf, (max(1, w // f), max(1, h // f)))
    return pygame.transform.smoothscale(small, (w, h))


def _avg_lum(surf):
    import pygame
    tiny = pygame.transform.smoothscale(surf, (4, 4))
    tot = 0.0
    for x in range(4):
        for y in range(4):
            r, g, b = tiny.get_at((x, y))[:3]
            tot += r * 0.299 + g * 0.587 + b * 0.114
    return tot / 16.0


def bleed_edges(screen):
    """여백 '깊이 마감'. 배경 함수(draw_story_backdrop·draw_tiled_background)가 이미 캔버스 전체 폭으로
    실제 배경(하늘·산·땅)을 이어 그리므로, 여기선 스미어/워시 없이 은은한 깊이감만 더한다:
    (1) 바깥 가장자리 비네트(초점) (2) 여백에 떠다니는 빛(어두운 씬). 4:3(여백 0)이면 무동작.
    배경 직후(UI 전)에 호출."""
    import pygame
    import math
    parent = screen.get_parent()
    if not parent:
        return
    if _MOTES is None:
        _init_motes()
    ox, oy = screen.get_offset()
    pw, ph = parent.get_size()
    sw, sh = screen.get_size()
    if ox <= 0 and oy <= 0:
        return
    safe = pygame.Rect(ox, oy, sw, sh)
    # 씬 밝기 감지 → 어두운 씬일수록 비네트·빛을 강하게(밝은 밭은 은은하게)
    d = max(0.0, min(1.0, (78.0 - _avg_lum(screen)) / 60.0))
    vig = 0.16 + 0.52 * d

    # (1) 바깥 가장자리 비네트 — 캔버스 끝으로 갈수록 살짝 어둑(초점). 블러 아님.
    if ox > 0:
        band = min(ox, 170)
        grad = pygame.Surface((band, ph), pygame.SRCALPHA)
        amax = int(210 * vig)
        for xi in range(0, band, 2):
            a = int(amax * ((1 - xi / band) ** 1.5))
            grad.fill((6, 6, 14, a), (xi, 0, 2, ph))
        parent.blit(grad, (0, 0))
        parent.blit(pygame.transform.flip(grad, True, False), (pw - band, 0))
    if oy > 0:
        band = min(oy, 150)
        grad = pygame.Surface((pw, band), pygame.SRCALPHA)
        amax = int(210 * vig)
        for yi in range(0, band, 2):
            a = int(amax * ((1 - yi / band) ** 1.5))
            grad.fill((6, 6, 14, a), (0, yi, pw, 2))
        parent.blit(grad, (0, 0))
        parent.blit(pygame.transform.flip(grad, False, True), (0, ph - band))

    # (2) 떠다니는 빛 — 여백 전체에 흩뿌리되 게임 화면(안전영역) 위에는 안 그림
    mote_scale = 0.12 + 0.88 * d
    if mote_scale < 0.06:
        return
    for m in _MOTES:
        mx = m["fx"] * pw + math.sin(_time * m["speed"] + m["phase"]) * m["amp"]
        my = m["fy"] * ph + math.cos(_time * m["speed"] * 0.7 + m["phase"]) * m["amp"] * 0.6
        if safe.collidepoint(mx, my):
            continue
        a = int(150 * m["bright"] * mote_scale)
        if a < 8:
            continue
        rr = m["size"]
        glow = _MOTE_GLOW[rr]
        glow.set_alpha(int(255 * a / 150))
        parent.blit(glow, (int(mx - rr * 3), int(my - rr * 3)))
