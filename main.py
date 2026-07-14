import os
import sys
import traceback

# 안드로이드 하드웨어/제스처 '뒤로가기' 버튼을 SDL 이 삼켜 앱을 곧장 종료해 버리지
# 않도록, pygame 이 임포트/초기화되기 '전에' 트랩 힌트를 켜 둔다. 이렇게 하면 뒤로가기가
# pygame.K_AC_BACK 키 이벤트로 우리 쪽에 전달돼 '한 단계 뒤로'로 쓸 수 있다.
# (데스크톱에서는 이 환경변수가 무시되므로 무해하다.)
os.environ.setdefault("SDL_ANDROID_TRAP_BACK_BUTTON", "1")

try:
    import game_main
    if __name__ == "__main__":
        game_main.main()
except Exception as e:
    tb = traceback.format_exc()
    # Write to crash log file in multiple locations (including user-accessible external storage via USB)
    paths_to_try = [
        f"/sdcard/Android/data/mongjung.nongwon.dreamfarm/files/crash.txt",
        f"/storage/emulated/0/Android/data/mongjung.nongwon.dreamfarm/files/crash.txt",
        f"/sdcard/DreamFarm_crash.txt",
        f"/storage/emulated/0/DreamFarm_crash.txt"
    ]
    if 'ANDROID_PRIVATE' in os.environ:
        paths_to_try.append(os.path.join(os.environ['ANDROID_PRIVATE'], 'crash.txt'))
        
    for path in paths_to_try:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(tb)
        except Exception:
            pass
            
    # Try to display using pygame
    try:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((800, 600))
        pygame.display.set_caption("DreamFarm - Crash Log")
        # Use default system font or a fallback monospace font
        font = pygame.font.SysFont("monospace", 15)
        
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or event.type == pygame.MOUSEBUTTONDOWN:
                    running = False
            
            screen.fill((30, 30, 30))
            y = 20
            # Draw header
            header = font.render("[DreamFarm Crash Log - Touch screen to exit]", True, (255, 255, 255))
            screen.blit(header, (20, y))
            y += 30
            
            for line in tb.split('\n'):
                line = line.replace('\t', '    ')
                # Render line
                text_surf = font.render(line, True, (255, 100, 100))
                screen.blit(text_surf, (20, y))
                y += 20
                if y > 580:
                    break
            pygame.display.flip()
            pygame.time.wait(100)
    except Exception:
        # Fallback to sys.stderr
        print(tb, file=sys.stderr)
    sys.exit(1)
