"""Steam(Steamworks) 도전과제 연동 — **순수 ctypes**로 공식 `steam_api64.dll`을 직접 호출한다.

왜 ctypes인가:
  이 프로젝트는 "GitHub 언어 통계 100% Python" 요구사항이 있다. `SteamworksPy` 같은 C 래퍼
  바인딩은 C 소스가 붙어 이 요구사항을 깬다. 반면 여기처럼 ctypes로 공식 DLL을 직접 부르면
  **소스는 순수 파이썬**이고, `steam_api64.dll`은 폰트(.ttf)·소리(.ogg)처럼 **바이너리 에셋**이라
  언어 통계에 잡히지 않는다.

동작 원칙 — **없으면 무해한 no-op**:
  - `steam_api64.dll`이 없거나(비스팀 데스크톱/개발 중), 안드로이드거나, App ID/심볼이 안 맞으면
    모든 함수가 조용히 아무 일도 하지 않는다. 게임으로 예외를 절대 던지지 않는다.
  - 따라서 지금 상태(App ID 미확보)에서도 코드에 넣어 두어 안전하다. App ID를 확보해
    `steam_api64.dll`과 `steam_appid.txt`(= 그 App ID)를 exe 옆(또는 개발 시 레포 루트)에 두면
    자동으로 살아난다.

붙이는 법 (App ID 확보 후):
  1. Steamworks 파트너 사이트에서 각 도전과제의 **API Name을 아래 로컬 id와 동일하게** 만든다
     (first_harvest, grow_carrot, grow_potato, grow_rice, grow_apple, perfect_harvest,
      veteran, all_crops, true_ending, nightmare_clear, hundred_clears, nightmare_ending,
      developer_secret). 이름을 다르게 지어야 하면 아래 ACHIEVEMENT_MAP에 매핑을 넣는다.
  2. Steamworks SDK의 `redistributable_bin/win64/steam_api64.dll`을 레포/빌드에 포함하고
     PyInstaller `--add-binary` 로 exe에 번들한다.
  3. 개발 중 로컬 테스트는 레포 루트에 `steam_appid.txt`(App ID 한 줄)를 두고 스팀 클라이언트를
     켠 채 실행한다. (steam_appid.txt는 배포본에는 넣지 않는다 — .gitignore 권장.)
"""

import os
import sys
import ctypes

try:
    from core.platform import IS_ANDROID
except Exception:  # 방어적: platform 모듈을 못 불러도 죽지 않는다
    IS_ANDROID = False


# 로컬 업적 id → 스팀 도전과제 API Name. 비어 있으면 로컬 id를 API Name으로 그대로 쓴다.
# (파트너 사이트에서 API Name을 로컬 id와 똑같이 만들면 여기 손댈 필요 없음.)
ACHIEVEMENT_MAP = {}

# ISteamUserStats 인터페이스 접근자 — SDK 버전에 따라 접미사가 다르므로 알려진 후보를 순서대로 시도.
_STATS_ACCESSORS = (
    "SteamAPI_SteamUserStats_v013",
    "SteamAPI_SteamUserStats_v012",
    "SteamAPI_SteamUserStats_v011",
)

_lib = None
_stats = None
_ready = False


def _find_dll():
    """steam_api64.dll 경로를 찾는다. 없으면 None (→ 전체 no-op)."""
    names = ("steam_api64.dll",)
    candidates = []
    # PyInstaller 번들 임시 폴더
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.append(base)
    # 배포 exe 옆
    if getattr(sys, "frozen", False):
        candidates.append(os.path.dirname(sys.executable))
    # 개발: 레포 루트 (이 파일의 상위 폴더의 상위)
    candidates.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 현재 작업 폴더
    candidates.append(os.getcwd())
    for d in candidates:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return p
    return None


def _get_stats_iface():
    """ISteamUserStats 인터페이스 포인터를 얻는다 (버전 접미사 후보를 차례로 시도)."""
    for accessor in _STATS_ACCESSORS:
        try:
            fn = getattr(_lib, accessor)
        except AttributeError:
            continue
        try:
            fn.restype = ctypes.c_void_p
            fn.argtypes = []
            ptr = fn()
            if ptr:
                return ptr
        except Exception:
            continue
    return None


def init():
    """스팀을 초기화한다. 성공하면 True, 아니면 (조용히) False.

    - 안드로이드거나 DLL이 없거나 스팀 클라이언트가 없으면 False로 no-op.
    - 게임 시작 시 한 번 호출 (실패해도 게임은 그대로 진행)."""
    global _lib, _stats, _ready
    if _ready:
        return True
    if IS_ANDROID:
        return False
    try:
        dll = _find_dll()
        if not dll:
            return False
        _lib = ctypes.CDLL(dll)
        try:
            _lib.SteamAPI_Init.restype = ctypes.c_bool
            _lib.SteamAPI_Init.argtypes = []
        except Exception:
            pass
        if not _lib.SteamAPI_Init():
            return False
        _stats = _get_stats_iface()
        if _stats:
            # 현재 유저의 도전과제/스탯을 스팀에서 받아 둔다 (SetAchievement 전에 권장).
            try:
                req = _lib.SteamAPI_ISteamUserStats_RequestCurrentStats
                req.argtypes = [ctypes.c_void_p]
                req.restype = ctypes.c_bool
                req(_stats)
            except Exception:
                pass
        _ready = True
        return True
    except Exception:
        _ready = False
        return False


def unlock_achievement(local_id):
    """로컬 업적 id에 해당하는 스팀 도전과제를 해제한다. no-op이면 조용히 무시."""
    if not _ready or not _stats or not local_id:
        return
    name = ACHIEVEMENT_MAP.get(local_id, local_id)
    try:
        setach = _lib.SteamAPI_ISteamUserStats_SetAchievement
        setach.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        setach.restype = ctypes.c_bool
        setach(_stats, name.encode("utf-8"))
        store()
    except Exception:
        pass


def store():
    """변경된 도전과제/스탯을 스팀 서버에 커밋한다 (오버레이 알림도 이때 뜬다)."""
    if not _ready or not _stats:
        return
    try:
        st = _lib.SteamAPI_ISteamUserStats_StoreStats
        st.argtypes = [ctypes.c_void_p]
        st.restype = ctypes.c_bool
        st(_stats)
    except Exception:
        pass


def run_callbacks():
    """스팀 콜백 처리 — 매 프레임 호출 (오버레이 알림 등). no-op이면 무시."""
    if not _ready:
        return
    try:
        _lib.SteamAPI_RunCallbacks()
    except Exception:
        pass


def shutdown():
    """게임 종료 시 스팀 정리."""
    global _ready
    if not _ready:
        return
    try:
        _lib.SteamAPI_Shutdown()
    except Exception:
        pass
    _ready = False


def is_active():
    """스팀 연동이 실제로 활성화됐는지 (테스트/디버그용)."""
    return _ready
