import pygame
from core.assets import *
from core.game_state import game_state

def draw_wood_panel(screen, rect):
    pygame.draw.rect(screen, WOOD_COLOR, rect)
    pygame.draw.rect(screen, WOOD_LIGHT, rect, 4)
    pygame.draw.rect(screen, WOOD_DARK, rect, 2)
    pygame.draw.rect(screen, BLACK, rect, 1)

def draw_top_bar(screen, show_stats=True):
    panel_rect = pygame.Rect(10, 10, 780, 60)
    draw_wood_panel(screen, panel_rect)
    
    font = get_font(30)
    
    if show_stats:
        timer_text = f"남은 시간: {max(0, game_state.timer):04.1f}"
        timer_surf = font.render(timer_text, True, TEXT_BROWN)
        screen.blit(timer_surf, (30, 25))
        
        score_text = f"점수: {game_state.score:06d}"
        score_surf = font.render(score_text, True, TEXT_BROWN)
        screen.blit(score_surf, (780 - score_surf.get_width() - 20, 25))
    else:
        title_text = "당근 한 뿌리의 시간"
        title_surf = font.render(title_text, True, TEXT_BROWN)
        screen.blit(title_surf, (400 - title_surf.get_width()//2, 25))

def draw_bottom_bar(screen, obj_name, obj_desc):
    panel_rect = pygame.Rect(10, 600 - 100, 780, 90)
    draw_wood_panel(screen, panel_rect)
    
    font_name = get_font(26)
    font_desc = get_font(20)
    
    name_surf = font_name.render(obj_name, True, TEXT_BROWN)
    desc_surf = font_desc.render(obj_desc, True, (80, 60, 40))
    
    screen.blit(name_surf, (30, 600 - 85))
    screen.blit(desc_surf, (30, 600 - 50))
