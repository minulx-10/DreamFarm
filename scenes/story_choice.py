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
        self.qte_theme = None

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
        self.qte_theme = task_data.get("theme")

        count = task_data.get("count", 4)
        if self.qte_kind == "trail":
            # 왼쪽 밭에서 오른쪽 꽃밭까지, 순서대로 늘어선 잎 (지그재그)
            for i in range(count):
                tx = 180 + (i * (440 // max(1, count - 1)) if count > 1 else 220)
                ty = 300 + (34 if i % 2 else -34)
                self.qte_targets.append({"pos": (tx, ty), "done": False})
        elif self.qte_theme == "fence":
            # 울타리 틈은 한 줄로 늘어선 울타리 위에 뚫려 있어야 한다 — 가로 울타리 선을 따라 배치
            for i in range(count):
                tx = 190 + int((i + 0.5) * (420 / count))
                ty = 302 + random.randint(-5, 5)
                self.qte_targets.append({"pos": (tx, ty), "done": False})
        elif self.qte_kind == "rub":
            # 녹슨 자국은 실제 호미 '날' 위에 있어야 한다 — 좁고 길쭉한 곡선날 안쪽 지점들에 배치
            blade_spots = [(402, 326), (392, 332), (384, 338), (376, 344), (372, 352), (396, 336)]
            for i in range(count):
                self.qte_targets.append({"pos": blade_spots[i % len(blade_spots)], "done": False})
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
                # 갤러리에서 '다시 하기'로 들어온 감상이면 갤러리로 복귀 (실제 진행에 영향 X)
                if getattr(game_state, "event_replay", False):
                    game_state.event_replay = False
                    game_state.current_scene = "gallery"
                else:
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
                self._draw_stone(screen, cx, cy)

        elif self.qte_kind == "trail":
            # 잎들을 잇는 점선 경로
            pts = [t["pos"] for t in self.qte_targets]
            for i in range(len(pts) - 1):
                pygame.draw.line(screen, (150, 170, 120), pts[i], pts[i + 1], 2)
            for i, t in enumerate(self.qte_targets):
                cx, cy = t["pos"]
                is_next = (t is active)
                last = (i == len(self.qte_targets) - 1)
                if last:
                    # 목적지는 잎이 아니라 꽃밭의 꽃 한 송이로 그린다
                    self._draw_flower(screen, cx, cy, t["done"], is_next, pulse)
                    continue
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
                num = get_font(13).render(str(i + 1), True, (30, 60, 35))
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
            if self.qte_theme == "fence":
                self._draw_fence_qte(screen, active, pulse)
            else:
                # 물길/이랑 등 — 막아야 할 틈/구멍 (테마에 따라 색만 달리)
                hole_c = (44, 78, 104) if self.qte_theme == "water" else (48, 34, 24)
                for t in self.qte_targets:
                    cx, cy = t["pos"]
                    if t["done"]:
                        fill = (110, 150, 180) if self.qte_theme == "water" else (120, 95, 70)
                        pygame.draw.circle(screen, fill, (cx, cy), 16)
                        continue
                    pygame.draw.circle(screen, hole_c, (cx, cy), 17)
                    if t is active:
                        pygame.draw.circle(screen, (210, 180, 90), (cx, cy), int(20 + 4 * pulse), 2)
                        if self.qte_progress > 0:
                            ang = -math.pi / 2
                            end = ang + self.qte_progress * 2 * math.pi
                            rect = pygame.Rect(cx - 15, cy - 15, 30, 30)
                            pygame.draw.arc(screen, (95, 200, 120), rect, ang, end, 5)
            hint = t_font.render("표적 위에서 마우스를 꾹 누르세요", True, TEXT_MUTED)
            screen.blit(hint, (400 - hint.get_width() // 2, 430))

        elif self.qte_kind == "rub":
            self._draw_hoe(screen)   # 실제 낡은 호미(자루+날)
            for t in self.qte_targets:
                cx, cy = t["pos"]
                if t["done"]:
                    # 닦인 자리 — 반짝이는 금속
                    pygame.draw.circle(screen, (176, 182, 190), (cx, cy), 11)
                    pygame.draw.circle(screen, (232, 238, 244), (cx - 3, cy - 3), 4)
                    continue
                # 녹슨 자국 (울퉁불퉁한 붉은 녹)
                import random as _r
                rng = _r.Random(cx * 17 + cy)
                for _ in range(5):
                    ox, oy = rng.randint(-8, 8), rng.randint(-7, 7)
                    rr = rng.randint(4, 8)
                    col = rng.choice([(150, 92, 44), (128, 72, 34), (172, 108, 52)])
                    pygame.draw.circle(screen, col, (cx + ox, cy + oy), rr)
                if t is active:
                    pygame.draw.circle(screen, (210, 150, 90), (cx, cy), int(16 + 4 * pulse), 2)
                    if self.qte_progress > 0:
                        w = int(24 * self.qte_progress)
                        pygame.draw.rect(screen, (180, 186, 192), (cx - 12, cy + 16, w, 4), border_radius=2)
            hint = t_font.render("호미의 녹슨 자리에서 마우스를 좌우로 문지르세요", True, TEXT_MUTED)
            screen.blit(hint, (400 - hint.get_width() // 2, 418))

    def _draw_hoe(self, screen):
        """아버지의 낡은 호미 — 한국식 손호미. 짧은 나무 자루 끝에 쇠목이 ㄱ자로 꺾이고,
        꺾인 뒤 좁고 길쭉한 쇠날이 아래쪽으로 휘어지며 끝이 뾰족하다(삽처럼 넓적하지 않다)."""
        wood_d, wood, wood_l = (92, 62, 36), (140, 98, 58), (176, 132, 82)
        iron_d, iron, iron_l = (78, 82, 90), (134, 140, 148), (196, 202, 210)

        # 1) 나무 자루 — 오른쪽 위에서 왼쪽 아래로 비스듬히 (약간 더 세운다)
        grip_top, ferrule = (470, 226), (426, 296)
        pygame.draw.line(screen, wood_d, grip_top, ferrule, 14)
        pygame.draw.line(screen, wood, grip_top, ferrule, 10)
        pygame.draw.line(screen, wood_l, (grip_top[0] - 2, grip_top[1] + 2),
                         (ferrule[0] - 2, ferrule[1] + 2), 3)
        # 손잡이 끝 둥근 혹
        pygame.draw.circle(screen, wood, grip_top, 9)
        pygame.draw.circle(screen, wood_d, grip_top, 9, 2)

        # 2) 쇠 물미(자루와 쇠를 잇는 테)
        pygame.draw.circle(screen, iron, ferrule, 8)
        pygame.draw.circle(screen, iron_d, ferrule, 8, 2)

        # 3) 쇠목: 물미에서 짧게 아래로 → ㄱ자로 확실히 꺾여서 왼쪽으로 진행
        neck_end = (422, 318)   # 아래로 짧게 내려감
        pygame.draw.line(screen, iron_d, ferrule, neck_end, 8)
        pygame.draw.line(screen, iron, ferrule, neck_end, 5)

        # 4) ㄱ자 꺾이는 지점 — 무릎 부분
        knee = (418, 322)
        pygame.draw.circle(screen, iron_l, knee, 3)   # 꺾이는 무릎 반짝임

        # 5) 쇠날: 쇠목에서 시작하여 왼쪽 아래로 곡선을 그리며 부드럽게 휘어져 뾰족해지는 호미 날 (삽 느낌 완전 배제)
        blade_pts = [
            (414, 324),    # 쇠목 부착부 (우상단)
            (394, 332),    # 등날 외곽 곡선 1
            (378, 344),    # 등날 외곽 곡선 2
            (370, 366),    # 뾰족한 날 끝 (좌하단)
            (382, 358),    # 안쪽 날선 곡선 1
            (394, 348),    # 안쪽 날선 곡선 2
            (404, 338),    # 안쪽 날선 곡선 3
        ]
        # 그림자
        pygame.draw.polygon(screen, iron_d, [(px, py + 3) for px, py in blade_pts])
        # 본체
        pygame.draw.polygon(screen, iron, blade_pts)
        pygame.draw.polygon(screen, iron_d, blade_pts, 2)

        # 날 등 능선 및 날선 반짝임 표현
        pygame.draw.line(screen, iron_l, (408, 324), (374, 356), 2)
        pygame.draw.line(screen, iron_l, (396, 322), (372, 344), 1)
        # 날 끝의 살짝 밝은 쐐기 (뾰족함 강조)
        pygame.draw.polygon(screen, iron_l, [(374, 360), (370, 366), (376, 360)])

    def _draw_stone(self, screen, cx, cy):
        """주워 담을 돌 — 종류를 다양하게. (이스터에그: 박서현이면 모아이 석상)"""
        if game_state.player_name == "박서현":
            g0, g1, g2 = (120, 116, 110), (92, 88, 82), (150, 146, 140)
            head = [(cx - 10, cy - 16), (cx + 10, cy - 16), (cx + 12, cy + 6), (cx + 8, cy + 18),
                    (cx - 8, cy + 18), (cx - 12, cy + 6)]
            pygame.draw.polygon(screen, (54, 50, 46), [(x, y + 3) for x, y in head])  # 그림자
            pygame.draw.polygon(screen, g0, head)
            pygame.draw.polygon(screen, g1, head, 2)
            pygame.draw.rect(screen, g1, (cx - 11, cy - 10, 22, 4))          # 눈두덩(무거운 이마)
            pygame.draw.rect(screen, (40, 38, 34), (cx - 8, cy - 6, 5, 4))   # 왼눈
            pygame.draw.rect(screen, (40, 38, 34), (cx + 3, cy - 6, 5, 4))   # 오눈
            pygame.draw.polygon(screen, g2, [(cx - 2, cy - 4), (cx + 2, cy - 4), (cx + 1, cy + 8), (cx - 1, cy + 8)])  # 긴 코
            pygame.draw.rect(screen, (60, 56, 52), (cx - 5, cy + 11, 10, 3))  # 입
            return
        import random as _r
        rng = _r.Random(cx * 31 + cy * 7)
        base, dark, light = rng.choice([
            ((150, 146, 138), (108, 104, 96), (198, 194, 186)),   # 회색 화강암
            ((152, 122, 92), (112, 88, 64), (198, 172, 138)),     # 갈색 사암
            ((96, 100, 108), (62, 66, 74), (150, 156, 164)),      # 짙은 현무암
            ((170, 152, 130), (128, 112, 94), (212, 198, 180)),   # 밝은 석회암
        ])
        r = rng.randint(11, 17)
        n = 7
        pts = []
        for i in range(n):
            ang = i * (2 * math.pi / n) + rng.uniform(-0.2, 0.2)
            rr = r * rng.uniform(0.76, 1.14)
            pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang) * 0.88))
        pygame.draw.polygon(screen, (52, 46, 42), [(x, y + 4) for x, y in pts])   # 그림자
        pygame.draw.polygon(screen, base, pts)
        pygame.draw.polygon(screen, dark, pts, 2)
        pygame.draw.circle(screen, light, (int(cx - r // 3), int(cy - r // 3)), max(3, r // 4))
        for _ in range(rng.randint(1, 3)):   # 결·얼룩
            sx = cx + rng.randint(-r // 2, r // 2)
            sy = cy + rng.randint(-r // 2, r // 2)
            pygame.draw.circle(screen, dark, (sx, sy), 1)

    def _draw_flower(self, screen, cx, cy, done, active, pulse):
        """길 잃은 벌의 목적지 — 꽃밭의 꽃 한 송이."""
        if active:
            pygame.draw.circle(screen, (250, 180, 205), (cx, cy), int(23 + 6 * pulse), 2)
        # 잎줄기
        pygame.draw.line(screen, (70, 130, 80), (cx, cy + 6), (cx, cy + 18), 3)
        petal = (222, 150, 182) if done else (240, 162, 194)
        petal_hi = (252, 200, 220)
        for k in range(6):
            ang = k * math.pi / 3
            px = cx + int(math.cos(ang) * 11)
            py = cy + int(math.sin(ang) * 11)
            pygame.draw.circle(screen, petal, (px, py), 7)
        for k in range(6):
            ang = k * math.pi / 3
            px = cx + int(math.cos(ang) * 11)
            py = cy + int(math.sin(ang) * 11)
            pygame.draw.circle(screen, petal_hi, (px - 2, py - 2), 3)
        pygame.draw.circle(screen, (246, 206, 92), (cx, cy), 6)
        pygame.draw.circle(screen, (208, 158, 58), (cx, cy), 6, 1)

    def _draw_fence_qte(self, screen, active, pulse):
        """새벽의 고라니 — 실제 울타리가 한 줄로 서 있고, 부러진 틈이 표적이 된다."""
        span_l, span_r = 150, 650
        y_top, y_bot = 292, 314
        rail_c, rail_d = (156, 114, 70), (112, 80, 48)
        post_c, post_d = (128, 90, 54), (88, 60, 36)

        undone = [t for t in self.qte_targets if not t["done"]]
        gaps = [(t["pos"][0] - 26, t["pos"][0] + 26) for t in undone]

        def in_gap(x):
            return any(a <= x <= b for a, b in gaps)

        # 활성 틈 뒤에서 노리는 고라니
        if active is not None and not active["done"]:
            dx, dy = active["pos"]
            self._draw_deer(screen, dx, y_top - 30)

        # 가로 살(rail) — 틈 구간은 건너뛰고 이어 그린다
        for yy in (y_top, y_bot):
            x = span_l
            while x < span_r:
                if in_gap(x):
                    x += 3
                    continue
                seg_end = x
                while seg_end < span_r and not in_gap(seg_end):
                    seg_end += 3
                pygame.draw.rect(screen, rail_c, (x, yy, seg_end - x, 8))
                pygame.draw.rect(screen, rail_d, (x, yy + 6, seg_end - x, 2))
                x = seg_end

        # 기둥(post)
        for px in range(span_l, span_r + 1, 100):
            pygame.draw.rect(screen, post_c, (px - 6, y_top - 18, 12, 62))
            pygame.draw.rect(screen, post_d, (px + 2, y_top - 18, 4, 62))
            pygame.draw.polygon(screen, post_c, [(px - 6, y_top - 18), (px, y_top - 26), (px + 6, y_top - 18)])

        # 표적별: 부러진 틈 또는 메운 자리
        for t in self.qte_targets:
            cx, cy = t["pos"]
            if t["done"]:
                self._draw_fence_patch(screen, cx, y_top, y_bot, 1.0)
                continue
            # 부러진 살 끝 (뾰족하게)
            for yy in (y_top, y_bot):
                pygame.draw.polygon(screen, rail_d, [(cx - 26, yy), (cx - 19, yy + 4), (cx - 26, yy + 8)])
                pygame.draw.polygon(screen, rail_d, [(cx + 26, yy), (cx + 19, yy + 4), (cx + 26, yy + 8)])
            if t is active:
                pygame.draw.circle(screen, (210, 180, 90), (cx, cy), int(23 + 4 * pulse), 2)
                if self.qte_progress > 0:
                    self._draw_fence_patch(screen, cx, y_top, y_bot, self.qte_progress)

    def _draw_fence_patch(self, screen, cx, y_top, y_bot, frac):
        """부러진 틈을 나뭇가지로 가로질러 메운다 (frac 만큼 자라난다)."""
        br, brd, leaf = (120, 82, 48), (86, 56, 32), (96, 152, 72)
        span = 24
        x0, y0 = cx - span, y_top - 4
        x1, y1 = cx + span, y_bot + 6
        ex, ey = x0 + (x1 - x0) * frac, y0 + (y1 - y0) * frac
        pygame.draw.line(screen, brd, (x0, y0), (ex, ey), 6)
        pygame.draw.line(screen, br, (x0, y0), (ex, ey), 4)
        if frac >= 0.999:
            pygame.draw.line(screen, brd, (x1, y0), (x0, y1), 5)
            pygame.draw.line(screen, br, (x1, y0), (x0, y1), 3)
            pygame.draw.circle(screen, leaf, (cx - 5, y_top - 1), 4)
            pygame.draw.circle(screen, leaf, (cx + 7, y_bot + 1), 3)

    def _draw_deer(self, screen, cx, cy):
        """울타리 너머로 고개를 들이민 고라니. (이스터에그: 김민욱이면 돼지)"""
        if game_state.player_name == "김민욱":
            pink, pdark, pnose = (240, 170, 180), (210, 130, 145), (225, 150, 160)
            pygame.draw.ellipse(screen, pink, (cx - 13, cy - 6, 9, 11))   # 왼귀
            pygame.draw.ellipse(screen, pink, (cx + 6, cy - 6, 9, 11))    # 오른귀
            pygame.draw.ellipse(screen, pink, (cx - 15, cy, 30, 28))      # 얼굴
            pygame.draw.ellipse(screen, pdark, (cx - 9, cy + 12, 18, 13)) # 코(주둥이)
            pygame.draw.circle(screen, pnose, (cx - 4, cy + 18), 2)
            pygame.draw.circle(screen, pnose, (cx + 4, cy + 18), 2)
            pygame.draw.circle(screen, (30, 24, 20), (cx - 6, cy + 6), 2)
            pygame.draw.circle(screen, (30, 24, 20), (cx + 6, cy + 6), 2)
            return
        body, dark, nose = (126, 100, 74), (94, 72, 52), (58, 46, 38)
        pygame.draw.ellipse(screen, body, (cx - 15, cy - 4, 8, 15))   # 왼귀
        pygame.draw.ellipse(screen, body, (cx + 7, cy - 4, 8, 15))    # 오른귀
        pygame.draw.ellipse(screen, body, (cx - 13, cy, 26, 30))      # 얼굴
        pygame.draw.ellipse(screen, dark, (cx - 8, cy + 16, 16, 14))  # 주둥이
        pygame.draw.circle(screen, nose, (cx, cy + 26), 3)
        pygame.draw.circle(screen, (28, 22, 18), (cx - 6, cy + 10), 2)
        pygame.draw.circle(screen, (28, 22, 18), (cx + 6, cy + 10), 2)

    def _draw_btn(self, screen, rect, label, hovered):
        draw_button(screen, rect, label, self.font_small, hovered=hovered)

    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")

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
