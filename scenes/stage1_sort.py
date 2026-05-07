import pygame
import random
from core.game_state import game_state
from core.assets import *
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel

class SortItem:
    def __init__(self, item_type, x, y):
        self.item_type = item_type
        self.x = x
        self.y = y
        self.sprite = sprites[item_type]
        self.size = self.sprite.get_width()
        self.rect = pygame.Rect(x, y, self.size, self.size)
        self.dragging = False
        
        if item_type == 'seed':
            self.name = "당근 씨앗"
            self.desc = "밭에 심어야 할 소중한 씨앗입니다."
            self.is_good = True
        elif item_type == 'weed':
            self.name = "잡초"
            self.desc = "영양분을 빼앗는 잡초입니다. 치워야 합니다."
            self.is_good = False
        elif item_type == 'rock':
            self.name = "돌멩이"
            self.desc = "뿌리를 막는 단단한 돌멩이입니다. 치워야 합니다."
            self.is_good = False
        elif item_type == 'leaf':
            self.name = "썩은 잎"
            self.desc = "병균을 옮길 수 있는 썩은 잎입니다. 치워야 합니다."
            self.is_good = False

    def draw(self, screen):
        screen.blit(self.sprite, self.rect)
        if self.dragging:
            pygame.draw.rect(screen, WHITE, self.rect, 2)

class Stage1Scene:
    def __init__(self):
        game_state.timer = 40.0
        game_state.score = 0
        self.items = []
        
        for _ in range(5): self.spawn_item('seed')
        for _ in range(3): self.spawn_item('weed')
        for _ in range(3): self.spawn_item('rock')
        for _ in range(2): self.spawn_item('leaf')
            
        self.dragged_item = None
        self.bin_keep = pygame.Rect(140, 400, 120, 120)
        self.bin_trash = pygame.Rect(540, 400, 120, 120)
        self.hovered_name = "밭 준비하기"
        self.hovered_desc = "씨앗은 밭(왼쪽)으로, 쓰레기는 쓰레기통(오른쪽)으로 분류하세요!"
        self.stage_clear = False
        self.clear_timer = 2.0

    def spawn_item(self, itype):
        x = random.randint(100, 700 - 40)
        y = random.randint(100, 350 - 40)
        self.items.append(SortItem(itype, x, y))

    def handle_events(self, events):
        if self.stage_clear: return
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for item in reversed(self.items):
                    if item.rect.collidepoint(event.pos):
                        item.dragging = True
                        self.dragged_item = item
                        self.items.remove(item)
                        self.items.append(item)
                        break
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragged_item:
                self.dragged_item.dragging = False
                if self.bin_keep.collidepoint(event.pos):
                    if self.dragged_item.is_good:
                        game_state.score += 100
                        self.hovered_desc = "정확합니다! 씨앗을 심을 준비가 되었습니다."
                    else:
                        game_state.score -= 50
                        self.hovered_desc = "앗! 이건 밭에 두면 안 됩니다."
                    self.items.remove(self.dragged_item)
                elif self.bin_trash.collidepoint(event.pos):
                    if not self.dragged_item.is_good:
                        game_state.score += 100
                        self.hovered_desc = "잘 치웠습니다!"
                    else:
                        game_state.score -= 50
                        self.hovered_desc = "앗! 소중한 씨앗을 버리면 안 됩니다."
                    self.items.remove(self.dragged_item)
                self.dragged_item = None
            elif event.type == pygame.MOUSEMOTION:
                if self.dragged_item:
                    self.dragged_item.rect.x += event.rel[0]
                    self.dragged_item.rect.y += event.rel[1]
                else:
                    hovered = False
                    for item in reversed(self.items):
                        if item.rect.collidepoint(event.pos):
                            self.hovered_name = item.name
                            self.hovered_desc = item.desc
                            hovered = True
                            break
                    if not hovered:
                        self.hovered_name = "밭 준비하기"
                        self.hovered_desc = "씨앗은 밭(왼쪽)으로, 쓰레기는 쓰레기통(오른쪽)으로 분류하세요!"

    def update(self, dt):
        if self.stage_clear:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                bonus = 0
                if game_state.score >= 500: bonus = 20
                elif game_state.score >= 200: bonus = 10
                elif game_state.score >= 100: bonus = 5
                
                game_state.understanding += bonus
                game_state.transition_text = f"미니게임 완료!\n\n획득 점수: {game_state.score}점\n추가 이해도 보너스: +{bonus}"
                game_state.transition_next = game_state.return_scene
                game_state.is_clear_transition = True
                game_state.current_scene = "transition"
            return
        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.stage_clear = True
        if len(self.items) == 0:
            self.stage_clear = True

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        
        screen.blit(sprites['basket'], (self.bin_keep.x, self.bin_keep.y))
        font = get_font(24)
        keep_text = font.render("밭에 심기", True, BLACK)
        pygame.draw.rect(screen, WOOD_LIGHT, (self.bin_keep.centerx - 60, self.bin_keep.bottom + 10, 120, 30), border_radius=5)
        screen.blit(keep_text, (self.bin_keep.centerx - keep_text.get_width()//2, self.bin_keep.bottom + 12))

        screen.blit(sprites['trashcan'], (self.bin_trash.x, self.bin_trash.y))
        trash_text = font.render("쓰레기통", True, BLACK)
        pygame.draw.rect(screen, WOOD_LIGHT, (self.bin_trash.centerx - 60, self.bin_trash.bottom + 10, 120, 30), border_radius=5)
        screen.blit(trash_text, (self.bin_trash.centerx - trash_text.get_width()//2, self.bin_trash.bottom + 12))

        for item in self.items: item.draw(screen)
        draw_top_bar(screen)
        
        if self.stage_clear:
            clear_text = font.render("스테이지 완료!", True, (200, 100, 0))
            panel = pygame.Rect(400 - 100, 300 - 30, 200, 60)
            draw_wood_panel(screen, panel)
            screen.blit(clear_text, (400 - clear_text.get_width()//2, 300 - clear_text.get_height()//2))
            draw_bottom_bar(screen, "결과", f"얻은 점수: {game_state.score}")
        else:
            if self.dragged_item:
                draw_bottom_bar(screen, self.dragged_item.name, "분류할 위치로 드래그하세요.")
            else:
                draw_bottom_bar(screen, self.hovered_name, self.hovered_desc)
