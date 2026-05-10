import pygame
from core.game_state import game_state
from core.assets import get_font, BLACK, WHITE, sprites

class IntroScene:
    def __init__(self):
        self.font = get_font(22)
        self.font_small = get_font(18)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.05
        self.finished = False
        
        self.text_to_print = ""
        self.initialized = False

    def wrap_text(self, text, font, max_width):
        wrapped_text = ""
        current_line = ""
        for char in text:
            if char == '\n':
                wrapped_text += current_line + '\n'
                current_line = ""
                continue
                
            test_line = current_line + char
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                wrapped_text += current_line + '\n'
                current_line = char if char != ' ' else ""
                
        if current_line:
            wrapped_text += current_line
        return wrapped_text

    def get_intro_text(self):
        from core.game_state import append_josa
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        name_ga = append_josa(name, "이/가")
        return (
            "[당근 한 뿌리의 시간]\n\n"
            f"{name_eun} 식탁 위 당근 반찬을 슬쩍 밀어냈다.\n"
            f"아버지는 아무 말 없이 그릇을 바라보다가 작게 한숨을 쉬었다.\n"
            f"'언젠가는 이 한 조각에도 시간이 들어 있다는 걸 알게 되겠지.'\n\n"
            f"그날 밤, {name_eun} 낯선 흙냄새 속에서 눈을 뜬다.\n"
            f"발밑에는 끝이 보이지 않는 당근밭이 펼쳐져 있었다.\n"
            f"어디선가 낮은 목소리가 들린다.\n"
            f"'네가 밀어낸 것을, 이번에는 네 손으로 길러 보아라.'"
        )

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                if not self.finished:
                    self.printed_text = self.text_to_print
                    self.char_idx = len(self.text_to_print)
                    self.finished = True
                else:
                    self.start_game()

    def start_game(self):
        game_state.understanding = 0
        game_state.transition_text = "[꿈속 밭일]\n밭의 상태를 살피고 알맞은 행동을 고르세요.\n기다리는 것도 선택이지만, 방치하면 문제가 커집니다."
        game_state.transition_next = "farm"
        game_state.is_clear_transition = False
        game_state.current_scene = "transition"

    def update(self, dt):
        if not self.initialized:
            raw_text = self.get_intro_text()
            self.text_to_print = self.wrap_text(raw_text, self.font, 680)
            self.initialized = True
            
        if not self.finished:
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
        
        dad = sprites['dad']
        screen.blit(dad, (400 - dad.get_width()//2, 80))
        
        box_rect = pygame.Rect(40, 260, 720, 310)
        pygame.draw.rect(screen, WHITE, box_rect, 4)
        
        y = 280
        lines = self.printed_text.split('\n')
        for line in lines:
            surf = self.font.render(line, True, WHITE)
            screen.blit(surf, (60, y))
            y += 28
            
        if self.finished:
            prompt = self.font_small.render("시작하려면 클릭하거나 스페이스바를 누르세요", True, (150, 150, 150))
            screen.blit(prompt, (50, 580))
