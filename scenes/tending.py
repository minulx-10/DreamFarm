"""밭일 손맛 인터랙션 — 씬 전환 없이 farm 위에 오버레이로 뜨는 즉석 행위들.
각 인터랙션은 farm 상태를 읽어 셋업하고, 플레이어의 실행이 결과 품질(result)을 가른다.
farm 은 result 를 받아 기존 apply_action 파이프라인으로 스탯을 적용한다.

매번 똑같지 않도록 개수·위치·속도·밴드에 소소한 변형을 둔다."""
import random
import pygame
from core.assets import sprites, get_font
from core import audio

PLOT = pygame.Rect(44, 140, 362, 318)


def _font(sz):
    return get_font(sz)


class WaterPour:
    """꾹 눌러 직접 물을 붓는다. 초록 '적정'에서 떼면 알맞게, 넘기면 과습(실패)."""
    PER_LEVEL = 0.7
    GAUGE_MAX = 112.0

    PROMPT = "꾹 눌러 물을 붓고, 초록 칸에서 손을 떼세요"

    def __init__(self, farm):
        self.farm = farm
        m = farm.moisture
        self.level = 0.0
        self.pouring = False
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.drops = []
        self.pour_played = False
        self.fill_rate = 55.0 * random.uniform(0.9, 1.14)   # 변형: 물줄기 세기

        def lvl_for(target):
            return max(0.0, (target - m) / self.PER_LEVEL)
        self.good_low = lvl_for(38)
        self.good_high = lvl_for(72)
        self.overflow = lvl_for(78)
        if self.good_high <= self.good_low:
            self.good_high = self.good_low + 6

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pouring = True
            if not self.pour_played:
                audio.play("water")
                self.pour_played = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.pouring:
            self.pouring = False
            self._resolve()

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        if self.pouring:
            self.level += self.fill_rate * dt
            sx = PLOT.x + 150 + 70
            self.drops.append([sx, 210.0, 40.0 + random.uniform(-12, 12), 120.0])
            if self.level >= self.GAUGE_MAX:
                self.pouring = False
                self._resolve()
        for d in self.drops:
            d[0] += d[2] * dt
            d[1] += d[3] * dt
        self.drops = [d for d in self.drops if d[1] < 430]

    def _resolve(self):
        add = self.level * self.PER_LEVEL
        if self.level > self.overflow:
            q = "over"; self.feedback = "너무 많아! 물이 흥건하다."; self.feedback_color = (235, 120, 90); audio.play("break")
        elif self.level < self.good_low:
            q = "under"; self.feedback = "조금 모자란 듯…"; self.feedback_color = (220, 205, 140); audio.play("page")
        else:
            q = "good"; self.feedback = "딱 알맞게 적셨다!"; self.feedback_color = (150, 230, 150); audio.play("success")
        self.result = {"quality": q, "moisture_add": add}
        self.settle = 1.1

    def draw(self, screen):
        _veil(screen)
        can = sprites["watering_can"]
        tilt = 28 + (22 if self.pouring else 0)
        rot = pygame.transform.rotate(can, tilt)
        screen.blit(rot, (PLOT.x + 150 - rot.get_width() // 2, 150))

        spout_x = PLOT.x + 150 + 64
        if self.pouring:
            pygame.draw.line(screen, (150, 205, 235), (spout_x, 196), (spout_x + 18, 240), 3)
        for d in self.drops:
            pygame.draw.circle(screen, (170, 215, 240), (int(d[0]), int(d[1])), 3)
            pygame.draw.circle(screen, (210, 238, 252), (int(d[0]), int(d[1])), 1)

        wet = min(1.0, self.level / max(1.0, self.overflow))
        if wet > 0:
            for (cx, cy) in self.farm.crop_positions():
                if self.level <= self.overflow:
                    col = (90, 150, 190, int(70 * wet))
                else:
                    col = (70, 110, 200, 150)
                puddle = pygame.Surface((54, 18), pygame.SRCALPHA)
                pygame.draw.ellipse(puddle, col, (0, 0, 54, 18))
                screen.blit(puddle, (cx - 27, cy + 20))

        # 세로 게이지
        gx, gtop, gh, gw = PLOT.right - 26, 178, 252, 18
        gbot = gtop + gh
        pygame.draw.rect(screen, (40, 34, 28), (gx - 2, gtop - 2, gw + 4, gh + 4), border_radius=5)
        pygame.draw.rect(screen, (24, 30, 36), (gx, gtop, gw, gh), border_radius=4)

        def y_for(lv):
            return gbot - min(lv, self.GAUGE_MAX) / self.GAUGE_MAX * gh
        pygame.draw.rect(screen, (70, 150, 80), (gx, y_for(self.overflow), gw, y_for(self.good_low) - y_for(self.overflow)))
        sweet = y_for(self.good_high)
        pygame.draw.rect(screen, (180, 240, 170), (gx, sweet - 1, gw, 2))
        pygame.draw.rect(screen, (150, 60, 55), (gx, y_for(self.GAUGE_MAX), gw, y_for(self.overflow) - y_for(self.GAUGE_MAX)))
        cur_y = y_for(self.level)
        pygame.draw.rect(screen, (90, 170, 220), (gx, cur_y, gw, gbot - cur_y), border_radius=4)
        pygame.draw.rect(screen, (210, 235, 250), (gx, cur_y, gw, 3))
        pygame.draw.rect(screen, (90, 78, 60), (gx, gtop, gw, gh), 2, border_radius=4)

        _caption(screen, self.PROMPT if self.result is None else self.feedback,
                 None if self.result is None else self.feedback_color,
                 hot=(self.result is None and self.pouring))


class WeedPull:
    """잡초를 잡고 쭉 뽑아낸다. 뿌리째 끌어내야(드래그 거리) 뽑힌다 — 많이 걷어낼수록 좋다."""
    PROMPT = "잡초를 잡고 쭉 끌어내 뽑으세요"

    def __init__(self, farm):
        self.farm = farm
        n = min(6, max(3, farm.weeds // 11)) + random.randint(0, 1)   # 변형: 개수
        self.items = []
        for _ in range(n):
            self.items.append({
                "x": random.randint(PLOT.x + 40, PLOT.right - 56),
                "y": random.randint(PLOT.y + 60, PLOT.bottom - 64),
                "ox": 0.0, "oy": 0.0, "pulled": False,
                "strength": random.randint(24, 42),   # 변형: 뿌리 깊이(필요 드래그)
            })
        self.total = len(self.items)
        self.grabbed = None
        self.timer = 6.5
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.puffs = []

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for w in self.items:
                if not w["pulled"] and abs(event.pos[0] - w["x"]) < 22 and abs(event.pos[1] - w["y"]) < 28:
                    self.grabbed = w
                    break
        elif event.type == pygame.MOUSEMOTION and self.grabbed is not None:
            self.grabbed["ox"] = event.pos[0] - self.grabbed["x"]
            self.grabbed["oy"] = event.pos[1] - self.grabbed["y"]
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.grabbed is not None:
            w = self.grabbed
            dist = (w["ox"] ** 2 + w["oy"] ** 2) ** 0.5
            if dist >= w["strength"]:
                w["pulled"] = True
                audio.play("soil")
                self.puffs.append([w["x"], w["y"] + 12, 0.45])
            else:
                w["ox"] = w["oy"] = 0.0   # 덜 뽑힘 → 도로 박힘
            self.grabbed = None
            if all(x["pulled"] for x in self.items):
                self._resolve()

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        for p in self.puffs:
            p[2] -= dt
        self.puffs = [p for p in self.puffs if p[2] > 0]
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        cleared = sum(1 for w in self.items if w["pulled"])
        frac = cleared / max(1, self.total)
        if frac >= 0.85:
            self.feedback = "잡초를 말끔히 걷어냈다!"; self.feedback_color = (150, 230, 150); audio.play("success")
        elif frac >= 0.45:
            self.feedback = "그런대로 정리했다."; self.feedback_color = (220, 205, 140); audio.play("page")
        else:
            self.feedback = "손이 더뎠다. 잡초가 남았다."; self.feedback_color = (225, 175, 130); audio.play("page")
        self.result = {"quality": "weed", "cleared_frac": frac}
        self.settle = 1.0

    def draw(self, screen):
        _veil(screen)
        wsp = sprites["weed"]
        for w in self.items:
            if w["pulled"]:
                continue
            ox, oy = int(w["ox"]), int(w["oy"])
            gx2, gy2 = w["x"] + ox, w["y"] + oy
            # 대상 표시 — 발밑에 옅은 빛 (이걸 뽑으라는 신호)
            glow = pygame.Surface((46, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 236, 165, 80), (0, 0, 46, 24))
            pygame.draw.ellipse(glow, (255, 250, 210, 120), (9, 6, 28, 12))
            screen.blit(glow, (gx2 - 23, gy2 + 6))
            # 뿌리에서 늘어나는 줄기 표시
            if self.grabbed is w and (ox or oy):
                pygame.draw.line(screen, (96, 132, 70), (w["x"], w["y"] + 10), (w["x"] + ox, w["y"] + oy), 3)
            screen.blit(wsp, (gx2 - wsp.get_width() // 2, gy2 - wsp.get_height() // 2))
        for p in self.puffs:
            r = int(14 * (1 - p[2] / 0.45)) + 4
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (150, 110, 70, int(150 * (p[2] / 0.45))), (r, r), r)
            screen.blit(s, (p[0] - r, p[1] - r))

        remain = sum(1 for w in self.items if not w["pulled"])
        cap = self.PROMPT if self.result is None else self.feedback
        _caption(screen, cap, None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"남은 잡초 {remain}", self.timer / 6.5)


class PestTap:
    """잎 사이를 기어다니는 해충을 빠르게 잡는다. 움직이니 놓치기 쉽다."""
    PROMPT = "잎의 벌레를 빠르게 잡으세요"

    def __init__(self, farm):
        self.farm = farm
        n = min(8, max(4, farm.pests // 7)) + random.randint(0, 1)   # 변형: 개수
        self.bugs = []
        for _ in range(n):
            sp = random.uniform(40, 95)        # 변형: 속도
            ang = random.uniform(0, 6.283)
            self.bugs.append({
                "x": float(random.randint(PLOT.x + 40, PLOT.right - 50)),
                "y": float(random.randint(PLOT.y + 56, PLOT.bottom - 56)),
                "vx": sp * pygame.math.Vector2(1, 0).rotate_rad(ang).x,
                "vy": sp * pygame.math.Vector2(1, 0).rotate_rad(ang).y,
                "dead": False,
            })
        self.total = len(self.bugs)
        self.timer = 6.0
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.puffs = []

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in self.bugs:
                if not b["dead"] and abs(event.pos[0] - b["x"]) < 20 and abs(event.pos[1] - b["y"]) < 20:
                    b["dead"] = True
                    audio.play("click")
                    self.puffs.append([b["x"], b["y"], 0.35])
                    break
            if all(b["dead"] for b in self.bugs):
                self._resolve()

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        for b in self.bugs:
            if b["dead"]:
                continue
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < PLOT.x + 36 or b["x"] > PLOT.right - 40:
                b["vx"] *= -1
            if b["y"] < PLOT.y + 50 or b["y"] > PLOT.bottom - 50:
                b["vy"] *= -1
        for p in self.puffs:
            p[2] -= dt
        self.puffs = [p for p in self.puffs if p[2] > 0]
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        killed = sum(1 for b in self.bugs if b["dead"])
        frac = killed / max(1, self.total)
        if frac >= 0.85:
            self.feedback = "벌레를 거의 다 잡았다!"; self.feedback_color = (150, 230, 150); audio.play("success")
        elif frac >= 0.45:
            self.feedback = "절반쯤 잡았다."; self.feedback_color = (220, 205, 140); audio.play("page")
        else:
            self.feedback = "놓친 벌레가 많다."; self.feedback_color = (225, 175, 130); audio.play("page")
        self.result = {"quality": "pest", "cleared_frac": frac}
        self.settle = 1.0

    def draw(self, screen):
        _veil(screen)
        bsp = sprites["bug"]
        for b in self.bugs:
            if b["dead"]:
                continue
            bx, by = int(b["x"]), int(b["y"])
            # 조준 고리 — 이 벌레를 잡으라는 신호 (움직여도 따라다님)
            ring = pygame.Surface((36, 36), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 90, 60, 70), (18, 18), 16)        # 옅은 채움
            pygame.draw.circle(ring, (255, 140, 95, 210), (18, 18), 15, 3)   # 또렷한 테두리
            screen.blit(ring, (bx - 18, by - 18))
            screen.blit(bsp, (bx - bsp.get_width() // 2, by - bsp.get_height() // 2))
        for p in self.puffs:
            r = int(10 * (1 - p[2] / 0.35)) + 3
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (210, 220, 120, int(180 * (p[2] / 0.35))), (r, r), r)
            screen.blit(s, (p[0] - r, p[1] - r))

        remain = sum(1 for b in self.bugs if not b["dead"])
        cap = self.PROMPT if self.result is None else self.feedback
        _caption(screen, cap, None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"남은 벌레 {remain}", self.timer / 6.0)


# ---- 공통 그리기 헬퍼 ----

def _veil(screen):
    veil = pygame.Surface((800, 600), pygame.SRCALPHA)
    veil.fill((10, 14, 22, 70))
    screen.blit(veil, (0, 0))


def _caption(screen, text, color=None, hot=False):
    if color is None:
        color = (255, 235, 150) if hot else (236, 228, 206)
    f = _font(18)
    t = f.render(text, True, color)
    screen.blit(t, (PLOT.centerx - t.get_width() // 2, 468))


def _counter(screen, text, time_frac):
    f = _font(15)
    t = f.render(text, True, (224, 214, 188))
    screen.blit(t, (PLOT.x + 6, PLOT.y + 6))
    # 남은 시간 바
    w = 120
    pygame.draw.rect(screen, (40, 34, 28), (PLOT.right - w - 8, PLOT.y + 8, w, 6), border_radius=3)
    pygame.draw.rect(screen, (210, 180, 90), (PLOT.right - w - 8, PLOT.y + 8, int(w * max(0.0, min(1.0, time_frac))), 6), border_radius=3)
