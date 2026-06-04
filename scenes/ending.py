import os
import math
import pygame
from core.game_state import (
    append_josa, game_state, get_understanding_stage,
    get_attitude_ending, save_progress, JOURNAL_RETROSPECTIVES,
)
from core.assets import BLACK, WHITE, TEXT_DARK, TEXT_MUTED, get_font, sprites
from core.ui import draw_centered_lines, draw_light_panel, draw_story_backdrop, wrap_text


class EndingScene:
    """Enhanced ending with attitude-based branching, table scene, journal retrospective."""

    def __init__(self):
        self.font = get_font(23)
        self.font_result = get_font(42)
        self.font_small = get_font(18)
        self.font_dad = get_font(30)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.065
        self.finished = False
        self.ending_data = self.get_ending()
        self.pages = self.build_pages()
        self.page_index = 0
        self.text_to_print = self.prepare_page(self.page_index)
        # Enhanced ending phases
        self.phase = "narration"  # narration -> table -> carrot -> golden -> dad_voice -> result -> credits -> journal
        self.phase_timer = 0
        self.table_alpha = 0
        self.golden_alpha = 0
        self.dad_text_alpha = 0
        self.show_result = False
        self.result_y = 620
        self.result_done = False
        self.is_happy = False
        self.journal_scroll = 0
        self.show_journal = False
        self.carrot_pulse = 0
        self.letter_written = False
        self.credit_lines = self.build_credit_lines()
        self.credits_y = 620

    def write_desktop_letter(self):
        try:
            desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
            if not os.path.exists(desktop):
                return
            filepath = os.path.join(desktop, "아버지의_편지.txt")
            if not os.path.exists(filepath):
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write("아들, 밥은 먹었냐.\n")
                    f.write("바쁘다고 굶지 말고, 당근은 몸에 좋으니까 남기지 마라.\n\n")
                    f.write("- 아빠가")
        except Exception:
            pass

    def get_ending(self, force_type=None):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        ending_type = force_type or get_attitude_ending()
        game_state.last_ending = ending_type

        endings = {
            "true": {
                "title": "진엔딩: 내일 새벽, 함께",
                "result": "True Ending",
                "text": (
                    f"수확한 당근을 베어 문 순간, 세상이 황금빛으로 물든다.\n"
                    f"아버지의 땀과 기다림이 담긴 달콤한 맛.\n"
                    f"잠에서 깬 {name_eun} 식탁 앞에 먼저 앉아 당근을 집어 먹는다.\n"
                    f"'아빠, 내일 새벽에 같이 나갈게요. 다 알려주세요.'"
                ),
            },
            "happy": {
                "title": "해피엔딩: 가장 달콤한 수확",
                "result": "Happy Ending!",
                "text": (
                    f"수확한 당근을 베어 문 순간, 꿈속의 세상은 황금빛으로 물든다.\n"
                    f"아버지가 흘린 땀과 오랜 기다림의 무게가 담긴 달콤한 맛이었다.\n"
                    f"잠에서 깬 {name_eun} 식탁 위의 당근을 망설임 없이 입에 넣는다.\n"
                    f"'아빠, 오늘부터 제가 삽질할게요. 다 알려주세요.'"
                ),
            },
            "growth": {
                "title": "성장엔딩: 서툴러도 포기하지 않은 손",
                "result": "Growth Ending",
                "text": (
                    f"{name_eun} 수확한 당근을 바라본다.\n"
                    f"서툴렀고, 실수도 많았다.\n"
                    f"하지만 매번 다시 흙을 만졌다.\n"
                    f"잠에서 깨어난 뒤, 식탁의 당근 반찬을 천천히 씹는다.\n"
                    f"'서툴러도 괜찮다'고 아버지가 말해준 것 같았다."
                ),
            },
            "skill": {
                "title": "기술엔딩: 능숙하지만 부족한 것",
                "result": "Skill Ending",
                "text": (
                    f"{name_eun} 밭일을 잘 해냈다.\n"
                    f"수확량도 충분하고, 실수도 적었다.\n"
                    f"하지만 꿈에서 깨어난 뒤 식탁 앞에서 멈칫한다.\n"
                    f"농사는 배웠지만, 아버지의 마음은 아직 모르겠다."
                ),
            },
            "rush": {
                "title": "조급함엔딩: 아직 기다리지 못하는 마음",
                "result": "Rush Ending",
                "text": (
                    f"{name_eun} 당근을 급하게 뽑았다.\n"
                    f"기다리는 법을 배우지 못했다.\n"
                    f"잠에서 깬 뒤에도 식탁 앞을 지나치며 생각한다.\n"
                    f"'아직... 뭔가 부족한 것 같다.'"
                ),
            },
            "normal": {
                "title": "노멀엔딩: 조금은 알 것 같은 마음",
                "result": "Normal Ending",
                "text": (
                    f"{name_eun} 수확한 당근을 아주 조금 베어 문다.\n"
                    f"잠에서 깬 뒤 식탁에서 머뭇거리다가 당근 반찬 한 조각을 집어 먹는다.\n"
                    f"아버지는 아무 말 없이 조용히 웃는다."
                ),
            },
            "bad": {
                "title": "배드엔딩: 아직은 쓰기만 한 맛",
                "result": "Bad Ending...",
                "text": (
                    f"{name_eun} 수확한 당근을 바라보았지만 끝내 입에 넣지 못한다.\n"
                    f"잠에서 깬 뒤에도 식탁 위 당근 반찬을 가만히 바라볼 뿐이다.\n"
                    f"하지만 예전처럼 무작정 밀어내지는 않는다."
                ),
            },
        }

        data = endings.get(ending_type, endings["normal"])
        self.is_happy = ending_type in ("true", "happy", "growth")
        return data

    def build_pages(self):
        text_lines = self.ending_data["text"].split("\n")
        if len(text_lines) <= 2:
            return [f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines)]
        split_at = max(1, len(text_lines) // 2)
        return [
            f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines[:split_at]),
            "\n".join(text_lines[split_at:]),
        ]

    def build_credit_lines(self):
        impact_heading = "남겨진 일들" if game_state.last_ending in ("bad", "rush") else "이어진 일들"
        lines = [
            "몽중농원",
            "",
            "이번 꿈에서 남은 기록",
            f"물 뿌리기: {game_state.water_count}회",
            f"잡초 뽑기: {game_state.weed_count}회",
            f"해충 잡기: {game_state.pest_count}회",
        ]

        if game_state.choice_impacts:
            lines.extend(["", impact_heading])
            for item in game_state.choice_impacts:
                lines.append(item["title"])
                lines.append(item["impact"])

        return lines

    def _credit_content_height(self):
        height = 0
        for line in self.credit_lines:
            if not line:
                height += 26
                continue
            font = self.font_result if line == "몽중농원" else self.font_small
            height += len(wrap_text(line, font, 610)) * (font.get_height() + 6)
            height += 8
        return height + 80

    def _start_credits(self):
        self.credit_lines = self.build_credit_lines()
        self.credits_y = 620
        self.phase = "credits"
        self.phase_timer = 0

    def _finish_after_credits(self):
        if game_state.journal_entries:
            self.phase = "journal"
            self.show_journal = True
        else:
            save_progress()
            game_state.running = False

    def prepare_page(self, index):
        lines = []
        for paragraph in self.pages[index].split("\n"):
            if not paragraph:
                lines.append("")
            else:
                lines.extend(wrap_text(paragraph, self.font, 610))
        return "\n".join(lines)

    def advance(self):
        if not self.finished:
            self.printed_text = self.text_to_print
            self.char_idx = len(self.text_to_print)
            self.finished = True
            return

        if self.page_index < len(self.pages) - 1:
            self.page_index += 1
            self.printed_text = ""
            self.char_idx = 0
            self.finished = False
            self.text_to_print = self.prepare_page(self.page_index)
        else:
            self.phase = "table"
            self.phase_timer = 0

    def retry(self):
        game_state.understanding = 0
        game_state.score = 0
        game_state.timer = 0
        game_state.transition_text = ""
        game_state.transition_next = ""
        game_state.is_clear_transition = False
        game_state.return_scene = "farm"
        game_state.memory_title = ""
        game_state.memory_text = ""
        game_state.memory_next = "farm"
        game_state.final_health = 100
        game_state.farm_mistakes = 0
        game_state.journal_entries = []
        game_state.epiphanies_seen = set()
        game_state.weather = "맑음"
        game_state.weather_turns_left = 3
        # Reset new systems
        game_state.patience_score = 0
        game_state.care_score = 0
        game_state.empathy_choices = 0
        game_state.recovery_count = 0
        game_state.rush_count = 0
        game_state.last_failure_action = ""
        game_state.dad_lessons = {}
        game_state.gifts_revealed = 0
        game_state.current_sense = "낯선 흙냄새가 코끝을 스친다."
        game_state.dad_mode = False
        game_state.dad_mode_turns = 0
        game_state.dad_mode_triggered = False
        game_state.father_day_seen = set()
        game_state.water_count = 0
        game_state.weed_count = 0
        game_state.pest_count = 0
        game_state.choice_impacts = []
        # #14 Save progress before retry
        save_progress()
        game_state.current_scene = "intro"

    def change_ending(self, ending_type):
        self.ending_data = self.get_ending(ending_type)
        self.pages = self.build_pages()
        self.page_index = 0
        self.text_to_print = self.prepare_page(self.page_index)
        self.phase = "narration"
        self.printed_text = ""
        self.char_idx = 0
        self.finished = False
        self.phase_timer = 0
        self.show_result = False
        self.result_done = False
        self.result_y = 620
        self.show_journal = False
        self.letter_written = False
        self.table_alpha = 0
        self.golden_alpha = 0
        self.dad_text_alpha = 0
        self.carrot_pulse = 0
        self.credit_lines = self.build_credit_lines()
        self.credits_y = 620

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    if self.phase in ("result", "journal") or self.finished:
                        self.retry()
                        return
                elif event.key == pygame.K_1: self.change_ending("true")
                elif event.key == pygame.K_2: self.change_ending("happy")
                elif event.key == pygame.K_3: self.change_ending("growth")
                elif event.key == pygame.K_4: self.change_ending("skill")
                elif event.key == pygame.K_5: self.change_ending("rush")
                elif event.key == pygame.K_6: self.change_ending("normal")
                elif event.key == pygame.K_7: self.change_ending("bad")

            click = (event.type == pygame.MOUSEBUTTONDOWN or
                     (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE))

            if self.phase == "narration":
                if click:
                    self.advance()
            elif self.phase == "table":
                pass
            elif self.phase == "carrot":
                if click:
                    self.phase = "golden"
                    self.phase_timer = 0
            elif self.phase == "golden":
                pass
            elif self.phase == "dad_voice":
                if click and self.phase_timer > 2.0:
                    self.phase = "result"
                    self.phase_timer = 0
            elif self.phase == "result":
                if self.result_done and click:
                    self._start_credits()
            elif self.phase == "credits":
                if click and self.phase_timer > 1.0:
                    self._finish_after_credits()
            elif self.phase == "journal":
                if click:
                    save_progress()
                    game_state.running = False

    def update(self, dt):
        self.carrot_pulse += dt

        if self.phase == "narration":
            if self.finished:
                return
            self.char_timer += dt
            if self.char_timer >= self.char_delay:
                self.char_timer = 0
                if self.char_idx < len(self.text_to_print):
                    self.printed_text += self.text_to_print[self.char_idx]
                    self.char_idx += 1
                else:
                    self.finished = True

        elif self.phase == "table":
            self.phase_timer += dt
            self.table_alpha = min(255, int(self.phase_timer * 120))
            if self.phase_timer > 2.5:
                self.phase = "carrot"
                self.phase_timer = 0

        elif self.phase == "carrot":
            self.phase_timer += dt

        elif self.phase == "golden":
            self.phase_timer += dt
            self.golden_alpha = min(255, int(self.phase_timer * 200))
            if self.phase_timer > 1.8:
                self.phase = "dad_voice"
                self.phase_timer = 0

        elif self.phase == "dad_voice":
            self.phase_timer += dt
            self.dad_text_alpha = min(255, int(self.phase_timer * 150))

        elif self.phase == "result":
            self.phase_timer += dt
            if self.result_y > 260:
                self.result_y -= 55 * dt
            else:
                self.result_y = 260
                self.result_done = True
                if self.is_happy and not self.letter_written:
                    self.write_desktop_letter()
                    self.letter_written = True

        elif self.phase == "credits":
            self.phase_timer += dt
            self.credits_y -= 34 * dt
            if self.credits_y + self._credit_content_height() < 84:
                self._finish_after_credits()

    def draw(self, screen):
        if self.phase == "narration":
            self._draw_narration(screen)
        elif self.phase == "table":
            self._draw_table(screen)
        elif self.phase == "carrot":
            self._draw_carrot_click(screen)
        elif self.phase == "golden":
            self._draw_golden(screen)
        elif self.phase == "dad_voice":
            self._draw_dad_voice(screen)
        elif self.phase == "result":
            self._draw_result(screen)
        elif self.phase == "credits":
            self._draw_credits(screen)
        elif self.phase == "journal":
            self._draw_journal(screen)

    def _draw_narration(self, screen):
        draw_story_backdrop(screen, "night")
        dad = sprites["dad"]
        shadow = dad.copy()
        shadow.set_alpha(80)
        screen.blit(shadow, (400 - dad.get_width() // 2 + 6, 74))
        screen.blit(dad, (400 - dad.get_width() // 2, 68))
        box_rect = pygame.Rect(58, 286, 684, 256)
        draw_light_panel(screen, box_rect)
        draw_centered_lines(screen, self.printed_text.split("\n"), self.font, TEXT_DARK, 400, 318, line_gap=5)
        page = self.font_small.render(f"{self.page_index + 1}/{len(self.pages)}", True, TEXT_MUTED)
        screen.blit(page, (690, 548))
        if self.finished:
            prompt_text = "다음으로" if self.page_index < len(self.pages) - 1 else "계속"
            prompt = self.font_small.render(f"{prompt_text}: 클릭 또는 스페이스바", True, TEXT_MUTED)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 562))

    def _draw_table(self, screen):
        bg_r = min(60, int(self.phase_timer * 30))
        bg_g = min(40, int(self.phase_timer * 20))
        bg_b = min(25, int(self.phase_timer * 12))
        screen.fill((bg_r, bg_g, bg_b))
        # Table surface
        if self.table_alpha > 50:
            tc = min(255, self.table_alpha)
            # Table
            table_rect = pygame.Rect(100, 350, 600, 150)
            pygame.draw.rect(screen, (min(tc, 180), min(tc, 130), min(tc, 80)), table_rect)
            pygame.draw.rect(screen, (min(tc, 120), min(tc, 80), min(tc, 40)), table_rect, 4)
            # #2 Plate
            plate_x, plate_y = 340, 320
            pygame.draw.ellipse(screen, (min(tc, 230), min(tc, 225), min(tc, 215)),
                                (plate_x, plate_y, 120, 50))
            pygame.draw.ellipse(screen, (min(tc, 200), min(tc, 195), min(tc, 185)),
                                (plate_x, plate_y, 120, 50), 2)
            # Carrot pieces on plate
            if tc > 120:
                for i in range(3):
                    cx = plate_x + 30 + i * 25
                    cy = plate_y + 12
                    pygame.draw.rect(screen, (min(tc, 255), min(tc, 140), min(tc, 40)),
                                     (cx, cy, 18, 8), border_radius=3)
            # Chopsticks
            if tc > 150:
                pygame.draw.line(screen, (min(tc, 140), min(tc, 110), min(tc, 70)),
                                 (490, 310), (520, 380), 3)
                pygame.draw.line(screen, (min(tc, 140), min(tc, 110), min(tc, 70)),
                                 (500, 310), (530, 380), 3)

    def _draw_carrot_click(self, screen):
        screen.fill((60, 40, 25))
        # Table
        pygame.draw.rect(screen, (180, 130, 80), (100, 350, 600, 150))
        pygame.draw.rect(screen, (120, 80, 40), (100, 350, 600, 150), 4)
        # Plate
        pygame.draw.ellipse(screen, (230, 225, 215), (340, 320, 120, 50))
        pygame.draw.ellipse(screen, (200, 195, 185), (340, 320, 120, 50), 2)
        # Carrot sprite pulsing in center
        carrot = sprites["carrot"]
        scale = 1.0 + 0.06 * math.sin(self.carrot_pulse * 3)
        cw = int(carrot.get_width() * scale)
        ch = int(carrot.get_height() * scale)
        scaled = pygame.transform.scale(carrot, (cw, ch))
        screen.blit(scaled, (400 - cw // 2, 280 - ch // 2))
        # Prompt
        prompt = self.font_small.render("당근을 클릭하세요", True, (200, 180, 140))
        screen.blit(prompt, (400 - prompt.get_width() // 2, 430))

    def _draw_golden(self, screen):
        g = self.golden_alpha
        ending = game_state.last_ending
        
        if ending in ("true", "happy"):
            # Golden glow
            screen.fill((min(255, g), min(200, int(g * 0.78)), min(80, int(g * 0.3))))
            if g > 200:
                t = self.font.render("아삭.", True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "growth":
            # Warm brown glow
            screen.fill((min(200, int(g*0.8)), min(150, int(g * 0.6)), min(100, int(g * 0.4))))
            if g > 200:
                t = self.font.render("오도독.", True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "skill":
            # Cold white glow
            screen.fill((min(240, g), min(240, g), min(255, g)))
            if g > 200:
                t = self.font.render("사각.", True, (100, 100, 100))
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "rush":
            # Fast red flash
            screen.fill((min(200, g), min(50, int(g*0.2)), min(50, int(g*0.2))))
            if g > 200:
                t = self.font.render("우적.", True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        elif ending == "normal":
            # Dim yellow
            screen.fill((min(150, int(g*0.6)), min(150, int(g*0.6)), min(100, int(g*0.4))))
            if g > 200:
                t = self.font.render("사각.", True, WHITE)
                screen.blit(t, (400 - t.get_width() // 2, 290))
        else: # bad
            # Fade to gray
            screen.fill((min(80, int(g*0.3)), min(80, int(g*0.3)), min(80, int(g*0.3))))
            if g > 200:
                t = self.font.render("......", True, (150, 150, 150))
                screen.blit(t, (400 - t.get_width() // 2, 290))

    def _draw_dad_voice(self, screen):
        ending = game_state.last_ending
        a = self.dad_text_alpha
        
        if ending in ("true", "happy"):
            screen.fill((255, 200, 80))
            color = (min(a, 80), min(a, 50), min(a, 20))
            text = "...내일 새벽, 같이 가자." if ending == "true" else "...맛있냐?"
        elif ending == "growth":
            screen.fill((200, 150, 100))
            color = (min(a, 60), min(a, 40), min(a, 20))
            text = "...많이 컸네."
        elif ending == "skill":
            screen.fill((240, 240, 255))
            color = (min(a, 100), min(a, 100), min(a, 120))
            text = "...농사는 잘 지었구나. 그런데..."
        elif ending == "rush":
            screen.fill((200, 50, 50))
            color = (min(a, 255), min(a, 200), min(a, 200))
            text = "...급할 거 없다."
        elif ending == "normal":
            screen.fill((150, 150, 100))
            color = (min(a, 50), min(a, 50), min(a, 30))
            text = "...천천히 무라."
        else:
            screen.fill((80, 80, 80))
            color = (min(a, 150), min(a, 150), min(a, 150))
            text = "...그래."

        t = self.font_dad.render(text, True, color)
        screen.blit(t, (400 - t.get_width() // 2, 270))
        if self.phase_timer > 2.0:
            prompt = self.font_small.render("계속하려면 클릭하세요", True, color)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 450))

    def _draw_result(self, screen):
        draw_story_backdrop(screen, "night")
        result_text = self.ending_data["result"]
        color = (255, 225, 130) if self.is_happy else (180, 180, 180)
        result = self.font_result.render(result_text, True, color)
        screen.blit(result, (400 - result.get_width() // 2, int(self.result_y)))

        _, stage_name, _ = get_understanding_stage(game_state.understanding)
        stage_surf = self.font_small.render(f"마음의 단계: {stage_name}", True, (160, 150, 120))
        screen.blit(stage_surf, (400 - stage_surf.get_width() // 2, int(self.result_y) + 60))

        # #11 Attitude summary
        att_font = get_font(14)
        att_y = int(self.result_y) + 90
        att_items = []
        if game_state.patience_score >= 3:
            att_items.append("인내")
        if game_state.care_score >= 3:
            att_items.append("세심함")
        if game_state.empathy_choices >= 2:
            att_items.append("공감")
        if game_state.recovery_count >= 2:
            att_items.append("회복력")
        if att_items:
            att_text = "당신의 태도: " + " · ".join(att_items)
            att_surf = att_font.render(att_text, True, (140, 130, 100))
            screen.blit(att_surf, (400 - att_surf.get_width() // 2, att_y))

        if self.result_done:
            if game_state.journal_entries:
                prompt = self.font_small.render("R: 다시하기 / 크레딧: 스페이스바 / 1~7: 다른 엔딩 보기", True, (150, 150, 150))
            else:
                prompt = self.font_small.render("R: 다시하기 / 크레딧: 스페이스바 / 1~7: 다른 엔딩 보기", True, (150, 150, 150))
            screen.blit(prompt, (400 - prompt.get_width() // 2, 535))

    def _draw_credits(self, screen):
        draw_story_backdrop(screen, "night")
        overlay = pygame.Surface((800, 600), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 88))
        screen.blit(overlay, (0, 0))

        y = self.credits_y
        for line in self.credit_lines:
            if not line:
                y += 26
                continue

            is_title = line == "몽중농원"
            is_section = line in ("이번 꿈에서 남은 기록", "남겨진 일들", "이어진 일들")
            font = self.font_result if is_title else self.font if is_section else self.font_small
            color = (255, 226, 150) if is_title else (232, 205, 156) if is_section else (226, 220, 198)
            max_width = 620 if not is_title else 760

            for wrapped in wrap_text(line, font, max_width):
                surf = font.render(wrapped, True, color)
                screen.blit(surf, (400 - surf.get_width() // 2, int(y)))
                y += font.get_height() + 6
            y += 8 if is_section else 4

        if self.phase_timer > 1.0:
            prompt = self.font_small.render("넘기려면 클릭 또는 스페이스바", True, (150, 145, 125))
            screen.blit(prompt, (400 - prompt.get_width() // 2, 560))

    def _draw_journal(self, screen):
        draw_story_backdrop(screen, "night")
        panel = pygame.Rect(70, 36, 660, 514)
        draw_light_panel(screen, panel)
        title = self.font.render("밭일 일지", True, TEXT_DARK)
        screen.blit(title, (400 - title.get_width() // 2, 64))
        pygame.draw.line(screen, (180, 141, 82), (120, 98), (680, 98), 2)

        retro_font = get_font(14)
        y = 118
        for entry in game_state.journal_entries[-6:]:
            for line in entry.split("\n"):
                if y > 500:
                    break
                surf = self.font_small.render(line, True, TEXT_DARK)
                screen.blit(surf, (120, y))
                y += 24

                # #8 Journal retrospective
                if self.is_happy and line.strip() in JOURNAL_RETROSPECTIVES:
                    retro = JOURNAL_RETROSPECTIVES[line.strip()]
                    rs = retro_font.render(retro, True, TEXT_MUTED)
                    screen.blit(rs, (140, y))
                    y += 20
            y += 12

        prompt = self.font_small.render("R: 다시하기 / 끝내기: 스페이스바 / 1~7: 다른 엔딩 보기", True, TEXT_MUTED)
        screen.blit(prompt, (400 - prompt.get_width() // 2, 560))
