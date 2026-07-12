"""몽중농원 절차적 오디오 엔진.

효과음과 배경음은 원래 numpy로 런타임에 합성했다. 그러나 numpy는
python-for-android(안드로이드 빌드)에서 매번 소스 컴파일돼 빌드를 몇 배 느리게
하고 자주 깨뜨린다. 그래서 배포 파이프라인은 빌드 시점에 `tools/bake_audio.py`로
모든 소리를 미리 .ogg로 구워(core/sound/**) APK/EXE에 실어 보내고, 런타임에는
그 파일을 불러 재생한다 — numpy 없이도 동작한다.

데스크톱 개발 환경에서 .ogg가 아직 없으면 그때만 numpy를 지연 로드해 즉석
합성한다(기존과 동일한 폴백). 오디오 장치가 없거나 mixer 초기화에 실패해도 모든
함수가 조용히 no-op으로 동작하도록 설계되어 게임 진행을 막지 않는다.
"""

import os
import pygame

from core.assets import resource_path

SAMPLE_RATE = 44100

# numpy는 '합성'에만 필요하다. 미리 구운 .ogg를 쓰는 정상 경로에서는 import하지
# 않는다(안드로이드엔 numpy가 없으므로 최상단 import는 곧 크래시다). 합성이 실제로
# 필요한 순간에만 아래 _ensure_np()로 지연 로드한다.
np = None


def _ensure_np():
    """합성이 필요할 때만 numpy를 지연 로드한다. 성공하면 True."""
    global np
    if np is None:
        try:
            import numpy as _np
            np = _np
        except Exception as e:
            print("numpy 없음 — 즉석 오디오 합성 불가(구운 .ogg만 재생):", e)
            return False
    return True

_enabled = False
_muted = False
_sfx = {}            # name -> pygame.Sound
_bgm_sounds = {}     # name -> pygame.Sound
_bgm_channel = None
_current_bgm = None
_sfx_volume = 0.55
_bgm_volume = 0.30


# ----------------------------------------------------------------------------
# 합성 헬퍼
# ----------------------------------------------------------------------------
def _t(dur):
    return np.linspace(0.0, dur, int(SAMPLE_RATE * dur), endpoint=False)


def _adsr(dur, a=0.01, d=0.06, s=0.7, r=0.12):
    """샘플 길이만큼의 ADSR 엔벨로프(0~1)를 만든다."""
    n = int(SAMPLE_RATE * dur)
    if n <= 0:
        return np.zeros(0)
    ai = max(1, int(SAMPLE_RATE * a))
    di = max(1, int(SAMPLE_RATE * d))
    ri = max(1, int(SAMPLE_RATE * r))
    if ai + di + ri >= n:
        return np.linspace(1.0, 0.0, n) ** 1.5
    env = np.empty(n)
    env[:ai] = np.linspace(0.0, 1.0, ai)
    env[ai:ai + di] = np.linspace(1.0, s, di)
    env[ai + di:n - ri] = s
    env[n - ri:] = np.linspace(s, 0.0, ri)
    return env


def _tone(freq, dur, harmonics=(1.0, 0.35, 0.12), detune=0.0):
    """배음을 더한 부드러운 톤."""
    t = _t(dur)
    wave = np.zeros(len(t))
    for i, amp in enumerate(harmonics, start=1):
        f = freq * i * (1.0 + detune)
        wave += amp * np.sin(2 * np.pi * f * t)
    peak = np.max(np.abs(wave)) or 1.0
    return wave / peak


def _noise(dur):
    return np.random.uniform(-1.0, 1.0, int(SAMPLE_RATE * dur))


def _lowpass(x, alpha=0.15):
    """간단한 1차 저역통과 (부드럽게) - numpy convolve 벡터화 최적화."""
    if alpha >= 1.0:
        return x.copy()
    if alpha <= 0.0:
        return np.zeros_like(x)
    
    # 지수 감쇠 커널 길이 결정 (커널 값이 1e-5 미만으로 떨어지는 지점 계산)
    # (1 - alpha)^K < 1e-5  =>  K > log(1e-5) / log(1 - alpha)
    ln_threshold = -11.5129
    K = int(np.ceil(ln_threshold / np.log(1.0 - alpha)))
    K = max(1, min(len(x), K, 500))  # 최대 500으로 제한하여 극소 알파값 방어
    
    kernel = alpha * ((1.0 - alpha) ** np.arange(K))
    return np.convolve(x, kernel, mode='full')[:len(x)]


def _to_sound(wave, gain=1.0):
    """float mono[-1,1] -> 스테레오 int16 pygame.Sound."""
    wave = np.clip(wave * gain, -1.0, 1.0)
    audio = (wave * 32767).astype(np.int16)
    stereo = np.column_stack((audio, audio))
    return pygame.sndarray.make_sound(np.ascontiguousarray(stereo))


def _mix(*waves):
    """길이가 다른 파형들을 0번 인덱스 정렬로 합산 후 정규화."""
    n = max(len(w) for w in waves)
    out = np.zeros(n)
    for w in waves:
        out[:len(w)] += w
    peak = np.max(np.abs(out)) or 1.0
    return out / peak


# ----------------------------------------------------------------------------
# 효과음 정의
# ----------------------------------------------------------------------------
def _sfx_click():
    w = _tone(680, 0.07, harmonics=(1.0, 0.2)) * _adsr(0.07, a=0.002, d=0.02, s=0.3, r=0.04)
    return _to_sound(w, 0.5)


def _sfx_hover():
    w = _tone(960, 0.04, harmonics=(1.0,)) * _adsr(0.04, a=0.002, d=0.01, s=0.2, r=0.02)
    return _to_sound(w, 0.25)


def _sfx_water():
    dur = 0.28
    t = _t(dur)
    pitch = 520 * np.exp(-5.0 * t) + 180
    drop = np.sin(2 * np.pi * pitch * t)
    splash = _lowpass(_noise(dur), 0.06) * 0.5
    w = _mix(drop * 0.9, splash) * _adsr(dur, a=0.005, d=0.05, s=0.4, r=0.12)
    return _to_sound(w, 0.45)


def _sfx_soil():
    dur = 0.18
    w = _lowpass(_noise(dur), 0.04) * _adsr(dur, a=0.003, d=0.04, s=0.2, r=0.08)
    low = _tone(120, dur, harmonics=(1.0, 0.3)) * _adsr(dur, a=0.003, d=0.03, s=0.2, r=0.08)
    return _to_sound(_mix(w * 0.8, low * 0.6), 0.4)


def _sfx_success():
    notes = [523.25, 659.25, 783.99]
    seg = 0.12
    total = np.zeros(int(SAMPLE_RATE * (seg * len(notes) + 0.4)))
    for i, f in enumerate(notes):
        tone = _tone(f, 0.4, harmonics=(1.0, 0.4, 0.15)) * _adsr(0.4, a=0.005, d=0.1, s=0.5, r=0.25)
        start = int(SAMPLE_RATE * seg * i)
        total[start:start + len(tone)] += tone
    peak = np.max(np.abs(total)) or 1.0
    return _to_sound(total / peak, 0.4)


def _sfx_harvest():
    dur = 0.22
    t = _t(dur)
    pitch = 280 + 600 * (t / dur)
    w = np.sin(2 * np.pi * pitch * t) * _adsr(dur, a=0.004, d=0.05, s=0.4, r=0.1)
    return _to_sound(w, 0.45)


def _sfx_break():
    dur = 0.3
    t = _t(dur)
    pitch = 220 * np.exp(-3.0 * t) + 60
    body = np.sin(2 * np.pi * pitch * t)
    crack = _lowpass(_noise(dur), 0.2) * 0.7
    w = _mix(body * 0.7, crack) * _adsr(dur, a=0.002, d=0.06, s=0.3, r=0.18)
    return _to_sound(w, 0.4)


def _sfx_epiphany():
    notes = [392.0, 523.25, 587.33, 659.25, 783.99]
    total = np.zeros(int(SAMPLE_RATE * 1.6))
    for i, f in enumerate(notes):
        tone = _tone(f, 1.2, harmonics=(1.0, 0.5, 0.25, 0.1)) * _adsr(1.2, a=0.08, d=0.2, s=0.5, r=0.5)
        start = int(SAMPLE_RATE * 0.09 * i)
        total[start:start + len(tone)] += tone
    peak = np.max(np.abs(total)) or 1.0
    return _to_sound(total / peak, 0.35)


def _sfx_page():
    w = _lowpass(_noise(0.05), 0.1) * _adsr(0.05, a=0.002, d=0.01, s=0.2, r=0.03)
    return _to_sound(w, 0.18)


def _sfx_type():
    """타자기 톡 — 아주 짧고 작게(빠른 타이핑에도 안 거슬리게)."""
    w = _tone(1500, 0.018, harmonics=(1.0,)) * _adsr(0.018, a=0.001, d=0.005, s=0.1, r=0.008)
    click = _lowpass(_noise(0.018), 0.4) * 0.5
    return _to_sound(_mix(w * 0.6, click), 0.17)


def _sfx_weed_pull():
    """스윽 — 잡초가 흙에서 빠져나오는 부드러운 마찰음."""
    dur = 0.26
    t = _t(dur)
    sweep = _lowpass(_noise(dur), 0.05)
    pitch = 230 + 200 * (t / dur)
    body = np.sin(2 * np.pi * pitch * t) * 0.3
    w = _mix(sweep * 0.85, body) * _adsr(dur, a=0.02, d=0.06, s=0.5, r=0.14)
    return _to_sound(w, 0.42)


def _sfx_pop():
    """뿅 — 튀어나오거나 두드릴 때."""
    dur = 0.12
    t = _t(dur)
    pitch = 480 * np.exp(-10 * t) + 130
    w = np.sin(2 * np.pi * pitch * t) * _adsr(dur, a=0.002, d=0.03, s=0.2, r=0.06)
    return _to_sound(w, 0.4)


def _sfx_chirp():
    """짹 — 새 울음."""
    dur = 0.14
    t = _t(dur)
    pitch = 1300 + 500 * np.sin(2 * np.pi * 18 * t)
    w = np.sin(2 * np.pi * pitch * t) * _adsr(dur, a=0.004, d=0.04, s=0.3, r=0.06)
    return _to_sound(w, 0.3)


def _sfx_thud():
    """툭 — 당근이 쏙 뽑히는 묵직한 마무리."""
    dur = 0.2
    t = _t(dur)
    pitch = 180 * np.exp(-6 * t) + 70
    body = np.sin(2 * np.pi * pitch * t)
    w = _mix(body * 0.8, _lowpass(_noise(dur), 0.08) * 0.4) * _adsr(dur, a=0.002, d=0.05, s=0.3, r=0.1)
    return _to_sound(w, 0.45)


def _sfx_pest():
    """찌직, 톡 — 해충을 누를 때 나는 터지는 효과음."""
    dur = 0.08
    t = _t(dur)
    pitch = 800 * np.exp(-15 * t) + 120
    crush = _lowpass(_noise(dur), 0.12) * 0.7
    w = _mix(np.sin(2 * np.pi * pitch * t) * 0.45, crush) * _adsr(dur, a=0.001, d=0.02, s=0.15, r=0.04)
    return _to_sound(w, 0.42)


def _sfx_memory_in():
    """회상 씬 진입음 — 몽환적인 신스 아르페지오."""
    notes = [261.63, 329.63, 392.0, 523.25, 659.25]
    total = np.zeros(int(SAMPLE_RATE * 1.5))
    for i, f in enumerate(notes):
        tone = _tone(f, 0.9, harmonics=(1.0, 0.25), detune=0.002) * _adsr(0.9, a=0.05, d=0.15, s=0.4, r=0.3)
        start = int(SAMPLE_RATE * 0.08 * i)
        total[start:start + len(tone)] += tone * 0.35
    peak = np.max(np.abs(total)) or 1.0
    return _to_sound(total / peak, 0.38)


def _sfx_memory_out():
    """회상 씬 이탈음 — 슈우우욱 번쩍하며 퍼지는 소리."""
    dur = 1.0
    t = _t(dur)
    sweep_noise = _lowpass(_noise(dur), 0.05) * np.linspace(0.0, 1.0, len(t))
    pitch = 440 * np.exp(-1.5 * t) + 80
    tone = np.sin(2 * np.pi * pitch * t) * (1.0 - t) * 0.3
    w = _mix(sweep_noise * 0.9, tone) * _adsr(dur, a=0.2, d=0.2, s=0.6, r=0.4)
    return _to_sound(w, 0.4)


_SFX_BUILDERS = {
    "click": _sfx_click,
    "hover": _sfx_hover,
    "water": _sfx_water,
    "soil": _sfx_soil,
    "success": _sfx_success,
    "harvest": _sfx_harvest,
    "break": _sfx_break,
    "epiphany": _sfx_epiphany,
    "page": _sfx_page,
    "type": _sfx_type,
    "weed_pull": _sfx_weed_pull,
    "pop": _sfx_pop,
    "chirp": _sfx_chirp,
    "thud": _sfx_thud,
    "pest": _sfx_pest,
    "memory_in": _sfx_memory_in,
    "memory_out": _sfx_memory_out,
}


# ----------------------------------------------------------------------------
# 배경음 (루프) 정의
# ----------------------------------------------------------------------------
def _pad_chord(freqs, dur):
    """느린 트레몰로가 있는 지속 패드 화음."""
    t = _t(dur)
    wave = np.zeros(len(t))
    for f in freqs:
        wave += np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)
    tremolo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.4 * t)
    wave *= tremolo
    peak = np.max(np.abs(wave)) or 1.0
    return wave / peak


def _melody(seq, base_dur):
    """(freq, beats) 시퀀스를 부드러운 보이스로 연주."""
    pos = 0
    total_len = int(SAMPLE_RATE * sum(b for _, b in seq) * base_dur) + SAMPLE_RATE
    out = np.zeros(total_len)
    for f, beats in seq:
        d = beats * base_dur
        if f > 0:
            note = _tone(f, d * 1.3, harmonics=(1.0, 0.3, 0.1)) * _adsr(d * 1.3, a=0.02, d=0.15, s=0.4, r=0.3)
            out[pos:pos + len(note)] += note * 0.6
        pos += int(SAMPLE_RATE * d)
    return out[:pos]


def _pad_progression(chords, chord_dur, xfade=0.32):
    """화음들을 크로스페이드로 이어 '코드 진행'을 만든다.
    한 화음만 길게 깔던 기존 방식은 8초마다 같은 소리가 되풀이돼 단조로웠다 —
    화음을 바꿔 가며 길게 이으면 루프가 길어지고 음악에 흐름이 생긴다."""
    xf = max(1, int(SAMPLE_RATE * xfade))
    seg = int(SAMPLE_RATE * chord_dur)
    out = np.zeros(seg * len(chords) + xf)
    fin = np.linspace(0.0, 1.0, xf)
    fout = np.linspace(1.0, 0.0, xf)
    pos = 0
    for freqs in chords:
        c = _pad_chord(freqs, chord_dur + xfade)   # 길이 seg+xf
        c[:xf] *= fin
        c[-xf:] *= fout
        out[pos:pos + len(c)] += c
        pos += seg
    peak = np.max(np.abs(out)) or 1.0
    return out / peak


# 자주 쓰는 3화음 (mid 옥타브)
_C  = [130.81, 164.81, 196.00]   # C  (C3 E3 G3)
_G  = [123.47, 146.83, 196.00]   # G  (B2 D3 G3)
_Am = [110.00, 164.81, 220.00]   # Am (A2 E3 A3)
_F  = [174.61, 220.00, 261.63]   # F  (F3 A3 C4)
_Em = [164.81, 196.00, 246.94]   # Em (E3 G3 B3)
_Dm = [146.83, 174.61, 220.00]   # Dm (D3 F3 A3)


def _bgm_farm():
    """밭 — 가장 오래 들리는 곡. 8화음(약 29초) 진행으로 되도록 덜 반복되게."""
    pad = _pad_progression([_C, _G, _Am, _F, _C, _G, _F, _C], 3.6)
    mel = _melody([
        (392.0, 1), (440.0, 1), (523.25, 2), (440.0, 1), (392.0, 1), (329.63, 2),
        (293.66, 1), (329.63, 1), (392.0, 2), (0, 1), (329.63, 1), (293.66, 2),
        (440.0, 1), (523.25, 1), (587.33, 2), (523.25, 1), (440.0, 1), (392.0, 2),
        (349.23, 1), (392.0, 1), (440.0, 2), (0, 1), (392.0, 1), (329.63, 2),
        (392.0, 1), (440.0, 1), (523.25, 2), (659.25, 1), (587.33, 1), (523.25, 2),
        (440.0, 1), (392.0, 1), (329.63, 2), (0, 2), (261.63, 2),
    ], 0.5)
    return _mix(pad * 0.5, mel * 0.66)


def _bgm_night():
    pad = _pad_progression([_Am, _F, _C, _G, _Am, _Em, _F, _Em], 3.4)
    mel = _melody([
        (440.0, 2), (523.25, 1), (493.88, 1), (440.0, 2), (392.0, 2),
        (329.63, 2), (392.0, 1), (440.0, 1), (329.63, 2), (0, 2),
        (523.25, 2), (493.88, 1), (440.0, 1), (392.0, 2), (440.0, 2),
        (329.63, 2), (293.66, 1), (329.63, 1), (392.0, 2), (0, 2),
    ], 0.55)
    return _mix(pad * 0.55, mel * 0.54)


def _bgm_ending():
    pad = _pad_progression([_F, _C, _Dm, _Am, _F, _G, _C, _C], 3.6)
    mel = _melody([
        (349.23, 2), (392.0, 1), (440.0, 1), (523.25, 2), (440.0, 2),
        (392.0, 2), (349.23, 1), (392.0, 1), (261.63, 2), (0, 2),
        (440.0, 2), (392.0, 1), (349.23, 1), (392.0, 2), (440.0, 2),
        (392.0, 2), (349.23, 1), (329.63, 1), (261.63, 4),
    ], 0.6)
    return _mix(pad * 0.55, mel * 0.58)


def _bgm_ending_warm():
    """진·해피·성장 엔딩용 — 밝고 따뜻한 장조(G)."""
    G  = [196.0, 246.94, 293.66]   # G
    C  = [261.63, 329.63, 392.0]   # C
    D  = [146.83, 220.0, 293.66]   # D
    Em = [164.81, 246.94, 329.63]  # Em
    pad = _pad_progression([G, D, Em, C, G, C, D, G], 3.6)
    mel = _melody([
        (392.0, 1), (493.88, 1), (587.33, 2), (523.25, 1), (493.88, 1), (440.0, 2),
        (392.0, 1), (440.0, 1), (493.88, 2), (0, 1), (440.0, 1), (392.0, 2),
        (587.33, 1), (659.25, 1), (587.33, 2), (493.88, 1), (440.0, 1), (392.0, 2),
        (440.0, 1), (493.88, 1), (392.0, 2), (0, 2), (392.0, 2),
    ], 0.55)
    return _mix(pad * 0.5, mel * 0.6)


def _bgm_ending_sad():
    """조급·배드·시듦 엔딩용 — 느리고 가라앉은 단조(D)."""
    Dm = [146.83, 174.61, 220.0]
    Am = [110.0, 164.81, 220.0]
    BbM = [116.54, 174.61, 233.08]  # Bb
    C  = [130.81, 196.0, 261.63]
    Gm = [98.0, 146.83, 233.08]
    pad = _pad_progression([Dm, Am, BbM, Gm, Dm, BbM, C, Dm], 4.0)   # 느린 호흡
    mel = _melody([
        (293.66, 2), (261.63, 1), (293.66, 1), (349.23, 2), (293.66, 2),
        (261.63, 2), (246.94, 1), (220.0, 1), (196.0, 2), (0, 2),
        (293.66, 2), (349.23, 1), (293.66, 1), (261.63, 2), (220.0, 2),
        (233.08, 2), (220.0, 1), (196.0, 1), (146.83, 4),
    ], 0.72)
    return _mix(pad * 0.55, mel * 0.5)


def _bgm_event():
    """돌발상황·악)몽중농원 — 긴장감 있는 단조 루프 (두근대는 저음 펄스 + 불안한 아르페지오).
    16화음(약 35초)이라도 여전히 짧아 반복감이 남는다 → 32화음(약 70초)으로 늘려 반복을 확실히 해결한다."""
    Am  = [110.00, 130.81, 164.81]   # Am
    Dm  = [146.83, 174.61, 220.00]   # Dm
    E   = [164.81, 207.65, 246.94]   # E (불안한 장3도)
    F   = [174.61, 220.00, 261.63]   # F
    Gm  = [98.00, 146.83, 233.08]    # Gm
    Bb  = [116.54, 174.61, 233.08]   # Bb
    C   = [130.81, 164.81, 196.00]   # C
    Eb  = [155.56, 196.00, 233.08]   # Eb (기묘하고 웅장한 화음)
    Ab  = [103.83, 130.81, 155.56]   # Ab (기괴한 베이스 라인)

    # 32개 화음 진행 (총 70.4초)
    pad = _pad_progression([
        Am, Dm, F, E,      # 1절 (기본 진행)
        Am, Gm, Dm, E,     # 2절 (Gm 변주)
        F, Dm, Bb, Am,     # 3절 (Bb 변주)
        Gm, C, Dm, E,      # 4절 (C 변주)
        
        Am, Dm, F, E,      # 5절 (2절기 반복)
        Am, Gm, Dm, E,     # 6절
        Bb, F, Gm, Dm,     # 7절 (조금 더 깊은 어둠)
        Eb, Ab, Dm, E,     # 8절 (기묘한 Eb -> Ab로 극도의 긴장감 연출)
    ], 2.2, xfade=0.22)

    # 두근대는 저음 펄스 (심장박동 같은 8분음표)
    pulse = np.zeros(len(pad))
    beat = 0.5
    one = _tone(82.41, 0.2, harmonics=(1.0, 0.5)) * _adsr(0.2, a=0.002, d=0.05, s=0.2, r=0.09)
    b = 0
    while True:
        s = int(b * beat * SAMPLE_RATE)
        if s >= len(pulse):
            break
        seg = one[:len(pulse) - s]
        pulse[s:s + len(seg)] += seg
        b += 1

    # 불안하게 맴도는 아르페지오 — 늘어난 pad 길이에 맞춰 루프 횟수를 76회로 크게 확장
    arp = _melody([(440.0, 1), (523.25, 1), (659.25, 1), (587.33, 1)] * 76, 0.225)
    return _mix(pad * 0.5, pulse * 0.5, arp * 0.3)


_BGM_BUILDERS = {
    "farm": _bgm_farm,
    "night": _bgm_night,
    "event": _bgm_event,              # 돌발상황(밭 정리·선택형 이벤트)
    "ending": _bgm_ending,            # 중립(솜씨·노멀)
    "ending_warm": _bgm_ending_warm,  # 따뜻함(진·해피·성장)
    "ending_sad": _bgm_ending_sad,    # 슬픔(조급·배드·시듦)
}


# ----------------------------------------------------------------------------
# 초기화 / 공개 API
# ----------------------------------------------------------------------------
_INSTANT_SFX = {"click", "hover", "type"}


def _build_instant_only():
    """즉각 반응이 필요한 기본 효과음만 시작 시점에 먼저 준비한다(로드 또는 합성)."""
    for name in _INSTANT_SFX:
        try:
            get_or_create_sfx(name)
        except Exception as e:
            print("Instant SFX prepare failed:", name, e)


def _load_baked(category, name):
    """미리 구워둔 core/sound/<category>/<name>.ogg 를 불러온다(있으면)."""
    path = resource_path(os.path.join("sound", category, name + ".ogg"))
    if os.path.exists(path):
        try:
            return pygame.mixer.Sound(path)
        except Exception as e:
            print("구운 사운드 로드 실패:", path, e)
    return None


def get_or_create_sfx(name):
    """효과음 준비 래퍼 — 구운 .ogg를 우선 불러오고, 없으면 numpy로 즉석 합성."""
    if name not in _sfx:
        snd = _load_baked("sfx", name)
        if snd is None:
            builder = _SFX_BUILDERS.get(name)
            if builder and _ensure_np():
                try:
                    snd = builder()
                except Exception as e:
                    print("SFX lazy build failed:", name, e)
                    return None
        if snd is None:
            return None
        snd.set_volume(_sfx_volume)
        _sfx[name] = snd
    return _sfx.get(name)


def get_or_create_bgm(name):
    """배경음 준비 래퍼 — 구운 .ogg를 우선 불러오고, 없으면 numpy로 즉석 합성."""
    if name not in _bgm_sounds:
        snd = _load_baked("bgm", name)
        if snd is None:
            builder = _BGM_BUILDERS.get(name)
            if builder and _ensure_np():
                try:
                    snd = _to_sound(builder(), 0.9)
                except Exception as e:
                    print("BGM lazy build failed:", name, e)
                    return None
        if snd is None:
            return None
        _bgm_sounds[name] = snd
    return _bgm_sounds.get(name)


def init():
    """게임 시작 시 1회 호출. 실패하면 오디오는 비활성(무음)으로 남는다."""
    global _enabled, _bgm_channel
    if _enabled:
        return
    try:
        # 안드로이드는 오디오 지연/언더런이 잦아 버퍼를 조금 키운다(512→1024).
        from core.platform import IS_ANDROID
        buffer = 1024 if IS_ANDROID else 512
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, buffer)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        _bgm_channel = pygame.mixer.Channel(0)
        _build_instant_only()
        _enabled = True
    except Exception as e:
        print("오디오 비활성화 (장치 없음 또는 초기화 실패):", e)
        _enabled = False


def play(name):
    """효과음 재생 (지연 합성 반영)."""
    if not _enabled or _muted:
        return
    snd = get_or_create_sfx(name)
    if snd is None:
        return
    try:
        ch = pygame.mixer.find_channel(True)
        if ch is not None and ch is not _bgm_channel:
            ch.play(snd)
        else:
            snd.play()
    except Exception:
        pass


def type_tick(ch):
    """타자기 글자 효과음 — 공백·줄바꿈은 건너뛴다(빈 곳에서 안 울리게)."""
    if ch and not ch.isspace():
        play("type")


def play_bgm(name, fade_ms=600):
    """배경음 루프 재생 (지연 합성 반영)."""
    global _current_bgm
    if not _enabled:
        return
    if _current_bgm == name:
        return
    snd = get_or_create_bgm(name)
    if snd is None or _bgm_channel is None:
        return
    try:
        snd.set_volume(0.0 if _muted else _bgm_volume)
        _bgm_channel.play(snd, loops=-1, fade_ms=fade_ms)
        _current_bgm = name
    except Exception:
        pass


def stop_bgm(fade_ms=400):
    global _current_bgm
    if not _enabled or _bgm_channel is None:
        return
    try:
        _bgm_channel.fadeout(fade_ms)
    except Exception:
        pass
    _current_bgm = None


def toggle_mute():
    """음소거 토글. 현재 음소거 상태를 반환."""
    global _muted
    _muted = not _muted
    if _bgm_channel is not None:
        try:
            _bgm_channel.set_volume(0.0 if _muted else _bgm_volume)
        except Exception:
            pass
    return _muted


def is_muted():
    return _muted


def set_muted(value):
    """음소거 상태를 명시적으로 지정."""
    global _muted
    if bool(value) == _muted:
        return _muted
    return toggle_mute()


def get_sfx_volume():
    return _sfx_volume


def set_sfx_volume(v):
    """효과음 음량(0.0~1.0)을 즉시 반영."""
    global _sfx_volume
    _sfx_volume = max(0.0, min(1.0, float(v)))
    for snd in _sfx.values():
        try:
            snd.set_volume(_sfx_volume)
        except Exception:
            pass
    return _sfx_volume


def get_bgm_volume():
    return _bgm_volume


def set_bgm_volume(v):
    """배경음 음량(0.0~1.0)을 즉시 반영."""
    global _bgm_volume
    _bgm_volume = max(0.0, min(1.0, float(v)))
    if _bgm_channel is not None and not _muted:
        try:
            _bgm_channel.set_volume(_bgm_volume)
        except Exception:
            pass
    return _bgm_volume


def is_enabled():
    return _enabled


def pause_all():
    """앱이 백그라운드로 갈 때 — 모든 채널(효과음+배경음)을 일시정지.
    안드로이드에서 재생을 켠 채 백그라운드로 가면 복귀 시 크래시/멈춤이 알려져 있어
    반드시 멈춰야 한다."""
    if not _enabled:
        return
    try:
        pygame.mixer.pause()
    except Exception:
        pass


def resume_all():
    """앱이 포그라운드로 복귀할 때 — 일시정지했던 채널을 다시 재생."""
    if not _enabled:
        return
    try:
        pygame.mixer.unpause()
    except Exception:
        pass
