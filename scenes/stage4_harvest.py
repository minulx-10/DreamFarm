import pygame
import math
import random
from core.game_state import game_state
from core.assets import *
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel, mix_color


class Stage4Scene:
    """Harvest minigame.
    Click and hold the carrot to drag it UP out of the soil.
    If you drag too fast, the tension rises. High tension breaks the carrot.
    Let go and it slips back down into the dirt."""

    def __init__(self):
        game_state.timer = 24.0
        game_state.score = 0
        self.phase = "intro"  # intro → pull → result
        self.intro_timer = 2.5

        self.attempts = 0
        self.max_attempts = 3
        self.results = []

        # 배경 데코용 당근들 (밭이랑 Y좌표에 맞춰 주변에 심어진 형태 연출)
        self.bg_crops = []
        bg_positions = [
            (90, 210, 12), (180, 205, 8), (280, 215, 11), (520, 210, 9), (620, 215, 13), (710, 205, 10),
            (120, 290, 13), (230, 285, 12), (600, 290, 11), (710, 285, 13),
            (150, 375, 13), (250, 385, 9), (570, 380, 12), (670, 385, 13)
        ]
        for bx, by, bstage in bg_positions:
            self.bg_crops.append({
                'x': bx,
                'y': by,
                'stage': bstage
            })

        # Carrot physics
        self.carrot_y = 360.0
        self.carrot_start_y = 360.0
        self.carrot_target_y = 230.0  # Harvest height (pull 130px)
        
        self.is_dragging = False
        self.drag_offset_y = 0.0
        self.pull_phase = "ready"  # ready → pulling → feedback
        self.tension = 0.0
        self.shake = 0.0
        self.feedback_text = ""
        self.feedback_timer = 0.0

        self.stage_clear = False
        self.clear_timer = 2.0

    def handle_events(self, events):
        if self.stage_clear or self.phase == "intro":
            return
        
        mx, my = pygame.mouse.get_pos()
        carrot_w = sprites["carrot"].get_width()
        carrot_h = sprites["carrot"].get_height()
        # Clickable bounding box for the carrot
        carrot_rect = pygame.Rect(400 - 35, self.carrot_y, 70, 90)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.pull_phase == "ready":
                    if carrot_rect.collidepoint(event.pos):
                        self.is_dragging = True
                        self.drag_offset_y = self.carrot_y - event.pos[1]
                        self.pull_phase = "pulling"
                        self.tension = 0.0

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.is_dragging:
                    self.is_dragging = False
                    if self.pull_phase == "pulling":
                        # Slips back down if released early
                        self.pull_phase = "ready"

    def update(self, dt):
        if self.phase == "intro":
            self.intro_timer -= dt
            if self.intro_timer <= 0:
                self.phase = "pull"
            return

        if self.stage_clear:
            self.clear_timer -= dt
            if self.clear_timer <= 0:
                perfects = self.results.count("perfect")
                bonus = 5 + perfects * 8
                game_state.understanding += bonus
                game_state.transition_text = (
                    "수확 완료!\n\n"
                    f"완벽한 수확: {perfects}회\n"
                    f"생명의 무게를 온전히 느꼈습니다. 이해도 +{bonus}"
                )
                game_state.transition_next = "ending"
                game_state.is_clear_transition = True
                game_state.current_scene = "transition"
            return

        if self.shake > 0:
            self.shake -= dt

        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.stage_clear = True

        # Handle dragging physics
        if self.is_dragging and self.pull_phase == "pulling":
            mx, my = pygame.mouse.get_pos()
            target_y = my + self.drag_offset_y
            # Clamp between start position and fully pulled target height
            clamped_y = max(self.carrot_target_y, min(self.carrot_start_y, target_y))
            
            # Calculate upward speed
            dy = self.carrot_y - clamped_y
            self.carrot_y = clamped_y

            if dy > 0:
                # Dragging upwards. Calculate tension based on speed
                speed = dy / dt
                # Safe speed limit is roughly 120 pixels per second
                tension_gain = max(0.0, (speed - 110.0) * 0.16)
                self.tension = min(100.0, self.tension + tension_gain)
            else:
                # Idle or moving down decreases tension
                self.tension = max(0.0, self.tension - 60.0 * dt)

            # Check break condition (too fast!)
            if self.tension >= 100.0:
                self.is_dragging = False
                self.pull_phase = "feedback"
                self.feedback_text = "너무 세게... 부러졌다."
                self.feedback_timer = 2.0
                self.results.append("broken")
                self.shake = 0.4
                self.attempts += 1
                game_state.score -= 50

            # Check pull clear condition
            elif self.carrot_y <= self.carrot_target_y:
                self.is_dragging = False
                self.pull_phase = "feedback"
                self.feedback_text = "쏙! 완벽하게 뽑혔다."
                self.feedback_timer = 2.0
                self.results.append("perfect")
                self.attempts += 1
                game_state.score += 300

        elif self.pull_phase == "ready":
            # Gravity slide back down to earth
            if self.carrot_y < self.carrot_start_y:
                self.carrot_y += (self.carrot_start_y - self.carrot_y) * 9.0 * dt
            self.tension = max(0.0, self.tension - 120.0 * dt)

        elif self.pull_phase == "feedback":
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                if self.attempts >= self.max_attempts:
                    self.stage_clear = True
                else:
                    self.pull_phase = "ready"
                    self.carrot_y = self.carrot_start_y
                    self.tension = 0.0

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)

        sx = 0
        if self.shake > 0:
            sx = random.randint(-4, 4)

        # 1. Draw background carrots to look like a full carrot patch
        bg_sprout = sprites["sprout4"]
        bsw = bg_sprout.get_width()
        bsh = bg_sprout.get_height()
        for crop in self.bg_crops:
            cx, cy = crop['x'], crop['y']
            # Draw individual background crops slightly buried
            screen.blit(bg_sprout, (cx - bsw // 2 + sx, cy + 12 - bsh // 2))

        # 2. Main target carrot dirt mound (3D Styled)
        mound_y = 350
        pygame.draw.ellipse(screen, DIRT_COLOR, (260 + sx, mound_y, 280, 70))
        pygame.draw.ellipse(screen, DIRT_DARK, (260 + sx, mound_y, 280, 70), 3)

        # 3. Draw target carrot sprout leaves & body
        carrot = sprites["carrot"]
        cw = carrot.get_width()
        cy = self.carrot_y - 20
        
        # If broken, blit a half carrot, otherwise draw normally
        if self.pull_phase == "feedback" and "부러졌다" in self.feedback_text:
            # Render only the top part of the carrot (cut off)
            cropped = pygame.Surface((cw, 35), pygame.SRCALPHA)
            cropped.blit(carrot, (0, 0))
            screen.blit(cropped, (400 - cw // 2 + sx, cy))
        else:
            screen.blit(carrot, (400 - cw // 2 + sx, cy))

        # 4. Tension gauge (only shown when dragging and pulling)
        if self.pull_phase == "pulling" and not self.stage_clear:
            gx, gy, gw, gh = 250, 444, 300, 16
            pygame.draw.rect(screen, (40, 35, 30), (gx, gy, gw, gh), border_radius=4)
            fill_w = int((gw - 4) * (self.tension / 100.0))
            if fill_w > 0:
                # Color transitions from green to red based on tension
                gauge_color = mix_color((80, 175, 110), (220, 60, 45), self.tension / 100.0)
                pygame.draw.rect(screen, gauge_color, (gx + 2, gy + 2, fill_w, gh - 4), border_radius=3)
            
            # Warning text
            font_t = get_font(14)
            txt = "속도 조절! 천천히 들어 올리세요." if self.tension > 50.0 else "적정 속도로 위로 끄세요."
            color = (230, 80, 60) if self.tension > 50.0 else TEXT_MUTED
            surf = font_t.render(txt, True, color)
            screen.blit(surf, (400 - surf.get_width() // 2, gy + 22))

        # 5. Feedback text
        if self.pull_phase == "feedback" and self.feedback_text:
            font = get_font(24)
            color = (255, 220, 120) if "쏙" in self.feedback_text else (210, 100, 80)
            surf = font.render(self.feedback_text, True, color)
            
            # Draw wood backing panel
            panel = pygame.Rect(400 - surf.get_width() // 2 - 16, 170, surf.get_width() + 32, 45)
            draw_wood_panel(screen, panel)
            screen.blit(surf, (400 - surf.get_width() // 2, 178))

        # 6. Relocated Attempt Counter (High visibility wood panel above the gauge)
        if not self.stage_clear and self.phase != "intro":
            att_font = get_font(16)
            # Display current attempt index clearly (e.g. 1/3)
            cur_attempt = min(self.attempts + 1, self.max_attempts)
            att_panel = pygame.Rect(400 - 80, 396, 160, 30)
            draw_wood_panel(screen, att_panel)
            att_text = att_font.render(f"수확 시도: {cur_attempt}/{self.max_attempts}", True, (255, 240, 210))
            screen.blit(att_text, (400 - att_text.get_width() // 2, 402))

        draw_top_bar(screen)

        if self.phase == "intro":
            # Intro overlay description
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            font_t = get_font(26)
            t1 = font_t.render("[수확의 시간]", True, (255, 220, 130))
            screen.blit(t1, (400 - t1.get_width() // 2, 200))
            font_b = get_font(18)
            t2 = font_b.render("마우스 왼쪽 버튼으로 당근을 꾹 누른 채", True, (200, 180, 140))
            screen.blit(t2, (400 - t2.get_width() // 2, 260))
            t3 = font_b.render("천천히 위로 끌어 올려주세요.", True, (200, 180, 140))
            screen.blit(t3, (400 - t3.get_width() // 2, 290))
            t4 = font_b.render("너무 빠르게 당기면 줄기가 꺾여 부러집니다.", True, (230, 110, 90))
            screen.blit(t4, (400 - t4.get_width() // 2, 330))
        elif self.stage_clear:
            font = get_font(28)
            t = font.render("수확 완료!", True, (200, 100, 0))
            panel = pygame.Rect(300, 200, 200, 50)
            draw_wood_panel(screen, panel)
            screen.blit(t, (400 - t.get_width() // 2, 210))
            draw_bottom_bar(screen, "결과", f"수확 점수: {game_state.score}")
        else:
            draw_bottom_bar(screen, "수확하기", "마우스 드래그로 당근을 위로 끌어 올리세요. 너무 성급하면 부러집니다.")
