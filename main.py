import pygame
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.game_state import game_state, apply_second_run
from core import audio
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
    audio.init()

    # #14 Check for 2nd playthrough
    apply_second_run()

    # 씬별 배경음 매핑 (None이면 현재 곡 유지)
    BGM_BY_SCENE = {
        "name_input": "night", "intro": "night", "memory": "night",
        "story_choice": "night", "father_day": "night",
        "farm": "farm", "stage1": "farm", "stage2": "farm",
        "stage3": "farm", "stage4": "farm",
        "ending": "ending",
        "transition": None, "epiphany": None,
    }

    # 씬 이름 → 생성자 레지스트리
    SCENE_FACTORIES = {
        "name_input": NameInputScene,
        "intro": IntroScene,
        "transition": TransitionScene,
        "memory": MemoryScene,
        "farm": FarmScene,
        "stage1": Stage1Scene,
        "stage2": Stage2Scene,
        "stage3": Stage3Scene,
        "stage4": Stage4Scene,
        "ending": EndingScene,
        "epiphany": EpiphanyScene,
        "story_choice": StoryChoiceScene,
        "father_day": FatherDayScene,
    }
    # 진입할 때마다 새 상태로 재생성해야 하는 씬 (farm/name_input/transition은 유지)
    FRESH_ON_ENTER = {
        "intro", "memory", "epiphany", "story_choice", "father_day",
        "stage1", "stage2", "stage3", "stage4", "ending",
    }

    scenes = {name: factory() for name, factory in SCENE_FACTORIES.items()}

    current_key = game_state.current_scene
    current_scene_obj = scenes[current_key]

    while game_state.running:
        dt = clock.tick(60) / 1000.0
        game_state.play_time += dt

        target_scene = game_state.current_scene

        if target_scene != current_key:
            # 인트로 진입은 새 게임이므로 밭도 함께 초기화
            if target_scene == "intro":
                scenes["farm"] = SCENE_FACTORIES["farm"]()
            if target_scene in FRESH_ON_ENTER:
                scenes[target_scene] = SCENE_FACTORIES[target_scene]()
            current_scene_obj = scenes[target_scene]
            current_key = target_scene

        # 씬에 맞는 배경음 재생 (같은 곡이면 내부에서 무시됨)
        desired_bgm = BGM_BY_SCENE.get(target_scene)
        if desired_bgm:
            audio.play_bgm(desired_bgm)

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                game_state.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                audio.toggle_mute()

        current_scene_obj.handle_events(events)
        current_scene_obj.update(dt)
        current_scene_obj.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
