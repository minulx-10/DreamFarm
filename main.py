import os
import sys
import traceback

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
