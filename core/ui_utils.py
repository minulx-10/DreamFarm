"""공통 UI 애니메이션 및 파티클 시스템 유틸리티.

내러티브 연출용 타이프라이터 효과 및 반딧불이 입자 효과를 통합하여 코드 중복을 제거한다.
"""

import pygame
import random
import math
from core import audio


# 텍스트 속도 설정(설정창에서 변경) — 타자기 char_delay 에 곱해지는 배속
_TEXT_SPEED_FACTORS = {"slow": 0.6, "normal": 1.0, "fast": 1.75}


def text_speed_factor():
    """현재 텍스트 속도 설정의 배속 (설정은 캐시돼 있어 매 프레임 호출해도 가볍다)."""
    from core import save_system
    return _TEXT_SPEED_FACTORS.get(save_system.get_setting("text_speed"), 1.0)


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
        effective_dt *= text_speed_factor()   # 설정창 '텍스트 속도' 반영 (느림/보통/빠름)
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
        """반딧불이 렌더링 — '계단 알파' 도트 글로우(캐시)로. 매끈한 원+연속 알파는
        큰 픽셀 규칙에 어긋나고 모자이크 블러처럼 보였다. 밝기는 set_alpha 로 맥동."""
        from core.pixelfx import glow_sprite, blit_glow
        for f in self.fireflies:
            alpha = int(110 + 70 * math.sin(f['scale_timer']))
            alpha = max(0, min(255, alpha))
            g = glow_sprite(f['size'] * 2.5, (255, 235, 140), px=3,
                            steps=(115,), core=((255, 255, 200), 255))
            blit_glow(screen, g, (f['x'], f['y']), alpha)
