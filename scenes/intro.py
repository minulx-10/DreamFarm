import pygame
from core.game_state import append_josa, game_state
from core.assets import TEXT_DARK, TEXT_MUTED, WHITE, get_font, sprites
from core.ui import draw_centered_lines, draw_light_panel, draw_story_backdrop, wrap_text
from core import audio


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
        from core.crops import current_crop, swap_crop_word, NIGHTMARE_INTRO
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        crop = current_crop()
        crop_name = crop["name"]

        # 악)몽중농원 — 진엔딩 해금 모드의 전용 도입부
        # NIGHTMARE_INTRO 전체를 한 페이지에 밀어넣으면 패널을 넘쳐 안내문구와 겹친다.
        # 문단 단위로 나눠 각 페이지가 패널 안에 들어오도록 한다.
        if game_state.nightmare:
            return [
                "[악)몽중농원]\n남긴 것들의 밭\n\n"
                "여느 밤과 같은 꿈인 줄 알았다.\n\n"
                "그런데 하늘이 검붉다. 흙에서 탄내가 난다.\n"
                "밭 한가운데, 낯익은 접시들이 쌓여 있다 —\n"
                "여태 내가 남긴 음식들이다.",
                (
                    "어디선가 낮은 목소리가 울린다.\n"
                    "'남긴 것은 여기서 다 먹어야 한다.\n"
                    "먹으려면, 다시 길러야지.'\n\n"
                    "이 검붉은 밭에서 작물을 끝까지 길러 수확해야\n"
                    "꿈에서 깨어날 수 있다."
                ),
                (
                    f"{name_eun} 검붉은 흙 앞에 선다.\n"
                    f"이 지옥의 밭에서 {crop_name}를 끝까지 길러 거두어야\n"
                    "비로소 꿈에서 놓여날 수 있다.\n\n"
                    "'남기지 마라. 이번엔, 끝까지.'"
                ),
            ]

        # 일반 도입부 — 고른 작물에 맞춰 '당근'을 갈아 끼운다
        page1 = swap_crop_word(
            "[몽중농원]\n당근 한 뿌리의 시간\n\n"
            f"{name_eun} 식탁 위 당근 반찬을 슬쩍 밀어냈다.\n"
            "아버지는 아무 말 없이 그릇을 바라보다가 작게 한숨을 쉬었다.\n"
            "'언젠가는 이 한 조각에도 시간이 들어 있다는 걸 알게 되겠지.'",
            crop_name,
        )
        page2 = swap_crop_word(
            f"그날 밤, {name_eun} 낯선 흙냄새 속에서 눈을 뜬다.\n"
            "발밑에는 끝이 보이지 않는 당근밭이 펼쳐져 있었다.\n\n"
            "어디선가 낮은 목소리가 들린다.\n"
            "'네가 밀어낸 것을, 이번에는 네 손으로 길러 보아라.'",
            crop_name,
        )
        return [page1, page2]

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
                audio.play("click")
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
                audio.type_tick(self.text_to_print[self.char_idx - 1])
            else:
                self.finished = True

    def draw(self, screen):
        draw_story_backdrop(screen, "nightmare" if game_state.nightmare else "night")

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
