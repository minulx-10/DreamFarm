import pygame
import random
import math
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

    def _build_barrel(self):
        """방해물을 버리는 나무 거름통 — 테라코타 화분과 어울리는 농가 소품.
        정적 그림이라 서피스에 한 번만 그려 캐시한다."""
        W, H = 176, 138
        surf = pygame.Surface((W, H), pygame.SRCALPHA)
        lcx = W // 2
        top_y, bot_y = 26, 124
        span = bot_y - top_y
        top_hw, mid_hw, bot_hw = 52, 65, 47
        wood = (150, 100, 58); wood_dk = (96, 62, 36); wood_hi = (198, 144, 92)
        hoop = (120, 92, 70); hoop_hi = (188, 158, 126); hoop_dk = (64, 46, 34)

        def hw(ry):
            f = (ry - top_y) / span
            bulge = math.sin(f * math.pi)                      # 0..1..0 (배부른 곡선)
            return (top_hw + (bot_hw - top_hw) * f) + (mid_hw - (top_hw + bot_hw) / 2) * bulge

        # 몸통 채움 + 둥근 곡면 음영 (세로 1px 컬럼, 왼쪽이 약간 밝게)
        maxhw = int(mid_hw) + 1
        rows = list(range(top_y, bot_y + 1))
        for px in range(-maxhw, maxhw + 1):
            fr = (px + maxhw) / (2 * maxhw)
            shade = min(1.0, abs(fr - 0.40) * 1.75)
            col = mix_color(wood_hi, wood_dk, shade)
            inside = [ry for ry in rows if hw(ry) >= abs(px)]
            if inside:
                pygame.draw.line(surf, col, (lcx + px, inside[0]), (lcx + px, inside[-1]))

        # 세로 판자 이음새
        for s in (-2, -1, 0, 1, 2):
            seam = [(lcx + s * 24 * (hw(ry) / mid_hw), ry)
                    for ry in range(top_y + 6, bot_y - 2, 3) if abs(s * 24) < hw(ry) - 3]
            if len(seam) > 1:
                pygame.draw.lines(surf, mix_color(wood_dk, BLACK, 0.12), False, seam, 1)

        # 금속 테(후프) 2줄 — 통 곡률 따라 감긴 띠
        for ry in (top_y + 22, bot_y - 16):
            w_ = hw(ry)
            band = pygame.Rect(int(lcx - w_), ry - 6, int(w_ * 2), 13)
            pygame.draw.ellipse(surf, hoop, band)
            pygame.draw.ellipse(surf, hoop_hi, (band.x + 4, band.y + 2, band.w - 8, 4))
            pygame.draw.ellipse(surf, hoop_dk, band, 1)

        # 열린 윗면 — 나무 림 + 어두운 입구
        rim = pygame.Rect(int(lcx - top_hw), top_y - 14, int(top_hw * 2), 28)
        pygame.draw.ellipse(surf, wood, rim)
        pygame.draw.ellipse(surf, wood_hi, (rim.x + 3, rim.y + 2, rim.w - 6, 9))
        inner = rim.inflate(-16, -9)
        pygame.draw.ellipse(surf, (54, 38, 28), inner)
        pygame.draw.ellipse(surf, (34, 24, 18), inner.inflate(-22, -7))
        pygame.draw.ellipse(surf, wood_dk, rim, 2)
        return surf

    def draw_trash_zone(self, screen):
        """오른쪽 '통' — 방해물을 여기로. 나무 거름통."""
        if not hasattr(self, "_barrel"):
            self._barrel = self._build_barrel()
        cx = self.bin_trash.x + self.bin_trash.width // 2
        pygame.draw.ellipse(screen, (38, 28, 20), (cx - 70, 486, 140, 24))   # 바닥 그림자
        screen.blit(self._barrel, (cx - self._barrel.get_width() // 2, 372))

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
