import pygame
from core.assets import *
from core.game_state import game_state


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
        screen.blit(title_surf, (400 - title_surf.get_width()//2, 25))

def draw_bottom_bar(screen, obj_name, obj_desc):
    panel_rect = pygame.Rect(10, 600 - 100, 780, 90)
    draw_wood_panel(screen, panel_rect)
    
    font_name = get_font(26)
    font_desc = get_font(16)
    
    name_surf = font_name.render(obj_name, True, TEXT_DARK)
    
    screen.blit(name_surf, (30, 600 - 85))
    draw_multiline_text(screen, obj_desc, font_desc, TEXT_DARK, 30, 600 - 50, 730, line_gap=0, max_lines=2)
