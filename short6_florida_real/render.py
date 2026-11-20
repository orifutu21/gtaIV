"""
SHORT 6 — «Escenas del tráiler de GTA 6 que pasaron de verdad»
Vertical 1080x1920, 30 fps. Reutiliza el estilo y utilidades del Short 1.

  python3 gen_voz.py     -> voz/voz.wav + voz/timeline.json (voz IA, tiempos por palabra)
  python3 render.py      -> short6_florida_real.mp4 (+ _sin_musica / _solo_voz)
  FRAMES=60,300 python3 render.py   -> solo PNGs de previsualización
"""
import importlib.util, json, math, os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("base", os.path.join(HERE, "..", "short1_leonida", "render.py"))
B = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(B)

W, H, FPS = B.W, B.H, B.FPS
YELLOW, PINK, TEAL, WHITE, BLACK, RED, ORANGE = B.YELLOW, B.PINK, B.TEAL, B.WHITE, B.BLACK, B.RED, B.ORANGE
GREEN = (60, 220, 110)
text_img, paste_center, pop, prog = B.text_img, B.paste_center, B.pop, B.prog
ease_out, ease_in_out, lerp, clamp = B.ease_out, B.ease_in_out, B.lerp, B.clamp
FONT_BLACK, FONT_BLACK_IT, FONT_BOLD = B.FONT_BLACK, B.FONT_BLACK_IT, B.FONT_BOLD

TL = json.load(open(os.path.join(HERE, "voz", "timeline.json")))
DUR = TL["duration"]
NFRAMES = int(DUR * FPS)
P = {p["id"]: p for p in TL["phrases"]}
S = {k: v["start"] for k, v in P.items()}
SEG = ["hook", "c1", "c2", "c3", "c4", "c5", "c6", "cta"]
# cada bloque visual dura desde el inicio de su frase hasta el inicio de la siguiente
SEG_END = {k: (S[SEG[i + 1]] if i + 1 < len(SEG) else DUR) for i, k in enumerate(SEG)}

def wt(pid, word, nth=0):
    hits = [w for w in P[pid]["words"] if w["w"].strip(",.…¿?¡!") == word]
    return hits[nth]["s"] if hits else S[pid]

# --------------------------------------------------------------------------
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
_emo = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _emo:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox())
        sc = size / max(im.size)
        _emo[k] = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    return _emo[k]

def seg_alpha(t, key, fade=0.2):
    a, b = S[key] - 0.1, SEG_END[key]
    return clamp(min((t - a) / 0.12, (b - t) / fade))

def badge_img(text, size, bg=YELLOW, fg=BLACK, rad=24):
    tag = text_img(text, size, fill=fg, stroke=0, shadow=False)
    bw, bh = tag.width + 34, tag.height + 8
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((0, 0, bw - 1, bh - 1), rad, fill=bg + (255,), outline=BLACK + (255,), width=6)
    im.alpha_composite(tag, ((bw - tag.width) // 2, (bh - tag.height) // 2))
    return im

def stamp(canvas, text, cx, cy, t0, t, color=RED, size=110, rot=-12):
    if t < t0:
        return
    s = 1 + 1.8 * (1 - ease_out(prog(t, t0, t0 + 0.22)))
    ti = text_img(text, size, fill=color, stroke=0, shadow=False)
    bw, bh = ti.width + 40, ti.height + 10
    im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle((4, 4, bw - 5, bh - 5), 18, fill=(255, 255, 255, 235), outline=color + (255,), width=12)
    im.alpha_composite(ti, ((bw - ti.width) // 2, (bh - ti.height) // 2))
    paste_center(canvas, im, cx, cy, s, clamp(prog(t, t0, t0 + 0.12)), rot=rot)

# --------------------------------------------------------------------------
# cabecera y escenas del Short 6
def header(canvas, t, n, title, title_t, color=WHITE, title_size=112):
    key = f"c{n}"
    a = seg_alpha(t, key)
    paste_center(canvas, badge_img(f"CASO {n}", 76, bg=YELLOW, fg=BLACK), W / 2, 215, pop(t, S[key] - 0.05), a, rot=-4)
    d = ImageDraw.Draw(canvas)
    for i in range(6):
        x = W / 2 + (i - 2.5) * 46
        on = i < n
        col = (YELLOW if on else (255, 255, 255)) + (int(255 * a * (1 if on else 0.35)),)
        d.ellipse((x - 12, 300 - 12, x + 12, 300 + 12), fill=col, outline=BLACK + (int(255 * a),), width=3)
    if t >= title_t:
        ti = text_img(title, title_size, fill=color, stroke=12, path=FONT_BLACK_IT)
        sc = min(1.0, (W - 60) / ti.width)
        paste_center(canvas, ti, W / 2, 420, pop(t, title_t) * sc, a, rot=-2)

def source(canvas, t, key, txt):
    a = seg_alpha(t, key) * 0.8 * prog(t, S[key] + 0.2, S[key] + 0.5)
    ti = text_img("Fuente: " + txt, 34, fill=WHITE, stroke=4, path=FONT_BOLD, shadow=False)
    paste_center(canvas, ti, W / 2, 1525, 1.0, a)

def panel(label, col, emojis, t, bg=(25, 10, 45, 235), extra=None):
    w, h = 450, 560
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 40, fill=bg, outline=col + (255,), width=10)
    d.rounded_rectangle((0, 0, w - 1, 100), 40, fill=col + (255,))
    d.rectangle((0, 60, w - 1, 100), fill=col + (255,))
    lb = text_img(label, 56, fill=BLACK if col != PINK else WHITE, stroke=0, shadow=False)
    im.alpha_composite(lb, ((w - lb.width) // 2, (100 - lb.height) // 2 + 4))
    if extra:
        extra(d, w, h, t)
    for e, sz, fx, fy, rot in emojis:
        em = emoji(e, sz)
        if rot:
            em = em.rotate(rot, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(em, (int(fx * w - em.width / 2), int(fy * h - em.height / 2)))
    return im

def compare(c, t, k, n, title, color, left, right, right_cue, badge, badge_cue, src, extra_l=None, extra_r=None,
            right_label="VIDA REAL"):
    a = seg_alpha(t, k)
    header(c, t, n, title, S[k] + 0.05, color=color, title_size=112)
    cy = 960
    paste_center(c, panel("TRÁILER", PINK, left(t), t, extra=extra_l), W / 2 - 245, cy, pop(t, S[k] + 0.1, 0.35), a, rot=-4)
    if t >= right_cue:
        paste_center(c, panel(right_label, TEAL, right(t), t, extra=extra_r), W / 2 + 245, cy, pop(t, right_cue, 0.35), a, rot=4)
        paste_center(c, text_img("=", 130, fill=YELLOW, stroke=11), W / 2, cy, pop(t, right_cue + 0.1), a)
    if t >= badge_cue:
        paste_center(c, badge_img(badge, 52, bg=YELLOW), W / 2, 1300, pop(t, badge_cue), a, rot=-2)
    source(c, t, k, src)

def pool(d, w, h, t):
    d.rounded_rectangle((40, 260, w - 40, h - 40), 30, fill=(40, 160, 230, 255), outline=WHITE + (255,), width=8)
    for j in range(3):
        y = 320 + j * 60
        d.line([(x, y + 8 * math.sin(x / 30 + t * 4 + j)) for x in range(60, w - 60, 15)], fill=(200, 240, 255, 200), width=4)

def road(d, w, h, t):
    d.rectangle((10, h - 170, w - 10, h - 20), fill=(50, 50, 60, 255))
    off = (t * 300) % 120
    for x in range(-120, w + 120, 120):
        d.rectangle((x - off, h - 100, x - off + 60, h - 88), fill=(255, 220, 80, 255))

def mugshot(d, w, h, t):
    for j in range(6):
        y = 130 + j * 70
        d.line((20, y, w - 20, y), fill=(255, 255, 255, 90), width=3)
    d.rounded_rectangle((90, h - 120, w - 90, h - 40), 10, fill=BLACK + (255,))

def sc_hook(c, t):
    k = "hook"; a = seg_alpha(t, k)
    paste_center(c, text_img("ESTO PASÓ", 150, fill=WHITE, stroke=13, path=FONT_BLACK_IT), W / 2, 380, pop(t, wt(k, "pasaron") - 0.1), a, rot=-3)
    paste_center(c, text_img("DE VERDAD", 170, fill=YELLOW, stroke=14, path=FONT_BLACK_IT), W / 2, 550, pop(t, wt(k, "verdad") - 0.1), a, rot=-3)
    # reproductor del tráiler con un "?" y estrellas de Florida
    x0, y0, x1, y1 = 140, 700, W - 140, 1150
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    al = int(255 * a * prog(t, 0.1, 0.4))
    d.rounded_rectangle((x0, y0, x1, y1), 40, fill=(15, 10, 30, int(235 * a)), outline=WHITE + (al,), width=8)
    pcx, pcy = W / 2, (y0 + y1) / 2 - 20
    d.ellipse((pcx - 80, pcy - 80, pcx + 80, pcy + 80), fill=RED + (al,))
    d.polygon([(pcx - 26, pcy - 40), (pcx - 26, pcy + 40), (pcx + 44, pcy)], fill=WHITE + (al,))
    d.rounded_rectangle((x0 + 50, y1 - 60, x1 - 50, y1 - 46), 7, fill=(255, 255, 255, int(80 * a)))
    d.rounded_rectangle((x0 + 50, y1 - 60, x0 + 50 + (x1 - x0 - 100) * (t / 4.2), y1 - 46), 7, fill=RED + (al,))
    c.alpha_composite(layer)
    paste_center(c, badge_img("TRÁILER 1 DE GTA 6", 56, bg=PINK, fg=WHITE), W / 2, 700, pop(t, wt(k, "tráiler") - 0.1), a, rot=-3)
    for i, e in enumerate(["🐊", "🌴", "🚨"]):
        tt = wt(k, "Florida") - 0.2 + 0.1 * i
        if t >= tt:
            paste_center(c, emoji(e, 150), W / 2 + (i - 1) * 330, 1300, pop(t, tt), a, rot=(i - 1) * 12)

def sc_c1(c, t):
    k = "c1"
    compare(c, t, k, 1, "CAIMÁN EN LA TIENDA", GREEN,
            lambda t: [("🏪", 200, 0.5, 0.42, 0), ("🐊", 210, 0.5 + 0.12 * math.sin(t * 2), 0.75, 0)],
            lambda t: [("📱", 200, 0.5, 0.45, 0), ("🐊", 170, 0.55, 0.75, -10)],
            wt(k, "vídeos") - 0.2, "VÍDEOS REALES EN FLORIDA", wt(k, "reales") - 0.1, "GTABoom · Sportskeeda")

def sc_c2(c, t):
    k = "c2"
    compare(c, t, k, 2, "CAIMÁN EN LA PISCINA", TEAL,
            lambda t: [("🧑", 170, 0.3, 0.33, 0), ("🐊", 240, 0.55, 0.62 + 0.02 * math.sin(t * 5), -15)],
            lambda t: [("👮", 170, 0.3, 0.33, 0), ("🐊", 240, 0.55, 0.62, 12)],
            wt(k, "Sarasota") - 0.15, "SARASOTA, FLORIDA", wt(k, "Sarasota"), "Sportskeeda · GTABoom",
            extra_l=pool, extra_r=pool)

def sc_c3(c, t):
    k = "c3"
    compare(c, t, k, 3, "BAILE SOBRE EL COCHE", PINK,
            lambda t: [("🚗", 240, 0.5, 0.66, 0), ("💃", 170, 0.5, 0.36 + 0.03 * abs(math.sin(t * 8)), 6 * math.sin(t * 8))],
            lambda t: [("🚙", 240, 0.5, 0.66, 0), ("💃", 170, 0.5, 0.36 + 0.03 * abs(math.sin(t * 8 + 1)), -6 * math.sin(t * 8))],
            wt(k, "clásico") - 0.2, "UN CLÁSICO VIRAL", wt(k, "internet") - 0.1, "GTABoom · Know Your Meme",
            extra_l=road, extra_r=road)

def sc_c4(c, t):
    k = "c4"
    compare(c, t, k, 4, "LA DE LOS MARTILLOS", ORANGE,
            lambda t: [("👩", 190, 0.5, 0.45, 0), ("🔨", 130, 0.2, 0.62, 25 * math.sin(t * 4)), ("🔨", 130, 0.8, 0.62, -25 * math.sin(t * 4))],
            lambda t: [("📸", 220, 0.5, 0.45, 0)],
            wt(k, "foto") - 0.15, "BASADA EN UNA FOTO POLICIAL", wt(k, "policial") - 0.1, "GTABoom · Sportskeeda",
            extra_r=mugshot, right_label="FICHA POLICIAL")

def sc_c5(c, t):
    k = "c5"
    compare(c, t, k, 5, "EL JOKER DE FLORIDA", (170, 120, 255),
            lambda t: [("🧑", 230, 0.5, 0.5, 0), ("🃏", 120, 0.78, 0.78, 15)],
            lambda t: [("🤡", 230, 0.5, 0.5, 0), ("🃏", 120, 0.22, 0.78, -15)],
            wt(k, "Joker") - 0.15, "LAWRENCE SULLIVAN", wt(k, "Florida") - 0.1, "PC Gamer · GamesRadar")

def sc_c6(c, t):
    k = "c6"; a = seg_alpha(t, k)
    header(c, t, 6, "SU RESPUESTA", S[k] + 0.05, color=YELLOW, title_size=124)
    # móvil con vídeo
    ph = Image.new("RGBA", (440, 700), (0, 0, 0, 0))
    d = ImageDraw.Draw(ph)
    d.rounded_rectangle((0, 0, 439, 699), 60, fill=(15, 10, 25, 255), outline=WHITE + (255,), width=10)
    d.rounded_rectangle((25, 40, 414, 660), 40, fill=(60, 30, 90, 255))
    em = emoji("🤡", 200)
    ph.alpha_composite(em, ((440 - em.width) // 2, 200))
    d.rounded_rectangle((170, 14, 270, 30), 8, fill=(40, 40, 50, 255))
    paste_center(c, ph, W / 2 - 220, 950, pop(t, S[k] + 0.1), a, rot=-4)
    if t >= wt(k, "GTA") - 0.1:
        bub = Image.new("RGBA", (520, 260), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((10, 10, 509, 219), 50, fill=WHITE + (255,), outline=BLACK + (255,), width=8)
        bd.polygon([(60, 210), (130, 210), (30, 255)], fill=WHITE + (255,), outline=BLACK + (255,))
        bd.line([(62, 214), (128, 214)], fill=WHITE + (255,), width=12)
        l1 = text_img("«GTA, TENEMOS", 48, fill=BLACK, stroke=0, shadow=False)
        l2 = text_img("QUE HABLAR»", 60, fill=PINK, stroke=5)
        bub.alpha_composite(l1, ((520 - l1.width) // 2, 34))
        bub.alpha_composite(l2, ((520 - l2.width) // 2, 104))
        paste_center(c, bub, W / 2 + 230, 700, pop(t, wt(k, "GTA") - 0.1), a, rot=4)
    tm = wt(k, "dos") - 0.1
    if t >= tm:
        v = int(2000000 * ease_out(prog(t, tm, wt(k, "millones") + 0.4)))
        num = text_img(f"${v:,}".replace(",", "."), 96, fill=GREEN, stroke=10)
        paste_center(c, num, W / 2 + 230, 1020, pop(t, tm), a, rot=-4)
    stamp(c, "ERA BROMA", W / 2 + 200, 1220, wt(k, "broma") - 0.1, t, color=RED, size=100, rot=-10)
    source(c, t, k, "PC Gamer · Dexerto · Sportskeeda")

def sc_cta(c, t):
    k = "cta"
    if t < S[k] - 0.1:
        return
    stamp(c, "NO CONFIRMADO", W / 2, 330, wt(k, "Rockstar"), t, color=RED, size=84, rot=-4)
    paste_center(c, text_img("¿INSPIRACIÓN", 130, fill=WHITE, stroke=12, path=FONT_BLACK_IT), W / 2, 560, pop(t, wt(k, "Inspiración") - 0.1), rot=-3)
    paste_center(c, text_img("O CASUALIDAD?", 130, fill=YELLOW, stroke=12, path=FONT_BLACK_IT), W / 2, 710, pop(t, wt(k, "casualidad") - 0.1), rot=-3)
    tb = wt(k, "Te") - 0.1
    if t >= tb:
        bw, bh = 860, 230
        bub = Image.new("RGBA", (bw + 40, bh + 110), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((20, 20, bw + 20, bh + 20), 60, fill=WHITE + (255,), outline=BLACK + (255,), width=10)
        bd.polygon([(140, bh + 10), (230, bh + 10), (120, bh + 100)], fill=WHITE + (255,), outline=BLACK + (255,))
        bd.line([(140, bh + 14), (230, bh + 14)], fill=WHITE + (255,), width=14)
        tl = text_img("TE LEO EN", 72, fill=BLACK, stroke=0, shadow=False)
        tl2 = text_img("COMENTARIOS", 92, fill=PINK, stroke=6)
        bub.alpha_composite(tl, ((bub.width - tl.width) // 2, 40))
        bub.alpha_composite(tl2, ((bub.width - tl2.width) // 2, 112))
        paste_center(c, bub, W / 2, 1010, pop(t, tb, 0.4) * (1 + 0.02 * math.sin(t * 6)))
    if t >= tb + 0.5:
        d = ImageDraw.Draw(c)
        bounce = abs(math.sin((t - tb) * 5)) * 40
        ax, ay = W / 2, 1260 + bounce
        d.polygon([(ax - 40, ay), (ax + 40, ay), (ax + 40, ay + 70), (ax + 85, ay + 70), (ax, ay + 150),
                   (ax - 85, ay + 70), (ax - 40, ay + 70)], fill=YELLOW + (255,), outline=BLACK + (255,), width=8)


SCENES = {"hook": sc_hook, "c1": sc_c1, "c2": sc_c2, "c3": sc_c3, "c4": sc_c4, "c5": sc_c5, "c6": sc_c6, "cta": sc_cta}

# --------------------------------------------------------------------------
# subtítulos palabra a palabra (solo curiosidades)
CHUNK = 3
DISPLAY = {"seis": "6", "tres.": "3."}
HL = {"caimán", "tienda", "reales", "piscina", "Sarasota", "bailando", "coche", "internet", "martillos", "policial",
      "tatuajes", "Joker", "Florida", "hablar", "millones", "broma", "dos", "vídeos"}

def build_caps():
    caps = []
    for pid in ["c1", "c2", "c3", "c4", "c5", "c6"]:
        p = P[pid]
        toks = p["text"].split(" ")
        ws = p["words"]
        if len(toks) != len(ws):
            toks = [w["w"] for w in ws]
        groups, g = [], []
        for tok, w in zip(toks, ws):
            g.append((DISPLAY.get(tok, tok), w["s"]))
            if len(g) >= CHUNK or tok[-1] in ",.…":
                groups.append(g); g = []
        if g:
            groups.append(g)
        for i, g in enumerate(groups):
            end = groups[i + 1][0][1] if i + 1 < len(groups) else p["end"] + 0.25
            caps.append((g, end))
    return caps
CAPS = build_caps()

def draw_caption(c, t):
    for words, end in CAPS:
        if words[0][1] - 0.05 <= t < end:
            f = B.font(FONT_BLACK, 76)
            sp = f.getlength(" ")
            widths = [f.getlength(w) for w, _ in words]
            x = W / 2 - (sum(widths) + sp * (len(words) - 1)) / 2
            for (wd, ts), wl in zip(words, widths):
                if t >= ts - 0.05:
                    col = YELLOW if wd.strip(",.…") in HL else WHITE
                    paste_center(c, text_img(wd, 76, fill=col, stroke=8), x + wl / 2, 1440, scale=pop(t, ts - 0.05, 0.18))
                x += wl + sp
            break

# --------------------------------------------------------------------------
CUTS = [S[k] - 0.1 for k in SEG[1:]]

def render_frame(t, bg, vig):
    c = bg.copy()
    B.draw_particles(c, t)
    B.draw_grid(c, t)
    for k in SEG:
        if S[k] - 0.15 <= t < SEG_END[k] + 0.05 or (k == "hook" and t < SEG_END[k]):
            SCENES[k](c, t)
    draw_caption(c, t)
    c.alpha_composite(vig)
    ImageDraw.Draw(c).rectangle((0, 0, int(W * t / DUR), 10), fill=YELLOW + (255,))
    z = 1.0
    for cu in [0.0] + CUTS:
        if cu <= t < cu + 0.25:
            z = 1 + 0.06 * (1 - ease_out((t - cu) / 0.25))
    if z != 1.0:
        cw, ch = int(W / z), int(H / z)
        c = c.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
    for cu in CUTS:
        if cu <= t < cu + 0.15:
            c.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(170 * (1 - (t - cu) / 0.15)))))
    return c

# --------------------------------------------------------------------------
SR = 44100
def synth_music(path):
    n = int(DUR * SR); t = np.arange(n) / SR; out = np.zeros(n)
    bpm = 118; beat = 60 / bpm; rng = np.random.default_rng(2)
    roots = [55.0, 43.65, 65.41, 49.0]
    for i in range(int(DUR / beat) + 1):
        st = i * beat; f = roots[int(i // 4) % 4]
        s0, s1 = int(st * SR), int(min(DUR, st + beat * 0.9) * SR)
        if s1 <= s0: continue
        tt = t[s0:s1] - st; env = np.exp(-tt * 3)
        out[s0:s1] += 0.11 * np.sign(np.sin(2 * np.pi * f * tt)) * env + 0.18 * np.sin(2 * np.pi * f * tt) * env
        k1 = int(min(DUR, st + 0.25) * SR); kt = t[s0:k1] - st
        out[s0:k1] += 0.55 * np.sin(2 * np.pi * (50 + 120 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 12)
        hs = st + beat / 2; h0, h1 = int(hs * SR), int(min(DUR, hs + 0.05) * SR)
        if h1 > h0:
            out[h0:h1] += 0.08 * rng.standard_normal(h1 - h0) * np.exp(-(t[h0:h1] - hs) * 80)
        if i % 2 == 1:
            c1 = int(min(DUR, st + 0.15) * SR)
            out[s0:c1] += 0.15 * rng.standard_normal(c1 - s0) * np.exp(-(t[s0:c1] - st) * 25)
    chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    for b in range(int(DUR / (beat * 4)) + 1):
        st = b * beat * 4; s0, s1 = int(st * SR), int(min(DUR, st + beat * 4) * SR)
        if s1 <= s0: continue
        tt = t[s0:s1] - st; env = np.minimum(1, tt / 0.3) * np.minimum(1, (beat * 4 - tt) / 0.3)
        for f in chords[b % 4]:
            out[s0:s1] += 0.035 * (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.005 * tt)) * env
    for cu in CUTS:   # whoosh
        s0, s1 = int(max(0, cu - 0.3) * SR), int(min(DUR, cu + 0.12) * SR)
        nz = rng.standard_normal(s1 - s0); env = np.sin(np.linspace(0, np.pi, s1 - s0)) ** 2
        y = np.zeros_like(nz); acc = 0
        for j in range(len(nz)):
            acc += (0.02 + 0.3 * j / len(nz)) * (nz[j] - acc); y[j] = acc
        out[s0:s1] += 0.5 * y * env
    for tc, f in [(wt("c1", "vídeos"), 880.0), (wt("c5", "Joker"), 587.3), (wt("c6", "millones"), 1318.5), (wt("c6", "broma"), 330.0)]:
        s0, s1 = int(tc * SR), int(min(DUR, tc + 1.0) * SR); tt = t[s0:s1] - tc
        out[s0:s1] += 0.18 * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 4)
    fo = int(1.2 * SR); out[-fo:] *= np.linspace(1, 0, fo)
    out = out / np.max(np.abs(out)) * 0.6
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())

def main():
    bg, vig = B.make_gradient(), B.make_vignette()
    only = os.environ.get("FRAMES")
    if only:
        for fi in map(int, only.split(",")):
            render_frame(fi / FPS, bg, vig).convert("RGB").save(os.path.join(HERE, f"preview_{fi:04d}.png"))
        return
    silent = os.path.join(HERE, "short6_florida_real_sin_musica.mp4")
    music = os.path.join(HERE, "musica.wav")
    voz = os.path.join(HERE, "voz", "voz.wav")
    final = os.path.join(HERE, "short6_florida_real.mp4")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
    for fi in range(NFRAMES):
        ff.stdin.write(render_frame(fi / FPS, bg, vig).convert("RGB").tobytes())
        if fi % 150 == 0:
            print(f"frame {fi}/{NFRAMES}", flush=True)
    ff.stdin.close(); ff.wait()
    synth_music(music)
    fc = ("[2:a]asplit=2[v1][v2];[1:a]volume=0.55[m0];"
          "[m0][v1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[m];"
          "[v2]highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=5:release=80,volume=1.15[vv];"
          "[m][vv]amix=inputs=2:normalize=0,alimiter=limit=0.95,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", music, "-i", voz, "-filter_complex", fc,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                    "-shortest", final], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", voz, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
                    "-shortest", os.path.join(HERE, "short6_florida_real_solo_voz.mp4")], check=True)
    print("OK ->", final)

if __name__ == "__main__":
    main()
