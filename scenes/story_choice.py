import pygame
import random
import math
from core.game_state import game_state
from core.assets import TEXT_DARK, TEXT_MUTED, WOOD_LIGHT, get_font, WHITE, GOLD
from core.ui import draw_button, draw_light_panel, draw_story_backdrop, wrap_text, mix_color, draw_panel
from core import audio


class StoryChoiceScene:
    """선택형 이벤트 화면. A/B 선택을 수행하고, 'task'가 포함된 경우 30초 QTE 미니게임이 열림."""

    def __init__(self):
        self.font_title = get_font(24)
        self.font = get_font(20)
        self.font_small = get_font(18)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.04
        self.finished = False
        self.choice_made = False
        self.result_text = ""
        self.result_timer = 0

        # QTE 상태 변수
        self.qte_active = False
        self.qte_task = None
        self.qte_kind = "tap"
        self.qte_timer = 30.0
        self.qte_progress = 0.0
        self.qte_targets = []
        self.qte_choice = None

        data = game_state.choice_data or {}
        
        from core.crops import swap_crop_word, current_crop
        crop_word = current_crop().get("food", "당근")
        
        self.title = swap_crop_word(data.get("title", ""), crop_word)
        self.text = swap_crop_word(data.get("text", ""), crop_word)
        
        raw_a_label, a_effects = data.get("choice_a", ("", {}))
        raw_b_label, b_effects = data.get("choice_b", ("", {}))
        
        self.choice_a = (swap_crop_word(raw_a_label, crop_word), self._cropify_effects(a_effects, crop_word))
        self.choice_b = (swap_crop_word(raw_b_label, crop_word), self._cropify_effects(b_effects, crop_word))
        
        self.text_to_print = self._prepare(self.text)

        self.btn_a = pygame.Rect(80, 390, 290, 65)
        self.btn_b = pygame.Rect(430, 390, 290, 65)
        self.hover_a = False
        self.hover_b = False

    def _cropify_effects(self, effects, crop_word):
        from core.crops import swap_crop_word
        new_effects = {}
        for k, v in effects.items():
            if k in ["result_text", "impact_text"]:
                new_effects[k] = swap_crop_word(v, crop_word)
            elif k == "task":
                new_task = {}
                for tk, tv in v.items():
                    if tk in ["prompt", "fail_text"]:
                        new_task[tk] = swap_crop_word(tv, crop_word)
                    else:
                        new_task[tk] = tv
                new_effects[k] = new_task
            else:
                new_effects[k] = v
        return new_effects

    def _prepare(self, text):
        lines = []
        for p in text.split("\n"):
            if not p:
                lines.append("")
            else:
                lines.extend(wrap_text(p, self.font, 560))
        return "\n".join(lines)

    def _start_qte(self, choice, task_data):
        self.qte_active = True
        self.qte_task = task_data
        self.qte_kind = task_data.get("kind", "tap")
        self.qte_timer = task_data.get("time_limit", 30.0)
        self.qte_choice = choice
        self.qte_progress = 0.0          # hold/rub 진행도 (0~1, 현재 표적 기준)
        self.qte_targets = []

        count = task_data.get("count", 4)
        if self.qte_kind == "trail":
            # 왼쪽 밭에서 오른쪽 꽃밭까지, 순서대로 늘어선 잎 (지그재그)
            for i in range(count):
                tx = 180 + (i * (440 // max(1, count - 1)) if count > 1 else 220)
                ty = 300 + (34 if i % 2 else -34)
                self.qte_targets.append({"pos": (tx, ty), "done": False})
        else:
            # 서로 겹치지 않게 랜덤 배치 (tap/hold/rub 공용)
            placed = []
            for _ in range(count):
                tx, ty = 400, 270
                for _try in range(40):
                    tx = random.randint(190, 610)
                    ty = random.randint(190, 355)
                    if all((tx - px) ** 2 + (ty - py) ** 2 > 78 * 78 for px, py in placed):
                        break
                placed.append((tx, ty))
                self.qte_targets.append({"pos": (tx, ty), "done": False})

    def _active_target(self):
        """순서가 있는 과제(hold/rub/trail)에서 지금 다뤄야 할 표적."""
        for t in self.qte_targets:
            if not t["done"]:
                return t
        return None

    @staticmethod
    def _near(pos, center, r=34):
        return (pos[0] - center[0]) ** 2 + (pos[1] - center[1]) ** 2 <= r * r

    def _apply(self, choice):
        label, effects = choice
        
        # 만약 'task'가 설정되어 있다면 바로 적용하지 않고 QTE 실행
        if "task" in effects:
            audio.play("water")
            self._start_qte(choice, effects["task"])
            return

        # #11 Track empathy if this is the compassionate choice (choice_b)
        if choice == self.choice_b:
            game_state.empathy_choices += 1

        # Record story in meta save data
        from core import save_system
        save_system.record_story(self.title)

        for key, val in effects.items():
            if key == "understanding":
                game_state.understanding += val
            elif key == "result_text":
                self.result_text = val
            elif key == "impact_text":
                game_state.choice_impacts.append({
                    "title": self.title,
                    "choice": label,
                    "impact": val,
                })
        self.choice_made = True
        self.result_timer = 3.5

    def _resolve_qte(self, success):
        self.qte_active = False
        label, effects = self.qte_choice
        
        # #11 Track empathy if this is the compassionate choice (choice_b)
        if self.qte_choice == self.choice_b:
            game_state.empathy_choices += 1

        # Record story in meta save data
        from core import save_system
        save_system.record_story(self.title)

        if success:
            audio.play("success")
            for key, val in effects.items():
                if key == "understanding":
                    game_state.understanding += val
                elif key == "result_text":
                    self.result_text = val
                elif key == "impact_text":
                    game_state.choice_impacts.append({
                        "title": self.title,
                        "choice": label,
                        "impact": val,
                    })
        else:
            audio.play("break")
            fail_text = self.qte_task.get("fail_text", "작업이 원활히 끝나지 못했습니다.")
            self.result_text = f"실패: {fail_text}"
            
            # 실패 시 이해도 획득 절반 차감
            und = effects.get("understanding", 6) // 2
            game_state.understanding += und
            
            game_state.choice_impacts.append({
                "title": self.title,
                "choice": label,
                "impact": effects.get("impact_text", "") + f" ({fail_text})",
            })
            
        self.choice_made = True
        self.result_timer = 4.0

    def handle_events(self, events):
        for event in events:
            # QTE 상태의 입력 처리 (종류별)
            if self.qte_active:
                if self.qte_kind == "tap":
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        for t in self.qte_targets:
                            if not t["done"] and self._near(event.pos, t["pos"]):
                                t["done"] = True
                                audio.play("click")
                                break
                elif self.qte_kind == "trail":
                    # 반드시 다음 순서의 잎을 눌러야 진행 (틀린 클릭은 무시)
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        tgt = self._active_target()
                        if tgt and self._near(event.pos, tgt["pos"], r=30):
                            tgt["done"] = True
                            audio.play("pop")
                elif self.qte_kind == "rub":
                    # 표적 위에서 마우스를 비비면(움직이면) 녹이 벗겨진다
                    if event.type == pygame.MOUSEMOTION:
                        tgt = self._active_target()
                        if tgt and self._near(event.pos, tgt["pos"], r=32):
                            moved = abs(event.rel[0]) + abs(event.rel[1])
                            self.qte_progress += moved / 240.0
                            if self.qte_progress >= 1.0:
                                tgt["done"] = True
                                self.qte_progress = 0.0
                                audio.play("soil")
                # hold는 update()에서 마우스 눌림 상태로 처리
                if self.qte_targets and all(t["done"] for t in self.qte_targets):
                    self._resolve_qte(success=True)
                continue

            if event.type == pygame.MOUSEMOTION and self.finished and not self.choice_made:
                self.hover_a = self.btn_a.collidepoint(event.pos)
                self.hover_b = self.btn_b.collidepoint(event.pos)

            if not self.finished:
                if event.type == pygame.MOUSEBUTTONDOWN or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
                ):
                    self.printed_text = self.text_to_print
                    self.char_idx = len(self.text_to_print)
                    self.finished = True
            elif not self.choice_made:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_a.collidepoint(event.pos):
                        audio.play("click")
                        self._apply(self.choice_a)
                    elif self.btn_b.collidepoint(event.pos):
                        audio.play("click")
                        self._apply(self.choice_b)

    def update(self, dt):
        if self.qte_active:
            self.qte_timer -= dt
            if self.qte_timer <= 0:
                self._resolve_qte(success=False)
                return
            # hold: 표적 위에서 마우스 왼쪽 버튼을 꾹 누르고 있으면 게이지가 찬다
            if self.qte_kind == "hold":
                tgt = self._active_target()
                if tgt:
                    pressed = pygame.mouse.get_pressed()[0]
                    if pressed and self._near(pygame.mouse.get_pos(), tgt["pos"], r=32):
                        self.qte_progress += dt / 0.85
                        if self.qte_progress >= 1.0:
                            tgt["done"] = True
                            self.qte_progress = 0.0
                            audio.play("soil")
                    else:
                        # 떼거나 벗어나면 서서히 풀린다 (끝까지 눌러야 함)
                        self.qte_progress = max(0.0, self.qte_progress - dt * 0.6)
                if self.qte_targets and all(t["done"] for t in self.qte_targets):
                    self._resolve_qte(success=True)
            return

        if self.choice_made:
            self.result_timer -= dt
            if self.result_timer <= 0:
                game_state.choice_data = None
                game_state.current_scene = "farm"
            return

        if self.finished:
            return

        self.char_timer += dt
        if self.char_timer >= self.char_delay:
            self.char_timer = 0
            if self.char_idx < len(self.text_to_print):
                self.printed_text += self.text_to_print[self.char_idx]
                self.char_idx += 1
                audio.type_tick(self.text_to_print[self.char_idx - 1])
            else:
                self.finished = True

    def _draw_qte(self, screen):
        # 상단 프롬프트
        prompt_surf = self.font.render(self.qte_task["prompt"], True, (170, 60, 40))
        screen.blit(prompt_surf, (400 - prompt_surf.get_width() // 2, 138))

        remain = sum(1 for t in self.qte_targets if not t["done"])
        remain_surf = self.font_small.render(f"남은 곳: {remain}개", True, TEXT_DARK)
        screen.blit(remain_surf, (400 - remain_surf.get_width() // 2, 170))

        # 타이머 바
        total = self.qte_task.get("time_limit", 30.0)
        timer_w = int(500 * max(0.0, self.qte_timer / total))
        pygame.draw.rect(screen, (80, 70, 60), (150, 470, 500, 16), border_radius=4)
        bar_col = (220, 60, 60) if self.qte_timer < total * 0.35 else (90, 160, 110)
        pygame.draw.rect(screen, bar_col, (150, 470, timer_w, 16), border_radius=4)
        t_font = get_font(13)
        time_text = t_font.render(f"제한시간: {self.qte_timer:.1f}초", True, WHITE)
        screen.blit(time_text, (400 - time_text.get_width() // 2, 472))

        pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
        active = self._active_target()

        if self.qte_kind == "tap":
            for t in self.qte_targets:
                if t["done"]:
                    continue
                cx, cy = t["pos"]
                # 주워 담을 돌멩이
                pygame.draw.circle(screen, (60, 50, 44, 90), (cx, cy + 4), 16)
                pygame.draw.circle(screen, (150, 146, 138), (cx, cy), 15)
                pygame.draw.circle(screen, (110, 104, 96), (cx, cy), 15, 2)
                pygame.draw.circle(screen, (196, 192, 184), (cx - 4, cy - 4), 5)

        elif self.qte_kind == "trail":
            # 잎들을 잇는 점선 경로
            pts = [t["pos"] for t in self.qte_targets]
            for i in range(len(pts) - 1):
                pygame.draw.line(screen, (150, 170, 120), pts[i], pts[i + 1], 2)
            for i, t in enumerate(self.qte_targets):
                cx, cy = t["pos"]
                is_next = (t is active)
                last = (i == len(self.qte_targets) - 1)
                if t["done"]:
                    col = (120, 150, 100)
                elif is_next:
                    col = (90, 200, 110)
                    pygame.draw.circle(screen, (90, 200, 110), (cx, cy), int(20 + 6 * pulse), 2)
                else:
                    col = (70, 130, 80)
                # 잎 모양
                pygame.draw.ellipse(screen, col, (cx - 13, cy - 9, 26, 18))
                pygame.draw.line(screen, (40, 90, 50), (cx - 10, cy), (cx + 10, cy), 1)
                num = get_font(13).render(str(i + 1) if not last else "꽃", True, (30, 60, 35))
                screen.blit(num, (cx - num.get_width() // 2, cy - num.get_height() // 2))
            # 벌: 다음 잎(또는 마지막 완료 잎) 위에 앉아 있다
            bee_t = active or self.qte_targets[-1]
            bx, by = bee_t["pos"]
            by -= 18
            pygame.draw.ellipse(screen, (240, 200, 60), (bx - 6, by - 4, 12, 8))
            pygame.draw.line(screen, (40, 30, 10), (bx - 2, by - 4), (bx - 2, by + 4), 1)
            pygame.draw.line(screen, (40, 30, 10), (bx + 2, by - 4), (bx + 2, by + 4), 1)
            pygame.draw.ellipse(screen, (220, 235, 255), (bx - 9, by - 7, 7, 5))
            pygame.draw.ellipse(screen, (220, 235, 255), (bx + 2, by - 7, 7, 5))

        elif self.qte_kind == "hold":
            for t in self.qte_targets:
                cx, cy = t["pos"]
                if t["done"]:
                    pygame.draw.circle(screen, (120, 150, 95), (cx, cy), 16)
                    continue
                # 막아야 할 틈/구멍
                pygame.draw.circle(screen, (48, 34, 24), (cx, cy), 17)
                if t is active:
                    # 누르는 동안 차는 게이지 링
                    pygame.draw.circle(screen, (210, 180, 90), (cx, cy), int(20 + 4 * pulse), 2)
                    if self.qte_progress > 0:
                        ang = -math.pi / 2
                        end = ang + self.qte_progress * 2 * math.pi
                        rect = pygame.Rect(cx - 15, cy - 15, 30, 30)
                        pygame.draw.arc(screen, (95, 200, 120), rect, ang, end, 5)
            hint = t_font.render("표적 위에서 마우스를 꾹 누르세요", True, TEXT_MUTED)
            screen.blit(hint, (400 - hint.get_width() // 2, 430))

        elif self.qte_kind == "rub":
            for t in self.qte_targets:
                cx, cy = t["pos"]
                if t["done"]:
                    pygame.draw.circle(screen, (170, 176, 182), (cx, cy), 15)   # 반짝이는 금속
                    pygame.draw.circle(screen, (230, 236, 240), (cx - 4, cy - 4), 4)
                    continue
                # 녹슨 자국
                pygame.draw.circle(screen, (150, 92, 44), (cx, cy), 16)
                pygame.draw.circle(screen, (120, 70, 34), (cx, cy), 16, 2)
                if t is active:
                    pygame.draw.circle(screen, (210, 150, 90), (cx, cy), int(20 + 4 * pulse), 2)
                    if self.qte_progress > 0:
                        w = int(28 * self.qte_progress)
                        pygame.draw.rect(screen, (180, 186, 192), (cx - 14, cy + 20, w, 4), border_radius=2)
            hint = t_font.render("표적 위에서 마우스를 좌우로 문지르세요", True, TEXT_MUTED)
            screen.blit(hint, (400 - hint.get_width() // 2, 430))

    def _draw_btn(self, screen, rect, label, hovered):
        draw_button(screen, rect, label, self.font_small, hovered=hovered)

    def draw(self, screen):
        draw_story_backdrop(screen, "night")

        panel = pygame.Rect(50, 50, 700, 500)
        draw_light_panel(screen, panel)

        title_surf = self.font_title.render(self.title, True, TEXT_DARK)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 80))
        pygame.draw.rect(screen, WOOD_LIGHT, (100, 118, 600, 3))

        # QTE 진행 중이면 종류별 미니게임을 그린다
        if self.qte_active:
            self._draw_qte(screen)
            return

        # 텍스트 출력
        y = 145
        for line in self.printed_text.split("\n"):
            surf = self.font.render(line, True, TEXT_DARK)
            screen.blit(surf, (100, y))
            y += 28

        if self.choice_made:
            r_surf = self.font.render(self.result_text, True, (140, 90, 20))
            screen.blit(r_surf, (400 - r_surf.get_width() // 2, 410))
        elif self.finished:
            self._draw_btn(screen, self.btn_a, "A. " + self.choice_a[0], self.hover_a)
            self._draw_btn(screen, self.btn_b, "B. " + self.choice_b[0], self.hover_b)
            prompt = self.font_small.render("선택하세요", True, TEXT_MUTED)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 480))
