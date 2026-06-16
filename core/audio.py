"""몽중농원 절차적 오디오 엔진.

모든 효과음과 배경음을 numpy로 런타임에 합성한다 — 외부 음원 파일 불필요.
오디오 장치가 없거나 mixer 초기화에 실패해도 모든 함수가 조용히 no-op으로
동작하도록 설계되어 게임 진행을 막지 않는다.
"""

import numpy as np
import pygame

SAMPLE_RATE = 44100

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
    """간단한 1차 저역통과 (부드럽게)."""
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += alpha * (x[i] - acc)
        y[i] = acc
    return y


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


def _bgm_farm():
    bar = 4.0
    pad = _pad_chord([130.81, 164.81, 196.0], bar * 2)
    mel = _melody([
        (392.0, 1), (440.0, 1), (523.25, 1), (440.0, 1),
        (392.0, 1), (329.63, 1), (392.0, 2),
        (293.66, 1), (329.63, 1), (392.0, 1), (329.63, 1),
        (293.66, 2), (261.63, 2),
    ], 0.5)
    return _mix(pad * 0.5, mel * 0.7)


def _bgm_night():
    bar = 4.0
    pad = _pad_chord([110.0, 130.81, 164.81], bar * 2)
    mel = _melody([
        (440.0, 2), (523.25, 1), (493.88, 1),
        (440.0, 2), (392.0, 2),
        (329.63, 2), (392.0, 1), (440.0, 1),
        (329.63, 4),
    ], 0.55)
    return _mix(pad * 0.55, mel * 0.55)


def _bgm_ending():
    bar = 4.0
    pad = _pad_chord([174.61, 220.0, 261.63], bar * 2)
    mel = _melody([
        (349.23, 2), (392.0, 1), (440.0, 1),
        (523.25, 2), (440.0, 2),
        (392.0, 2), (349.23, 1), (392.0, 1),
        (261.63, 4),
    ], 0.6)
    return _mix(pad * 0.55, mel * 0.6)


def _bgm_ending_warm():
    """진·해피·성장 엔딩용 — 밝고 따뜻한 장조."""
    bar = 4.0
    pad = _pad_chord([196.0, 246.94, 293.66], bar * 2)   # G장조 느낌
    mel = _melody([
        (392.0, 1), (493.88, 1), (587.33, 2),
        (523.25, 1), (493.88, 1), (440.0, 2),
        (392.0, 1), (440.0, 1), (493.88, 2),
        (392.0, 4),
    ], 0.55)
    return _mix(pad * 0.5, mel * 0.62)


def _bgm_ending_sad():
    """조급·배드·시듦 엔딩용 — 느리고 가라앉은 단조."""
    bar = 4.0
    pad = _pad_chord([146.83, 174.61, 220.0], bar * 2)   # D단조 느낌
    mel = _melody([
        (293.66, 2), (261.63, 1), (293.66, 1),
        (349.23, 2), (293.66, 2),
        (261.63, 2), (246.94, 1), (220.0, 1),
        (196.0, 4),
    ], 0.72)   # 느린 호흡
    return _mix(pad * 0.55, mel * 0.52)


_BGM_BUILDERS = {
    "farm": _bgm_farm,
    "night": _bgm_night,
    "ending": _bgm_ending,            # 중립(솜씨·노멀)
    "ending_warm": _bgm_ending_warm,  # 따뜻함(진·해피·성장)
    "ending_sad": _bgm_ending_sad,    # 슬픔(조급·배드·시듦)
}


# ----------------------------------------------------------------------------
# 초기화 / 공개 API
# ----------------------------------------------------------------------------
def _build_all():
    for name, builder in _SFX_BUILDERS.items():
        try:
            _sfx[name] = builder()
            _sfx[name].set_volume(_sfx_volume)
        except Exception as e:
            print("SFX build failed:", name, e)
    for name, builder in _BGM_BUILDERS.items():
        try:
            # 배경음 빌더는 numpy 파형을 돌려주므로 반드시 Sound로 변환해야 한다.
            # (이 변환이 빠져 있어 play_bgm의 set_volume에서 조용히 실패, 배경음이 안 나오던 버그)
            _bgm_sounds[name] = _to_sound(builder(), 0.9)
        except Exception as e:
            print("BGM build failed:", name, e)


def init():
    """게임 시작 시 1회 호출. 실패하면 오디오는 비활성(무음)으로 남는다."""
    global _enabled, _bgm_channel
    if _enabled:
        return
    try:
        pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        _bgm_channel = pygame.mixer.Channel(0)
        _build_all()
        _enabled = True
    except Exception as e:
        print("오디오 비활성화 (장치 없음 또는 초기화 실패):", e)
        _enabled = False


def play(name):
    """효과음 재생."""
    if not _enabled or _muted:
        return
    snd = _sfx.get(name)
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
    """배경음 루프 재생. 같은 트랙이면 무시."""
    global _current_bgm
    if not _enabled:
        return
    if _current_bgm == name:
        return
    snd = _bgm_sounds.get(name)
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
