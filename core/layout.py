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


def bleed_edges(screen):
    """안전영역(서브서피스) 밖 여백을 가장자리 배경의 세로/가로 연장으로 채운다.
    배경을 그린 '직후'(UI 그리기 전)에 호출해야 UI가 아니라 배경만 늘어난다. 4:3(여백 0)이면 무동작.
    (core.ui.draw_story_backdrop·core.assets.draw_tiled_background 끝에서 호출)"""
    import pygame
    parent = screen.get_parent()
    if not parent:
        return
    ox, oy = screen.get_offset()
    pw, ph = parent.get_size()
    sw, sh = screen.get_size()
    if ox > 0:                                   # 왼쪽 여백 — 안전영역 왼쪽 한 열을 늘림
        col = screen.subsurface((0, 0, 1, sh)).copy()
        parent.blit(pygame.transform.scale(col, (ox, sh)), (0, oy))
    rw = pw - (ox + sw)
    if rw > 0:                                   # 오른쪽 여백
        col = screen.subsurface((sw - 1, 0, 1, sh)).copy()
        parent.blit(pygame.transform.scale(col, (rw, sh)), (ox + sw, oy))
    if oy > 0:                                   # 위 여백 — (좌우 채운 뒤) 전체 폭 한 행을 늘림
        row = parent.subsurface((0, oy, pw, 1)).copy()
        parent.blit(pygame.transform.scale(row, (pw, oy)), (0, 0))
    bh = ph - (oy + sh)
    if bh > 0:                                   # 아래 여백
        row = parent.subsurface((0, oy + sh - 1, pw, 1)).copy()
        parent.blit(pygame.transform.scale(row, (pw, bh)), (0, oy + sh))
