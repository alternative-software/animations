# -*- coding: utf-8 -*-
"""Синтез звуковой дорожки под анимацию (без внешних сэмплов)."""
import numpy as np, wave, struct, math

SR   = 48000
DUR  = 20.60
N    = int(SR * DUR)
rng  = np.random.default_rng(7)
mix  = np.zeros((2, N), dtype=np.float64)

# ---------- тайминг (совпадает с T в scene.html) ----------
T = dict(typing=1.00, msgIn=2.30, nav1=4.00, nav2=5.42, focus=6.30,
         typeA=6.60, typeB=8.35, sendMsg=8.95, kbHide=9.30, botTyping=9.45,
         botExec=10.10, botDone=13.10, nav3=14.70, nav4=16.05, deleted=17.40)
TAPS = [3.90, 5.30, 8.85, 14.60, 15.95]
NAVS = [T['nav1'], T['nav2'], T['nav3'], T['nav4']]
KEYS = [T['typeA'] + (i + 1) / 9 * (T['typeB'] - T['typeA']) - 0.05 for i in range(9)]
CAPS = [1.45, 4.45, 6.95, 10.40]

# ---------- утилиты ----------
def t_axis(dur): return np.arange(int(SR * dur)) / SR

def env_exp(dur, a=0.004, d=None, power=1.0):
    t = t_axis(dur); d = d if d else dur
    atk = np.clip(t / max(a, 1e-6), 0, 1)
    return (atk * np.exp(-t / d) ** power)

def env_ad(dur, a, r):
    t = t_axis(dur)
    e = np.where(t < a, t / max(a, 1e-9), np.exp(-(t - a) / max(r, 1e-9)))
    return np.clip(e, 0, 1)

def sine(f, dur, phase=0.0):
    t = t_axis(dur)
    f = np.asarray(f, dtype=float)
    if f.ndim == 0: f = np.full(t.shape, float(f))
    return np.sin(2 * np.pi * np.cumsum(f) / SR + phase)

def lp1(x, fc):
    """однополюсный ФНЧ, fc — скаляр или массив той же длины"""
    fc = np.asarray(fc, dtype=float)
    if fc.ndim == 0: fc = np.full(x.shape, float(fc))
    a = 1.0 - np.exp(-2 * np.pi * np.clip(fc, 20, SR / 2.2) / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(x.size):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y

def hp1(x, fc): return x - lp1(x, fc)

def noise(dur): return rng.standard_normal(int(SR * dur))

def place(sig, t0, gain=1.0, pan=0.0):
    i0 = int(t0 * SR)
    if i0 >= N: return
    s = sig[:max(0, N - i0)] * gain
    l = math.sqrt(0.5 * (1 - pan)); r = math.sqrt(0.5 * (1 + pan))
    mix[0, i0:i0 + s.size] += s * l * 1.414
    mix[1, i0:i0 + s.size] += s * r * 1.414

# ---------- сэмплы ----------
def ui_tap(soft=1.0):
    d = 0.09
    body = sine(np.linspace(2100, 1150, int(SR * d)), d) * env_exp(d, 0.0008, 0.016)
    tr   = hp1(noise(0.02), 2500) * env_exp(0.02, 0.0004, 0.004)
    out  = np.zeros(int(SR * d)); out[:tr.size] += tr * 0.5
    return (out + body * 0.8) * soft

def key_click(i):
    d = 0.055
    f = 1650 + (i % 3) * 180
    body = sine(np.linspace(f, f * 0.55, int(SR * d)), d) * env_exp(d, 0.0005, 0.009)
    tr   = hp1(noise(0.012), 3200) * env_exp(0.012, 0.0003, 0.0025)
    out  = np.zeros(int(SR * d)); out[:tr.size] += tr * 0.45
    return out + body * 0.55

def whoosh(dur=0.34, up=True, bright=1.0):
    n = noise(dur)
    f = np.linspace(400, 2600, n.size) if up else np.linspace(2400, 420, n.size)
    band = lp1(hp1(n, f * 0.45), f * 1.6 * bright)
    return band * env_ad(dur, dur * 0.35, dur * 0.3) * 1.2

def msg_in():
    """тёмное входящее уведомление"""
    d = 0.75
    sub  = sine(np.linspace(150, 62, int(SR * d)), d) * env_exp(d, 0.002, 0.11)
    t1   = sine(740, 0.5) * env_exp(0.5, 0.002, 0.075)
    t2   = sine(493.9, 0.6) * env_exp(0.6, 0.004, 0.13)
    bell = np.zeros(int(SR * d))
    bell[:t1.size] += t1 * 0.5
    i2 = int(0.11 * SR); bell[i2:i2 + t2.size] += t2[:bell.size - i2] * 0.42
    air = hp1(noise(0.25), 5000) * env_exp(0.25, 0.001, 0.05) * 0.18
    out = sub * 0.75 + bell
    out[:air.size] += air
    return out

def send_pop():
    d = 0.38
    sw = whoosh(0.26, up=True) * 0.55
    tone = sine(np.linspace(520, 1250, int(SR * 0.16)), 0.16) * env_exp(0.16, 0.002, 0.035)
    out = np.zeros(int(SR * d)); out[:sw.size] += sw
    i = int(0.06 * SR); out[i:i + tone.size] += tone * 0.7
    return out

def tick():
    d = 0.04
    return sine(np.linspace(1500, 900, int(SR * d)), d) * env_exp(d, 0.0006, 0.007)

def drone(dur):
    """гудение «обработки»"""
    t = t_axis(dur)
    f0 = 55 * (1 + 0.06 * t / dur)
    s = (sine(f0, dur) * 0.6 + sine(f0 * 2, dur) * 0.25 + sine(f0 * 3.01, dur) * 0.12)
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * 5.5 * t)
    hiss = lp1(hp1(noise(dur), 1800), np.linspace(2500, 6000, int(SR * dur))) * 0.05
    env = env_ad(dur, 0.25, 9e9) * (1 - np.clip((t - (dur - 0.3)) / 0.3, 0, 1))
    return (s * trem + hiss) * env

def success():
    freqs = [523.25, 659.25, 783.99, 1046.5]
    d = 1.1
    out = np.zeros(int(SR * d))
    for i, f in enumerate(freqs):
        seg = (sine(f, 0.9) * 0.7 + sine(f * 2, 0.9) * 0.18) * env_exp(0.9, 0.004, 0.19)
        o = int((0.055 * i) * SR)
        out[o:o + seg.size] += seg[:out.size - o] * (0.9 - 0.12 * i)
    sh = hp1(noise(0.5), 6000) * env_exp(0.5, 0.01, 0.11) * 0.22
    out[:sh.size] += sh
    return out * 0.55

def impact():
    """удар + цифровой глитч при удалении аккаунта"""
    d = 2.2
    sub = sine(np.linspace(78, 34, int(SR * 1.6)), 1.6) * env_exp(1.6, 0.003, 0.32)
    gl = noise(0.22)
    step = 420                                   # «биткрашер»
    gl = np.repeat(gl[::step], step)[:int(SR * 0.22)]
    gl = hp1(gl, 300) * env_exp(0.22, 0.001, 0.045)
    crack = hp1(noise(0.09), 2200) * env_exp(0.09, 0.0006, 0.018)
    out = np.zeros(int(SR * d))
    out[:sub.size] += sub * 0.95
    out[:gl.size] += gl * 0.85
    out[:crack.size] += crack * 0.8
    mid = sine(np.linspace(330, 110, int(SR * 0.45)), 0.45) * env_exp(0.45, 0.002, 0.075)
    out[:mid.size] += mid * 0.45
    tail = sine(np.linspace(240, 120, int(SR * 0.9)), 0.9) * env_exp(0.9, 0.02, 0.2) * 0.12
    i = int(0.08 * SR); out[i:i + tail.size] += tail
    return out

def riser(dur=1.2):
    n = noise(dur)
    f = np.linspace(500, 7000, n.size)
    band = hp1(n, f * 0.7) * np.linspace(0.05, 1.0, n.size) ** 2
    tone = sine(np.linspace(180, 900, int(SR * dur)), dur) * np.linspace(0, 0.5, int(SR * dur)) ** 2
    return (band * 0.6 + tone * 0.5) * env_ad(dur, dur * 0.95, 0.04)

# ---------- музыкальная подложка ----------
def pad(freqs, dur, detune=0.004):
    t = t_axis(dur); out = np.zeros(t.size)
    for f in freqs:
        out += sine(f, dur) * 0.5 + sine(f * (1 + detune), dur) * 0.4 + sine(f * 0.5, dur) * 0.25
    out = lp1(out / len(freqs), 1100)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.17 * t)
    return out * lfo

# тёмный пад (ля минор) -> светлый (до мажор) после «готово»
p1 = pad([220.0, 261.63, 329.63], T['botDone'] + 0.4)
p1 *= env_ad(p1.size / SR, 1.6, 9e9) * np.clip(np.linspace(1, 0, p1.size) * 6, 0, 1) ** 0.5
place(p1, 0.0, 0.11)

p2d = DUR - T['botDone']
p2 = pad([261.63, 329.63, 392.0, 523.25], p2d)
p2 *= env_ad(p2d, 0.5, 9e9) * np.clip((1 - (t_axis(p2d) - (p2d - 2.2)) / 2.2), 0, 1)
place(p2, T['botDone'], 0.10)

# пульс сабом
tb = 0.75
k = 0
while k * tb < DUR - 0.4:
    tt = k * tb
    amp = 0.6 if k % 2 else 1.0
    if tt > T['botDone']: amp *= 0.65
    puls = sine(np.linspace(72, 44, int(SR * 0.42)), 0.42) * env_exp(0.42, 0.004, 0.08)
    place(puls, tt, 0.075 * amp)
    if k % 2 == 1:
        hat = hp1(noise(0.05), 7000) * env_exp(0.05, 0.001, 0.009)
        place(hat, tt + tb / 2, 0.022, pan=0.25)
    k += 1

# ---------- события ----------
place(msg_in(), T['msgIn'], 0.62)
for i, tt in enumerate(TAPS):
    place(ui_tap(), tt, 0.26, pan=(-0.08 if i % 2 else 0.08))
for i, tt in enumerate(NAVS):
    place(whoosh(0.36, up=(i % 2 == 1)), tt + 0.02, 0.16, pan=(0.25 if i % 2 else -0.25))
place(whoosh(0.3, up=True, bright=0.7), T['focus'], 0.12)            # клавиатура вверх
place(whoosh(0.3, up=False, bright=0.7), T['kbHide'], 0.09)          # клавиатура вниз
for i, tt in enumerate(KEYS):
    place(key_click(i), tt, 0.19, pan=(-0.12 + 0.03 * i))
place(send_pop(), T['sendMsg'], 0.28)
place(sine(np.linspace(900, 1300, int(SR * 0.1)), 0.1) * env_exp(0.1, 0.004, 0.02), T['botTyping'], 0.07)

# «выполняю…» — гудение и тики ровно 3 секунды
place(drone(T['botDone'] - T['botExec'] + 0.05), T['botExec'], 0.10)
tt = T['botExec'] + 0.18
while tt < T['botDone'] - 0.05:
    place(tick(), tt, 0.075, pan=0.12)
    tt += 0.3
place(success(), T['botDone'], 0.38)

# удаление аккаунта
place(riser(1.25), T['deleted'] - 1.25, 0.22)
place(impact(), T['deleted'], 0.85)

# тики субтитров
for tt in CAPS:
    place(hp1(noise(0.05), 4500) * env_exp(0.05, 0.001, 0.009), tt, 0.055, pan=-0.1)

# ---------- мастер ----------
fade_in  = np.clip(np.arange(N) / (0.35 * SR), 0, 1)
fade_out = np.clip((N - np.arange(N)) / (0.55 * SR), 0, 1)
mix *= fade_in * fade_out
mix = np.tanh(mix * 1.25) / 1.25                 # мягкий лимитер
peak = np.max(np.abs(mix))
mix *= 0.92 / peak
print('peak %.3f  rms %.4f' % (peak, float(np.sqrt(np.mean(mix ** 2)))))

data = (np.clip(mix.T, -1, 1) * 32767).astype('<i2')
with wave.open('out/soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(data.tobytes())
print('out/soundtrack.wav', data.shape)
