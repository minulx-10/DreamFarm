import pygame

# 색은 공용 팔레트(core/palette.py)를 단일 소스로 쓴다. 여기서 re-export 해 기존
# `from core.assets import GOLD, TEXT_DARK ...` 임포트를 그대로 유지한다.
from core.palette import *  # noqa: F401,F403
# 곡선 없음: 픽셀 챔퍼 사각형·픽셀 원 프리미티브(ui 와 공유, 순환참조 방지 위해 별도 모듈)
from core.pixelfx import (pixel_rect, pixel_disc, pixelate, glow_sprite, blit_glow,
                          CHAMFER, CHAMFER_SM)

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


class _I18nFont:
    """폰트 래퍼 — render()/size() 시 문자열을 현재 언어로 번역해 그린다.

    로직은 원문(한국어)을 그대로 쓰고 '표시'만 번역되도록, 렌더 계층에서만 개입한다.
    render/size 외의 메서드(get_height 등)는 __getattr__로 실제 폰트에 그대로 위임한다."""

    __slots__ = ("_f",)

    def __init__(self, font):
        self._f = font

    def render(self, text, *args, **kwargs):
        from core import i18n
        return self._f.render(i18n.t(text), *args, **kwargs)

    def size(self, text, *args, **kwargs):
        from core import i18n
        return self._f.size(i18n.t(text), *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._f, name)


fonts = {}          # size -> _I18nFont (번역 래퍼, 게임 코드가 받는 것)


def _make_raw_font(size):
    """실제 pygame Font 하나를 만든다 (폰트 파일 없으면 다운로드 시도 후 시스템 폰트 폴백)."""
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
                return pygame.font.SysFont("malgungothic", size)
            except Exception:
                return pygame.font.Font(None, size)
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        try:
            return pygame.font.SysFont("malgungothic", size)
        except Exception:
            return pygame.font.Font(None, size)


def get_font(size):
    """번역 래퍼(_I18nFont)로 감싼 폰트를 돌려준다 (사이즈별 캐시)."""
    if size not in fonts:
        fonts[size] = _I18nFont(_make_raw_font(size))
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
        # 작물 '먹는 것' 픽셀 통일용 (사과·감자·쌀밥)
        'A': (216, 58, 54, 255),  # Apple red
        'a': (150, 34, 34, 255),  # Apple red shade
        'h': (245, 138, 128, 255),# Apple highlight
        'u': (242, 244, 248, 255),# Bowl/rice white
        'U': (198, 206, 216, 255),# Bowl shade
        'c': (96, 140, 192, 255), # Bowl blue band
        'v': (255, 255, 255, 255),# Rice grain highlight
        'j': (206, 210, 218, 255),# Rice grain shade
        # 아이콘 통일용 (날씨·톱니·메달) — 팔레트와 톤 일치
        'Q': (255, 208, 70, 255), # Sun body
        'T': (236, 176, 40, 255), # Sun edge / ray
        'C': (206, 212, 224, 255),# Cloud body
        'P': (150, 158, 172, 255),# Cloud shade
        'J': (96, 156, 226, 255), # Rain drop
        'F': (232, 146, 46, 255), # Drought orange
        'f': (196, 104, 24, 255), # Drought shade / crack
        'V': (150, 176, 152, 255),# Wind stroke
        'Z': (208, 216, 210, 255),# Gear body (steel, 밝게)
        'z': (140, 150, 148, 255),# Gear shade
        'E': (242, 248, 242, 255),# Gear highlight
    }
    
    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            if char in colors and colors[char][3] > 0:
                pygame.draw.rect(surf, colors[char], (x*scale, y*scale, scale, scale))
    return surf


def _pixelize(surf, target_w, target_h, block=4, levels=6):
    """래스터 이미지(사진·일러스트)를 픽셀 아트 톤에 맞춘다.

    작은 해상도로 부드럽게 줄여 세부를 뭉갠 뒤, 색을 계단화(posterize)하고, 최근접으로 확대해
    도트 블록을 만든다. **numpy 미사용**(안드로이드 빌드 호환) — 작은 중간 이미지에만 픽셀 연산."""
    sw = max(1, target_w // block)
    sh = max(1, target_h // block)
    small = pygame.transform.smoothscale(surf, (sw, sh))
    if levels and levels >= 2:
        step = 255 // (levels - 1)
        small.lock()
        for y in range(sh):
            for x in range(sw):
                r, g, b, a = small.get_at((x, y))
                if a < 8:
                    continue
                r = min(255, ((r + step // 2) // step) * step)
                g = min(255, ((g + step // 2) // step) * step)
                b = min(255, ((b + step // 2) // step) * step)
                small.set_at((x, y), (r, g, b, a))
        small.unlock()
    return pygame.transform.scale(small, (target_w, target_h))   # 최근접 확대 → 도트 블록


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
    sprites['mini_apple'] = create_sprite_from_string('''
.L.
.X.
iYi
iii
iii
.i.
''', 2)
    sprites['mini_potato'] = create_sprite_from_string('''
.XXXX.
XBYYBX
XYYbYX
XYbYYX
XBYYBX
.XbbX.
''', 2)
    # 초록 벼 줄기 + 고개 숙인 금빛 이삭 (다른 mini 아이콘과 톤을 맞춘 벼 한 포기)
    sprites['mini_rice'] = create_sprite_from_string('''
....Yy
...YYy
..Yy..
.GgY..
LGg...
.Gg...
.Gg...
LGgL..
''', 2)

    # ── 아버지의 창고 물건 아이콘 (갤러리 '창고' 탭) ──
    sprites['item_hoe'] = create_sprite_from_string('''
.........BB.
........BBB.
.......BB...
......BB....
.....BB.....
....BB......
...mBB......
..MMm.......
.MMMm.......
MMMm........
WMm.........
.m..........
''', 3)
    sprites['item_seed_pouch'] = create_sprite_from_string('''
...BB.....
..ByyB....
.BBBBBB...
BBbBBBBB..
BBBBOBBB..
BBbBOBBB..
.BBBBBB...
..bbbb....
''', 3)
    sprites['item_shears'] = create_sprite_from_string('''
.M......M.
.MM....MM.
..MM..MM..
...MMMM...
....WW....
...ByyB...
..By..yB..
.By....yB.
.B......B.
''', 3)
    sprites['item_basket'] = create_sprite_from_string('''
..bBBBBb..
.B.BBBB.B.
.BBbBbBBB.
.BbBbBbBB.
.BBbBbBBB.
..BBBBBB..
...bbbb...
''', 3)
    sprites['item_boots'] = create_sprite_from_string('''
.nn...nn..
.nn...nn..
.nn...nn..
.nn...nn..
.nnn..nnn.
.nnnn.nnnn
.kkkk.kkkk
''', 3)
    sprites['item_radio'] = create_sprite_from_string('''
......y...
.....y....
KKKKKKKKKK
KmmmKKWWKK
KmmmKKQKKK
KmmmKKKKKK
KKKKKKKKKK
kkkkkkkkkk
''', 3)
    sprites['item_bojagi'] = create_sprite_from_string('''
....YY....
...Y..Y...
....YY....
..YYYYYY..
.YyYYYYyY.
.YYYYYYYY.
..YYYYYY..
''', 3)
    sprites['item_key'] = create_sprite_from_string('''
.MMM......
M...M.....
M...M.....
.MMM......
..M.......
..M.MM....
..M.......
..M.MM....
..MM......
''', 3)
    sprites['item_black_hat'] = create_sprite_from_string('''
...kkkk...
..kKKKKk..
..kKKKKk..
kkkkkkkkkk
kKKKKKKKKk
.kkkkkkkk.
''', 3)
    sprites['seed'] = create_sprite_from_string('''
...XX...
..XooX..
.XoOoOX.
.XoOoOX.
..XooX..
...XX...
''', 5)
    _WEED_ART = '''
..w.X.w..
.XwGwGwX.
X.XGgGX.X
..XGgGX..
.XwgXgwX.
...XeX...
..XgegX..
.Xg.X.gX.
'''
    sprites['weed'] = create_sprite_from_string(_WEED_ART, 5)
    # 악)몽중농원용 붉게 시든 잡초 (초록 팔레트를 붉은색으로 매핑)
    sprites['weed_nm'] = create_sprite_from_string(
        _WEED_ART.translate(str.maketrans({'G': 'i', 'g': 'q', 'e': '#', 'w': 'o'})), 5)
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
    # 해충 — 예전의 작고 아담한 딱정벌레(붉은 눈). 크고 징그럽지 않게 작은 스케일로.
    sprites['bug'] = create_sprite_from_string('''
.X....X.
..XkkX..
.XkKKkX.
XkKiiKkX
XkKKKKkX
.XkKKkX.
X.XkkX.X
.XX..XX.
''', 4)
    dad_path = resource_path("dad.png")
    loaded_dad = False
    if os.path.exists(dad_path):
        try:
            dad_img = pygame.image.load(dad_path).convert_alpha()
            # dad.png도 이미 픽셀 아트다. 초상화라 세게 뭉개면 얼굴이 뭉개지므로, 픽셀 '결'만 살짝
            # 굵게(2px 블록) + 색 살짝 계단화해 작물·아이콘의 굵은 도트 톤에 조금 더 맞춘다.
            sprites['dad'] = _pixelize(dad_img, 160, 160, block=2, levels=12)
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

    # 작물 '먹는 것' 픽셀 스프라이트 — 당근(픽셀)과 톤·질감을 맞춰 사과·감자·쌀밥도 도트로 통일.
    # (예전엔 사과·감자·쌀밥이 벡터 도형이라 당근만 픽셀이라 이질감이 컸다.)
    sprites['food_apple'] = create_sprite_from_string('''
....gg....
...gGb....
....Xb....
..XAAAAX..
.XhhAAAaX.
XhAAAAAaaX
XAAAAAAaaX
XAAAAAAaaX
XAAAAAAaaX
.XAAAaaaX.
..XaaaaX..
...XXX....
''', 6)
    sprites['food_potato'] = create_sprite_from_string('''
..XXXXX...
.XBYBBBX..
XBYBbBBBX.
XBBBBBbBX.
XBbBBBBBX.
XBBBBBBbX.
.XBBBBBX..
..XXXXX...
''', 8)
    sprites['food_rice'] = create_sprite_from_string('''
...uvuvu...
..uuvuuvu..
.uuuuuuuuu.
XUUUUUUUUUX
XucccccccuX
XuuuuuuuuuX
.XuuuuuuuX.
..XUUUUUX..
...XXXXX...
''', 8)

    # 아이콘 픽셀 통일 (날씨·톱니) — 벡터 대신 도트로 그려 작물·UI와 톤을 맞춘다. scale 1(원본=격자px),
    # draw_weather_icon 등에서 목표 size로 확대해 쓴다.
    sprites['icon_clear'] = create_sprite_from_string('''
.....T.....
...T.Q.T...
....QQQ....
.T.QQQQQ.T.
T.QQQQQQQ.T
.T.QQQQQ.T.
....QQQ....
...T.Q.T...
.....T.....
''', 1)
    sprites['icon_cloudy'] = create_sprite_from_string('''
....CCC....
..CCCCCCC..
.CCCCCCCCC.
CCCCCCCCCCC
PPPPPPPPPPP
''', 1)
    sprites['icon_rain'] = create_sprite_from_string('''
...CCC.....
.CCCCCCC...
CCCCCCCCC..
PPPPPPPPP..
.J..J..J...
J..J..J....
.J..J..J...
''', 1)
    sprites['icon_drought'] = create_sprite_from_string('''
.....F.....
...F.F.F...
....FFF....
.F.FFFFF.F.
F.FFFFFFF.F
.F.FFFFF.F.
....FFF....
...........
.f..f.f..f.
''', 1)
    sprites['icon_wind'] = create_sprite_from_string('''
...........
.VVVVVV.V..
V.....VVVV.
...VVVVV...
VVVV....V..
.V.VVVVVVV.
...........
''', 1)
    sprites['icon_gear'] = create_sprite_from_string('''
...Z.Z.Z...
.ZZZZZZZZZ.
.ZZEEEEEZZ.
ZZEz...zEZZ
.ZE.....EZ.
ZZE..z..EZZ
.ZE.....EZ.
ZZEz...zEZZ
.ZZEEEEEZZ.
.ZZZZZZZZZ.
...Z.Z.Z...
''', 1)

    # 밭 이미지 에셋 불러오기 (여백 크롭 및 362x318 리사이징)
    field_bed_path = resource_path("field_bed.jpg")
    if os.path.exists(field_bed_path):
        try:
            raw_img = pygame.image.load(field_bed_path).convert_alpha()
            cropped = raw_img.subsurface(pygame.Rect(59, 74, 904, 763))
            # field_bed.jpg는 이미 도트(픽셀 아트) 톤이라 그대로 스케일만 한다(픽셀화하면 오히려 뭉개짐).
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


# 배경 그라데이션 밴딩(P4) — 하늘·잔디를 계단식 '띠'로 그려 도트 톤에 맞춘다.
# (core.ui 와 같은 개념이지만 assets는 ui를 import 하면 순환이라 여기 로컬로 둠.)
_BG_BAND = 10


def _bg_quant(color, step=10):
    return tuple(min(255, ((c + step // 2) // step) * step) for c in color[:3])


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

    # 여백까지 '실제 배경'을 이어 그린다 — 안전영역 밖(부모 캔버스에 여백이 있으면) 하늘/산/땅을
    # 캔버스 전체 폭으로 연장한다(지평선이 자연스럽게 옆으로 이어짐). 오브젝트(해·밭)는 안전영역에.
    parent = screen.get_parent()
    if parent is not None and parent.get_size() != (w, h):
        bg = parent
        ox, oy = screen.get_offset()
        PW, PH = parent.get_size()
    else:
        bg = screen
        ox, oy = 0, 0
        PW, PH = w, h
    top_y = -oy                  # 그릴 최상단(safe-y, 여백 있으면 음수)
    bot_y = PH - oy              # 그릴 최하단(safe-y)

    # --- 하늘: 다단 황혼 그라데이션 (계단식 밴딩) — 위 여백까지 전체 폭 ---
    y = (top_y // _BG_BAND) * _BG_BAND
    while y < horizon:
        t = max(0.0, min(1.0, (y + _BG_BAND * 0.5) / horizon))
        pygame.draw.rect(bg, _bg_quant(_sky_color(t)), (0, y + oy, PW, _BG_BAND))
        y += _BG_BAND

    # --- 별 (윗하늘, 태양에서 먼 쪽일수록 또렷하게) ---
    for sx, sy, sb in _STARS:
        if sx < 540 or sy > 110:
            tw = 200 + sb * 22
            # 악몽 모드에서는 붉은 빛 별로 변경
            col = (min(255, tw), 60, 60) if game_state.nightmare else (min(255, tw), min(255, tw), 210)
            pygame.draw.circle(bg, col, (sx + ox, sy + oy), sb)

    # --- 태양 + 블룸 — '계단 알파' 도트 글로우 (캐시: 매 프레임 원 18개+pixelate 재생성 제거) ---
    sun_x, sun_y = 640 + ox, 78 + oy
    bloom_c = (180, 20, 20) if game_state.nightmare else (255, 188, 120)
    blit_glow(bg, glow_sprite(126, bloom_c, px=5, steps=(14, 30, 50)), (sun_x, sun_y))
    # 태양 본체 — 블룸(위)은 소프트하게 두고, 본체는 큰 픽셀 디스크로(곡선 없음)
    if game_state.nightmare:
        pixel_disc(bg, (30, 0, 0), (sun_x, sun_y), 40, px=3)
        pixel_disc(bg, (90, 10, 10), (sun_x, sun_y), 29, px=3)
        pixel_disc(bg, (150, 15, 15), (sun_x, sun_y), 15, px=3)
    else:
        pixel_disc(bg, (255, 152, 86), (sun_x, sun_y), 40, px=3)
        pixel_disc(bg, (255, 206, 142), (sun_x, sun_y), 29, px=3)
        pixel_disc(bg, (255, 240, 206), (sun_x, sun_y), 15, px=3)

    # --- 노을 구름 (반투명, 빛을 받은 아랫면이 환하게) ---
    for cx, cy, cw, ch in _CLOUDS:
        cloud = pygame.Surface((cw, ch * 2), pygame.SRCALPHA)
        cloud_c1 = (60, 20, 20, 120) if game_state.nightmare else (90, 52, 84, 120)
        cloud_c2 = (140, 30, 30, 110) if game_state.nightmare else (236, 158, 120, 110)
        pygame.draw.ellipse(cloud, cloud_c1, (0, 0, cw, ch))
        pygame.draw.ellipse(cloud, cloud_c2, (cw * 0.18, ch * 0.5, cw * 0.7, ch))
        bg.blit(cloud, (cx - cw // 2 + ox, cy - ch // 2 + oy))

    # --- 안개 낀 산 3겹 (멀수록 옅고 푸르게) — 능선을 캔버스 양끝까지 평평하게 연장 ---
    if game_state.nightmare:
        m1 = (48, 10, 10)
        m2 = (34, 6, 6)
        m3 = (20, 3, 3)
    else:
        m1 = (108, 74, 116)
        m2 = (78, 52, 98)
        m3 = (46, 70, 78)

    def _hill(color, ridge, base):
        poly = [(0, ridge[0][1] + oy)]                        # 왼쪽 캔버스 끝(첫 능선 높이로 평평히)
        poly += [(px + ox, py + oy) for px, py in ridge]      # 능선
        poly += [(PW, ridge[-1][1] + oy), (PW, base + oy), (0, base + oy)]  # 오른쪽 끝 + 아래 모서리
        pygame.draw.polygon(bg, color, poly)

    _hill(m1, [(0, horizon - 6), (140, 96), (300, horizon - 14), (470, 92), (650, horizon - 4), (800, 104)], horizon + 10)
    _hill(m2, [(0, horizon + 22), (110, 116), (260, horizon + 12), (440, 108), (610, horizon + 20), (800, 122)], h)
    _hill(m3, [(0, horizon + 52), (160, 146), (340, horizon + 44), (520, 138), (800, horizon + 50)], h)

    # --- 지평선 햇무리 (따뜻한 가로 빛띠) — 전체 폭 ---
    haze = pygame.Surface((PW, 40), pygame.SRCALPHA)
    for i in range(20):
        a = int(70 * (1 - abs(i - 10) / 10))
        col = (180, 20, 20, a) if game_state.nightmare else (255, 196, 140, a)
        pygame.draw.line(haze, col, (0, i * 2), (PW, i * 2))
    bg.blit(pixelate(haze), (0, horizon - 20 + oy))   # 큰 픽셀: 햇무리 밴드 도트화

    # --- 잔디: 세로 그라데이션(계단식 밴딩) + 결 — 아래 여백까지 전체 폭 ---
    i = 0
    while horizon + i < bot_y:
        c = _mix_color(_mix_color(gc, (255, 200, 150) if not game_state.nightmare else (100, 40, 40), 0.12), gd, min(1.0, i / 150.0))
        pygame.draw.rect(bg, _bg_quant(c), (0, horizon + i + oy, PW, _BG_BAND))
        i += _BG_BAND
    for gy in range(horizon, bot_y, 34):
        c = _mix_color(gc, gd, 0.30 if (gy // 34) % 2 == 0 else 0.50)
        pygame.draw.line(bg, c, (0, gy + oy), (PW, gy + 16 + oy), 2)

    for gx in range(0, PW, 44):
        for gy in range(horizon + 18, bot_y, 70):
            if (gx + gy) % 3 == 0:
                pygame.draw.line(bg, gd, (gx + 10, gy + 8 + oy), (gx + 18, gy + 2 + oy), 2)
                pygame.draw.line(bg, gd, (gx + 17, gy + 3 + oy), (gx + 22, gy + 11 + oy), 2)

    # --- 텃밭 흙바닥: 나무 테두리 + 결 고운 흙 + 빛·그늘 밴드 + 입체 이랑 ---
    dirt_rect = pygame.Rect(38, 112, w - 76, h - 246)
    # 나무 테두리
    frame = dirt_rect.inflate(12, 12)
    border_c1 = (40, 15, 15) if game_state.nightmare else (52, 36, 25)
    border_c2 = (100, 30, 30) if game_state.nightmare else (122, 86, 53)
    border_c3 = (130, 45, 45) if game_state.nightmare else (156, 114, 74)
    pixel_rect(screen, border_c1, frame.move(0, 6), chamfer=CHAMFER)
    pixel_rect(screen, border_c2, frame, chamfer=CHAMFER)
    pixel_rect(screen, border_c3, frame, width=2, chamfer=CHAMFER)
    # 흙 바닥
    pixel_rect(screen, dd, dirt_rect.move(0, 4), chamfer=CHAMFER)
    pixel_rect(screen, dc, dirt_rect, chamfer=CHAMFER)
    # 위쪽 빛 밴드 / 아래쪽 그늘 밴드로 깊이감
    top_band = pygame.Surface((dirt_rect.w, 64), pygame.SRCALPHA)
    for i in range(64):
        top_band.fill((255, 205, 150, int(58 * (1 - i / 64))) if not game_state.nightmare else (200, 50, 50, int(58 * (1 - i / 64))), (0, i, dirt_rect.w, 1))
    screen.blit(pixelate(top_band), (dirt_rect.x, dirt_rect.y))   # 큰 픽셀: 빛 밴드 도트화
    bot_band = pygame.Surface((dirt_rect.w, 90), pygame.SRCALPHA)
    for i in range(90):
        bot_band.fill((26, 16, 10, int(72 * (i / 90))) if not game_state.nightmare else (20, 5, 5, int(72 * (i / 90))), (0, i, dirt_rect.w, 1))
    screen.blit(pixelate(bot_band), (dirt_rect.x, dirt_rect.bottom - 90))   # 큰 픽셀: 그늘 밴드 도트화
    # 입체 이랑 (어두운 고랑 + 윗면 노을 하이라이트)
    for y in range(dirt_rect.y + 30, dirt_rect.bottom - 16, 40):
        pygame.draw.rect(screen, _mix_color(dd, BLACK, 0.20), (dirt_rect.x + 14, y + 6, dirt_rect.w - 28, 6))
        pygame.draw.rect(screen, _mix_color(dc, (255, 205, 150) if not game_state.nightmare else (200, 80, 80), 0.24), (dirt_rect.x + 14, y, dirt_rect.w - 28, 4))
    # 흙 알갱이 텍스처
    speck = _mix_color(dc, dd, 0.65)
    for sx_, sy_, ss in _SOIL_SPECKS:
        pygame.draw.rect(screen, speck, (dirt_rect.x + sx_, dirt_rect.y + sy_, ss, ss))
    pixel_rect(screen, _mix_color(dd, BLACK, 0.10), dirt_rect, width=3, chamfer=CHAMFER)

    from core.layout import bleed_edges
    bleed_edges(screen)   # 적응형: 안전영역 밖 여백을 잔디/하늘로 이어 채움(4:3이면 무동작)


_FOOD_SPRITE = {"apple": "food_apple", "potato": "food_potato", "rice": "food_rice"}


def draw_crop_food(screen, cx, cy, crop_key, r=26):
    """작물별 '먹는 것'을 (cx, cy) 중심에 픽셀 스프라이트로 그린다 (엔딩·수확 연출 공용).

    당근·사과·감자·쌀밥 모두 도트 스프라이트로 통일했다(예전엔 사과·감자·쌀밥만 벡터라 이질감).
    r에 맞춰 **정수 배율**로만 확대해 픽셀이 뭉개지지 않게 한다."""
    spr = sprites.get(_FOOD_SPRITE.get(crop_key, "carrot"))
    if not spr:
        return
    # 목표 높이 ≈ 2.7*r 에 가장 가까운 정수 배율(최소 1배)로 확대 → 픽셀 유지
    target_h = max(1, int(r * 2.7))
    factor = max(1, round(target_h / spr.get_height()))
    if factor != 1:
        spr = pygame.transform.scale(spr, (spr.get_width() * factor, spr.get_height() * factor))
    screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() // 2))


def draw_crop_seed(screen, cx, cy, crop_key):
    """작물별 씨앗 모양을 (cx, cy) 중심에 그린다.
    당근은 기존 픽셀 스프라이트를, 나머지는 벡터 도형을 그린다."""
    if crop_key == "apple":
        # 사과 씨앗: 작고 검붉은 도트 씨앗 몇 알(각진 픽셀)
        for dx, dy in [(-5, 1), (5, -1), (0, 6)]:
            pygame.draw.rect(screen, (92, 46, 28), (cx + dx - 2, cy + dy - 3, 4, 7))
            pygame.draw.rect(screen, (150, 92, 56), (cx + dx - 1, cy + dy - 1, 2, 3))
        return
    if crop_key == "potato":
        # 씨감자: 각진 황갈색 덩이 + 싹눈 도트
        pixel_rect(screen, (120, 84, 50), (cx - 10, cy - 7, 20, 14), chamfer=CHAMFER)
        pixel_rect(screen, (170, 130, 82), (cx - 8, cy - 5, 15, 10), chamfer=CHAMFER_SM)
        for ex, ey in [(-3, -1), (3, 2), (0, 4)]:
            pygame.draw.rect(screen, (92, 62, 38), (cx + ex - 1, cy + ey - 1, 2, 2))
        return
    if crop_key == "rice":
        # 볍씨: 물 위에 흩뿌린 각진 낟알 도트
        for dx, dy in [(-6, 1), (-1, 5), (4, -1), (7, 4), (1, -3)]:
            pygame.draw.rect(screen, (200, 186, 120), (cx + dx - 1, cy + dy - 3, 3, 6))
            pygame.draw.rect(screen, (240, 232, 190), (cx + dx, cy + dy - 2, 2, 3))
        return
    # carrot (기본): 픽셀 씨앗 스프라이트
    spr = sprites.get("seed")
    if spr:
        screen.blit(spr, (cx - spr.get_width() // 2, cy - spr.get_height() // 2))



_WEATHER_ICON = {'맑음': 'icon_clear', '흐림': 'icon_cloudy', '비': 'icon_rain',
                 '가뭄': 'icon_drought', '강풍': 'icon_wind'}


def draw_weather_icon(screen, weather, x, y, size=20):
    """날씨 아이콘을 (x, y) 좌상단, size 정사각 박스 안에 픽셀 스프라이트로 그린다.
    (예전엔 벡터 pygame.draw였는데 도트로 통일해 작물·UI와 톤을 맞춤.)"""
    spr = sprites.get(_WEATHER_ICON.get(weather))
    if spr is None:
        return
    sw, sh = spr.get_size()
    scale = size / max(sw, sh)
    w, h = max(1, int(round(sw * scale))), max(1, int(round(sh * scale)))
    scaled = pygame.transform.scale(spr, (w, h))
    screen.blit(scaled, (x + (size - w) // 2, y + (size - h) // 2))
