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
        self.qte_timer = 30.0
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
        self.qte_timer = 30.0
        self.qte_choice = choice
        self.qte_targets = []
        
        # 30초 동안 클릭할 타겟 랜덤 배치 (텍스트 영역 하단 및 선택창 안쪽 영역: Y 150~350)
        count = task_data.get("count", 4)
        for _ in range(count):
            tx = random.randint(160, 640)
            ty = random.randint(180, 350)
            self.qte_targets.append({
                "rect": pygame.Rect(tx - 20, ty - 20, 40, 40),
                "clicked": False
            })

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
            # QTE 상태의 입력 처리
            if self.qte_active:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for t in self.qte_targets:
                        if not t["clicked"] and t["rect"].collidepoint(event.pos):
                            t["clicked"] = True
                            audio.play("click")
                            break
                    if all(t["clicked"] for t in self.qte_targets):
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

    def _draw_btn(self, screen, rect, label, hovered):
        draw_button(screen, rect, label, self.font_small, hovered=hovered)

    def draw(self, screen):
        draw_story_backdrop(screen, "night")

        panel = pygame.Rect(50, 50, 700, 500)
        draw_light_panel(screen, panel)

        title_surf = self.font_title.render(self.title, True, TEXT_DARK)
        screen.blit(title_surf, (400 - title_surf.get_width() // 2, 80))
        pygame.draw.rect(screen, WOOD_LIGHT, (100, 118, 600, 3))

        # 만약 QTE 진행 중이라면 작업 지시와 빨간 클릭 타겟들을 그린다
        if self.qte_active:
            # 상단 프롬프트
            prompt_surf = self.font.render(self.qte_task["prompt"], True, (200, 50, 50))
            screen.blit(prompt_surf, (400 - prompt_surf.get_width() // 2, 140))
            
            # 남은 개수 표기
            remain = sum(1 for t in self.qte_targets if not t["clicked"])
            remain_surf = self.font_small.render(f"남은 표적: {remain}개", True, TEXT_DARK)
            screen.blit(remain_surf, (400 - remain_surf.get_width() // 2, 172))
            
            # 타이머 바
            timer_w = int(500 * (self.qte_timer / 30.0))
            pygame.draw.rect(screen, (80, 70, 60), (150, 390, 500, 16), border_radius=4)
            pygame.draw.rect(screen, (220, 60, 60), (150, 390, timer_w, 16), border_radius=4)
            
            t_font = get_font(13)
            time_text = t_font.render(f"제한시간: {self.qte_timer:.1f}초", True, WHITE)
            screen.blit(time_text, (400 - time_text.get_width() // 2, 392))
            
            # 과제 타겟들 그리기
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.008))
            for t in self.qte_targets:
                if not t["clicked"]:
                    r = t["rect"]
                    # 파동 효과 테두리
                    pygame.draw.circle(screen, (240, 60, 60, 90), r.center, int(18 + 5 * pulse))
                    pygame.draw.circle(screen, (255, 160, 80), r.center, int(15), 3)
                    pygame.draw.circle(screen, (255, 255, 255), r.center, 5)
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
