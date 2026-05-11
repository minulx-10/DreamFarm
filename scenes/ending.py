import pygame
from core.game_state import append_josa, game_state
from core.assets import BLACK, WHITE, get_font, sprites
from core.ui import draw_centered_lines, wrap_text


class EndingScene:
    def __init__(self):
        self.font = get_font(23)
        self.font_small = get_font(18)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.065
        self.finished = False
        self.ending_data = self.get_ending()
        self.pages = self.build_pages()
        self.page_index = 0
        self.text_to_print = self.prepare_page(self.page_index)

    def get_ending(self):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        u = game_state.understanding
        if u < 20:
            return {
                "title": "배드엔딩: 아직은 쓰기만 한 맛",
                "text": f"{name_eun} 수확한 당근을 바라보았지만 끝내 입에 넣지 못한다.\n잠에서 깬 뒤에도 식탁 위 당근 반찬을 가만히 바라볼 뿐이다.\n하지만 예전처럼 무작정 밀어내지는 않는다."
            }
        elif u < 50:
            return {
                "title": "배드엔딩: 조금은 알 것 같은 마음",
                "text": f"{name_eun} 수확한 당근을 아주 조금 베어 문다.\n잠에서 깬 뒤 식탁에서 머뭇거리다가 당근 반찬 한 조각을 집어 먹는다.\n아버지는 아무 말 없이 조용히 웃는다."
            }
        else:
            return {
                "title": "해피엔딩: 가장 달콤한 수확",
                "text": f"수확한 당근을 베어 문 순간, 꿈속의 세상은 황금빛으로 물든다.\n아버지가 흘린 땀과 오랜 기다림의 무게가 담긴 달콤한 맛이었다.\n잠에서 깬 {name_eun} 식탁 위의 당근을 망설임 없이 입에 넣는다.\n'아빠, 오늘부터 제가 삽질할게요. 다 알려주세요.'"
            }

    def build_pages(self):
        text_lines = self.ending_data["text"].split("\n")
        if len(text_lines) <= 2:
            return [
                f"[{self.ending_data['title']}]\n\n" + "\n".join(text_lines),
            ]
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
            game_state.running = False

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
        game_state.current_scene = "intro"

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.finished:
                self.retry()
            elif event.type == pygame.MOUSEBUTTONDOWN or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            ):
                self.advance()

    def update(self, dt):
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

    def draw(self, screen):
        screen.fill(BLACK)

        dad = sprites["dad"]
        screen.blit(dad, (400 - dad.get_width() // 2, 78))

        box_rect = pygame.Rect(55, 292, 690, 250)
        pygame.draw.rect(screen, WHITE, box_rect, 4)

        draw_centered_lines(screen, self.printed_text.split("\n"), self.font, WHITE, 400, 322, line_gap=5)

        page = self.font_small.render(f"{self.page_index + 1}/{len(self.pages)}", True, (130, 130, 130))
        screen.blit(page, (690, 548))

        if self.finished:
            prompt_text = "다음으로" if self.page_index < len(self.pages) - 1 else "끝내기"
            if self.page_index < len(self.pages) - 1:
                prompt = self.font_small.render(f"{prompt_text}: 클릭 또는 스페이스바", True, (150, 150, 150))
            else:
                prompt = self.font_small.render("R: 다시하기 / 끝내기: 클릭 또는 스페이스바", True, (150, 150, 150))
            screen.blit(prompt, (400 - prompt.get_width() // 2, 562))
