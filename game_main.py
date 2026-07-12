import pygame
import sys
import os
import math

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.platform import IS_ANDROID
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


def setup_window_icon():
    # 윈도우 창 아이콘 설정 (exe로 묶였을 때도 찾도록 resource_path 사용)
    try:
        from core.assets import resource_path
        icon_path = resource_path("logo.png")
        if os.path.exists(icon_path):
            raw_icon = pygame.image.load(icon_path).convert_alpha()
            # 원본 logo.png는 원형 그림 둘레에 투명 여백이 넓어, 작업표시줄에 넣으면
            # 다른 앱 아이콘보다 작아 보인다. 실제 그림의 경계만 잘라 정사각 캔버스에
            # 꽉 채워 넣으면 작업표시줄 칸을 다른 아이콘만큼 채운다.
            bb = raw_icon.get_bounding_rect(min_alpha=8)
            if bb.width > 0 and bb.height > 0:
                cropped = raw_icon.subsurface(bb).copy()
                side = max(bb.width, bb.height)
                canvas = pygame.Surface((side, side), pygame.SRCALPHA)
                canvas.blit(cropped, ((side - bb.width) // 2, (side - bb.height) // 2))
            else:
                canvas = raw_icon
            # 작업표시줄/제목표시줄은 아이콘을 32~48px로 줄여 쓴다. OS의 거친 축소를
            # 피하려고 미리 256px로 다듬어 넘긴다.
            icon_surf = pygame.transform.smoothscale(canvas, (256, 256))
            pygame.display.set_icon(icon_surf)
    except Exception:
        pass


def main():
    pygame.init()

    # 윈도우 작업표시줄 아이콘 대응 —
    # 파이썬/pygame 창은 기본적으로 작업표시줄에서 python.exe 아이콘으로 뜬다.
    # 프로세스에 고유한 AppUserModelID를 지정하면 윈도우가 이 창을 독립 앱으로 보고
    # set_icon()으로 넣은 아이콘을 작업표시줄에도 그대로 쓴다.
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mongjung.nongwon.game")
    except Exception:
        pass

    # 디스플레이 초기화 변수
    # 안드로이드는 창 개념이 없고 항상 전체화면이므로, 시작부터 전체화면 스케일 모드로 둔다.
    # (800x600 가상 캔버스를 기기 해상도에 4:3 레터박스로 맞춰 그린다.)
    is_fullscreen = IS_ANDROID
    current_nightmare = False
    screen = None
    offset_x, offset_y = 0, 0
    target_w, target_h = 800, 600
    
    def update_display_mode():
        nonlocal screen, current_nightmare, is_fullscreen, offset_x, offset_y, target_w, target_h
        current_nightmare = game_state.nightmare
        # 창 크기는 항상 800x600. 악몽 모드에서 960x720으로 키우면 픽셀 폰트가 1.2배로
        # 뭉개져 흐릿해졌다 → 크기는 그대로 두고 '검붉은 배경 테마'로만 악몽을 표현한다.
        w, h = 800, 600

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
    setup_window_icon()
        
    clock = pygame.time.Clock()
    
    from core.assets import init_sprites
    init_sprites()
    audio.init()

    # #14 Check for 2nd playthrough
    apply_second_run()

    # 가상 화면 800x600 버퍼 생성
    virtual_screen = pygame.Surface((800, 600))

    # 마우스 좌표 역계산(역배율 스케일링)을 위한 변환 함수 및 get_pos 재정의 (종횡비 보정 반영)
    def to_virtual_pos(pos):
        mx = pos[0] - offset_x
        my = pos[1] - offset_y
        vx = int(mx * 800.0 / target_w)
        vy = int(my * 600.0 / target_h)
        return max(0, min(799, vx)), max(0, min(599, vy))

    orig_get_pos = pygame.mouse.get_pos
    def mapped_get_pos():
        return to_virtual_pos(orig_get_pos())
    pygame.mouse.get_pos = mapped_get_pos

    BGM_BY_SCENE = {
        "title": "night", "crop_select": "night", "gallery": "night", 
        "name_input": "night", "intro": "night",
        "memory": None, "story_choice": "event", "father_day": None,
        "farm": "farm", "stage1": "event", "stage2": "farm",
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
        "title", "crop_select", "gallery", "name_input", "intro", "memory", "epiphany",
        "story_choice", "father_day", "stage1", "stage2", "stage3",
        "stage4", "star_connect", "ending",
    }

    # 씬 지연 초기화 (Lazy Initialization) 적용
    scenes = {}
    current_key = game_state.current_scene
    scenes[current_key] = SCENE_FACTORIES[current_key]()
    current_scene_obj = scenes[current_key]

    settings_overlay = SettingsOverlay()
    from core.quit_overlay import QuitOverlay
    quit_overlay = QuitOverlay()
    from core.dev_overlay import DevOverlay
    dev_overlay = DevOverlay()   # F9로 여는 개발자/테스트 모드

    # 전역 상태에 포커스/배속 플래그 초기화
    game_state.paused = False
    game_state.fast_forward = False
    fullscreen_cooldown = 0.0

    # 안드로이드 생명주기/뒤로가기 상수. 데스크톱 pygame-ce 에도 존재하나 발생하지 않으며,
    # 구버전 classic pygame 폴백을 대비해 getattr 로 안전하게 얻는다.
    APP_BG = getattr(pygame, "APP_WILLENTERBACKGROUND", None)
    APP_FG = getattr(pygame, "APP_DIDENTERFOREGROUND", None)
    KEY_BACK = getattr(pygame, "K_AC_BACK", None)
    app_backgrounded = False

    while game_state.running:
        dt = clock.tick(60) / 1000.0
        # dt가 튀는 것을 방지하기 위해 최대 0.1초로 클램핑
        dt = min(0.1, dt)
        game_state.play_time += dt

        if fullscreen_cooldown > 0:
            fullscreen_cooldown = max(0.0, fullscreen_cooldown - dt)

        target_scene = game_state.current_scene

        # 지옥 모드 진입/해제에 따른 동적 해상도 창 크기 재설정
        if game_state.nightmare != current_nightmare:
            update_display_mode()

        if target_scene != current_key:
            if target_scene == "intro":
                scenes["farm"] = SCENE_FACTORIES["farm"]()
            if target_scene in FRESH_ON_ENTER or target_scene not in scenes:
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
                if "farm" not in scenes:
                    scenes["farm"] = SCENE_FACTORIES["farm"]()
                save_system.restore(data, scenes["farm"])
                game_state.current_scene = "farm"
                current_scene_obj = scenes["farm"]
                current_key = "farm"
                # 지옥 모드 여부에 맞게 창 크기 즉시 갱신
                if game_state.nightmare != current_nightmare:
                    update_display_mode()
                audio.play_bgm("event" if game_state.nightmare else "farm")

        # 개발자 모드에서 작물을 바꾸면 밭을 새로 만들어 farm으로 이동
        if getattr(game_state, "dev_new_farm", False):
            game_state.dev_new_farm = False
            scenes["farm"] = SCENE_FACTORIES["farm"]()
            game_state.current_scene = "farm"
            current_scene_obj = scenes["farm"]
            current_key = "farm"
            target_scene = "farm"
            if game_state.nightmare != current_nightmare:
                update_display_mode()

        desired_bgm = BGM_BY_SCENE.get(target_scene)
        # 이스터에그/악몽: 악몽 모드가 켜져 있다면 밤 BGM(night)과 농장 밭 BGM(farm)을 타이틀 악몽 BGM인 'event'로 바꾼다.
        if game_state.nightmare and desired_bgm in ("night", "farm"):
            desired_bgm = "event"
        if desired_bgm:
            audio.play_bgm(desired_bgm)

        # Space key 홀드 상태 또는 배속 토글 버튼 활성화 상태에 따른 배속 전역 감지
        game_state.fast_forward = pygame.key.get_pressed()[pygame.K_SPACE] or getattr(game_state, "fast_forward_toggle", False)

        events = pygame.event.get()

        # --- 안드로이드 생명주기: 백그라운드 진입 시 오디오·렌더를 즉시 멈춘다 ---
        # (재생/그리기를 켠 채 백그라운드로 가면 복귀 시 크래시/멈춤이 알려져 있다.)
        for event in events:
            if APP_BG is not None and event.type == APP_BG:
                audio.pause_all()
                app_backgrounded = True
                # 밀려날 때 진행 중인 밭을 자동 저장(자동저장이 켜져 있으면)
                if current_key == "farm" and scenes.get("farm") is not None:
                    from core import save_system
                    if save_system.get_setting("autosave"):
                        try:
                            save_system.save_game(scenes["farm"])
                        except Exception:
                            pass
            elif APP_FG is not None and event.type == APP_FG:
                audio.resume_all()
                app_backgrounded = False
        if app_backgrounded:
            # GL 컨텍스트가 백업된 상태 → 그리기/flip 금지. 이벤트 큐만 돌리며 대기.
            pygame.time.wait(120)
            continue

        # 안드로이드 하드웨어 '뒤로가기'(K_AC_BACK)를 ESC 로 치환 →
        # 오버레이 닫기·뒤로가기·설정 열기 등 기존 ESC 로직을 그대로 재사용한다.
        if KEY_BACK is not None:
            events = [
                pygame.event.Event(e.type, key=pygame.K_ESCAPE, mod=0,
                                   unicode=("\x1b" if e.type == pygame.KEYDOWN else ""))
                if e.type in (pygame.KEYDOWN, pygame.KEYUP) and e.key == KEY_BACK else e
                for e in events
            ]

        # 1. F11 전체화면 감지 및 마우스 좌표 가상 해상도로 역배율 보정 (종횡비 고려)
        mapped_events = []
        for event in events:
            if event.type == pygame.QUIT:
                game_state.request_quit = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                update_display_mode()
                fullscreen_cooldown = 0.6  # 전체화면 시 포커스 감지 쿨타임 작동
            elif not IS_ANDROID and event.type == pygame.ACTIVEEVENT:
                # 윈도우 포커스 분실 감지 (gain이 0이고, 전체화면 쿨다운이 없을 때만 발동)
                # 안드로이드에서는 ACTIVEEVENT 가 부정확해 APP_* 생명주기 이벤트로 대체한다.
                if getattr(event, "gain", 1) == 0 and fullscreen_cooldown <= 0:
                    game_state.paused = True
            
            # 마우스 입력 좌표 역배율 보정 (레터박스/필러박스 여백 감산 및 가변 배율 적용)
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                vx, vy = to_virtual_pos(event.pos)
                mapped_event = pygame.event.Event(event.type, pos=(vx, vy), button=event.button)
                mapped_events.append(mapped_event)
            elif event.type == pygame.MOUSEMOTION:
                vx, vy = to_virtual_pos(event.pos)
                vrx = int(event.rel[0] * 800.0 / target_w)
                vry = int(event.rel[1] * 600.0 / target_h)
                mapped_event = pygame.event.Event(event.type, pos=(vx, vy), rel=(vrx, vry), buttons=event.buttons)
                mapped_events.append(mapped_event)
            else:
                mapped_events.append(event)

        # 2. 모든 입력을 가상 좌표 이벤트로 흘려보냄
        # 일시정지 상태일 때 이벤트 감지 분리 처리
        if game_state.paused:
            for event in mapped_events:
                # 마우스 클릭 혹은 임의의 키(ESC 등) 입력 시 해제
                if event.type in (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN):
                    game_state.paused = False
                    audio.play("click")
        else:
            # 배속 버튼 터치 선처리 (설정창이나 종료창이 닫혀 있을 때만 작동)
            if not game_state.request_quit and not settings_overlay.open:
                ff_btn = pygame.Rect(708, 27, 28, 28)
                filtered_events = []
                for event in mapped_events:
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and ff_btn.collidepoint(event.pos):
                        game_state.fast_forward_toggle = not getattr(game_state, "fast_forward_toggle", False)
                        audio.play("click")
                    else:
                        filtered_events.append(event)
                mapped_events = filtered_events

            # 종료 확인 오버레이, 소리 설정 overlay 또는 인게임 설정(esc/m) 처리 포함
            if not quit_overlay.handle_events(mapped_events):
                if not settings_overlay.handle_events(mapped_events, farm_scene=scenes.get("farm")) \
                        and not dev_overlay.handle_events(mapped_events, farm_scene=scenes.get("farm")):
                    for event in mapped_events:
                        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                            audio.toggle_mute()
                    # ESC로 설정 오버레이 열기 — 여기까지 왔다는 건 설정이 닫혀 있다는 뜻(열려 있으면
                    # settings_overlay가 위에서 소비함). 단, ESC를 '뒤로가기'로 쓰는 메뉴 화면은 예외.
                    esc_pressed = any(e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE
                                      for e in mapped_events)
                    if esc_pressed and current_key not in ("crop_select", "name_input"):
                        settings_overlay.open = True
                    else:
                        current_scene_obj.handle_events(mapped_events)

        if not game_state.paused:
            current_scene_obj.update(dt)
            settings_overlay.update(dt)
            from core import achievements
            achievements.update(dt)

        # 3. 모든 그리기 연산은 800x600 가상 화면 버퍼에 수행
        current_scene_obj.draw(virtual_screen)
        
        # 배속 토글 버튼 그리기 (설정창이나 종료창이 닫혀 있을 때만 활성화)
        if not game_state.request_quit and not settings_overlay.open:
            ff_btn = pygame.Rect(708, 27, 28, 28)
            hovered_ff = ff_btn.collidepoint(pygame.mouse.get_pos())
            ff_active = getattr(game_state, "fast_forward_toggle", False)
            bg_ff = (96, 120, 110) if ff_active else (60, 74, 74)
            if hovered_ff:
                from core.ui import mix_color
                bg_ff = mix_color(bg_ff, (250, 246, 231), 0.2)
            pygame.draw.rect(virtual_screen, bg_ff, ff_btn, border_radius=7)
            pygame.draw.rect(virtual_screen, (229, 192, 124), ff_btn, 1, border_radius=7)
            
            # 화살표 기호 '>>' 렌더링
            from core.assets import get_font
            font_ver = get_font(12)
            symbol = ">>" if ff_active else ">"
            text_surf = font_ver.render(symbol, True, (250, 246, 231))
            virtual_screen.blit(text_surf, (ff_btn.centerx - text_surf.get_width() // 2, ff_btn.centery - text_surf.get_height() // 2))
        
        # 좌상단 디버그 버전 표시 (회색 소형 텍스트) — core/version.py 한 곳에서 관리
        try:
            from core import save_system
            if save_system.get_setting("show_version"):
                from core.assets import get_font
                from core.version import display_version
                font_ver = get_font(12)
                ver_surf = font_ver.render(display_version(), True, (236, 224, 190))
                vbox = pygame.Rect(6, 4, ver_surf.get_width() + 12, ver_surf.get_height() + 6)
                vbg = pygame.Surface(vbox.size, pygame.SRCALPHA)
                vbg.fill((20, 24, 28, 200))
                pygame.draw.rect(vbg, (120, 130, 120, 200), vbg.get_rect(), 1, border_radius=5)
                virtual_screen.blit(vbg, vbox.topleft)
                virtual_screen.blit(ver_surf, (vbox.x + 6, vbox.y + 3))
        except Exception:
            pass

        settings_overlay.draw(virtual_screen)
        quit_overlay.draw(virtual_screen)
        dev_overlay.draw(virtual_screen)
        achievements.draw(virtual_screen)   # 업적 토스트는 항상 맨 위에

        # 창 포커스 분실 일시정지 오버레이 반사
        if game_state.paused:
            pause_veil = pygame.Surface((800, 600), pygame.SRCALPHA)
            pause_veil.fill((12, 14, 20, 195))
            pygame.draw.rect(pause_veil, (130, 105, 75, 230), (198, 248, 404, 104), 2, border_radius=12)
            from core.assets import get_font
            font_pause = get_font(23)
            font_sub = get_font(16)
            txt_pause = font_pause.render("게임이 일시정지되었습니다", True, (244, 236, 214))
            txt_sub = font_sub.render("화면을 클릭하거나 아무 키를 눌러 재개", True, (168, 150, 130))
            pause_veil.blit(txt_pause, (400 - txt_pause.get_width() // 2, 276))
            pause_veil.blit(txt_sub, (400 - txt_sub.get_width() // 2, 318))
            virtual_screen.blit(pause_veil, (0, 0))

        # 4. 가상 화면을 실제 물리 창 해상도로 스케일링 복사 (종횡비 유지 검은 띠 적용)
        scaled_screen = pygame.transform.scale(virtual_screen, (target_w, target_h))
        screen.fill((0, 0, 0))
        screen.blit(scaled_screen, (offset_x, offset_y))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
