"""특별 이벤트 미니게임 — 씨앗 받기.

간밤의 바람에 흩날린 씨앗과 당근을, 바구니를 좌우로 움직여 받아낸다.
돌멩이와 썩은 잎은 피한다. 끝나면 점수만큼 이해도를 얻고 밭으로 돌아간다.
드래그 정렬(stage1)이나 탭하기와 다른, '받기' 방식의 손맛을 노린 새 미니게임."""
import random
import pygame
from core.game_state import game_state
from core.assets import sprites, get_font, draw_tiled_background, WHITE, TEXT_DARK, TEXT_MUTED
from core.ui import draw_top_bar, draw_bottom_bar
from core import audio

GOOD = {"seed": 100, "carrot": 150}
BAD = {"rock": -60, "leaf": -60}


class FallItem:
    def __init__(self, kind, x, vy):
        self.kind = kind
        self.sprite = sprites[kind]
        self.x = float(x)
        self.y = -30.0
        self.vy = vy
        self.good = kind in GOOD
        self.dead = False

    def update(self, dt):
        self.y += self.vy * dt

    def draw(self, screen):
        s = self.sprite
        screen.blit(s, (int(self.x - s.get_width() / 2), int(self.y - s.get_height() / 2)))


class SeedCatchScene:
    DURATION = 20.0
    PROMPT = "바구니를 움직여 씨앗과 당근을 받으세요. 돌멩이와 썩은 잎은 피하세요."

    def __init__(self):
        game_state.timer = self.DURATION
        game_state.score = 0
        self.basket = sprites["basket"]
        self.bw = self.basket.get_width()
        self.bx = 400.0          # 바구니 중심 x (마우스를 따라감)
        self.basket_y = 360      # 하단 정보 바(486~)에 가리지 않게 그 위에 둔다
        self.items = []
        self.spawn_timer = 0.0
        self.spawn_interval = 0.85
        self.caught = 0
        self.missed = 0
        self.done = False
        self.finished = False
        self.end_timer = 1.8
        self.flash = ""
        self.flash_color = WHITE
        self.flash_t = 0.0

    # --------------------------------------------------------------- 입력
    def handle_events(self, events):
        if self.done:
            return
        for event in events:
            if event.type == pygame.MOUSEMOTION:
                self.bx = float(event.pos[0])

    # --------------------------------------------------------------- 진행
    def _spawn(self):
        if random.random() < 0.7:
            kind = "carrot" if random.random() < 0.22 else "seed"
        else:
            kind = random.choice(list(BAD))
        elapsed = self.DURATION - max(0.0, game_state.timer)
        vy = random.uniform(155, 235) + elapsed * 4.0   # 시간이 갈수록 조금씩 빨라짐
        self.items.append(FallItem(kind, random.randint(54, 746), vy))

    def _set_flash(self, text, color):
        self.flash, self.flash_color, self.flash_t = text, color, 0.5

    def update(self, dt):
        if self.done:
            self.end_timer -= dt
            if self.end_timer <= 0:
                self._finish()
            return

        game_state.timer -= dt
        self.flash_t = max(0.0, self.flash_t - dt)
        if game_state.timer <= 0:
            game_state.timer = 0
            self.done = True
            return

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self._spawn()
            self.spawn_interval = max(0.45, self.spawn_interval * 0.985)

        half = self.bw // 2
        self.bx = max(half, min(800 - half, self.bx))

        for it in self.items:
            it.update(dt)
            if it.dead:
                continue
            # 바구니 입구 밴드에 들어오고 x가 겹치면 받기
            if self.basket_y <= it.y <= self.basket_y + 36 and abs(it.x - self.bx) < self.bw * 0.42:
                it.dead = True
                if it.good:
                    game_state.score += GOOD[it.kind]
                    self.caught += 1
                    audio.play("harvest")
                    self._set_flash("+" + str(GOOD[it.kind]), (150, 230, 150))
                else:
                    game_state.score = max(0, game_state.score + BAD[it.kind])
                    audio.play("break")
                    self._set_flash(str(BAD[it.kind]), (235, 120, 90))
            elif it.y > 620:
                it.dead = True
                if it.good:
                    self.missed += 1
        self.items = [it for it in self.items if not it.dead]

    def _finish(self):
        if self.finished:
            return
        self.finished = True
        s = game_state.score
        bonus = 18 if s >= 600 else 12 if s >= 400 else 7 if s >= 200 else 3
        game_state.understanding += bonus
        game_state.transition_text = (
            "흩날리던 씨앗을 거두었다.\n\n"
            f"받은 것: {self.caught}개    점수: {s}\n"
            f"작은 것 하나도 허투루 하지 않는 마음.  이해도 +{bonus}"
        )
        game_state.transition_next = game_state.return_scene
        game_state.is_clear_transition = True
        game_state.current_scene = "transition"

    # --------------------------------------------------------------- 그리기
    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)

        for it in self.items:
            it.draw(screen)

        # 바구니
        screen.blit(self.basket, (int(self.bx - self.bw // 2), self.basket_y))

        # 받기/놓침 피드백
        if self.flash_t > 0 and self.flash:
            f = get_font(22).render(self.flash, True, self.flash_color)
            screen.blit(f, (int(self.bx - f.get_width() // 2), self.basket_y - 26))

        draw_top_bar(screen)

        if self.done:
            draw_bottom_bar(screen, "거두기 끝", f"받은 것 {self.caught}개 · 점수 {game_state.score}")
        else:
            draw_bottom_bar(screen, "씨앗 받기", self.PROMPT)
