"""공통 UI 애니메이션 및 파티클 시스템 유틸리티.

내러티브 연출용 타이프라이터 효과 및 반딧불이 입자 효과를 통합하여 코드 중복을 제거한다.
"""

import pygame
import random
import math
from core import audio


class Typewriter:
    """텍스트가 한 글자씩 타이핑 효과음과 함께 출력되는 클래스."""
    def __init__(self, char_delay=0.065):
        self.text_to_print = ""
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0.0
        self.char_delay = char_delay
        self.finished = False

    def set_text(self, text):
        """출력할 대상 텍스트를 초기화하여 시작 상태로 만든다."""
        self.text_to_print = text
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0.0
        self.finished = False if text else True

    def skip(self):
        """텍스트 연출을 건너뛰고 전체를 바로 보여준다."""
        self.printed_text = self.text_to_print
        self.char_idx = len(self.text_to_print)
        self.finished = True

    def update(self, dt, fast_forward=False):
        """시간 누적에 따라 한 글자씩 추가한다. 배속 상태일 때 속도를 증폭시킨다."""
        if self.finished:
            return
        effective_dt = dt * 6.0 if fast_forward else dt
        self.char_timer += effective_dt
        while self.char_timer >= self.char_delay and not self.finished:
            self.char_timer -= self.char_delay
            if self.char_idx < len(self.text_to_print):
                char = self.text_to_print[self.char_idx]
                self.printed_text += char
                self.char_idx += 1
                # 배속 연출 시 소리가 중첩되어 찢어지는 현상을 방지하기 위해 일정 빈도로만 소리 재생
                if not fast_forward or (self.char_idx % 3 == 0):
                    audio.type_tick(char)
            else:
                self.finished = True


class FireflyEmitter:
    """화면에 부유하는 반딧불이 입자(꿈 입자)들을 시뮬레이션하고 렌더링하는 클래스."""
    def __init__(self, count=16, bounds_x=(10, 790), bounds_y=(10, 590)):
        self.bounds_x = bounds_x
        self.bounds_y = bounds_y
        self.fireflies = []
        for _ in range(count):
            self.fireflies.append({
                'x': random.randint(bounds_x[0], bounds_x[1]),
                'y': random.randint(bounds_y[0], bounds_y[1]),
                'speed_x': random.uniform(-10.0, 10.0),
                'speed_y': random.uniform(-5.0, 5.0),
                'scale_timer': random.uniform(0.0, 6.28),
                'size': random.uniform(2.5, 5.0)
            })

    def update(self, dt):
        """입자의 위치 및 투명도 타이머를 업데이트하고 경계 바운스 처리."""
        for f in self.fireflies:
            f['x'] += f['speed_x'] * dt
            f['y'] += f['speed_y'] * dt
            f['scale_timer'] += 2.0 * dt
            
            # 경계 충돌 처리
            if f['x'] < self.bounds_x[0] or f['x'] > self.bounds_x[1]:
                f['speed_x'] *= -1
                f['x'] = max(self.bounds_x[0], min(self.bounds_x[1], f['x']))
            if f['y'] < self.bounds_y[0] or f['y'] > self.bounds_y[1]:
                f['speed_y'] *= -1
                f['y'] = max(self.bounds_y[0], min(self.bounds_y[1], f['y']))

    def draw(self, screen):
        """화면에 알파 블렌딩된 글로우 효과를 가진 반딧불이 렌더링."""
        for f in self.fireflies:
            alpha = int(110 + 70 * math.sin(f['scale_timer']))
            alpha = max(0, min(255, alpha))
            glow_color = (255, 235, 140)
            size = f['size']
            
            glow_surf = pygame.Surface((int(size * 6), int(size * 6)), pygame.SRCALPHA)
            # 은은한 외곽 글로우 효과
            pygame.draw.circle(
                glow_surf, 
                (glow_color[0], glow_color[1], glow_color[2], int(alpha * 0.45)), 
                (int(size * 3), int(size * 3)), 
                int(size * 2.5)
            )
            # 중심 밝은 입자 효과
            pygame.draw.circle(
                glow_surf, 
                (255, 255, 200, alpha), 
                (int(size * 3), int(size * 3)), 
                int(size * 1.1)
            )
            screen.blit(glow_surf, (int(f['x'] - size * 3), int(f['y'] - size * 3)))
