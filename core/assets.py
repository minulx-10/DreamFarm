import pygame

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
DARK_GRAY = (40, 40, 40)
YELLOW = (255, 215, 0)
GREEN = (34, 139, 34)
BROWN = (139, 69, 19)
RED = (200, 50, 50)
BLUE = (50, 50, 200)
GOLD = (235, 190, 70)
GRAY = (150, 150, 150)
ORANGE = (255, 150, 50)

# Stardew palette
DIRT_COLOR = (145, 95, 60)
DIRT_DARK = (120, 75, 45)
DIRT_WET = (100, 60, 35)
GRASS_COLOR = (90, 160, 70)
GRASS_DARK = (70, 130, 50)
WOOD_COLOR = (220, 170, 110)
WOOD_DARK = (170, 120, 70)
WOOD_LIGHT = (250, 210, 150)
TEXT_BROWN = (60, 40, 20)
TEXT_DARK = (35, 24, 14)
TEXT_MUTED = (95, 72, 48)
PANEL_PALE = (242, 200, 138)

import os
import urllib.request

FONT_PATH = os.path.join(os.path.dirname(__file__), "Galmuri11.ttf")
FONT_URL = "https://cdn.jsdelivr.net/npm/galmuri/dist/Galmuri11.ttf"

fonts = {}

def get_font(size):
    if size not in fonts:
        if not os.path.exists(FONT_PATH):
            try:
                print("Downloading Galmuri11 pixel font...")
                req = urllib.request.Request(FONT_URL, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as response, open(FONT_PATH, 'wb') as out_file:
                    out_file.write(response.read())
                print("Download complete!")
            except Exception as e:
                print("Failed to download font, falling back to system font:", e)
                try:
                    fonts[size] = pygame.font.SysFont("malgungothic", size)
                except:
                    fonts[size] = pygame.font.Font(None, size)
                return fonts[size]
                
        try:
            fonts[size] = pygame.font.Font(FONT_PATH, size)
        except:
            try:
                fonts[size] = pygame.font.SysFont("malgungothic", size)
            except:
                fonts[size] = pygame.font.Font(None, size)
    return fonts[size]

def create_sprite_from_string(sprite_str, scale=4):
    lines = sprite_str.strip().split('\n')
    lines = [line for line in lines if line] # filter empty lines
    h = len(lines)
    w = max(len(line) for line in lines) if lines else 0
    surf = pygame.Surface((w * scale, h * scale), pygame.SRCALPHA)
    
    colors = {
        '.': (0,0,0,0),
        'X': (40,40,40,255),    # Outline
        'G': (100,220,100,255), # Bright Green
        'g': (50,150,50,255),   # Dark Green
        'O': (255,160,50,255),  # Orange
        'o': (200,100,20,255),  # Dark Orange
        'R': (180,180,180,255), # Rock light
        'r': (120,120,120,255), # Rock dark
        'B': (150,100,60,255),  # Brown
        'b': (100,60,30,255),   # Dark Brown
    }
    
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char in colors and colors[char][3] > 0:
                pygame.draw.rect(surf, colors[char], (x*scale, y*scale, scale, scale))
    return surf

sprites = {}
def init_sprites():
    if 'seed' in sprites: return
    sprites['seed'] = create_sprite_from_string('''
...XX...
..XooX..
.XoOoOX.
.XoOoOX.
..XooX..
...XX...
''', 5)
    sprites['weed'] = create_sprite_from_string('''
....X....
..X.X.X..
.XGgGgGX.
..XgGgX..
.XGgXgGX.
...XgX...
...XgX...
..XgXgX..
''', 5)
    sprites['rock'] = create_sprite_from_string('''
..XXXX..
.XRRRRX.
XRRrrRRX
XRrrrrrX
XrrrrrrX
.XXXXXX.
''', 5)
    sprites['leaf'] = create_sprite_from_string('''
....XX..
..XXggX.
.XggbggX
XgbbbbgX
Xgb..bgX
.X....X.
''', 5)
    sprites['sprout1'] = create_sprite_from_string('''
..X..
.XGX.
..X..
''', 6)
    sprites['sprout2'] = create_sprite_from_string('''
...X...
..XGX..
.XgGgX.
...X...
''', 6)
    sprites['sprout3'] = create_sprite_from_string('''
...X.X...
..XGXGX..
.XGGGGGX.
..XgXgX..
...XgX...
''', 6)
    sprites['sprout4'] = create_sprite_from_string('''
...X.X...
..XGXGX..
.XGGGGGX.
XgGGGGGgX
.XgXgXgX.
..XXXXX..
''', 6)
    sprites['carrot'] = create_sprite_from_string('''
...X.X...
..XGXGX..
.XGGGGGX.
..XgXgX..
.XXXXXXX.
XOOOOOOOX
XOOOOOOOX
XoOOOOOoX
.XOOOOOX.
.XoOOOoX.
..XOOOX..
..XoOoX..
...XXX...
...XoX...
....X....
''', 5)
    sprites['bug'] = create_sprite_from_string('''
..X..X..
.XoXXoX.
XooooooX
.XooooX.
X.XXXX.X
''', 6)
    sprites['dad'] = create_sprite_from_string('''
..XXXXX..
.XrrrrrX.
XrrrrrrrX
XWWWWWWWX
XW.W.W.WX
XWWWWWWWX
.XWWWWWX.
..XXXXX..
.XXXXXXX.
XX.XXX.XX
XX.XXX.XX
...XXX...
...X.X...
...X.X...
''', 10)
    sprites['basket'] = create_sprite_from_string('''
..XXXXXX..
.XBBBBBBX.
XbBBbbBBbX
XBBbbbbBBX
XBBbbbbBBX
XbBBbbBBbX
.XBBBBBBX.
..XXXXXX..
''', 15)
    sprites['trashcan'] = create_sprite_from_string('''
..XXXXXX..
.XRRRRRRX.
XrrrrrrrrX
XRRRrrRRRX
XRRRrrRRRX
XRRRrrRRRX
.XRRRRRRX.
..XXXXXX..
''', 15)

def draw_tiled_background(screen, w, h):
    screen.fill(GRASS_COLOR)
    for y in range(0, h, 40):
        for x in range(0, w, 40):
            if (x+y) % 120 == 0:
                pygame.draw.rect(screen, GRASS_DARK, (x+10, y+10, 8, 4))
                pygame.draw.rect(screen, GRASS_DARK, (x+14, y+6, 4, 8))

    dirt_rect = pygame.Rect(50, 80, w - 100, h - 250)
    pygame.draw.rect(screen, DIRT_COLOR, dirt_rect)
    pygame.draw.rect(screen, DIRT_DARK, dirt_rect, 6)
    
    for y in range(80, h - 170, 40):
        pygame.draw.line(screen, DIRT_DARK, (50, y), (w-50, y), 2)
    for x in range(50, w - 50, 40):
        pygame.draw.line(screen, DIRT_DARK, (x, 80), (x, h-170), 2)
