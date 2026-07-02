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
import sys
import urllib.request


def resource_path(rel):
    """core/ 안의 데이터 파일 경로를 돌려준다.
    PyInstaller로 묶인 exe에서는 _MEIPASS 임시 폴더 아래를 가리키게 한다."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "core", rel)
    return os.path.join(os.path.dirname(__file__), rel)


FONT_PATH = resource_path("Galmuri11.ttf")
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
        'X': (38,32,34,255),    # Outline (warm near-black)
        '#': (22,18,22,255),    # Deepest outline / contact shadow
        'L': (158,228,128,255), # Light leaf green (highlight)
        'G': (96,200,96,255),   # Bright Green
        'g': (52,150,64,255),   # Dark Green
        'e': (32,104,54,255),   # Deepest green (shadow)
        'w': (150,162,72,255),  # Sickly weed yellow-green
        'H': (255,206,128,255), # Carrot highlight
        'O': (250,150,52,255),  # Orange
        'o': (214,104,30,255),  # Dark Orange
        'q': (160,68,22,255),   # Deepest orange shadow
        'k': (66,58,52,255),    # Beetle dark
        'K': (104,92,78,255),   # Beetle mid
        'i': (212,74,62,255),   # Beetle eye (red)
        'R': (180,180,180,255), # Rock light
        'r': (120,120,120,255), # Rock dark
        'B': (150,100,60,255),  # Brown
        'b': (100,60,30,255),   # Dark Brown
        'S': (218,164,112,255), # Skin
        's': (172,112,76,255),  # Skin shade
        'N': (66,92,92,255),    # Workwear
        'n': (42,58,62,255),    # Workwear shade
        'W': (230,238,234,255), # Metal highlight (shine)
        'M': (180,192,190,255), # Metal light
        'm': (108,124,124,255), # Metal shade
        'Y': (238,190,92,255),  # Warm accent
        'y': (178,132,70,255),  # Warm accent shade
        'd': (87, 51, 25, 255),   # Pit base brown
        'D': (56, 33, 15, 255),   # Pit dark shadow
        'l': (110, 65, 30, 255),  # Pit light brown speckle
    }
    
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char in colors and colors[char][3] > 0:
                pygame.draw.rect(surf, colors[char], (x*scale, y*scale, scale, scale))
    return surf


sprites = {}
def init_sprites():
    if 'seed' in sprites: return
    sprites['dirt_patch'] = create_sprite_from_string('''
...DDD...
..DdddD..
.DddlddD.
DdddddldD
DddlddddD
.DdddddD.
..DddD...
...DD....
''', 3)
    sprites['mini_carrot'] = create_sprite_from_string('''
LGL
gGg
.X.
HOo
HOo
HOo
.oX
.qX
''', 2)
    sprites['seed'] = create_sprite_from_string('''
...XX...
..XooX..
.XoOoOX.
.XoOoOX.
..XooX..
...XX...
''', 5)
    sprites['weed'] = create_sprite_from_string('''
..w.X.w..
.XwGwGwX.
X.XGgGX.X
..XGgGX..
.XwgXgwX.
...XeX...
..XgegX..
.Xg.X.gX.
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
.LGL.
.XGX.
..X..
''', 6)
    sprites['sprout2'] = create_sprite_from_string('''
..LGL..
.LGgGL.
.XGgGX.
...X...
''', 6)
    sprites['sprout3'] = create_sprite_from_string('''
..L.L.L..
.LGgGgGL.
XLGGgGGLX
.XGgGgGX.
...XeX...
''', 6)
    sprites['sprout4'] = create_sprite_from_string('''
..L.X.L..
.LGgGgGL.
XLGGgGGLX
XLGgGgGLX
.XGgGgGX.
..XXeXX..
''', 6)
    sprites['carrot'] = create_sprite_from_string('''
...LGL...
..LGGGL..
.LGgGgGL.
.XGgGgGX.
..XGGGX..
.XHOOOoX.
XHOOOOOoX
XHOOOOOoX
XHOOOOOoX
.XHOOOoX.
.XHOOooX.
..XOOoX..
..XOooX..
...XOoX..
...XoqX..
....XX...
''', 5)
    sprites['bug'] = create_sprite_from_string('''
.X....X.
..XkkX..
.XkKKkX.
XkKiiKkX
XkKKKKkX
.XkKKkX.
X.XkkX.X
.XX..XX.
''', 5)
    dad_path = resource_path("dad.png")
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
    # 밭 정리(stage1) 두 통 — 게임의 다른 스프라이트(돌멩이·당근 등)와 같은 납작 픽셀 방식.
    # 한 모양(좌우대칭)을 색만 바꿔: 왼쪽 = 나무색 통(씨앗), 오른쪽 = 회색 통(방해물).
    _BIN_ART = '''
..XXXXXXXXXXXX..
.XYYYYYYYYYYYYX.
XYbDDDDDDDDDDbYX
.XbBBBBBBBBBBbX.
.XbBBBBBBBBBBbX.
.XbBlBBBBBBlBbX.
.XbBBBBBBBBBBbX.
..XbBBBBBBBBbX..
..XbBlBBBBlBbX..
..XbBBBBBBBBbX..
...XbBBBBBBbX...
...XbbBBBBbbX...
....XbbbbbbX....
....XXXXXXXX....
'''
    sprites['basket'] = create_sprite_from_string(_BIN_ART, 6)
    sprites['trashcan'] = create_sprite_from_string(
        _BIN_ART.translate(str.maketrans({'Y': 'W', 'B': 'M', 'b': 'm', 'D': '#', 'l': 'm'})), 6)
    sprites['watering_can'] = create_sprite_from_string('''
....XXXXX.........
....X...X.....XXX.
....X...X....XXmX.
...XXXXXXX..XXmMX.
..XWMMMMMmXXmMMMX.
..XWWMMMMMMMMMMMX.
..XWMMMMMMMMMMMmX.
..XWMMMMMMMMMMMmX.
..XMMMMMMMMMMMmmX.
..XMMMMMMMMMMmmmX.
..XmMMMMMMMMmmmX..
...XmMMMMMMmmmX...
....XmmmmmmmX.....
.....XXXXXXX......
''', 5)

    # 밭 이미지 에셋 불러오기 (여백 크롭 및 362x318 리사이징)
    field_bed_path = resource_path("field_bed.jpg")
    if os.path.exists(field_bed_path):
        try:
            raw_img = pygame.image.load(field_bed_path).convert_alpha()
            cropped = raw_img.subsurface(pygame.Rect(59, 74, 904, 763))
            sprites['field_bed'] = pygame.transform.scale(cropped, (362, 318))

            # 4 모퉁이의 흰색/베이지색 여백 픽셀을 투명 처리하여 둥글게 마감
            w, h = 362, 318
            for cx, cy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
                dx_dir = 1 if cx == 0 else -1
                dy_dir = 1 if cy == 0 else -1
                for dy in range(16):
                    for dx in range(16):
                        px = cx + dx * dx_dir
                        py = cy + dy * dy_dir
                        if 0 <= px < w and 0 <= py < h:
                            color = sprites['field_bed'].get_at((px, py))
                            if color.r > 200 and color.g > 195 and color.b > 170:
                                sprites['field_bed'].set_at((px, py), (0, 0, 0, 0))
        except Exception as e:
            print("Failed to load field_bed image:", e)

def _mix_color(a, b, ratio):
    return (
        int(a[0] + (b[0] - a[0]) * ratio),
        int(a[1] + (b[1] - a[1]) * ratio),
        int(a[2] + (b[2] - a[2]) * ratio),
    )


# 황혼 하늘 다단 그라데이션 — 위에서 지평선으로 갈수록 남보라→자주→장미→노을빛
_SKY_STOPS = [
    (0.00, (30, 20, 56)),    # 깊은 남보라 (천정)
    (0.32, (66, 36, 92)),    # 보랏빛
    (0.58, (150, 66, 104)),  # 장미빛
    (0.82, (232, 126, 86)),  # 노을 주황
    (1.00, (252, 178, 116)), # 지평선 따뜻한 빛
]

# 악)몽중농원 검붉은 하늘 그라데이션
_NIGHTMARE_SKY_STOPS = [
    (0.00, (0, 0, 0)),        # 검은색 (천정)
    (0.35, (40, 5, 5)),       # 매우 어두운 붉은색
    (0.70, (110, 15, 15)),    # 검붉은색
    (1.00, (160, 20, 20)),    # 피빛 빨간색 (지평선)
]

# 별·구름은 매 프레임 같은 자리에 있어야 깜빡이지 않으므로 고정 배치
_STARS = [(58, 26, 2), (124, 52, 1), (208, 20, 2), (332, 44, 1), (96, 92, 1),
          (470, 28, 1), (250, 70, 2), (150, 130, 1), (560, 22, 1), (40, 120, 1),
          (412, 104, 1), (300, 16, 1), (90, 56, 1)]
_CLOUDS = [(150, 92, 132, 22), (520, 64, 168, 28), (350, 126, 96, 16), (60, 138, 80, 14)]
# 흙바닥 알갱이 텍스처 — 고정 배치 (dirt_rect 기준 상대좌표)
import random as _random
_speck_rng = _random.Random(7)
_SOIL_SPECKS = [(_speck_rng.randint(18, 700), _speck_rng.randint(18, 330), _speck_rng.choice([2, 2, 3]))
                for _ in range(48)]


def _sky_color(t):
    from core.game_state import game_state
    if game_state.nightmare:
        for i in range(len(_NIGHTMARE_SKY_STOPS) - 1):
            t0, c0 = _NIGHTMARE_SKY_STOPS[i]
            t1, c1 = _NIGHTMARE_SKY_STOPS[i + 1]
            if t <= t1:
                return _mix_color(c0, c1, (t - t0) / max(1e-6, t1 - t0))
        return _NIGHTMARE_SKY_STOPS[-1][1]
    else:
        for i in range(len(_SKY_STOPS) - 1):
            t0, c0 = _SKY_STOPS[i]
            t1, c1 = _SKY_STOPS[i + 1]
            if t <= t1:
                return _mix_color(c0, c1, (t - t0) / max(1e-6, t1 - t0))
        return _SKY_STOPS[-1][1]


def draw_tiled_background(screen, w, h, grass=None, grass_dk=None, dirt=None, dirt_dk=None):
    from core.game_state import game_state
    if game_state.nightmare:
        gc = (34, 16, 16)      # Charcoal/dark red grass
        gd = (18, 8, 8)        # Even darker grass shadow
        dc = (54, 20, 20)      # Demonic soil
        dd = (32, 10, 10)      # Dark demonic soil shadow
    else:
        gc = grass or (70, 128, 96)    # Twilight teal-green grass
        gd = grass_dk or (42, 88, 64)  # Dark grass shadow
        dc = dirt or DIRT_COLOR
        dd = dirt_dk or DIRT_DARK
    horizon = 166

    # --- 하늘: 다단 황혼 그라데이션 ---
    for y in range(horizon):
        pygame.draw.line(screen, _sky_color(y / horizon), (0, y), (w, y))

    # --- 별 (윗하늘, 태양에서 먼 쪽일수록 또렷하게) ---
    for sx, sy, sb in _STARS:
        if sx < 540 or sy > 110:
            tw = 200 + sb * 22
            # 악몽 모드에서는 붉은 빛 별로 변경
            col = (min(255, tw), 60, 60) if game_state.nightmare else (min(255, tw), min(255, tw), 210)
            pygame.draw.circle(screen, col, (sx, sy), sb)

    # --- 태양 + 부드러운 블룸 ---
    sun_x, sun_y = 640, 78
    bloom = pygame.Surface((260, 260), pygame.SRCALPHA)
    for r in range(126, 0, -7):
        a = int(54 * (1.0 - r / 126.0))
        glow_c = (180, 20, 20, a) if game_state.nightmare else (255, 188, 120, a)
        pygame.draw.circle(bloom, glow_c, (130, 130), r)
    screen.blit(bloom, (sun_x - 130, sun_y - 130))
    if game_state.nightmare:
        pygame.draw.circle(screen, (30, 0, 0), (sun_x, sun_y), 40)
        pygame.draw.circle(screen, (90, 10, 10), (sun_x, sun_y), 29)
        pygame.draw.circle(screen, (150, 15, 15), (sun_x, sun_y), 15)
    else:
        pygame.draw.circle(screen, (255, 152, 86), (sun_x, sun_y), 40)
        pygame.draw.circle(screen, (255, 206, 142), (sun_x, sun_y), 29)
        pygame.draw.circle(screen, (255, 240, 206), (sun_x, sun_y), 15)

    # --- 노을 구름 (반투명, 빛을 받은 아랫면이 환하게) ---
    for cx, cy, cw, ch in _CLOUDS:
        cloud = pygame.Surface((cw, ch * 2), pygame.SRCALPHA)
        cloud_c1 = (60, 20, 20, 120) if game_state.nightmare else (90, 52, 84, 120)
        cloud_c2 = (140, 30, 30, 110) if game_state.nightmare else (236, 158, 120, 110)
        pygame.draw.ellipse(cloud, cloud_c1, (0, 0, cw, ch))
        pygame.draw.ellipse(cloud, cloud_c2, (cw * 0.18, ch * 0.5, cw * 0.7, ch))
        screen.blit(cloud, (cx - cw // 2, cy - ch // 2))

    # --- 안개 낀 산 3겹 (멀수록 옅고 푸르게) ---
    if game_state.nightmare:
        m1 = (48, 10, 10)
        m2 = (34, 6, 6)
        m3 = (20, 3, 3)
    else:
        m1 = (108, 74, 116)
        m2 = (78, 52, 98)
        m3 = (46, 70, 78)
    pygame.draw.polygon(screen, m1, [(0, horizon - 6), (140, 96), (300, horizon - 14), (470, 92), (650, horizon - 4), (800, 104), (800, horizon + 10), (0, horizon + 10)])
    pygame.draw.polygon(screen, m2, [(0, horizon + 22), (110, 116), (260, horizon + 12), (440, 108), (610, horizon + 20), (800, 122), (800, h), (0, h)])
    pygame.draw.polygon(screen, m3, [(0, horizon + 52), (160, 146), (340, horizon + 44), (520, 138), (800, horizon + 50), (800, h), (0, h)])

    # --- 지평선 햇무리 (따뜻한 가로 빛띠) ---
    haze = pygame.Surface((w, 40), pygame.SRCALPHA)
    for i in range(20):
        a = int(70 * (1 - abs(i - 10) / 10))
        col = (180, 20, 20, a) if game_state.nightmare else (255, 196, 140, a)
        pygame.draw.line(haze, col, (0, i * 2), (w, i * 2))
    screen.blit(haze, (0, horizon - 20))

    # --- 잔디: 세로 그라데이션 + 결 ---
    for i in range(h - horizon):
        c = _mix_color(_mix_color(gc, (255, 200, 150) if not game_state.nightmare else (100, 40, 40), 0.12), gd, min(1.0, i / 150.0))
        pygame.draw.line(screen, c, (0, horizon + i), (w, horizon + i))
    for y in range(horizon, h, 34):
        c = _mix_color(gc, gd, 0.30 if (y // 34) % 2 == 0 else 0.50)
        pygame.draw.line(screen, c, (0, y), (w, y + 16), 2)

    for x in range(0, w, 44):
        for y in range(horizon + 18, h, 70):
            if (x + y) % 3 == 0:
                pygame.draw.line(screen, gd, (x + 10, y + 8), (x + 18, y + 2), 2)
                pygame.draw.line(screen, gd, (x + 17, y + 3), (x + 22, y + 11), 2)

    # --- 텃밭 흙바닥: 나무 테두리 + 결 고운 흙 + 빛·그늘 밴드 + 입체 이랑 ---
    dirt_rect = pygame.Rect(38, 112, w - 76, h - 246)
    # 나무 테두리
    frame = dirt_rect.inflate(12, 12)
    border_c1 = (40, 15, 15) if game_state.nightmare else (52, 36, 25)
    border_c2 = (100, 30, 30) if game_state.nightmare else (122, 86, 53)
    border_c3 = (130, 45, 45) if game_state.nightmare else (156, 114, 74)
    pygame.draw.rect(screen, border_c1, frame.move(0, 6), border_radius=15)
    pygame.draw.rect(screen, border_c2, frame, border_radius=15)
    pygame.draw.rect(screen, border_c3, frame, 2, border_radius=15)
    # 흙 바닥
    pygame.draw.rect(screen, dd, dirt_rect.move(0, 4), border_radius=12)
    pygame.draw.rect(screen, dc, dirt_rect, border_radius=12)
    # 위쪽 빛 밴드 / 아래쪽 그늘 밴드로 깊이감
    top_band = pygame.Surface((dirt_rect.w, 64), pygame.SRCALPHA)
    for i in range(64):
        top_band.fill((255, 205, 150, int(58 * (1 - i / 64))) if not game_state.nightmare else (200, 50, 50, int(58 * (1 - i / 64))), (0, i, dirt_rect.w, 1))
    screen.blit(top_band, (dirt_rect.x, dirt_rect.y))
    bot_band = pygame.Surface((dirt_rect.w, 90), pygame.SRCALPHA)
    for i in range(90):
        bot_band.fill((26, 16, 10, int(72 * (i / 90))) if not game_state.nightmare else (20, 5, 5, int(72 * (i / 90))), (0, i, dirt_rect.w, 1))
    screen.blit(bot_band, (dirt_rect.x, dirt_rect.bottom - 90))
    # 입체 이랑 (어두운 고랑 + 윗면 노을 하이라이트)
    for y in range(dirt_rect.y + 30, dirt_rect.bottom - 16, 40):
        pygame.draw.rect(screen, _mix_color(dd, BLACK, 0.20), (dirt_rect.x + 14, y + 6, dirt_rect.w - 28, 6), border_radius=3)
        pygame.draw.rect(screen, _mix_color(dc, (255, 205, 150) if not game_state.nightmare else (200, 80, 80), 0.24), (dirt_rect.x + 14, y, dirt_rect.w - 28, 4), border_radius=2)
    # 흙 알갱이 텍스처
    speck = _mix_color(dc, dd, 0.65)
    for sx_, sy_, ss in _SOIL_SPECKS:
        pygame.draw.rect(screen, speck, (dirt_rect.x + sx_, dirt_rect.y + sy_, ss, ss))
    pygame.draw.rect(screen, _mix_color(dd, BLACK, 0.10), dirt_rect, 3, border_radius=12)


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
