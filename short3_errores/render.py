"""
SHORT 3 — «6 errores en GTA 6»
Vertical 1080x1920, 30 fps. Reutiliza el estilo y utilidades del Short 1.

  python3 gen_voz.py     -> voz/voz.wav + voz/timeline.json (voz IA, tiempos por palabra)
  python3 render.py      -> short3_errores.mp4 (+ _sin_musica / _solo_voz)
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
# cabecera y escenas del Short 3
def header(canvas, t, n, title, title_t, color=WHITE, title_size=112):
    key = f"c{n}"
    a = seg_alpha(t, key)
    paste_center(canvas, badge_img(f"ERROR {n}", 76, bg=RED, fg=WHITE), W / 2, 215, pop(t, S[key] - 0.05), a, rot=-4)
    d = ImageDraw.Draw(canvas)
    for i in range(6):
        x = W / 2 + (i - 2.5) * 46
        on = i < n
        col = (RED if on else (255, 255, 255)) + (int(255 * a * (1 if on else 0.35)),)
        d.ellipse((x - 12, 300 - 12, x + 12, 300 + 12), fill=col, outline=BLACK + (int(255 * a),), width=3)
    if t >= title_t:
        ti = text_img(title, title_size, fill=color, stroke=12, path=FONT_BLACK_IT)
        sc = min(1.0, (W - 60) / ti.width)
        paste_center(canvas, ti, W / 2, 420, pop(t, title_t) * sc, a, rot=-2)

def source(canvas, t, key, txt):
    a = seg_alpha(t, key) * 0.8 * prog(t, S[key] + 0.2, S[key] + 0.5)
    ti = text_img("Fuente: " + txt, 34, fill=WHITE, stroke=4, path=FONT_BOLD, shadow=False)
    paste_center(canvas, ti, W / 2, 1525, 1.0, a)

def big_x(canvas, cx, cy, size, t, t0, a=1.0):
    if t < t0:
        return
    s = pop(t, t0, 0.35)
    im = Image.new("RGBA", (size + 40, size + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = 20
    for wdt, col in [(int(size * 0.26), BLACK), (int(size * 0.18), RED)]:
        d.line((m + 20, m + 20, size - 20 + m - 20, size - 20 + m - 20), fill=col + (255,), width=wdt)
        d.line((size - 20 + m - 20, m + 20, m + 20, size - 20 + m - 20), fill=col + (255,), width=wdt)
    paste_center(canvas, im, cx, cy, s, a, rot=-8)

def money_bill(color=(70, 170, 80), w=230, h=110, ink=0.0):
    im = Image.new("RGBA", (w + 10, h + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((5, 5, w + 5, h + 5), 14, fill=color + (255,), outline=BLACK + (255,), width=5)
    d.ellipse((w / 2 - 32, h / 2 - 28, w / 2 + 38, h / 2 + 38), outline=(20, 80, 30, 255), width=6)
    tt = text_img("$", 60, fill=(20, 80, 30), stroke=0, shadow=False)
    im.alpha_composite(tt, (int(w / 2 + 5 - tt.width / 2), int(h / 2 + 5 - tt.height / 2)))
    if ink > 0:
        rng = np.random.default_rng(5)
        for _ in range(int(14 * ink)):
            x, y, r = rng.uniform(10, w), rng.uniform(10, h), rng.uniform(12, 34)
            d.ellipse((x - r, y - r, x + r, y + r), fill=(40, 90, 230, 235))
    return im

def sc_hook(c, t):
    k = "hook"
    a = seg_alpha(t, k)
    big_x(c, W / 2, 520, 420, t, 0.0, a * 0.95)
    paste_center(c, text_img("6 ERRORES", 170, fill=WHITE, stroke=14, path=FONT_BLACK_IT), W / 2, 860, pop(t, wt(k, "errores") - 0.1), a, rot=-3)
    paste_center(c, text_img("QUE NO DEBES COMETER", 78, fill=YELLOW, stroke=9), W / 2, 1020, pop(t, wt(k, "no") - 0.1), a)
    paste_center(c, text_img("EN GTA 6", 150, fill=PINK, stroke=13), W / 2, 1170, pop(t, wt(k, "GTA") - 0.1), a, rot=2)

def sc_c1(c, t):
    k = "c1"; a = seg_alpha(t, k)
    header(c, t, 1, "NO GUARDAR EL DINERO", S[k] + 0.05, color=WHITE, title_size=100)
    cx, cy = W / 2, 1000
    paste_center(c, emoji("🏃", 280), cx, cy + 40 + abs(math.sin(t * 7)) * 12, pop(t, S[k]), a)
    tl = wt(k, "pierdes") - 0.15
    # fajo de billetes encima
    for i in range(4):
        fly = ease_out(prog(t, tl, tl + 0.8))
        x = cx - 60 + i * 40 + fly * (i - 1.5) * 260
        y = cy - 200 - i * 22 - fly * (300 + i * 60)
        if t >= wt(k, "encima") - 0.3:
            paste_center(c, money_bill(), x, y, 0.8 * pop(t, wt(k, "encima") - 0.3 + 0.07 * i), a * (1 - fly * 0.9), rot=8 * i - 12 + fly * 90 * (i - 1.5))
    if t >= wt(k, "mueres") - 0.1:
        paste_center(c, emoji("💀", 160), cx - 330, cy + 120, pop(t, wt(k, "mueres") - 0.1), a, rot=-10)
    if t >= wt(k, "pillan") - 0.1:
        paste_center(c, emoji("🚔", 180), cx + 330, cy + 120, pop(t, wt(k, "pillan") - 0.1), a, rot=8)
    stamp(c, "LO PIERDES", W / 2, 1290, tl, t, size=90, rot=-6)
    source(c, t, k, "HappyGamer")

def sc_c2(c, t):
    k = "c2"; a = seg_alpha(t, k)
    header(c, t, 2, "ROBAR BANCOS YA", S[k] + 0.05, color=WHITE)
    paste_center(c, emoji("🏦", 260), W / 2, 760, pop(t, S[k] + 0.05), a)
    ink = prog(t, wt(k, "tinta") - 0.1, wt(k, "tinta") + 0.4)
    for i in range(3):
        paste_center(c, money_bill(ink=ink), W / 2 + (i - 1) * 270, 1040, pop(t, wt(k, "dinero") - 0.1 + 0.08 * i), a, rot=(i - 1) * 6)
    if t >= wt(k, "tinta"):
        paste_center(c, badge_img("TINTA ANTIRROBO", 56, bg=(40, 90, 230), fg=WHITE), W / 2, 560, pop(t, wt(k, "tinta")), a, rot=2)
    if t >= wt(k, "capítulo") - 0.1:
        paste_center(c, badge_img("HASTA EL CAPÍTULO 3", 60, bg=YELLOW), W / 2, 1280, pop(t, wt(k, "capítulo") - 0.1), a, rot=-3)
    source(c, t, k, "EndgameTools")

def sc_c3(c, t):
    k = "c3"; a = seg_alpha(t, k)
    header(c, t, 3, "IR A LO LOCO", S[k] + 0.05, color=YELLOW, title_size=120)
    paste_center(c, emoji("🏪", 200), W / 2, 640, pop(t, wt(k, "tienda") - 0.15), a)
    levels = [("BAJA", GREEN, "SOLO"), ("MEDIA", YELLOW, "EN EQUIPO"), ("ALTA", RED, "EN EQUIPO")]
    t0 = wt(k, "seguridad") - 0.3
    for i, (lab, col, who) in enumerate(levels):
        y = 860 + i * 150
        tt = t0 + 0.18 * i
        if t >= tt:
            card = Image.new("RGBA", (860, 120), (0, 0, 0, 0))
            d = ImageDraw.Draw(card)
            d.rounded_rectangle((0, 0, 859, 119), 30, fill=(25, 10, 45, 235), outline=col + (255,), width=8)
            for j in range(3):
                d.rounded_rectangle((30 + j * 46, 70 - j * 18, 66 + j * 46, 98), 6,
                                    fill=(col if j <= i else (90, 80, 110)) + (255,))
            l1 = text_img(lab, 60, fill=col, stroke=6)
            card.alpha_composite(l1, (200, (120 - l1.height) // 2))
            l2 = text_img(who, 52, fill=WHITE, stroke=6)
            card.alpha_composite(l2, (840 - l2.width, (120 - l2.height) // 2))
            paste_center(c, card, W / 2, y, pop(t, tt), a)
    if t >= wt(k, "mapa") - 0.1:
        paste_center(c, badge_img("JASON + LUCÍA", 54, bg=PINK, fg=WHITE), W / 2 + 230, 1300, pop(t, wt(k, "mapa") - 0.1), a, rot=-4)
    source(c, t, k, "EndgameTools")

def sc_c4(c, t):
    k = "c4"; a = seg_alpha(t, k)
    header(c, t, 4, "NO MIRAR EL BUZÓN", S[k] + 0.05, color=TEAL, title_size=110)
    cx, cy = W / 2, 980
    paste_center(c, emoji("📬", 340), cx, cy, pop(t, wt(k, "buzón") - 0.15) * (1 + 0.03 * math.sin(t * 6)), a)
    t0 = wt(k, "llega") - 0.2
    for i in range(4):
        p = prog(t, t0 + i * 0.25, t0 + i * 0.25 + 0.7)
        if 0 < p < 1:
            x = lerp(cx + (420 if i % 2 else -420), cx, ease_in_out(p))
            y = lerp(cy - 380 + i * 40, cy - 40, ease_in_out(p))
            paste_center(c, emoji("✉️", 110), x, y, 1.0, a * (1 - p * 0.4), rot=(1 - p) * 30 * (1 if i % 2 else -1))
    if t >= wt(k, "dinero") - 0.1:
        rise = ease_out(prog(t, wt(k, "dinero") - 0.1, wt(k, "dinero") + 0.8))
        paste_center(c, text_img("+$$$", 120, fill=GREEN, stroke=11), cx + 240, cy - 160 - rise * 60, pop(t, wt(k, "dinero") - 0.1), a, rot=8)
    if t >= wt(k, "misiones") - 0.1:
        paste_center(c, badge_img("PAGOS DE MISIONES + BRIAN", 50, bg=YELLOW), W / 2, 1300, pop(t, wt(k, "misiones") - 0.1), a, rot=-2)
    source(c, t, k, "OutputLag")

def sc_c5(c, t):
    k = "c5"; a = seg_alpha(t, k)
    header(c, t, 5, "VENDER MAL", S[k] + 0.05, color=ORANGE, title_size=130)
    paste_center(c, emoji("💎", 170), W / 2, 640, pop(t, wt(k, "botín") - 0.1), a, rot=-6)
    t0 = wt(k, "perista") - 0.1
    for i, (lab, val, col) in enumerate([("PERISTA A", 500, (170, 150, 210)), ("PERISTA B", 1200, GREEN)]):
        x = W / 2 + (i - 0.5) * 440
        tt = t0 + 0.2 * i
        if t >= tt:
            v = int(val * ease_out(prog(t, tt, tt + 0.8)))
            card = Image.new("RGBA", (380, 420), (0, 0, 0, 0))
            d = ImageDraw.Draw(card)
            d.rounded_rectangle((0, 0, 379, 419), 40, fill=(25, 10, 45, 235), outline=col + (255,), width=10)
            l1 = text_img(lab, 50, fill=WHITE, stroke=5)
            card.alpha_composite(l1, ((380 - l1.width) // 2, 40))
            l2 = text_img(f"${v:,}".replace(",", "."), 96, fill=col, stroke=9)
            card.alpha_composite(l2, ((380 - l2.width) // 2, 170))
            paste_center(c, card, x, 1010, pop(t, tt), a, rot=(-1) ** i * 3)
    if t >= wt(k, "más") - 0.05:
        paste_center(c, emoji("✅", 130), W / 2 + 220 + 150, 820, pop(t, wt(k, "más") - 0.05), a)
        paste_center(c, badge_img("COMPARA ANTES DE VENDER", 50, bg=YELLOW), W / 2, 1300, pop(t, wt(k, "cosas") - 0.1), a, rot=2)
    source(c, t, k, "EndgameTools")

def sc_c6(c, t):
    k = "c6"; a = seg_alpha(t, k)
    header(c, t, 6, "FARMEAR SIN PARAR", S[k] + 0.05, color=PINK, title_size=110)
    t0, t1 = wt(k, "Al") - 0.1, wt(k, "igual") + 0.3
    v = int(lerp(25000, 0, ease_in_out(prog(t, t0, t1))))
    box = Image.new("RGBA", (820, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(box)
    col = GREEN if v > 8000 else (YELLOW if v > 2000 else RED)
    d.rounded_rectangle((0, 0, 819, 299), 50, fill=(25, 10, 45, 235), outline=col + (255,), width=12)
    num = text_img(f"${v:,}".replace(",", "."), 170, fill=col, stroke=12)
    box.alpha_composite(num, ((820 - num.width) // 2, (300 - num.height) // 2))
    shake = math.sin(t * 50) * 6 if t0 < t < t1 else 0
    paste_center(c, box, W / 2 + shake, 900, pop(t, wt(k, "dinero") - 0.15), a)
    if t >= wt(k, "dinero"):
        paste_center(c, emoji("💸", 160), W / 2 - 330, 690, pop(t, wt(k, "dinero")), a, rot=-12)
    if t >= t0:
        paste_center(c, emoji("📉", 170), W / 2 + 330, 690, pop(t, t0), a, rot=10)
    if t >= wt(k, "acabar") - 0.1:
        paste_center(c, badge_img("SE ACABA IGUAL: NO FARMEES", 50, bg=YELLOW), W / 2, 1200, pop(t, wt(k, "acabar") - 0.1), a, rot=-2)
    source(c, t, k, "Red Bull")

def sc_cta(c, t):
    k = "cta"
    if t < S[k] - 0.1:
        return
    paste_center(c, text_img("¿CUÁL HAS", 150, fill=WHITE, stroke=12), W / 2, 480, pop(t, wt(k, "Cuál") - 0.1))
    paste_center(c, text_img("COMETIDO?", 150, fill=YELLOW, stroke=13, path=FONT_BLACK_IT), W / 2, 640, pop(t, wt(k, "cometido") - 0.15), rot=-3)
    for i in range(6):
        tt = wt(k, "estos") + 0.08 * i
        if t >= tt:
            x = W / 2 + (i - 2.5) * 150
            paste_center(c, badge_img(f"{i + 1}", 64, bg=RED, fg=WHITE), x, 820, pop(t, tt) * (1 + 0.06 * math.sin(t * 6 + i)))
    tb = wt(k, "Guárdalo") - 0.1
    if t >= tb:
        bw, bh = 860, 230
        bub = Image.new("RGBA", (bw + 40, bh + 110), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bub)
        bd.rounded_rectangle((20, 20, bw + 20, bh + 20), 60, fill=WHITE + (255,), outline=BLACK + (255,), width=10)
        bd.polygon([(140, bh + 10), (230, bh + 10), (120, bh + 100)], fill=WHITE + (255,), outline=BLACK + (255,))
        bd.line([(140, bh + 14), (230, bh + 14)], fill=WHITE + (255,), width=14)
        tl = text_img("GUÁRDALO", 70, fill=BLACK, stroke=0, shadow=False)
        tl2 = text_img("Y COMENTA", 86, fill=PINK, stroke=6)
        bub.alpha_composite(tl, ((bub.width - tl.width) // 2, 28))
        bub.alpha_composite(tl2, ((bub.width - tl2.width) // 2, 128))
        paste_center(c, bub, W / 2, 1060, pop(t, tb, 0.4) * (1 + 0.02 * math.sin(t * 6)))
        paste_center(c, emoji("🔖", 150), W / 2 + 400, 940, pop(t, tb + 0.1), rot=12)
    if t >= tb + 0.4:
        d = ImageDraw.Draw(c)
        bounce = abs(math.sin((t - tb) * 5)) * 40
        ax, ay = W / 2, 1290 + bounce
        d.polygon([(ax - 40, ay), (ax + 40, ay), (ax + 40, ay + 70), (ax + 85, ay + 70), (ax, ay + 150),
                   (ax - 85, ay + 70), (ax - 40, ay + 70)], fill=YELLOW + (255,), outline=BLACK + (255,), width=8)


SCENES = {"hook": sc_hook, "c1": sc_c1, "c2": sc_c2, "c3": sc_c3, "c4": sc_c4, "c5": sc_c5, "c6": sc_c6, "cta": sc_cta}

# --------------------------------------------------------------------------
# subtítulos palabra a palabra (solo curiosidades)
CHUNK = 3
DISPLAY = {"seis": "6", "tres.": "3."}
HL = {"dinero", "mueres", "pillan", "pierdes", "bancos", "tinta", "capítulo", "tres", "solo", "seguridad", "mapa",
      "buzón", "misiones", "botín", "perista", "más", "Obsesionarte", "acabar", "igual"}

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
    for tc, f in [(wt("c1", "pierdes"), 440.0), (wt("c2", "tinta"), 880.0), (wt("c5", "perista") + 0.2, 1174.7), (wt("c6", "igual"), 330.0)]:
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
    silent = os.path.join(HERE, "short3_errores_sin_musica.mp4")
    music = os.path.join(HERE, "musica.wav")
    voz = os.path.join(HERE, "voz", "voz.wav")
    final = os.path.join(HERE, "short3_errores.mp4")
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
                    "-shortest", os.path.join(HERE, "short3_errores_solo_voz.mp4")], check=True)
    print("OK ->", final)

if __name__ == "__main__":
    main()
