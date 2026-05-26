import pygame
import random
from core.game_state import game_state
from core.assets import *
from core.ui import draw_top_bar, draw_bottom_bar, draw_light_panel, draw_wood_panel

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
            self.desc = "밭으로 보내야 할 당근 씨앗입니다."
            self.is_good = True
        elif item_type == 'weed':
            self.name = "잡초"
            self.desc = "당근의 영양분을 빼앗습니다. 치워야 합니다."
            self.is_good = False
        elif item_type == 'rock':
            self.name = "돌멩이"
            self.desc = "뿌리가 뻗는 길을 막습니다. 치워야 합니다."
            self.is_good = False
        elif item_type == 'leaf':
            self.name = "썩은 잎"
            self.desc = "병이 옮을 수 있습니다. 치워야 합니다."
            self.is_good = False

    def draw(self, screen):
        screen.blit(self.sprite, self.rect)
        if self.dragging:
            pygame.draw.rect(screen, WHITE, self.rect, 2)

class Stage1Scene:
    def __init__(self):
        game_state.timer = 24.0
        game_state.score = 0
        self.items = []
        
        for _ in range(6): self.spawn_item('seed')
        for _ in range(4): self.spawn_item('weed')
        for _ in range(4): self.spawn_item('rock')
        for _ in range(3): self.spawn_item('leaf')
            
        self.dragged_item = None
        self.bin_keep = pygame.Rect(145, 348, 182, 148)
        self.bin_trash = pygame.Rect(548, 326, 178, 170)
        self.hovered_name = "밭 준비하기"
        self.hovered_desc = "씨앗은 왼쪽 밭으로, 방해물은 오른쪽 통으로 옮기세요."
        self.stage_clear = False
        self.clear_timer = 2.0

    def spawn_item(self, itype):
        x = random.randint(100, 700 - 40)
        y = random.randint(100, 350 - 40)
        self.items.append(SortItem(itype, x, y))

    def draw_seed_bed(self, screen):
        x, y, w, h = self.bin_keep
        pygame.draw.ellipse(screen, (86, 54, 31), (x + 8, y + 103, w - 16, 34))
        pygame.draw.rect(screen, (179, 103, 50), (x + 22, y + 48, w - 44, h - 26), border_radius=14)
        pygame.draw.rect(screen, (103, 58, 34), (x + 22, y + 48, w - 44, h - 26), 4, border_radius=14)

        for i in range(8):
            by = y + 60 + i * 8
            pygame.draw.arc(screen, (118, 69, 38), (x + 26, by, w - 52, 30), 3.25, 6.0, 2)
            pygame.draw.arc(screen, (218, 138, 72), (x + 30, by + 1, w - 60, 24), 3.3, 5.9, 1)

        lip = pygame.Rect(x, y + 22, w, 54)
        pygame.draw.ellipse(screen, (221, 135, 62), lip)
        pygame.draw.ellipse(screen, (80, 47, 29), lip, 5)
        pygame.draw.ellipse(screen, (96, 54, 31), lip.inflate(-24, -16))
        pygame.draw.ellipse(screen, (61, 37, 25), lip.inflate(-50, -26))
        pygame.draw.arc(screen, (245, 167, 89), lip.inflate(-12, -10), 3.2, 6.2, 4)

    def draw_trash_zone(self, screen):
        x, y, w, h = self.bin_trash
        can_x, can_y = x + 20, y + 70
        can_w, can_h = 120, 130

        pygame.draw.ellipse(screen, (42, 43, 40), (can_x + 10, can_y + can_h - 8, can_w, 24))
        body = pygame.Rect(can_x, can_y + 26, can_w, can_h - 32)
        pygame.draw.rect(screen, (171, 176, 170), body)
        pygame.draw.rect(screen, (44, 45, 43), body, 4)
        for stripe_x in (can_x + 18, can_x + 44, can_x + 72):
            pygame.draw.line(screen, (104, 109, 105), (stripe_x, body.y + 8), (stripe_x + 3, body.bottom - 8), 4)
            pygame.draw.line(screen, (223, 225, 219), (stripe_x + 5, body.y + 6), (stripe_x + 8, body.bottom - 10), 2)

        rim = pygame.Rect(can_x - 8, can_y, can_w + 16, 40)
        pygame.draw.ellipse(screen, (220, 223, 217), rim)
        pygame.draw.ellipse(screen, (37, 38, 37), rim, 5)
        pygame.draw.ellipse(screen, (18, 19, 18), rim.inflate(-18, -12))

        lid = pygame.Rect(x + 108, y + 8, 72, 126)
        pygame.draw.ellipse(screen, (194, 198, 192), lid)
        pygame.draw.ellipse(screen, (43, 44, 42), lid, 5)
        pygame.draw.arc(screen, (235, 237, 231), lid.inflate(-12, -10), 4.7, 7.5, 3)
        pygame.draw.line(screen, (43, 44, 42), (x + 124, y + 118), (x + 140, y + 134), 5)
        pygame.draw.ellipse(screen, (67, 68, 65), (x + 146, y + 84, 18, 42), 3)

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
                        self.hovered_desc = "좋습니다. 씨앗이 제자리를 찾았습니다."
                    else:
                        game_state.score -= 80
                        self.hovered_desc = "이건 밭에 두면 당근이 자라기 어렵습니다."
                    self.items.remove(self.dragged_item)
                elif self.bin_trash.collidepoint(event.pos):
                    if not self.dragged_item.is_good:
                        game_state.score += 100
                        self.hovered_desc = "잘 치웠습니다. 흙이 한결 깨끗해졌습니다."
                    else:
                        game_state.score -= 80
                        self.hovered_desc = "씨앗까지 버리면 수확할 것이 없어집니다."
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
                        self.hovered_desc = "씨앗은 왼쪽 밭으로, 방해물은 오른쪽 통으로 옮기세요."

    def update(self, dt):
        if self.stage_clear:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                bonus = 0
                if game_state.score >= 500: bonus = 20
                elif game_state.score >= 200: bonus = 10
                elif game_state.score >= 100: bonus = 5
                
                game_state.understanding += bonus
                game_state.transition_text = f"밭 정리 완료!\n\n획득 점수: {game_state.score}점\n흙을 보는 눈이 깊어졌습니다. 이해도 +{bonus}"
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
        
        self.draw_seed_bed(screen)
        self.draw_trash_zone(screen)
        font = get_font(24)

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
                draw_bottom_bar(screen, self.dragged_item.name, "알맞은 위치로 끌어다 놓으세요.")
            else:
                draw_bottom_bar(screen, self.hovered_name, self.hovered_desc)
