"""
SHORT 2 — «6 cosas que no sabías de GTA 6»
Vertical 1080x1920, 30 fps. Reutiliza el estilo y utilidades del Short 1.

  python3 gen_voz.py     -> voz/voz.wav + voz/timeline.json (voz IA, tiempos por palabra)
  python3 render.py      -> short2_curiosidades.mp4 (+ _sin_musica / _solo_voz)
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
def sc_hook(c, t):
    k = "hook"
    a = seg_alpha(t, k)
    sh = math.sin(t * 60) * 6 * max(0, 1 - t / 0.4)
    six = text_img("6", 520, fill=YELLOW, stroke=22, path=FONT_BLACK_IT)
    paste_center(c, six, W / 2 + sh, 560, pop(t, wt(k, "Seis") - 0.1, 0.4) * (1 + 0.03 * math.sin(t * 6)), a, rot=-6)
    paste_center(c, text_img("COSAS QUE", 104, stroke=10), W / 2, 880, pop(t, wt(k, "curiosidades") - 0.1), a)
    paste_center(c, text_img("NO SABÍAS", 140, fill=PINK, stroke=12, path=FONT_BLACK_IT), W / 2, 1010, pop(t, wt(k, "no") - 0.1), a, rot=-2)
    paste_center(c, text_img("DE GTA 6", 120, stroke=11), W / 2, 1150, pop(t, wt(k, "GTA") - 0.1), a)
    t2 = wt(k, "La") - 0.05
    if t >= t2:
        paste_center(c, badge_img("LA ÚLTIMA ES UNA LOCURA", 58, bg=YELLOW), W / 2, 1320, pop(t, t2), a, rot=2)
        paste_center(c, emoji("🤯", 150), W / 2 + 400, 1240, pop(t, wt(k, "locura") - 0.1), a, rot=12)

def sc_c1(c, t):
    k = "c1"
    a = seg_alpha(t, k)
    header(c, t, 1, "LEÓN + FLORIDA", wt(k, "León"), color=YELLOW, title_size=110)
    t0, tl = S[k], wt(k, "por")
    morph = prog(t, wt(k, "Florida"), wt(k, "Florida") + 1.0)
    mp = B.render_map(t, prog(t, t0, t0 + 0.9), prog(t, t0 + 0.5, t0 + 1.0), morph, prog(t, wt(k, "Florida") + 0.9, wt(k, "Florida") + 1.3))
    paste_center(c, mp, W / 2, 960, 0.72, a)
    if t >= wt(k, "Florida") + 0.4:
        paste_center(c, text_img("= LEONIDA", 120, fill=TEAL, stroke=11, path=FONT_BLACK_IT), W / 2, 560,
                     pop(t, wt(k, "Florida") + 0.4), a, rot=-2)
    if t >= wt(k, "Ponce"):
        paste_center(c, badge_img("PONCE DE LEÓN · 1513", 52, bg=WHITE), W / 2, 1290, pop(t, wt(k, "Ponce") - 0.1), a, rot=-3)
    source(c, t, k, "EssentiallySports")

def sc_c2(c, t):
    k = "c2"
    a = seg_alpha(t, k)
    header(c, t, 2, "GRASS RIVERS", wt(k, "Grass") - 0.1, color=GREEN)
    # pantano: agua + hierbas que se mecen
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    top = 900
    d.rounded_rectangle((70, top, W - 70, 1330), 60, fill=(20, 90, 90, int(220 * a)), outline=BLACK + (int(255 * a),), width=8)
    for j in range(5):
        yy = top + 90 + j * 75
        pts = [(x, yy + 10 * math.sin(x / 60 + t * 3 + j)) for x in range(100, W - 100, 20)]
        d.line(pts, fill=(120, 230, 210, int(120 * a)), width=5)
    rng = np.random.default_rng(3)
    for i in range(26):
        x = 90 + i * 37 + rng.uniform(-10, 10)
        h = rng.uniform(90, 200)
        sway = 18 * math.sin(t * 2.2 + i)
        side = top + (0 if i % 2 else 430)
        base_y = side + (20 if side == top else -20)
        tip = (x + sway, base_y - h if side == top else base_y - h)
        d.line([(x, base_y), tip], fill=(90, 200, 70, int(255 * a)), width=9)
    c.alpha_composite(layer)
    # caimán que cruza
    tc = wt(k, "hay") - 0.5
    if t >= tc:
        p = prog(t, tc, tc + 1.4)
        x = lerp(W + 200, W / 2, ease_out(p))
        y = 1120 + 8 * math.sin(t * 5)
        paste_center(c, emoji("🐊", 330), x, y, 1.0, a, rot=-10 + 4 * math.sin(t * 4))
    if t >= wt(k, "Everglades"):
        paste_center(c, text_img("(los Everglades del juego)", 54, fill=WHITE, stroke=6, path=FONT_BLACK_IT), W / 2, 540,
                     pop(t, wt(k, "Everglades")), a)
    source(c, t, k, "GTABoom")

def sc_c3(c, t):
    k = "c3"
    a = seg_alpha(t, k)
    header(c, t, 3, "PODCASTS A PIE", wt(k, "podcasts") - 0.1, color=TEAL, title_size=112)
    cx, cy = W / 2, 1000
    # ondas de sonido
    d = ImageDraw.Draw(c)
    for i in range(4):
        ph = ((t * 0.8 + i / 4) % 1)
        r = 180 + ph * 300
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=TEAL + (int(200 * (1 - ph) * a),), width=8)
    walk = math.sin(t * 6) * 10
    paste_center(c, emoji("🚶", 300), cx + 10, cy + 40 + abs(walk), pop(t, S[k]), a)
    if t >= wt(k, "auriculares") - 0.1:
        paste_center(c, emoji("🎧", 170), cx + 15, cy - 175, pop(t, wt(k, "auriculares") - 0.1), a, rot=walk / 2)
    # notas flotando
    for i in range(5):
        ph = (t * 0.6 + i * 0.21) % 1
        nx = cx - 300 + i * 150 + 30 * math.sin(t * 2 + i)
        ny = cy + 200 - ph * 500
        paste_center(c, text_img("♪" if i % 2 else "♫", 90, fill=YELLOW, stroke=6, path="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                     nx, ny, 1.0, a * math.sin(ph * math.pi) * prog(t, wt(k, "escuchar"), wt(k, "escuchar") + 0.3))
    if t >= S[k]:
        paste_center(c, badge_img("POR PRIMERA VEZ", 56, bg=YELLOW), W / 2, 560, pop(t, S[k] + 0.05), a, rot=2)
    source(c, t, k, "PlayStation Blog")

def sc_c4(c, t):
    k = "c4"
    a = seg_alpha(t, k)
    header(c, t, 4, "TRÁILER 1", wt(k, "tráiler") - 0.1, color=WHITE)
    # reproductor de vídeo genérico
    x0, y0, x1, y1 = 110, 720, W - 110, 1250
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    al = int(255 * a)
    d.rounded_rectangle((x0, y0, x1, y1), 40, fill=(15, 10, 30, int(235 * a)), outline=WHITE + (al,), width=8)
    # play
    pcx, pcy = W / 2, (y0 + y1) / 2 - 30
    d.ellipse((pcx - 90, pcy - 90, pcx + 90, pcy + 90), fill=RED + (al,))
    d.polygon([(pcx - 30, pcy - 45), (pcx - 30, pcy + 45), (pcx + 50, pcy)], fill=WHITE + (al,))
    # barra que avanza demasiado rápido
    pr = ease_in_out(prog(t, wt(k, "estrenó"), wt(k, "tiempo") + 0.3))
    by = y1 - 70
    d.rounded_rectangle((x0 + 50, by, x1 - 50, by + 16), 8, fill=(255, 255, 255, int(80 * a)))
    d.rounded_rectangle((x0 + 50, by, x0 + 50 + (x1 - x0 - 100) * pr, by + 16), 8, fill=RED + (al,))
    c.alpha_composite(layer)
    if t >= wt(k, "antes"):
        paste_center(c, badge_img("ANTES DE TIEMPO", 56, bg=YELLOW), W / 2, 560, pop(t, wt(k, "antes") - 0.05), a, rot=2)
    stamp(c, "FILTRADO", W / 2, 1000, wt(k, "filtración") - 0.05, t, size=130)
    if t >= wt(k, "filtración") + 0.15:
        paste_center(c, emoji("😳", 190), W / 2 + 360, 1180, pop(t, wt(k, "filtración") + 0.15), a, rot=10)
    source(c, t, k, "Windows Central")

def sc_c5(c, t):
    k = "c5"
    a = seg_alpha(t, k)
    header(c, t, 5, "#1 EN RESERVAS", wt(k, "reservado") - 0.1, color=YELLOW, title_size=112)
    # gráfico de barras: el último sale disparado
    base_y, x_start, bw, gap = 1250, 150, 120, 35
    hs = [180, 240, 210, 290, 260]
    grow = ease_out(prog(t, S[k] + 0.1, S[k] + 0.9))
    d = ImageDraw.Draw(c)
    al = int(255 * a)
    for i, h in enumerate(hs):
        x = x_start + i * (bw + gap)
        d.rounded_rectangle((x, base_y - h * grow, x + bw, base_y), 14, fill=(170, 150, 210, al), outline=BLACK + (al,), width=5)
    big = ease_out(prog(t, wt(k, "más"), wt(k, "historia")))
    x = x_start + 5 * (bw + gap)
    hb = lerp(10, 560, big)
    d.rounded_rectangle((x, base_y - hb, x + bw, base_y), 14, fill=YELLOW + (al,), outline=BLACK + (al,), width=6)
    d.line((110, base_y, W - 110, base_y), fill=WHITE + (al,), width=6)
    if big > 0.9:
        paste_center(c, emoji("🏆", 170), x + bw / 2, base_y - hb - 100, pop(t, wt(k, "historia")), a, rot=-6)
    if t >= wt(k, "Xbox"):
        paste_center(c, badge_img("MICROSOFT STORE", 56, bg=(80, 200, 90), fg=WHITE), W / 2, 560, pop(t, wt(k, "Xbox") - 0.05), a, rot=2)
    if t >= wt(k, "historia"):
        paste_center(c, text_img("EL MÁS RESERVADO DE LA HISTORIA", 50, fill=WHITE, stroke=6), W / 2, 1320, pop(t, wt(k, "historia")), a)
    source(c, t, k, "Xbox Wire")

def sc_c6(c, t):
    k = "c6"
    a = seg_alpha(t, k)
    header(c, t, 6, "LA MÁS LOCA", S[k] + 0.05, color=PINK, title_size=110)
    stamp(c, "RETRASO", W / 2 - 180, 700, wt(k, "retrasó"), t, size=80, rot=-14)
    stamp(c, "RETRASO", W / 2 + 180, 790, wt(k, "veces") - 0.05, t, size=80, rot=10)
    ts = wt(k, "hoy") - 0.1
    if t >= ts:
        # marcador de nota (genérico)
        v = int(round(99 * ease_out(prog(t, ts, wt(k, "sobre")))))
        box = 370
        im = Image.new("RGBA", (box + 40, box + 40), (0, 0, 0, 0))
        dd = ImageDraw.Draw(im)
        dd.rounded_rectangle((20, 20, box + 20, box + 20), 50, fill=GREEN + (255,), outline=BLACK + (255,), width=12)
        num = text_img(str(v), 230, fill=WHITE, stroke=12)
        im.alpha_composite(num, ((im.width - num.width) // 2, (im.height - num.height) // 2 - 15))
        s = pop(t, ts, 0.4) * (1.08 if wt(k, "sobre") <= t < wt(k, "sobre") + 0.12 else 1.0)
        paste_center(c, im, W / 2 - 40, 1010, s, a, rot=-3)
        if t >= wt(k, "sobre"):
            paste_center(c, text_img("/100", 110, fill=WHITE, stroke=10), W / 2 + 250, 1150, pop(t, wt(k, "sobre")), a)
        if t >= wt(k, "Metacritic") - 0.1:
            paste_center(c, badge_img("METACRITIC · 150 RESEÑAS", 50, bg=WHITE), W / 2, 1300, pop(t, wt(k, "Metacritic") - 0.1), a, rot=2)
            paste_center(c, emoji("🤯", 170), W / 2 - 340, 1150, pop(t, wt(k, "Metacritic")), a, rot=-12)
    source(c, t, k, "Yahoo Tech")

def sc_cta(c, t):
    k = "cta"
    if t < S[k] - 0.1:
        return
    paste_center(c, text_img("¿CUÁL", 150, fill=WHITE, stroke=12), W / 2, 480, pop(t, wt(k, "Cuál") - 0.1))
    paste_center(c, text_img("NO SABÍAS?", 150, fill=YELLOW, stroke=13, path=FONT_BLACK_IT), W / 2, 640, pop(t, wt(k, "no") - 0.1), rot=-3)
    # chips 1-6
    for i in range(6):
        tt = wt(k, "sabías") + 0.08 * i
        if t >= tt:
            x = W / 2 + (i - 2.5) * 150
            paste_center(c, badge_img(f"#{i + 1}", 64, bg=PINK, fg=WHITE), x, 820, pop(t, tt) * (1 + 0.06 * math.sin(t * 6 + i)))
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
DISPLAY = {"seis": "6"}
HL = {"Leonida", "León", "Florida", "Everglades", "Grass", "Rivers", "caimanes", "auriculares", "podcasts",
      "tráiler", "filtración", "Xbox", "reservado", "historia", "99", "100", "Metacritic", "dos", "primera"}

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
    for tc, f in [(wt("c4", "filtración"), 880.0), (wt("c5", "historia"), 1174.7), (wt("c6", "sobre"), 1318.5)]:
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
    silent = os.path.join(HERE, "short2_curiosidades_sin_musica.mp4")
    music = os.path.join(HERE, "musica.wav")
    voz = os.path.join(HERE, "voz", "voz.wav")
    final = os.path.join(HERE, "short2_curiosidades.mp4")
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
                    "-shortest", os.path.join(HERE, "short2_curiosidades_solo_voz.mp4")], check=True)
    print("OK ->", final)

if __name__ == "__main__":
    main()
