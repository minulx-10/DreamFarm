import pygame
import random
from core.game_state import game_state
from core.assets import *
from core.ui import draw_wood_panel, draw_top_bar, draw_bottom_bar

class Button:
    def __init__(self, x, y, w, h, text, value):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.value = value
        self.font = get_font(20)

    def draw(self, screen):
        draw_wood_panel(screen, self.rect)
        text_surf = self.font.render(self.text, True, TEXT_BROWN)
        screen.blit(text_surf, (self.rect.centerx - text_surf.get_width()//2, self.rect.centery - text_surf.get_height()//2))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

class FarmScene:
    def __init__(self):
        self.stages = [
            {"title": "스테이지 1: 낯선 밭", "tasks": ["흙 고르기", "씨앗 심기", "물 주기"]},
            {"title": "스테이지 2: 싹 돌보기", "tasks": ["물 주기", "잡초 제거", "기다리기"]},
            {"title": "스테이지 3: 벌레와 병충해", "tasks": ["해충 제거", "잡초 제거", "물 주기"]},
            {"title": "스테이지 4: 폭우 대응", "tasks": ["배수로 정리", "흙 고르기", "물 주기"]},
            {"title": "스테이지 5: 기다림", "tasks": ["기다리기", "잡초 제거", "기다리기"]},
            {"title": "최종장: 수확", "tasks": ["수확하기"]}
        ]
        self.actions = ["흙 고르기", "씨앗 심기", "물 주기", "잡초 제거", "해충 제거", "배수로 정리", "기다리기", "수확하기"]
        
        self.buttons = []
        start_x = 440
        start_y = 150
        for i, act in enumerate(self.actions):
            bx = start_x + (i % 2) * 160
            by = start_y + (i // 2) * 60
            self.buttons.append(Button(bx, by, 140, 45, act, act))
            
        self.stage_index = 0
        self.task_index = 0
        self.message = "꿈속의 낯선 밭에서 깨어난다. 오른쪽에서 올바른 행동을 선택하세요."
        self.growth_stage = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in self.buttons:
                    if btn.is_clicked(event.pos):
                        self.do_action(btn.value)

    def do_action(self, action):
        if self.stage_index >= len(self.stages): return
        
        stage = self.stages[self.stage_index]
        expected = stage["tasks"][self.task_index]
        
        if action == expected:
            self.task_index += 1
            self.message = f"[{action}]을(를) 무사히 마쳤습니다!"
            self.growth_stage += 1
            
            # 미니게임 돌발 이벤트 발생 (확률 30%)
            if random.random() < 0.3 and action != "수확하기":
                mg = random.choice(["stage1", "stage2", "stage3"])
                if mg == "stage1":
                    game_state.transition_text = "[돌발 이벤트!]\n\n밭에 엉뚱한 것들이 섞여 있습니다!\n올바르게 분류하여 추가 이해도를 얻으세요."
                elif mg == "stage2":
                    game_state.transition_text = "[돌발 이벤트!]\n\n작물이 더 많은 물을 필요로 합니다!\n정확한 타이밍에 물을 주어 추가 이해도를 얻으세요."
                else:
                    game_state.transition_text = "[돌발 이벤트!]\n\n벌레가 떼로 나타났습니다!\n빠르게 해충을 제거하여 추가 이해도를 얻으세요."
                
                game_state.current_scene = "transition"
                game_state.is_clear_transition = False
                game_state.transition_next = mg
                game_state.return_scene = "farm"
                
        else:
            self.message = f"지금은 [{expected}] 행동이 필요합니다. 순서가 틀렸습니다."
            game_state.understanding = max(0, game_state.understanding - 1)

    def update(self, dt):
        if self.stage_index < len(self.stages):
            stage = self.stages[self.stage_index]
            if self.task_index >= len(stage["tasks"]):
                self.stage_index += 1
                self.task_index = 0
                game_state.understanding += 10 # 스테이지 클리어 기본 보상
                
                if self.stage_index >= len(self.stages):
                    game_state.current_scene = "ending"
                else:
                    self.message = f"{self.stages[self.stage_index]['title']} 시작. 다음 행동을 선택하세요."

    def draw(self, screen):
        draw_tiled_background(screen, 800, 600)
        
        # 농장 구역
        plot_rect = pygame.Rect(50, 150, 350, 300)
        draw_wood_panel(screen, plot_rect)
        inner_plot = plot_rect.inflate(-20, -20)
        pygame.draw.rect(screen, DIRT_COLOR, inner_plot)
        pygame.draw.rect(screen, DIRT_DARK, inner_plot, 4)
        
        # 작물 성장 표시
        if self.growth_stage > 0:
            for i in range(5):
                x = 80 + i * 60
                y = 250
                if self.growth_stage < 4:
                    screen.blit(sprites['seed'], (x, y))
                elif self.growth_stage < 7:
                    screen.blit(sprites['sprout1'], (x, y-10))
                elif self.growth_stage < 10:
                    screen.blit(sprites['sprout2'], (x-5, y-20))
                elif self.growth_stage < 13:
                    screen.blit(sprites['sprout3'], (x-5, y-30))
                elif self.growth_stage < 16:
                    screen.blit(sprites['sprout4'], (x-5, y-35))
                else: # 다 자란 당근
                    screen.blit(sprites['carrot'], (x-5, y-60))
                    
        # 제목 표시
        title_font = get_font(26)
        if self.stage_index < len(self.stages):
            title_surf = title_font.render(self.stages[self.stage_index]["title"], True, TEXT_BROWN)
            title_rect = pygame.Rect(50, 80, 350, 50)
            draw_wood_panel(screen, title_rect)
            screen.blit(title_surf, (title_rect.centerx - title_surf.get_width()//2, title_rect.centery - title_surf.get_height()//2))
            
            # 현재 할 일 힌트
            hint_surf = get_font(20).render(f"필요한 일: {self.stages[self.stage_index]['tasks'][self.task_index]}", True, BLACK)
            screen.blit(hint_surf, (50, 460))
        
        for btn in self.buttons:
            btn.draw(screen)
            
        draw_top_bar(screen, show_stats=False)
        draw_bottom_bar(screen, "농장 일지", self.message)
