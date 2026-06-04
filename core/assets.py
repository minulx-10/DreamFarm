import pygame

BLACK = (13, 16, 20)
WHITE = (250, 246, 231)
DARK_GRAY = (42, 46, 48)
YELLOW = (245, 200, 88)
GREEN = (54, 142, 94)
BROWN = (132, 83, 48)
RED = (190, 70, 58)
BLUE = (72, 122, 170)
GOLD = (232, 178, 84)
GRAY = (142, 146, 138)
ORANGE = (232, 132, 58)

# Dream-farm palette
DIRT_COLOR = (136, 88, 56)
DIRT_DARK = (92, 60, 43)
DIRT_WET = (88, 72, 58)
GRASS_COLOR = (84, 148, 91)
GRASS_DARK = (48, 104, 73)
WOOD_COLOR = (177, 123, 72)
WOOD_DARK = (75, 57, 45)
WOOD_LIGHT = (238, 201, 137)
TEXT_BROWN = (75, 52, 34)
TEXT_DARK = (38, 35, 30)
TEXT_MUTED = (102, 91, 75)
PANEL_PALE = (248, 232, 196)
PANEL_WARM = (255, 242, 213)
PANEL_DEEP = (55, 61, 58)
PANEL_EDGE = (121, 94, 68)
ACCENT_BLUE = (74, 131, 151)
ACCENT_MINT = (104, 164, 118)
ACCENT_CORAL = (213, 104, 72)

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
        'S': (218,164,112,255), # Skin
        's': (172,112,76,255),  # Skin shade
        'N': (66,92,92,255),    # Workwear
        'n': (42,58,62,255),    # Workwear shade
        'M': (188,198,194,255), # Metal light
        'm': (108,124,124,255), # Metal shade
        'Y': (238,190,92,255),  # Warm accent
        'y': (178,132,70,255),  # Warm accent shade
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
...XX....
..XggX...
.XgGGgX..
XgGYYGgX.
XgGGGGgX.
.XgGGgX..
..XgXgX..
.X..X..X.
''', 5)
    dad_path = os.path.join(os.path.dirname(__file__), "dad.png")
    loaded_dad = False
    if os.path.exists(dad_path):
        try:
            dad_img = pygame.image.load(dad_path).convert_alpha()
            sprites['dad'] = pygame.transform.scale(dad_img, (160, 160))
            loaded_dad = True
        except Exception as e:
            print("Failed to load custom dad sprite:", e)

    if not loaded_dad:
        sprites['dad'] = create_sprite_from_string('''
....YYYY....
...YyyyyY...
..YYSSSSYY..
..XSSSSSSX..
..XSXSSXSX..
..XSSSSSSX..
...XssssX...
..XXNNNNXX..
.XNNNNNNNNX.
.XNYNNNNYNX.
.XNNNNNNNNX.
..XNnnnnNX..
...XNNNNX...
...XBBBX....
..XB...BX...
..XB...BX...
..XX...XX...
''', 7)
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
...XXXX...
..XMMMMX..
.XXXXXXXX.
.XMmmMMmX.
.XMmMMmmX.
.XMmmMMmX.
.XMmMMmmX.
.XMmmMMmX.
..XmmmmX..
...XXXX...
''', 12)
    sprites['watering_can'] = create_sprite_from_string('''
......XXXXXX.....
....XX......X....
...X..X.....X....
..X...XXXXXX.XXX.
.X....X....X.X..X
X.....X....X.X..X
X.....X....X.X..X
.X....XXXXXX.XX..
..X...X....X.....
...XXX......X....
''', 3)

    # 밭 이미지 에셋 불러오기 (여백 크롭 및 362x318 리사이징)
    field_bed_path = os.path.join(os.path.dirname(__file__), "field_bed.jpg")
    if os.path.exists(field_bed_path):
        try:
            raw_img = pygame.image.load(field_bed_path).convert_alpha()
            cropped = raw_img.subsurface(pygame.Rect(59, 74, 904, 763))
            sprites['field_bed'] = pygame.transform.scale(cropped, (362, 318))
        except Exception as e:
            print("Failed to load field_bed image:", e)

def _mix_color(a, b, ratio):
    return (
        int(a[0] + (b[0] - a[0]) * ratio),
        int(a[1] + (b[1] - a[1]) * ratio),
        int(a[2] + (b[2] - a[2]) * ratio),
    )


def draw_tiled_background(screen, w, h, grass=None, grass_dk=None, dirt=None, dirt_dk=None):
    gc = grass or (60, 95, 85)     # Twilight teal-green grass
    gd = grass_dk or (45, 75, 65)  # Dark grass shadow
    dc = dirt or DIRT_COLOR
    dd = dirt_dk or DIRT_DARK

    sky_top = (45, 24, 78)       # Twilight purple sky
    sky_bottom = (245, 125, 65)  # Twilight orange sunset
    for y in range(h):
        ratio = min(1, y / max(1, h * 0.62))
        pygame.draw.line(screen, _mix_color(sky_top, sky_bottom, ratio), (0, y), (w, y))

    # Glowing twilight sun
    pygame.draw.circle(screen, (245, 140, 70), (670, 82), 42)
    pygame.draw.circle(screen, (255, 210, 120), (670, 82), 30)

    horizon = 166
    # Misty twilight mountains
    pygame.draw.polygon(screen, (75, 45, 90), [(0, horizon + 28), (110, 118), (260, horizon + 18), (440, 112), (610, horizon + 26), (800, 126), (800, h), (0, h)])
    pygame.draw.polygon(screen, (50, 75, 80), [(0, horizon + 56), (160, 148), (340, horizon + 48), (520, 142), (800, horizon + 54), (800, h), (0, h)])

    pygame.draw.rect(screen, gc, (0, horizon, w, h - horizon))
    for y in range(horizon, h, 34):
        c = _mix_color(gc, gd, 0.35 if (y // 34) % 2 == 0 else 0.55)
        pygame.draw.line(screen, c, (0, y), (w, y + 18), 2)

    for x in range(0, w, 44):
        for y in range(horizon + 18, h, 70):
            if (x + y) % 3 == 0:
                pygame.draw.line(screen, gd, (x + 10, y + 8), (x + 18, y + 2), 2)
                pygame.draw.line(screen, gd, (x + 17, y + 3), (x + 22, y + 11), 2)

    # Farming soil bed
    dirt_rect = pygame.Rect(38, 112, w - 76, h - 246)
    pygame.draw.rect(screen, dd, dirt_rect.move(0, 6), border_radius=12)
    pygame.draw.rect(screen, dc, dirt_rect, border_radius=12)
    pygame.draw.rect(screen, _mix_color(dc, WHITE, 0.18), dirt_rect.inflate(-14, -14), 2, border_radius=9)
    pygame.draw.rect(screen, dd, dirt_rect, 3, border_radius=12)

    # 3D Horizontal farming ridges (furrows) instead of grid lines
    for y in range(dirt_rect.y + 36, dirt_rect.bottom - 20, 42):
        # Ridge shadow
        pygame.draw.rect(screen, dd, (dirt_rect.x + 16, y, dirt_rect.w - 32, 8), border_radius=3)
        # Ridge highlight (sunset glow reflection)
        pygame.draw.rect(screen, _mix_color(dc, (255, 200, 150), 0.15), (dirt_rect.x + 16, y - 4, dirt_rect.w - 32, 4), border_radius=2)


def draw_weather_icon(screen, weather, x, y, size=20):
    import math
    cx, cy = x + size // 2, y + size // 2
    r = size // 2
    if weather == '맑음':
        pygame.draw.circle(screen, (255, 210, 60), (cx, cy), r - 2)
        pygame.draw.circle(screen, (240, 180, 30), (cx, cy), r - 2, 2)
        for angle in range(0, 360, 45):
            dx = int(math.cos(math.radians(angle)) * (r + 1))
            dy = int(math.sin(math.radians(angle)) * (r + 1))
            pygame.draw.line(screen, (255, 200, 50), (cx + dx, cy + dy),
                             (cx + int(dx * 1.4), cy + int(dy * 1.4)), 2)
    elif weather == '흐림':
        pygame.draw.ellipse(screen, (180, 180, 190), (x, y + 4, size, size - 6))
        pygame.draw.ellipse(screen, (160, 160, 170), (x + 4, y, size - 6, size - 4))
        pygame.draw.ellipse(screen, (200, 200, 210), (x + 2, y + 2, size - 2, size - 6))
    elif weather == '비':
        pygame.draw.ellipse(screen, (140, 150, 165), (x, y, size, size // 2))
        for i in range(3):
            lx = x + 4 + i * (size // 3)
            pygame.draw.line(screen, (100, 160, 230), (lx, y + size // 2 + 2),
                             (lx - 2, y + size - 2), 2)
    elif weather == '가뭄':
        pygame.draw.circle(screen, (230, 140, 40), (cx, cy - 2), r - 3)
        pygame.draw.circle(screen, (200, 100, 20), (cx, cy - 2), r - 3, 2)
        for i in range(3):
            wx = x + 2 + i * (size // 3)
            pygame.draw.line(screen, (180, 80, 20), (wx, y + size - 5),
                             (wx + 4, y + size - 2), 2)
    elif weather == '강풍':
        for i in range(3):
            ly = y + 3 + i * 6
            pygame.draw.arc(screen, (120, 150, 130),
                            (x, ly, size - 4, 8), 0.3, 2.8, 2)
