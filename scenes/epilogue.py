# -*- coding: utf-8 -*-
"""에필로그 — '아버지의 새벽'. 진엔딩을 본 뒤 타이틀에서 열린다.

회상 구조의 반전: 본편이 '자식이 아버지의 시간을 이해하는 꿈'이었다면,
에필로그는 그 시간의 원본 — 아이가 반찬을 밀어내던 무렵, 아버지의 하루다.
5개의 비트(새벽·아침·한낮·해 질 녘·밤 식탁)로 흐르고, 두 번은 실제 밭일
손맛 인터랙션(물 주기·흙 북돋기)을 아버지의 손으로 직접 한다.
"""
import pygame
from core.game_state import game_state
from core.assets import get_font, TEXT_DARK, TEXT_MUTED, WHITE, GOLD
from core.ui import draw_light_panel, draw_story_backdrop, wrap_text
from core.pixelfx import pixel_rect, glow_sprite, blit_glow, CHAMFER
from core.ui_utils import Typewriter
from core import audio
from core import save_system
from core import i18n


# (시간 라벨, 본문, 인터랙션 클래스 이름 또는 None, 밭 틴트 RGBA 또는 None)
BEATS = [
    ("[새벽 네 시]",
     "아이는 아직 잠들어 있다.\n숨소리를 확인하고, 아버지는 조용히 문을 닫는다.\n밭은 어제보다 조금 자라 있다.\n물부터 준다. 하루는 늘 물에서 시작된다.",
     "WaterPour", (30, 20, 60, 90)),
    ("[해 뜰 무렵]",
     "이랑 사이의 풀을 뽑는다.\n아이 입에 들어갈 것이니, 약은 치지 않는다.\n손이 조금 더 거칠어지는 쪽을 고른다.",
     "WeedPull", (60, 45, 70, 45)),
    ("[한낮]",
     "새참 보자기를 풀다가, 문득 웃는다.\n어젯밤 아이가 반찬을 밀어냈다.\n'맛없어.' 그 한마디가 온종일 따라다닌다.\n그래도 — 아이는 크고 있다.",
     None, None),
    ("[해 질 녘]",
     "흙을 북돋아 준다.\n보이지 않는 곳이 든든해야\n보이는 것이 견딘다.",
     "SoilMound", (100, 40, 0, 60)),
    ("[밤 — 식탁]",
     "아이가 또 당근을 밀어낸다.\n아버지는 잠깐 말을 멈췄다가, 조용히 그릇을 거둔다.\n괜찮다. 내일 또 심으면 된다.\n언젠가 이 맛을 알게 될 날이 올 테니까.\n\n— 그리고 그 날은, 당신이 이미 다녀온 꿈이다.",
     None, None),
]


class EpilogueScene:
    def __init__(self):
        self.font_label = get_font(22)
        self.font_body = get_font(17)
        self.font_hint = get_font(14)

        # 아버지의 당근밭 — 실제 FarmScene을 배경 호스트로 쓴다 (UI는 그리지 않음)
        game_state.crop = "carrot"
        game_state.nightmare = False
        from scenes.farm import FarmScene
        self.farm = FarmScene()
        self.farm.tutorial_active = False
        self.farm.sim.growth = int(self.farm.sim.growth_goal * 0.45)
        self.farm.sim.moisture = 40
        self.farm.sim.weeds = 46          # 아침 김매기가 그럴듯하게
        from core.game_state import get_season_colors
        self.farm.season_colors = get_season_colors(self.farm.sim.growth, self.farm.sim.growth_goal)

        self.beat = 0
        self.phase = "text"               # text → (interact) → text ...
        self.typewriter = Typewriter(0.05)
        self.interaction = None
        self.done_timer = 0.0
        self._load_beat()

    # ------------------------------------------------------------------ 진행
    def _load_beat(self):
        label, text, _inter, _tint = BEATS[self.beat]
        self.phase = "text"
        self.interaction = None
        # 통째로 번역 후 폭에 맞춰 개행 (HANDOFF 팁#5)
        body = i18n.t(text)
        lines = []
        for p in body.split("\n"):
            lines.extend(wrap_text(p, self.font_body, 660) if p else [""])
        self.typewriter.set_text("\n".join(lines))

    def _start_interaction(self):
        from scenes import tending
        cls = getattr(tending, BEATS[self.beat][2])
        self.interaction = cls(self.farm)
        self.farm.interaction = self.interaction
        self.phase = "interact"

    def _advance(self):
        if self.beat + 1 < len(BEATS):
            self.beat += 1
            audio.play("page")
            self._load_beat()
        else:
            # 끝 — 기록하고 타이틀로
            save_system.update_meta(epilogue_seen=True)
            from core import achievements
            achievements.unlock("dawn_reply")
            audio.play("epiphany")
            game_state.current_scene = "title"

    # ------------------------------------------------------------------ 입출력
    def handle_events(self, events):
        if self.phase == "interact" and self.interaction:
            for event in events:
                self.interaction.handle(event)
            return
        for event in events:
            advance = (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1) or (
                event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN))
            if not advance:
                continue
            if not self.typewriter.finished:
                self.typewriter.skip()
            elif BEATS[self.beat][2] and self.interaction is None:
                audio.play("click")
                self._start_interaction()
            else:
                self._advance()

    def update(self, dt):
        if self.phase == "interact" and self.interaction:
            self.interaction.update(dt)
            if self.interaction.done:
                self.farm.interaction = None
                self.interaction = None
                self._advance()
            return
        self.typewriter.update(dt, getattr(game_state, "fast_forward", False))

    # ------------------------------------------------------------------ 그리기
    def draw(self, screen):
        label, _text, inter_name, tint = BEATS[self.beat]
        last = (self.beat == len(BEATS) - 1)

        if last:
            # 밤 식탁 — 밭 대신 고요한 밤 배경 + 온기 글로우
            draw_story_backdrop(screen, "night")
            blit_glow(screen, glow_sprite(160, (255, 210, 120), px=5, steps=(10, 20, 32)), (400, 300))
        else:
            # 아버지의 밭 — HUD 없이 배경·밭만 빌려 그린다
            r = self.farm.renderer
            from core.assets import draw_tiled_background
            sc = self.farm.season_colors
            draw_tiled_background(screen, 800, 600, sc["grass"], sc["grass_dark"],
                                  sc["dirt"], sc["dirt_dark"])
            r.draw_farm_plot(screen, self.farm)
            if tint:
                veil = pygame.Surface((800, 600), pygame.SRCALPHA)
                veil.fill(tint)
                screen.blit(veil, (0, 0))

        if self.phase == "interact" and self.interaction:
            self.interaction.draw(screen)
            return

        # 시간 라벨 — 상단 중앙 알약
        ls = self.font_label.render(label, True, (255, 240, 206))
        pill_w, pill_h = ls.get_width() + 40, ls.get_height() + 14
        pill = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pixel_rect(pill, (24, 26, 30, 200), (0, 0, pill_w, pill_h), chamfer=CHAMFER)
        pixel_rect(pill, (229, 192, 124, 220), (0, 0, pill_w, pill_h), width=1, chamfer=CHAMFER)
        screen.blit(pill, (400 - pill_w // 2, 42))
        screen.blit(ls, (400 - ls.get_width() // 2, 49))

        # 본문 패널 — 하단
        panel = pygame.Rect(60, 396, 680, 172)
        draw_light_panel(screen, panel)
        y = panel.y + 20
        for line in self.typewriter.printed_text.split("\n"):
            surf = self.font_body.render(line, True, TEXT_DARK)
            screen.blit(surf, (panel.x + 28, y))
            y += self.font_body.get_height() + 5

        if self.typewriter.finished:
            if inter_name and self.interaction is None:
                hint = "클릭해 밭일을 시작"
            elif last:
                hint = "클릭하여 마치기"
            else:
                hint = "클릭하여 계속"
            hs = self.font_hint.render(hint, True, TEXT_MUTED)
            screen.blit(hs, (panel.right - hs.get_width() - 24, panel.bottom - 30))
