import pygame
import sys
import os
import math

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.game_state import game_state, apply_second_run
from core import audio
from core.settings_overlay import SettingsOverlay
from scenes.title import TitleScene
from scenes.crop_select import CropSelectScene
from scenes.gallery import GalleryScene
from scenes.name_input import NameInputScene
from scenes.intro import IntroScene
from scenes.transition import TransitionScene
from scenes.memory import MemoryScene
from scenes.farm import FarmScene
from scenes.stage1_sort import Stage1Scene
from scenes.stage2_water import Stage2Scene
from scenes.stage3_pest import Stage3Scene
from scenes.stage4_harvest import Stage4Scene
from scenes.star_connect import StarConnectScene
from scenes.ending import EndingScene
from scenes.epiphany import EpiphanyScene
from scenes.story_choice import StoryChoiceScene
from scenes.father_day import FatherDayScene


def main():
    pygame.init()
    
    # 디스플레이 초기화 변수
    is_fullscreen = False
    current_nightmare = False
    screen = None
    offset_x, offset_y = 0, 0
    target_w, target_h = 800, 600
    
    def update_display_mode():
        nonlocal screen, current_nightmare, is_fullscreen, offset_x, offset_y, target_w, target_h
        current_nightmare = game_state.nightmare
        w = 960 if current_nightmare else 800
        h = 720 if current_nightmare else 600

        if is_fullscreen:
            # (0,0) + FULLSCREEN → 모니터 native 해상도로 꽉 채운다.
            # 그리기는 800x600 가상 버퍼에 하고 실제 창 크기로 스케일하므로 어떤 해상도든 무방하다.
            try:
                screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.DOUBLEBUF)
            except Exception:
                try:
                    # native 실패 시, 가상 해상도 비율 그대로 전체화면 시도
                    screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
                except Exception:
                    # 전체화면 모두 실패 시 창모드로 복귀 (크래시 방지)
                    screen = pygame.display.set_mode((w, h), pygame.DOUBLEBUF)
                    is_fullscreen = False
        else:
            screen = pygame.display.set_mode((w, h), pygame.DOUBLEBUF)
            
        # 4:3 종횡비를 유지하며 화면을 스케일링하기 위한 해상도 및 검은 띠 여백 계산
        actual_w, actual_h = screen.get_size()
        if actual_w / actual_h > 4.0 / 3.0:
            target_h = actual_h
            target_w = int(actual_h * 4.0 / 3.0)
            offset_x = (actual_w - target_w) // 2
            offset_y = 0
        else:
            target_w = actual_w
            target_h = int(actual_w * 3.0 / 4.0)
            offset_x = 0
            offset_y = (actual_h - target_h) // 2
        
    update_display_mode()
    pygame.display.set_caption("몽중농원")
    
    # 윈도우 창 아이콘 설정
    try:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "logo.png")
        if os.path.exists(icon_path):
            icon_surf = pygame.image.load(icon_path)
            pygame.display.set_icon(icon_surf)
    except Exception as e:
        pass
        
    clock = pygame.time.Clock()
    
    from core.assets import init_sprites
    init_sprites()
    audio.init()

    # #14 Check for 2nd playthrough
    apply_second_run()

    # 가상 화면 800x600 버퍼 생성
    virtual_screen = pygame.Surface((800, 600))

    # 마우스 좌표 역계산(역배율 스케일링)을 위한 get_pos 재정의 (종횡비 보정 반영)
    orig_get_pos = pygame.mouse.get_pos
    def mapped_get_pos():
        ax, ay = orig_get_pos()
        vx = int((ax - offset_x) * 800.0 / target_w)
        vy = int((ay - offset_y) * 600.0 / target_h)
        return (max(0, min(799, vx)), max(0, min(599, vy)))
    pygame.mouse.get_pos = mapped_get_pos

    BGM_BY_SCENE = {
        "title": "night", "crop_select": "night", "gallery": "night", 
        "name_input": "night", "intro": "night",
        "memory": None, "story_choice": None, "father_day": None,
        "farm": "farm", "stage1": "farm", "stage2": "farm",
        "stage3": "farm", "stage4": "farm", "star_connect": None,
        "ending": None,
        "transition": None, "epiphany": None,
    }

    SCENE_FACTORIES = {
        "title": TitleScene,
        "crop_select": CropSelectScene,
        "gallery": GalleryScene,
        "name_input": NameInputScene,
        "intro": IntroScene,
        "transition": TransitionScene,
        "memory": MemoryScene,
        "farm": FarmScene,
        "stage1": Stage1Scene,
        "stage2": Stage2Scene,
        "stage3": Stage3Scene,
        "stage4": Stage4Scene,
        "star_connect": StarConnectScene,
        "ending": EndingScene,
        "epiphany": EpiphanyScene,
        "story_choice": StoryChoiceScene,
        "father_day": FatherDayScene,
    }
    
    FRESH_ON_ENTER = {
        "title", "crop_select", "gallery", "intro", "memory", "epiphany", 
        "story_choice", "father_day", "stage1", "stage2", "stage3", 
        "stage4", "star_connect", "ending",
    }

    scenes = {name: factory() for name, factory in SCENE_FACTORIES.items()}

    settings_overlay = SettingsOverlay()
    from core.quit_overlay import QuitOverlay
    quit_overlay = QuitOverlay()

    current_key = game_state.current_scene
    current_scene_obj = scenes[current_key]

    while game_state.running:
        dt = clock.tick(60) / 1000.0
        game_state.play_time += dt

        target_scene = game_state.current_scene

        # 지옥 모드 진입/해제에 따른 동적 해상도 창 크기 재설정
        if game_state.nightmare != current_nightmare:
            update_display_mode()

        if target_scene != current_key:
            if target_scene == "intro":
                scenes["farm"] = SCENE_FACTORIES["farm"]()
            if target_scene in FRESH_ON_ENTER:
                scenes[target_scene] = SCENE_FACTORIES[target_scene]()
            current_scene_obj = scenes[target_scene]
            current_key = target_scene

        # 타이틀 등에서 '설정' 버튼을 누르면 소리/저장 오버레이를 연다
        if game_state.request_settings:
            game_state.request_settings = False
            settings_overlay.open = True

        # 설정 오버레이에서 이어하기 로드 요청 시 처리
        if game_state.request_load:
            game_state.request_load = False
            from core import save_system
            data = save_system.load_slot()
            if data:
                save_system.restore(data, scenes["farm"])
                game_state.current_scene = "farm"
                current_scene_obj = scenes["farm"]
                current_key = "farm"
                # 지옥 모드 여부에 맞게 창 크기 즉시 갱신
                if game_state.nightmare != current_nightmare:
                    update_display_mode()
                audio.play_bgm("farm")

        desired_bgm = BGM_BY_SCENE.get(target_scene)
        if desired_bgm:
            audio.play_bgm(desired_bgm)

        events = pygame.event.get()
        
        # 1. F11 전체화면 감지 및 마우스 좌표 가상 해상도로 역배율 보정 (종횡비 고려)
        mapped_events = []
        for event in events:
            if event.type == pygame.QUIT:
                game_state.request_quit = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                update_display_mode()
            
            # 마우스 입력 좌표 역배율 보정 (레터박스/필러박스 여백 감산 및 가변 배율 적용)
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                mx = event.pos[0] - offset_x
                my = event.pos[1] - offset_y
                vx = int(mx * 800.0 / target_w)
                vy = int(my * 600.0 / target_h)
                vx = max(0, min(799, vx))
                vy = max(0, min(599, vy))
                mapped_event = pygame.event.Event(event.type, pos=(vx, vy), button=event.button)
                mapped_events.append(mapped_event)
            elif event.type == pygame.MOUSEMOTION:
                mx = event.pos[0] - offset_x
                my = event.pos[1] - offset_y
                vx = int(mx * 800.0 / target_w)
                vy = int(my * 600.0 / target_h)
                vx = max(0, min(799, vx))
                vy = max(0, min(599, vy))
                vrx = int(event.rel[0] * 800.0 / target_w)
                vry = int(event.rel[1] * 600.0 / target_h)
                mapped_event = pygame.event.Event(event.type, pos=(vx, vy), rel=(vrx, vry), buttons=event.buttons)
                mapped_events.append(mapped_event)
            else:
                mapped_events.append(event)

        # 2. 모든 입력을 가상 좌표 이벤트로 흘려보냄
        # 종료 확인 오버레이, 소리 설정 overlay 또는 인게임 설정(esc/m) 처리 포함
        if not quit_overlay.handle_events(mapped_events):
            if not settings_overlay.handle_events(mapped_events, farm_scene=scenes.get("farm")):
                for event in mapped_events:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                        audio.toggle_mute()
                current_scene_obj.handle_events(mapped_events)

        current_scene_obj.update(dt)
        settings_overlay.update(dt)

        # 3. 모든 그리기 연산은 800x600 가상 화면 버퍼에 수행
        current_scene_obj.draw(virtual_screen)
        
        # 좌상단 디버그 버전 표시 (회색 소형 텍스트)
        try:
            from core.assets import get_font
            font_ver = get_font(12)
            ver_surf = font_ver.render("v1.0.4.5", True, (120, 120, 120))
            virtual_screen.blit(ver_surf, (8, 6))
        except Exception:
            pass

        settings_overlay.draw(virtual_screen)
        quit_overlay.draw(virtual_screen)

        # 4. 가상 화면을 실제 물리 창 해상도로 스케일링 복사 (종횡비 유지 검은 띠 적용)
        scaled_screen = pygame.transform.scale(virtual_screen, (target_w, target_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled_screen, (offset_x, offset_y))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
