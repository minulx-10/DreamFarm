"""빌드 시 모든 효과음/배경음을 numpy로 합성해 core/sound/**.ogg 로 굽는다.

왜? core/audio.py 는 원래 numpy 로 소리를 런타임 합성했지만, numpy 는
python-for-android 에서 매번 소스 컴파일돼 안드로이드 빌드를 몇 배 느리게 만들고
자주 깨뜨린다. 그래서 배포 파이프라인은 빌드 시점에 이 스크립트로 소리를 미리
.ogg 로 구워 두고, 런타임(APK/EXE)에는 numpy 없이 그 파일만 실어 재생한다.

사용:  python tools/bake_audio.py [출력경로]
필요:  numpy, pygame-ce, soundfile   (개발/CI 환경에만 필요, 최종 산출물엔 불필요)
"""

import os
import sys

# CI 등 헤드리스(사운드 장치 없음) 환경에서도 mixer 를 초기화할 수 있게 더미 드라이버.
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import soundfile as sf  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT_DIR = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "core", "sound")


def main():
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.mixer.init()

    from core import audio
    if not audio._ensure_np():
        print("ERROR: numpy 를 불러올 수 없어 굽기를 진행할 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    total = 0

    def bake(category, builders, wrap=None):
        nonlocal total
        d = os.path.join(OUT_DIR, category)
        os.makedirs(d, exist_ok=True)
        for name, fn in builders.items():
            snd = wrap(fn()) if wrap else fn()          # pygame.Sound (int16 stereo)
            arr = pygame.sndarray.array(snd)            # (N, 2) int16
            path = os.path.join(d, name + ".ogg")
            # 한 번에 큰 OGG/Vorbis를 쓰면 libsndfile 이 네이티브 크래시를 내는
            # 경우가 있다(특히 수십 초짜리 BGM). 블록 단위로 쪼개 쓰면 안전하다.
            with sf.SoundFile(path, "w", samplerate=44100, channels=arr.shape[1],
                              format="OGG", subtype="VORBIS") as f:
                for i in range(0, len(arr), 44100):
                    f.write(arr[i:i + 44100])
            kb = os.path.getsize(path) / 1024.0
            print(f"  baked {category}/{name}.ogg  ({arr.shape[0]/44100:.1f}s, {kb:.0f}KB)")
            total += 1

    print(f"Baking audio -> {OUT_DIR}")
    # 효과음 빌더는 이미 pygame.Sound 를 돌려준다. 배경음 빌더는 float 파형이라 _to_sound 로 감싼다.
    bake("sfx", audio._SFX_BUILDERS)
    bake("bgm", audio._BGM_BUILDERS, wrap=lambda w: audio._to_sound(w, 0.9))
    print(f"Done — {total} files baked.")


if __name__ == "__main__":
    main()
