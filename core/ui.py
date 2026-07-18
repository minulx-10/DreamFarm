import math
import pygame
from core.assets import *
from core.game_state import game_state, get_understanding_stage
from core import audio


# ─────────────────────── 디자인 토큰 (UI 크롬 규칙 일원화, P4) ───────────────────────
# 패널·버튼·그림자·배경의 값을 여기 한곳에서 정한다. 개별 화면은 이 함수/토큰을 쓰면 자동 통일.
#
# [곡선 없음 규칙] 예전엔 border_radius(둥근 곡선)로 모서리를 부드럽게 했지만, 큰-픽셀 톤에서는
# 매끈한 곡선이 도드라진다. 이제 모서리는 '둥긂'이 아니라 계단식 픽셀 챔퍼(CHAMFER)로 처리한다.
# RADIUS 계열 상수는 하위호환용 별칭으로 남기되(값=챔퍼 크기), 실제 렌더는 pixel_rect가 담당한다.
# 픽셀 프리미티브·챔퍼 상수는 core.pixelfx 가 단일 소스(assets 와 공유, 순환참조 방지).
from core.pixelfx import (CHAMFER, CHAMFER_STEP, CHAMFER_LG, CHAMFER_SM,
                          pixel_rect, pixel_disc, pixelate, _fill_chamfer)
RADIUS = CHAMFER      # 하위호환 별칭 — 이제 '챔퍼 크기'로 해석됨
RADIUS_LG = CHAMFER_LG
RADIUS_SM = CHAMFER_SM
BORDER_INSET = 4      # 테두리 안쪽 채움 간격(패널 = 바깥 테두리 + 안쪽 fill)
SHADOW_OFFSET = (4, 5)
SHADOW_ALPHA = 80
HIGHLIGHT_MIX = 0.24  # 패널 상단 하이라이트 강도
SKY_BAND = 14         # 하늘 그라데이션 밴딩 높이(px) — 도트 톤에 맞게 계단식으로
SKY_QUANT = 10        # 하늘 색 계단화 단계 폭(채널당 반올림 간격)


def _quantize(color, step=SKY_QUANT):
    """색을 채널별로 step 간격으로 반올림 — 배경 그라데이션을 픽셀 톤의 '띠'로 보이게 한다."""
    return tuple(min(255, ((c + step // 2) // step) * step) for c in color[:3])


def draw_mute_icon(screen, x, y):
    """음소거 상태를 보여주는 작은 스피커 아이콘."""
    muted = audio.is_muted() or not audio.is_enabled()
    base = (150, 162, 150) if not muted else (120, 108, 104)
    pygame.draw.rect(screen, base, (x, y + 5, 6, 9))
    pygame.draw.polygon(screen, base, [(x + 6, y + 5), (x + 13, y), (x + 13, y + 19), (x + 6, y + 14)])
    if muted:
        pygame.draw.line(screen, (214, 96, 84), (x + 16, y + 2), (x + 24, y + 17), 2)
        pygame.draw.line(screen, (214, 96, 84), (x + 24, y + 2), (x + 16, y + 17), 2)
    else:
        # 음파 — 매끈한 arc(곡선) 대신 계단식 픽셀 점으로(곡선 없음)
        for wx, wy in [(x + 16, y + 4), (x + 18, y + 7), (x + 16, y + 13)]:
            pygame.draw.rect(screen, base, (wx, wy, 2, 3))
        for wx, wy in [(x + 21, y + 2), (x + 23, y + 6), (x + 23, y + 11), (x + 21, y + 15)]:
            pygame.draw.rect(screen, base, (wx, wy, 2, 3))


def wrap_text(text, font, max_width, max_lines=None):
    # 긴 문장은 줄바꿈 '전에' 통째로 번역해야 영어 기준으로 정확히 줄바꿈된다.
    from core import i18n
    text = i18n.t(str(text))
    lines = []
    truncated = False
    for paragraph in str(text).split("\n"):
        current = ""
        for char in paragraph:
            test_line = current + char
            if font.size(test_line)[0] <= max_width:
                current = test_line
            else:
                if char == " ":
                    # 공백에서 넘치면 지금까지를 한 줄로 확정하고 공백은 버린다
                    # (영어에서 단어가 서로 붙어버리던 버그 방지 — "carrotinto")
                    if current:
                        lines.append(current)
                    current = ""
                elif " " in current:
                    # 단어 중간에서 넘치면 마지막 공백 기준 단어 단위 줄바꿈
                    split_at = current.rfind(" ")
                    lines.append(current[:split_at])
                    current = current[split_at + 1:] + char
                elif current:
                    lines.append(current)
                    current = char
                else:
                    current = char
                if max_lines and len(lines) >= max_lines:
                    truncated = True
                    break
        if max_lines and len(lines) >= max_lines:
            truncated = True
            break
        lines.append(current)

    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        truncated = True

    if truncated and lines:
        while lines[-1] and font.size(lines[-1] + "...")[0] > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] += "..."
    return lines


def clamp_percent(value, max_value=100):
    if max_value <= 0:
        return 0
    return max(0, min(1, value / max_value))


def draw_full_veil(screen, color):
    """캔버스 '전체'(4:3 안전영역 밖 여백 포함)를 덮는 반투명 베일/틴트.
    씬은 800x600 안전영역 서브서피스에 그리므로, 전면 딤을 (800,600)으로만 채우면
    넓은/세로 화면에서 여백만 밝게 남는 '가운데만 어두운 액자' 현상이 생긴다."""
    parent = screen.get_parent()
    target = parent if (parent is not None and parent.get_size() != screen.get_size()) else screen
    veil = pygame.Surface(target.get_size(), pygame.SRCALPHA)
    veil.fill(color)
    target.blit(veil, (0, 0))


def mix_color(a, b, ratio):
    return (
        int(a[0] + (b[0] - a[0]) * ratio),
        int(a[1] + (b[1] - a[1]) * ratio),
        int(a[2] + (b[2] - a[2]) * ratio),
    )


def draw_soft_shadow(screen, rect, radius=RADIUS, offset=SHADOW_OFFSET, alpha=SHADOW_ALPHA):
    # 곡선 없음: 그림자도 계단식 픽셀 챔퍼로(패널 모서리와 톤 일치).
    shadow = pygame.Surface((rect.w + abs(offset[0]) + 8, rect.h + abs(offset[1]) + 8), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(4 + max(0, offset[0]), 4 + max(0, offset[1]), rect.w, rect.h)
    pixel_rect(shadow, (12, 16, 18, alpha), shadow_rect, chamfer=radius)
    screen.blit(shadow, (rect.x - 4, rect.y - 4))


def draw_panel(screen, rect, fill=PANEL_WARM, border=PANEL_EDGE, radius=RADIUS, shadow=True):
    rect = pygame.Rect(rect)
    if shadow:
        draw_soft_shadow(screen, rect, radius=radius)
    pixel_rect(screen, border, rect, chamfer=radius)
    inner = rect.inflate(-BORDER_INSET, -BORDER_INSET)
    pixel_rect(screen, fill, inner, chamfer=max(0, radius - 2))
    highlight = mix_color(fill, WHITE, HIGHLIGHT_MIX)
    pygame.draw.line(screen, highlight, (inner.x + 8, inner.y + 3), (inner.right - 8, inner.y + 3), 2)


def draw_button(screen, rect, text, font, hovered=False, selected=False):
    base = (255, 236, 188) if not selected else (113, 154, 120)
    edge = (123, 92, 65) if not selected else (61, 100, 76)
    if hovered:
        base = mix_color(base, WHITE, 0.18)
    draw_panel(screen, rect, fill=base, border=edge, radius=RADIUS, shadow=True)
    rect = pygame.Rect(rect)
    lines = wrap_text(text, font, rect.w - 18, max_lines=2)
    line_h = font.get_height()
    # 라벨이 버튼 세로를 넘치면(긴 영어가 2줄로 감길 때) 폰트를 줄여 안에 맞춘다.
    if len(lines) * line_h + (len(lines) - 1) * 2 > rect.h - 6:
        for sz in (15, 13, 11):
            small = get_font(sz)
            cand = wrap_text(text, small, rect.w - 18, max_lines=2)
            if len(cand) * small.get_height() + (len(cand) - 1) * 2 <= rect.h - 6:
                font, lines, line_h = small, cand, small.get_height()
                break
        else:
            small = get_font(11)
            font = small
            lines = wrap_text(text, small, rect.w - 18, max_lines=2)
            line_h = small.get_height()
    y = rect.centery - (len(lines) * line_h + (len(lines) - 1) * 2) // 2
    text_color = WHITE if selected else TEXT_DARK
    for line in lines:
        surf = font.render(line, True, text_color)
        screen.blit(surf, (rect.centerx - surf.get_width() // 2, y))
        y += line_h + 2


def draw_meter_bar(screen, rect, value, max_value=100, color=ACCENT_MINT, back=(63, 59, 50)):
    rect = pygame.Rect(rect)
    pixel_rect(screen, back, rect, chamfer=CHAMFER_SM)
    fill_w = int((rect.w - 4) * clamp_percent(value, max_value))
    if fill_w > 0:
        fill_rect = pygame.Rect(rect.x + 2, rect.y + 2, fill_w, rect.h - 4)
        pixel_rect(screen, color, fill_rect, chamfer=CHAMFER_SM)
        shine = mix_color(color, WHITE, 0.22)
        pygame.draw.line(screen, shine, (fill_rect.x + 3, fill_rect.y + 2), (fill_rect.right - 3, fill_rect.y + 2), 1)
    pixel_rect(screen, mix_color(back, WHITE, 0.16), rect, width=1, chamfer=CHAMFER_SM)


# 밤하늘 배경의 고정 별자리 — 매 프레임 같은 자리 (밝기 다양)
_BACKDROP_STARS = [
    (62, 70, 2), (138, 44, 1), (210, 96, 1), (300, 58, 2), (96, 130, 1),
    (250, 24, 1), (430, 78, 1), (372, 120, 1), (508, 40, 2), (566, 96, 1),
    (700, 60, 1), (744, 118, 1), (180, 78, 1), (48, 36, 1), (620, 130, 1),
    (336, 86, 1), (470, 132, 1), (126, 104, 1),
]


from core.layout import bleed_edges   # 적응형 캔버스 여백 채우기(재노출)


def draw_story_backdrop(screen, mood="night"):
    if mood == "nightmare":
        # 악)몽중농원 — 검붉은 하늘과 핏빛 달
        stops = [(0.0, (8, 2, 4)), (0.42, (52, 8, 10)), (1.0, (120, 18, 18))]
        hill_far, hill_near = (46, 10, 10), (28, 5, 5)
        ground = (34, 8, 8)
        moon_glow = (200, 40, 36)
    elif mood == "warm":
        stops = [(0.0, (58, 82, 96)), (0.5, (132, 98, 90)), (1.0, (188, 130, 84))]
        hill_far, hill_near = (70, 92, 84), (50, 74, 60)
        ground = (92, 68, 52)
        moon_glow = (255, 224, 150)
    else:
        stops = [(0.0, (10, 12, 28)), (0.46, (28, 24, 54)), (1.0, (60, 48, 64))]
        hill_far, hill_near = (36, 42, 60), (22, 30, 44)
        ground = (32, 27, 33)
        moon_glow = (246, 234, 198)

    def sky(t):
        for i in range(len(stops) - 1):
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            if t <= t1:
                return mix_color(c0, c1, (t - t0) / max(1e-6, t1 - t0))
        return stops[-1][1]

    # 배경을 캔버스 전체 폭으로 이어 그린다(여백까지 하늘/산/땅 연장). 오브젝트(달·별)는 안전영역에.
    parent = screen.get_parent()
    if parent is not None and parent.get_size() != screen.get_size():
        bg = parent
        ox, oy = screen.get_offset()
        PW, PH = parent.get_size()
    else:
        bg = screen
        ox, oy = 0, 0
        PW, PH = screen.get_size()
    top_y = -oy
    bot_y = PH - oy

    # 하늘 — 계단식 '띠'(도트 톤), 위 여백까지 전체 폭
    yy = (top_y // SKY_BAND) * SKY_BAND
    while yy < 600:
        t = max(0.0, min(1.0, (yy + SKY_BAND * 0.5) / 600.0))
        pygame.draw.rect(bg, _quantize(sky(t)), (0, yy + oy, PW, SKY_BAND))
        yy += SKY_BAND

    # 별 — 안전영역 + 여백 일부에도 흩뿌려 밤하늘이 이어지게(가로로 반복 배치)
    for sx, sy, sb in _BACKDROP_STARS:
        v = 190 + sb * 24
        col = (min(255, v), min(255, v), 220)
        for rep in range(-1, (PW // 800) + 2):          # 안전영역 좌우 여백까지 별 패턴 반복
            bx = sx + ox + rep * 800
            if -8 <= bx <= PW + 8:
                pygame.draw.circle(bg, col, (bx, sy + oy), sb)

    # 달 — 헤일로는 '계단 알파' 도트 글로우 (연속 falloff 평균축소는 모자이크 블러로 보임 + 캐시로 매 프레임 재생성 제거)
    mx, my = 648, 90
    from core.pixelfx import glow_sprite, blit_glow
    blit_glow(screen, glow_sprite(84, moon_glow, px=5, steps=(10, 22, 38)), (mx, my))
    if game_state.player_name == "서태양":
        # 이스터에그: 달 대신 '얼굴 그려진 태양'. 악)몽중농원에서는 붉게 물들고 선글라스를 낀다.
        nm = (mood == "nightmare")
        ray_col = (222, 74, 52) if nm else (255, 210, 90)
        body_col = (204, 60, 50) if nm else (255, 214, 92)
        edge_col = (255, 140, 120) if nm else (255, 236, 150)
        for i in range(12):
            ang = i * (math.pi / 6)
            x1, y1 = mx + int(38 * math.cos(ang)), my + int(38 * math.sin(ang))
            x2, y2 = mx + int(50 * math.cos(ang)), my + int(50 * math.sin(ang))
            pygame.draw.line(screen, ray_col, (x1, y1), (x2, y2), 3)
        pygame.draw.circle(screen, body_col, (mx, my), 34)
        pygame.draw.circle(screen, edge_col, (mx, my), 34, 3)
        if nm:
            # 검붉은 해 + 캣아이 선글라스 (지옥의 간지)
            lens, frame, shine = (16, 12, 20), (5, 4, 6), (180, 175, 190)
            
            # 왼쪽/오른쪽 프레임 (바깥쪽 테두리 먼저 검게 채우기)
            left_frame = [(mx - 1, my - 9), (mx - 27, my - 15), (mx - 19, my + 3), (mx - 3, my - 4)]
            right_frame = [(mx + 1, my - 9), (mx + 27, my - 15), (mx + 19, my + 3), (mx + 3, my - 4)]
            pygame.draw.polygon(screen, frame, left_frame)
            pygame.draw.polygon(screen, frame, right_frame)
            
            # 왼쪽/오른쪽 렌즈 (내부에 렌즈 색 얹기)
            left_lens = [(mx - 2, my - 7), (mx - 24, my - 13), (mx - 18, my + 1), (mx - 4, my - 3)]
            right_lens = [(mx + 2, my - 7), (mx + 24, my - 13), (mx + 18, my + 1), (mx + 4, my - 3)]
            pygame.draw.polygon(screen, lens, left_lens)
            pygame.draw.polygon(screen, lens, right_lens)
            
            # 외곽선 살짝 깎아 윤곽 뚜렷이
            pygame.draw.polygon(screen, (35, 30, 40), left_frame, 1)
            pygame.draw.polygon(screen, (35, 30, 40), right_frame, 1)

            # 브릿지 (두 알 연결)
            pygame.draw.line(screen, frame, (mx - 2, my - 6), (mx + 2, my - 6), 3)
            # 선글라스 다리 (귀 쪽으로 비스듬히)
            pygame.draw.line(screen, frame, (mx - 25, my - 11), (mx - 33, my - 13), 2)
            pygame.draw.line(screen, frame, (mx + 25, my - 11), (mx + 33, my - 13), 2)
            
            # 캣아이 선글라스 렌즈 반짝임 사선
            pygame.draw.line(screen, shine, (mx - 20, my - 10), (mx - 15, my - 4), 2)
            pygame.draw.line(screen, shine, (mx + 15, my - 4), (mx + 20, my - 10), 2)
            
            # 씩 웃는 입
            pygame.draw.arc(screen, (70, 22, 18), (mx - 13, my + 2, 26, 18), 3.4, 6.02, 3)  # 씩 웃음
        else:
            pygame.draw.circle(screen, (120, 80, 20), (mx - 12, my - 6), 4)   # 왼눈
            pygame.draw.circle(screen, (120, 80, 20), (mx + 12, my - 6), 4)   # 오눈
            pygame.draw.arc(screen, (120, 80, 20), (mx - 14, my - 2, 28, 22), 3.34, 6.08, 3)  # 미소
    else:
        # 달 — 헤일로(위 halo)는 소프트하게 두고, 달 본체는 큰 픽셀 디스크로(곡선 없음).
        pixel_disc(screen, moon_glow, (mx, my), 32, px=3)
        pixel_disc(screen, mix_color(moon_glow, WHITE, 0.4), (mx, my), 30, px=3)
        pixel_disc(screen, _quantize(sky(my / 600.0)), (mx - 13, my - 7), 27, px=3)  # 그림자로 초승달

    # 산 2겹 (멀고 옅은 뒤, 가깝고 짙은 앞) — 능선을 캔버스 양끝까지 연장
    def _hill(color, ridge):
        poly = [(0, ridge[0][1] + oy)]
        poly += [(px + ox, py + oy) for px, py in ridge]
        poly += [(PW, ridge[-1][1] + oy), (PW, bot_y + oy), (0, bot_y + oy)]
        pygame.draw.polygon(bg, color, poly)
    _hill(hill_far, [(0, 332), (140, 264), (300, 320), (470, 250), (650, 318), (800, 268)])
    _hill(hill_near, [(0, 372), (130, 312), (286, 360), (430, 300), (610, 356), (800, 308)])

    # 바닥 — 전체 폭, 아래 여백까지
    pygame.draw.rect(bg, ground, (0, 396 + oy, PW, bot_y - 396))
    for gy in range(420, bot_y, 38):
        pygame.draw.line(bg, mix_color(ground, WHITE, 0.07), (0, gy + oy), (PW, gy + 16 + oy), 1)

    bleed_edges(screen)   # 여백 깊이 마감(가장자리 비네트 + 떠다니는 빛; 배경은 이미 전체 폭으로 그림)


def draw_multiline_text(screen, text, font, color, x, y, max_width, line_gap=4, max_lines=None):
    lines = wrap_text(text, font, max_width, max_lines)
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        screen.blit(surf, (x, y + i * (font.get_height() + line_gap)))
    return y + len(lines) * (font.get_height() + line_gap)


def draw_centered_lines(screen, lines, font, color, center_x, start_y, line_gap=4):
    y = start_y
    for line in lines:
        surf = font.render(line, True, color)
        screen.blit(surf, (center_x - surf.get_width() // 2, y))
        y += font.get_height() + line_gap
    return y


def draw_wood_panel(screen, rect):
    draw_panel(screen, rect, fill=(236, 202, 149), border=(111, 78, 54), radius=8)


def draw_light_panel(screen, rect):
    draw_panel(screen, rect, fill=PANEL_WARM, border=PANEL_EDGE, radius=8)


def draw_understanding_badge(screen, x, y, w):
    """Draw the understanding stage name with moon phase."""
    _, stage_name, phase = get_understanding_stage(game_state.understanding)

    font = get_font(15)
    label_font = get_font(13)

    label = label_font.render("이해도", True, TEXT_MUTED)

    # 달 위상 아이콘은 자꾸 어긋나 보여 빼고, 라벨 뒤에 단계명을 바로 붙여 이름이 잘리지 않게 한다.
    name_x = x + label.get_width() + 8
    avail = x + w - name_x
    name_surf = font.render(stage_name, True, TEXT_DARK)
    if name_surf.get_width() > avail:
        name_surf = get_font(13).render(stage_name, True, TEXT_DARK)
    if name_surf.get_width() <= avail:
        screen.blit(label, (x, y - 1))
        screen.blit(name_surf, (name_x, y))
    else:
        # 라벨+이름이 같이 안 들어가면(영어 단계명) 라벨을 빼고 이름만 남긴다 —
        # 서사 장치인 단계명이 정보의 핵심이라 이름 생략은 정보 손실이었다.
        for sz in (13, 12, 11):
            name_surf = get_font(sz).render(stage_name, True, TEXT_DARK)
            if name_surf.get_width() <= w:
                break
        screen.blit(name_surf, (x, y))

    bar = pygame.Rect(x, y + 22, w, 10)
    fill_w = int((bar.w - 4) * clamp_percent(game_state.understanding, 60))
    pixel_rect(screen, (73, 65, 54), bar, chamfer=CHAMFER_SM)
    if fill_w:
        pixel_rect(screen, GOLD, (bar.x + 2, bar.y + 2, fill_w, bar.h - 4), chamfer=CHAMFER_SM)
    pixel_rect(screen, mix_color(TEXT_MUTED, WHITE, 0.18), bar, width=1, chamfer=CHAMFER_SM)


def draw_top_bar(screen, show_stats=True):
    # 적응형(가장자리 앵커): 확장 캔버스에선 바를 캔버스 폭까지 늘려 그린다. 내용(제목·타이머·점수)은
    # 안전영역 좌표 그대로 두어 가운데 정렬을 유지한다. 4:3(여백 0)이면 기존과 동일.
    parent = screen.get_parent()
    if parent:
        ox, oy = screen.get_offset()
        pw = parent.get_size()[0]
        g = 14 + int(min(58, max(0, ox - 40) * 0.32))   # 넓을수록 가장자리 여유를 더 남긴다(끝까지 안 늘림)
        draw_panel(parent, pygame.Rect(g, oy + 12, pw - 2 * g, 56),
                   fill=(44, 57, 58), border=(229, 192, 124), radius=RADIUS_LG)
    else:
        draw_panel(screen, pygame.Rect(14, 12, 772, 56),
                   fill=(44, 57, 58), border=(229, 192, 124), radius=RADIUS_LG)

    font = get_font(23)
    small_font = get_font(14)

    if show_stats:
        timer_rect = pygame.Rect(28, 23, 222, 34)
        # 오른쪽 끝에 소리 설정 버튼 자리를 남기려고 점수 박스를 살짝 좁힘
        score_rect = pygame.Rect(550, 23, 186, 34)
        pixel_rect(screen, (29, 38, 40), timer_rect, chamfer=RADIUS)
        pixel_rect(screen, (29, 38, 40), score_rect, chamfer=RADIUS)
        pixel_rect(screen, (79, 96, 92), timer_rect, width=1, chamfer=RADIUS)
        pixel_rect(screen, (79, 96, 92), score_rect, width=1, chamfer=RADIUS)

        timer_label = small_font.render("남은 시간", True, (199, 186, 147))
        screen.blit(timer_label, (timer_rect.x + 12, timer_rect.y + 9))
        timer_value = font.render(f"{max(0, game_state.timer):04.1f}", True, WHITE)
        screen.blit(timer_value, (timer_rect.right - timer_value.get_width() - 12, timer_rect.y + 5))

        score_label = small_font.render("점수", True, (199, 186, 147))
        screen.blit(score_label, (score_rect.x + 12, score_rect.y + 9))
        score_value = font.render(f"{game_state.score:06d}", True, WHITE)
        screen.blit(score_value, (score_rect.right - score_value.get_width() - 12, score_rect.y + 5))
    else:
        title_text = "악)몽중농원" if game_state.nightmare else "몽중농원"
        title_col = (255, 158, 148) if game_state.nightmare else WHITE
        title_surf = get_font(27).render(title_text, True, title_col)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 24))
        # 음소거/음량은 오른쪽 위 스피커 버튼(소리 설정)에서 관리


def draw_bottom_bar(screen, obj_name, obj_desc):
    # 적응형(가장자리 앵커): 확장 캔버스에선 하단 바를 캔버스 폭까지 늘린다. 글은 안전영역 좌표 유지.
    parent = screen.get_parent()
    if parent:
        ox, oy = screen.get_offset()
        pw = parent.get_size()[0]
        g = 18 + int(min(58, max(0, ox - 40) * 0.32))   # 하단 바도 가장자리 여유를 남긴다
        draw_panel(parent, pygame.Rect(g, oy + 486, pw - 2 * g, 98),
                   fill=(252, 238, 211), border=(119, 90, 64), radius=RADIUS_LG)
    else:
        draw_panel(screen, pygame.Rect(18, 486, 764, 98),
                   fill=(252, 238, 211), border=(119, 90, 64), radius=RADIUS_LG)

    font_name = get_font(22)
    font_desc = get_font(16)

    name_surf = font_name.render(obj_name, True, TEXT_DARK)
    screen.blit(name_surf, (40, 498))
    pygame.draw.rect(screen, (221, 173, 96), (40, 527, min(170, name_surf.get_width() + 16), 3))
    draw_multiline_text(screen, obj_desc, font_desc, TEXT_DARK, 40, 536, 718, line_gap=1, max_lines=2)
