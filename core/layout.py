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
# 캔버스 폭/높이 상한 — 극단적 울트라와이드/세로에서 여백이 과하게 늘어나는 걸 막는다.
# (상한을 넘는 비율은 약간의 레터박스가 다시 생기지만, 그 안은 배경으로 꽉 찬다.)
MAX_W, MAX_H = 1280, 960

canvas_w, canvas_h = SAFE_W, SAFE_H
safe_x, safe_y = 0, 0


def set_viewport(win_w, win_h):
    """실제 창 비율에 맞춰 캔버스 크기와 안전영역 오프셋을 정한다."""
    global canvas_w, canvas_h, safe_x, safe_y
    if win_w <= 0 or win_h <= 0:
        return
    aspect = win_w / win_h
    if aspect >= SAFE_W / SAFE_H:          # 4:3보다 넓음 → 좌우로 확장
        canvas_h = SAFE_H
        canvas_w = max(SAFE_W, min(MAX_W, round(SAFE_H * aspect)))
    else:                                  # 4:3보다 김(세로) → 상하로 확장
        canvas_w = SAFE_W
        canvas_h = max(SAFE_H, min(MAX_H, round(SAFE_W / aspect)))
    safe_x = (canvas_w - SAFE_W) // 2
    safe_y = (canvas_h - SAFE_H) // 2


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
    for rr in (1, 2, 3):                     # 빛 스프라이트 1회 생성(기준 밝기 150) → blit 시 set_alpha 로 조절
        glow = pygame.Surface((rr * 6, rr * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 238, 188, 50), (rr * 3, rr * 3), rr * 3)
        pygame.draw.circle(glow, (255, 246, 212, 150), (rr * 3, rr * 3), rr)
        _MOTE_GLOW[rr] = glow


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
    """안전영역(서브서피스) 밖 여백을 '자연스럽게' 채운다.
    스트레치로 연속성만 잡은 뒤 (1) 소프트 블러로 뭉개짐을 지우고 (2) 어두운 씬은 꿈-어둠으로
    페이드 + 떠다니는 빛, 밝은 씬(밭 등)은 부드러운 자연 연장만 남긴다(밝기 자동 감지).
    배경 직후(UI 전)에 호출. 4:3(여백 0)이면 무동작.
    (core.ui.draw_story_backdrop·core.assets.draw_tiled_background 끝에서 호출)"""
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

    # 좌/우 여백 — 가장자리 한 열을 늘려 base 연속성 확보
    sides = []
    if ox > 0:
        col = screen.subsurface((0, 0, 1, sh)).copy()
        parent.blit(pygame.transform.scale(col, (ox, sh)), (0, oy))
        sides.append((0, ox, True))
    rw = pw - (ox + sw)
    if rw > 0:
        col = screen.subsurface((sw - 1, 0, 1, sh)).copy()
        parent.blit(pygame.transform.scale(col, (rw, sh)), (ox + sw, oy))
        sides.append((ox + sw, rw, False))

    for (mx0, mw, is_left) in sides:
        region = parent.subsurface((mx0, oy, mw, sh)).copy()
        lum = _avg_lum(region)
        parent.blit(_blur(region, 11), (mx0, oy))       # (1) 소프트 블러 → 뭉개짐 제거
        # 어두운 씬일수록 바깥으로 강하게 어두워짐(밝은 밭은 거의 유지). lum<15→1, lum>70→0
        darkness = max(0.0, min(1.0, (70.0 - lum) / 55.0))
        if darkness > 0.03:                             # (2) 꿈-어둠 그라데이션
            grad = pygame.Surface((mw, sh), pygame.SRCALPHA)
            amax = int(210 * darkness)
            for xi in range(0, mw, 2):
                t = (1 - xi / mw) if is_left else (xi / mw)
                grad.fill((9, 8, 26, int(amax * (t ** 1.5))), (xi, 0, 2, sh))
            parent.blit(grad, (mx0, oy))
        mote_scale = 0.12 + 0.88 * darkness             # (3) 떠다니는 빛(어두운 씬에서 뚜렷)
        for m in _MOTES:
            if m["side"] != (0 if is_left else 1):
                continue
            px = mx0 + m["fx"] * mw + math.sin(_time * m["speed"] + m["phase"]) * m["amp"]
            py = oy + m["fy"] * sh + math.cos(_time * m["speed"] * 0.7 + m["phase"]) * m["amp"] * 0.6
            if not (mx0 <= px < mx0 + mw):
                continue
            a = int(150 * m["bright"] * mote_scale)
            if a < 8:
                continue
            rr = m["size"]
            glow = _MOTE_GLOW[rr]
            glow.set_alpha(int(255 * a / 150))        # 캐시된 스프라이트를 밝기만 조절해 재사용
            parent.blit(glow, (int(px - rr * 3), int(py - rr * 3)))

    # 상/하 여백(세로 화면) — 행을 늘리고 부드럽게 블러
    if oy > 0:
        row = parent.subsurface((0, oy, pw, 1)).copy()
        parent.blit(pygame.transform.scale(row, (pw, oy)), (0, 0))
        parent.blit(_blur(parent.subsurface((0, 0, pw, oy)).copy(), 9), (0, 0))
    bh = ph - (oy + sh)
    if bh > 0:
        row = parent.subsurface((0, oy + sh - 1, pw, 1)).copy()
        parent.blit(pygame.transform.scale(row, (pw, bh)), (0, oy + sh))
        parent.blit(_blur(parent.subsurface((0, oy + sh, pw, bh)).copy(), 9), (0, oy + sh))
