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
            # 물줄기 — 반투명 리본 여러 겹 + 밝은 심줄
            ribbon = pygame.Surface((48, 56), pygame.SRCALPHA)
            for ox, a, wd in ((-2, 70, 6), (1, 120, 4), (4, 80, 5)):
                pygame.draw.line(ribbon, (150, 205, 235, a), (8 + ox, 0), (26 + ox, 46), wd)
            pygame.draw.line(ribbon, (222, 242, 252, 210), (8, 0), (26, 44), 2)
            screen.blit(ribbon, (spout_x - 8, 196))
        for d in self.drops:
            glow = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(glow, (170, 215, 240, 110), (5, 5), 5)
            screen.blit(glow, (int(d[0]) - 5, int(d[1]) - 5))
            pygame.draw.circle(screen, (226, 244, 253), (int(d[0]), int(d[1])), 2)

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
                audio.play("weed_pull")
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


# ============================================================================
# 날씨별 미니게임 — 밭 위 오버레이로 farm.interaction 에 꽂힌다.
# result 는 {"weather_bonus": {...}} 딕셔너리로 farm 이 스탯에 적용한다.
# ============================================================================

import math

class WeatherSunshine:
    """맑음 — 햇빛 모으기. 하늘에서 내려오는 햇살 구슬을 클릭해 모은다."""
    PROMPT = "떨어지는 햇살을 클릭해 모으세요"

    def __init__(self, farm):
        self.farm = farm
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.timer = 8.0
        self.collected = 0
        self.target = 8
        self.orbs = []
        self.sparkles = []
        self._spawn(4)

    def _spawn(self, n):
        for _ in range(n):
            self.orbs.append({
                "x": random.randint(PLOT.x + 30, PLOT.right - 30),
                "y": float(random.randint(PLOT.y - 40, PLOT.y - 10)),
                "speed": random.uniform(50, 100),
                "size": random.randint(10, 16),
                "pulse": random.uniform(0, 6.28),
                "alive": True,
            })

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for orb in self.orbs:
                if not orb["alive"]:
                    continue
                dx = mx - orb["x"]
                dy = my - orb["y"]
                if dx * dx + dy * dy < (orb["size"] + 8) ** 2:
                    orb["alive"] = False
                    self.collected += 1
                    audio.play("pop")
                    self.sparkles.append([orb["x"], orb["y"], 0.4])
                    if self.collected >= self.target:
                        self._resolve()
                    break

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        for orb in self.orbs:
            if orb["alive"]:
                orb["y"] += orb["speed"] * dt
                orb["pulse"] += dt * 3
                if orb["y"] > PLOT.bottom + 10:
                    orb["y"] = float(random.randint(PLOT.y - 40, PLOT.y - 10))
                    orb["x"] = random.randint(PLOT.x + 30, PLOT.right - 30)
        # 주기적으로 새 구슬 생성
        alive_count = sum(1 for o in self.orbs if o["alive"])
        if alive_count < 3 and self.collected < self.target:
            self._spawn(2)
        for s in self.sparkles:
            s[2] -= dt
        self.sparkles = [s for s in self.sparkles if s[2] > 0]
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        frac = self.collected / max(1, self.target)
        bonus = {}
        if frac >= 0.8:
            self.feedback = "햇살을 가득 모았다! 밭이 따뜻해졌다."
            self.feedback_color = (255, 230, 130)
            bonus = {"health": 6, "stress": -8}
            audio.play("success")
        elif frac >= 0.4:
            self.feedback = "어느 정도 모았다."
            self.feedback_color = (220, 205, 140)
            bonus = {"health": 3, "stress": -4}
            audio.play("page")
        else:
            self.feedback = "햇살을 많이 놓쳤다."
            self.feedback_color = (225, 175, 130)
            audio.play("page")
        self.result = {"weather_bonus": bonus}
        self.settle = 1.2

    def draw(self, screen):
        _veil(screen)
        for orb in self.orbs:
            if not orb["alive"]:
                continue
            x, y = int(orb["x"]), int(orb["y"])
            pulse = 0.85 + 0.15 * math.sin(orb["pulse"])
            r = int(orb["size"] * pulse)
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 230, 100, 50), (r * 2, r * 2), r * 2)
            pygame.draw.circle(glow, (255, 240, 150, 120), (r * 2, r * 2), r)
            screen.blit(glow, (x - r * 2, y - r * 2))
        for s in self.sparkles:
            r = int(12 * (1 - s[2] / 0.4)) + 3
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 200, int(200 * (s[2] / 0.4))), (r, r), r)
            screen.blit(surf, (int(s[0]) - r, int(s[1]) - r))
        _caption(screen, self.PROMPT if self.result is None else self.feedback,
                 None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"모은 햇살 {self.collected}/{self.target}", self.timer / 8.0)


class WeatherRain:
    """비 — 빗물 받기. 양동이를 좌우로 움직여 떨어지는 빗방울을 받는다."""
    PROMPT = "마우스를 움직여 빗물을 받으세요"

    def __init__(self, farm):
        self.farm = farm
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.timer = 8.0
        self.bucket_x = PLOT.centerx
        self.bucket_y = PLOT.bottom - 30
        self.drops = []
        self.caught = 0
        self.target = 12
        self.spawn_timer = 0
        self.splashes = []

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEMOTION:
            self.bucket_x = max(PLOT.x + 20, min(PLOT.right - 20, event.pos[0]))

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        self.spawn_timer += dt
        if self.spawn_timer > 0.25:
            self.drops.append({
                "x": random.randint(PLOT.x + 20, PLOT.right - 20),
                "y": float(PLOT.y),
                "speed": random.uniform(160, 280),
            })
            self.spawn_timer = 0
        for drop in self.drops[:]:
            drop["y"] += drop["speed"] * dt
            # 양동이 충돌 체크
            if drop["y"] >= self.bucket_y - 10 and abs(drop["x"] - self.bucket_x) < 24:
                self.caught += 1
                self.drops.remove(drop)
                audio.play("water")
                self.splashes.append([drop["x"], self.bucket_y - 5, 0.3])
                if self.caught >= self.target:
                    self._resolve()
            elif drop["y"] > PLOT.bottom + 10:
                self.drops.remove(drop)
        for s in self.splashes:
            s[2] -= dt
        self.splashes = [s for s in self.splashes if s[2] > 0]
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        frac = self.caught / max(1, self.target)
        bonus = {}
        if frac >= 0.8:
            self.feedback = "빗물을 넉넉히 모았다!"
            self.feedback_color = (150, 200, 255)
            bonus = {"moisture": 12, "drainage": -4}
            audio.play("success")
        elif frac >= 0.4:
            self.feedback = "어느 정도 모았다."
            self.feedback_color = (220, 205, 140)
            bonus = {"moisture": 6}
            audio.play("page")
        else:
            self.feedback = "빗물을 많이 흘렸다."
            self.feedback_color = (225, 175, 130)
            bonus = {"moisture": 2}
            audio.play("page")
        self.result = {"weather_bonus": bonus}
        self.settle = 1.2

    def draw(self, screen):
        _veil(screen)
        # 빗방울
        for drop in self.drops:
            x, y = int(drop["x"]), int(drop["y"])
            pygame.draw.line(screen, (150, 190, 240), (x, y), (x - 1, y + 6), 2)
        # 양동이
        bx, by = int(self.bucket_x), int(self.bucket_y)
        pygame.draw.polygon(screen, (120, 110, 90), [
            (bx - 18, by - 16), (bx + 18, by - 16),
            (bx + 14, by + 8), (bx - 14, by + 8)
        ])
        pygame.draw.polygon(screen, (150, 140, 110), [
            (bx - 16, by - 14), (bx + 16, by - 14),
            (bx + 12, by + 6), (bx - 12, by + 6)
        ])
        # 물 튀김
        for s in self.splashes:
            r = int(8 * (1 - s[2] / 0.3)) + 2
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (150, 200, 255, int(180 * (s[2] / 0.3))), (r, r), r)
            screen.blit(surf, (int(s[0]) - r, int(s[1]) - r))
        _caption(screen, self.PROMPT if self.result is None else self.feedback,
                 None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"받은 빗물 {self.caught}/{self.target}", self.timer / 8.0)


class WeatherCloudy:
    """흐림 — 구름 걷기. 구름을 드래그해서 화면 밖으로 밀어낸다."""
    PROMPT = "구름을 끌어 화면 밖으로 밀어내세요"

    def __init__(self, farm):
        self.farm = farm
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.timer = 10.0
        self.clouds = []
        self.cleared = 0
        self.target = 5
        self.dragging = None
        self.drag_offset = (0, 0)
        for _ in range(self.target):
            self.clouds.append({
                "x": random.randint(PLOT.x + 20, PLOT.right - 80),
                "y": random.randint(PLOT.y + 10, PLOT.y + 120),
                "w": random.randint(60, 100),
                "h": random.randint(30, 45),
                "alive": True,
                "drift": random.uniform(-10, 10),
            })

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for cloud in self.clouds:
                if not cloud["alive"]:
                    continue
                cr = pygame.Rect(cloud["x"], cloud["y"], cloud["w"], cloud["h"])
                if cr.collidepoint(mx, my):
                    self.dragging = cloud
                    self.drag_offset = (mx - cloud["x"], my - cloud["y"])
                    audio.play("click")
                    break
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.dragging["x"] = event.pos[0] - self.drag_offset[0]
            self.dragging["y"] = event.pos[1] - self.drag_offset[1]
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            c = self.dragging
            # 화면 밖으로 밀었는지 체크
            if c["x"] + c["w"] < PLOT.x - 10 or c["x"] > PLOT.right + 10 or c["y"] + c["h"] < PLOT.y - 20:
                c["alive"] = False
                self.cleared += 1
                audio.play("pop")
                if self.cleared >= self.target:
                    self._resolve()
            self.dragging = None

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        for c in self.clouds:
            if c["alive"] and c is not self.dragging:
                c["x"] += c["drift"] * dt
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        frac = self.cleared / max(1, self.target)
        bonus = {}
        if frac >= 0.8:
            self.feedback = "구름이 걷혔다! 햇빛이 비친다."
            self.feedback_color = (255, 240, 160)
            bonus = {"health": 5, "stress": -6}
            audio.play("success")
        elif frac >= 0.4:
            self.feedback = "구름이 좀 걷혔다."
            self.feedback_color = (220, 205, 140)
            bonus = {"health": 2, "stress": -3}
            audio.play("page")
        else:
            self.feedback = "구름이 여전히 두껍다."
            self.feedback_color = (225, 175, 130)
            audio.play("page")
        self.result = {"weather_bonus": bonus}
        self.settle = 1.2

    def draw(self, screen):
        _veil(screen)
        for c in self.clouds:
            if not c["alive"]:
                continue
            cx, cy, cw, ch = int(c["x"]), int(c["y"]), c["w"], c["h"]
            surf = pygame.Surface((cw, ch), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (210, 215, 225, 200), (0, ch // 4, cw, ch * 3 // 4))
            pygame.draw.ellipse(surf, (220, 225, 235, 220), (cw // 5, 0, cw * 3 // 5, ch * 3 // 4))
            screen.blit(surf, (cx, cy))
        _caption(screen, self.PROMPT if self.result is None else self.feedback,
                 None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"치운 구름 {self.cleared}/{self.target}", self.timer / 10.0)


class WeatherDrought:
    """가뭄 — 물길 찾기. 갈라진 땅에서 수맥 표시가 깜빡일 때 타이밍 맞춰 클릭."""
    PROMPT = "수맥이 빛날 때 재빨리 클릭하세요"

    def __init__(self, farm):
        self.farm = farm
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.timer = 10.0
        self.spots = []
        self.found = 0
        self.target = 5
        self.current_spot = 0
        for i in range(self.target):
            self.spots.append({
                "x": random.randint(PLOT.x + 50, PLOT.right - 50),
                "y": random.randint(PLOT.y + 60, PLOT.bottom - 50),
                "active": False,
                "found": False,
                "glow_timer": 0.0,
                "glow_duration": random.uniform(1.2, 2.0),
                "delay": i * 1.8 + random.uniform(0, 0.5),
            })

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for spot in self.spots:
                if not spot["found"] and spot["active"]:
                    dx = mx - spot["x"]
                    dy = my - spot["y"]
                    if dx * dx + dy * dy < 25 ** 2:
                        spot["found"] = True
                        spot["active"] = False
                        self.found += 1
                        audio.play("water")
                        if self.found >= self.target:
                            self._resolve()
                        break

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        elapsed = 10.0 - self.timer
        for spot in self.spots:
            if spot["found"]:
                continue
            if elapsed >= spot["delay"]:
                spot["active"] = True
                spot["glow_timer"] += dt
                if spot["glow_timer"] >= spot["glow_duration"]:
                    spot["active"] = False
                    # 놓쳤으면 다시 돌아옴 (딜레이 리셋)
                    spot["delay"] = elapsed + random.uniform(1.5, 2.5)
                    spot["glow_timer"] = 0.0
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        frac = self.found / max(1, self.target)
        bonus = {}
        if frac >= 0.8:
            self.feedback = "수맥을 모두 찾았다! 물길이 열렸다."
            self.feedback_color = (120, 200, 255)
            bonus = {"moisture": 15, "health": 4}
            audio.play("success")
        elif frac >= 0.4:
            self.feedback = "수맥을 몇 개 찾았다."
            self.feedback_color = (220, 205, 140)
            bonus = {"moisture": 8}
            audio.play("page")
        else:
            self.feedback = "수맥을 거의 찾지 못했다."
            self.feedback_color = (225, 175, 130)
            bonus = {"moisture": 3}
            audio.play("page")
        self.result = {"weather_bonus": bonus}
        self.settle = 1.2

    def draw(self, screen):
        _veil(screen)
        # 갈라진 땅 그리기
        for i in range(6):
            sx = PLOT.x + 30 + i * 55
            sy = PLOT.y + 40 + (i % 3) * 80
            pygame.draw.line(screen, (100, 70, 45), (sx, sy), (sx + 20, sy + 30), 2)
            pygame.draw.line(screen, (100, 70, 45), (sx + 20, sy + 30), (sx + 10, sy + 50), 1)
        for spot in self.spots:
            if spot["found"]:
                # 찾은 수맥 — 물 표시
                pygame.draw.circle(screen, (100, 180, 255, 150), (int(spot["x"]), int(spot["y"])), 12)
                pygame.draw.circle(screen, (150, 210, 255), (int(spot["x"]), int(spot["y"])), 6)
            elif spot["active"]:
                # 빛나는 수맥 — 깜빡깜빡
                glow_phase = math.sin(spot["glow_timer"] * 8) * 0.5 + 0.5
                alpha = int(100 + 155 * glow_phase)
                r = int(14 + 6 * glow_phase)
                glow_surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                pygame.draw.circle(glow_surf, (100, 180, 255, alpha), (r, r), r)
                screen.blit(glow_surf, (int(spot["x"]) - r, int(spot["y"]) - r))
        _caption(screen, self.PROMPT if self.result is None else self.feedback,
                 None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"찾은 수맥 {self.found}/{self.target}", self.timer / 10.0)


class WeatherWind:
    """강풍 — 작물 지키기. 날아오는 나뭇잎/돌을 연타 클릭해 방어한다."""
    PROMPT = "날아오는 것들을 클릭해 막으세요"

    def __init__(self, farm):
        self.farm = farm
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)
        self.timer = 8.0
        self.debris = []
        self.blocked = 0
        self.missed = 0
        self.target = 10
        self.spawn_timer = 0
        self.puffs = []

    def _spawn_debris(self):
        self.debris.append({
            "x": float(PLOT.x - 20),
            "y": float(random.randint(PLOT.y + 30, PLOT.bottom - 40)),
            "speed": random.uniform(100, 200),
            "type": random.choice(["leaf", "leaf", "stone"]),
            "alive": True,
        })

    def handle(self, event):
        if self.done or self.result is not None:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for d in self.debris:
                if not d["alive"]:
                    continue
                dx = mx - d["x"]
                dy = my - d["y"]
                if dx * dx + dy * dy < 20 ** 2:
                    d["alive"] = False
                    self.blocked += 1
                    audio.play("click")
                    self.puffs.append([d["x"], d["y"], 0.3])
                    break

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self.timer -= dt
        self.spawn_timer += dt
        if self.spawn_timer > 0.6 and len([d for d in self.debris if d["alive"]]) < 4:
            self._spawn_debris()
            self.spawn_timer = 0
        for d in self.debris[:]:
            if d["alive"]:
                d["x"] += d["speed"] * dt
                d["y"] += math.sin(d["x"] * 0.05) * 30 * dt
                if d["x"] > PLOT.right + 20:
                    d["alive"] = False
                    self.missed += 1
        for p in self.puffs:
            p[2] -= dt
        self.puffs = [p for p in self.puffs if p[2] > 0]
        if self.timer <= 0 or self.blocked + self.missed >= self.target:
            self._resolve()

    def _resolve(self):
        total = self.blocked + self.missed
        frac = self.blocked / max(1, total) if total > 0 else 0
        bonus = {}
        if frac >= 0.7:
            self.feedback = "바람을 잘 막아냈다!"
            self.feedback_color = (180, 220, 160)
            bonus = {"stress": -10, "health": 4}
            audio.play("success")
        elif frac >= 0.4:
            self.feedback = "그런대로 막았다."
            self.feedback_color = (220, 205, 140)
            bonus = {"stress": -5}
            audio.play("page")
        else:
            self.feedback = "바람에 많이 당했다."
            self.feedback_color = (225, 175, 130)
            bonus = {"stress": 5}
            audio.play("page")
        self.result = {"weather_bonus": bonus}
        self.settle = 1.2

    def draw(self, screen):
        _veil(screen)
        for d in self.debris:
            if not d["alive"]:
                continue
            x, y = int(d["x"]), int(d["y"])
            if d["type"] == "leaf":
                leaf = pygame.Surface((16, 10), pygame.SRCALPHA)
                pygame.draw.ellipse(leaf, (120, 170, 80, 200), (0, 0, 16, 10))
                screen.blit(leaf, (x - 8, y - 5))
            else:
                pygame.draw.circle(screen, (140, 130, 120), (x, y), 6)
                pygame.draw.circle(screen, (170, 160, 150), (x - 1, y - 1), 3)
        for p in self.puffs:
            r = int(10 * (1 - p[2] / 0.3)) + 3
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(s, (200, 210, 180, int(160 * (p[2] / 0.3))), (r, r), r)
            screen.blit(s, (int(p[0]) - r, int(p[1]) - r))
        _caption(screen, self.PROMPT if self.result is None else self.feedback,
                 None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"막은 횟수 {self.blocked}", self.timer / 8.0)


# 날씨 → 미니게임 클래스 매핑
WEATHER_MINIGAMES = {
    "맑음": WeatherSunshine,
    "비": WeatherRain,
    "흐림": WeatherCloudy,
    "가뭄": WeatherDrought,
    "강풍": WeatherWind,
}
