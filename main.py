import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.game_state import game_state, apply_second_run
from scenes.name_input import NameInputScene
from scenes.intro import IntroScene
from scenes.transition import TransitionScene
from scenes.memory import MemoryScene
from scenes.farm import FarmScene
from scenes.stage1_sort import Stage1Scene
from scenes.stage2_water import Stage2Scene
from scenes.stage3_pest import Stage3Scene
from scenes.stage4_harvest import Stage4Scene
from scenes.ending import EndingScene
from scenes.epiphany import EpiphanyScene
from scenes.story_choice import StoryChoiceScene
from scenes.father_day import FatherDayScene

def main():
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("몽중농원")
    clock = pygame.time.Clock()
    
    from core.assets import init_sprites
    init_sprites()

    # #14 Check for 2nd playthrough
    apply_second_run()

    scenes = {
        "name_input": NameInputScene(),
        "intro": IntroScene(),
        "transition": TransitionScene(),
        "memory": MemoryScene(),
        "farm": FarmScene(),
        "stage1": Stage1Scene(),
        "stage2": Stage2Scene(),
        "stage3": Stage3Scene(),
        "stage4": Stage4Scene(),
        "ending": EndingScene(),
        "epiphany": EpiphanyScene(),
        "story_choice": StoryChoiceScene(),
        "father_day": FatherDayScene(),
    }

    current_scene_obj = scenes[game_state.current_scene]

    while game_state.running:
        dt = clock.tick(60) / 1000.0
        
        target_scene = game_state.current_scene

        if current_scene_obj != scenes.get(target_scene):
            # 상태 리셋이 필요한 씬만 새로 생성
            if target_scene == "stage1": scenes["stage1"] = Stage1Scene()
            elif target_scene == "stage2": scenes["stage2"] = Stage2Scene()
            elif target_scene == "stage3": scenes["stage3"] = Stage3Scene()
            elif target_scene == "stage4": scenes["stage4"] = Stage4Scene()
            elif target_scene == "ending": scenes["ending"] = EndingScene()
            elif target_scene == "intro": scenes["intro"] = IntroScene()
            elif target_scene == "memory": scenes["memory"] = MemoryScene()
            elif target_scene == "epiphany": scenes["epiphany"] = EpiphanyScene()
            elif target_scene == "story_choice": scenes["story_choice"] = StoryChoiceScene()
            elif target_scene == "father_day": scenes["father_day"] = FatherDayScene()
            
            current_scene_obj = scenes[target_scene]

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                game_state.running = False

        current_scene_obj.handle_events(events)
        current_scene_obj.update(dt)
        current_scene_obj.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
