import pygame
import random
from core.game_state import game_state
from core.assets import *
from core import audio
from core.ui import draw_top_bar, draw_bottom_bar, draw_light_panel, draw_wood_panel, mix_color

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
            self.desc = "병을 옮길 수 있습니다. 치워야 합니다."
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
        """왼쪽 '밭' — 흙 담긴 테라코타 화분 (씨앗을 여기로)."""
        x, y, w, h = self.bin_keep
        cx = x + w // 2
        rim_y, bot_y = 402, 496
        th, bh = 78, 54
        clay = (188, 112, 64); clay_dk = (150, 84, 46); clay_hi = (220, 150, 96)
        # 바닥 그림자
        pygame.draw.ellipse(screen, (40, 28, 18), (cx - bh - 8, bot_y - 12, (bh + 8) * 2, 26))
        # 몸통(사다리꼴)
        body = [(cx - th, rim_y), (cx + th, rim_y), (cx + bh, bot_y), (cx - bh, bot_y)]
        pygame.draw.polygon(screen, clay, body)
        pygame.draw.polygon(screen, clay_hi, [(cx - th, rim_y), (cx - th + 15, rim_y), (cx - bh + 11, bot_y), (cx - bh, bot_y)])      # 왼쪽 빛
        pygame.draw.polygon(screen, clay_dk, [(cx + th - 17, rim_y), (cx + th, rim_y), (cx + bh, bot_y), (cx + bh - 13, bot_y)])      # 오른쪽 그늘
        pygame.draw.polygon(screen, mix_color(clay_dk, BLACK, 0.2), body, 3)
        # 윗 턱(림)
        lip = pygame.Rect(cx - th - 8, rim_y - 18, (th + 8) * 2, 36)
        pygame.draw.ellipse(screen, clay_hi, lip)
        pygame.draw.ellipse(screen, mix_color(clay_dk, BLACK, 0.2), lip, 3)
        # 담긴 흙
        inner = lip.inflate(-26, -14)
        pygame.draw.ellipse(screen, (98, 62, 38), inner)
        pygame.draw.ellipse(screen, (66, 42, 26), inner.inflate(-30, -8))
        pygame.draw.arc(screen, mix_color(clay_hi, WHITE, 0.4), lip.inflate(-12, -8), 3.3, 6.1, 3)   # 림 광택

    def draw_trash_zone(self, screen):
        """오른쪽 '통' — 뚜껑이 비스듬히 열린 양철 쓰레기통 (방해물을 여기로)."""
        x, y, w, h = self.bin_trash
        cx = x + w // 2
        top_y, bot_y = 392, 492
        th, bh = 56, 48
        met = (170, 174, 170); met_dk = (102, 106, 102); met_hi = (214, 218, 212)
        # 바닥 그림자
        pygame.draw.ellipse(screen, (38, 30, 24), (cx - bh - 8, bot_y - 12, (bh + 8) * 2, 26))
        # 몸통(살짝 좁아지는 원통)
        body = [(cx - th, top_y), (cx + th, top_y), (cx + bh, bot_y), (cx - bh, bot_y)]
        pygame.draw.polygon(screen, met, body)
        # 원통 음영 (왼쪽 밝음 → 오른쪽 어둠)
        for i in range(-4, 5):
            col = mix_color(met_hi, met_dk, (i + 4) / 8)
            pygame.draw.line(screen, col, (cx + int(i / 4 * th), top_y + 6), (cx + int(i / 4 * bh), bot_y - 4), 4)
        # 가로 골(2줄)
        def half_at(ry):
            f = (ry - top_y) / (bot_y - top_y)
            return th + (bh - th) * f
        for ry in (top_y + 26, bot_y - 26):
            hw = half_at(ry)
            pygame.draw.line(screen, mix_color(met_dk, BLACK, 0.15), (cx - hw + 5, ry), (cx + hw - 5, ry), 3)
            pygame.draw.line(screen, met_hi, (cx - hw + 5, ry + 4), (cx + hw - 5, ry + 4), 1)
        pygame.draw.polygon(screen, (56, 58, 56), body, 3)
        # 림 + 어두운 입구
        rim = pygame.Rect(cx - th - 6, top_y - 15, (th + 6) * 2, 30)
        pygame.draw.ellipse(screen, met_hi, rim)
        pygame.draw.ellipse(screen, (56, 58, 56), rim, 3)
        pygame.draw.ellipse(screen, (40, 42, 41), rim.inflate(-14, -8))
        # 비스듬히 열린 뚜껑 (오른쪽 위로 들림)
        lid_surf = pygame.Surface((130, 42), pygame.SRCALPHA)
        pygame.draw.ellipse(lid_surf, met, (0, 0, 130, 42))
        pygame.draw.ellipse(lid_surf, met_hi, (6, 4, 118, 16))
        pygame.draw.ellipse(lid_surf, (56, 58, 56), (0, 0, 130, 42), 3)
        pygame.draw.circle(lid_surf, met_hi, (65, 21), 8)
        pygame.draw.circle(lid_surf, (56, 58, 56), (65, 21), 8, 2)
        lid_rot = pygame.transform.rotate(lid_surf, 38)
        lr = lid_rot.get_rect(center=(cx + 66, top_y - 30))
        screen.blit(lid_rot, lr)
        # 경첩
        pygame.draw.line(screen, (62, 64, 62), (cx + th - 8, top_y - 3), (cx + 42, top_y - 16), 5)

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
                        audio.play("soil")
                        self.hovered_desc = "좋습니다. 씨앗이 제자리를 찾았습니다."
                    else:
                        game_state.score -= 80
                        audio.play("break")
                        self.hovered_desc = "이건 밭에 두면 당근이 자라기 어렵습니다."
                    self.items.remove(self.dragged_item)
                elif self.bin_trash.collidepoint(event.pos):
                    if not self.dragged_item.is_good:
                        game_state.score += 100
                        audio.play("soil")
                        self.hovered_desc = "잘 치웠습니다. 흙이 한결 깨끗해졌습니다."
                    else:
                        game_state.score -= 80
                        audio.play("break")
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
