"""특별 이벤트 미니게임 — 별 잇기.

꿈결 같은 새벽, 밭 위로 별이 유난히 밝다. 아버지가 새벽을 가늠하던 북두칠성을,
순서대로 별과 별을 이어 그려 본다. 다 이으면 이해도를 얻고 밭으로 돌아간다.

'받기'(씨앗 받기)는 날씨 미니게임의 '빗물 받기'와 메커니즘이 겹쳐 폐지하고,
어디에도 없던 '순서대로 잇기' 방식의 새 미니게임으로 대체했다."""
import random
import math
import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_MUTED
from core.ui import draw_story_backdrop
from core import audio

# 북두칠성 모양 — 손잡이(1~4) → 바가지(4~7). 매 판 살짝 흔들어 똑같지 않게.
_DIPPER = [(583, 116), (505, 138), (432, 166), (368, 198),
           (300, 212), (290, 150), (360, 140)]

GOLD = (255, 226, 150)
GOLD_DIM = (210, 196, 150)


class StarConnectScene:
    DURATION = 24.0
    PROMPT = "반짝이는 다음 별을 순서대로 이어 보세요"
    HIT_R = 30

    def __init__(self):
        self.stars = [(x + random.randint(-9, 9), y + random.randint(-8, 8)) for (x, y) in _DIPPER]
        self.total = len(self.stars)
        self.idx = 0                 # 이은 별 개수
        self.timer = self.DURATION
        self.dragging = False
        self.mx, self.my = 0, 0
        self.pulse = 0.0
        self.spark = []              # 이어질 때 튀는 빛 [x, y, life]
        self.done = False
        self.finished = False
        self.end_timer = 1.8
        self.font = get_font(20)
        self.font_small = get_font(16)

    # --------------------------------------------------------------- 입력
    def _try_connect(self, pos):
        if self.idx >= self.total:
            return
        tx, ty = self.stars[self.idx]
        if (pos[0] - tx) ** 2 + (pos[1] - ty) ** 2 <= self.HIT_R ** 2:
            self.idx += 1
            self.spark.append([tx, ty, 0.5])
            if self.idx >= self.total:
                audio.play("success")
                self.done = True
            else:
                audio.play("pop")

    def handle_events(self, events):
        if self.done:
            return
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.dragging = True
                self.mx, self.my = event.pos
                self._try_connect(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self.mx, self.my = event.pos
                if self.dragging:
                    self._try_connect(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False

    # --------------------------------------------------------------- 진행
    def update(self, dt):
        self.pulse = (self.pulse + dt * 3.0) % (2 * math.pi)
        for s in self.spark:
            s[2] -= dt
        self.spark = [s for s in self.spark if s[2] > 0]
        if self.done:
            self.end_timer -= dt
            if self.end_timer <= 0:
                self._finish()
            return
        self.timer -= dt
        if self.timer <= 0:
            self.timer = 0
            self.done = True

    def _finish(self):
        if self.finished:
            return
        self.finished = True
        n = self.idx
        frac = n / self.total
        bonus = 18 if frac >= 0.99 else 12 if frac >= 0.7 else 7 if frac >= 0.4 else 3
        game_state.understanding += bonus
        game_state.transition_text = (
            "흩어진 별을 이어, 아버지가 보던 새벽 하늘을 그렸다.\n\n"
            f"이은 별: {n}/{self.total}    이해도 +{bonus}\n"
            "'저 별이 기울면 일어날 때란다.' 아버지의 말이 떠올랐다."
        )
        game_state.transition_next = game_state.return_scene
        game_state.is_clear_transition = True
        game_state.current_scene = "transition"

    # --------------------------------------------------------------- 그리기
    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")

        # 이미 이은 선 (별과 별 사이) — 은은한 금빛 + 글로우
        for i in range(1, self.idx):
            a, b = self.stars[i - 1], self.stars[i]
            glow = pygame.Surface((800, 600), pygame.SRCALPHA)
            pygame.draw.line(glow, (255, 226, 150, 70), a, b, 7)
            screen.blit(glow, (0, 0))
            pygame.draw.line(screen, GOLD, a, b, 2)

        # 다음 별로 가는 안내선 (마지막으로 이은 별 → 다음 별), 손가락도 따라옴
        if 0 < self.idx < self.total:
            last = self.stars[self.idx - 1]
            nxt = self.stars[self.idx]
            self._dotted(screen, last, nxt, (180, 180, 210, 110))
        if self.dragging and self.idx < self.total:
            last = self.stars[self.idx - 1] if self.idx > 0 else (self.mx, self.my)
            pygame.draw.line(screen, (255, 240, 200), last, (self.mx, self.my), 1)

        # 별들
        for i, (x, y) in enumerate(self.stars):
            if i < self.idx:                              # 이은 별 — 밝은 금빛
                self._star(screen, x, y, 6, GOLD, halo=22)
            elif i == self.idx:                           # 다음 별 — 맥동하는 신호
                p = 0.5 + 0.5 * math.sin(self.pulse)
                r = int(20 + 8 * p)
                ring = pygame.Surface((r * 2 + 6, r * 2 + 6), pygame.SRCALPHA)
                pygame.draw.circle(ring, (255, 236, 170, int(60 + 90 * p)),
                                   (r + 3, r + 3), r, 2)
                screen.blit(ring, (x - r - 3, y - r - 3))
                self._star(screen, x, y, 6, (255, 240, 190), halo=int(18 + 10 * p))
                num = self.font_small.render(str(i + 1), True, (255, 244, 210))
                screen.blit(num, (x - num.get_width() // 2, y + 14))
            else:                                         # 아직 — 옅은 별
                self._star(screen, x, y, 4, (170, 178, 205), halo=8)

        # 이어질 때 튀는 빛
        for sx, sy, life in self.spark:
            r = int(26 * (1 - life / 0.5)) + 4
            su = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(su, (255, 240, 190, int(180 * (life / 0.5))), (r, r), r, 2)
            screen.blit(su, (sx - r, sy - r))

        self._hud(screen)

    def _star(self, screen, x, y, size, color, halo=0):
        if halo:
            h = pygame.Surface((halo * 2, halo * 2), pygame.SRCALPHA)
            for r in range(halo, 0, -2):
                a = int(70 * (1 - r / halo))
                pygame.draw.circle(h, (color[0], color[1], color[2], a), (halo, halo), r)
            screen.blit(h, (x - halo, y - halo))
        pygame.draw.circle(screen, color, (x, y), size)
        pygame.draw.circle(screen, (255, 255, 255), (x, y), max(1, size - 3))

    def _dotted(self, screen, a, b, color):
        dx, dy = b[0] - a[0], b[1] - a[1]
        dist = max(1.0, math.hypot(dx, dy))
        steps = int(dist // 12)
        layer = pygame.Surface((800, 600), pygame.SRCALPHA)
        for k in range(1, steps):
            t = k / steps
            pygame.draw.circle(layer, color, (int(a[0] + dx * t), int(a[1] + dy * t)), 2)
        screen.blit(layer, (0, 0))

    def _hud(self, screen):
        # 진행 + 남은 시간 (밤하늘에 어울리게 최소한으로)
        prog = self.font.render(f"이은 별  {self.idx}/{self.total}", True, (236, 230, 206))
        screen.blit(prog, (28, 26))
        w = 220
        pygame.draw.rect(screen, (40, 44, 60), (28, 56, w, 6), border_radius=3)
        pygame.draw.rect(screen, (210, 190, 120),
                         (28, 56, int(w * max(0.0, self.timer / self.DURATION)), 6), border_radius=3)
        if self.done:
            msg = "다 이었다…" if self.idx >= self.total else "별이 흐려진다…"
            tip = self.font.render(msg, True, GOLD_DIM)
        else:
            tip = self.font.render(self.PROMPT, True, TEXT_MUTED)
        screen.blit(tip, (400 - tip.get_width() // 2, 556))
