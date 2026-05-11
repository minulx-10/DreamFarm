import math
import pygame
from core.assets import *
from core.game_state import game_state, get_understanding_stage


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
    pygame.draw.rect(screen, WOOD_COLOR, rect)
    pygame.draw.rect(screen, WOOD_LIGHT, rect, 4)
    pygame.draw.rect(screen, WOOD_DARK, rect, 2)
    pygame.draw.rect(screen, BLACK, rect, 1)


def draw_light_panel(screen, rect):
    pygame.draw.rect(screen, PANEL_PALE, rect)
    pygame.draw.rect(screen, WOOD_LIGHT, rect, 3)
    pygame.draw.rect(screen, WOOD_DARK, rect, 2)
    pygame.draw.rect(screen, TEXT_DARK, rect, 1)


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

    # "마음" label
    label = label_font.render("마음", True, TEXT_MUTED)
    screen.blit(label, (x, y - 1))

    # Moon icon + stage name
    draw_moon_phase(screen, x + 30, y - 2, phase, 18)
    name_surf = font.render(stage_name, True, TEXT_DARK)
    screen.blit(name_surf, (x + 52, y))

    # Gradient bar underneath
    bar = pygame.Rect(x, y + 22, w, 10)
    fill_w = int((bar.w - 4) * clamp_percent(game_state.understanding, 60))
    pygame.draw.rect(screen, (60, 50, 35), bar, border_radius=3)

    if fill_w > 0:
        fill_surf = pygame.Surface((fill_w, bar.h - 4), pygame.SRCALPHA)
        for i in range(fill_w):
            ratio = i / max(1, fill_w)
            cr = int(120 + 135 * ratio)
            cg = int(100 + 100 * ratio)
            cb = int(50 + 30 * (1 - ratio))
            fill_surf.set_at((i, 0), (cr, cg, cb))
        # Stretch single row to full height
        fill_surf = pygame.transform.scale(fill_surf, (fill_w, bar.h - 4))
        screen.blit(fill_surf, (bar.x + 2, bar.y + 2))

    pygame.draw.rect(screen, TEXT_DARK, bar, 1, border_radius=3)


def draw_top_bar(screen, show_stats=True):
    panel_rect = pygame.Rect(10, 10, 780, 60)
    draw_wood_panel(screen, panel_rect)

    font = get_font(30)

    if show_stats:
        timer_text = f"남은 시간: {max(0, game_state.timer):04.1f}"
        timer_surf = font.render(timer_text, True, TEXT_DARK)
        screen.blit(timer_surf, (30, 25))

        score_text = f"점수: {game_state.score:06d}"
        score_surf = font.render(score_text, True, TEXT_DARK)
        screen.blit(score_surf, (780 - score_surf.get_width() - 20, 25))
    else:
        title_text = "몽중농원"
        title_surf = font.render(title_text, True, TEXT_DARK)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 25))


def draw_bottom_bar(screen, obj_name, obj_desc):
    panel_rect = pygame.Rect(10, 600 - 100, 780, 90)
    draw_wood_panel(screen, panel_rect)

    font_name = get_font(26)
    font_desc = get_font(16)

    name_surf = font_name.render(obj_name, True, TEXT_DARK)

    screen.blit(name_surf, (30, 600 - 85))
    draw_multiline_text(screen, obj_desc, font_desc, TEXT_DARK, 30, 600 - 50, 730, line_gap=0, max_lines=2)
