"""Synthesises the soundtrack for the launch video (120 BPM, cuts land on bars). numpy only.
   python3 audio.py  ->  out/music.wav"""
import numpy as np, wave, os

SR = 44100
DUR = 44.0
N = int(SR * DUR)
rs = np.random.RandomState(3)
BEAT = 0.5


def buf(): return np.zeros(N)
def t_(n): return np.arange(n) / SR
def hz(m): return 440.0 * 2 ** ((m - 69) / 12)

def add(dst, sig, at, gain=1.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    n = min(len(sig), N - i)
    dst[i:i + n] += sig[:n] * gain

def lp(x, cutoff):
    """FFT brick-ish low-pass with a soft roll-off (cutoff may be a scalar)."""
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / (1 + (f / cutoff) ** 4), len(x))

def hp(x, cutoff):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X * (f / cutoff) ** 4 / (1 + (f / cutoff) ** 4), len(x))

def saw(freq, n, det=0.0):
    ph = (t_(n) * freq * (1 + det)) % 1.0
    return 2 * ph - 1

def env(n, a, d, sus=0.0, r=0.02):
    e = np.ones(n) * sus; tt = t_(n)
    att = np.clip(tt / max(a, 1e-4), 0, 1)
    dec = sus + (1 - sus) * np.exp(-np.clip(tt - a, 0, None) / d)
    e = att * dec
    k = int(r * SR)
    if k < n: e[-k:] *= np.linspace(1, 0, k)
    return e

# ---------- instruments ----------
def kick():
    n = int(.42 * SR); tt = t_(n)
    f = 48 + 110 * np.exp(-tt / .035)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / .16)
    s += .35 * rs.randn(n) * np.exp(-tt / .004)
    return np.tanh(s * 1.6)

def hat(open_=False):
    n = int((.22 if open_ else .06) * SR)
    return hp(rs.randn(n), 7000) * np.exp(-t_(n) / (.07 if open_ else .014))

def clap():
    n = int(.3 * SR); tt = t_(n); x = rs.randn(n)
    x = hp(lp(x, 4500), 900)
    e = sum(np.exp(-np.clip(tt - d, 0, None) / .012) * (tt >= d) for d in (0, .011, .023)) * .5 + np.exp(-tt / .09) * .6
    return x * e

def pluck(m, dur=.4, bright=3200):
    n = int(dur * SR); f = hz(m)
    s = saw(f, n) * .6 + saw(f, n, .006) * .4 + np.sin(2 * np.pi * f * 2 * t_(n)) * .2
    return lp(s, bright) * env(n, .003, .11)

def pad(notes, dur, cutoff=1400, a=.4):
    n = int(dur * SR); s = np.zeros(n)
    for m in notes:
        for det in (-.004, 0, .005):
            s += saw(hz(m), n, det)
    s = lp(s / (len(notes) * 3), cutoff)
    return s * env(n, a, 99, 1, .5)

def bass(m, dur=.22):
    n = int(dur * SR); f = hz(m)
    s = np.sin(2 * np.pi * f * t_(n)) * .9 + lp(saw(f, n), 500) * .5
    return np.tanh(s * 1.4) * env(n, .004, .25, 0, .03)

def boom():
    n = int(3 * SR); tt = t_(n)
    f = 34 + 60 * np.exp(-tt / .09)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / .7)
    s += lp(rs.randn(n), 900) * np.exp(-tt / .25) * .5
    s += hp(rs.randn(n), 3000) * np.exp(-tt / .6) * .12      # crash tail
    return np.tanh(s * 1.5)

def riser(dur):
    n = int(dur * SR); x = rs.randn(n); p = np.linspace(0, 1, n)
    out = np.zeros(n); seg = 2048
    for i in range(0, n, seg):                                 # stepped rising band-pass
        c = 300 * (40 ** p[i]); j = min(n, i + seg + 512)
        out[i:j] += hp(lp(x[i:j], c * 1.6), c * .6) * np.hanning(j - i) if j - i > 8 else 0
    tone = np.sin(2 * np.pi * np.cumsum(200 * 4 ** p) / SR) * .15
    return (out * .5 + tone) * p ** 2.2

def whoosh(dur=.7):
    n = int(dur * SR); x = hp(lp(rs.randn(n), 5000), 500)
    return x * np.hanning(n) ** 2

def tick():
    n = int(.03 * SR)
    return np.sin(2 * np.pi * 2400 * t_(n)) * np.exp(-t_(n) / .004)

def stab(notes, bright=2600):
    n = int(.5 * SR); s = sum(saw(hz(m), n) + saw(hz(m), n, .007) for m in notes) / (2 * len(notes))
    return lp(s, bright) * env(n, .002, .12)

# ---------- arrangement ----------
#        Bb            F             Dm            C
CH = [(58, 62, 65, 70), (53, 57, 60, 65), (50, 57, 62, 65), (48, 55, 60, 64)]
ROOT = [34, 29, 38, 36]

drums, music, low, fx = buf(), buf(), buf(), buf()
K, H, OH, C, TK = kick(), hat(), hat(True), clap(), tick()
bar = lambda b: 12 + b * 2.0

# intro 0-4: dark pad + ticking
add(music, pad((38, 50, 57, 62, 65), 4.4, 700, 1.2), 0, .5)
for i in range(4, 8): add(fx, TK, i * BEAT, .25)
add(fx, whoosh(.5), 1.7, .1)
add(fx, riser(1.2), 2.8, .2)

# problem 4-8: one hit per slam word, rising tension
for i, tt in enumerate((4, 5, 6, 7)):
    add(low, K, tt, 1.0)
    add(music, stab((50 + i, 57 + i, 62 + i), 1800 + 300 * i), tt, .5)
    add(fx, whoosh(.3), tt - .12, .12)
    for s in range(1, 4): add(fx, TK, tt + s * .25, .16)
add(fx, riser(2.0), 6.0, .5)
for i in range(16): add(drums, C, 7 + i / 16, .12 + .3 * i / 16)

# logo 8-12: impact + wide chord, arp fades in
add(low, boom(), 8, 1.0)
add(music, pad((46, 58, 62, 65, 70, 74), 2.2, 2600, .02), 8, .7)
add(music, pad((41, 53, 57, 60, 65, 72), 2.2, 2200, .2), 10, .6)
for i in range(16):
    add(music, pluck(CH[1][i % 4] + 12, .3), 10 + i * .125, .1 + .35 * i / 16)
for i in range(8): add(drums, H, 11 + i * .125, .1 + .2 * i / 8)
add(fx, riser(1.0), 11.0, .3)

# groove 12-34 (11 bars) then outro groove 38-42
def groove(b0, bars, level=1.0, hi=False, kicks=True):
    for b in range(bars):
        t0 = b0 + b * 2.0; ci = b % 4; ch = CH[ci]
        add(music, pad(ch, 2.1, 1500, .08), t0, .32 * level)
        for q in range(4):
            tq = t0 + q * BEAT
            if kicks: add(low, K, tq, .95)
            add(drums, OH, tq + .25, .16)
            if q % 2: add(drums, C, tq, .5)
            for s in range(4): add(drums, H, tq + s * .125, .1 if s % 2 else .16)
        for e in range(8):                                    # offbeat bass
            if e % 2 or e in (0,): add(low, bass(ROOT[ci] + (12 if e == 7 else 0)), t0 + e * .25, .7)
        pat = [0, 1, 2, 3, 2, 1, 3, 2, 0, 2, 3, 1, 2, 3, 1, 2]
        for s, pi in enumerate(pat):
            add(music, pluck(ch[pi] + 12 + (12 if hi and s % 4 == 3 else 0), .34, 3600 if hi else 2800), t0 + s * .125, .34 * level)

groove(12, 4)
groove(20, 4, hi=True)
groove(28, 3, hi=True)
for tt in (12, 20, 28):
    add(low, boom(), tt, .55); add(fx, whoosh(.6), tt - .35, .3)
add(fx, riser(1.0), 19.0, .3); add(fx, riser(1.0), 27.0, .35)
for tt in (13.22, 19.86, 23.92): add(fx, TK, tt, .5)          # mouse clicks

# audience 34-38: drums drop out, stab per word, riser into the outro
add(music, pad((46, 53, 58, 62), 4.0, 1100, .3), 34, .45)
add(low, boom(), 34, .5)
for i, tt in enumerate((34.5, 35.5, 36.5)):
    add(music, stab((58 + 2 * i, 65 + 2 * i, 70 + 2 * i), 3000), tt, .7); add(low, K, tt, .9)
    add(fx, whoosh(.3), tt - .15, .15)
add(fx, riser(2.0), 36.0, .55)
for i in range(16): add(drums, C, 37 + i / 16, .1 + .35 * i / 16)

# outro 38-44
add(low, boom(), 38, 1.0)
groove(38, 2, level=.9, hi=True)
add(music, pad((41, 53, 57, 60, 65, 69, 72), 5.5, 2400, .05), 38, .5)
add(music, pad((41, 53, 60, 65, 69), 2.0, 1800, .05), 42, .5)
add(low, boom(), 42, .6)
add(fx, TK, 41.5, .5)

# ---------- mix ----------
def reverb(x, secs=1.8, mix=.25):
    n = int(secs * SR); ir = rs.randn(n) * np.exp(-t_(n) / (secs / 5)); ir = hp(ir, 400)
    L = len(x) + n; w = np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
    return x + w / (np.abs(w).max() + 1e-9) * np.abs(x).max() * mix

def echo(x, d=.375, fb=.35, mix=.3):
    out = x.copy(); k = int(d * SR); tap = x.copy()
    for _ in range(5):
        tap = np.concatenate([np.zeros(k), tap[:-k]]) * fb; out += tap * mix / fb
    return out

duck = np.ones(N)                                              # sidechain to the kick
kick_times = [12 + i * BEAT for i in range(44)] + [38 + i * BEAT for i in range(8)]
shape = 1 - .55 * np.exp(-t_(int(.3 * SR)) / .09)
for kt in kick_times:
    i = int(kt * SR); n = min(len(shape), N - i); duck[i:i + n] = np.minimum(duck[i:i + n], shape[:n])

music = reverb(echo(music), 2.2, .3) * duck
drums = reverb(drums, .9, .12)
fx = reverb(fx, 2.0, .35)
mono = low * .8 + drums * .55 + music * .85 + fx * .8

# stereo width from a short Haas delay on the non-bass parts
side = music * .85 + fx * .8 + drums * .3; k = int(.012 * SR)
sd = np.concatenate([np.zeros(k), side[:-k]])
Lc, Rc = mono + .25 * (side - sd), mono - .25 * (side - sd)
st = np.stack([Lc, Rc], 1)
fade = np.ones(N); f0 = int(42.6 * SR); fade[f0:] = np.linspace(1, 0, N - f0) ** 1.5
st *= fade[:, None]
st = np.tanh(st / np.abs(st).max() * 2.2)                      # glue / soft limit
st = st / np.abs(st).max() * .89

os.makedirs('out', exist_ok=True)
with wave.open('out/music.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((st * 32767).astype('<i2').tobytes())
print('wrote out/music.wav', st.shape)
