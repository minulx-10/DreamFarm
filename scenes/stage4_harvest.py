import pygame
import math
import random
from core.game_state import game_state
from core.assets import *
from core import audio
from core.ui import draw_top_bar, draw_bottom_bar, draw_wood_panel, mix_color


class Stage4Scene:
    """Harvest minigame — 연타 클릭 방식.
    당근을 클릭할 때마다 조금씩 위로 올라온다.
    클릭을 멈추면 중력처럼 다시 아래로 미끄러진다.
    너무 빠르게 연타하면 tension이 올라 부러질 수 있다."""

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

        # 당근 물리
        self.carrot_y = 360.0
        self.carrot_start_y = 360.0
        self.carrot_target_y = 230.0  # 이 높이까지 뽑으면 성공 (130px 끌어올리기)

        self.pull_phase = "ready"  # ready → pulling → feedback
        self.tension = 0.0
        self.shake = 0.0
        self.feedback_text = ""
        self.feedback_timer = 0.0

        # 연타 클릭 관련
        self.pull_per_click = 16.0       # 클릭당 올라가는 픽셀 (10 -> 16 버프)
        self.slide_speed = 32.0          # 클릭 안 할 때 내려가는 속도 (50 -> 32 너프)
        self.last_click_time = 0.0       # 마지막 클릭 시각 (pygame.time.get_ticks 기반)
        self.rapid_threshold = 0.055     # 이 시간(초) 미만 간격이면 과도한 연타로 판정 (0.08 -> 0.055)

        self.stage_clear = False
        self.clear_timer = 2.0
        self.dirt_particles = []

    def handle_events(self, events):
        if self.stage_clear or self.phase == "intro":
            return

        # 클릭하기 쉽게 충돌 범위를 넉넉히 확장 (특히 Y축 위쪽 잎사귀 영역 포함)
        carrot_rect = pygame.Rect(400 - 55, self.carrot_y - 30, 110, 120)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.pull_phase == "ready":
                    # 당근 클릭 시 pulling 상태로 전환
                    if carrot_rect.collidepoint(event.pos):
                        self.pull_phase = "pulling"
                        self.tension = 0.0
                        self.last_click_time = pygame.time.get_ticks() / 1000.0
                        audio.play("pop")

                elif self.pull_phase == "pulling":
                    # 클릭할 때마다 당근을 위로 올림
                    now = pygame.time.get_ticks() / 1000.0
                    interval = now - self.last_click_time

                    # 당근 위로 이동
                    self.carrot_y = max(self.carrot_target_y, self.carrot_y - self.pull_per_click)
                    audio.play("pop")

                    # 연타 속도 체크: 너무 빠르면 tension 증가
                    if interval < self.rapid_threshold:
                        self.tension = min(100.0, self.tension + 8.0)

                    self.last_click_time = now

                    # 흙 파티클 생성
                    for _ in range(random.randint(1, 3)):
                        self.dirt_particles.append({
                            'x': random.uniform(370, 430),
                            'y': random.uniform(330, 360),
                            'vx': random.uniform(-65, 65),
                            'vy': random.uniform(-40, 20),
                            'color': random.choice([DIRT_COLOR, DIRT_DARK, (168, 112, 70)]),
                            'size': random.randint(2, 5),
                            'life': random.uniform(0.3, 0.6)
                        })

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

        # pulling 상태 업데이트
        if self.pull_phase == "pulling":
            # tension 자연 감소
            self.tension = max(0.0, self.tension - 25.0 * dt)

            # 클릭이 없으면 당근이 중력처럼 아래로 미끄러짐
            if self.carrot_y < self.carrot_start_y:
                self.carrot_y = min(self.carrot_start_y, self.carrot_y + self.slide_speed * dt)

            # 완전히 내려갔으면 다시 ready 상태로
            if self.carrot_y >= self.carrot_start_y:
                self.carrot_y = self.carrot_start_y

            # 부러짐 체크 (tension 과다)
            if self.tension >= 100.0:
                self.pull_phase = "feedback"
                self.feedback_text = "너무 세게... 부러졌다."
                self.feedback_timer = 2.0
                audio.play("break")
                self.results.append("broken")
                self.shake = 0.4
                self.attempts += 1
                game_state.score -= 50

            # 수확 성공 체크
            elif self.carrot_y <= self.carrot_target_y:
                self.pull_phase = "feedback"
                self.feedback_text = "쏙! 완벽하게 뽑혔다."
                self.feedback_timer = 2.0
                audio.play("harvest")
                self.results.append("perfect")
                self.attempts += 1
                game_state.score += 300

        elif self.pull_phase == "ready":
            # ready 상태에서도 자연 복귀 & tension 감소
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

        # 흙 파티클 업데이트
        for p in self.dirt_particles[:]:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] += 380.0 * dt  # 중력
            p['life'] -= dt
            if p['life'] <= 0:
                self.dirt_particles.remove(p)

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)

        sx = 0
        if self.shake > 0:
            sx = random.randint(-4, 4)

        # 1. 배경 당근밭 — 줄지어 심긴 모습 (종류·크기 살짝 다르게 + 발밑 그늘)
        for i, crop in enumerate(self.bg_crops):
            cx, cy = crop['x'], crop['y']
            spr = sprites["sprout4"] if (crop['stage'] + i) % 3 else sprites["sprout3"]
            bsw, bsh = spr.get_width(), spr.get_height()
            sh = pygame.Surface((bsw, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (20, 12, 8, 120), (0, 0, bsw, 12))
            screen.blit(sh, (cx - bsw // 2 + sx, cy + 16))
            screen.blit(spr, (cx - bsw // 2 + sx, cy + 12 - bsh // 2))

        # 2. 가운데 당근이 솟은 흙두둑 — 봉긋한 둔덕 + 심긴 자리
        mcx, mcy = 400 + sx, 392
        pygame.draw.ellipse(screen, (40, 26, 16), (mcx - 150, mcy - 4, 300, 50))           # 바닥 그늘
        pygame.draw.ellipse(screen, mix_color(DIRT_DARK, BLACK, 0.10), (mcx - 144, mcy - 26, 288, 64))
        pygame.draw.ellipse(screen, DIRT_COLOR, (mcx - 144, mcy - 30, 288, 60))            # 둔덕
        pygame.draw.ellipse(screen, mix_color(DIRT_COLOR, (255, 210, 150), 0.18), (mcx - 130, mcy - 30, 260, 28))  # 윗면 빛
        pygame.draw.ellipse(screen, (52, 34, 22), (mcx - 36, mcy - 16, 72, 28))            # 심긴 자리
        pygame.draw.ellipse(screen, (34, 22, 14), (mcx - 26, mcy - 12, 52, 20))
        srng = random.Random(123)
        for _ in range(16):
            rx = mcx + srng.randint(-128, 128)
            ry = mcy + srng.randint(-22, 16)
            pygame.draw.rect(screen, mix_color(DIRT_COLOR, DIRT_DARK, 0.6), (rx, ry, 3, 3))

        # 흙 파티클 그리기
        for p in self.dirt_particles:
            pygame.draw.rect(screen, p['color'], (int(p['x'] + sx), int(p['y']), p['size'], p['size']))

        # 3. 당근 스프라이트 그리기
        carrot = sprites["carrot"]
        cw = carrot.get_width()
        cy = self.carrot_y - 20

        # 부러진 경우 윗부분만 표시
        if self.pull_phase == "feedback" and "부러졌다" in self.feedback_text:
            cropped = pygame.Surface((cw, 35), pygame.SRCALPHA)
            cropped.blit(carrot, (0, 0))
            screen.blit(cropped, (400 - cw // 2 + sx, cy))
        else:
            screen.blit(carrot, (400 - cw // 2 + sx, cy))

        # 4. Tension 게이지 (pulling 중에만 표시)
        if self.pull_phase == "pulling" and not self.stage_clear:
            gx, gy, gw, gh = 250, 444, 300, 16
            pygame.draw.rect(screen, (40, 35, 30), (gx, gy, gw, gh), border_radius=4)
            fill_w = int((gw - 4) * (self.tension / 100.0))
            if fill_w > 0:
                # 초록 → 빨강 그라데이션
                gauge_color = mix_color((80, 175, 110), (220, 60, 45), self.tension / 100.0)
                pygame.draw.rect(screen, gauge_color, (gx + 2, gy + 2, fill_w, gh - 4), border_radius=3)

            # 경고 텍스트
            font_t = get_font(14)
            txt = "너무 빨라요! 천천히 클릭하세요." if self.tension > 50.0 else "적당한 속도로 클릭하세요."
            color = (230, 80, 60) if self.tension > 50.0 else TEXT_MUTED
            surf = font_t.render(txt, True, color)
            screen.blit(surf, (400 - surf.get_width() // 2, gy + 22))

        # 5. 피드백 텍스트
        if self.pull_phase == "feedback" and self.feedback_text:
            font = get_font(24)
            color = (255, 220, 120) if "쏙" in self.feedback_text else (210, 100, 80)
            surf = font.render(self.feedback_text, True, color)

            # 나무 패널 배경
            panel = pygame.Rect(400 - surf.get_width() // 2 - 16, 170, surf.get_width() + 32, 45)
            draw_wood_panel(screen, panel)
            screen.blit(surf, (400 - surf.get_width() // 2, 178))

        # 6. 시도 횟수 표시
        if not self.stage_clear and self.phase != "intro":
            att_font = get_font(16)
            cur_attempt = min(self.attempts + 1, self.max_attempts)
            att_panel = pygame.Rect(400 - 80, 396, 160, 30)
            draw_wood_panel(screen, att_panel)
            att_text = att_font.render(f"수확 시도: {cur_attempt}/{self.max_attempts}", True, (255, 240, 210))
            screen.blit(att_text, (400 - att_text.get_width() // 2, 402))

        draw_top_bar(screen)

        if self.phase == "intro":
            # 인트로 오버레이
            overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))
            font_t = get_font(26)
            t1 = font_t.render("[수확의 시간]", True, (255, 220, 130))
            screen.blit(t1, (400 - t1.get_width() // 2, 200))
            font_b = get_font(18)
            t2 = font_b.render("마우스 왼쪽 버튼을 연타해서", True, (200, 180, 140))
            screen.blit(t2, (400 - t2.get_width() // 2, 260))
            t3 = font_b.render("당근을 조금씩 뽑아 올리세요.", True, (200, 180, 140))
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
            draw_bottom_bar(screen, "수확하기", "마우스를 연타해 당근을 뽑아 올리세요. 너무 빠르면 부러집니다.")
