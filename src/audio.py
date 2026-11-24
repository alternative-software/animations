# -*- coding: utf-8 -*-
"""Синтез звуковой дорожки под анимацию (без сэмплов, чистый numpy).
Тайминг совпадает с объектом T в src/scene.html."""
import numpy as np, wave, math

SR   = 48000
DUR  = 59.60
N    = int(SR * DUR)
rng  = np.random.default_rng(7)
mix  = np.zeros((2, N), dtype=np.float64)

# ---------- тайминг (совпадает с T в scene.html) ----------
T = dict(
  scrollA=0.90, scrollAe=2.05, scrollB=2.45, scrollBe=3.25,
  hl=3.45, tapCat=4.35, sheetIn=4.45, tapBuy=6.30, modalIn=6.45, tapYes=7.55,
  fly=7.95, flyEnd=8.95, avPop=8.92,
  navList1=12.50, timerOn=12.95, notifIn=13.60, tapNotif=14.55, navDox1=14.75,
  d1type=15.30, d1=16.10, kbOn=17.15, qA=17.35, qB=18.25, sendQ=18.60,
  d2type=19.05, d2=19.85, capName=20.40,
  okA=24.60, okB=25.90, sendOk=26.20, d3type=26.65, d3=27.25,
  noA=27.85, noB=29.25, sendNo=29.55, kbOff=29.90,
  d4type=30.15, gift1=30.80, gift2=31.55,
  tapBack1=32.90, navList2=33.02, tapBot=34.10, navBot=34.22,
  focusBot=34.95, uA=35.25, uB=36.95, tapSend=37.35, sendU=37.45,
  kbHide=37.80, botTyping=37.95, botExec=38.60, botDone=41.60,
  tapBack2=43.10, navList3=43.22, tapDox=44.30, navDox2=44.42,
  ghost=45.20, delBtn=46.40, END=59.60)

TAPS = [T['tapCat'], T['tapBuy'], T['tapYes'], T['tapNotif'], T['sendQ']-0.08,
        T['sendOk']-0.08, T['sendNo']-0.08, T['tapBack1'], T['tapBot'],
        T['tapSend'], T['tapBack2'], T['tapDox']]
NAVS = [T['navList1'], T['navDox1'], T['navList2'], T['navBot'], T['navList3'], T['navDox2']]

def keys(a, b, text):
    n = len(text)
    return [a + (i + 1) / n * (b - a) - 0.03 for i in range(n)]
KEYS = (keys(T['qA'], T['qB'], 'ты кто?') + keys(T['okA'], T['okB'], 'хорошо, хорошо. Щас отправлю подарок')
        + keys(T['noA'], T['noB'], 'черт, у меня нету звёзд на передачу') + keys(T['uA'], T['uB'], '@doxsv_tbog'))
CAPS = [9.15, 20.40, 46.95, 50.70, 54.40]

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


# =====================================================================
#                        музыкальная подложка
# =====================================================================
def pad(freqs, dur, detune=0.004, cut=1100):
    t = t_axis(dur); out = np.zeros(t.size)
    for f in freqs:
        out += sine(f, dur) * 0.5 + sine(f * (1 + detune), dur) * 0.4 + sine(f * 0.5, dur) * 0.25
    out = lp1(out / len(freqs), cut)
    lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.17 * t)
    return out * lfo

def bed(freqs, t0, t1, gain, fade_in=1.2, fade_out=1.4, cut=1100):
    d = t1 - t0
    p = pad(freqs, d, cut=cut)
    t = t_axis(d)
    p *= np.clip(t / fade_in, 0, 1) * np.clip((d - t) / fade_out, 0, 1)
    place(p, t0, gain)

A3, C4, E4, F4, G4, A4, C5, E5, D4, B3 = 220.0, 261.63, 329.63, 349.23, 392.0, 440.0, 523.25, 659.25, 293.66, 246.94
# S1 — светлый «магазинный» пад
bed([C4, E4, G4, C5], 0.0, 12.9, 0.085, 1.4, 1.0, cut=1500)
# S2-S3 — тёмный минор
bed([A3, C4, E4], 12.6, 24.2, 0.085, 1.6, 0.8, cut=900)
bed([A3, C4, F4], 23.8, 32.6, 0.095, 0.8, 0.8, cut=900)
# S4 — ожидание
bed([A3, D4, F4], 32.4, 41.8, 0.085, 1.0, 0.6, cut=800)
# S5 — эпичный мажор
bed([C4, G4, C5, E5], 41.5, 50.9, 0.105, 0.9, 0.5, cut=1700)
bed([F4, A4, C5, E5], 50.5, 59.6, 0.115, 0.7, 2.6, cut=1700)

# пульс сабом: тихий в начале, плотный в тревожной части, мягкий в финале
tb, kk = 0.75, 0
while kk * tb < DUR - 0.5:
    tt = kk * tb
    amp = 0.55 if kk % 2 else 1.0
    if tt < T['navList1']:          amp *= 0.5
    elif tt < T['capName']:         amp *= 0.8
    elif tt < T['botDone']:         amp *= 1.25
    else:                           amp *= 0.9
    place(sine(np.linspace(72, 44, int(SR * 0.42)), 0.42) * env_exp(0.42, 0.004, 0.08), tt, 0.075 * amp)
    if kk % 2 == 1:
        place(hp1(noise(0.05), 7000) * env_exp(0.05, 0.001, 0.009), tt + tb / 2, 0.02, pan=0.25)
    kk += 1

# =====================================================================
#                             события
# =====================================================================
def shimmer(dur=0.9, f0=1400, n=7, up=True):
    out = np.zeros(int(SR * dur))
    for i in range(n):
        f = f0 * (1.26 ** (i if up else n - i))
        seg = sine(f, 0.35) * env_exp(0.35, 0.002, 0.055)
        o = int(i * 0.055 * SR)
        out[o:o + seg.size] += seg[:out.size - o] * (0.9 - 0.08 * i)
    return out * 0.5

def ding(f=1174.7, dur=1.4, bright=1.0):
    """чистое «дзынь» с обертонами"""
    out = np.zeros(int(SR * dur))
    for mult, g, dcy in ((1, 1.0, 0.33), (2.01, 0.5, 0.2), (3.02, 0.26, 0.13), (5.4, 0.14, 0.08)):
        s = sine(f * mult, dur) * env_exp(dur, 0.002, dcy)
        out += s * g
    air = hp1(noise(0.3), 6500) * env_exp(0.3, 0.001, 0.05) * 0.2 * bright
    out[:air.size] += air
    return out * 0.45

def coin():
    d = 0.7
    out = np.zeros(int(SR * d))
    for i, f in enumerate((1318.5, 1760.0, 2093.0)):
        seg = sine(f, 0.5) * env_exp(0.5, 0.001, 0.1)
        o = int(i * 0.045 * SR); out[o:o + seg.size] += seg[:out.size - o] * (0.8 - 0.2 * i)
    return out * 0.5

def swipe(dur=0.5, up=True):
    n = noise(dur)
    f = np.linspace(700, 2200, n.size) if up else np.linspace(1900, 600, n.size)
    band = lp1(hp1(n, f * 0.5), f * 1.5)
    return band * env_ad(dur, dur * 0.4, dur * 0.35) * 0.9

def rumble(dur=2.2):
    t = t_axis(dur)
    s = sine(np.linspace(46, 33, int(SR * dur)), dur) * 0.8 + sine(np.linspace(92, 66, int(SR * dur)), dur) * 0.25
    nz = lp1(noise(dur), 160) * 0.5
    return (s + nz) * env_ad(dur, 0.06, dur * 0.42)

def ghost_fx():
    d = 2.6
    out = np.zeros(int(SR * d))
    rev = whoosh(0.9, up=False, bright=0.8) * 0.8                 # «всасывание»
    out[:rev.size] += rev
    sub = sine(np.linspace(90, 30, int(SR * 1.8)), 1.8) * env_exp(1.8, 0.004, 0.34)
    out[:sub.size] += sub * 0.9
    gl = noise(0.3); step = 380
    gl = np.repeat(gl[::step], step)[:int(SR * 0.3)]
    out[:gl.size] += hp1(gl, 400) * env_exp(0.3, 0.001, 0.05) * 0.5
    sh = shimmer(0.9, 900, 7, up=False)
    o = int(0.25 * SR); out[o:o + sh.size] += sh[:out.size - o] * 0.5
    return out

# --- S1: витрина ---
place(swipe(0.55, up=True),  T['scrollA'] + 0.05, 0.10, pan=0.1)
place(swipe(0.45, up=False), T['scrollB'] + 0.05, 0.08, pan=-0.1)
place(shimmer(0.6, 1800, 5), T['hl'], 0.06)
place(whoosh(0.38, up=True), T['sheetIn'], 0.14)                    # раскрытие карточки
place(ding(880, 0.5), T['sheetIn'] + 0.08, 0.10)
place(whoosh(0.3, up=True, bright=0.8), T['modalIn'], 0.11)
place(riser(0.95), T['fly'] - 0.1, 0.13)                            # разгон полёта
place(shimmer(0.85, 1500, 8), T['fly'] + 0.05, 0.11)
place(ding(1567.98, 1.8, 1.2), T['avPop'], 0.40)                    # «дзынь» — подарок в профиле
place(coin(), T['avPop'] + 0.02, 0.22)
place(success(), T['avPop'] + 0.06, 0.16)

# --- общие: тапы, переходы, клавиши ---
for i, tt in enumerate(TAPS):
    place(ui_tap(), tt, 0.24, pan=(-0.08 if i % 2 else 0.08))
for i, tt in enumerate(NAVS):
    place(whoosh(0.36, up=(i % 2 == 1)), tt + 0.02, 0.15, pan=(0.25 if i % 2 else -0.25))
for i, tt in enumerate(KEYS):
    place(key_click(i), tt, 0.14, pan=(-0.1 + 0.02 * (i % 9)))
place(whoosh(0.3, up=True,  bright=0.7), T['kbOn'], 0.11)
place(whoosh(0.3, up=False, bright=0.7), T['kbOff'], 0.08)
place(whoosh(0.3, up=True,  bright=0.7), T['focusBot'], 0.11)
place(whoosh(0.3, up=False, bright=0.7), T['kbHide'], 0.08)
for tt in (T['sendQ'], T['sendOk'], T['sendNo'], T['sendU']):
    place(send_pop(), tt, 0.26)

# --- S2: угроза ---
place(msg_in(), T['notifIn'], 0.62)
place(msg_in(), T['d1'], 0.40)
place(msg_in(), T['d2'], 0.36)
place(msg_in(), T['d3'], 0.30)
tt = T['timerOn'] + 0.4                                             # тиканье таймера
while tt < T['botDone']:
    hot = 1.0 if tt > 34 else 0.6
    place(tick(), tt, 0.055 * hot, pan=0.3)
    tt += 1.0
place(riser(1.3), T['capName'] - 1.3, 0.17)                         # подъём к «Но это было не моё имя»
place(impact(), T['capName'], 0.48)
place(rumble(2.4), T['capName'], 0.22)

# --- S3: подарки-медведи ---
for tt in (T['gift1'], T['gift2']):
    place(ding(1046.5, 1.1), tt, 0.26)
    place(shimmer(0.5, 1600, 4), tt + 0.05, 0.07)

# --- S4: бот ---
place(drone(T['botDone'] - T['botExec'] + 0.05), T['botExec'], 0.11)
tt = T['botExec'] + 0.2
while tt < T['botDone'] - 0.05:
    place(tick(), tt, 0.07, pan=0.12)
    tt += 0.3
place(riser(0.8), T['botDone'] - 0.8, 0.12)
place(success(), T['botDone'], 0.42)
place(ding(1567.98, 1.6), T['botDone'] + 0.02, 0.20)

# --- S5: исчезновение и финал ---
place(ghost_fx(), T['ghost'], 0.48)
place(ui_tap(0.8), T['delBtn'], 0.14)
place(riser(1.5), 46.95 - 1.5, 0.16)
for i, tt in enumerate(CAPS):                                        # мягкий акцент на субтитрах
    place(hp1(noise(0.05), 4500) * env_exp(0.05, 0.001, 0.009), tt, 0.05, pan=-0.1)
    if i >= 2:
        place(ding(1046.5 * (1.12 ** (i - 2)), 1.2, 0.6), tt + 0.02, 0.10)
place(impact(), 54.40, 0.30)
place(success(), 57.6, 0.22)

# =====================================================================
#                               мастер
# =====================================================================
fade_in  = np.clip(np.arange(N) / (0.45 * SR), 0, 1)
fade_out = np.clip((N - np.arange(N)) / (1.1 * SR), 0, 1)
mix *= fade_in * fade_out
mix = np.tanh(mix * 1.25) / 1.25
peak = np.max(np.abs(mix))
mix *= 0.92 / peak
print('peak %.3f  rms %.4f  dur %.2fs' % (peak, float(np.sqrt(np.mean(mix ** 2))), DUR))

data = (np.clip(mix.T, -1, 1) * 32767).astype('<i2')
with wave.open('out/soundtrack.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(data.tobytes())
print('out/soundtrack.wav', data.shape)
