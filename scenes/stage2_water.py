import pygame
import random
import math
from core.game_state import game_state
from core.assets import *
from core import audio
from core import i18n
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel, mix_color
from core.pixelfx import pixel_rect, CHAMFER, CHAMFER_SM

class Stage2Scene:
    """Interactive watering minigame.
    Follows the cursor with a watering can. Click and drag to tilt and spray water droplets.
    Water 5 circular soil mounds to 100% moisture to clear the stage."""

    def __init__(self):
        from core import behavior
        game_state.timer = 24.0 / behavior.difficulty_factor()   # 숙련자는 시간이 조금 짧다
        game_state.score = 600
        self.stage_clear = False
        self.timed_out = False
        self.clear_timer = 2.0
        self._score_drain = 0.0

        # Spawn 5 rounded soil mounds
        self.mounds = []
        for i in range(5):
            self.mounds.append({
                'x': 140 + i * 130,
                'y': 310,
                'moisture': 0.0
            })

        # Water droplets particles list
        self.particles = []

        # Watering can physics
        self.can_x = 400.0
        self.can_y = 150.0
        self.can_angle = 0.0
        self.is_watering = False

    def handle_events(self, events):
        if self.stage_clear:
            return
        for event in events:
            # We track click/space bar to trigger spraying
            pass
        
        # Check mouse press state
        mouse_pressed = pygame.mouse.get_pressed()[0]
        keys = pygame.key.get_pressed()
        self.is_watering = mouse_pressed or keys[pygame.K_SPACE]

    def update(self, dt):
        if self.stage_clear:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                if self.timed_out:
                    # 시간 초과 — 성공 문구·보상을 그대로 주면 제한시간이 무의미하다
                    bonus = 6
                    game_state.understanding += bonus
                    game_state.transition_text = i18n.tf(
                        "시간이 다 됐다…\n\n미처 다 적시지 못한 두둑이 남았다.\n그래도 물의 무게는 조금 알 것 같다. 이해도 +{bonus}",
                        bonus=bonus)
                else:
                    bonus = 15
                    game_state.understanding += bonus
                    game_state.transition_text = i18n.tf(
                        "물 주기 완료!\n\n모든 흙이 충분히 물을 흡수했습니다.\n생명의 근원을 전했습니다. 이해도 +{bonus}",
                        bonus=bonus)
                game_state.transition_next = game_state.return_scene
                game_state.is_clear_transition = True

                from core import behavior
                behavior.log("minigame", stage="stage2",
                             score=game_state.score,
                             norm=0.4 if self.timed_out else 1.0)

                game_state.current_scene = "transition"
            return

        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.timed_out = True
            self.stage_clear = True
            self.clear_timer = 2.0
            audio.play("page")

        # Slowly decrease score as time ticks — int(10*dt)는 60fps에서 항상 0이라 감점이 죽어 있었다
        self._score_drain = getattr(self, "_score_drain", 0.0) + 10 * dt
        drop = int(self._score_drain)
        if drop:
            self._score_drain -= drop
            game_state.score = max(100, game_state.score - drop)

        # Smoothly follow mouse
        mx, my = pygame.mouse.get_pos()
        self.can_x += (mx - self.can_x) * 14.0 * dt
        self.can_y += (my - self.can_y) * 14.0 * dt

        # Watering can rotation & particle spawning
        target_angle = 0.0
        if self.is_watering:
            target_angle = 35.0  # Tilts forward to pour water
            
            # Position of the spout (adjust relative to can center - can is scaled to 6)
            # The can is drawn centered at (can_x, can_y). When tilted, the nozzle is roughly to the right and down.
            spout_x = self.can_x + 52
            spout_y = self.can_y + 16

            # Spawn 2-3 drops of water
            for _ in range(random.randint(2, 4)):
                self.particles.append({
                    'x': spout_x + random.uniform(-4, 4),
                    'y': spout_y + random.uniform(-4, 4),
                    'vx': random.uniform(40.0, 90.0),   # Flows forward
                    'vy': random.uniform(-40.0, 10.0), # Sprays out
                    'life': 0.7
                })
            
            # Count watering turn stats randomly while spraying
            if random.random() < 0.08:
                game_state.water_count += 1
            # 물소리 효과음 (과하지 않게 간헐적으로)
            if random.random() < 0.05:
                audio.play("water")
        else:
            target_angle = 0.0

        # Interpolate angle
        self.can_angle += (target_angle - self.can_angle) * 10.0 * dt

        # Update water droplets particles
        for p in self.particles:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 320 * dt  # Gravity effect
            p['life'] -= dt

            # Check collision with each mound
            for mound in self.mounds:
                # Mound bounding circle detection
                dx = p['x'] - mound['x']
                dy = p['y'] - (mound['y'] - 5)
                # Approximate mound ellipse collision: (dx/45)^2 + (dy/18)^2 <= 1.0
                if (dx*dx) / (45*45) + (dy*dy) / (18*18) <= 1.0:
                    mound['moisture'] = min(100.0, mound['moisture'] + 6.0)
                    p['life'] = 0.0  # Kill particle on hit

        # Filter dead particles
        self.particles = [p for p in self.particles if p['life'] > 0]

        # Check if all mounds are fully watered
        all_watered = True
        for mound in self.mounds:
            if mound['moisture'] < 100.0:
                all_watered = False
                break
        if all_watered:
            if not self.stage_clear:
                audio.play("success")
            self.stage_clear = True
            self.clear_timer = 2.0

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)

        # Draw 5 rounded soil mounds (이랑 / 두둑) — 매끈한 대형 타원 대신 도트화(곡선 없음 규칙)
        from core.pixelfx import pixelate
        for i, mound in enumerate(self.mounds):
            x, y = mound['x'], mound['y']

            mud_color = (66, 44, 30)
            mound_color = mix_color(DIRT_DARK, mud_color, mound['moisture'] / 100.0)
            mound_surf = pygame.Surface((96, 41), pygame.SRCALPHA)
            pygame.draw.ellipse(mound_surf, (38, 25, 18), (0, 3, 96, 38))
            pygame.draw.ellipse(mound_surf, mound_color, (4, 0, 88, 32))
            screen.blit(pixelate(mound_surf, 3, smooth=False), (x - 48, y - 11))

            # Draw sprouts on top
            screen.blit(sprites['sprout2'], (x - 20, y - 28))

            # Draw moisture progress bar (Enlarged for high visibility)
            bar_rect = pygame.Rect(x - 40, y + 26, 80, 12)
            pixel_rect(screen, (40, 35, 30), bar_rect, chamfer=CHAMFER_SM)
            pixel_rect(screen, (100, 95, 90), bar_rect, width=1, chamfer=CHAMFER_SM)  # Light outer border
            fill_w = int(74 * (mound['moisture'] / 100.0))
            if fill_w > 0:
                # Glowing blue/cyan moisture color
                pixel_rect(screen, (60, 160, 240), (bar_rect.x + 3, bar_rect.y + 3, fill_w, 6), chamfer=CHAMFER_SM)

        # Draw falling water drops particles — 3px 사각 도트(곡선 없음 규칙, screen 직접 원 금지)
        for p in self.particles:
            pygame.draw.rect(screen, (90, 185, 240), (int(p['x']) - 1, int(p['y']) - 1, 3, 3))

        # Draw watering can (tilts when clicking)
        can_sprite = sprites['watering_can']
        rotated_can = pygame.transform.rotate(can_sprite, -self.can_angle)
        
        # Draw centered at physics coordinates
        screen.blit(rotated_can, (self.can_x - rotated_can.get_width() // 2, self.can_y - rotated_can.get_height() // 2))

        draw_top_bar(screen)

        if self.stage_clear:
            font = get_font(30)
            clear_text = font.render("시간 초과…" if self.timed_out else "물 주기 완료!", True, (200, 100, 0))
            panel_clear = pygame.Rect(400 - 150, 210, 300, 60)
            draw_wood_panel(screen, panel_clear)
            screen.blit(clear_text, (400 - clear_text.get_width()//2, 220))
            draw_bottom_bar(screen, "결과", i18n.tf("얻은 점수: {score}", score=game_state.score))
        else:
            status_desc = "마우스 클릭/드래그하여 물뿌리개로 흙 두둑을 100% 듬뿍 젖게 하세요."
            draw_bottom_bar(screen, "물 주기", status_desc)
