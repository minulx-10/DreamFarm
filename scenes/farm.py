import pygame
import random
from core.game_state import append_josa, game_state
from core.assets import *
from core.ui import clamp_percent, draw_light_panel, draw_wood_panel, draw_top_bar, draw_bottom_bar


class Button:
    def __init__(self, x, y, w, h, text, value):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.value = value
        self.font = get_font(20)

    def draw(self, screen):
        pygame.draw.rect(screen, WOOD_DARK, self.rect.move(3, 3), border_radius=6)
        pygame.draw.rect(screen, PANEL_PALE, self.rect, border_radius=6)
        pygame.draw.rect(screen, WOOD_LIGHT, self.rect.inflate(-6, -6), border_radius=4)
        pygame.draw.rect(screen, TEXT_DARK, self.rect, 2, border_radius=6)
        text_surf = self.font.render(self.text, True, TEXT_DARK)
        screen.blit(
            text_surf,
            (
                self.rect.centerx - text_surf.get_width() // 2,
                self.rect.centery - text_surf.get_height() // 2,
            ),
        )

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class FarmScene:
    def __init__(self):
        self.day = 1
        self.growth = 0
        self.growth_goal = 36
        self.moisture = 44
        self.health = 66
        self.weeds = 25
        self.pests = 14
        self.drainage = 55
        self.stress = 0
        self.actions_taken = 0
        self.last_action = ""
        self.message = "상태를 확인하세요."
        self.notice = "추천 행동: 살펴보기"
        self.memory_cooldown = 2
        self.minigame_cooldown = 5
        self.last_minigame = None
        self.memories_seen = set()
        self.buttons = []
        self.rebuild_buttons()

    def rebuild_buttons(self):
        actions = self.get_available_actions()
        self.buttons = []
        start_x = 440
        start_y = 330
        for i, action in enumerate(actions):
            bx = start_x + (i % 2) * 160
            by = start_y + (i // 2) * 72
            self.buttons.append(Button(bx, by, 140, 54, action, action))

    def get_available_actions(self):
        if self.growth >= self.growth_goal:
            return ["수확하기", "살펴보기", "기다리기", "흙 북돋기"]

        priority = ["살펴보기"]
        if self.moisture < 35:
            priority.append("물 주기")
        if self.moisture > 72 or self.drainage < 35:
            priority.append("배수로 정리")
        if self.weeds > 28:
            priority.append("잡초 뽑기")
        if self.pests > 24:
            priority.append("해충 살피기")
        if self.health < 55 or self.stress > 35:
            priority.append("흙 북돋기")

        fillers = ["기다리기", "물 주기", "잡초 뽑기", "해충 살피기", "배수로 정리", "흙 북돋기"]
        for action in fillers:
            if len(priority) >= 4:
                break
            if action not in priority:
                priority.append(action)

        return priority[:4]

    def clamp_stats(self):
        self.moisture = max(0, min(100, self.moisture))
        self.health = max(0, min(100, self.health))
        self.weeds = max(0, min(100, self.weeds))
        self.pests = max(0, min(100, self.pests))
        self.drainage = max(0, min(100, self.drainage))
        self.stress = max(0, min(100, self.stress))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in self.buttons:
                    if btn.is_clicked(event.pos):
                        self.do_action(btn.value)
                        break

    def do_action(self, action):
        if action == "수확하기":
            if self.growth >= self.growth_goal and self.health >= 35:
                game_state.understanding += 12
                game_state.current_scene = "ending"
            else:
                self.health -= 8
                self.stress += 10
                self.message = "아직 성장 수치가 부족합니다."
                self.notice = "추천 행동: 수확하지 말고 밭 상태를 먼저 회복하세요."
            return

        self.actions_taken += 1
        self.last_action = action
        difficulty = 1 + self.growth // 6
        result = self.apply_action(action, difficulty)
        self.apply_field_pressure(difficulty)

        if self.is_good_turn():
            gain = 1
            if action == "기다리기" and self.health >= 74 and self.weeds < 35 and self.pests < 30:
                gain += 1
            self.growth += gain
            game_state.understanding += 1
            result += f" 당근이 조금 더 자랐습니다. (+성장 {gain})"
        elif self.health <= 20:
            self.growth = max(0, self.growth - 1)
            result += " 작물이 버티지 못해 성장이 조금 늦어졌습니다."

        self.message = result
        self.notice = self.build_notice()
        self.clamp_stats()
        self.try_trigger_memory()
        if game_state.current_scene == "farm":
            self.try_trigger_minigame(action)
        self.rebuild_buttons()

    def apply_action(self, action, difficulty):
        if action == "살펴보기":
            game_state.understanding += 1
            self.stress = max(0, self.stress - 4)
            return self.inspect_message()

        if action == "물 주기":
            if self.moisture < 35:
                self.moisture += 34
                self.health += 4
                self.stress = max(0, self.stress - 6)
                return "물 주기 성공: 수분이 회복되었습니다."
            if self.moisture > 70:
                self.moisture += 18
                self.health -= 12 + difficulty
                self.stress += 10
                return "물 주기 실패: 수분이 너무 높아 건강이 감소했습니다."
            self.moisture += 18
            self.health += 0
            return "물 주기 완료: 수분이 증가했습니다."

        if action == "잡초 뽑기":
            if self.weeds > 20:
                self.weeds -= 34
                self.health += 3
                return "잡초 뽑기 성공: 잡초 수치가 크게 감소했습니다."
            self.health -= 5
            self.stress += 6
            return "잡초 뽑기 실패: 잡초가 적어 건강이 감소했습니다."

        if action == "해충 살피기":
            if self.pests > 18:
                self.pests -= 32
                self.health += 3
                return "해충 살피기 성공: 해충 수치가 감소했습니다."
            self.stress = max(0, self.stress - 2)
            return "해충 살피기 완료: 큰 해충은 없습니다."

        if action == "배수로 정리":
            if self.moisture > 68 or self.drainage < 45:
                self.moisture -= 22
                self.drainage += 22
                self.health += 1
                return "배수로 정리 성공: 수분이 낮아지고 배수가 회복되었습니다."
            self.drainage += 8
            self.stress += 5
            return "배수로 정리 효과 낮음: 지금은 다른 행동이 더 필요합니다."

        if action == "흙 북돋기":
            if self.health < 65 or self.stress > 24:
                self.health += 8
                self.stress = max(0, self.stress - 10)
                self.drainage += 4
                return "흙 북돋기 성공: 건강과 스트레스가 회복되었습니다."
            self.health += 2
            self.moisture -= 4
            return "흙 북돋기 완료: 변화는 작습니다."

        if action == "기다리기":
            if self.is_good_turn():
                self.moisture -= 8
                return "기다리기 성공: 안정 상태라 성장이 진행됩니다."
            self.health -= 8 + difficulty
            self.stress += 8
            return "기다리기 실패: 문제가 있는 상태라 건강이 감소했습니다."

        return "행동을 처리했습니다."

    def apply_field_pressure(self, difficulty):
        self.day += 1
        self.moisture -= random.randint(4, 7 + difficulty)
        self.weeds += random.randint(4, 7 + difficulty)
        self.pests += random.randint(2, 5 + difficulty)

        if self.moisture > 75:
            self.health -= 5 + difficulty
            self.drainage -= 5
        if self.moisture < 22:
            self.health -= 6 + difficulty
            self.stress += 5
        if self.weeds > 55:
            self.health -= 5 + difficulty
        if self.pests > 48:
            self.health -= 6 + difficulty
        if random.random() < 0.18 + difficulty * 0.04:
            self.drainage -= random.randint(4, 10)

    def is_good_turn(self):
        return (
            30 <= self.moisture <= 72
            and self.health >= 45
            and self.weeds <= 62
            and self.pests <= 58
            and self.stress <= 62
        )

    def inspect_message(self):
        warnings = []
        if self.moisture < 30:
            warnings.append("수분 부족")
        elif self.moisture > 72:
            warnings.append("수분 과다")
        if self.weeds > 45:
            warnings.append("잡초 많음")
        if self.pests > 38:
            warnings.append("해충 많음")
        if self.health < 50:
            warnings.append("건강 낮음")
        if self.drainage < 35:
            warnings.append("배수 낮음")

        if not warnings:
            return "상태 확인: 밭이 안정적입니다."
        return "상태 확인: " + ", ".join(warnings[:3]) + "."

    def build_notice(self):
        if self.growth >= self.growth_goal:
            return "추천 행동: 수확하기"
        if self.health < 45:
            return "추천 행동: 흙 북돋기"
        if self.moisture < 30:
            return "추천 행동: 물 주기"
        if self.moisture > 72:
            return "추천 행동: 배수로 정리"
        if self.weeds > 50:
            return "추천 행동: 잡초 뽑기"
        if self.pests > 42:
            return "추천 행동: 해충 살피기"
        if self.is_good_turn():
            return "추천 행동: 기다리기"
        return "추천 행동: 살펴보기"

    def grade_text(self, value, low_bad=True):
        if low_bad:
            if value >= 70:
                return "좋음"
            if value >= 45:
                return "보통"
            return "위험"
        if value <= 30:
            return "낮음"
        if value <= 65:
            return "주의"
        return "높음"

    def try_trigger_memory(self):
        if self.memory_cooldown > 0:
            self.memory_cooldown -= 1
            return

        forced_key = None
        if self.growth >= 6 and "first" not in self.memories_seen:
            forced_key = "first"
        elif self.growth >= 12 and "second" not in self.memories_seen:
            forced_key = "second"

        u = game_state.understanding
        chance = 0.24 if u < 18 else 0.14 if u < 45 else 0.06
        if forced_key is None and random.random() >= chance:
            return

        memory = self.pick_memory(forced_key)
        if not memory:
            return

        key, title, text = memory
        self.memories_seen.add(key)
        self.memory_cooldown = 4 if u < 25 else 6 if u < 50 else 8
        game_state.memory_title = title
        game_state.memory_text = text
        game_state.memory_next = "farm"
        game_state.current_scene = "memory"

    def pick_memory(self, forced_key):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        name_ga = append_josa(name, "이/가")
        u = game_state.understanding

        if u < 18:
            memories = [
                (
                    "first",
                    "희미한 식탁",
                    f"식탁 위에 당근 반찬이 놓여 있다.\n{name_eun} 젓가락으로 그릇을 밀어냈고, 아버지는 잠깐 말을 멈췄다.\n그때는 그 침묵이 왜 길게 느껴졌는지 몰랐다.",
                ),
                (
                    "low_market",
                    "장바구니 소리",
                    f"비닐봉지가 문고리에 부딪히는 소리가 난다.\n아버지는 흙 묻은 당근을 꺼내며 '오늘 건 달다'고 말했다.\n{name_ga}는 대답 대신 물컵만 만지작거렸다.",
                ),
                (
                    "second",
                    "남긴 접시",
                    "싱크대 옆에 남은 반찬 그릇이 보인다.\n작은 주황색 조각들이 물에 젖어 천천히 가라앉는다.\n어쩐지 꿈속의 흙냄새가 더 짙어진다.",
                ),
            ]
        elif u < 45:
            memories = [
                (
                    "first",
                    "다시 보이는 식탁",
                    f"당근 반찬을 밀어내던 손이 떠오른다.\n{name_eun} 그때 아버지의 표정보다 자기 입맛만 먼저 생각했다는 걸 알아차린다.",
                ),
                (
                    "mid_field",
                    "이른 아침",
                    "아버지는 아직 어두운 시간에 밭으로 나갔다.\n흙을 털어내는 손등에는 잔금이 많았다.\n그 손이 식탁 위 반찬을 만들었다는 생각이 뒤늦게 따라온다.",
                ),
                (
                    "second",
                    "한 조각의 무게",
                    "젓가락 끝에 걸린 당근 한 조각이 이상하게 무겁다.\n맛보다 먼저 떠오르는 건, 누군가의 기다림이었다.",
                ),
            ]
        else:
            memories = [
                (
                    "first",
                    "따뜻한 식탁",
                    f"식탁 위의 당근 반찬이 떠오른다.\n이번에는 밀어내고 싶다는 생각보다, 한 번쯤 제대로 맛보고 싶다는 마음이 먼저 든다.",
                ),
                (
                    "high_field",
                    "손등의 흙",
                    "아버지가 웃으며 손등의 흙을 털어낸다.\n그 모습은 무겁기보다 다정하다.\n꿈속의 밭도 조금은 덜 낯설게 느껴진다.",
                ),
                (
                    "second",
                    "짧은 고개 끄덕임",
                    f"{name_ga} 말없이 고개를 끄덕인다.\n무언가를 완전히 알게 된 건 아니지만, 이제 외면하고 싶지는 않다.",
                ),
            ]

        if forced_key:
            for memory in memories:
                if memory[0] == forced_key:
                    return memory

        candidates = [memory for memory in memories if memory[0] not in self.memories_seen]
        return random.choice(candidates or memories)

    def try_trigger_minigame(self, action):
        if action in ("살펴보기", "수확하기"):
            return
        if self.minigame_cooldown > 0:
            self.minigame_cooldown -= 1
            return

        risk = max(self.weeds, self.pests, abs(self.moisture - 52), 100 - self.health)
        chance = 0.06 + min(0.12, risk / 650)
        if random.random() >= chance:
            return

        candidates = []
        if self.weeds > 52:
            candidates.append(("stage1", 1, "[돌발 상황]\n\n밭에 씨앗과 잡동사니가 뒤섞였습니다.\n필요한 것만 골라 밭을 다시 정리하세요."))
        if self.moisture < 38 or action == "물 주기":
            candidates.append(("stage2", 3, "[돌발 상황]\n\n흙이 갑자기 물을 빨아들입니다.\n타이밍을 맞춰 알맞은 만큼만 물을 주세요."))
        if self.pests > 34 or self.health < 55:
            candidates.append(("stage3", 3, "[돌발 상황]\n\n잎 아래에서 해충이 한꺼번에 튀어나왔습니다.\n빠르게 눌러 작물을 지켜내세요."))

        if not candidates:
            return

        if self.last_minigame and len(candidates) > 1:
            candidates = [candidate for candidate in candidates if candidate[0] != self.last_minigame] or candidates

        total_weight = sum(weight for _, weight, _ in candidates)
        roll = random.uniform(0, total_weight)
        upto = 0
        mg, text = candidates[-1][0], candidates[-1][2]
        for candidate, weight, candidate_text in candidates:
            upto += weight
            if roll <= upto:
                mg, text = candidate, candidate_text
                break

        game_state.transition_text = text
        game_state.current_scene = "transition"
        game_state.is_clear_transition = False
        game_state.transition_next = mg
        game_state.return_scene = "farm"
        self.last_minigame = mg
        self.minigame_cooldown = 7 if mg == "stage1" else 5

    def update(self, dt):
        if self.health <= 0:
            self.health = 25
            self.stress = 45
            game_state.understanding = max(0, game_state.understanding - 8)
            self.message = "당근이 크게 시들었습니다. 다시 흙을 다독이며 회복시켜야 합니다."
            self.rebuild_buttons()

    def draw_status_meter(self, screen, label, value, x, y, color):
        font = get_font(17)
        label_surf = font.render(label, True, BLACK)
        screen.blit(label_surf, (x, y - 2))
        bar = pygame.Rect(x + 58, y, 155, 15)
        pygame.draw.rect(screen, (70, 55, 40), bar)
        fill = pygame.Rect(bar.x + 2, bar.y + 2, int((bar.w - 4) * clamp_percent(value)), bar.h - 4)
        pygame.draw.rect(screen, color, fill)
        pygame.draw.rect(screen, BLACK, bar, 2)

    def draw_labeled_meter(self, screen, label, value, max_value, x, y, w, color):
        font = get_font(16)
        label_surf = font.render(label, True, TEXT_DARK)
        value_surf = font.render(f"{value}/{max_value}", True, TEXT_DARK)
        screen.blit(label_surf, (x, y - 1))
        screen.blit(value_surf, (x + w - value_surf.get_width(), y - 1))

        bar = pygame.Rect(x, y + 22, w, 15)
        fill_w = int((bar.w - 4) * clamp_percent(value, max_value))
        pygame.draw.rect(screen, (82, 62, 42), bar)
        pygame.draw.rect(screen, color, (bar.x + 2, bar.y + 2, fill_w, bar.h - 4))
        pygame.draw.rect(screen, TEXT_DARK, bar, 2)

    def draw_field_summary(self, screen):
        panel = pygame.Rect(430, 82, 320, 100)
        draw_light_panel(screen, panel)
        title_font = get_font(20)
        title = title_font.render("밭 상태", True, TEXT_DARK)
        screen.blit(title, (450, 96))

        self.draw_labeled_meter(screen, "성장", self.growth, self.growth_goal, 450, 123, 130, (235, 150, 55))
        self.draw_labeled_meter(screen, "이해도", game_state.understanding, 60, 600, 123, 125, (120, 180, 90))

        status_font = get_font(16)
        health_text = status_font.render(f"건강 {self.grade_text(self.health)}", True, TEXT_DARK)
        screen.blit(health_text, (450, 162))

        if self.growth >= self.growth_goal:
            ready = status_font.render("수확 가능", True, (145, 55, 0))
            screen.blit(ready, (640, 162))

    def draw_meters(self, screen):
        panel = pygame.Rect(430, 190, 320, 100)
        draw_light_panel(screen, panel)
        self.draw_status_meter(screen, "수분", self.moisture, 452, 208, (80, 170, 240))
        self.draw_status_meter(screen, "건강", self.health, 452, 232, (90, 185, 95))
        self.draw_status_meter(screen, "잡초", self.weeds, 452, 256, (80, 140, 55))
        self.draw_status_meter(screen, "해충", self.pests, 452, 280, (210, 110, 60))

    def crop_positions(self):
        return [(112, 235), (210, 235), (308, 235), (112, 345), (210, 345), (308, 345)]

    def draw_crop(self, screen, x, y, growth_stage):
        mound = pygame.Rect(x - 24, y + 32, 48, 16)
        pygame.draw.rect(screen, DIRT_DARK, mound)
        pygame.draw.rect(screen, DIRT_COLOR, mound.inflate(-8, -6))

        if growth_stage <= 0:
            return
        if growth_stage < 5:
            sprite, offset = sprites["seed"], (-15, 21)
        elif growth_stage < 10:
            sprite, offset = sprites["sprout1"], (-15, 9)
        elif growth_stage < 16:
            sprite, offset = sprites["sprout2"], (-20, -2)
        elif growth_stage < 23:
            sprite, offset = sprites["sprout3"], (-22, -12)
        elif growth_stage < self.growth_goal:
            sprite, offset = sprites["sprout4"], (-24, -18)
        else:
            sprite, offset = sprites["carrot"], (-24, -45)
        screen.blit(sprite, (x + offset[0], y + offset[1]))

    def draw_farm_plot(self, screen):
        plot_rect = pygame.Rect(50, 145, 350, 305)
        draw_wood_panel(screen, plot_rect)
        inner_plot = plot_rect.inflate(-22, -22)

        if self.moisture > 72:
            base_color = (110, 75, 45)
        elif self.moisture < 28:
            base_color = (128, 78, 48)
        else:
            base_color = DIRT_COLOR

        pygame.draw.rect(screen, base_color, inner_plot)
        pygame.draw.rect(screen, DIRT_DARK, inner_plot, 4)

        for y in (inner_plot.y + 72, inner_plot.y + 182):
            pygame.draw.rect(screen, DIRT_DARK, (inner_plot.x + 20, y, inner_plot.w - 40, 56))
            pygame.draw.rect(screen, base_color, (inner_plot.x + 28, y + 8, inner_plot.w - 56, 40))
            for x in range(inner_plot.x + 28, inner_plot.right - 44, 40):
                pygame.draw.rect(screen, DIRT_DARK, (x, y + 8, 4, 40))

        if self.moisture < 28:
            for x in range(inner_plot.x + 35, inner_plot.right - 35, 55):
                pygame.draw.line(screen, (85, 55, 35), (x, inner_plot.y + 44), (x + 18, inner_plot.y + 58), 2)
                pygame.draw.line(screen, (85, 55, 35), (x + 10, inner_plot.y + 180), (x - 8, inner_plot.y + 198), 2)
        elif self.moisture > 72:
            for x in range(inner_plot.x + 30, inner_plot.right - 40, 65):
                pygame.draw.rect(screen, (95, 130, 150), (x, inner_plot.y + 214, 36, 8))

        growth_stage = max(0, min(self.growth, self.growth_goal))
        for x, y in self.crop_positions():
            self.draw_crop(screen, x, y, growth_stage)

        if self.weeds > 32:
            weed_count = 2 if self.weeds < 55 else 4
            weed_spots = [(86, 373), (258, 371), (348, 262), (166, 264)]
            for x, y in weed_spots[:weed_count]:
                screen.blit(sprites["weed"], (x, y))

        if self.pests > 32:
            bug_count = 1 if self.pests < 55 else 3
            bug_spots = [(150, 228), (284, 336), (332, 220)]
            for x, y in bug_spots[:bug_count]:
                screen.blit(sprites["bug"], (x, y))

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        self.draw_farm_plot(screen)

        title_font = get_font(24)
        title = f"{self.day}일째: 꿈속 당근밭"
        title_surf = title_font.render(title, True, TEXT_DARK)
        title_rect = pygame.Rect(50, 82, 350, 48)
        draw_wood_panel(screen, title_rect)
        screen.blit(
            title_surf,
            (
                title_rect.centerx - title_surf.get_width() // 2,
                title_rect.centery - title_surf.get_height() // 2,
            ),
        )

        self.draw_field_summary(screen)
        self.draw_meters(screen)
        action_panel = pygame.Rect(430, 300, 320, 164)
        draw_light_panel(screen, action_panel)
        action_title = get_font(20).render("오늘 할 일", True, TEXT_DARK)
        screen.blit(action_title, (450, 306))

        for btn in self.buttons:
            btn.draw(screen)

        draw_top_bar(screen, show_stats=False)
        draw_bottom_bar(screen, "농장 일지", f"{self.message} {self.notice}")
