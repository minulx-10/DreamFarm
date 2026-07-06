import pygame
import math
import random
from core.game_state import game_state, append_josa
from core.assets import *
from core import audio
from core.crops import current_crop
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

        # 당근/감자/사과/벼 물리
        self.harvest_offsets = [-110, 0, 110]
        self.center_x = 400 + self.harvest_offsets[0] # 첫 수확 구덩이는 왼쪽에서 시작

        self.is_apple = (game_state.crop == "apple")
        self.is_potato = (game_state.crop == "potato")
        self.is_rice = (game_state.crop == "rice")
        if self.is_apple:
            self.carrot_y = 200.0
            self.carrot_start_y = 200.0
            self.carrot_target_y = 330.0  # 아래로 당겨 따냄 (130px 끌어내리기)
        elif self.is_potato:
            self.potato_x = self.center_x
            self.potato_start_x = self.center_x
            # 감자는 한 번 밀어서 캐는 게 아니라, 좌우로 번갈아 흔들어 흙에서 풀어내야 뽑힌다.
            self.dragging = False
            self.drag_start_x = self.center_x
            self.drag_current_x = self.center_x
            self.last_drag_x = self.center_x
            self.potato_loosen = 0.0   # 흔들어 풀린 정도 (100이면 쏙 뽑힌다)
            self.shake_dir = 0         # 마지막 흔든 방향 (+1 오른쪽 / -1 왼쪽)
            self.swing = 0.0           # 현재 방향으로 흔든 누적 거리
            self.shake_count = 0
        elif self.is_rice:
            self.rice_phase = "thresh"  # thresh (탈곡) -> hull (도정)
            self.thresh_progress = 0.0
            self.hull_progress = 0.0
            self.dragging = False
            self.drag_start_x = self.center_x
            self.drag_current_x = self.center_x
            self.last_drag_x = self.center_x
            self.shake_dir = 0
        else:
            self.carrot_y = 360.0
            self.carrot_start_y = 360.0
            self.carrot_target_y = 230.0  # 이 높이까지 뽑으면 성공 (130px 끌어올리기)
            self.dragging = False
            self.last_drag_y = 360.0
            self.carrot_loosen = 0.0   # 뽑힌 정도 (100이면 쏙). 여러 번 끌어당겨야 참
            self.grab_carrot = 0.0     # 이번 잡음에서 뽑아낸 양(한 번에 다 못 뽑게 상한)

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

        for event in events:
            if self.is_rice:
                if self.rice_phase == "thresh":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.pull_phase == "ready":
                            rice_rect = pygame.Rect(self.center_x - 65, 360 - 50, 130, 120)
                            if rice_rect.collidepoint(event.pos):
                                self.pull_phase = "pulling"
                                self.dragging = True
                                self.drag_start_x = event.pos[0]
                                self.drag_current_x = event.pos[0]
                                self.last_drag_x = event.pos[0]
                                self.shake_dir = 0
                                self.tension = 0.0
                                audio.play("pop")
                    elif event.type == pygame.MOUSEMOTION:
                        if self.pull_phase == "pulling" and self.dragging:
                            self.drag_current_x = event.pos[0]
                            dx = event.pos[0] - self.last_drag_x
                            if abs(dx) > 3.0:
                                new_dir = 1 if dx > 0 else -1
                                if self.shake_dir != new_dir:
                                    self.shake_dir = new_dir
                                    self.thresh_progress = min(100.0, self.thresh_progress + 5.0)
                                    audio.play("pop")
                                    for _ in range(random.randint(2, 4)):
                                        self.dirt_particles.append({
                                            'x': random.uniform(self.center_x - 30, self.center_x + 30),
                                            'y': random.uniform(320, 350),
                                            'vx': random.uniform(-100, 100),
                                            'vy': random.uniform(-120, -40),
                                            'color': random.choice([(245, 220, 95), (210, 185, 45), (190, 160, 40)]),
                                            'size': random.randint(3, 5),
                                            'life': random.uniform(0.4, 0.7)
                                        })
                                    # 과도한 속도/흔들림 감지 시 tension 증가
                                    if abs(dx) > 18.0:
                                        self.tension = min(100.0, self.tension + 12.0)
                            self.last_drag_x = event.pos[0]
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        if self.dragging:
                            self.dragging = False
                elif self.rice_phase == "hull":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        grain_rect = pygame.Rect(320, 230, 160, 100)
                        if grain_rect.collidepoint(event.pos):
                            self.dragging = True
                            self.pull_phase = "pulling"   # 도정 완료 판정이 thresh에서 넘어온 상태에 의존하지 않게 명시
                            self.drag_start_x = event.pos[0]
                    elif event.type == pygame.MOUSEMOTION:
                        if self.dragging:
                            grain_rect = pygame.Rect(320, 230, 160, 100)
                            if grain_rect.collidepoint(event.pos):
                                dist = abs(event.rel[0]) + abs(event.rel[1])
                                if dist > 1:
                                    self.hull_progress = min(100.0, self.hull_progress + dist * 0.12)
                                    if random.random() < 0.12:
                                        audio.play("pop")
                                        self.dirt_particles.append({
                                            'x': event.pos[0],
                                            'y': event.pos[1],
                                            'vx': random.uniform(-30, 30),
                                            'vy': random.uniform(-30, 30),
                                            'color': (165, 125, 75),
                                            'size': random.randint(2, 3),
                                            'life': random.uniform(0.2, 0.4)
                                        })
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        if self.dragging:
                            self.dragging = False
            elif self.is_potato:
                # 감자는 좌우 드래그 방식
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.pull_phase == "ready":
                        potato_rect = pygame.Rect(self.potato_x - 55, 366 - 30, 110, 120)
                        if potato_rect.collidepoint(event.pos):
                            self.pull_phase = "pulling"
                            self.dragging = True
                            self.drag_start_x = event.pos[0]
                            self.drag_current_x = event.pos[0]
                            self.last_drag_x = event.pos[0]
                            self.tension = 0.0
                            self.potato_loosen = 0.0
                            self.shake_dir = 0
                            self.swing = 0.0
                            audio.play("pop")
                elif event.type == pygame.MOUSEMOTION:
                    if self.pull_phase == "pulling" and self.dragging:
                        self.drag_current_x = event.pos[0]
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if self.dragging:
                        self.dragging = False
            elif self.is_apple:
                # 사과: 연타로 아래로 당겨 따냄 (기존 방식 유지)
                carrot_rect = pygame.Rect(self.center_x - 55, self.carrot_y - 30, 110, 120)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.pull_phase == "ready":
                        if carrot_rect.collidepoint(event.pos):
                            self.pull_phase = "pulling"
                            self.tension = 0.0
                            self.last_click_time = pygame.time.get_ticks() / 1000.0
                            audio.play("pop")
                    elif self.pull_phase == "pulling":
                        now = pygame.time.get_ticks() / 1000.0
                        interval = now - self.last_click_time
                        self.carrot_y = min(self.carrot_target_y + 15.0, self.carrot_y + self.pull_per_click)
                        audio.play("pop")
                        if interval < self.rapid_threshold:
                            self.tension = min(100.0, self.tension + 8.0)
                        self.last_click_time = now
                        for _ in range(random.randint(1, 2)):
                            self.dirt_particles.append({
                                'x': random.uniform(self.center_x - 30, self.center_x + 30),
                                'y': random.uniform(160, 180),
                                'vx': random.uniform(-40, 40), 'vy': random.uniform(40, 100),
                                'color': random.choice([(76, 150, 78), (96, 180, 98), (56, 120, 58)]),
                                'size': random.randint(3, 6), 'life': random.uniform(0.5, 0.9)})
            else:
                # 당근: 한 번에 안 뽑히고, 잡고-끌고-놓기를 여러 번 반복해야 뽑힌다.
                # 한 번 잡았을 때 뽑히는 양(grab_carrot)에 상한을 둬, 빨리 홱 당겨도 끝까지 안 뽑힌다.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.pull_phase == "ready":
                    carrot_rect = pygame.Rect(self.center_x - 55, self.carrot_y - 34, 110, 130)
                    if carrot_rect.collidepoint(event.pos):
                        self.pull_phase = "pulling"
                        self.dragging = True
                        self.last_drag_y = event.pos[1]
                        self.grab_carrot = 0.0
                        audio.play("pop")
                elif event.type == pygame.MOUSEMOTION and self.dragging and self.pull_phase == "pulling":
                    dy = event.pos[1] - self.last_drag_y
                    if dy < 0 and self.grab_carrot < 34.0:   # 위로 끌 때만, 이번 잡음에선 최대 34까지
                        add = min(-dy * 0.45, 34.0 - self.grab_carrot)
                        self.carrot_loosen = min(100.0, self.carrot_loosen + add)
                        self.grab_carrot += add
                        for _ in range(random.randint(0, 2)):
                            self.dirt_particles.append({
                                'x': random.uniform(self.center_x - 26, self.center_x + 26),
                                'y': random.uniform(340, 365),
                                'vx': random.uniform(-60, 60), 'vy': random.uniform(-40, 10),
                                'color': random.choice([DIRT_COLOR, DIRT_DARK, (168, 112, 70)]),
                                'size': random.randint(2, 5), 'life': random.uniform(0.3, 0.6)})
                    if -dy > 85:   # 너무 홱 잡아채면 상한다
                        self.tension = min(100.0, self.tension + 20.0)
                    self.last_drag_y = event.pos[1]
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging = False

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
                # 작물을 끝까지 길러 수확했다 — 작물별 클리어 횟수를 누적하고 업적을 확인한다.
                from core import save_system
                save_system.record_crop_clear(game_state.crop)
                from core import achievements
                achievements.on_harvest(game_state.crop, perfects, self.attempts)
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
            if self.is_rice:
                if self.rice_phase == "thresh":
                    if self.dragging:
                        # 흔드는 동안 tension은 서서히 감소
                        self.tension = max(0.0, self.tension - 25.0 * dt)
                        
                        # 부러짐 체크 (너무 강한 흔들림/마우스 속도로 인한 tension 과다)
                        if self.tension >= 100.0:
                            self.pull_phase = "feedback"
                            self.feedback_text = "너무 세게 털어 낟알이 상했다."
                            self.feedback_timer = 2.0
                            audio.play("break")
                            self.results.append("broken")
                            self.shake = 0.4
                            self.attempts += 1
                            game_state.score -= 50
                            self.dragging = False
                        # 탈곡 완료 체크 -> 도정 단계로 전환
                        elif self.thresh_progress >= 100.0:
                            self.rice_phase = "hull"
                            self.dragging = False
                            self.tension = 0.0
                            audio.play("success")
                    else:
                        # 손을 놓으면 다시 잡을 수 있도록 '준비' 상태로 복귀한다 (탈곡 진행도는 유지).
                        # 이 복귀가 없어서, 벼를 끝까지 못 털고 손을 떼면 다시 못 잡아 나머지 수확이 막혔다.
                        self.tension = max(0.0, self.tension - 60.0 * dt)
                        self.pull_phase = "ready"
                elif self.rice_phase == "hull":
                    # 도정(껍질 벗기기) 완료 체크
                    if self.hull_progress >= 100.0:
                        self.pull_phase = "feedback"
                        self.feedback_text = "툭! 탈곡과 도정을 마쳤다."
                        self.feedback_timer = 2.0
                        audio.play("harvest")
                        self.results.append("perfect")
                        self.attempts += 1
                        game_state.score += 300
                        self.dragging = False
            elif self.is_potato:
                if self.dragging:
                    dx = self.drag_current_x - self.last_drag_x

                    # 좌우로 번갈아 흔들어야 풀린다 — 방향이 바뀔 때마다 '한 번 흔든' 것으로 친다.
                    self.swing += dx
                    if dx != 0:
                        new_dir = 1 if dx > 0 else -1
                        if new_dir != self.shake_dir and abs(self.swing) > 26.0:
                            self.shake_dir = new_dir
                            self.swing = 0.0
                            self.shake_count += 1
                            self.potato_loosen = min(100.0, self.potato_loosen + 20.0)
                            audio.play("pop")
                            for _ in range(random.randint(2, 4)):
                                self.dirt_particles.append({
                                    'x': random.uniform(self.potato_x - 26, self.potato_x + 26),
                                    'y': random.uniform(345, 372),
                                    'vx': random.uniform(-70, 70),
                                    'vy': random.uniform(-70, -20),
                                    'color': random.choice([DIRT_COLOR, DIRT_DARK, (168, 112, 70)]),
                                    'size': random.randint(2, 5),
                                    'life': random.uniform(0.3, 0.6)
                                })

                    # 너무 격하게 홱홱 채면 감자가 상한다
                    speed = abs(dx) / max(0.001, dt)
                    if speed > 1500.0:
                        self.tension = min(100.0, self.tension + 22.0 * dt * (speed / 1500.0))
                    else:
                        self.tension = max(0.0, self.tension - 45.0 * dt)

                    # 손짓 따라 감자가 좌우로 살짝 흔들린다 (뽑히진 않고 흔들리기만)
                    wiggle = (self.drag_current_x - self.drag_start_x) * 0.35
                    self.potato_x = max(self.center_x - 34.0, min(self.center_x + 34.0, self.center_x + wiggle))
                    self.last_drag_x = self.drag_current_x

                    if self.tension >= 100.0:
                        self.pull_phase = "feedback"
                        self.feedback_text = "너무 거칠게... 상했다."
                        self.feedback_timer = 2.0
                        audio.play("break")
                        self.results.append("broken")
                        self.shake = 0.4
                        self.attempts += 1
                        game_state.score -= 50
                        self.dragging = False
                    elif self.potato_loosen >= 100.0:
                        self.pull_phase = "feedback"
                        self.feedback_text = "쏙! 완벽하게 캐냈다."
                        self.feedback_timer = 2.0
                        audio.play("harvest")
                        self.results.append("perfect")
                        self.attempts += 1
                        game_state.score += 300
                        self.dragging = False
                else:
                    # 손을 놓으면 흔든 정도가 서서히 풀리고 제자리로
                    self.tension = max(0.0, self.tension - 60.0 * dt)
                    self.potato_loosen = max(0.0, self.potato_loosen - 28.0 * dt)
                    if self.potato_x < self.center_x:
                        self.potato_x = min(self.center_x, self.potato_x + self.slide_speed * 4.0 * dt)
                    elif self.potato_x > self.center_x:
                        self.potato_x = max(self.center_x, self.potato_x - self.slide_speed * 4.0 * dt)
                    if abs(self.potato_x - self.center_x) < 0.5:
                        self.potato_x = self.center_x
                        self.pull_phase = "ready"
            else:
                # tension 자연 감소
                self.tension = max(0.0, self.tension - 25.0 * dt)

                # 클릭이 없으면 제자리로 미끄러짐
                if self.is_apple:
                    if self.carrot_y > self.carrot_start_y:
                        self.carrot_y = max(self.carrot_start_y, self.carrot_y - self.slide_speed * dt)
                    if self.carrot_y <= self.carrot_start_y:
                        self.carrot_y = self.carrot_start_y
                else:
                    # 당근: 높이는 '뽑힌 정도'에 따라 결정된다. 손을 놓으면 풀린 정도는 유지한 채
                    # '준비'로 돌아가 다시 잡을 수 있다 (여러 번 끌어당겨 뽑는 느낌).
                    self.carrot_y = self.carrot_start_y - (self.carrot_start_y - self.carrot_target_y) * min(1.0, self.carrot_loosen / 100.0)
                    if not getattr(self, "dragging", False):
                        self.pull_phase = "ready"

                # 부러짐 체크 (tension 과다)
                if self.tension >= 100.0:
                    self.pull_phase = "feedback"
                    self.feedback_text = "너무 세게... 상했다."
                    self.feedback_timer = 2.0
                    audio.play("break")
                    self.results.append("broken")
                    self.shake = 0.4
                    self.attempts += 1
                    game_state.score -= 50

                # 수확 성공 체크
                else:
                    success = (self.carrot_y >= self.carrot_target_y) if self.is_apple else (self.carrot_y <= self.carrot_target_y)
                    if success:
                        self.pull_phase = "feedback"
                        if game_state.crop == "apple":
                            self.feedback_text = "툭! 완벽하게 땄다."
                        else:
                            self.feedback_text = "쏙! 완벽하게 뽑혔다."
                        self.feedback_timer = 2.0
                        audio.play("harvest")
                        self.results.append("perfect")
                        self.attempts += 1
                        game_state.score += 300

        elif self.pull_phase == "ready":
            # ready 상태에서도 자연 복귀 & tension 감소
            if self.is_potato:
                self.tension = max(0.0, self.tension - 120.0 * dt)
            elif self.is_rice:
                self.tension = max(0.0, self.tension - 120.0 * dt)
            else:
                if self.is_apple:
                    if self.carrot_y > self.carrot_start_y:
                        self.carrot_y += (self.carrot_start_y - self.carrot_y) * 9.0 * dt
                else:
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
                    self.tension = 0.0
                    # 다음 수확 구덩이 X 좌표로 갱신!
                    self.center_x = 400 + self.harvest_offsets[min(2, self.attempts)]
                    if self.is_potato:
                        self.potato_start_x = self.center_x
                        self.potato_x = self.potato_start_x
                    elif self.is_rice:
                        self.rice_phase = "thresh"
                        self.thresh_progress = 0.0
                        self.hull_progress = 0.0
                    else:
                        self.carrot_y = self.carrot_start_y
                        self.carrot_loosen = 0.0
                        self.grab_carrot = 0.0
                        self.dragging = False

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

        if self.is_apple:
            # 1. 배경 데코 (사과나무 가지와 매달린 사과)
            bg_apples = [(110, 180), (220, 200), (580, 210), (690, 180)]
            for bx, by in bg_apples:
                pygame.draw.line(screen, (80, 50, 30), (bx - 30, by - 20), (bx + 30, by - 12), 4)
                pygame.draw.line(screen, (96, 62, 36), (bx, by - 16), (bx, by), 2)
                pygame.draw.circle(screen, (160, 30, 30), (bx, by), 12)
                pygame.draw.circle(screen, (86, 168, 84), (bx + 4, by - 14), 5)
            
            # 2. 가운데 사과나무 가지와 꼭지 줄기
            mcx = self.center_x + sx
            pygame.draw.line(screen, (96, 62, 36), (mcx, 172), (mcx, int(self.carrot_y) - 16), 3)
            pygame.draw.line(screen, (90, 60, 40), (260, 160), (540, 180), 8)
            pygame.draw.circle(screen, (46, 112, 60), (320, 165), 18)
            pygame.draw.circle(screen, (66, 150, 78), (480, 175), 15)
        else:
            # 1. 배경 밭 — 줄지어 심긴 모습 (작물별 잎사귀 색조/형태 다양화)
            for i, crop in enumerate(self.bg_crops):
                cx, cy = crop['x'], crop['y']
                orig_spr = sprites["sprout4"] if (crop['stage'] + i) % 3 else sprites["sprout3"]
                
                if self.is_potato:
                    # 감자는 누렇고 시든 잎
                    spr = orig_spr.copy()
                    tint = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
                    tint.fill((160, 150, 40, 95))
                    spr.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    sh = spr.get_height()
                    spr = pygame.transform.scale(spr, (spr.get_width(), int(sh * 0.85)))
                    bsw, bsh = spr.get_width(), spr.get_height()
                    cy_offset = 12 - bsh // 2 + int(sh * 0.07)
                elif game_state.crop == "rice":
                    # 벼는 황금빛 노란 잎
                    spr = orig_spr.copy()
                    tint = pygame.Surface(spr.get_size(), pygame.SRCALPHA)
                    tint.fill((210, 185, 45, 120))
                    spr.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    bsw, bsh = spr.get_width(), spr.get_height()
                    cy_offset = 12 - bsh // 2
                else:
                    spr = orig_spr
                    bsw, bsh = spr.get_width(), spr.get_height()
                    cy_offset = 12 - bsh // 2

                sh_surf = pygame.Surface((bsw, 12), pygame.SRCALPHA)
                pygame.draw.ellipse(sh_surf, (20, 12, 8, 120), (0, 0, bsw, 12))
                screen.blit(sh_surf, (cx - bsw // 2 + sx, cy + 16))
                screen.blit(spr, (cx - bsw // 2 + sx, cy + cy_offset))

            # 2. 가운데 당근이 솟은 흙두둑 — 봉긋한 둔덕 + 심긴 자리
            mcx, mcy = self.center_x + sx, 392
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

        # 파티클 그리기
        for p in self.dirt_particles:
            pygame.draw.rect(screen, p['color'], (int(p['x'] + sx), int(p['y']), p['size'], p['size']))

        # 3. 작물별 수확물 그리기 (당근=스프라이트, 그 외=고유 도형)
        broken = self.pull_phase == "feedback" and "상했다" in self.feedback_text
        if game_state.crop == "carrot":
            carrot = sprites["carrot"]
            cw = carrot.get_width()
            cy = self.carrot_y - 20
            if broken:
                cropped = pygame.Surface((cw, 35), pygame.SRCALPHA)
                cropped.blit(carrot, (0, 0))
                screen.blit(cropped, (self.center_x - cw // 2 + sx, cy))
            else:
                screen.blit(carrot, (self.center_x - cw // 2 + sx, cy))
        elif self.is_potato:
            # 감자: 흔들어 풀린 정도(potato_loosen)만큼 흙 밑에서 서서히 솟아오른다.
            # 처음엔 땅에 묻혀 있다가, 다 풀리거나 뽑힌 뒤에 완전히 올라온다.
            loosen = 100.0 if self.pull_phase == "feedback" else getattr(self, "potato_loosen", 0.0)
            px = int(self.potato_x + sx)
            py = 372 - int(loosen * 0.40)
            
            # 감자알들
            pygame.draw.ellipse(screen, (78, 52, 32), (px - 22, py + 12, 18, 12))
            pygame.draw.ellipse(screen, (150, 108, 66), (px - 21, py + 11, 16, 10))
            pygame.draw.ellipse(screen, (78, 52, 32), (px + 4, py + 14, 20, 14))
            pygame.draw.ellipse(screen, (150, 108, 66), (px + 5, py + 13, 18, 12))
            
            # 줄기들
            pygame.draw.line(screen, (100, 85, 45), (px, py - 20), (px - 14, py + 12), 2)
            pygame.draw.line(screen, (100, 85, 45), (px, py - 20), (px + 10, py + 14), 2)
            
            # 위에 달린 시든 잎뭉치
            orig_spr = sprites["sprout4"]
            withered = orig_spr.copy()
            tint = pygame.Surface(withered.get_size(), pygame.SRCALPHA)
            tint.fill((160, 150, 40, 95))
            withered.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            sh = withered.get_height()
            withered = pygame.transform.scale(withered, (withered.get_width(), int(sh * 0.8)))
            screen.blit(withered, (px - withered.get_width() // 2, py - 20 - withered.get_height() // 2))
            
            if broken:
                # 감자알 상함 표시 (어두운 멍자국)
                pygame.draw.ellipse(screen, (70, 30, 20, 190), (px - 22, py + 12, 18, 12))
                pygame.draw.ellipse(screen, (70, 30, 20, 190), (px + 4, py + 14, 20, 14))
        elif game_state.crop == "rice":
            if self.rice_phase == "thresh":
                # 벼: 황금빛 벼 이삭과 노랗게 물든 벼 포기
                px = self.center_x + sx
                py = 360
                
                # 벼 잎/줄기 (황금빛 틴트된 sprout4)
                orig_spr = sprites["sprout4"]
                golden = orig_spr.copy()
                tint = pygame.Surface(golden.get_size(), pygame.SRCALPHA)
                tint.fill((210, 185, 45, 120))
                golden.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                
                # 흔드는 각도 계산
                angle = 0.0
                if self.dragging:
                    angle = max(-25.0, min(25.0, (self.drag_current_x - self.drag_start_x) * 0.25))
                
                if abs(angle) > 1.0:
                    rotated = pygame.transform.rotate(golden, -angle)
                    screen.blit(rotated, (px - rotated.get_width() // 2, py - 20 - rotated.get_height() // 2))
                else:
                    screen.blit(golden, (px - golden.get_width() // 2, py - 20 - golden.get_height() // 2))
                
                # 늘어진 벼 이삭들 (각도만큼 회전해서 그리기)
                gold_dark = (190, 160, 40)
                gold_light = (245, 220, 95)
                rad = math.radians(angle)
                cos_a, sin_a = math.cos(rad), math.sin(rad)
                def rot_pt(cx, cy, px_val, py_val):
                    dx, dy = px_val - cx, py_val - cy
                    rx = cx + dx * cos_a - dy * sin_a
                    ry = cy + dx * sin_a + dy * cos_a
                    return int(rx), int(ry)

                if broken:
                    # 상하면 이삭이 꺾이고 어둡게 변함
                    p1 = rot_pt(px, py - 20, px, py - 25)
                    p2 = rot_pt(px, py - 20, px - 14, py - 18)
                    p3 = rot_pt(px, py - 20, px - 18, py - 8)
                    pygame.draw.line(screen, (100, 80, 20), p1, p2, 2)
                    pygame.draw.line(screen, (100, 80, 20), p2, p3, 2)
                    for dx, dy in [(-10, -20), (-14, -18), (-18, -8)]:
                        pt = rot_pt(px, py - 20, px + dx, py + dy)
                        pygame.draw.circle(screen, (130, 110, 30), pt, 2)
                else:
                    # 왼쪽 이삭
                    p1 = rot_pt(px, py - 20, px, py - 25)
                    p2 = rot_pt(px, py - 20, px - 22, py - 3)
                    pygame.draw.line(screen, gold_dark, p1, p2, 2)
                    for dx, dy in [(-12, -15), (-17, -9), (-22, -3)]:
                        pt = rot_pt(px, py - 20, px + dx, py + dy)
                        pygame.draw.circle(screen, gold_light, pt, 3)
                    # 오른쪽 이삭
                    p3 = rot_pt(px, py - 20, px, py - 28)
                    p4 = rot_pt(px, py - 20, px + 22, py - 5)
                    pygame.draw.line(screen, gold_dark, p3, p4, 2)
                    for dx, dy in [(12, -18), (17, -12), (22, -5)]:
                        pt = rot_pt(px, py - 20, px + dx, py + dy)
                        pygame.draw.circle(screen, gold_light, pt, 3)
            elif self.rice_phase == "hull":
                # 어두운 도정 오버레이
                veil = pygame.Surface((800, 600), pygame.SRCALPHA)
                veil.fill((0, 0, 0, 150))
                screen.blit(veil, (0, 0))
                
                # 가운데 큰 백미 낟알
                pygame.draw.ellipse(screen, (250, 250, 245), (320, 230, 160, 100))
                pygame.draw.ellipse(screen, (230, 225, 215), (325, 235, 150, 90), 2)
                
                # 껍질 반쪽씩 슬라이딩 분리
                offset = int(90 * (self.hull_progress / 100.0))
                husk_surf = pygame.Surface((160, 100), pygame.SRCALPHA)
                pygame.draw.ellipse(husk_surf, (165, 125, 75), (0, 0, 160, 100))
                pygame.draw.ellipse(husk_surf, (135, 100, 55), (0, 0, 160, 100), 2)
                pygame.draw.line(husk_surf, (135, 100, 55), (20, 50), (140, 50), 2)
                
                screen.blit(husk_surf, (320 - offset, 230), (0, 0, 80, 100))
                screen.blit(husk_surf, (400 + offset, 230), (80, 0, 80, 100))
        else:
            # 사과나무 등
            if broken:
                draw_crop_food(screen, self.center_x + sx, int(self.carrot_y + 6), game_state.crop, r=24)
                pygame.draw.ellipse(screen, (110, 60, 45, 185), (self.center_x + sx - 16, int(self.carrot_y) - 6, 32, 24))
            else:
                draw_crop_food(screen, self.center_x + sx, int(self.carrot_y + 6), game_state.crop, r=24)

        # 4. Tension 게이지 (pulling 중에만 표시, 도정 단계에서는 미표시)
        if self.pull_phase == "pulling" and not self.stage_clear and (not self.is_rice or self.rice_phase == "thresh"):
            gx, gy, gw, gh = 250, 444, 300, 16
            pygame.draw.rect(screen, (40, 35, 30), (gx, gy, gw, gh), border_radius=4)
            fill_w = int((gw - 4) * (self.tension / 100.0))
            if fill_w > 0:
                # 초록 → 빨강 그라데이션
                gauge_color = mix_color((80, 175, 110), (220, 60, 45), self.tension / 100.0)
                pygame.draw.rect(screen, gauge_color, (gx + 2, gy + 2, fill_w, gh - 4), border_radius=3)

            # 감자: 흔들어 풀린 정도 게이지 (다 차면 쏙 뽑힌다)
            if self.is_potato:
                lx, ly, lw, lh = 250, 428, 300, 13
                pygame.draw.rect(screen, (40, 35, 30), (lx, ly, lw, lh), border_radius=4)
                lfill = int((lw - 4) * (self.potato_loosen / 100.0))
                if lfill > 0:
                    pygame.draw.rect(screen, (210, 180, 90), (lx + 2, ly + 2, lfill, lh - 4), border_radius=3)
                cap = get_font(12).render("풀림", True, (236, 224, 200))
                screen.blit(cap, (lx - cap.get_width() - 8, ly - 1))

            # 경고 텍스트 — 어두운 흙 위에서도 읽히도록 알약 배경 + 밝은 색
            font_t = get_font(14)
            warn = self.tension > 50.0
            if self.is_potato:
                txt = "너무 거칠어요! 살살 흔드세요." if warn else "좌우로 번갈아 흔들어 캐내세요!"
            elif self.is_rice:
                txt = "너무 빨라요! 천천히 흔드세요." if warn else "마우스를 드래그해 좌우로 흔들어 터세요."
            elif self.is_apple:
                txt = "너무 빨라요! 천천히 클릭하세요." if warn else "적당한 속도로 클릭하세요."
            else:
                txt = "너무 홱 채면 상해요! 살살." if warn else "잡고 위로 쭉 끌어올려 뽑으세요."
            color = (255, 124, 96) if warn else (236, 224, 200)
            surf = font_t.render(txt, True, color)
            wx, wy = 400 - surf.get_width() // 2, gy + 22
            chip = pygame.Surface((surf.get_width() + 18, surf.get_height() + 7), pygame.SRCALPHA)
            pygame.draw.rect(chip, (20, 16, 14, 195), chip.get_rect(), border_radius=9)
            screen.blit(chip, (wx - 9, wy - 4))
            screen.blit(surf, (wx, wy))

        # 5. 피드백 텍스트
        if self.pull_phase == "feedback" and self.feedback_text:
            font = get_font(24)
            color = (255, 220, 120) if "쏙" in self.feedback_text or "툭" in self.feedback_text else (210, 100, 80)
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
            
            if self.is_potato:
                t2 = font_b.render("감자를 마우스 왼쪽 버튼으로 누른 채", True, (200, 180, 140))
            elif self.is_rice:
                t2 = font_b.render("벼를 마우스 왼쪽 버튼으로 누른 채", True, (200, 180, 140))
            elif self.is_apple:
                t2 = font_b.render("마우스 왼쪽 버튼을 연타해서", True, (200, 180, 140))
            else:
                t2 = font_b.render("당근을 잡고 마우스를 위로 끌어", True, (200, 180, 140))
            screen.blit(t2, (400 - t2.get_width() // 2, 260))
            
            food_eul = append_josa(current_crop()["food"], "을/를")
            if self.is_apple:
                t3 = font_b.render(f"{food_eul} 조금씩 당겨 따내세요.", True, (200, 180, 140))
                t4 = font_b.render("너무 빠르게 하면 꼭지가 상해 못 쓰게 됩니다.", True, (230, 110, 90))
            elif self.is_potato:
                t3 = font_b.render("좌우로 조금씩 흔들며 뽑아 캐내세요.", True, (200, 180, 140))
                t4 = font_b.render("너무 거칠게 흔들면 감자가 상하니 주의하세요.", True, (230, 110, 90))
            elif self.is_rice:
                t3 = font_b.render("좌우로 흔들어 이삭을 털고 (탈곡),", True, (200, 180, 140))
                t4 = font_b.render("마우스로 비벼 낟알의 껍질을 벗기세요 (도정).", True, (200, 180, 140))
            else:
                t3 = font_b.render(f"{food_eul} 쭉 뽑아 올리세요.", True, (200, 180, 140))
                t4 = font_b.render("너무 홱 잡아채면 상해서 못 쓰게 됩니다.", True, (230, 110, 90))
            screen.blit(t3, (400 - t3.get_width() // 2, 290))
            screen.blit(t4, (400 - t4.get_width() // 2, 330))
        elif self.stage_clear:
            font = get_font(28)
            t = font.render("수확 완료!", True, (200, 100, 0))
            panel = pygame.Rect(300, 200, 200, 50)
            draw_wood_panel(screen, panel)
            screen.blit(t, (400 - t.get_width() // 2, 210))
            draw_bottom_bar(screen, "결과", f"수확 점수: {game_state.score}")
        else:
            food_eul = append_josa(current_crop()["food"], "을/를")
            if self.is_apple:
                draw_bottom_bar(screen, "수확하기", f"마우스를 연타해 {food_eul} 당겨 따내세요. 너무 빠르면 상합니다.")
            elif self.is_potato:
                draw_bottom_bar(screen, "수확하기", f"감자를 잡고 좌우로 번갈아 흔들어 캐내세요. 너무 거칠면 상합니다.")
            elif self.is_rice:
                draw_bottom_bar(screen, "수확하기", f"좌우로 흔들어 이삭을 털고, 비벼서 껍질을 벗기세요.")
            else:
                draw_bottom_bar(screen, "수확하기", f"{food_eul} 잡고 마우스를 위로 쭉 끌어 뽑으세요. 너무 홱 채면 상합니다.")
