import pygame
from core.game_state import game_state
from core.assets import get_font, BLACK, WHITE

class EndingScene:
    def __init__(self):
        self.font = get_font(28)
        self.font_small = get_font(20)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.05
        self.finished = False
        
        self.text_to_print = ""
        self.initialized = False

    def get_ending(self):
        from core.game_state import append_josa
        name = game_state.player_name
        name_eun = append_josa(name, "은/는")
        u = game_state.understanding
        if u < 20:
            return {
                "title": "엔딩 1: 아직은 쓰기만 한 맛",
                "text": f"{name_eun} 수확한 당근을 바라보았지만 끝내 입에 넣지 못한다.\n잠에서 깬 뒤에도 식탁 위 당근 반찬을 가만히 바라볼 뿐이다.\n하지만 예전처럼 무작정 밀어내지는 않는다."
            }
        elif u < 50:
            return {
                "title": "엔딩 2: 조금은 알 것 같은 마음",
                "text": f"{name_eun} 수확한 당근을 아주 조금 베어 문다.\n잠에서 깬 뒤 식탁에서 머뭇거리다가 당근 반찬 한 조각을 집어 먹는다.\n아버지는 아무 말 없이 조용히 웃는다."
            }
        else:
            return {
                "title": "진엔딩: 가장 달콤한 수확",
                "text": f"수확한 당근을 베어 문 순간, 꿈속의 세상은 황금빛으로 물든다.\n아버지가 흘린 땀과 오랜 기다림의 무게가 담긴 달콤한 맛이었다.\n잠에서 깬 {name_eun} 식탁 위의 당근을 망설임 없이 입에 넣는다.\n'아빠, 오늘부터 제가 삽질할게요. 다 알려주세요.'"
            }

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
                if not self.finished:
                    self.printed_text = self.text_to_print
                    self.char_idx = len(self.text_to_print)
                    self.finished = True
                else:
                    game_state.running = False

    def update(self, dt):
        if not self.initialized:
            ending_data = self.get_ending()
            self.text_to_print = f"[{ending_data['title']}]\n\n" + ending_data["text"]
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
        
        # Draw Dad sprite
        from core.assets import sprites
        dad = sprites['dad']
        screen.blit(dad, (400 - dad.get_width()//2, 80))
        
        # Undertale text box style
        box_rect = pygame.Rect(50, 350, 700, 200)
        pygame.draw.rect(screen, WHITE, box_rect, 4)
        
        y = 380
        lines = self.printed_text.split('\n')
        for line in lines:
            surf = self.font.render(line, True, WHITE)
            screen.blit(surf, (80, y))
            y += 35
            
        if self.finished:
            prompt = self.font_small.render("계속...", True, (150, 150, 150))
            screen.blit(prompt, (650, 510))
