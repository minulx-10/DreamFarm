import pygame
import random
from core.game_state import append_josa, game_state
from core.assets import *
from core.ui import draw_wood_panel, draw_top_bar, draw_bottom_bar


class Button:
    def __init__(self, x, y, w, h, text, value):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.value = value
        self.font = get_font(20)

    def draw(self, screen):
        pygame.draw.rect(screen, WOOD_DARK, self.rect.move(3, 3), border_radius=6)
        pygame.draw.rect(screen, WOOD_LIGHT, self.rect, border_radius=6)
        pygame.draw.rect(screen, WOOD_COLOR, self.rect.inflate(-6, -6), border_radius=4)
        pygame.draw.rect(screen, TEXT_BROWN, self.rect, 2, border_radius=6)
        text_surf = self.font.render(self.text, True, TEXT_BROWN)
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
        self.growth_goal = 24
        self.moisture = 45
        self.health = 72
        self.weeds = 18
        self.pests = 8
        self.drainage = 55
        self.stress = 0
        self.actions_taken = 0
        self.last_action = ""
        self.message = "꿈속의 밭은 조용하지만, 흙은 이미 목이 말라 보입니다."
        self.notice = "상태를 살피며 당근을 수확까지 키우세요."
        self.memory_cooldown = 2
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
                self.message = "아직 뽑기에는 이릅니다. 잎이 힘없이 흔들립니다."
                self.notice = "수확은 성장과 건강이 충분할 때 시도하세요."
            return

        self.actions_taken += 1
        self.last_action = action
        difficulty = 1 + self.growth // 6
        result = self.apply_action(action, difficulty)
        self.apply_field_pressure(difficulty)

        if self.is_good_turn():
            gain = 1 + (1 if self.health >= 70 else 0)
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
                self.moisture += 38
                self.health += 7
                self.stress = max(0, self.stress - 6)
                return "마른 흙이 물을 천천히 머금습니다."
            if self.moisture > 70:
                self.moisture += 18
                self.health -= 10 + difficulty
                self.stress += 8
                return "이미 젖은 흙에 물이 고였습니다. 뿌리가 답답해 보입니다."
            self.moisture += 20
            self.health += 2
            return "알맞게 물을 주었습니다. 잎 끝이 조금 살아납니다."

        if action == "잡초 뽑기":
            if self.weeds > 20:
                self.weeds -= 45
                self.health += 5
                return "잡초를 뽑아내자 당근 주변에 숨 쉴 틈이 생겼습니다."
            self.health -= 5
            self.stress += 6
            return "뽑을 잡초가 거의 없습니다. 괜히 흙만 뒤흔들었습니다."

        if action == "해충 살피기":
            if self.pests > 18:
                self.pests -= 42
                self.health += 5
                return "잎 아래 숨어 있던 해충을 미리 털어냈습니다."
            self.stress = max(0, self.stress - 2)
            return "큰 해충은 보이지 않습니다. 대신 잎 상태를 차분히 확인했습니다."

        if action == "배수로 정리":
            if self.moisture > 68 or self.drainage < 45:
                self.moisture -= 24
                self.drainage += 26
                self.health += 3
                return "고인 물길을 터 주자 흙냄새가 한결 가벼워졌습니다."
            self.drainage += 8
            self.stress += 5
            return "지금은 물길보다 흙 상태를 먼저 보는 편이 나아 보입니다."

        if action == "흙 북돋기":
            if self.health < 65 or self.stress > 24:
                self.health += 12
                self.stress = max(0, self.stress - 14)
                self.drainage += 4
                return "흙을 살짝 북돋우자 기울던 줄기가 다시 중심을 잡습니다."
            self.health += 2
            self.moisture -= 4
            return "흙을 다듬었습니다. 큰 변화는 없지만 밭이 단정해졌습니다."

        if action == "기다리기":
            if self.is_good_turn():
                self.growth += 1
                self.moisture -= 8
                return "손대지 않고 기다리자 당근이 조용히 뿌리를 내립니다."
            self.health -= 8 + difficulty
            self.stress += 8
            return "기다리는 사이 밭의 문제가 더 커졌습니다."

        return "잠시 밭을 둘러보았습니다."

    def apply_field_pressure(self, difficulty):
        self.day += 1
        self.moisture -= random.randint(3, 6 + difficulty)
        self.weeds += random.randint(3, 5 + difficulty)
        self.pests += random.randint(1, 3 + difficulty)

        if self.moisture > 75:
            self.health -= 4 + difficulty
            self.drainage -= 5
        if self.moisture < 22:
            self.health -= 5 + difficulty
            self.stress += 5
        if self.weeds > 55:
            self.health -= 4 + difficulty
        if self.pests > 48:
            self.health -= 5 + difficulty
        if random.random() < 0.15 + difficulty * 0.03:
            self.drainage -= random.randint(4, 10)

    def is_good_turn(self):
        return (
            30 <= self.moisture <= 72
            and self.health >= 45
            and self.weeds <= 70
            and self.pests <= 65
            and self.stress <= 70
        )

    def inspect_message(self):
        warnings = []
        if self.moisture < 30:
            warnings.append("흙이 바짝 말랐습니다")
        elif self.moisture > 72:
            warnings.append("물이 조금 고여 있습니다")
        if self.weeds > 45:
            warnings.append("잡초가 뿌리 가까이 번졌습니다")
        if self.pests > 38:
            warnings.append("잎 아래에서 작은 움직임이 보입니다")
        if self.health < 50:
            warnings.append("줄기가 힘을 잃고 있습니다")
        if self.drainage < 35:
            warnings.append("물길이 막혀 있습니다")

        if not warnings:
            return "밭은 안정적입니다. 지금은 기다려도 괜찮아 보입니다."
        return "살펴보니 " + ", ".join(warnings[:2]) + "."

    def build_notice(self):
        if self.growth >= self.growth_goal:
            return "수확할 수 있습니다. 건강이 너무 낮아지기 전에 거두세요."
        if self.health < 45:
            return "작물이 약해졌습니다. 흙 북돋기로 회복시키는 편이 좋습니다."
        if self.moisture < 30:
            return "흙이 말랐습니다. 물 주기를 우선 고민하세요."
        if self.moisture > 72:
            return "흙이 젖었습니다. 배수로를 정리하면 안정됩니다."
        if self.weeds > 50:
            return "잡초가 번졌습니다. 오래 두면 건강이 깎입니다."
        if self.pests > 42:
            return "해충 조짐이 큽니다. 잎 아래를 살펴야 합니다."
        if self.is_good_turn():
            return "밭이 안정적입니다. 기다리면 성장하기 좋은 흐름입니다."
        return "한 가지 문제가 커지기 전에 균형을 맞추세요."

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
        risk = max(self.weeds, self.pests, abs(self.moisture - 52), 100 - self.health)
        chance = 0.16 + min(0.2, risk / 350)
        if random.random() >= chance:
            return

        if self.weeds > self.pests and self.weeds > 35:
            mg = "stage1"
            text = "[돌발 상황]\n\n밭에 씨앗과 잡동사니가 뒤섞였습니다.\n필요한 것만 골라 밭을 다시 정리하세요."
        elif self.moisture < 35 or action == "물 주기":
            mg = "stage2"
            text = "[돌발 상황]\n\n흙이 갑자기 물을 빨아들입니다.\n타이밍을 맞춰 알맞은 만큼만 물을 주세요."
        else:
            mg = "stage3"
            text = "[돌발 상황]\n\n잎 아래에서 해충이 한꺼번에 튀어나왔습니다.\n빠르게 눌러 작물을 지켜내세요."

        game_state.transition_text = text
        game_state.current_scene = "transition"
        game_state.is_clear_transition = False
        game_state.transition_next = mg
        game_state.return_scene = "farm"

    def update(self, dt):
        if self.health <= 0:
            self.health = 25
            self.stress = 45
            game_state.understanding = max(0, game_state.understanding - 8)
            self.message = "당근이 크게 시들었습니다. 다시 흙을 다독이며 회복시켜야 합니다."
            self.rebuild_buttons()

    def draw_status_meter(self, screen, label, value, x, y, color):
        font = get_font(18)
        label_surf = font.render(label, True, BLACK)
        screen.blit(label_surf, (x, y - 2))
        bar = pygame.Rect(x + 62, y, 175, 16)
        pygame.draw.rect(screen, (70, 55, 40), bar)
        fill = pygame.Rect(bar.x + 2, bar.y + 2, int((bar.w - 4) * value / 100), bar.h - 4)
        pygame.draw.rect(screen, color, fill)
        pygame.draw.rect(screen, BLACK, bar, 2)

    def draw_field_summary(self, screen):
        panel = pygame.Rect(430, 82, 320, 92)
        draw_wood_panel(screen, panel)
        status_font = get_font(18)
        title_font = get_font(20)
        title = title_font.render("밭 상태", True, TEXT_BROWN)
        screen.blit(title, (455, 98))

        growth_text = status_font.render(f"성장 {self.growth}/{self.growth_goal}", True, TEXT_BROWN)
        insight_text = status_font.render(f"이해도 {game_state.understanding}", True, TEXT_BROWN)
        health_text = status_font.render(f"건강 {self.grade_text(self.health)}", True, TEXT_BROWN)
        screen.blit(growth_text, (455, 126))
        screen.blit(insight_text, (585, 126))
        screen.blit(health_text, (455, 150))

        if self.growth >= self.growth_goal:
            ready = status_font.render("수확 가능", True, (170, 70, 20))
            screen.blit(ready, (620, 150))

    def draw_meters(self, screen):
        panel = pygame.Rect(430, 182, 320, 108)
        draw_wood_panel(screen, panel)
        self.draw_status_meter(screen, "수분", self.moisture, 452, 204, (80, 170, 240))
        self.draw_status_meter(screen, "건강", self.health, 452, 228, (90, 185, 95))
        self.draw_status_meter(screen, "잡초", self.weeds, 452, 252, (80, 140, 55))
        self.draw_status_meter(screen, "해충", self.pests, 452, 276, (210, 110, 60))

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)

        plot_rect = pygame.Rect(50, 145, 350, 305)
        draw_wood_panel(screen, plot_rect)
        inner_plot = plot_rect.inflate(-20, -20)
        dirt_color = DIRT_WET if self.moisture > 68 else DIRT_COLOR if self.moisture > 28 else DIRT_DARK
        pygame.draw.rect(screen, dirt_color, inner_plot)
        pygame.draw.rect(screen, DIRT_DARK, inner_plot, 4)

        growth_stage = max(0, min(self.growth, self.growth_goal))
        if growth_stage > 0:
            for i in range(5):
                x = 80 + i * 60
                y = 260
                if growth_stage < 4:
                    screen.blit(sprites["seed"], (x, y))
                elif growth_stage < 8:
                    screen.blit(sprites["sprout1"], (x, y - 10))
                elif growth_stage < 12:
                    screen.blit(sprites["sprout2"], (x - 5, y - 20))
                elif growth_stage < 16:
                    screen.blit(sprites["sprout3"], (x - 5, y - 30))
                elif growth_stage < self.growth_goal:
                    screen.blit(sprites["sprout4"], (x - 5, y - 35))
                else:
                    screen.blit(sprites["carrot"], (x - 5, y - 60))

        if self.weeds > 35:
            for i in range(3):
                screen.blit(sprites["weed"], (95 + i * 95, 345))
        if self.pests > 35:
            for i in range(2):
                screen.blit(sprites["bug"], (160 + i * 105, 205))

        title_font = get_font(24)
        title = f"{self.day}일째: 꿈속 당근밭"
        title_surf = title_font.render(title, True, TEXT_BROWN)
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
        action_title = get_font(20).render("오늘 할 일", True, TEXT_BROWN)
        screen.blit(action_title, (450, 306))

        for btn in self.buttons:
            btn.draw(screen)

        draw_top_bar(screen, show_stats=False)
        draw_bottom_bar(screen, "농장 일지", f"{self.message} {self.notice}")
