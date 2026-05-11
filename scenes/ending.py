import math
import pygame
from core.game_state import append_josa, game_state, get_understanding_stage
from core.assets import BLACK, WHITE, get_font, sprites
from core.ui import draw_centered_lines, wrap_text


class EndingScene:
    """Enhanced ending with narrative pages → table scene → carrot click → dad's voice → journal review."""

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
        self.phase = "narration"  # narration → table → carrot → golden → dad_voice → result → journal
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

    def get_ending(self):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        u = game_state.understanding
        final_health = game_state.final_health
        mistakes = game_state.farm_mistakes
        if final_health < 45 or mistakes >= 8 or u < 20:
            self.is_happy = False
            return {
                "title": "배드엔딩: 아직은 쓰기만 한 맛",
                "result": "Bad Ending...",
                "text": f"{name_eun} 수확한 당근을 바라보았지만 끝내 입에 넣지 못한다.\n잠에서 깬 뒤에도 식탁 위 당근 반찬을 가만히 바라볼 뿐이다.\n하지만 예전처럼 무작정 밀어내지는 않는다."
            }
        elif final_health < 70 or mistakes >= 4 or u < 50:
            self.is_happy = False
            return {
                "title": "노멀엔딩: 조금은 알 것 같은 마음",
                "result": "Normal Ending",
                "text": f"{name_eun} 수확한 당근을 아주 조금 베어 문다.\n잠에서 깬 뒤 식탁에서 머뭇거리다가 당근 반찬 한 조각을 집어 먹는다.\n아버지는 아무 말 없이 조용히 웃는다."
            }
        else:
            self.is_happy = True
            return {
                "title": "해피엔딩: 가장 달콤한 수확",
                "result": "Happy Ending!",
                "text": f"수확한 당근을 베어 문 순간, 꿈속의 세상은 황금빛으로 물든다.\n아버지가 흘린 땀과 오랜 기다림의 무게가 담긴 달콤한 맛이었다.\n잠에서 깬 {name_eun} 식탁 위의 당근을 망설임 없이 입에 넣는다.\n'아빠, 오늘부터 제가 삽질할게요. 다 알려주세요.'"
            }

    def build_pages(self):
        text_lines = self.ending_data["text"].split("\n")
        if len(text_lines) <= 2:
            return [f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines)]
        split_at = max(1, len(text_lines) // 2)
        return [
            f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines[:split_at]),
            "\n".join(text_lines[split_at:]),
        ]

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
            # Move to table scene
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
        game_state.current_scene = "intro"

    def handle_events(self, events):
        for event in events:
            # R to retry (available in most phases)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                if self.phase in ("result", "journal") or self.finished:
                    self.retry()
                    return

            click = (event.type == pygame.MOUSEBUTTONDOWN or
                     (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE))

            if self.phase == "narration":
                if click:
                    self.advance()
            elif self.phase == "table":
                pass  # auto-advance
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
                    if game_state.journal_entries:
                        self.phase = "journal"
                        self.show_journal = True
                    else:
                        game_state.running = False
            elif self.phase == "journal":
                if click:
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
        elif self.phase == "journal":
            self._draw_journal(screen)

    def _draw_narration(self, screen):
        screen.fill(BLACK)
        dad = sprites["dad"]
        screen.blit(dad, (400 - dad.get_width() // 2, 78))
        box_rect = pygame.Rect(55, 292, 690, 250)
        pygame.draw.rect(screen, WHITE, box_rect, 4)
        draw_centered_lines(screen, self.printed_text.split("\n"), self.font, WHITE, 400, 322, line_gap=5)
        page = self.font_small.render(f"{self.page_index + 1}/{len(self.pages)}", True, (130, 130, 130))
        screen.blit(page, (690, 548))
        if self.finished:
            prompt_text = "다음으로" if self.page_index < len(self.pages) - 1 else "계속"
            prompt = self.font_small.render(f"{prompt_text}: 클릭 또는 스페이스바", True, (150, 150, 150))
            screen.blit(prompt, (400 - prompt.get_width() // 2, 562))

    def _draw_table(self, screen):
        # Fade from black to warm brown (table)
        bg_r = min(60, int(self.phase_timer * 30))
        bg_g = min(40, int(self.phase_timer * 20))
        bg_b = min(25, int(self.phase_timer * 12))
        screen.fill((bg_r, bg_g, bg_b))
        # Table surface
        if self.table_alpha > 50:
            table_rect = pygame.Rect(100, 350, 600, 150)
            tc = min(255, self.table_alpha)
            pygame.draw.rect(screen, (min(tc, 180), min(tc, 130), min(tc, 80)), table_rect)
            pygame.draw.rect(screen, (min(tc, 120), min(tc, 80), min(tc, 40)), table_rect, 4)

    def _draw_carrot_click(self, screen):
        screen.fill((60, 40, 25))
        # Table
        pygame.draw.rect(screen, (180, 130, 80), (100, 350, 600, 150))
        pygame.draw.rect(screen, (120, 80, 40), (100, 350, 600, 150), 4)
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
        # Golden light fills screen
        g = self.golden_alpha
        screen.fill((min(255, g), min(200, int(g * 0.78)), min(80, int(g * 0.3))))
        if g > 200:
            t = self.font.render("아삭.", True, WHITE)
            screen.blit(t, (400 - t.get_width() // 2, 290))

    def _draw_dad_voice(self, screen):
        screen.fill((255, 200, 80))
        a = self.dad_text_alpha
        color = (min(a, 80), min(a, 50), min(a, 20))
        text = self.font_dad.render("...맛있냐?", True, color)
        screen.blit(text, (400 - text.get_width() // 2, 270))
        if self.phase_timer > 2.0:
            prompt = self.font_small.render("계속하려면 클릭하세요", True, (140, 110, 50))
            screen.blit(prompt, (400 - prompt.get_width() // 2, 450))

    def _draw_result(self, screen):
        screen.fill(BLACK)
        result_text = self.ending_data["result"]
        color = (255, 225, 130) if self.is_happy else (180, 180, 180)
        result = self.font_result.render(result_text, True, color)
        screen.blit(result, (400 - result.get_width() // 2, int(self.result_y)))

        # Understanding stage
        _, stage_name, _ = get_understanding_stage(game_state.understanding)
        stage_surf = self.font_small.render(f"마음의 단계: {stage_name}", True, (160, 150, 120))
        screen.blit(stage_surf, (400 - stage_surf.get_width() // 2, int(self.result_y) + 60))

        if self.result_done:
            if game_state.journal_entries:
                prompt = self.font_small.render("R: 다시하기 / 일지 보기: 클릭 또는 스페이스바", True, (150, 150, 150))
            else:
                prompt = self.font_small.render("R: 다시하기 / 끝내기: 클릭 또는 스페이스바", True, (150, 150, 150))
            screen.blit(prompt, (400 - prompt.get_width() // 2, 535))

    def _draw_journal(self, screen):
        screen.fill((20, 18, 15))
        title = self.font.render("밭일 일지", True, (220, 200, 160))
        screen.blit(title, (400 - title.get_width() // 2, 30))
        pygame.draw.line(screen, (80, 70, 50), (100, 65), (700, 65), 2)

        y = 80
        for entry in game_state.journal_entries[-6:]:
            for line in entry.split("\n"):
                if y > 520:
                    break
                surf = self.font_small.render(line, True, (180, 165, 130))
                screen.blit(surf, (120, y))
                y += 24
            y += 12

        prompt = self.font_small.render("R: 다시하기 / 끝내기: 클릭 또는 스페이스바", True, (120, 110, 90))
        screen.blit(prompt, (400 - prompt.get_width() // 2, 560))
