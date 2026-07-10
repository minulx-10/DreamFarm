"""밭일 손맛 인터랙션 — 씬 전환 없이 farm 위에 오버레이로 뜨는 즉석 행위들.
각 인터랙션은 farm 상태를 읽어 셋업하고, 플레이어의 실행이 결과 품질(result)을 가른다.
farm 은 result 를 받아 기존 apply_action 파이프라인으로 스탯을 적용한다.

매번 똑같지 않도록 개수·위치·속도·밴드에 소소한 변형을 둔다."""
import random
import pygame
from core.assets import sprites, get_font
from core.game_state import game_state
from core import audio

PLOT = pygame.Rect(44, 140, 362, 318)


def _font(sz):
    return get_font(sz)


class MiniGameBase:
    """밭일/날씨 미니게임의 공통 상태 및 수명주기(Settle)를 정의하는 부모 클래스."""
    def __init__(self, farm):
        self.farm = farm
        self.done = False
        self.result = None
        self.settle = 0.0
        self.feedback = ""
        self.feedback_color = (255, 255, 255)

    def handle(self, event):
        if self.done or self.result is not None:
            return
        self._handle_event(event)

    def _handle_event(self, event):
        pass

    def update(self, dt):
        if self.result is not None:
            self.settle -= dt
            if self.settle <= 0:
                self.done = True
            return
        self._update_game(dt)

    def _update_game(self, dt):
        pass


class WaterPour(MiniGameBase):
    """꾹 눌러 직접 물을 붓는다. 초록 '적정'에서 떼면 알맞게, 넘기면 과습(실패)."""
    PER_LEVEL = 0.7
    GAUGE_MAX = 112.0

    PROMPT = "꾹 눌러 물을 붓고, 초록 칸에서 손을 떼세요"

    def __init__(self, farm):
        super().__init__(farm)
        m = farm.sim.moisture
        self.level = 0.0
        self.pouring = False
        self.drops = []
        self.pour_played = False
        self.pour_anim = 0.0   # 0=쉼(입구 위), 1=붓는 중(입구가 아래로 기울어짐)
        self.fill_rate = 55.0 * random.uniform(0.9, 1.14)   # 변형: 물줄기 세기

        # 작물별 프롬프트 정의
        self.PROMPT = "물꼬를 터 물을 넉넉히 대고, 초록 칸에서 손을 떼세요" if game_state.crop == "rice" else "꾹 눌러 물을 붓고, 초록 칸에서 손을 떼세요"

        def lvl_for(target):
            return max(0.0, (target - m) / self.PER_LEVEL)
        self.good_low = lvl_for(38)
        self.good_high = lvl_for(72)
        self.overflow = lvl_for(78)
        if self.good_high <= self.good_low:
            self.good_high = self.good_low + 6

    def _handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.pouring = True
            if not self.pour_played:
                audio.play("water")
                self.pour_played = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.pouring:
            self.pouring = False
            self._resolve()

    def _update_game(self, dt):
        # 붓기 시작/멈춤을 부드럽게 — 물뿌리개 입구가 스르륵 기울어지도록
        target = 1.0 if self.pouring else 0.0
        self.pour_anim += (target - self.pour_anim) * min(1.0, dt * 10.0)
        if self.pouring:
            self.level += self.fill_rate * dt
            if game_state.crop != "rice":
                # 물방울은 실제 입구에서 시작한 물줄기 끝에서 떨어진다
                spx, spy = self._watering_spout()
                slen = 38 + 22 * self.pour_anim
                self.drops.append([spx + random.uniform(-3, 3), spy + slen, 24.0 + random.uniform(-12, 12), 130.0])
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

    def _water_tilt(self):
        # 붓는 동안 입구를 더 깊이 기울여 물이 자연스럽게 쏟아지도록 한다.
        return 34 - 94 * self.pour_anim

    def _watering_spout(self):
        """회전한 물뿌리개 스프라이트의 실제 입구(스파웃) 화면 좌표."""
        can = sprites["watering_can"]
        cw, ch = can.get_size()
        center = (PLOT.x + 150, 172 + int(8 * self.pour_anim))
        sv = pygame.math.Vector2(85 - cw / 2, 8 - ch / 2).rotate(-self._water_tilt())
        return center[0] + sv.x, center[1] + sv.y

    def draw(self, screen):
        from core.game_state import game_state
        _veil(screen)

        p = self.pour_anim
        if game_state.crop == "rice":
            # 픽셀풍 나무 물꼬(水門) — 좌우 기둥 + 대들보 + 미닫이 판자, 열리면 문턱으로 물이 쏟아진다.
            gx, gw = PLOT.x + 120, 58
            wood_d, wood, grain = (86, 56, 30), (140, 98, 54), (104, 72, 40)
            for px in (gx, gx + gw - 10):                       # 좌우 기둥
                pygame.draw.rect(screen, wood_d, (px, 138, 10, 68))
                pygame.draw.rect(screen, wood, (px + 1, 139, 8, 66))
                for yy in range(144, 204, 9):
                    pygame.draw.line(screen, grain, (px + 1, yy), (px + 8, yy), 1)
            pygame.draw.rect(screen, wood_d, (gx, 134, gw, 11))  # 대들보
            pygame.draw.rect(screen, wood, (gx + 2, 135, gw - 4, 8))
            # 미닫이 막이 판 — p만큼 위로 들린다 (가로 판자 3장)
            lift = int(30 * p)
            for i in range(3):
                by = (150 - lift) + i * 11
                pygame.draw.rect(screen, (66, 42, 22), (gx + 11, by, gw - 22, 10))
                pygame.draw.rect(screen, (112, 78, 44), (gx + 12, by + 1, gw - 24, 7))
                pygame.draw.line(screen, (150, 108, 66), (gx + 13, by + 2), (gx + gw - 13, by + 2), 1)
            # 열린 문턱에서 쏟아지는 픽셀 물기둥
            if p > 0.05:
                wx, top_y = gx + gw // 2, 196
                wlen = int(28 + 30 * p)
                pygame.draw.rect(screen, (150, 200, 236), (wx - 12, top_y - 4, 24, 5))  # 문턱 물보라
                for k in range(0, wlen, 4):                     # 짙고/밝은 물 블록 교차
                    wob = -2 if (k // 8) % 2 == 0 else 2
                    shade = (84, 148, 214) if (k // 4) % 2 == 0 else (120, 182, 234)
                    pygame.draw.rect(screen, shade, (wx - 8 + wob, top_y + k, 16, 4))
                pygame.draw.rect(screen, (206, 230, 248), (wx - 2, top_y, 4, wlen))     # 밝은 심줄
        else:
            # 물뿌리개가 붓는 동안 입구(스파웃)를 아래로 기울인다. 물줄기는 회전한 스프라이트의
            # 실제 입구 위치(중심 기준 오프셋을 -tilt로 회전)에서 정확히 시작한다.
            spx, spy = self._watering_spout()
            can = sprites["watering_can"]
            tilt = self._water_tilt()
            rot = pygame.transform.rotate(can, tilt)
            center = (PLOT.x + 150, 172 + int(8 * p))
            screen.blit(rot, rot.get_rect(center=center))
            if p > 0.05:
                slen = int(38 + 22 * p)
                ribbon = pygame.Surface((26, slen + 6), pygame.SRCALPHA)
                for ox, a, wd in ((-3, int(70 * p) + 20, 6), (0, int(120 * p) + 30, 4), (3, int(80 * p) + 20, 5)):
                    pygame.draw.line(ribbon, (150, 205, 235, a), (11 + ox, 0), (11 + ox, slen), wd)
                pygame.draw.line(ribbon, (222, 242, 252, 210), (11, 0), (11, slen - 2), 2)
                screen.blit(ribbon, (int(spx) - 11, int(spy)))
        if game_state.crop != "rice":
            for d in self.drops:
                glow = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(glow, (170, 215, 240, 110), (5, 5), 5)
                screen.blit(glow, (int(d[0]) - 5, int(d[1]) - 5))
                pygame.draw.circle(screen, (226, 244, 253), (int(d[0]), int(d[1])), 2)

        wet = min(1.0, self.level / max(1.0, self.overflow))
        if wet > 0:
            if self.farm.sim.is_tree:
                if self.level <= self.overflow:
                    col = (90, 150, 190, int(70 * wet))
                else:
                    col = (70, 110, 200, 150)
                puddle = pygame.Surface((80, 26), pygame.SRCALPHA)
                pygame.draw.ellipse(puddle, col, (0, 0, 80, 26))
                screen.blit(puddle, (225 - 40, 360 - 10))
            else:
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


class WeedPull(MiniGameBase):
    """잡초를 잡고 쭉 뽑아낸다. 뿌리째 끌어내야(드래그 거리) 뽑힌다 — 많이 걷어낼수록 좋다."""
    PROMPT = "잡초를 잡고 쭉 끌어내 뽑으세요"

    def __init__(self, farm):
        super().__init__(farm)
        import math
        self.is_apple = (game_state.crop == "apple")
        # 사과나무 가지치기는 나무에서 뻗어 나온 곁가지를 잡아 밖으로 끌어낸다.
        # 가지들이 실제 나무 우듬지에서 뻗어 나오도록 밑동(anchor) 기준 방사형으로 배치한다.
        self.tree_anchor = (225, 316)
        self.items = []
        if self.is_apple:
            n = random.randint(4, 5)
            for i in range(n):
                ang = math.radians(202 + 136 * (i / max(1, n - 1)) + random.uniform(-8, 8))
                rad = random.randint(42, 74)
                self.items.append({
                    "x": int(225 + rad * math.cos(ang)),
                    "y": int(300 + rad * math.sin(ang)),
                    "ox": 0.0, "oy": 0.0, "pulled": False,
                    "strength": random.randint(26, 44),
                })
        else:
            n = min(6, max(3, farm.sim.weeds // 11)) + random.randint(0, 1)   # 변형: 개수
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
        self.puffs = []
        
        self.PROMPT = "가지를 잡아 밭 밖으로 끌어내어 가지치기 하세요" if game_state.crop == "apple" else "잡초를 잡고 쭉 끌어내 뽑으세요"

    def _handle_event(self, event):
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

    def _update_game(self, dt):
        self.timer -= dt
        
        # 마우스 포인터의 가상 좌표상 호버 여부 확인
        mx, my = pygame.mouse.get_pos()
        for w in self.items:
            if not w["pulled"] and abs(mx - w["x"]) < 22 and abs(my - w["y"]) < 28:
                w["hovered"] = True
            else:
                w["hovered"] = False

        for p in self.puffs:
            p[2] -= dt
        self.puffs = [p for p in self.puffs if p[2] > 0]
        if self.timer <= 0:
            self._resolve()

    def _resolve(self):
        cleared = sum(1 for w in self.items if w["pulled"])
        frac = cleared / max(1, self.total)
        is_apple = (game_state.crop == "apple")
        if frac >= 0.85:
            self.feedback = "가지를 깨끗하게 정리했습니다!" if is_apple else "잡초를 말끔히 걷어냈다!"
            self.feedback_color = (150, 230, 150)
            audio.play("success")
        elif frac >= 0.45:
            self.feedback = "어느 정도 가지를 쳤습니다." if is_apple else "그런대로 정리했다."
            self.feedback_color = (220, 205, 140)
            audio.play("page")
        else:
            self.feedback = "정리가 덜 되었습니다." if is_apple else "손이 더뎠다. 잡초가 남았다."
            self.feedback_color = (225, 175, 130)
            audio.play("page")
        self.result = {"quality": "weed", "cleared_frac": frac}
        self.settle = 1.0

    def draw(self, screen):
        _veil(screen)
        wsp = sprites["weed_nm"] if game_state.nightmare else sprites["weed"]
        is_apple = (game_state.crop == "apple")
        
        import math
        for w in self.items:
            if w["pulled"]:
                continue
            ox, oy = int(w["ox"]), int(w["oy"])
            
            # 호버 시 진동 연출 (드래그하는 개체는 제외)
            shake_x, shake_y = 0, 0
            if w.get("hovered", False) and self.grabbed is not w:
                ticks = pygame.time.get_ticks() * 0.05
                shake_x = int(math.sin(ticks) * 3)
                shake_y = int(math.cos(ticks * 0.7) * 2)
                
            gx2, gy2 = w["x"] + ox + shake_x, w["y"] + oy + shake_y

            if is_apple:
                # 나무 밑동(anchor)에서 가지가 뻗어 나온 것처럼 굵은 곁가지를 그린다.
                ax, ay = self.tree_anchor
                # 악몽 모드일 때 검붉은 핏빛 나뭇가지 색
                branch_col1 = (60, 20, 20) if game_state.nightmare else (78, 52, 30)
                branch_col2 = (90, 30, 30) if game_state.nightmare else (120, 82, 46)
                branch_col3 = (80, 25, 25) if game_state.nightmare else (110, 76, 44)

                pygame.draw.line(screen, branch_col1, (ax, ay), (gx2, gy2), 7)
                pygame.draw.line(screen, branch_col2, (ax, ay), (gx2, gy2), 4)
                # 잔가지
                pygame.draw.line(screen, branch_col3, (gx2, gy2), (gx2 - 8, gy2 - 10), 3)
                pygame.draw.line(screen, branch_col3, (gx2, gy2), (gx2 + 9, gy2 - 6), 3)
                # 곁가지 잎 (쳐내야 할 웃자란 잎) - 악몽 모드일 때 붉은 빛깔 잎사귀
                leaf_col1 = (120, 32, 32) if game_state.nightmare else (60, 120, 58)
                leaf_col2 = (160, 48, 48) if game_state.nightmare else (86, 162, 78)
                leaf_col3 = (190, 70, 70) if game_state.nightmare else (108, 190, 96)

                pygame.draw.circle(screen, leaf_col1, (gx2 - 6, gy2 - 12), 7)
                pygame.draw.circle(screen, leaf_col2, (gx2 + 9, gy2 - 9), 6)
                pygame.draw.circle(screen, leaf_col3, (gx2 + 2, gy2 - 15), 5)
                # 잡는 곳 표시
                glow = pygame.Surface((30, 30), pygame.SRCALPHA)
                pygame.draw.circle(glow, (240, 255, 210, 90), (15, 15), 14)
                screen.blit(glow, (gx2 - 15, gy2 - 15))
            else:
                # 대상 표시
                glow = pygame.Surface((46, 24), pygame.SRCALPHA)
                pygame.draw.ellipse(glow, (255, 236, 165, 80), (0, 0, 46, 24))
                pygame.draw.ellipse(glow, (255, 250, 210, 120), (9, 6, 28, 12))
                screen.blit(glow, (gx2 - 23, gy2 + 6))
                if self.grabbed is w and (ox or oy):
                    # 악)몽중농원에선 잡초가 붉으니 끌어당기는 선도 붉게 맞춘다.
                    line_col = (196, 78, 66) if game_state.nightmare else (96, 132, 70)
                    pygame.draw.line(screen, line_col, (w["x"], w["y"] + 10), (w["x"] + ox, w["y"] + oy), 3)
                screen.blit(wsp, (gx2 - wsp.get_width() // 2, gy2 - wsp.get_height() // 2))
                
        for p in self.puffs:
            r = int(14 * (1 - p[2] / 0.45)) + 4
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            if is_apple:
                if game_state.nightmare:
                    color = (160, 48, 48, int(150 * (p[2] / 0.45)))
                else:
                    color = (130, 160, 110, int(150 * (p[2] / 0.45)))
            else:
                color = (150, 110, 70, int(150 * (p[2] / 0.45)))
            pygame.draw.circle(s, color, (r, r), r)
            screen.blit(s, (p[0] - r, p[1] - r))

        remain = sum(1 for w in self.items if not w["pulled"])
        cap = self.PROMPT if self.result is None else self.feedback
        _caption(screen, cap, None if self.result is None else self.feedback_color)
        if self.result is None:
            remain_txt = f"남은 가지 {remain}" if is_apple else f"남은 잡초 {remain}"
            _counter(screen, remain_txt, self.timer / 6.5)


class PestTap(MiniGameBase):
    """잎 사이를 기어다니는 해충을 빠르게 잡는다. 움직이니 놓치기 쉽다."""
    PROMPT = "잎의 벌레를 빠르게 잡으세요"

    def __init__(self, farm):
        super().__init__(farm)
        n = min(6, max(3, farm.sim.pests // 7)) + random.randint(0, 1)   # 변형: 개수
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
        self.puffs = []
        
        self.PROMPT = "밭의 굼벵이를 빠르게 잡으세요" if game_state.crop == "potato" else "잎의 벌레를 빠르게 잡으세요"

    def _handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for b in self.bugs:
                if not b["dead"] and abs(event.pos[0] - b["x"]) < 20 and abs(event.pos[1] - b["y"]) < 20:
                    b["dead"] = True
                    audio.play("pest")
                    self.puffs.append([b["x"], b["y"], 0.35])
                    break
            if all(b["dead"] for b in self.bugs):
                self._resolve()

    def _update_game(self, dt):
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
        is_potato = (game_state.crop == "potato")
        if frac >= 0.85:
            self.feedback = "굼벵이를 거의 다 잡았다!" if is_potato else "벌레를 거의 다 잡았다!"
            self.feedback_color = (150, 230, 150)
            audio.play("success")
        elif frac >= 0.45:
            self.feedback = "굼벵이를 절반쯤 잡았다." if is_potato else "절반쯤 잡았다."
            self.feedback_color = (220, 205, 140)
            audio.play("page")
        else:
            self.feedback = "굼벵이가 많이 남았다." if is_potato else "놓친 벌레가 많다."
            self.feedback_color = (225, 175, 130)
            audio.play("page")
        self.result = {"quality": "pest", "cleared_frac": frac}
        self.settle = 1.0

    def draw(self, screen):
        _veil(screen)
        bsp = sprites["bug"]
        is_potato = (game_state.crop == "potato")
        for b in self.bugs:
            if b["dead"]:
                continue
            bx, by = int(b["x"]), int(b["y"])
            # 조준 고리
            ring = pygame.Surface((36, 36), pygame.SRCALPHA)
            pygame.draw.circle(ring, (255, 90, 60, 70) if not is_potato else (240, 200, 100, 70), (18, 18), 16)
            pygame.draw.circle(ring, (255, 140, 95, 210) if not is_potato else (229, 180, 50, 210), (18, 18), 15, 3)
            screen.blit(ring, (bx - 18, by - 18))
            
            # 밭에 보이던 해충과 같은 스프라이트로 통일 (잡을 때 다른 벌레로 바뀌지 않게)
            screen.blit(bsp, (bx - bsp.get_width() // 2, by - bsp.get_height() // 2))
        for p in self.puffs:
            r = int(10 * (1 - p[2] / 0.35)) + 3
            s = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            color = (245, 240, 220, int(180 * (p[2] / 0.35))) if is_potato else (210, 220, 120, int(180 * (p[2] / 0.35)))
            pygame.draw.circle(s, color, (r, r), r)
            screen.blit(s, (p[0] - r, p[1] - r))

        remain = sum(1 for b in self.bugs if not b["dead"])
        cap = self.PROMPT if self.result is None else self.feedback
        _caption(screen, cap, None if self.result is None else self.feedback_color)
        if self.result is None:
            remain_txt = f"남은 굼벵이 {remain}" if is_potato else f"남은 벌레 {remain}"
            _counter(screen, remain_txt, self.timer / 6.0)


class SoilMound:
    """흙을 쓸어 뿌리를 덮어 북돋운다. 마우스를 누른 채 자리 위를 문질러 두둑을 쌓는다.
    잘 덮을수록(채운 자리 비율) 건강·안정에 도움이 크다 — 못해도 소폭은 보장."""
    PROMPT = "마우스를 누른 채 흙을 쓸어 뿌리를 덮어 주세요"

class SoilMound(MiniGameBase):
    """흙을 쓸어 뿌리를 덮어 북돋운다. 마우스를 누른 채 자리 위를 문질러 두둑을 쌓는다.
    잘 덮을수록(채운 자리 비율) 건강·안정에 도움이 크다 — 못해도 소폭은 보장."""
    PROMPT = "마우스를 누른 채 흙을 쓸어 뿌리를 덮어 주세요"

    def __init__(self, farm):
        super().__init__(farm)
        if farm.sim.is_tree:
            pts = [(225, 360)]
        else:
            pts = farm.crop_positions() or [(PLOT.centerx, PLOT.centery)]
        self.spots = [
            {"x": cx, "y": cy, "fill": 0.0,
             "need": random.uniform(0.85, 1.0), "done": False}   # 변형: 자리마다 필요량
            for (cx, cy) in pts
        ]
        self.total = len(self.spots)
        self.raking = False
        self.mx, self.my = 0, 0
        self.timer = 6.5
        self.puffs = []
        self.rake_played = False
        
        self.PROMPT = "마우스를 누른 채 거름을 골고루 주어 영양을 채우세요" if game_state.crop == "apple" else "마우스를 누른 채 흙을 쓸어 뿌리를 덮어 주세요"

    def _handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.raking = True
            self.mx, self.my = event.pos
        elif event.type == pygame.MOUSEMOTION:
            self.mx, self.my = event.pos
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.raking = False

    def _update_game(self, dt):
        self.timer -= dt
        if self.raking:
            near = False
            for s in self.spots:
                if s["done"]:
                    continue
                if abs(self.mx - s["x"]) < 40 and abs(self.my - s["y"]) < 34:
                    near = True
                    if not self.rake_played:
                        audio.play("soil"); self.rake_played = True
                    s["fill"] += 1.7 * dt
                    if s["fill"] >= s["need"]:
                        s["fill"] = s["need"]; s["done"] = True
                        audio.play("soil")
                        self.puffs.append([s["x"], s["y"] + 10, 0.4])
            if not near:
                self.rake_played = False   # 자리를 벗어나면 다시 닿을 때 사각사각
        else:
            self.rake_played = False
        for p in self.puffs:
            p[2] -= dt
        self.puffs = [p for p in self.puffs if p[2] > 0]
        if self.timer <= 0 or all(s["done"] for s in self.spots):
            self._resolve()

    def _resolve(self):
        done = sum(1 for s in self.spots if s["done"])
        frac = done / max(1, self.total)
        is_apple = (game_state.crop == "apple")
        if frac >= 0.85:
            self.feedback = "거름을 골고루 잘 주었습니다!" if is_apple else "두둑이 북돋우니 흙에 생기가 돈다!"
            self.feedback_color = (150, 230, 150)
            audio.play("success")
        elif frac >= 0.45:
            self.feedback = "거름을 적당히 나누어 주었습니다." if is_apple else "흙을 어느 정도 다독였다."
            self.feedback_color = (220, 205, 140)
            audio.play("page")
        else:
            self.feedback = "거름이 한쪽에 뭉쳤거나 부족합니다." if is_apple else "북돋다 말아 뿌리가 허전하다."
            self.feedback_color = (225, 175, 130)
            audio.play("page")
        self.result = {"quality": "soil", "cleared_frac": frac}
        self.settle = 1.0

    def draw(self, screen):
        _veil(screen)
        is_apple = (game_state.crop == "apple")
        for s in self.spots:
            cx, cy = s["x"], s["y"]
            f = s["fill"] / max(0.01, s["need"])
            pit = pygame.Surface((52, 22), pygame.SRCALPHA)
            pygame.draw.ellipse(pit, (40, 26, 16, 150) if not is_apple else (30, 20, 10, 150), (0, 0, 52, 22))     # 파인 자리
            screen.blit(pit, (cx - 26, cy + 6))
            if f > 0.02:                                                    # 쌓이는 두둑
                h = int(16 * f); w = int(20 + 26 * f)
                mound = pygame.Surface((w, h + 12), pygame.SRCALPHA)
                
                if is_apple:
                    base = (60, 48, 40) if s["done"] else (45, 35, 30)
                    pygame.draw.ellipse(mound, (*base, 235), (0, 8, w, h + 2))
                    pygame.draw.ellipse(mound, (80, 70, 60, 230), (3, 6, w - 6, max(3, h - 2)))
                    for ox in (w//3, w//2, 2*w//3):
                        pygame.draw.rect(mound, (15, 10, 5), (ox, h // 2 + 5, 2, 2))
                else:
                    base = (150, 104, 62) if s["done"] else (120, 78, 48)
                    pygame.draw.ellipse(mound, (*base, 235), (0, 8, w, h + 2))
                    pygame.draw.ellipse(mound, (176, 128, 78, 230), (3, 6, w - 6, max(3, h - 2)))
                screen.blit(mound, (cx - w // 2, cy + 6 - h))
            if not s["done"]:                                              # 덮으라는 신호 빛
                glow = pygame.Surface((46, 22), pygame.SRCALPHA)
                pygame.draw.ellipse(glow, (255, 232, 150, 70) if not is_apple else (200, 255, 150, 70), (0, 0, 46, 22))
                screen.blit(glow, (cx - 23, cy + 6))
        for p in self.puffs:
            r = int(13 * (1 - p[2] / 0.4)) + 4
            su = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            color = (80, 70, 60, int(150 * (p[2] / 0.4))) if is_apple else (150, 110, 70, int(150 * (p[2] / 0.4)))
            pygame.draw.circle(su, color, (r, r), r)
            screen.blit(su, (p[0] - r, p[1] - r))
        if self.raking and self.result is None:                            # 흙손 커서
            ring = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(ring, (220, 195, 150, 120), (15, 15), 13, 3)
            screen.blit(ring, (self.mx - 15, self.my - 15))

        remain = sum(1 for s in self.spots if not s["done"])
        cap = self.PROMPT if self.result is None else self.feedback
        _caption(screen, cap, None if self.result is None else self.feedback_color)
        if self.result is None:
            _counter(screen, f"남은 자리 {remain}", self.timer / 6.5)


# ---- 공통 그리기 헬퍼 ----

def _veil(screen):
    veil = pygame.Surface((800, 600), pygame.SRCALPHA)
    veil.fill((10, 14, 22, 70))
    screen.blit(veil, (0, 0))


def _pill(screen, rect, alpha=190):
    """텍스트 가독성용 반투명 알약 배경 — 밭 위 어디서든 글자가 읽히게."""
    bg = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(bg, (16, 18, 24, alpha), bg.get_rect(), border_radius=rect.height // 2)
    pygame.draw.rect(bg, (96, 84, 64, 160), bg.get_rect(), 1, border_radius=rect.height // 2)
    screen.blit(bg, rect.topleft)


def _caption(screen, text, color=None, hot=False):
    if color is None:
        color = (255, 235, 150) if hot else (244, 236, 214)
    f = _font(18)
    t = f.render(text, True, color)
    x = PLOT.centerx - t.get_width() // 2
    y = 466
    _pill(screen, pygame.Rect(x - 12, y - 5, t.get_width() + 24, t.get_height() + 8))
    screen.blit(t, (x, y))


def _counter(screen, text, time_frac):
    f = _font(15)
    t = f.render(text, True, (236, 228, 204))
    x, y = PLOT.x + 8, PLOT.y + 6
    _pill(screen, pygame.Rect(x - 7, y - 3, t.get_width() + 14, t.get_height() + 5), alpha=170)
    screen.blit(t, (x, y))
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
