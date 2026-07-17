import math
import random
import datetime
import pygame
from core.game_state import (
    game_state, get_season, get_season_colors,
)
from core.assets import *
from core.ui import (
    draw_light_panel, draw_panel, draw_wood_panel, draw_top_bar,
    draw_bottom_bar, draw_understanding_badge, draw_meter_bar,
    wrap_text, mix_color,
)
from core.crops import current_crop
from core import i18n
from core.pixelfx import (pixel_rect, pixel_disc, pixelate, glow_sprite, blit_glow,
                          CHAMFER, CHAMFER_SM)  # 곡선 없음: 픽셀 챔퍼/원

TEXT_DARK = (48, 38, 28)
TEXT_MUTED = (123, 106, 92)
PLOT = pygame.Rect(44, 140, 362, 318)
DASH_BTN = pygame.Rect(24, 27, 108, 28)    # 좁은 화면 '밭 수첩' 팝업 토글 — 상단 바 왼쪽 빈자리
                                           # (예전 (430,70)은 '밭 상태' 패널 상단과 7px 겹쳤다)
JOURNAL_BTN = pygame.Rect(622, 494, 138, 26)   # 하단 '농장 일지' 바 우측 — 지난 일지 열람 버튼
JOURNAL_PANEL = pygame.Rect(90, 70, 620, 470)  # 지난 일지 팝업 패널


class FarmRenderer:
    def __init__(self):
        # 밭 데코레이션 생성 (초록 풀싹, 흙/돌 알갱이 고정 좌표 지정)
        self.plot_decorations = []
        self.plot_decorations.append({'type': 'grass', 'x': 86, 'y': 180})
        self.plot_decorations.append({'type': 'grass', 'x': 150, 'y': 184})
        self.plot_decorations.append({'type': 'grass', 'x': 354, 'y': 180})
        self.plot_decorations.append({'type': 'grass', 'x': 324, 'y': 200})
        self.plot_decorations.append({'type': 'grass', 'x': 88, 'y': 295})
        self.plot_decorations.append({'type': 'grass', 'x': 360, 'y': 390})
        self.plot_decorations.append({'type': 'grass', 'x': 88, 'y': 410})
        self.plot_decorations.append({'type': 'grass', 'x': 206, 'y': 414})
        
        pebbles = [
            (95, 196), (158, 196), (164, 198), (105, 290), (350, 280),
            (88, 335), (242, 290), (145, 300), (324, 305), (148, 412),
            (232, 408), (238, 410), (320, 404), (325, 406), (356, 330)
        ]
        for px, py in pebbles:
            self.plot_decorations.append({'type': 'pebble', 'x': px, 'y': py})

        # 날씨 앰비언트 파티클 상태 — FarmScene.update 가 매 프레임 update_ambient 로 굴린다
        self.ambient = {"weather": None, "parts": [], "t": 0.0}

    # ── 날씨 앰비언트 — 밭 위에 살아 있는 잔디테일 ────────────────────────────
    # 비: 떨어지는 빗줄기 / 강풍: 날리는 잎 / 가뭄: 피어오르는 흙먼지 아지랑이 /
    # 흐림: 흘러가는 구름 그림자 / 맑음: 밭을 배회하는 나비. 전부 픽셀 블록 톤.
    def _ambient_init(self, weather):
        parts = []
        if weather == "비":
            for _ in range(34):
                parts.append({"x": random.uniform(0, 800), "y": random.uniform(-600, 0),
                              "spd": random.uniform(360, 520)})
        elif weather == "강풍":
            for _ in range(6):
                parts.append({"x": random.uniform(-800, 0), "y": random.uniform(60, 440),
                              "spd": random.uniform(180, 300), "ph": random.uniform(0, 6.28),
                              "shade": random.randint(0, 2)})
        elif weather == "가뭄":
            for _ in range(14):
                parts.append({"x": random.uniform(60, 740), "y": random.uniform(150, 560),
                              "spd": random.uniform(14, 30), "ph": random.uniform(0, 6.28)})
        elif weather == "흐림":
            for i in range(2):
                parts.append({"x": random.uniform(0, 800), "y": (210, 360)[i],
                              "spd": random.uniform(10, 18), "w": random.choice([170, 230])})
        else:   # 맑음 — 나비 두 마리
            for i in range(2):
                parts.append({"x": random.uniform(PLOT.x + 40, PLOT.right - 40),
                              "y": random.uniform(PLOT.y + 40, PLOT.bottom - 60),
                              "tx": 0.0, "ty": 0.0, "ph": random.uniform(0, 6.28), "hue": i})
        return parts

    def update_ambient(self, dt, weather):
        st = self.ambient
        st["t"] += dt
        if st["weather"] != weather:
            st["weather"] = weather
            st["parts"] = self._ambient_init(weather)
        if weather == "비":
            for p in st["parts"]:
                p["y"] += p["spd"] * dt
                p["x"] -= p["spd"] * 0.12 * dt          # 살짝 비껴 내리는 비
                if p["y"] > 600:
                    p["y"] = random.uniform(-40, -6)
                    p["x"] = random.uniform(0, 820)
        elif weather == "강풍":
            for p in st["parts"]:
                p["x"] += p["spd"] * dt
                p["y"] += math.sin(st["t"] * 2.2 + p["ph"]) * 46 * dt
                if p["x"] > 820:
                    p["x"] = random.uniform(-60, -10)
                    p["y"] = random.uniform(60, 440)
        elif weather == "가뭄":
            for p in st["parts"]:
                p["y"] -= p["spd"] * dt                  # 아지랑이처럼 떠오르는 흙먼지
                p["x"] += math.sin(st["t"] * 1.4 + p["ph"]) * 10 * dt
                if p["y"] < 130:
                    p["y"] = random.uniform(430, 580)
                    p["x"] = random.uniform(60, 740)
        elif weather == "흐림":
            for p in st["parts"]:
                p["x"] += p["spd"] * dt
                if p["x"] - p["w"] > 820:
                    p["x"] = -p["w"] - random.uniform(0, 200)
        else:   # 맑음 — 나비 배회
            for p in st["parts"]:
                p["ph"] += dt * (7.5 + p["hue"])
                need_new = (p["tx"] == 0.0 or (abs(p["tx"] - p["x"]) < 6 and abs(p["ty"] - p["y"]) < 6)
                            or random.random() < dt * 0.4)
                if need_new:
                    p["tx"] = random.uniform(PLOT.x + 30, PLOT.right - 30)
                    p["ty"] = random.uniform(PLOT.y + 30, PLOT.bottom - 50)
                dx, dy = p["tx"] - p["x"], p["ty"] - p["y"]
                d = max(1.0, (dx * dx + dy * dy) ** 0.5)
                p["x"] += dx / d * 34 * dt
                p["y"] += dy / d * 34 * dt + math.sin(p["ph"]) * 9 * dt

    _RAIN_SPR = None
    _RAIN_SPR_NM = None
    _CLOUD_SHADOWS = {}

    def _draw_ambient(self, screen):
        st = self.ambient
        w = st["weather"]
        nm = game_state.nightmare
        if w == "비":
            if FarmRenderer._RAIN_SPR is None:
                s = pygame.Surface((2, 9), pygame.SRCALPHA)
                s.fill((168, 200, 244, 150), (0, 0, 2, 6))
                s.fill((208, 228, 252, 190), (0, 6, 2, 3))
                FarmRenderer._RAIN_SPR = s
                s2 = pygame.Surface((2, 9), pygame.SRCALPHA)
                s2.fill((176, 84, 78, 150), (0, 0, 2, 6))
                s2.fill((216, 120, 110, 190), (0, 6, 2, 3))
                FarmRenderer._RAIN_SPR_NM = s2
            spr = FarmRenderer._RAIN_SPR_NM if nm else FarmRenderer._RAIN_SPR
            for p in st["parts"]:
                screen.blit(spr, (int(p["x"]), int(p["y"])))
        elif w == "강풍":
            shades = ([((150, 90, 70), (110, 60, 50))] * 3 if nm else
                      [((120, 170, 80), (86, 132, 60)),
                       ((150, 178, 96), (104, 140, 66)),
                       ((176, 150, 84), (130, 108, 58))])
            for p in st["parts"]:
                x, y = int(p["x"]), int(p["y"])
                c1, c2 = shades[p["shade"] % len(shades)]
                pygame.draw.rect(screen, c1, (x, y, 9, 4))
                pygame.draw.rect(screen, c2, (x + 3, y + 4, 6, 3))
        elif w == "가뭄":
            for p in st["parts"]:
                a = 130 + int(60 * math.sin(st["t"] * 2 + p["ph"]))
                spr = glow_sprite(5, (240, 202, 128), px=2, steps=(90,), core=((248, 220, 160), 200))
                blit_glow(screen, spr, (p["x"], p["y"]), max(0, min(255, a)))
        elif w == "흐림":
            for p in st["parts"]:
                spr = self._cloud_shadow(p["w"])
                screen.blit(spr, (int(p["x"] - p["w"]), int(p["y"] - p["w"] // 3)))
        elif not nm:   # 맑음 — 나비 (악몽 밭엔 나비가 오지 않는다)
            for p in st["parts"]:
                self._draw_butterfly(screen, p)

    def _cloud_shadow(self, w):
        """흘러가는 구름 그림자 — 도트 블록 블롭(캐시)."""
        spr = FarmRenderer._CLOUD_SHADOWS.get(w)
        if spr is None:
            h = w * 2 // 3
            s = pygame.Surface((w * 2, h), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (18, 22, 30, 46), (0, h // 4, w * 2, h * 3 // 4))
            pygame.draw.ellipse(s, (18, 22, 30, 46), (w // 3, 0, w, h * 2 // 3))
            spr = pixelate(s, 6, smooth=False)
            FarmRenderer._CLOUD_SHADOWS[w] = spr
        return spr

    # ── 지난 일지 열람 (J 키 / 하단 바 버튼) ──────────────────────────────────
    def _draw_journal_button(self, screen):
        r = JOURNAL_BTN
        hovered = r.collidepoint(pygame.mouse.get_pos())
        base = (44, 57, 58) if not hovered else (66, 84, 82)
        draw_panel(screen, r, fill=base, border=(229, 192, 124), radius=8, shadow=False)
        t = get_font(13).render(i18n.tf("지난 일지 ({n})", n=len(game_state.journal_entries)),
                                True, (240, 224, 190))
        screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

    def _draw_journal_popup(self, screen, farm_scene):
        """지금까지 쌓인 밭일 일지를 인게임에서 훑어보는 팝업 (표시 시점 번역 — 엔딩과 동일 규칙)."""
        from scenes.ending import _localize_journal_line
        veil = pygame.Surface((800, 600), pygame.SRCALPHA)
        veil.fill((10, 12, 18, 170))
        screen.blit(veil, (0, 0))
        panel = JOURNAL_PANEL
        draw_light_panel(screen, panel)
        title = get_font(22).render("밭일 일지", True, TEXT_DARK)
        screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 18))
        bar_w = min(title.get_width(), 160)
        pygame.draw.rect(screen, GOLD, (panel.centerx - bar_w // 2, panel.y + 46, bar_w, 3))
        hint = get_font(13).render("J · ESC · 바깥 클릭으로 닫기  ·  휠로 스크롤", True, TEXT_MUTED)
        screen.blit(hint, (panel.centerx - hint.get_width() // 2, panel.bottom - 28))

        entries = list(game_state.journal_entries)
        view = pygame.Rect(panel.x + 26, panel.y + 62, panel.w - 52, panel.h - 100)
        if not entries:
            es = get_font(16).render("아직 일지가 없습니다. 하루가 지나면 기록됩니다.", True, TEXT_MUTED)
            screen.blit(es, (panel.centerx - es.get_width() // 2, panel.centery - 10))
            farm_scene.journal_scroll = 0
            return

        body_font = get_font(15)
        head_font = get_font(16)
        line_h = body_font.get_height() + 4
        lines = []
        for entry in entries:
            for raw in entry.split("\n"):
                loc = _localize_journal_line(raw)
                is_head = raw.startswith("[")
                for wl in wrap_text(loc, body_font, view.w - 14):
                    lines.append((wl, is_head))
            lines.append((None, False))   # 문단 간격
        total_h = sum((line_h if t is not None else 10) for t, _ in lines)
        max_scroll = max(0, total_h - view.h)
        farm_scene.journal_scroll = max(0, min(farm_scene.journal_scroll, max_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(view)
        y = view.y - farm_scene.journal_scroll
        for text, is_head in lines:
            if text is None:
                y += 10
                continue
            if y > view.bottom:
                break
            if y + line_h >= view.y:
                col = (150, 110, 60) if is_head else TEXT_DARK
                fs = (head_font if is_head else body_font).render(text, True, col)
                screen.blit(fs, (view.x, y))
            y += line_h
        screen.set_clip(old_clip)

        if max_scroll > 0:
            track = pygame.Rect(panel.right - 20, view.y, 6, view.h)
            pixel_rect(screen, (206, 188, 158), track, chamfer=CHAMFER_SM)
            th = max(24, int(view.h * view.h / max(1, total_h)))
            ty = track.y + int((track.h - th) * (farm_scene.journal_scroll / max_scroll))
            pixel_rect(screen, (123, 92, 65), (track.x, ty, 6, th), chamfer=CHAMFER_SM)

    def _draw_butterfly(self, screen, p):
        """도트 나비 — 날개 두 블록이 접었다 폈다."""
        x, y = int(p["x"]), int(p["y"])
        flap = math.sin(p["ph"]) > 0
        wing = (244, 196, 92) if p["hue"] == 0 else (232, 168, 186)
        wing_d = (196, 148, 60) if p["hue"] == 0 else (188, 122, 142)
        if flap:
            pygame.draw.rect(screen, wing, (x - 5, y - 3, 4, 5))
            pygame.draw.rect(screen, wing, (x + 2, y - 3, 4, 5))
            pygame.draw.rect(screen, wing_d, (x - 4, y + 1, 3, 2))
            pygame.draw.rect(screen, wing_d, (x + 2, y + 1, 3, 2))
        else:
            pygame.draw.rect(screen, wing, (x - 3, y - 4, 3, 6))
            pygame.draw.rect(screen, wing, (x + 1, y - 4, 3, 6))
        pygame.draw.rect(screen, (58, 48, 40), (x - 1, y - 3, 2, 7))

    def draw_compact_meter(self, screen, label, value, x, y, color):
        font = get_font(14)
        label_surf = font.render(label, True, TEXT_DARK)
        screen.blit(label_surf, (x, y - 1))
        bar_right = x + 134
        bar_x = x + max(48, label_surf.get_width() + 6)
        bar = pygame.Rect(bar_x, y, bar_right - bar_x, 13)
        # 도전 '무일지' — 수치를 감춘다: 빈 트랙에 '?'만
        if getattr(game_state, "challenge", None) == "no_journal":
            pixel_rect(screen, (73, 65, 54), bar, chamfer=CHAMFER_SM)
            q = get_font(12).render("?", True, (170, 158, 138))
            screen.blit(q, (bar.centerx - q.get_width() // 2, bar.y))
            return
        draw_meter_bar(screen, bar, value, 100, color)

    def draw_labeled_meter(self, screen, label, value, max_value, x, y, w, color):
        font = get_font(16)
        shown_value = max(0, min(value, max_value))
        label_surf = font.render(label, True, TEXT_DARK)
        value_surf = font.render(f"{shown_value}/{max_value}", True, TEXT_DARK)
        screen.blit(label_surf, (x, y - 1))
        screen.blit(value_surf, (x + w - value_surf.get_width(), y - 1))

        bar = pygame.Rect(x, y + 22, w, 15)
        draw_meter_bar(screen, bar, value, max_value, color)

        if label == "성장":
            fill_w = int(bar.w * (shown_value / max_value))
            carrot_x = max(bar.x, bar.x + fill_w - 3)
            crop_key = game_state.crop
            mini_spr = sprites.get(f"mini_{crop_key}", sprites["mini_carrot"])
            screen.blit(mini_spr, (carrot_x, bar.y + 7 - mini_spr.get_height() // 2))

    def draw_field_summary(self, screen, sim):
        panel = pygame.Rect(430, 82, 320, 100)
        draw_light_panel(screen, panel)
        title_font = get_font(20)
        
        crop_name = current_crop()["name"]
        title_text = i18n.tf("밭 상태 ({crop})", crop=i18n.t(crop_name))
        
        title = title_font.render(title_text, True, TEXT_DARK)
        screen.blit(title, (450, 96))

        self.draw_labeled_meter(screen, "성장", sim.growth, sim.growth_goal, 450, 123, 116, (235, 150, 55))
        draw_understanding_badge(screen, 600, 123, 130)

        status_font = get_font(16)
        grade = ("?" if getattr(game_state, "challenge", None) == "no_journal"
                 else i18n.t(sim.grade_text(sim.health)))   # 무일지: 건강 요약도 감춘다
        health_text = status_font.render(i18n.tf("건강 {grade}", grade=grade), True, TEXT_DARK)
        screen.blit(health_text, (450, 162))

        if sim.is_harvest_ready():
            ready = status_font.render("수확 가능", True, (145, 55, 0))
            screen.blit(ready, (640, 162))

    def draw_meters(self, screen, sim):
        panel = pygame.Rect(430, 190, 320, 106)
        draw_light_panel(screen, panel)
        c1, c2 = 450, 600
        self.draw_compact_meter(screen, "수분", sim.moisture, c1, 205, (80, 170, 240))
        self.draw_compact_meter(screen, "건강", sim.health, c2, 205, (90, 185, 95))
        if sim.no_weeds:
            # 잡초 없는 작물(나무): 5칸 — 스트레스를 위로 당겨 그리드 '중간 구멍'을 없앤다
            self.draw_compact_meter(screen, "해충", sim.pests, c1, 232, (210, 110, 60))
            self.draw_compact_meter(screen, "스트레스", sim.stress, c2, 232, (210, 95, 95))
            self.draw_compact_meter(screen, "배수", sim.drainage, c1, 259, (90, 160, 185))
        else:
            self.draw_compact_meter(screen, "잡초", sim.weeds, c1, 232, (150, 160, 60))
            self.draw_compact_meter(screen, "해충", sim.pests, c2, 232, (210, 110, 60))
            self.draw_compact_meter(screen, "배수", sim.drainage, c1, 259, (90, 160, 185))
            self.draw_compact_meter(screen, "스트레스", sim.stress, c2, 259, (210, 95, 95))

    def draw_action_scrollbar(self, screen, farm_scene):
        sim = farm_scene.sim
        actions = sim.get_action_choices()
        if not farm_scene.action_menu_open or len(actions) <= 4:
            return

        track = pygame.Rect(732, 330, 8, 121)
        pixel_rect(screen, (198, 166, 118), track, chamfer=CHAMFER_SM)
        thumb_h = max(22, int(track.h * 4 / len(actions)))
        max_scroll = max(1, len(actions) - 4)
        thumb_y = track.y + int((track.h - thumb_h) * farm_scene.action_scroll / max_scroll)
        thumb = pygame.Rect(track.x, thumb_y, track.w, thumb_h)
        pixel_rect(screen, (123, 92, 65), thumb, chamfer=CHAMFER_SM)

    def crop_positions(self):
        return [(126, 241), (223, 241), (322, 241), (126, 360), (223, 360), (322, 360)]

    def _draw_seeds(self, screen, x, y):
        screen.blit(sprites["dirt_patch"], (x - 13, y - 12))
        draw_crop_seed(screen, x, y, game_state.crop)

    def _draw_plain_soil(self, screen, sim, plot_rect, season_colors):
        sc = season_colors
        inner = pygame.Rect(plot_rect.x + 22, plot_rect.y + 28, plot_rect.w - 44, plot_rect.h - 56)
        nm = game_state.nightmare
        frame = inner.inflate(16, 16)
        pixel_rect(screen, (40, 30, 25) if not nm else (28, 8, 8), frame.move(0, 4), chamfer=CHAMFER)
        pixel_rect(screen, (132, 83, 48) if not nm else (96, 32, 30), frame, chamfer=CHAMFER)
        pixel_rect(screen, (185, 125, 80) if not nm else (150, 45, 42), frame, width=3, chamfer=CHAMFER)
        
        if nm:
            soil = (78, 20, 18) if sim.moisture > 72 else (116, 40, 34) if sim.moisture < 28 else (96, 30, 28)
            soil_dark = (48, 12, 12)
        else:
            soil = (96, 62, 42) if sim.moisture > 72 else (120, 82, 54) if sim.moisture < 28 else sc["dirt"]
            soil_dark = sc["dirt_dark"]
        pixel_rect(screen, soil_dark, inner.move(0, 3), chamfer=CHAMFER)
        pixel_rect(screen, soil, inner, chamfer=CHAMFER)
        
        for i in range(1, 5):
            ly = inner.y + inner.h * i // 5
            pygame.draw.line(screen, mix_color(soil, (0, 0, 0), 0.12),
                             (inner.x + 10, ly), (inner.right - 10, ly), 2)
        if sim.moisture < 28:
            cx, cy = inner.centerx, inner.centery
            pygame.draw.line(screen, (82, 53, 35), (cx - 40, cy + 30), (cx - 20, cy + 40), 2)
            pygame.draw.line(screen, (82, 53, 35), (cx + 24, cy - 34), (cx + 40, cy - 24), 2)

    def _draw_paddy_field(self, screen, sim, plot_rect, season_colors):
        sc = season_colors
        inner = pygame.Rect(plot_rect.x + 22, plot_rect.y + 28, plot_rect.w - 44, plot_rect.h - 56)
        
        nm = game_state.nightmare
        if nm:
            frame_body, frame_dark = (90, 30, 28), (60, 16, 16)
            mud_dry, mud_wet = (120, 40, 34), (58, 16, 16)
            water_col = (150, 30, 30)
        else:
            frame_body, frame_dark = (100, 75, 55), (75, 55, 40)
            mud_dry, mud_wet = (158, 118, 78), (74, 58, 42)
            water_col = (66, 150, 198)

        frame = inner.inflate(16, 16)
        pixel_rect(screen, (35, 30, 25), frame.move(0, 4), chamfer=CHAMFER)
        pixel_rect(screen, frame_body, frame, chamfer=CHAMFER)
        pixel_rect(screen, frame_dark, frame, width=3, chamfer=CHAMFER)

        wet = max(0.0, min(1.0, (sim.moisture - 12) / 74.0))

        mud = mix_color(mud_dry, mud_wet, wet)
        pixel_rect(screen, mix_color(mud, (0, 0, 0), 0.25), inner.move(0, 3), chamfer=CHAMFER)
        pixel_rect(screen, mud, inner, chamfer=CHAMFER)

        base_col = (36, 100, 152) if not nm else (110, 24, 24)
        film_col = (96, 178, 214) if not nm else (172, 52, 44)
        water = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        pixel_rect(water, (*base_col, int(120 + 110 * wet)), (0, 0, inner.w, inner.h), chamfer=CHAMFER)
        film = pygame.Surface((inner.w, int(inner.h * 0.5)), pygame.SRCALPHA)
        pixel_rect(film, (*film_col, int(34 + 54 * wet)), film.get_rect(), chamfer=CHAMFER)
        water.blit(film, (0, 0))
        screen.blit(water, (inner.x, inner.y))

        hl = (214, 240, 255) if not nm else (236, 150, 140)
        # 큰 픽셀: 물 잔물결을 '각진 픽셀 대시'로 (가는 타원 외곽선 대신)
        for i in range(1, 5):
            ly = inner.y + inner.h * i // 5
            indent = 18 + (20 if i % 2 else 0)
            ln = max(30, inner.w - 2 * indent - i * 4)
            for seg in range(inner.x + indent, inner.x + indent + ln, 12):
                pygame.draw.rect(screen, hl, (seg, ly - 1, 7, 3))
        import random as _r
        _rng = _r.Random(11)
        for _ in range(6):
            sx = inner.x + _rng.randint(20, inner.w - 20)
            sy = inner.y + _rng.randint(18, inner.h - 18)
            pygame.draw.rect(screen, hl, (sx, sy, 2, 2))

        if wet < 0.18:
            for cx, cy in self.crop_positions()[:3]:
                pixel_rect(screen, mud, (cx - 20, cy - 6, 40, 14), chamfer=CHAMFER)

        mound_top = mix_color(mud, (206, 172, 118) if not nm else (150, 60, 50), 0.45)
        for cx, cy in self.crop_positions():
            pixel_rect(screen, mix_color(mud, (0, 0, 0), 0.25), (cx - 19, cy - 1, 38, 13), chamfer=CHAMFER)
            pixel_rect(screen, mud, (cx - 18, cy - 4, 36, 13), chamfer=CHAMFER)
            pixel_rect(screen, mound_top, (cx - 12, cy - 5, 24, 7), chamfer=CHAMFER_SM)
            for dx, dy in ((-6, -2), (5, -1), (0, 1)):
                pygame.draw.rect(screen, mix_color(mud, (0, 0, 0), 0.3), (cx + dx, cy + dy, 2, 2))

        for cx, cy in self.crop_positions():
            for seg in range(cx - 16, cx + 16, 9):
                pygame.draw.rect(screen, hl, (seg, cy + 6, 5, 2))

    def _draw_tree(self, screen, sim, ratio):
        ratio = max(0.0, min(1.2, ratio))
        g = min(1.0, ratio)
        PX = 6
        base_x, base_y = 225, 362

        bark_d, bark, bark_l = (74, 48, 28), (110, 72, 42), (150, 104, 62)
        leaf_d, leaf_m, leaf_l = (46, 110, 60), (72, 150, 80), (120, 196, 112)
        if game_state.nightmare:
            bark_d, bark, bark_l = (48, 24, 22), (86, 44, 36), (120, 66, 52)
            leaf_d, leaf_m, leaf_l = (72, 20, 20), (112, 30, 28), (156, 52, 42)
        fruit_c = sim.crop_cfg.get("tint") or (200, 60, 50)

        def cell(cx, cy, color):
            pygame.draw.rect(screen, color, (base_x + cx * PX - PX // 2, base_y - cy * PX - PX, PX, PX))

        shadow = pygame.Surface((150, 22), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 55), shadow.get_rect())
        screen.blit(pixelate(shadow, 4, smooth=False), (base_x - 75, base_y - 8))   # 큰 픽셀: 나무 그림자 도트화

        trunk_h = 4 + int(13 * g)

        if g < 0.16:
            lg = 0.4 + 0.6 * (g / 0.16)
            h = int(16 + 44 * (g / 0.16))
            # 큰 픽셀: 묘목(가는 줄기·잎 폴리곤)을 임시 서피스에 그린 뒤 통째로 도트화
            sap = pygame.Surface((48, h + 20), pygame.SRCALPHA)
            LX, LY = 24, h + 12
            topx, topy = LX, LY - h
            pygame.draw.line(sap, bark_d, (LX, LY), (topx, topy + 4), 4)
            pygame.draw.line(sap, bark, (LX, LY), (topx, topy + 4), 2)
            fy = topy + int(h * 0.3)
            pygame.draw.line(sap, bark, (LX, fy), (LX - int(7 * lg), fy - int(6 * lg)), 2)
            pygame.draw.line(sap, bark, (LX, fy), (LX + int(7 * lg), fy - int(6 * lg)), 2)

            def _leaf(ex, ey, s, col_d, col_m):
                w2, h2 = int(4 * lg * s), int(8 * lg * s)
                pygame.draw.polygon(sap, col_d, [(ex, ey - h2), (ex - w2, ey), (ex, ey + h2 // 2), (ex + w2, ey)])
                pygame.draw.polygon(sap, col_m, [(ex, ey - h2 + 2), (ex - w2 + 1, ey), (ex + w2 - 1, ey)])
            _leaf(LX - int(7 * lg), fy - int(6 * lg), 0.8, leaf_d, leaf_m)
            _leaf(LX + int(7 * lg), fy - int(6 * lg), 0.8, leaf_d, leaf_m)
            _leaf(topx, topy, 1.0, leaf_m, leaf_l)
            screen.blit(pixelate(sap, 3, smooth=False), (base_x - LX, base_y - LY))
            return

        for cy in range(trunk_h):
            hw = 1 if (cy / trunk_h) < 0.45 else 0
            for cx in range(-hw, hw + 1):
                cell(cx, cy, bark_l if cx < 0 else (bark if cx == 0 else bark_d))
        cell(-2, 0, bark_d); cell(2, 0, bark_d)

        def leaf_blob(cx0, cy0, rad, grow):
            if grow <= 0:
                return
            r = rad * grow
            rq = r * r + r
            ri = int(r) + 1
            for dx in range(-ri, ri + 1):
                for dy in range(-ri, ri + 1):
                    if dx * dx + dy * dy <= rq:
                        s = dx + dy
                        cell(cx0 + dx, cy0 + dy, leaf_l if s <= -1 else (leaf_d if s >= 2 else leaf_m))

        def fruit(cx, cy):
            px = base_x + cx * PX - PX // 2
            py = base_y - cy * PX - PX
            pygame.draw.rect(screen, fruit_c, (px, py, PX, PX))
            pygame.draw.rect(screen, (255, 236, 218), (px + 1, py + 1, 2, 2))

        branches = [
            (0.52, -1, 3, 0.14, 0.34),
            (0.60,  1, 3, 0.18, 0.40),
            (0.74, -1, 4, 0.28, 0.50),
            (0.82,  1, 4, 0.32, 0.54),
        ]
        tips = []
        for frac, d, length, br_g, lf_g in branches:
            if g < br_g:
                continue
            node = int(trunk_h * frac)
            grow = min(1.0, (g - br_g) / 0.16)
            steps = max(1, int(length * grow))
            tx, ty = 0, node
            for s in range(1, steps + 1):
                tx = d * s
                ty = node + int(s * 0.6)
                cell(tx, ty, bark if s % 2 else bark_l)
            lg = min(1.0, (g - lf_g) / 0.22)
            if lg > 0:
                leaf_blob(tx, ty + 1, 2.2, lg)
                tips.append((tx, ty + 1))

        apex = min(1.0, (g - 0.10) / 0.34)
        if apex > 0:
            leaf_blob(0, trunk_h + 1, 0.9 + 2.3 * apex, 1.0)
            tips.append((0, trunk_h + 1))

        if g >= 0.82 and tips:
            import random as _r
            rng = _r.Random(9)
            n = 3 if g < 1.0 else 6
            spots = tips[:]
            rng.shuffle(spots)
            for fx, fy in spots[:n]:
                fruit(fx + rng.randint(-1, 1), fy + rng.randint(-1, 1))

    def _rice_water_base(self, screen, x, y):
        sh = pygame.Surface((36, 13), pygame.SRCALPHA)
        base_shadow = (24, 12, 12, 120) if game_state.nightmare else (26, 66, 92, 115)
        pygame.draw.ellipse(sh, base_shadow, sh.get_rect())
        screen.blit(pixelate(sh, 3, smooth=False), (x - 18, y + 4))          # 큰 픽셀: 물그림자 도트화
        ring = (150, 60, 60) if game_state.nightmare else (150, 210, 235)
        for seg in range(x - 12, x + 12, 8):                   # 물 링 → 픽셀 대시
            pygame.draw.rect(screen, ring, (seg, y + 8, 5, 2))

    def _rice_blade(self, screen, bx, by, dx, dy, dark, mid, light):
        import math
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        mx = int(bx + dx * 0.55 + px * 2.4)
        my = int(by + dy * 0.55 + py * 2.4)
        tx, ty = bx + dx, by + dy
        if game_state.nightmare:
            dark, mid, light = (70, 20, 20), (110, 34, 30), (150, 60, 46)
        pygame.draw.line(screen, dark, (bx, by), (mx, my), 4)     # 큰 픽셀: 잎 굵게
        pygame.draw.line(screen, mid, (mx, my), (tx, ty), 3)
        pygame.draw.line(screen, light, (bx, by - 1), (mx, my - 1), 2)

    def _rice_ear(self, screen, bx, by, side):
        gold_d = (150, 60, 46) if game_state.nightmare else (196, 164, 52)
        gold_l = (196, 90, 70) if game_state.nightmare else (246, 224, 120)
        midx, midy = bx + side * 7, by + 3
        tipx, tipy = bx + side * 11, by + 15
        pygame.draw.line(screen, gold_d, (bx, by), (midx, midy), 3)
        pygame.draw.line(screen, gold_d, (midx, midy), (tipx, tipy), 3)
        grains = [(bx, by), (midx, midy), ((midx + tipx) // 2, (midy + tipy) // 2), (tipx, tipy)]
        for i, (gx, gy) in enumerate(grains):                  # 큰 픽셀: 낟알을 각진 도트로
            pygame.draw.rect(screen, gold_l if i % 2 == 0 else gold_d, (gx - 2, gy - 2, 4, 4))

    def draw_crop(self, screen, sim, x, y, growth_stage, crop_idx=0):
        offset_val = sim.crop_offsets[crop_idx] if crop_idx < len(sim.crop_offsets) else 0
        adj_stage = max(0, growth_stage + offset_val)

        if adj_stage < 5:
            if game_state.crop == "rice":
                self._rice_water_base(screen, x, y)
                gd, gm, gl = (40, 120, 58), (78, 168, 92), (150, 220, 120)
                for dx, dy in [(-3, -9), (0, -13), (3, -9)]:
                    self._rice_blade(screen, x, y + 8, dx, dy, gd, gm, gl)
                return
            if game_state.crop != "carrot":
                self._draw_seeds(screen, x, y)
            return

        if game_state.crop != "rice":
            screen.blit(sprites["dirt_patch"], (x - 13, y - 12))

        if game_state.crop == "potato" and adj_stage < sim.growth_goal:
            if adj_stage < 10:
                leaves = [(-6, 3, 5), (5, 2, 5), (0, -3, 6)]
                flower = False
            elif adj_stage < 16:
                leaves = [(-9, 4, 6), (8, 3, 6), (-3, -3, 7), (6, -5, 6), (0, -10, 6)]
                flower = False
            else:
                leaves = [(-12, 5, 7), (11, 4, 7), (-5, -1, 8), (7, -4, 8), (-2, -11, 7), (5, -12, 6)]
                flower = True
            # 큰 픽셀: 잎·꽃(둥근 벡터)을 임시 서피스에 그린 뒤 통째로 도트화 → 도트 잎으로 통일
            plant = pygame.Surface((56, 52), pygame.SRCALPHA)
            ox2, oy2 = 28, 30
            pygame.draw.line(plant, (70, 120, 60), (ox2, oy2 + 10), (ox2, oy2 - 6), 2)
            for lx, ly, lr in leaves:
                pygame.draw.circle(plant, (48, 108, 54), (ox2 + lx, oy2 + ly + 1), lr)
                pygame.draw.circle(plant, (80, 152, 78), (ox2 + lx, oy2 + ly), lr)
                pygame.draw.circle(plant, (122, 192, 110), (ox2 + lx - 2, oy2 + ly - 2), max(2, lr // 2))
            if flower:
                for fx, fy in [(-8, -6), (7, -8)]:
                    pygame.draw.circle(plant, (240, 238, 248), (ox2 + fx, oy2 + fy), 3)
                    pygame.draw.circle(plant, (234, 202, 92), (ox2 + fx, oy2 + fy), 1)
            screen.blit(pixelate(plant, 3, smooth=False), (x - ox2, y - oy2))
            return

        if game_state.crop == "rice" and adj_stage < sim.growth_goal:
            self._rice_water_base(screen, x, y)
            gd, gm, gl = (40, 120, 58), (78, 168, 92), (150, 220, 120)
            if adj_stage < 10:
                blades = [(-3, -15), (0, -20), (3, -15)]
            elif adj_stage < 16:
                blades = [(-5, -18), (-2, -25), (2, -25), (5, -18)]
            else:
                blades = [(-7, -21), (-3, -29), (0, -34), (2, -34), (5, -29), (8, -21)]
            for dx, dy in blades:
                self._rice_blade(screen, x, y + 8, dx, dy, gd, gm, gl)
            return

        if adj_stage < 10:
            sprite, offset = sprites["sprout1"], (-15, 9)
        elif adj_stage < 16:
            sprite, offset = sprites["sprout2"], (-20, -2)
        elif adj_stage < 23:
            sprite, offset = sprites["sprout3"], (-22, -12)
        elif adj_stage < sim.growth_goal:
            sprite, offset = sprites["sprout4"], (-24, -18)
        else:
            if game_state.crop == "potato":
                orig_spr = sprites["sprout4"]
                withered = orig_spr.copy()
                tint = pygame.Surface(withered.get_size(), pygame.SRCALPHA)
                tint.fill((160, 150, 40, 95))
                withered.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                sh = withered.get_height()
                withered = pygame.transform.scale(withered, (withered.get_width(), int(sh * 0.85)))
                
                sprite, offset = withered, (-24, -18 + int(sh * 0.15))
                screen.blit(sprite, (x + offset[0], y + offset[1]))
                
                pygame.draw.ellipse(screen, (78, 52, 32), (x - 15, y - 1, 14, 9))
                pygame.draw.ellipse(screen, (150, 108, 66), (x - 14, y - 2, 12, 7))
                pygame.draw.ellipse(screen, (78, 52, 32), (x + 1, y + 2, 12, 8))
                pygame.draw.ellipse(screen, (150, 108, 66), (x + 2, y + 1, 10, 6))
                return
            elif game_state.crop == "rice":
                self._rice_water_base(screen, x, y)
                gd, gm, gl = (150, 120, 36), (196, 166, 60), (236, 214, 120)
                for dx, dy in [(-6, -17), (-2, -24), (2, -24), (6, -17)]:
                    self._rice_blade(screen, x, y + 8, dx, dy, gd, gm, gl)
                self._rice_ear(screen, x - 8, y - 15, -1)
                self._rice_ear(screen, x + 8, y - 17, 1)
                self._rice_ear(screen, x, y - 20, 0)
                return
            else:
                sprite, offset = sprites["carrot"], (-24, -45)
        screen.blit(sprite, (x + offset[0], y + offset[1]))

    def draw_farm_plot(self, screen, farm_scene):
        sim = farm_scene.sim
        draw_light_panel(screen, PLOT)

        if sim.is_tree:
            self._draw_plain_soil(screen, sim, PLOT, farm_scene.season_colors)
        elif game_state.crop == "rice":
            self._draw_paddy_field(screen, sim, PLOT, farm_scene.season_colors)
        elif "field_bed" in sprites:
            screen.blit(sprites["field_bed"], (PLOT.x, PLOT.y))
        else:
            inner_plot = pygame.Rect(66, 168, 318, 256)
            sc = farm_scene.season_colors
            base_color = (110, 75, 45) if sim.moisture > 72 else (135, 92, 60) if sim.moisture < 28 else sc["dirt"]
            frame_rect = inner_plot.inflate(16, 16)
            pixel_rect(screen, (40, 30, 25), frame_rect.move(0, 4), chamfer=CHAMFER)
            pixel_rect(screen, (132, 83, 48), frame_rect, chamfer=CHAMFER)
            pixel_rect(screen, (185, 125, 80), frame_rect, width=3, chamfer=CHAMFER)
            pixel_rect(screen, (65, 42, 28), inner_plot.inflate(2, 2), width=2, chamfer=CHAMFER)
            bed_bg_color = (80, 52, 36) if sim.moisture > 72 else (100, 66, 46) if sim.moisture < 28 else sc["dirt_dark"]
            pixel_rect(screen, bed_bg_color, inner_plot, chamfer=CHAMFER)
            pw, ph = 88, 92
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x - pw // 2, y + 12 - ph // 2
                patch_rect = pygame.Rect(px, py, pw, ph)
                pixel_rect(screen, sc["dirt_dark"], patch_rect.move(0, 3), chamfer=CHAMFER)
                pixel_rect(screen, base_color, patch_rect, chamfer=CHAMFER)
                pixel_rect(screen, mix_color(base_color, (255, 235, 180), 0.16), patch_rect, width=2, chamfer=CHAMFER)

        if not sim.is_tree and game_state.crop != "rice" and sim.moisture < 28:
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x, y + 12
                pygame.draw.line(screen, (82, 53, 35), (px - 22, py - 14), (px - 10, py - 8), 2)
                pygame.draw.line(screen, (82, 53, 35), (px + 10, py + 14), (px + 22, py + 18), 2)
        elif not sim.is_tree and game_state.crop != "rice" and sim.moisture > 72:
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x - 18, y + 36
                pygame.draw.ellipse(screen, (95, 130, 155), (px, py, 36, 6))

        growth_stage = max(0, min(sim.growth, sim.growth_goal))
        if sim.is_tree:
            self._draw_tree(screen, sim, sim.growth / max(1, sim.growth_goal))
        else:
            for idx, (x, y) in enumerate(self.crop_positions()):
                self.draw_crop(screen, sim, x, y, growth_stage, idx)

        if farm_scene.interaction is None:
            if not sim.no_weeds and sim.weeds > 32:
                weed_count = 2 if sim.weeds < 55 else 4
                weed_spots = [(86, 373), (258, 371), (348, 262), (166, 264)]
                weed_spr = sprites["weed_nm"] if game_state.nightmare else sprites["weed"]
                for x, y in weed_spots[:weed_count]:
                    screen.blit(weed_spr, (x, y))

            if sim.pests > 32:
                bug_count = 1 if sim.pests < 55 else 3
                bug_spots = [(150, 228), (284, 336), (332, 220)]
                for x, y in bug_spots[:bug_count]:
                    screen.blit(sprites["bug"], (x, y))

    def draw(self, screen, farm_scene):
        sim = farm_scene.sim
        sc = farm_scene.season_colors
        # 적응형 대시보드: 넓은 화면이면 여백에 사이드 패널(상시), 좁은 화면이면 상단 팝업 토글(잠깐 띄움).
        parent = screen.get_parent()
        ox = screen.get_offset()[0] if parent else 0
        wide = bool(parent) and ox >= 122
        overlay_open = (not wide) and getattr(game_state, "dashboard_open", False)
        farm_scene._dash_wide = wide   # 입력 처리(좁은 화면 토글)에서 참조
        draw_tiled_background(screen, 800, 600, sc["grass"], sc["grass_dark"],
                              sc["dirt"], sc["dirt_dark"])

        for f in farm_scene.fireflies:
            # '계단 알파' 도트 글로우(캐시) — 평균축소 pixelate 는 모자이크 블러로 보였다
            alpha = int(120 + 80 * math.sin(f['scale_timer']))
            alpha = max(0, min(255, alpha))
            g = glow_sprite(f['size'] * 2.5, (255, 235, 140), px=3,
                            steps=(115,), core=((255, 255, 200), 255))
            blit_glow(screen, g, (f['x'], f['y']), alpha)

        self.draw_farm_plot(screen, farm_scene)

        hour = datetime.datetime.now().hour
        tint = pygame.Surface((800, 600), pygame.SRCALPHA)
        if 4 <= hour <= 6:
            tint.fill((30, 20, 60, 70))
        elif 17 <= hour <= 19:
            tint.fill((100, 40, 0, 50))
        elif hour >= 20 or hour <= 3:
            tint.fill((10, 15, 30, 100))

        if hour < 7 or hour >= 17:
            screen.blit(tint, (0, 0))

        self._draw_ambient(screen)   # 날씨 앰비언트 (비/강풍 잎/가뭄 먼지/구름 그림자/나비)

        # 계절 전환 배너 — 잔잔하게 떠올랐다 스러진다
        sbt = getattr(sim, "season_banner_timer", 0)
        if sbt > 0 and sim.season_banner:
            appear = min(1.0, (3.2 - sbt) / 0.45)          # 떠오름
            fade = min(1.0, sbt / 0.7)                     # 스러짐
            a = max(0, min(255, int(240 * appear * fade)))
            bf = get_font(24)
            ts = bf.render(i18n.tf("{season}이 왔다", season=i18n.t(sim.season_banner)),
                           True, (255, 240, 206))
            pill_w, pill_h = ts.get_width() + 44, ts.get_height() + 18
            pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
            pixel_rect(pill, (30, 34, 30, int(a * 0.82)), (0, 0, pill_w, pill_h), chamfer=CHAMFER)
            pixel_rect(pill, (229, 192, 124, a), (0, 0, pill_w, pill_h), width=1, chamfer=CHAMFER)
            ts.set_alpha(a)
            px0 = PLOT.centerx - pill_w // 2
            py0 = 150 - int(6 * (1 - appear))
            screen.blit(pill, (px0, py0))
            screen.blit(ts, (px0 + 22, py0 + 9))

        title_font = get_font(20)
        season_name = get_season(sim.growth, sim.growth_goal)
        if game_state.dad_mode:
            prefix = i18n.tf("[{season}] 아버지의 밭 ", season=i18n.t(season_name))
        else:
            prefix = i18n.tf("[{season}] {day}일째 ", season=i18n.t(season_name), day=sim.day)

        prefix_surf = title_font.render(prefix, True, TEXT_DARK)
        weather_text = i18n.tf("{weather} ({turns}일간)", weather=i18n.t(game_state.weather),
                               turns=game_state.weather_turns_left)
        weather_surf = title_font.render(weather_text, True, TEXT_DARK)
        
        title_rect = pygame.Rect(50, 82, 350, 48)
        draw_wood_panel(screen, title_rect)
        
        total_w = prefix_surf.get_width() + 25 + weather_surf.get_width()
        tx = title_rect.centerx - total_w // 2
        ty = title_rect.centery - prefix_surf.get_height() // 2
        
        screen.blit(prefix_surf, (tx, ty))
        draw_weather_icon(screen, game_state.weather, tx + prefix_surf.get_width(), ty + 2, 20)
        screen.blit(weather_surf, (tx + prefix_surf.get_width() + 25, ty))

        self.draw_field_summary(screen, sim)
        self.draw_meters(screen, sim)
        
        # 메뉴 열림 시 닫기 버튼(바닥 y=478)이 패널 밖으로 2px 나가던 것 → 높이 여유 확보
        panel_h = 182 if farm_scene.action_menu_open else 164
        action_panel = pygame.Rect(430, 300, 320, panel_h)
        draw_light_panel(screen, action_panel)
        action_title = get_font(20).render("오늘 할 일", True, TEXT_DARK)
        screen.blit(action_title, (450, 306))

        if not (wide or overlay_open):   # 대시보드가 예보를 보여줄 땐 중앙 To-Do에선 뺀다(중복 제거)
            forecast_font = get_font(14)
            fc_text = i18n.tf("예보: {weather} ({turns}일 뒤)", weather=i18n.t(game_state.next_weather),
                              turns=game_state.weather_turns_left)
            fc = forecast_font.render(fc_text, True, TEXT_MUTED)
            fc_x = 738 - fc.get_width()
            screen.blit(fc, (fc_x, 308))
            draw_weather_icon(screen, game_state.next_weather, fc_x - 22, 306, 16)

        for btn in farm_scene.buttons:
            btn.draw(screen)
        self.draw_action_scrollbar(screen, farm_scene)

        draw_top_bar(screen, show_stats=False)

        if sim.thought_text:
            tf = get_font(15)
            alpha = 1.0 if sim.thought_timer > 1.0 else max(0.0, sim.thought_timer)
            line = wrap_text(sim._cropify(sim.thought_text), tf, 330, max_lines=1)[0]
            ts = tf.render(line, True, (245, 232, 198))
            pad = 12
            pill_w = ts.get_width() + pad * 2
            pill_h = ts.get_height() + 8
            px = 225 - pill_w // 2
            py = 460
            pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
            pixel_rect(pill, (28, 24, 20, int(205 * alpha)), (0, 0, pill_w, pill_h), chamfer=CHAMFER)
            pixel_rect(pill, (150, 120, 80, int(220 * alpha)), (0, 0, pill_w, pill_h), width=1, chamfer=CHAMFER)
            screen.blit(pill, (px, py))
            ts.set_alpha(int(255 * alpha))
            screen.blit(ts, (px + pad, py + 4))

        # '살펴보기' 결과 메시지는 조사·상태가 합쳐진 동적 문구라, 저장된 것을 쓰면 언어 전환이 한 턴
        # 늦게 반영된다. 매 프레임 현재 언어로 다시 생성해 즉시 반영되게 한다(inspect_message는 부작용 없음).
        msg = sim.inspect_message() if sim.last_action == "살펴보기" else sim.message
        draw_bottom_bar(screen, "농장 일지", sim._cropify(f"{msg}\n{sim.notice}"))
        if not farm_scene.interaction:
            self._draw_journal_button(screen)   # 지난 일지 열람 (J)

        if farm_scene.forced_wait_active:
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((200, 30, 30, int(20 + 20 * pulse)))
            screen.blit(overlay, (0, 0))
            
            timer_box = pygame.Rect(220, 20, 360, 42)
            draw_panel(screen, timer_box, fill=(255, 230, 230), border=(200, 50, 50))
            
            timer_font = get_font(16)
            timer_text = i18n.tf("돌발 상황 해결 중! 남은 시간: {t}초", t=f"{farm_scene.forced_wait_timer:.1f}")
            ts = timer_font.render(timer_text, True, (200, 30, 30))
            screen.blit(ts, (400 - ts.get_width() // 2, 31))

        if farm_scene.interaction:
            farm_scene.interaction.draw(screen)

        if not farm_scene.tutorial_active:
            if wide:
                oy_off = screen.get_offset()[1] if parent else 0
                self.draw_side_dashboard(parent, ox, farm_scene, oy=oy_off)  # 넓은 화면: 사이드 상시
            elif parent:
                self._draw_dash_button(screen, overlay_open)               # 좁은 화면: 상단 팝업 토글
                if overlay_open:
                    self.draw_top_overlay(screen, farm_scene)

        if getattr(farm_scene, "journal_open", False):
            self._draw_journal_popup(screen, farm_scene)

        if farm_scene.tutorial_active:
            self.draw_tutorial(screen, farm_scene)

    _WEATHER_TIP = {
        "비": "곧 비 예보 — 물주기는 아껴 두자.",
        "가뭄": "가뭄이 온다 — 물을 넉넉히.",
        "강풍": "강풍 예보 — 잡초·해충을 미리 정리.",
        "흐림": "흐린 날엔 수분이 더디 마른다.",
        "맑음": "맑을 땐 수분을 자주 살피자.",
    }

    def _panel_card(self, parent, px, y0, w, title, build):
        """내용 높이에 맞춰(빈 여백 없이) 패널을 그린다. build(temp, start_y)가 내용을 그리고 마지막 y를 반환."""
        MAXH = 470
        temp = pygame.Surface((w, MAXH), pygame.SRCALPHA)
        t = get_font(15).render(i18n.t(title), True, (92, 66, 42))
        temp.blit(t, (w // 2 - t.get_width() // 2, 11))
        pygame.draw.rect(temp, (203, 160, 96), (12, 33, w - 24, 2))
        h = min(MAXH, build(temp, 46) + 14)
        draw_light_panel(parent, pygame.Rect(px, y0, w, h))
        parent.blit(temp.subsurface((0, 0, w, h)), (px, y0))

    def draw_side_dashboard(self, parent, ox, farm_scene, oy=0):
        """넓은 화면 여백의 사이드 대시보드 — 왼쪽 '계절 수첩'(달력·예보), 오른쪽 '밭 노트'(요약). 높이는 내용에 맞춤.
        oy: 안전영역 세로 오프셋 — 상하 여백도 있는 화면(폴더블·울트라와이드 캡)에서 카드가
        상단 바 위로 떠오르지 않게 안전영역 기준 y(88)에 더한다."""
        sim = farm_scene.sim
        f_l, f_b = get_font(12), get_font(12)
        gold, brown = (150, 110, 60), (74, 92, 60)
        w = ox - 20

        def build_left(s, y):
            season = get_season(sim.growth, sim.growth_goal)
            for ln in wrap_text(i18n.tf("{season} · {day}일째", season=i18n.t(season), day=sim.day), f_b, w - 24):
                s.blit(f_b.render(ln, True, brown), (12, y)); y += 17
            if getattr(game_state, "year_seed", "평년") != "평년":
                for ln in wrap_text(i18n.tf("올해: {seed}", seed=i18n.t(game_state.year_seed)), f_b, w - 24):
                    s.blit(f_b.render(ln, True, (150, 110, 60)), (12, y)); y += 17
            y += 9
            s.blit(f_l.render(i18n.t("날씨"), True, gold), (12, y)); y += 18
            s.blit(f_l.render(i18n.t("오늘"), True, brown), (12, y)); y += 15
            draw_weather_icon(s, game_state.weather, 21, y + 8, 15)
            s.blit(f_b.render(i18n.t(game_state.weather), True, TEXT_DARK), (38, y + 1)); y += 22
            s.blit(f_l.render(i18n.tf("{n}일 뒤", n=game_state.weather_turns_left), True, brown), (12, y)); y += 15
            draw_weather_icon(s, game_state.next_weather, 21, y + 8, 15)
            s.blit(f_b.render(i18n.t(game_state.next_weather), True, TEXT_DARK), (38, y + 1)); y += 24
            tip = self._WEATHER_TIP.get(game_state.next_weather)
            if tip:
                pygame.draw.rect(s, (223, 200, 160), (12, y, w - 24, 1)); y += 9
                for ln in wrap_text(i18n.t(tip), f_b, w - 24):
                    s.blit(f_b.render(ln, True, (110, 92, 66)), (12, y)); y += 17
            return y

        def build_right(s, y):
            from core.game_state import get_understanding_stage
            _, stage, _ = get_understanding_stage(game_state.understanding)
            rows = [(i18n.t("이해"), i18n.t(stage)),
                    (i18n.t("실수"), str(sim.mistakes)),
                    (i18n.t("밭 상태"), i18n.t("평온" if sim.is_good_turn() else "손이 필요해"))]
            for label, val in rows:
                s.blit(f_l.render(label, True, gold), (12, y)); y += 16
                for ln in wrap_text(val, f_b, w - 26)[:2]:
                    s.blit(f_b.render(ln, True, TEXT_DARK), (18, y)); y += 15
                y += 11
            return y - 11

        self._panel_card(parent, 14, oy + 88, w, "계절 수첩", build_left)
        self._panel_card(parent, ox + 800 + 6, oy + 88, w, "밭 노트", build_right)

    def _draw_dash_button(self, screen, is_open):
        """좁은 화면용 '밭 수첩' 토글 버튼 — 클릭하면 상단 팝업이 열리고 닫힌다."""
        r = DASH_BTN
        draw_panel(screen, r, fill=(44, 57, 58), border=(229, 192, 124), radius=8)
        label = i18n.t("밭 수첩") + ("  ▴" if is_open else "  ▾")
        t = get_font(13).render(label, True, (240, 224, 190))
        screen.blit(t, (r.centerx - t.get_width() // 2, r.centery - t.get_height() // 2))

    def draw_top_overlay(self, screen, farm_scene):
        """좁은 화면에서 '밭 수첩' 버튼을 누르면 상단에 잠깐 뜨는 가로형 요약 패널(계절 수첩 + 밭 노트)."""
        sim = farm_scene.sim
        panel = pygame.Rect(46, 74, 708, 110)
        draw_light_panel(screen, panel)
        f_l, f_b = get_font(12), get_font(13)
        gold, brown = (150, 110, 60), (74, 92, 60)
        # ── 왼쪽: 계절 · 날씨 · 예보 · 팁 ──
        x = 66
        season = get_season(sim.growth, sim.growth_goal)
        screen.blit(f_b.render(i18n.tf("{season} · {day}일째", season=i18n.t(season), day=sim.day), True, brown), (x, 88))
        draw_weather_icon(screen, game_state.weather, x + 8, 122, 16)
        screen.blit(f_b.render(i18n.tf("오늘 · {w}", w=i18n.t(game_state.weather)), True, TEXT_DARK), (x + 26, 114))
        draw_weather_icon(screen, game_state.next_weather, x + 8, 148, 16)
        screen.blit(f_b.render(i18n.tf("{n}일 뒤 · {w}", n=game_state.weather_turns_left, w=i18n.t(game_state.next_weather)), True, TEXT_DARK), (x + 26, 140))
        tip = self._WEATHER_TIP.get(game_state.next_weather)
        if tip:
            for i, ln in enumerate(wrap_text(i18n.t(tip), f_b, 210)):
                screen.blit(f_b.render(ln, True, (110, 92, 66)), (x + 175, 114 + i * 18))
        pygame.draw.rect(screen, (223, 200, 160), (452, 92, 1, 74))
        # ── 오른쪽: 밭 노트 요약 ──
        rx = 474
        from core.game_state import get_understanding_stage
        _, stage, _ = get_understanding_stage(game_state.understanding)
        stats = [(i18n.t("이해"), i18n.t(stage)),
                 (i18n.t("실수"), str(sim.mistakes)),
                 (i18n.t("밭 상태"), i18n.t("평온" if sim.is_good_turn() else "손이 필요해"))]
        sy = 92
        for label, val in stats:
            screen.blit(f_l.render(label, True, gold), (rx, sy))
            for i, ln in enumerate(wrap_text(val, f_b, 210)[:1]):
                screen.blit(f_b.render(ln, True, TEXT_DARK), (rx + 96, sy - 1))
            sy += 24
        self._draw_dash_button(screen, True)   # 버튼(닫기 ▴)을 오버레이 위에 다시 얹음

    def draw_tutorial(self, screen, farm_scene):
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((10, 12, 18, 185))
        screen.blit(overlay, (0, 0))

        title, body = farm_scene.TUTORIAL_PAGES[farm_scene.tutorial_step]
        title = farm_scene.sim._cropify(title)
        body = farm_scene.sim._cropify(body)
        card = pygame.Rect(120, 180, 560, 252)
        draw_light_panel(screen, card)

        # 제목: 카드 폭에 맞춰 폰트 자동 축소(영어가 길어 넘치지 않게). size()도 현재 언어로 측정.
        title_font = get_font(23)
        for sz in (23, 21, 19, 17):
            title_font = get_font(sz)
            if title_font.size(title)[0] <= card.w - 48:
                break
        title_surf = title_font.render(title, True, TEXT_DARK)
        title_y = card.y + 24
        screen.blit(title_surf, (card.centerx - title_surf.get_width() // 2, title_y))
        # 강조 바 — 고정 120px 은 긴 영어 제목에서 중간 단어 밑줄처럼 보였다
        # → 제목 폭에 비례(상한 160px), y 도 제목 높이 기준으로 간격 일정하게. 색은 팔레트 GOLD.
        bar_w = min(title_surf.get_width(), 160)
        bar_y = title_y + title_surf.get_height() + 7
        pygame.draw.rect(screen, GOLD, (card.centerx - bar_w // 2, bar_y, bar_w, 3))

        # 본문: 폭에 맞춰 줄바꿈하고, 세로로 넘치면 폰트를 줄여 카드 안에 맞춘다.
        body_top = card.y + 76
        avail_h = (card.bottom - 34) - body_top   # 하단 진행표시(step) 공간 확보
        body_font = get_font(17)
        lines = wrap_text(body, body_font, card.w - 56)
        for sz in (17, 16, 15, 14, 13):
            body_font = get_font(sz)
            lines = wrap_text(body, body_font, card.w - 56)
            if len(lines) * (body_font.get_height() + 6) <= avail_h:
                break
        # 짧은 페이지에서 하단이 텅 비지 않게, 본문 블록을 가용 영역 세로 중앙에 배치
        block_h = len(lines) * (body_font.get_height() + 6) - 6
        y = body_top + max(0, (avail_h - block_h) // 2)
        for line in lines:
            ls = body_font.render(line, True, TEXT_DARK)
            screen.blit(ls, (card.x + 28, y))
            y += body_font.get_height() + 6

        last_page = farm_scene.tutorial_step >= len(farm_scene.TUTORIAL_PAGES) - 1
        step_txt = i18n.tf("{step} / {total}   ·   클릭하여 시작" if last_page
                           else "{step} / {total}   ·   클릭하여 계속",
                           step=farm_scene.tutorial_step + 1, total=len(farm_scene.TUTORIAL_PAGES))
        ss = get_font(14).render(step_txt, True, TEXT_MUTED)
        screen.blit(ss, (card.centerx - ss.get_width() // 2, card.bottom - 26))
