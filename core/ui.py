import math
import pygame
from core.assets import *
from core.game_state import game_state, get_understanding_stage
from core import audio


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
        pygame.draw.arc(screen, base, (x + 12, y + 2, 9, 15), -0.9, 0.9, 2)
        pygame.draw.arc(screen, base, (x + 15, y - 2, 12, 23), -0.9, 0.9, 2)


def wrap_text(text, font, max_width, max_lines=None):
    lines = []
    truncated = False
    for paragraph in str(text).split("\n"):
        current = ""
        for char in paragraph:
            test_line = current + char
            if font.size(test_line)[0] <= max_width:
                current = test_line
            else:
                if current:
                    if " " in current:
                        split_at = current.rfind(" ")
                        lines.append(current[:split_at])
                        current = current[split_at + 1:] + ("" if char == " " else char)
                    else:
                        lines.append(current)
                        current = char if char != " " else ""
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


def mix_color(a, b, ratio):
    return (
        int(a[0] + (b[0] - a[0]) * ratio),
        int(a[1] + (b[1] - a[1]) * ratio),
        int(a[2] + (b[2] - a[2]) * ratio),
    )


def draw_vertical_gradient(screen, rect, top_color, bottom_color):
    for i in range(rect.h):
        ratio = i / max(1, rect.h - 1)
        pygame.draw.line(
            screen,
            mix_color(top_color, bottom_color, ratio),
            (rect.x, rect.y + i),
            (rect.right, rect.y + i),
        )


def draw_soft_shadow(screen, rect, radius=8, offset=(4, 5), alpha=80):
    shadow = pygame.Surface((rect.w + abs(offset[0]) + 8, rect.h + abs(offset[1]) + 8), pygame.SRCALPHA)
    shadow_rect = pygame.Rect(4 + max(0, offset[0]), 4 + max(0, offset[1]), rect.w, rect.h)
    pygame.draw.rect(shadow, (12, 16, 18, alpha), shadow_rect, border_radius=radius)
    screen.blit(shadow, (rect.x - 4, rect.y - 4))


def draw_panel(screen, rect, fill=PANEL_WARM, border=PANEL_EDGE, radius=8, shadow=True):
    if shadow:
        draw_soft_shadow(screen, rect, radius=radius)
    pygame.draw.rect(screen, border, rect, border_radius=radius)
    inner = rect.inflate(-4, -4)
    pygame.draw.rect(screen, fill, inner, border_radius=max(2, radius - 2))
    highlight = mix_color(fill, WHITE, 0.24)
    pygame.draw.line(screen, highlight, (inner.x + 8, inner.y + 3), (inner.right - 8, inner.y + 3), 2)


def draw_button(screen, rect, text, font, hovered=False, selected=False):
    base = (255, 236, 188) if not selected else (113, 154, 120)
    edge = (123, 92, 65) if not selected else (61, 100, 76)
    if hovered:
        base = mix_color(base, WHITE, 0.18)
    draw_panel(screen, rect, fill=base, border=edge, radius=8, shadow=True)
    lines = wrap_text(text, font, rect.w - 18, max_lines=2)
    line_h = font.get_height()
    y = rect.centery - (len(lines) * line_h + (len(lines) - 1) * 2) // 2
    text_color = WHITE if selected else TEXT_DARK
    for line in lines:
        surf = font.render(line, True, text_color)
        screen.blit(surf, (rect.centerx - surf.get_width() // 2, y))
        y += line_h + 2


def draw_meter_bar(screen, rect, value, max_value=100, color=ACCENT_MINT, back=(63, 59, 50)):
    pygame.draw.rect(screen, back, rect, border_radius=5)
    fill_w = int((rect.w - 4) * clamp_percent(value, max_value))
    if fill_w > 0:
        fill_rect = pygame.Rect(rect.x + 2, rect.y + 2, fill_w, rect.h - 4)
        pygame.draw.rect(screen, color, fill_rect, border_radius=4)
        shine = mix_color(color, WHITE, 0.22)
        pygame.draw.line(screen, shine, (fill_rect.x + 3, fill_rect.y + 2), (fill_rect.right - 3, fill_rect.y + 2), 1)
    pygame.draw.rect(screen, mix_color(back, WHITE, 0.16), rect, 1, border_radius=5)


# 밤하늘 배경의 고정 별자리 — 매 프레임 같은 자리 (밝기 다양)
_BACKDROP_STARS = [
    (62, 70, 2), (138, 44, 1), (210, 96, 1), (300, 58, 2), (96, 130, 1),
    (250, 24, 1), (430, 78, 1), (372, 120, 1), (508, 40, 2), (566, 96, 1),
    (700, 60, 1), (744, 118, 1), (180, 78, 1), (48, 36, 1), (620, 130, 1),
    (336, 86, 1), (470, 132, 1), (126, 104, 1),
]


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

    for y in range(600):
        pygame.draw.line(screen, sky(y / 600.0), (0, y), (800, y))

    # 별
    for sx, sy, sb in _BACKDROP_STARS:
        v = 190 + sb * 24
        pygame.draw.circle(screen, (min(255, v), min(255, v), 220), (sx, sy), sb)

    # 달 — 부드러운 헤일로 + 초승달
    mx, my = 648, 90
    halo = pygame.Surface((180, 180), pygame.SRCALPHA)
    for r in range(84, 0, -6):
        a = int(40 * (1 - r / 84.0))
        pygame.draw.circle(halo, (moon_glow[0], moon_glow[1], moon_glow[2], a), (90, 90), r)
    screen.blit(halo, (mx - 90, my - 90))
    pygame.draw.circle(screen, moon_glow, (mx, my), 32)
    pygame.draw.circle(screen, mix_color(moon_glow, WHITE, 0.4), (mx, my), 30)
    pygame.draw.circle(screen, sky(my / 600.0), (mx - 13, my - 7), 27)  # 그림자로 초승달

    # 산 2겹 (멀고 옅은 뒤, 가깝고 짙은 앞)
    pygame.draw.polygon(screen, hill_far, [(0, 332), (140, 264), (300, 320), (470, 250), (650, 318), (800, 268), (800, 600), (0, 600)])
    pygame.draw.polygon(screen, hill_near, [(0, 372), (130, 312), (286, 360), (430, 300), (610, 356), (800, 308), (800, 600), (0, 600)])

    # 바닥
    pygame.draw.rect(screen, ground, (0, 396, 800, 204))
    for y in range(420, 600, 38):
        pygame.draw.line(screen, mix_color(ground, WHITE, 0.07), (0, y), (800, y + 12), 1)


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


def draw_moon_phase(screen, x, y, phase, size=18):
    """Draw a clean moon phase icon."""
    cx, cy = x + size // 2, y + size // 2
    r = size // 2

    # Outer glow
    pygame.draw.circle(screen, (80, 75, 55), (cx, cy), r + 1)
    # Dark base
    pygame.draw.circle(screen, (40, 35, 28), (cx, cy), r)

    bright = (255, 240, 180)
    if phase == 0:
        pygame.draw.circle(screen, (55, 50, 40), (cx, cy), r, 1)
    elif phase == 4:
        pygame.draw.circle(screen, bright, (cx, cy), r)
        pygame.draw.circle(screen, (220, 200, 140), (cx, cy), r - 2)
        pygame.draw.circle(screen, bright, (cx, cy), r - 3)
        pygame.draw.circle(screen, (180, 160, 110), (cx, cy), r, 1)
    else:
        # Draw lit portion using overlapping circles
        if phase == 1:
            clip_r = r
            clip_offset = r // 2
        elif phase == 2:
            clip_r = r
            clip_offset = 0
        else:  # phase 3
            clip_r = r
            clip_offset = -(r // 2)
        # Bright side
        for dy in range(-r, r + 1):
            row_w = int(math.sqrt(max(0, r * r - dy * dy)))
            shadow_w = int(math.sqrt(max(0, clip_r * clip_r - dy * dy)))
            left = cx + clip_offset - shadow_w if phase < 3 else cx - row_w
            right = cx + row_w
            if phase == 1:
                left = max(left, cx - row_w + row_w // 2)
            if right > left:
                pygame.draw.line(screen, bright, (max(cx - r, left), cy + dy), (min(cx + r, right), cy + dy))
        pygame.draw.circle(screen, (180, 160, 110), (cx, cy), r, 1)


def draw_understanding_badge(screen, x, y, w):
    """Draw the understanding stage name with moon phase."""
    _, stage_name, phase = get_understanding_stage(game_state.understanding)

    font = get_font(15)
    label_font = get_font(13)

    label = label_font.render("이해도", True, TEXT_MUTED)
    screen.blit(label, (x, y - 1))

    # 달 위상 아이콘은 자꾸 어긋나 보여 빼고, 라벨 뒤에 단계명을 바로 붙여 이름이 잘리지 않게 한다.
    name_x = x + label.get_width() + 8
    avail = x + w - name_x
    name_surf = font.render(stage_name, True, TEXT_DARK)
    if name_surf.get_width() > avail:
        name_surf = get_font(13).render(stage_name, True, TEXT_DARK)
    screen.blit(name_surf, (name_x, y))

    bar = pygame.Rect(x, y + 22, w, 10)
    fill_w = int((bar.w - 4) * clamp_percent(game_state.understanding, 60))
    pygame.draw.rect(screen, (73, 65, 54), bar, border_radius=4)
    if fill_w:
        pygame.draw.rect(screen, GOLD, (bar.x + 2, bar.y + 2, fill_w, bar.h - 4), border_radius=3)
    pygame.draw.rect(screen, mix_color(TEXT_MUTED, WHITE, 0.18), bar, 1, border_radius=4)


def draw_top_bar(screen, show_stats=True):
    panel_rect = pygame.Rect(14, 12, 772, 56)
    draw_panel(screen, panel_rect, fill=(44, 57, 58), border=(229, 192, 124), radius=10)

    font = get_font(23)
    small_font = get_font(14)

    if show_stats:
        timer_rect = pygame.Rect(28, 23, 222, 34)
        # 오른쪽 끝에 소리 설정 버튼 자리를 남기려고 점수 박스를 살짝 좁힘
        score_rect = pygame.Rect(550, 23, 186, 34)
        pygame.draw.rect(screen, (29, 38, 40), timer_rect, border_radius=8)
        pygame.draw.rect(screen, (29, 38, 40), score_rect, border_radius=8)
        pygame.draw.rect(screen, (79, 96, 92), timer_rect, 1, border_radius=8)
        pygame.draw.rect(screen, (79, 96, 92), score_rect, 1, border_radius=8)

        timer_label = small_font.render("남은 시간", True, (199, 186, 147))
        screen.blit(timer_label, (timer_rect.x + 12, timer_rect.y + 9))
        timer_value = font.render(f"{max(0, game_state.timer):04.1f}", True, WHITE)
        screen.blit(timer_value, (timer_rect.right - timer_value.get_width() - 12, timer_rect.y + 5))

        score_label = small_font.render("점수", True, (199, 186, 147))
        screen.blit(score_label, (score_rect.x + 12, score_rect.y + 9))
        score_value = font.render(f"{game_state.score:06d}", True, WHITE)
        screen.blit(score_value, (score_rect.right - score_value.get_width() - 12, score_rect.y + 5))
    else:
        title_text = "몽중농원"
        title_surf = get_font(27).render(title_text, True, WHITE)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 24))
        # 음소거/음량은 오른쪽 위 스피커 버튼(소리 설정)에서 관리


def draw_bottom_bar(screen, obj_name, obj_desc):
    panel_rect = pygame.Rect(18, 486, 764, 98)
    draw_panel(screen, panel_rect, fill=(252, 238, 211), border=(119, 90, 64), radius=10)

    font_name = get_font(22)
    font_desc = get_font(16)

    name_surf = font_name.render(obj_name, True, TEXT_DARK)
    screen.blit(name_surf, (40, 498))
    pygame.draw.rect(screen, (221, 173, 96), (40, 527, min(170, name_surf.get_width() + 16), 3), border_radius=2)
    draw_multiline_text(screen, obj_desc, font_desc, TEXT_DARK, 40, 536, 718, line_gap=1, max_lines=2)
