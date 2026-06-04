import pygame
from core.game_state import append_josa, game_state
from core.assets import TEXT_DARK, TEXT_MUTED, WHITE, get_font, sprites
from core.ui import draw_centered_lines, draw_light_panel, draw_story_backdrop, wrap_text


class IntroScene:
    def __init__(self):
        self.font = get_font(22)
        self.font_small = get_font(18)
        self.pages = self.get_intro_pages()
        self.page_index = 0
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.065
        self.finished = False
        self.text_to_print = self.prepare_page(self.page_index)

    def get_intro_pages(self):
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")

        return [
            (
                "[몽중농원]\n당근 한 뿌리의 시간\n\n"
                f"{name_eun} 식탁 위 당근 반찬을 슬쩍 밀어냈다.\n"
                "아버지는 아무 말 없이 그릇을 바라보다가 작게 한숨을 쉬었다.\n"
                "'언젠가는 이 한 조각에도 시간이 들어 있다는 걸 알게 되겠지.'"
            ),
            (
                f"그날 밤, {name_eun} 낯선 흙냄새 속에서 눈을 뜬다.\n"
                "발밑에는 끝이 보이지 않는 당근밭이 펼쳐져 있었다.\n\n"
                "어디선가 낮은 목소리가 들린다.\n"
                "'네가 밀어낸 것을, 이번에는 네 손으로 길러 보아라.'"
            ),
        ]

    def prepare_page(self, index):
        lines = []
        for paragraph in self.pages[index].split("\n"):
            if not paragraph:
                lines.append("")
            else:
                lines.extend(wrap_text(paragraph, self.font, 640))
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
            self.start_game()

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE
            ):
                self.advance()

    def start_game(self):
        game_state.reset()
        game_state.transition_text = (
            "[꿈속 밭일]\n"
            "밭의 상태를 살피고 알맞은 행동을 고르세요.\n"
            "기다리는 것도 선택이지만, 방치하면 문제가 커집니다."
        )
        game_state.transition_next = "farm"
        game_state.is_clear_transition = False
        game_state.current_scene = "transition"

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
        draw_story_backdrop(screen, "night")

        dad = sprites["dad"]
        shadow = dad.copy()
        shadow.set_alpha(80)
        screen.blit(shadow, (400 - dad.get_width() // 2 + 5, 51))
        screen.blit(dad, (400 - dad.get_width() // 2, 45))

        box_rect = pygame.Rect(58, 256, 684, 272)
        draw_light_panel(screen, box_rect)

        lines = self.printed_text.split("\n")
        draw_centered_lines(screen, lines, self.font, TEXT_DARK, 400, 288, line_gap=5)

        page = self.font_small.render(f"{self.page_index + 1}/{len(self.pages)}", True, TEXT_MUTED)
        screen.blit(page, (690, 538))

        if self.finished:
            prompt_text = "다음으로" if self.page_index < len(self.pages) - 1 else "시작하기"
            prompt = self.font_small.render(f"{prompt_text}: 클릭 또는 스페이스바", True, TEXT_MUTED)
            screen.blit(prompt, (400 - prompt.get_width() // 2, 560))
