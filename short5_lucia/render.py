"""
SHORT 5 — «La historia de Lucía Caminos»
Vertical 1080x1920, 30 fps. Reutiliza el estilo y utilidades del Short 1.

  python3 gen_voz.py     -> voz/voz.wav + voz/timeline.json (voz IA, tiempos por palabra)
  python3 render.py      -> short5_lucia.mp4 (+ _sin_musica / _solo_voz)
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
# cabecera y escenas del Short 5
def header(canvas, t, n, title, title_t, color=WHITE, title_size=112):
    key = f"c{n}"
    a = seg_alpha(t, key)
    paste_center(canvas, badge_img(f"PARTE {n}", 76, bg=PINK, fg=WHITE), W / 2, 215, pop(t, S[key] - 0.05), a, rot=-4)
    d = ImageDraw.Draw(canvas)
    for i in range(6):
        x = W / 2 + (i - 2.5) * 46
        on = i < n
        col = (PINK if on else (255, 255, 255)) + (int(255 * a * (1 if on else 0.35)),)
        d.ellipse((x - 12, 300 - 12, x + 12, 300 + 12), fill=col, outline=BLACK + (int(255 * a),), width=3)
    if t >= title_t:
        ti = text_img(title, title_size, fill=color, stroke=12, path=FONT_BLACK_IT)
        sc = min(1.0, (W - 60) / ti.width)
        paste_center(canvas, ti, W / 2, 420, pop(t, title_t) * sc, a, rot=-2)

def source(canvas, t, key, txt):
    a = seg_alpha(t, key) * 0.8 * prog(t, S[key] + 0.2, S[key] + 0.5)
    ti = text_img("Fuente: " + txt, 34, fill=WHITE, stroke=4, path=FONT_BOLD, shadow=False)
    paste_center(canvas, ti, W / 2, 1525, 1.0, a)

def person_card(name, col, w=380, h=470, bars=0.0):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 40, fill=(25, 10, 45, 235), outline=col + (255,), width=10)
    d.ellipse((w / 2 - 60, 60, w / 2 + 60, 180), fill=col + (255,))
    d.rounded_rectangle((w / 2 - 95, 190, w / 2 + 95, 360), 60, fill=col + (255,))
    nm = text_img(name, 62, fill=WHITE, stroke=7)
    im.alpha_composite(nm, ((w - nm.width) // 2, 370))
    if bars > 0:
        for j in range(5):
            x = 30 + j * (w - 60) / 4
            d.rounded_rectangle((x - 10, 0, x + 10, (h - 10) * bars), 6, fill=(150, 150, 165, 255), outline=BLACK + (255,), width=3)
        d.rounded_rectangle((10, (h - 10) * bars * 0.45 - 12, w - 10, (h - 10) * bars * 0.45 + 12), 6, fill=(150, 150, 165, 255), outline=BLACK + (255,), width=3)
    return im

def sc_hook(c, t):
    k = "hook"; a = seg_alpha(t, k)
    t0 = wt(k, "historia") - 0.2
    if t >= t0:
        fo = Image.new("RGBA", (820, 700), (0, 0, 0, 0))
        d = ImageDraw.Draw(fo)
        d.rounded_rectangle((0, 40, 819, 699), 30, fill=(214, 170, 100, 255), outline=BLACK + (255,), width=10)
        d.rounded_rectangle((40, 0, 330, 90), 20, fill=(214, 170, 100, 255), outline=BLACK + (255,), width=10)
        d.rectangle((50, 40, 320, 60), fill=(214, 170, 100, 255))
        fo.alpha_composite(text_img("EXPEDIENTE", 60, fill=(90, 50, 20), stroke=0, shadow=False), (60, 90))
        d.rounded_rectangle((60, 200, 340, 560), 16, fill=(60, 40, 70, 255), outline=BLACK + (255,), width=6)
        d.ellipse((140, 250, 260, 370), fill=(20, 10, 30, 255))
        d.rounded_rectangle((105, 380, 295, 560), 60, fill=(20, 10, 30, 255))
        q = text_img("?", 110, fill=PINK, stroke=8)
        fo.alpha_composite(q, (200 - q.width // 2, 250))
        for j, (k1, v1) in enumerate([("NOMBRE", "LUCÍA CAMINOS"), ("ESPECIALIDAD", "PELEAR"), ("ESTADO", "EX PRESA")]):
            fo.alpha_composite(text_img(k1, 34, fill=(90, 50, 20), stroke=0, shadow=False), (380, 210 + j * 120))
            fo.alpha_composite(text_img(v1, 46, fill=BLACK, stroke=0, shadow=False), (380, 245 + j * 120))
        paste_center(c, fo, W / 2, 820, pop(t, t0, 0.4) * 0.95, a, rot=-3)
    paste_center(c, text_img("LA HISTORIA DE", 80, stroke=9), W / 2, 340, pop(t, wt(k, "historia") - 0.15), a)
    if t >= wt(k, "Lucía") - 0.1:
        paste_center(c, text_img("LUCÍA CAMINOS", 118, fill=PINK, stroke=14, path=FONT_BLACK_IT), W / 2, 480,
                     pop(t, wt(k, "Lucía") - 0.1) * (1 + 0.02 * math.sin(t * 7)), a, rot=-3)
    stamp(c, "PROTAGONISTA", W / 2 + 120, 1230, wt(k, "protagonista") - 0.05, t, color=RED, size=84, rot=-10)

def sc_c1(c, t):
    k = "c1"; a = seg_alpha(t, k)
    header(c, t, 1, "LUCHADORA DESDE NIÑA", S[k] + 0.05, color=YELLOW, title_size=100)
    cx, cy = W / 2, 960
    paste_center(c, emoji("👧", 250), cx, cy + 6 * math.sin(t * 3), pop(t, wt(k, "pelear") - 0.6), a)
    tp = wt(k, "pelear") - 0.1
    if t >= tp:
        jab = abs(math.sin((t - tp) * 9)) * 50
        paste_center(c, emoji("🥊", 170), cx - 230 - jab, cy + 40, pop(t, tp), a, rot=20)
        paste_center(c, emoji("🥊", 170), cx + 230 + (50 - jab), cy + 40, pop(t, tp + 0.08), a, rot=-20)
    if t >= wt(k, "padre") - 0.1:
        paste_center(c, badge_img("SU PADRE LE ENSEÑÓ", 56, bg=WHITE), W / 2, 640, pop(t, wt(k, "padre") - 0.1), a, rot=2)
    if t >= wt(k, "andar") - 0.15:
        paste_center(c, badge_img("NADA MÁS APRENDER A ANDAR", 48, bg=YELLOW), W / 2, 1290, pop(t, wt(k, "andar") - 0.15), a, rot=-2)
    source(c, t, k, "Rockstar Games")

def sc_c2(c, t):
    k = "c2"; a = seg_alpha(t, k)
    header(c, t, 2, "LA VIDA LE PEGA", S[k] + 0.05, color=RED, title_size=124)
    cx, cy = W / 2, 960
    # barra de vida que baja con cada golpe
    hits = [wt(k, "vida"), wt(k, "dejado"), wt(k, "darle"), wt(k, "golpes")]
    n_hits = sum(1 for h in hits if t >= h)
    hp = 1.0 - 0.2 * n_hits
    bar = Image.new("RGBA", (820, 110), (0, 0, 0, 0))
    d = ImageDraw.Draw(bar)
    d.rounded_rectangle((0, 0, 819, 109), 30, fill=(25, 10, 45, 235), outline=WHITE + (255,), width=8)
    col = GREEN if hp > 0.5 else (YELLOW if hp > 0.3 else RED)
    d.rounded_rectangle((16, 16, 16 + 788 * hp, 93), 20, fill=col + (255,))
    paste_center(c, bar, cx, 700, pop(t, S[k] + 0.1), a)
    paste_center(c, emoji("❤️", 110), cx - 440, 700, pop(t, S[k] + 0.1), a)
    paste_center(c, emoji("😤", 260), cx + (math.sin(t * 60) * 12 if any(h <= t < h + 0.2 for h in hits) else 0), cy + 60, pop(t, S[k] + 0.2), a)
    for i, h in enumerate(hits):
        if h <= t < h + 0.7:
            ang = i * 1.7
            paste_center(c, emoji("💥", 170), cx + 250 * math.cos(ang), cy + 60 + 200 * math.sin(ang), pop(t, h, 0.2), a * (1 - prog(t, h + 0.4, h + 0.7)))
    source(c, t, k, "Rockstar Games")

def sc_c3(c, t):
    k = "c3"; a = seg_alpha(t, k)
    header(c, t, 3, "PRISIÓN DE LEONIDA", wt(k, "cárcel") - 0.15, color=WHITE, title_size=112)
    cx, cy = W / 2, 980
    bars = ease_out(prog(t, wt(k, "cárcel") - 0.1, wt(k, "cárcel") + 0.35))
    paste_center(c, person_card("LUCÍA", PINK, bars=bars), cx, cy, pop(t, S[k] + 0.05), a, rot=-2)
    if t >= wt(k, "familia") - 0.1:
        paste_center(c, badge_img("POR SU FAMILIA", 60, bg=YELLOW), W / 2, 640, pop(t, wt(k, "familia") - 0.1), a, rot=2)
        paste_center(c, emoji("👨‍👩‍👧", 150), cx + 330, cy - 180, pop(t, wt(k, "familia")), a, rot=8)
    stamp(c, "ENCERRADA", W / 2, 1300, wt(k, "Leonida") - 0.05, t, size=90, rot=-6)
    source(c, t, k, "Rockstar Games")

def sc_c4(c, t):
    k = "c4"; a = seg_alpha(t, k)
    header(c, t, 4, "¿QUÉ HIZO?", S[k] + 0.05, color=YELLOW, title_size=140)
    doc = Image.new("RGBA", (760, 620), (0, 0, 0, 0))
    d = ImageDraw.Draw(doc)
    d.rounded_rectangle((0, 0, 759, 619), 24, fill=(240, 235, 220, 255), outline=BLACK + (255,), width=8)
    doc.alpha_composite(text_img("INFORME POLICIAL", 50, fill=BLACK, stroke=0, shadow=False), (40, 30))
    red = prog(t, wt(k, "exactamente") - 0.2, wt(k, "hizo") + 0.3)
    for j in range(7):
        y = 130 + j * 66
        wline = 660 - (j % 3) * 120
        d.rounded_rectangle((40, y, 40 + wline, y + 22), 8, fill=(170, 165, 150, 255))
        rw = wline * clamp(red * 7 - j)
        if rw > 0:
            d.rounded_rectangle((36, y - 8, 36 + rw + 8, y + 30), 6, fill=(10, 10, 10, 255))
    paste_center(c, doc, W / 2, 1000, pop(t, S[k] + 0.1), a, rot=-3)
    for i in range(3):
        tt = wt(k, "misterio") - 0.2 + 0.12 * i
        if t >= tt:
            paste_center(c, text_img("?", 170, fill=PINK, stroke=12), W / 2 + (i - 1) * 360, 600 + (i % 2) * 30,
                         pop(t, tt) * (1 + 0.08 * math.sin(t * 5 + i)), a, rot=(i - 1) * 15)
    stamp(c, "CLASIFICADO", W / 2, 1290, wt(k, "misterio"), t, size=90, rot=-8)
    source(c, t, k, "Rockstar Games")

def sc_c5(c, t):
    k = "c5"; a = seg_alpha(t, k)
    header(c, t, 5, "PURA SUERTE", wt(k, "suerte") - 0.4, color=GREEN, title_size=135)
    cx, cy = W / 2, 980
    bars = 1 - ease_in_out(prog(t, wt(k, "pura") - 0.1, wt(k, "suerte") + 0.3))
    paste_center(c, person_card("LUCÍA", PINK, bars=bars), cx, cy, 1.0, a, rot=-2)
    if t >= wt(k, "pura") - 0.1:
        paste_center(c, emoji("🔓", 150), cx - 330, cy - 160, pop(t, wt(k, "pura") - 0.1), a, rot=-10)
    if t >= wt(k, "suerte") - 0.15:
        paste_center(c, emoji("🍀", 200), cx + 320, cy - 170, pop(t, wt(k, "suerte") - 0.15) * (1 + 0.05 * math.sin(t * 6)), a, rot=12)
        paste_center(c, badge_img("¡FUERA DE PRISIÓN!", 60, bg=GREEN, fg=WHITE), W / 2, 1300, pop(t, wt(k, "suerte")), a, rot=-2)
    source(c, t, k, "Rockstar Games")

def sc_c6(c, t):
    k = "c6"; a = seg_alpha(t, k)
    header(c, t, 6, "LECCIÓN APRENDIDA", wt(k, "lección") - 0.2, color=TEAL, title_size=110)
    cx, cy = W / 2, 960
    paste_center(c, emoji("🧠", 240), cx - 180, cy, pop(t, wt(k, "aprendido") - 0.1) * (1 + 0.05 * math.sin(t * 4)), a, rot=-6)
    if t >= wt(k, "jugadas") - 0.15:
        paste_center(c, emoji("♟️", 240), cx + 180, cy, pop(t, wt(k, "jugadas") - 0.15), a, rot=6)
        paste_center(c, badge_img("SOLO JUGADAS INTELIGENTES", 50, bg=YELLOW), W / 2, 1290, pop(t, wt(k, "inteligentes") - 0.1), a, rot=-2)
    if t >= wt(k, "partir") - 0.1:
        paste_center(c, text_img("A PARTIR DE AQUÍ...", 72, fill=WHITE, stroke=8), W / 2, 650, pop(t, wt(k, "partir") - 0.1), a)
    source(c, t, k, "Rockstar Games")

def sc_cta(c, t):
    k = "cta"
    if t < S[k] - 0.1:
        return
    paste_center(c, text_img("¿PREFIERES A...", 104, fill=WHITE, stroke=10), W / 2, 400, pop(t, wt(k, "Prefieres") - 0.1))
    cy = 760
    if t >= wt(k, "Lucía") - 0.1:
        paste_center(c, person_card("LUCÍA", PINK), W / 2 - 230, cy, pop(t, wt(k, "Lucía") - 0.1) * 0.85, 1, rot=-5)
    if t >= wt(k, "o") - 0.05:
        paste_center(c, text_img("VS", 120, fill=YELLOW, stroke=11, path=FONT_BLACK_IT), W / 2, cy, pop(t, wt(k, "o") - 0.05) * (1 + 0.06 * math.sin(t * 8)))
    if t >= wt(k, "Jason") - 0.1:
        paste_center(c, person_card("JASON", TEAL), W / 2 + 230, cy, pop(t, wt(k, "Jason") - 0.1) * 0.85, 1, rot=5)
    tb = wt(k, "Te") - 0.1
    if t >= tb:
        bw, bh = 860, 200
        bub = Image.new("RGBA", (bw + 40, bh + 110), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((20, 20, bw + 20, bh + 20), 60, fill=WHITE + (255,), outline=BLACK + (255,), width=10)
        bd.polygon([(140, bh + 10), (230, bh + 10), (120, bh + 100)], fill=WHITE + (255,), outline=BLACK + (255,))
        bd.line([(140, bh + 14), (230, bh + 14)], fill=WHITE + (255,), width=14)
        tl = text_img("TE LEO EN", 62, fill=BLACK, stroke=0, shadow=False)
        tl2 = text_img("COMENTARIOS", 84, fill=PINK, stroke=6)
        bub.alpha_composite(tl, ((bub.width - tl.width) // 2, 34))
        bub.alpha_composite(tl2, ((bub.width - tl2.width) // 2, 100))
        paste_center(c, bub, W / 2, 1150, pop(t, tb, 0.4) * (1 + 0.02 * math.sin(t * 6)))
    if t >= tb + 0.5:
        d = ImageDraw.Draw(c)
        bounce = abs(math.sin((t - tb) * 5)) * 30
        ax, ay = W / 2, 1330 + bounce
        d.polygon([(ax - 35, ay), (ax + 35, ay), (ax + 35, ay + 60), (ax + 75, ay + 60), (ax, ay + 130),
                   (ax - 75, ay + 60), (ax - 35, ay + 60)], fill=YELLOW + (255,), outline=BLACK + (255,), width=8)


SCENES = {"hook": sc_hook, "c1": sc_c1, "c2": sc_c2, "c3": sc_c3, "c4": sc_c4, "c5": sc_c5, "c6": sc_c6, "cta": sc_cta}

# --------------------------------------------------------------------------
# subtítulos palabra a palabra (solo curiosidades)
CHUNK = 3
DISPLAY = {"seis": "6", "tres.": "3."}
HL = {"padre", "pelear", "andar", "vida", "golpes", "familia", "cárcel", "Leonida", "Rockstar", "misterio",
      "prisión", "suerte", "lección", "inteligentes", "jugadas"}

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
    for tc, f in [(wt("c3", "cárcel"), 330.0), (wt("c4", "misterio"), 587.3), (wt("c5", "suerte"), 1318.5)]:
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
    silent = os.path.join(HERE, "short5_lucia_sin_musica.mp4")
    music = os.path.join(HERE, "musica.wav")
    voz = os.path.join(HERE, "voz", "voz.wav")
    final = os.path.join(HERE, "short5_lucia.mp4")
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
                    "-shortest", os.path.join(HERE, "short5_lucia_solo_voz.mp4")], check=True)
    print("OK ->", final)

if __name__ == "__main__":
    main()
