import pygame
import random
from core.game_state import game_state
from core.assets import *
from core import audio
from core import i18n
from core.ui import draw_top_bar, draw_bottom_bar, draw_light_panel, draw_wood_panel, mix_color
from core.crops import current_crop, swap_crop_word

class SortItem:
    def __init__(self, item_type, x, y):
        self.item_type = item_type
        self.x = x
        self.y = y
        self.sprite = sprites[item_type]
        # 판정 상자는 스프라이트 실제 크기로 — 높이에 너비를 쓰면 납작한 스프라이트가
        # 아래로 10px 넘게 유령 판정을 가진다
        self.rect = pygame.Rect(x, y, self.sprite.get_width(), self.sprite.get_height())
        self.dragging = False
        
        if item_type == 'seed':
            crop = game_state.crop
            if crop == "apple":
                self.name = "사과 씨앗"
                self.desc = "밭으로 보내야 할 사과나무 씨앗입니다."
            elif crop == "potato":
                self.name = "씨감자"
                self.desc = "밭으로 보내야 할 씨감자입니다."
            elif crop == "rice":
                self.name = "볍씨"
                self.desc = "밭으로 보내야 할 볍씨 낟알입니다."
            else:
                self.name = "당근 씨앗"
                self.desc = "밭으로 보내야 할 당근 씨앗입니다."
            self.is_good = True
        elif item_type == 'weed':
            self.name = "잡초"
            # 정본(당근) 유지 — 표시 시점 tnar 번역·치환 (미리 치환하면 EN 미번역)
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
        if self.item_type == 'seed':
            draw_crop_seed(screen, self.rect.centerx, self.rect.centery, game_state.crop)
        else:
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
        # 화면 중심(x=400) 기준 좌우 대칭으로 배치 — 한쪽으로 쏠리지 않게.
        self.bin_keep = pygame.Rect(114, 366, 192, 146)    # 중심 x=210
        self.bin_trash = pygame.Rect(494, 366, 192, 146)   # 중심 x=590
        self.hovered_name = "밭 준비하기"
        self.hovered_desc = "씨앗은 왼쪽 밭으로, 방해물은 오른쪽 통으로 옮기세요."
        self.stage_clear = False
        self.clear_timer = 2.0

    def spawn_item(self, itype):
        # 서로 겹쳐 태어나지 않게 몇 번 자리를 다시 굴린다 (완벽할 필요는 없고 덜 겹치면 됨)
        x, y = 100, 100
        for _ in range(24):
            x = random.randint(100, 700 - 40)
            y = random.randint(100, 350 - 40)
            if all((x - it.rect.x) ** 2 + (y - it.rect.y) ** 2 > 44 * 44 for it in self.items):
                break
        self.items.append(SortItem(itype, x, y))

    def draw_seed_bed(self, screen):
        """왼쪽 — 씨앗을 담는 따뜻한 색 통(sprites['basket']). 오른쪽 통과 같은 모양."""
        self._blit_bin(screen, sprites['basket'], self.bin_keep)

    def draw_trash_zone(self, screen):
        """오른쪽 — 방해물을 버리는 픽셀 아트 회색 금속통(sprites['trashcan'])."""
        self._blit_bin(screen, sprites['trashcan'], self.bin_trash)

    def _blit_bin(self, screen, spr, zone):
        """두 통을 같은 방식·같은 바닥선으로 그려 통일감을 준다.
        바닥선 486 — 500이면 하단 바(y≈500~)가 통 아래 14px과 그림자를 가렸다."""
        cx = zone.x + zone.width // 2
        w, h = spr.get_width(), spr.get_height()
        shadow = pygame.Surface((w, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (30, 22, 16, 120), (0, 0, w, 22))
        from core.pixelfx import pixelate
        screen.blit(pixelate(shadow, 3, smooth=False), (cx - w // 2, 476))
        screen.blit(spr, (cx - w // 2, 486 - h))

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
                        game_state.score = max(0, game_state.score - 80)
                        audio.play("break")
                        self.hovered_desc = "이건 밭에 두면 당근이 자라기 어렵습니다."
                    self.items.remove(self.dragged_item)
                elif self.bin_trash.collidepoint(event.pos):
                    if not self.dragged_item.is_good:
                        game_state.score += 100
                        audio.play("soil")
                        self.hovered_desc = "잘 치웠습니다. 흙이 한결 깨끗해졌습니다."
                    else:
                        game_state.score = max(0, game_state.score - 80)
                        audio.play("break")
                        self.hovered_desc = "씨앗까지 버리면 수확할 것이 없어집니다."
                    self.items.remove(self.dragged_item)
                self.dragged_item = None
            elif event.type == pygame.MOUSEMOTION:
                if self.dragged_item:
                    self.dragged_item.rect.x += event.rel[0]
                    self.dragged_item.rect.y += event.rel[1]
                    # 상/하단 바 밑으로 끌고 들어가 안 보이는 채 버려지지 않게 화면 안으로 클램프
                    self.dragged_item.rect.clamp_ip(pygame.Rect(8, 62, 784, 438))
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
                game_state.transition_text = i18n.tf("밭 정리 완료!\n\n획득 점수: {score}점\n흙을 보는 눈이 깊어졌습니다. 이해도 +{bonus}", score=game_state.score, bonus=bonus)
                game_state.transition_next = game_state.return_scene
                game_state.is_clear_transition = True

                from core import behavior
                behavior.log("minigame", stage="stage1",
                             score=game_state.score,
                             norm=max(0.0, min(1.0, game_state.score / 500.0)))

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
            done_msg = "스테이지 완료!" if not self.items else "시간 초과…"
            clear_text = font.render(done_msg, True, (200, 100, 0))
            panel = pygame.Rect(400 - 100, 300 - 30, 200, 60)
            draw_wood_panel(screen, panel)
            screen.blit(clear_text, (400 - clear_text.get_width()//2, 300 - clear_text.get_height()//2))
            draw_bottom_bar(screen, "결과", i18n.tf("얻은 점수: {score}", score=game_state.score))
        else:
            ck = game_state.crop
            if self.dragged_item:
                draw_bottom_bar(screen, i18n.tnar(self.dragged_item.name, crop_key=ck),
                                "알맞은 위치로 끌어다 놓으세요.")
            else:
                draw_bottom_bar(screen, i18n.tnar(self.hovered_name, crop_key=ck),
                                i18n.tnar(self.hovered_desc, crop_key=ck))
