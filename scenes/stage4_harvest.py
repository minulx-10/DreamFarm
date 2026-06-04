import pygame
import math
from core.game_state import game_state
from core.assets import *
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel, mix_color


class Stage4Scene:
    """#4 Harvest minigame — carefully pull the carrot with a power gauge.
    Too strong = breaks, too weak = doesn't budge, just right = perfect harvest."""

    def __init__(self):
        game_state.timer = 30.0
        game_state.score = 0
        self.phase = "intro"  # intro → pull → result
        self.intro_timer = 2.5

        # Gauge
        self.gauge_power = 0.0
        self.gauge_dir = 1
        self.gauge_speed = 120.0
        self.target_min = 50
        self.target_max = 72

        # Pull attempts
        self.attempts = 0
        self.max_attempts = 3
        self.results = []
        self.pull_anim = 0
        self.pull_phase = "gauge"  # gauge → pulling → feedback
        self.feedback_timer = 0
        self.feedback_text = ""

        self.stage_clear = False
        self.clear_timer = 2.5
        self.shake = 0
        self.carrot_y_offset = 0

    def handle_events(self, events):
        if self.stage_clear or self.phase == "intro":
            return
        for event in events:
            if self.pull_phase != "gauge":
                continue
            if event.type == pygame.MOUSEBUTTONDOWN or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            ):
                self._do_pull()

    def _do_pull(self):
        power = self.gauge_power
        self.attempts += 1
        self.pull_phase = "pulling"
        self.pull_anim = 0

        if self.target_min <= power <= self.target_max:
            self.results.append("perfect")
            game_state.score += 300
            self.feedback_text = "쏙! 완벽하게 뽑혔다."
            self.carrot_y_offset = -40
        elif power > self.target_max:
            self.results.append("broken")
            game_state.score -= 50
            self.feedback_text = "너무 세게... 부러졌다."
            self.shake = 0.4
        else:
            self.results.append("weak")
            game_state.score += 50
            self.feedback_text = "꿈쩍도 안 한다. 더 힘을 줘야 해."

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
                    f"수확 완료!\n\n"
                    f"완벽한 수확: {perfects}회\n"
                    f"한 뿌리의 무게를 알게 되었습니다. 이해도 +{bonus}"
                )
                game_state.transition_next = "ending"
                game_state.is_clear_transition = True
                game_state.current_scene = "transition"
            return

        if self.shake > 0:
            self.shake -= dt

        if self.pull_phase == "gauge":
            self.gauge_power += self.gauge_speed * self.gauge_dir * dt
            if self.gauge_power >= 100:
                self.gauge_power = 100
                self.gauge_dir = -1
            elif self.gauge_power <= 0:
                self.gauge_power = 0
                self.gauge_dir = 1

        elif self.pull_phase == "pulling":
            self.pull_anim += dt
            if self.pull_anim > 0.6:
                self.pull_phase = "feedback"
                self.feedback_timer = 1.8

        elif self.pull_phase == "feedback":
            self.feedback_timer -= dt
            if self.feedback_timer <= 0:
                if self.attempts >= self.max_attempts:
                    self.stage_clear = True
                else:
                    self.pull_phase = "gauge"
                    self.gauge_power = 0
                    self.gauge_dir = 1
                    self.carrot_y_offset = 0

        game_state.timer -= dt
        if game_state.timer <= 0:
            game_state.timer = 0
            self.stage_clear = True

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)

        sx = 0
        if self.shake > 0:
            import random
            sx = random.randint(-3, 3)

        # Dirt mound
        mound_y = 320
        pygame.draw.ellipse(screen, DIRT_COLOR, (280 + sx, mound_y, 240, 60))
        pygame.draw.ellipse(screen, DIRT_DARK, (280 + sx, mound_y, 240, 60), 3)

        # Carrot (partially buried)
        carrot = sprites["carrot"]
        cy = mound_y - 30 + int(self.carrot_y_offset)
        if self.pull_phase == "pulling":
            cy -= int(self.pull_anim * 30)
        screen.blit(carrot, (400 - carrot.get_width() // 2 + sx, cy))

        # Power gauge
        if self.pull_phase == "gauge" and not self.stage_clear:
            gx, gy, gw, gh = 200, 430, 400, 35
            panel = pygame.Rect(gx - 8, gy - 8, gw + 16, gh + 16)
            draw_wood_panel(screen, panel)
            gauge_rect = pygame.Rect(gx, gy, gw, gh)
            pygame.draw.rect(screen, (36, 47, 50), gauge_rect, border_radius=8)

            # Target zone (green)
            tz_x = gx + int(gw * self.target_min / 100)
            tz_w = int(gw * (self.target_max - self.target_min) / 100)
            pygame.draw.rect(screen, mix_color(GRASS_COLOR, WHITE, 0.18), (tz_x, gy, tz_w, gh), border_radius=6)
            pygame.draw.rect(screen, (87, 109, 96), gauge_rect, 2, border_radius=8)

            # Cursor
            cx = gx + int(gw * self.gauge_power / 100)
            pygame.draw.rect(screen, (244, 197, 80), (cx - 5, gy - 8, 10, gh + 16), border_radius=5)
            pygame.draw.rect(screen, WHITE, (cx - 5, gy - 8, 10, gh + 16), 2, border_radius=5)

            # Labels
            font = get_font(14)
            weak = font.render("약하게", True, (150, 150, 150))
            strong = font.render("세게", True, (150, 150, 150))
            screen.blit(weak, (gx, gy + gh + 6))
            screen.blit(strong, (gx + gw - strong.get_width(), gy + gh + 6))

        # Feedback text
        if self.pull_phase == "feedback" and self.feedback_text:
            font = get_font(22)
            color = (255, 220, 120) if "완벽" in self.feedback_text or "아삭" in self.feedback_text else (180, 140, 100)
            surf = font.render(self.feedback_text, True, color)
            screen.blit(surf, (400 - surf.get_width() // 2, 260))

        # Attempt counter
        font_s = get_font(18)
        att = font_s.render(f"시도: {self.attempts}/{self.max_attempts}", True, TEXT_DARK)
        screen.blit(att, (650, 440))

        draw_top_bar(screen)

        if self.phase == "intro":
            # Intro overlay
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            font_t = get_font(26)
            t1 = font_t.render("[수확의 시간]", True, (255, 220, 130))
            screen.blit(t1, (400 - t1.get_width() // 2, 220))
            font_b = get_font(20)
            t2 = font_b.render("초록 구간에 맞춰 클릭하세요.", True, (200, 180, 140))
            screen.blit(t2, (400 - t2.get_width() // 2, 270))
            t3 = font_b.render("너무 세면 부러지고, 너무 약하면 안 뽑힙니다.", True, (200, 180, 140))
            screen.blit(t3, (400 - t3.get_width() // 2, 300))
        elif self.stage_clear:
            font = get_font(28)
            t = font.render("수확 완료!", True, (200, 100, 0))
            panel = pygame.Rect(300, 210, 200, 50)
            draw_wood_panel(screen, panel)
            screen.blit(t, (400 - t.get_width() // 2, 220))
            draw_bottom_bar(screen, "결과", f"점수: {game_state.score}")
        else:
            draw_bottom_bar(screen, "수확하기", "초록 구간에서 멈추세요. 한 뿌리의 무게를 느끼며.")
