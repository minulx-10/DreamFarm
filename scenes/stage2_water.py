import pygame
import random
import math
from core.game_state import game_state
from core.assets import *
from core import audio
from core import i18n
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel, mix_color

class Stage2Scene:
    """Interactive watering minigame.
    Follows the cursor with a watering can. Click and drag to tilt and spray water droplets.
    Water 5 circular soil mounds to 100% moisture to clear the stage."""

    def __init__(self):
        game_state.timer = 24.0
        game_state.score = 600
        self.stage_clear = False
        self.clear_timer = 2.0

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
                bonus = 15
                game_state.understanding += bonus
                game_state.transition_text = i18n.tf(
                    "물 주기 완료!\n\n모든 흙이 충분히 물을 흡수했습니다.\n생명의 근원을 전했습니다. 이해도 +{bonus}",
                    bonus=bonus)
                game_state.transition_next = game_state.return_scene
                game_state.is_clear_transition = True
                game_state.current_scene = "transition"
            return

        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.stage_clear = True

        # Slowly decrease score as time ticks
        game_state.score = max(100, game_state.score - int(10 * dt))

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

        # Draw 5 rounded soil mounds (이랑 / 두둑)
        for i, mound in enumerate(self.mounds):
            x, y = mound['x'], mound['y']
            
            # Outer dark shadow of the soil mound
            pygame.draw.ellipse(screen, (38, 25, 18), (x - 48, y - 8, 96, 38))
            
            # Inner dirt color fades from DIRT_DARK to wet mud color as moisture increases
            # DIRT_DARK = (92, 60, 43), Wet Mud = (66, 44, 30)
            mud_color = (66, 44, 30)
            mound_color = mix_color(DIRT_DARK, mud_color, mound['moisture'] / 100.0)
            pygame.draw.ellipse(screen, mound_color, (x - 44, y - 11, 88, 32))
            
            # Draw sprouts on top
            screen.blit(sprites['sprout2'], (x - 20, y - 28))

            # Draw moisture progress bar (Enlarged for high visibility)
            bar_rect = pygame.Rect(x - 40, y + 26, 80, 12)
            pygame.draw.rect(screen, (40, 35, 30), bar_rect, border_radius=4)
            pygame.draw.rect(screen, (100, 95, 90), bar_rect, 1, border_radius=4) # Light outer border
            fill_w = int(74 * (mound['moisture'] / 100.0))
            if fill_w > 0:
                # Glowing blue/cyan moisture color
                pygame.draw.rect(screen, (60, 160, 240), (bar_rect.x + 3, bar_rect.y + 3, fill_w, 6), border_radius=2)

        # Draw falling water drops particles
        for p in self.particles:
            pygame.draw.circle(screen, (90, 185, 240), (int(p['x']), int(p['y'])), 3)

        # Draw watering can (tilts when clicking)
        can_sprite = sprites['watering_can']
        rotated_can = pygame.transform.rotate(can_sprite, -self.can_angle)
        
        # Draw centered at physics coordinates
        screen.blit(rotated_can, (self.can_x - rotated_can.get_width() // 2, self.can_y - rotated_can.get_height() // 2))

        draw_top_bar(screen)

        if self.stage_clear:
            font = get_font(30)
            clear_text = font.render("물 주기 완료!", True, (200, 100, 0))
            panel_clear = pygame.Rect(400 - 150, 210, 300, 60)
            draw_wood_panel(screen, panel_clear)
            screen.blit(clear_text, (400 - clear_text.get_width()//2, 220))
            draw_bottom_bar(screen, "결과", i18n.tf("얻은 점수: {score}", score=game_state.score))
        else:
            status_desc = "마우스 클릭/드래그하여 물뿌리개로 흙 두둑을 100% 듬뿍 젖게 하세요."
            draw_bottom_bar(screen, "물 주기", status_desc)
