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

TEXT_DARK = (48, 38, 28)
TEXT_MUTED = (123, 106, 92)
PLOT = pygame.Rect(44, 140, 362, 318)


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

    def draw_compact_meter(self, screen, label, value, x, y, color):
        font = get_font(14)
        label_surf = font.render(label, True, TEXT_DARK)
        screen.blit(label_surf, (x, y - 1))
        bar_right = x + 134
        bar_x = x + max(48, label_surf.get_width() + 6)
        bar = pygame.Rect(bar_x, y, bar_right - bar_x, 13)
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
        health_text = status_font.render(i18n.tf("건강 {grade}", grade=i18n.t(sim.grade_text(sim.health))), True, TEXT_DARK)
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
            self.draw_compact_meter(screen, "해충", sim.pests, c1, 232, (210, 110, 60))
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
        pygame.draw.rect(screen, (198, 166, 118), track, border_radius=4)
        thumb_h = max(22, int(track.h * 4 / len(actions)))
        max_scroll = max(1, len(actions) - 4)
        thumb_y = track.y + int((track.h - thumb_h) * farm_scene.action_scroll / max_scroll)
        thumb = pygame.Rect(track.x, thumb_y, track.w, thumb_h)
        pygame.draw.rect(screen, (123, 92, 65), thumb, border_radius=4)

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
        pygame.draw.rect(screen, (40, 30, 25) if not nm else (28, 8, 8), frame.move(0, 4), border_radius=18)
        pygame.draw.rect(screen, (132, 83, 48) if not nm else (96, 32, 30), frame, border_radius=18)
        pygame.draw.rect(screen, (185, 125, 80) if not nm else (150, 45, 42), frame, 3, border_radius=18)
        
        if nm:
            soil = (78, 20, 18) if sim.moisture > 72 else (116, 40, 34) if sim.moisture < 28 else (96, 30, 28)
            soil_dark = (48, 12, 12)
        else:
            soil = (96, 62, 42) if sim.moisture > 72 else (120, 82, 54) if sim.moisture < 28 else sc["dirt"]
            soil_dark = sc["dirt_dark"]
        pygame.draw.rect(screen, soil_dark, inner.move(0, 3), border_radius=14)
        pygame.draw.rect(screen, soil, inner, border_radius=14)
        
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
        pygame.draw.rect(screen, (35, 30, 25), frame.move(0, 4), border_radius=18)
        pygame.draw.rect(screen, frame_body, frame, border_radius=18)
        pygame.draw.rect(screen, frame_dark, frame, 3, border_radius=18)

        wet = max(0.0, min(1.0, (sim.moisture - 12) / 74.0))

        mud = mix_color(mud_dry, mud_wet, wet)
        pygame.draw.rect(screen, mix_color(mud, (0, 0, 0), 0.25), inner.move(0, 3), border_radius=14)
        pygame.draw.rect(screen, mud, inner, border_radius=14)

        base_col = (36, 100, 152) if not nm else (110, 24, 24)
        film_col = (96, 178, 214) if not nm else (172, 52, 44)
        water = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        pygame.draw.rect(water, (*base_col, int(120 + 110 * wet)), (0, 0, inner.w, inner.h), border_radius=14)
        film = pygame.Surface((inner.w, int(inner.h * 0.5)), pygame.SRCALPHA)
        pygame.draw.rect(film, (*film_col, int(34 + 54 * wet)), film.get_rect(),
                         border_top_left_radius=14, border_top_right_radius=14)
        water.blit(film, (0, 0))
        screen.blit(water, (inner.x, inner.y))

        hl = (214, 240, 255) if not nm else (236, 150, 140)
        for i in range(1, 5):
            ly = inner.y + inner.h * i // 5
            indent = 18 + (20 if i % 2 else 0)
            ln = max(30, inner.w - 2 * indent - i * 4)
            pygame.draw.ellipse(screen, hl, (inner.x + indent, ly - 3, ln, 7), 1)
        import random as _r
        _rng = _r.Random(11)
        for _ in range(6):
            sx = inner.x + _rng.randint(20, inner.w - 20)
            sy = inner.y + _rng.randint(18, inner.h - 18)
            pygame.draw.circle(screen, hl, (sx, sy), 1)

        if wet < 0.18:
            for cx, cy in self.crop_positions()[:3]:
                pygame.draw.ellipse(screen, mud, (cx - 20, cy - 6, 40, 16))

        mound_top = mix_color(mud, (206, 172, 118) if not nm else (150, 60, 50), 0.45)
        for cx, cy in self.crop_positions():
            pygame.draw.ellipse(screen, mix_color(mud, (0, 0, 0), 0.25), (cx - 19, cy - 1, 38, 15))
            pygame.draw.ellipse(screen, mud, (cx - 18, cy - 4, 36, 15))
            pygame.draw.ellipse(screen, mound_top, (cx - 12, cy - 5, 24, 8))
            for dx, dy in ((-6, -2), (5, -1), (0, 1)):
                pygame.draw.rect(screen, mix_color(mud, (0, 0, 0), 0.3), (cx + dx, cy + dy, 2, 2))

        for cx, cy in self.crop_positions():
            pygame.draw.ellipse(screen, hl, (cx - 18, cy + 5, 36, 10), 1)
            pygame.draw.ellipse(screen, hl, (cx - 10, cy + 7, 20, 6), 1)

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
        screen.blit(shadow, (base_x - 75, base_y - 8))

        trunk_h = 4 + int(13 * g)

        if g < 0.16:
            lg = 0.4 + 0.6 * (g / 0.16)
            h = int(16 + 44 * (g / 0.16))
            topx, topy = base_x, base_y - h
            pygame.draw.line(screen, bark_d, (base_x, base_y), (topx, topy + 4), 4)
            pygame.draw.line(screen, bark, (base_x, base_y), (topx, topy + 4), 2)
            fy = topy + int(h * 0.3)
            pygame.draw.line(screen, bark, (base_x, fy), (base_x - int(7 * lg), fy - int(6 * lg)), 2)
            pygame.draw.line(screen, bark, (base_x, fy), (base_x + int(7 * lg), fy - int(6 * lg)), 2)
            def _leaf(ex, ey, s, col_d, col_m):
                w2, h2 = int(4 * lg * s), int(8 * lg * s)
                pygame.draw.polygon(screen, col_d, [(ex, ey - h2), (ex - w2, ey), (ex, ey + h2 // 2), (ex + w2, ey)])
                pygame.draw.polygon(screen, col_m, [(ex, ey - h2 + 2), (ex - w2 + 1, ey), (ex + w2 - 1, ey)])
            _leaf(base_x - int(7 * lg), fy - int(6 * lg), 0.8, leaf_d, leaf_m)
            _leaf(base_x + int(7 * lg), fy - int(6 * lg), 0.8, leaf_d, leaf_m)
            _leaf(topx, topy, 1.0, leaf_m, leaf_l)
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
        screen.blit(sh, (x - 18, y + 4))
        ring = (150, 60, 60) if game_state.nightmare else (150, 210, 235)
        pygame.draw.ellipse(screen, ring, (x - 12, y + 6, 24, 6), 1)

    def _rice_blade(self, screen, bx, by, dx, dy, dark, mid, light):
        import math
        L = math.hypot(dx, dy) or 1.0
        px, py = -dy / L, dx / L
        mx = int(bx + dx * 0.55 + px * 2.4)
        my = int(by + dy * 0.55 + py * 2.4)
        tx, ty = bx + dx, by + dy
        if game_state.nightmare:
            dark, mid, light = (70, 20, 20), (110, 34, 30), (150, 60, 46)
        pygame.draw.line(screen, dark, (bx, by), (mx, my), 3)
        pygame.draw.line(screen, mid, (mx, my), (tx, ty), 2)
        pygame.draw.line(screen, light, (bx, by - 1), (mx, my - 1), 1)

    def _rice_ear(self, screen, bx, by, side):
        gold_d = (150, 60, 46) if game_state.nightmare else (196, 164, 52)
        gold_l = (196, 90, 70) if game_state.nightmare else (246, 224, 120)
        midx, midy = bx + side * 7, by + 3
        tipx, tipy = bx + side * 11, by + 15
        pygame.draw.line(screen, gold_d, (bx, by), (midx, midy), 2)
        pygame.draw.line(screen, gold_d, (midx, midy), (tipx, tipy), 2)
        grains = [(bx, by), (midx, midy), ((midx + tipx) // 2, (midy + tipy) // 2), (tipx, tipy)]
        for i, (gx, gy) in enumerate(grains):
            pygame.draw.circle(screen, gold_l if i % 2 == 0 else gold_d, (gx, gy), 2)

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
            pygame.draw.line(screen, (70, 120, 60), (x, y + 10), (x, y - 6), 2)
            for lx, ly, lr in leaves:
                pygame.draw.circle(screen, (48, 108, 54), (x + lx, y + ly + 1), lr)
                pygame.draw.circle(screen, (80, 152, 78), (x + lx, y + ly), lr)
                pygame.draw.circle(screen, (122, 192, 110), (x + lx - 2, y + ly - 2), max(2, lr // 2))
            if flower:
                for fx, fy in [(-8, -6), (7, -8)]:
                    pygame.draw.circle(screen, (240, 238, 248), (x + fx, y + fy), 3)
                    pygame.draw.circle(screen, (234, 202, 92), (x + fx, y + fy), 1)
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
            pygame.draw.rect(screen, (40, 30, 25), frame_rect.move(0, 4), border_radius=18)
            pygame.draw.rect(screen, (132, 83, 48), frame_rect, border_radius=18)
            pygame.draw.rect(screen, (185, 125, 80), frame_rect, 3, border_radius=18)
            pygame.draw.rect(screen, (65, 42, 28), inner_plot.inflate(2, 2), 2, border_radius=14)
            bed_bg_color = (80, 52, 36) if sim.moisture > 72 else (100, 66, 46) if sim.moisture < 28 else sc["dirt_dark"]
            pygame.draw.rect(screen, bed_bg_color, inner_plot, border_radius=12)
            pw, ph = 88, 92
            for idx, (x, y) in enumerate(self.crop_positions()):
                px, py = x - pw // 2, y + 12 - ph // 2
                patch_rect = pygame.Rect(px, py, pw, ph)
                pygame.draw.rect(screen, sc["dirt_dark"], patch_rect.move(0, 3), border_radius=12)
                pygame.draw.rect(screen, base_color, patch_rect, border_radius=12)
                pygame.draw.rect(screen, mix_color(base_color, (255, 235, 180), 0.16), patch_rect, 2, border_radius=12)

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
        draw_tiled_background(screen, 800, 600, sc["grass"], sc["grass_dark"],
                              sc["dirt"], sc["dirt_dark"])

        for f in farm_scene.fireflies:
            alpha = int(120 + 80 * math.sin(f['scale_timer']))
            alpha = max(0, min(255, alpha))
            
            glow_color = (255, 235, 140)
            glow_surf = pygame.Surface((int(f['size'] * 6), int(f['size'] * 6)), pygame.SRCALPHA)
            pygame.draw.circle(glow_surf, (glow_color[0], glow_color[1], glow_color[2], int(alpha * 0.45)), (int(f['size'] * 3), int(f['size'] * 3)), int(f['size'] * 2.5))
            pygame.draw.circle(glow_surf, (255, 255, 200, alpha), (int(f['size'] * 3), int(f['size'] * 3)), int(f['size'] * 1.1))
            screen.blit(glow_surf, (int(f['x'] - f['size'] * 3), int(f['y'] - f['size'] * 3)))

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
        
        panel_h = 176 if farm_scene.action_menu_open else 164
        action_panel = pygame.Rect(430, 300, 320, panel_h)
        draw_light_panel(screen, action_panel)
        action_title = get_font(20).render("오늘 할 일", True, TEXT_DARK)
        screen.blit(action_title, (450, 306))

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
            pill.fill((28, 24, 20, int(205 * alpha)))
            pygame.draw.rect(pill, (150, 120, 80, int(220 * alpha)), (0, 0, pill_w, pill_h), 1, border_radius=8)
            screen.blit(pill, (px, py))
            ts.set_alpha(int(255 * alpha))
            screen.blit(ts, (px + pad, py + 4))

        # '살펴보기' 결과 메시지는 조사·상태가 합쳐진 동적 문구라, 저장된 것을 쓰면 언어 전환이 한 턴
        # 늦게 반영된다. 매 프레임 현재 언어로 다시 생성해 즉시 반영되게 한다(inspect_message는 부작용 없음).
        msg = sim.inspect_message() if sim.last_action == "살펴보기" else sim.message
        draw_bottom_bar(screen, "농장 일지", sim._cropify(f"{msg}\n{sim.notice}"))

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

        if farm_scene.tutorial_active:
            self.draw_tutorial(screen, farm_scene)

    def draw_tutorial(self, screen, farm_scene):
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((10, 12, 18, 185))
        screen.blit(overlay, (0, 0))

        title, body = farm_scene.TUTORIAL_PAGES[farm_scene.tutorial_step]
        title = farm_scene.sim._cropify(title)
        body = farm_scene.sim._cropify(body)
        card = pygame.Rect(150, 195, 500, 210)
        draw_light_panel(screen, card)

        title_surf = get_font(23).render(title, True, TEXT_DARK)
        screen.blit(title_surf, (card.centerx - title_surf.get_width() // 2, card.y + 26))
        pygame.draw.rect(screen, (221, 173, 96),
                         (card.centerx - 60, card.y + 58, 120, 3), border_radius=2)

        body_font = get_font(17)
        y = card.y + 78
        for line in wrap_text(body, body_font, card.w - 56):
            ls = body_font.render(line, True, TEXT_DARK)
            screen.blit(ls, (card.x + 28, y))
            y += body_font.get_height() + 7

        step_txt = i18n.tf("{step} / {total}   ·   클릭하여 계속",
                           step=farm_scene.tutorial_step + 1, total=len(farm_scene.TUTORIAL_PAGES))
        ss = get_font(14).render(step_txt, True, TEXT_MUTED)
        screen.blit(ss, (card.centerx - ss.get_width() // 2, card.bottom - 32))
