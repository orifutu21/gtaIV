"""
SHORT 7 — «6 curiosidades más de GTA 6»
Vertical 1080x1920, 30 fps. Reutiliza el estilo y utilidades del Short 1.

  python3 gen_voz.py     -> voz/voz.wav + voz/timeline.json (voz IA, tiempos por palabra)
  python3 render.py      -> short7_curiosidades2.mp4 (+ _sin_musica / _solo_voz)
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
# cabecera: número de curiosidad + puntos de progreso
def header(canvas, t, n, title, title_t, color=YELLOW, title_size=120):
    key = f"c{n}"
    a = seg_alpha(t, key)
    paste_center(canvas, badge_img(f"#{n}", 90, bg=PINK, fg=WHITE), W / 2, 215, pop(t, S[key] - 0.05), a, rot=-5)
    # progreso 1..6
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

# --------------------------------------------------------------------------
def counter_box(text, col, w=820, h=260, size=150):
    box = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle((0, 0, w - 1, h - 1), 50, fill=(25, 10, 45, 235), outline=col + (255,), width=12)
    num = text_img(text, size, fill=col, stroke=12)
    sc = min(1.0, (w - 60) / num.width)
    if sc < 1:
        num = num.resize((int(num.width * sc), int(num.height * sc)), Image.LANCZOS)
    box.alpha_composite(num, ((w - num.width) // 2, (h - num.height) // 2))
    return box

def person_card(name, col, w=360, h=440):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 40, fill=(25, 10, 45, 235), outline=col + (255,), width=10)
    d.ellipse((w / 2 - 55, 55, w / 2 + 55, 165), fill=col + (255,))
    d.rounded_rectangle((w / 2 - 90, 175, w / 2 + 90, 330), 55, fill=col + (255,))
    nm = text_img(name, 56, fill=WHITE, stroke=6)
    sc = min(1.0, (w - 30) / nm.width)
    if sc < 1:
        nm = nm.resize((int(nm.width * sc), int(nm.height * sc)), Image.LANCZOS)
    im.alpha_composite(nm, ((w - nm.width) // 2, 345))
    return im

def sc_hook(c, t):
    k = "hook"
    a = seg_alpha(t, k)
    sh = math.sin(t * 60) * 6 * max(0, 1 - t / 0.4)
    six = text_img("6", 480, fill=YELLOW, stroke=22, path=FONT_BLACK_IT)
    paste_center(c, six, W / 2 - 120 + sh, 560, pop(t, wt(k, "Seis") - 0.1, 0.4) * (1 + 0.03 * math.sin(t * 6)), a, rot=-6)
    paste_center(c, text_img("MÁS", 150, fill=PINK, stroke=13, path=FONT_BLACK_IT), W / 2 + 220, 640, pop(t, wt(k, "más") - 0.1), a, rot=-10)
    paste_center(c, text_img("CURIOSIDADES", 120, stroke=11), W / 2, 870, pop(t, wt(k, "curiosidades") - 0.1), a)
    paste_center(c, text_img("DE GTA 6", 130, fill=YELLOW, stroke=12, path=FONT_BLACK_IT), W / 2, 1010, pop(t, wt(k, "GTA") - 0.1), a, rot=-2)
    t2 = wt(k, "La") - 0.05
    if t >= t2:
        paste_center(c, badge_img("LA ÚLTIMA ES MUY RARA", 60, bg=YELLOW), W / 2, 1200, pop(t, t2), a, rot=2)
        paste_center(c, emoji("🤨", 150), W / 2 + 400, 1120, pop(t, wt(k, "rara") - 0.1), a, rot=12)

def sc_c1(c, t):
    k = "c1"; a = seg_alpha(t, k)
    header(c, t, 1, "TRÁILER RÉCORD", S[k] + 0.05, color=RED, title_size=120)
    t0, t1 = wt(k, "noventa") - 0.1, wt(k, "día") + 0.2
    v = int(90_000_000 * ease_out(prog(t, t0, t1)))
    paste_center(c, counter_box(f"{v:,}".replace(",", "."), WHITE, size=130), W / 2, 820, pop(t, S[k] + 0.1), a)
    paste_center(c, text_img("VISITAS", 70, fill=WHITE, stroke=7), W / 2, 990, pop(t, wt(k, "visitas") - 0.1), a)
    paste_center(c, emoji("👀", 140), W / 2 - 400, 650, pop(t, wt(k, "visitas") - 0.1), a, rot=-10)
    if t >= wt(k, "día") - 0.1:
        paste_center(c, badge_img("EN 24 HORAS", 64, bg=RED, fg=WHITE), W / 2, 560, pop(t, wt(k, "día") - 0.1), a, rot=3)
    if t >= wt(k, "récord") - 0.1:
        paste_center(c, emoji("🏆", 170), W / 2 + 380, 1140, pop(t, wt(k, "récord") - 0.1), a, rot=10)
        paste_center(c, badge_img("ADIÓS, RÉCORD DE MRBEAST", 52, bg=YELLOW), W / 2, 1180, pop(t, wt(k, "MrBeast") - 0.1), a, rot=-3)
    source(c, t, k, "PC Gamer · Push Square")

def sc_c2(c, t):
    k = "c2"; a = seg_alpha(t, k)
    header(c, t, 2, "LA PRIMERA", S[k] + 0.05, color=PINK, title_size=140)
    paste_center(c, person_card("LUCÍA", PINK, 400, 480), W / 2, 890, pop(t, S[k] + 0.1, 0.4), a, rot=-3)
    if t >= wt(k, "primera") - 0.1:
        paste_center(c, emoji("🥇", 200), W / 2 + 270, 720, pop(t, wt(k, "primera") - 0.1), a, rot=12)
    if t >= wt(k, "protagonista") - 0.1:
        paste_center(c, badge_img("PROTAGONISTA FEMENINA", 56, bg=YELLOW), W / 2, 1210, pop(t, wt(k, "protagonista") - 0.1), a, rot=-2)
    if t >= wt(k, "moderna") - 0.1:
        paste_center(c, text_img("DE LA ERA MODERNA", 58, fill=WHITE, stroke=6), W / 2, 1305, pop(t, wt(k, "moderna") - 0.1), a)
    source(c, t, k, "La Silla Rota · GTA Wiki")

def sc_c3(c, t):
    k = "c3"; a = seg_alpha(t, k)
    header(c, t, 3, "BONNIE Y CLYDE", wt(k, "Bonnie") - 0.15, color=ORANGE, title_size=120)
    cy = 920
    paste_center(c, person_card("JASON", TEAL), W / 2 - 220, cy, pop(t, wt(k, "Jason") - 0.1), a, rot=-5)
    if t >= wt(k, "Lucía") - 0.1:
        paste_center(c, person_card("LUCÍA", PINK), W / 2 + 220, cy, pop(t, wt(k, "Lucía") - 0.1), a, rot=5)
    if t >= wt(k, "compara") - 0.1:
        paste_center(c, text_img("=", 140, fill=YELLOW, stroke=12), W / 2, cy, pop(t, wt(k, "compara") - 0.1), a)
    if t >= wt(k, "Bonnie") - 0.1:
        paste_center(c, badge_img("BONNIE & CLYDE · 1930", 56, bg=(214, 170, 100)), W / 2, 1250, pop(t, wt(k, "Bonnie") - 0.1), a, rot=-3)
        for i, e in enumerate(["🚗", "💰"]):
            paste_center(c, emoji(e, 130), W / 2 + (i * 2 - 1) * 380, 650, pop(t, wt(k, "Clyde") - 0.1 + 0.1 * i), a, rot=(i * 2 - 1) * 10)
    source(c, t, k, "La Silla Rota")

def sc_c4(c, t):
    k = "c4"; a = seg_alpha(t, k)
    header(c, t, 4, "GUIÑOS A VICE CITY", S[k] + 0.05, color=TEAL, title_size=110)
    # cartel de hotel con neón
    if t >= wt(k, "hotel") - 0.15:
        sign = Image.new("RGBA", (760, 300), (0, 0, 0, 0))
        d = ImageDraw.Draw(sign)
        flick = 1.0 if (t * 7) % 3 > 0.25 else 0.55
        d.rounded_rectangle((0, 0, 759, 299), 40, fill=(20, 10, 40, 240), outline=PINK + (int(255 * flick),), width=12)
        l1 = text_img("OCEAN VIEW", 110, fill=(255, 140, 220), stroke=6, path=FONT_BLACK_IT)
        l2 = text_img("HOTEL", 70, fill=TEAL, stroke=6)
        sign.alpha_composite(l1, ((760 - l1.width) // 2, 30))
        sign.alpha_composite(l2, ((760 - l2.width) // 2, 175))
        glow = sign.filter(ImageFilter.GaussianBlur(18))
        paste_center(c, glow, W / 2, 760, pop(t, wt(k, "hotel") - 0.15), a * 0.7 * flick)
        paste_center(c, sign, W / 2, 760, pop(t, wt(k, "hotel") - 0.15), a)
    if t >= wt(k, "sigue") - 0.1:
        paste_center(c, emoji("🌴", 140), W / 2 - 410, 640, pop(t, wt(k, "sigue") - 0.1), a, rot=-8)
    if t >= wt(k, "camisa") - 0.15:
        paste_center(c, emoji("👕", 220), W / 2 - 160, 1060, pop(t, wt(k, "camisa") - 0.15), a, rot=-6)
        paste_center(c, emoji("🌺", 110), W / 2 - 140, 1060, pop(t, wt(k, "camisa") - 0.05), a)
    if t >= wt(k, "Tommy") - 0.1:
        paste_center(c, badge_img("ESTILO TOMMY VERCETTI", 52, bg=YELLOW), W / 2 + 160, 1260, pop(t, wt(k, "Tommy") - 0.1), a, rot=-3)
    source(c, t, k, "Retro Playing BCN")

def sc_c5(c, t):
    k = "c5"; a = seg_alpha(t, k)
    header(c, t, 5, "RESERVAS DE LOCURA", S[k] + 0.05, color=GREEN, title_size=110)
    t0, t1 = wt(k, "casi") - 0.1, wt(k, "reservas") + 0.2
    v = int(15_880_000 * ease_out(prog(t, t0, t1)))
    paste_center(c, counter_box(f"{v:,}".replace(",", "."), GREEN, size=130), W / 2, 860, pop(t, S[k] + 0.1), a)
    paste_center(c, text_img("RESERVAS", 70, fill=WHITE, stroke=7), W / 2, 1030, pop(t, wt(k, "reservas") - 0.1), a)
    if t >= wt(k, "salir") - 0.1:
        paste_center(c, badge_img("ANTES DE SALIR", 60, bg=YELLOW), W / 2, 600, pop(t, wt(k, "salir") - 0.1), a, rot=2)
    if t >= wt(k, "reservas"):
        paste_center(c, emoji("🛒", 160), W / 2 + 390, 690, pop(t, wt(k, "reservas")), a, rot=10)
    if t >= wt(k, "Sensor") - 0.1:
        paste_center(c, text_img("(estimación de Sensor Tower)", 48, fill=WHITE, stroke=5, path=FONT_BLACK_IT), W / 2, 1150, pop(t, wt(k, "Sensor") - 0.1), a)
    source(c, t, k, "Vandal · Sensor Tower")

def sc_c6(c, t):
    k = "c6"; a = seg_alpha(t, k)
    header(c, t, 6, "CENSURA EN JAPÓN", S[k] + 0.05, color=WHITE, title_size=116)
    if t >= wt(k, "Japón") - 0.15:
        flag = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
        fd = ImageDraw.Draw(flag)
        fd.rounded_rectangle((0, 0, 299, 199), 16, fill=WHITE + (255,), outline=BLACK + (255,), width=6)
        fd.ellipse((90, 40, 210, 160), fill=(220, 20, 50, 255))
        paste_center(c, flag, W / 2 - 330, 640, pop(t, wt(k, "Japón") - 0.15), a, rot=-8)
    # ducha
    cx, cy = W / 2 + 60, 980
    if t >= wt(k, "ducha") - 0.2:
        paste_center(c, emoji("🚿", 200), cx + 130, cy - 230, pop(t, wt(k, "ducha") - 0.2), a, rot=-10)
        d = ImageDraw.Draw(c)
        for i in range(10):
            ph = (t * 2 + i * 0.1) % 1
            x = cx + 40 + (i - 5) * 18
            y = cy - 160 + ph * 380
            d.line((x, y, x - 6, y + 30), fill=(150, 220, 255, int(200 * a * (1 - ph))), width=6)
        paste_center(c, person_card("JASON", TEAL, 340, 430), cx - 10, cy + 60, pop(t, wt(k, "Jason") - 0.1), a)
    if t >= wt(k, "tanga") - 0.1:
        bar = Image.new("RGBA", (380, 84), (0, 0, 0, 0))
        ImageDraw.Draw(bar).rounded_rectangle((0, 0, 379, 83), 14, fill=(10, 10, 10, 255))
        cz = text_img("CENSURADO", 44, fill=WHITE, stroke=0, shadow=False)
        bar.alpha_composite(cz, ((380 - cz.width) // 2, (84 - cz.height) // 2))
        paste_center(c, bar, cx - 10, cy + 95, pop(t, wt(k, "tanga") - 0.1), a, rot=-4)
    if t >= wt(k, "negro") - 0.05:
        paste_center(c, badge_img("CON TANGA NEGRO", 60, bg=YELLOW), W / 2, 1320, pop(t, wt(k, "negro") - 0.05), a, rot=-2)
    if t >= wt(k, "desnudo") - 0.1:
        paste_center(c, emoji("😳", 170), W / 2 - 360, 1120, pop(t, wt(k, "desnudo") - 0.1), a, rot=-12)
    source(c, t, k, "Vandal")

def sc_cta(c, t):
    k = "cta"
    if t < S[k] - 0.1:
        return
    paste_center(c, text_img("¿CUÁL TE HA", 140, fill=WHITE, stroke=12), W / 2, 460, pop(t, wt(k, "Cuál") - 0.1))
    paste_center(c, text_img("SORPRENDIDO?", 140, fill=YELLOW, stroke=13, path=FONT_BLACK_IT), W / 2, 620, pop(t, wt(k, "sorprendido") - 0.1), rot=-3)
    for i in range(6):
        tt = wt(k, "más") + 0.08 * i
        if t >= tt:
            x = W / 2 + (i - 2.5) * 150
            paste_center(c, badge_img(f"#{i + 1}", 64, bg=PINK, fg=WHITE), x, 800, pop(t, tt) * (1 + 0.06 * math.sin(t * 6 + i)))
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
        paste_center(c, bub, W / 2, 1060, pop(t, tb, 0.4) * (1 + 0.02 * math.sin(t * 6)))
    if t >= tb + 0.5:
        d = ImageDraw.Draw(c)
        bounce = abs(math.sin((t - tb) * 5)) * 40
        ax, ay = W / 2, 1290 + bounce
        d.polygon([(ax - 40, ay), (ax + 40, ay), (ax + 40, ay + 70), (ax + 85, ay + 70), (ax, ay + 150),
                   (ax - 85, ay + 70), (ax - 40, ay + 70)], fill=YELLOW + (255,), outline=BLACK + (255,), width=8)


SCENES = {"hook": sc_hook, "c1": sc_c1, "c2": sc_c2, "c3": sc_c3, "c4": sc_c4, "c5": sc_c5, "c6": sc_c6, "cta": sc_cta}

# --------------------------------------------------------------------------
# subtítulos palabra a palabra (solo curiosidades)
CHUNK = 3
DISPLAY = {"seis": "6", "noventa": "90", "dieciséis": "16"}
HL = {"noventa", "90", "millones", "día", "récord", "MrBeast", "Lucía", "primera", "femenina", "Bonnie", "Clyde",
      "Ocean", "View", "Vice", "City", "Tommy", "Vercetti", "16", "reservas", "Japón", "tanga", "negro", "desnudo"}

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
    for tc, f in [(wt("c1", "récord"), 1174.7), (wt("c5", "reservas"), 880.0), (wt("c6", "tanga"), 587.3)]:
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
    silent = os.path.join(HERE, "short7_curiosidades2_sin_musica.mp4")
    music = os.path.join(HERE, "musica.wav")
    voz = os.path.join(HERE, "voz", "voz.wav")
    final = os.path.join(HERE, "short7_curiosidades2.mp4")
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
                    "-shortest", os.path.join(HERE, "short7_curiosidades2_solo_voz.mp4")], check=True)
    print("OK ->", final)

if __name__ == "__main__":
    main()
