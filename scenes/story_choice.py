import pygame
from core.game_state import game_state
from core.assets import TEXT_DARK, TEXT_MUTED, WOOD_LIGHT, get_font
from core.ui import draw_button, draw_light_panel, draw_story_backdrop, wrap_text
from core import audio


class StoryChoiceScene:
    """Narrative choice event with two options that affect understanding differently."""

    def __init__(self):
        self.font_title = get_font(24)
        self.font = get_font(20)
        self.font_small = get_font(18)
        self.printed_text = ""
        self.char_idx = 0
        self.char_timer = 0
        self.char_delay = 0.055
        self.finished = False
        self.choice_made = False
        self.result_text = ""
        self.result_timer = 0

        data = game_state.choice_data or {}
        self.title = data.get("title", "")
        self.text = data.get("text", "")
        self.choice_a = data.get("choice_a", ("", {}))
        self.choice_b = data.get("choice_b", ("", {}))
        self.text_to_print = self._prepare(self.text)

        self.btn_a = pygame.Rect(80, 370, 290, 65)
        self.btn_b = pygame.Rect(430, 370, 290, 65)
        self.hover_a = False
        self.hover_b = False

    def _prepare(self, text):
        lines = []
        for p in text.split("\n"):
            if not p:
                lines.append("")
            else:
                lines.extend(wrap_text(p, self.font, 560))
        return "\n".join(lines)

    def _apply(self, choice):
        label, effects = choice
        # #11 Track empathy if this is the compassionate choice (choice_b)
        if choice == self.choice_b:
            game_state.empathy_choices += 1
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
        self.result_timer = 3.0

    def handle_events(self, events):
        for event in events:
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
