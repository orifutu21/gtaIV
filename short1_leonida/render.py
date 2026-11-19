"""
SHORT 1 — «¿Por qué se llama Leonida?»
Renderiza un YouTube Short vertical (1080x1920, 30 fps) con Pillow + ffmpeg.

Uso:  python3 render.py            -> genera short1_leonida.mp4 (con música) y
                                      short1_leonida_sin_musica.mp4
"""
import math, os, subprocess, wave, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
DUR = 26.0
NFRAMES = int(DUR * FPS)

FONT_BLACK = "/usr/share/fonts/opentype/inter/InterDisplay-Black.otf"
FONT_BLACK_IT = "/usr/share/fonts/opentype/inter/InterDisplay-BlackItalic.otf"
FONT_BOLD = "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
if not os.path.exists(FONT_BOLD):
    FONT_BOLD = FONT_BLACK

# Paleta "atardecer neón"
PINK = (255, 64, 160)
TEAL = (40, 230, 220)
YELLOW = (255, 214, 64)
ORANGE = (255, 120, 60)
WHITE = (255, 255, 255)
BLACK = (10, 4, 20)
RED = (255, 50, 60)

# --------------------------------------------------------------------------
# utilidades
# --------------------------------------------------------------------------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))

def prog(t, t0, t1):
    return clamp((t - t0) / (t1 - t0)) if t1 > t0 else float(t >= t0)

def ease_out(x):
    return 1 - (1 - x) ** 3

def ease_in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2

def ease_back(x, s=1.9):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1

def lerp(a, b, x):
    return a + (b - a) * x

_font_cache = {}
def font(path, size):
    k = (path, size)
    if k not in _font_cache:
        _font_cache[k] = ImageFont.truetype(path, size)
    return _font_cache[k]

_txt_cache = {}
def text_img(text, size, fill=WHITE, stroke=10, stroke_fill=BLACK, path=FONT_BLACK, shadow=True):
    """Texto renderizado como RGBA recortado (cacheado)."""
    k = (text, size, fill, stroke, stroke_fill, path, shadow)
    if k in _txt_cache:
        return _txt_cache[k]
    f = font(path, size)
    l, t, r, b = f.getbbox(text, stroke_width=stroke)
    pad = 30
    w, h = r - l + pad * 2, b - t + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if shadow:
        sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - l + 8, pad - t + 10), text, font=f,
                                fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        img.alpha_composite(sh)
    d.text((pad - l, pad - t), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill)
    _txt_cache[k] = img
    return img

def two_tone(a, b, size, ca=YELLOW, cb=TEAL, stroke=14):
    k = ("2t", a, b, size)
    if k in _txt_cache:
        return _txt_cache[k]
    f = font(FONT_BLACK_IT, size)
    full = a + b
    l, t, r, bt = f.getbbox(full, stroke_width=stroke)
    pad = 30
    w, h = r - l + pad * 2, bt - t + pad * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((pad - l + 8, pad - t + 10), full, font=f, fill=(0, 0, 0, 170),
                            stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    d.text((pad - l, pad - t), full, font=f, fill=cb, stroke_width=stroke, stroke_fill=BLACK)
    d.text((pad - l, pad - t), a, font=f, fill=ca, stroke_width=stroke, stroke_fill=BLACK)
    _txt_cache[k] = img
    return img

def paste_center(canvas, img, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if alpha <= 0.003 or scale <= 0.01:
        return
    if scale != 1.0:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BICUBIC)
    if rot:
        img = img.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1.0:
        a = img.getchannel("A").point(lambda v: int(v * alpha))
        img = img.copy()
        img.putalpha(a)
    x, y = int(cx - img.width / 2), int(cy - img.height / 2)
    canvas.alpha_composite(img, (x, y)) if x >= 0 and y >= 0 and x + img.width <= W and y + img.height <= H \
        else _safe_paste(canvas, img, x, y)

def _safe_paste(canvas, img, x, y):
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    layer.paste(img, (x, y), img)
    canvas.alpha_composite(layer)

def pop(t, t0, dur=0.35):
    """escala con rebote para entradas."""
    p = prog(t, t0, t0 + dur)
    return ease_back(p) if p > 0 else 0.0

# --------------------------------------------------------------------------
# fondo
# --------------------------------------------------------------------------
def make_gradient():
    top = np.array([18, 6, 40], float)
    mid = np.array([70, 14, 90], float)
    bot = np.array([200, 60, 80], float)
    y = np.linspace(0, 1, H)[:, None]
    c = np.where(y < 0.62,
                 top + (mid - top) * (y / 0.62),
                 mid + (bot - mid) * ((y - 0.62) / 0.38))
    arr = np.repeat(c[:, None, :], W, axis=1).reshape(H, W, 3)
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB").convert("RGBA")
    # sol retro
    sun = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sun)
    cx, cy, r = W // 2, 1470, 300
    for i in range(r, 0, -2):
        k = i / r
        col = (255, int(lerp(220, 70, k)), int(lerp(80, 150, k)), 255)
        sd.ellipse((cx - i, cy - i, cx + i, cy + i), fill=col)
    # franjas del sol
    for j in range(7):
        yy = cy + 40 + j * 38
        sd.rectangle((0, yy, W, yy + 6 + j * 2), fill=(0, 0, 0, 0))
    sun_alpha = sun.getchannel("A").point(lambda v: int(v * 0.55))
    sun.putalpha(sun_alpha)
    glow = sun.filter(ImageFilter.GaussianBlur(40))
    img.alpha_composite(glow)
    img.alpha_composite(sun)
    return img

HORIZON = 1500

def draw_grid(canvas, t):
    """suelo synthwave en movimiento."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle((0, HORIZON, W, H), fill=(20, 4, 36, 235))
    col = (255, 70, 190, 200)
    # líneas horizontales con perspectiva
    off = (t * 0.9) % 1.0
    for i in range(14):
        z = (i + off)
        yy = HORIZON + (H - HORIZON) * ((z / 14) ** 2.2)
        d.line((0, yy, W, yy), fill=col, width=2 + int(3 * z / 14))
    # líneas de fuga
    for i in range(-12, 13):
        xb = W / 2 + i * 170
        d.line((W / 2 + i * 22, HORIZON, xb, H), fill=col, width=3)
    d.line((0, HORIZON, W, HORIZON), fill=(255, 150, 230, 255), width=4)
    canvas.alpha_composite(layer)

random.seed(7)
PARTICLES = [(random.uniform(0, W), random.uniform(0, HORIZON), random.uniform(1.5, 4.5),
              random.uniform(10, 40), random.uniform(0, 6.28)) for _ in range(60)]

def draw_particles(canvas, t):
    d = ImageDraw.Draw(canvas)
    for x, y, r, sp, ph in PARTICLES:
        yy = (y - t * sp) % HORIZON
        a = int(120 + 100 * math.sin(t * 2 + ph))
        d.ellipse((x - r, yy - r, x + r, yy + r), fill=(255, 220, 255, a))

# --------------------------------------------------------------------------
# mapa (Florida estilizada -> Leonida ficticia)
# --------------------------------------------------------------------------
FLORIDA_LL = [
    (-87.60, 31.00), (-86.40, 31.00), (-85.00, 31.00), (-84.86, 30.71), (-83.50, 30.65),
    (-82.21, 30.57), (-82.05, 30.72), (-81.45, 30.71), (-81.33, 30.10), (-81.18, 29.55),
    (-80.95, 29.10), (-80.60, 28.50), (-80.55, 28.05), (-80.35, 27.50), (-80.10, 26.90),
    (-80.03, 26.40), (-80.10, 25.85), (-80.30, 25.40), (-80.60, 25.15), (-81.05, 25.15),
    (-81.25, 25.60), (-81.70, 25.95), (-81.85, 26.35), (-82.15, 26.70), (-82.45, 27.15),
    (-82.70, 27.55), (-82.75, 28.00), (-82.80, 28.60), (-82.70, 29.00), (-83.05, 29.25),
    (-83.55, 29.80), (-84.00, 30.10), (-84.35, 29.95), (-84.90, 29.70), (-85.35, 29.70),
    (-85.40, 30.00), (-86.20, 30.40), (-87.00, 30.40), (-87.45, 30.30), (-87.60, 30.60),
]
KEYS_LL = [(-80.45, 25.05), (-80.65, 24.90), (-80.90, 24.78), (-81.15, 24.68), (-81.45, 24.62), (-81.78, 24.56)]

MAP_BOX = 1000           # lado del área de mapa en px finales
SS = 2                   # supersampling
LON0, LON1, LAT0, LAT1 = -88.0, -79.6, 24.2, 31.4

def ll_to_xy(lon, lat):
    # proyección equirectangular corregida por cos(lat)
    k = math.cos(math.radians(27.5))
    sx = MAP_BOX / ((LON1 - LON0) * k)
    sy = MAP_BOX / (LAT1 - LAT0)
    s = min(sx, sy)
    x = (lon - LON0) * k * s + (MAP_BOX - (LON1 - LON0) * k * s) / 2
    y = (LAT1 - lat) * s
    return x, y

def resample(pts, n):
    pts = np.array(pts + [pts[0]], float)
    seg = np.sqrt(((pts[1:] - pts[:-1]) ** 2).sum(1))
    cum = np.concatenate([[0], np.cumsum(seg)])
    tgt = np.linspace(0, cum[-1], n, endpoint=False)
    out = np.empty((n, 2))
    for i, s in enumerate(tgt):
        j = np.searchsorted(cum, s, side="right") - 1
        j = min(j, len(seg) - 1)
        u = (s - cum[j]) / seg[j] if seg[j] else 0
        out[i] = pts[j] + (pts[j + 1] - pts[j]) * u
    return out

FL_XY = resample([ll_to_xy(*p) for p in FLORIDA_LL], 360)
KEYS_XY = np.array([ll_to_xy(*p) for p in KEYS_LL])

def leonida_warp(p):
    """deformación propia (ficticia) para la versión 'Leonida' del mapa."""
    x, y = p[:, 0] / MAP_BOX, p[:, 1] / MAP_BOX
    nx = x + 0.025 * np.sin(y * 17) + 0.018 * np.sin(x * 23 + 1.3)
    ny = y + 0.02 * np.sin(x * 19 + 0.5) + 0.012 * np.cos(y * 29)
    # sur un poco más ancho y "mordido", panhandle más corto
    south = np.clip((y - 0.55) / 0.45, 0, 1)
    cx = 0.66
    nx = cx + (nx - cx) * (1 + 0.12 * south)
    west = np.clip((0.35 - x) / 0.35, 0, 1)
    nx = nx + 0.06 * west
    return np.stack([nx * MAP_BOX, ny * MAP_BOX], 1)

LEO_XY = leonida_warp(FL_XY)
LEO_KEYS = leonida_warp(KEYS_XY) + np.array([10, 20])
LEO_EXTRA = [(0.86, 0.90, 26), (0.93, 0.80, 16), (0.30, 0.86, 30)]  # islas extra (fx, fy, r)

def render_map(t, draw_frac, fill_a, morph, extra_a, route_frac=0.0, ship_a=0.0,
               label_florida=0.0, cross=0.0, label_leonida=0.0):
    """Devuelve una imagen RGBA MAP_BOX x MAP_BOX del mapa."""
    S = MAP_BOX * SS
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    m = ease_in_out(morph)
    pts = (FL_XY * (1 - m) + LEO_XY * m) * SS
    keys = (KEYS_XY * (1 - m) + LEO_KEYS * m) * SS
    land_col = tuple(int(lerp(a, b, m)) for a, b in zip((40, 200, 190), (255, 80, 170)))
    edge_col = tuple(int(lerp(a, b, m)) for a, b in zip((160, 255, 250), (255, 210, 240)))

    # glow
    if fill_a > 0:
        glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ImageDraw.Draw(glow).polygon([tuple(p) for p in pts], fill=land_col + (int(160 * fill_a),))
        glow = glow.filter(ImageFilter.GaussianBlur(40))
        img.alpha_composite(glow)
        d.polygon([tuple(p) for p in pts], fill=land_col + (int(235 * fill_a),))
        for kx, ky in keys:
            r = 9 * SS
            d.ellipse((kx - r, ky - r, kx + r, ky + r), fill=land_col + (int(235 * fill_a),))
    if extra_a > 0:
        for fx, fy, r in LEO_EXTRA:
            cx, cy, rr = fx * S, fy * S, r * SS * ease_back(clamp(extra_a))
            d.ellipse((cx - rr, cy - rr * 0.7, cx + rr, cy + rr * 0.7), fill=(255, 80, 170, int(235 * clamp(extra_a))))
    # contorno que se dibuja
    if draw_frac > 0:
        n = int(len(pts) * clamp(draw_frac))
        seq = [tuple(p) for p in pts[:max(2, n)]]
        if draw_frac >= 1:
            seq.append(seq[0])
        d.line(seq, fill=edge_col + (255,), width=6 * SS, joint="curve")
        if draw_frac < 1:
            hx, hy = seq[-1]
            d.ellipse((hx - 14 * SS, hy - 14 * SS, hx + 14 * SS, hy + 14 * SS), fill=WHITE + (255,))

    # ruta de Ponce de León (desde el sureste / Puerto Rico)
    if route_frac > 0:
        start = np.array([1.02 * S, 0.98 * S])
        land = np.array(ll_to_xy(-81.20, 29.55)) * SS + np.array([14 * SS, 0])
        ctrl = np.array([1.05 * S, 0.30 * S])
        N = 60
        ts = np.linspace(0, 1, N)
        curve = [(1 - u) ** 2 * start + 2 * (1 - u) * u * ctrl + u ** 2 * land for u in ts]
        k = int(N * clamp(route_frac))
        for i in range(0, k - 1, 2):
            d.line([tuple(curve[i]), tuple(curve[i + 1])], fill=YELLOW + (255,), width=7 * SS)
        if ship_a > 0 and k >= 2:
            sx, sy = curve[min(k - 1, N - 1)]
            sc = SS * 1.5
            bob = math.sin(t * 6) * 4 * SS
            sy += bob
            a = int(255 * ship_a)
            d.polygon([(sx - 30 * sc, sy), (sx + 30 * sc, sy), (sx + 20 * sc, sy + 14 * sc), (sx - 20 * sc, sy + 14 * sc)],
                      fill=(120, 60, 30, a), outline=BLACK + (a,))
            d.line([(sx, sy), (sx, sy - 50 * sc)], fill=BLACK + (a,), width=3 * SS)
            d.polygon([(sx + 2 * sc, sy - 48 * sc), (sx + 26 * sc, sy - 22 * sc), (sx + 2 * sc, sy - 6 * sc)],
                      fill=(250, 245, 230, a), outline=BLACK + (a,))
            d.polygon([(sx - 2 * sc, sy - 44 * sc), (sx - 22 * sc, sy - 16 * sc), (sx - 2 * sc, sy - 8 * sc)],
                      fill=(250, 245, 230, a), outline=BLACK + (a,))
            # cruz roja de la vela (estilo carabela)
            d.line([(sx + 8 * sc, sy - 28 * sc), (sx + 16 * sc, sy - 28 * sc)], fill=RED + (a,), width=2 * SS)
            d.line([(sx + 12 * sc, sy - 33 * sc), (sx + 12 * sc, sy - 22 * sc)], fill=RED + (a,), width=2 * SS)
        if route_frac >= 1:
            lx, ly = land
            pulse = (t * 1.5) % 1
            r = (20 + 50 * pulse) * SS
            d.ellipse((lx - r, ly - r, lx + r, ly + r), outline=YELLOW + (int(255 * (1 - pulse)),), width=4 * SS)
            d.ellipse((lx - 12 * SS, ly - 12 * SS, lx + 12 * SS, ly + 12 * SS), fill=YELLOW + (255,), outline=BLACK + (255,), width=3 * SS)

    img = img.resize((MAP_BOX, MAP_BOX), Image.LANCZOS)

    # etiquetas
    cx, cy = 330, 690
    if label_florida > 0:
        ti = text_img("FLORIDA", 110, fill=WHITE, stroke=9)
        paste_center(img, ti, cx, cy, scale=pop(label_florida, 0) if label_florida < 1 else 1.0, alpha=1.0)
        if cross > 0:
            dd = ImageDraw.Draw(img)
            x0, x1 = cx - 260, cx - 260 + 520 * ease_out(cross)
            dd.line((x0, cy + 18, x1, cy - 10), fill=RED + (255,), width=18)
    if label_leonida > 0:
        ti = text_img("LEONIDA", 120, fill=YELLOW, stroke=10, path=FONT_BLACK_IT)
        paste_center(img, ti, cx + 10, cy + 130, scale=pop(label_leonida, 0) if label_leonida < 1 else 1.0, rot=6)
    return img

# --------------------------------------------------------------------------
# subtítulos (palabra a palabra)
# --------------------------------------------------------------------------
CAPTIONS = [
    (3.0, 5.2, "GTA 6 no pasa en Florida,", {"Florida,"}),
    (5.2, 7.4, "sino en Leonida.", {"Leonida."}),
    (7.5, 9.0, "La teoría más extendida", {"teoría"}),
    (9.0, 10.4, "es que el nombre viene de", set()),
    (10.4, 11.8, "Juan Ponce de León,", {"Juan", "Ponce", "de", "León,"}),
    (11.8, 13.0, "el explorador español", {"español"}),
    (13.0, 14.5, "que llegó a Florida en 1513.", {"1513."}),
    (14.5, 16.5, "León más Florida…", {"León", "Florida…"}),
    (16.5, 19.3, "Leonida.", {"Leonida."}),
]
CAP_Y = 1420

def draw_caption(canvas, t):
    for t0, t1, txt, hl in CAPTIONS:
        if t0 <= t < t1:
            words = txt.split(" ")
            span = (t1 - t0) * 0.6
            f = font(FONT_BLACK, 74)
            sp = f.getlength(" ")
            widths = [f.getlength(w) for w in words]
            total = sum(widths) + sp * (len(words) - 1)
            x = W / 2 - total / 2
            for i, (wd, wl) in enumerate(zip(words, widths)):
                ts = t0 + span * i / max(1, len(words))
                if t >= ts:
                    s = pop(t, ts, 0.18)
                    col = YELLOW if wd in hl else WHITE
                    ti = text_img(wd, 74, fill=col, stroke=8)
                    paste_center(canvas, ti, x + wl / 2, CAP_Y, scale=s)
                x += wl + sp
            break

# --------------------------------------------------------------------------
# escenas
# --------------------------------------------------------------------------
MAP_CX, MAP_CY = W // 2, 930

def scene(canvas, t):
    # ---------- A. Gancho 0–3 s ----------
    if t < 3.1:
        shake = (math.sin(t * 60) * 6 * max(0, 1 - t / 0.5))
        l1 = text_img("EL NOMBRE DE", 92, fill=WHITE, stroke=9)
        l2 = text_img("LEONIDA", 200, fill=YELLOW, stroke=14, path=FONT_BLACK_IT)
        l3 = text_img("ESCONDE A UN", 92, fill=WHITE, stroke=9)
        l4 = text_img("EXPLORADOR", 128, fill=PINK, stroke=12)
        l5 = text_img("ESPAÑOL", 140, fill=PINK, stroke=12)
        out = 1 - prog(t, 2.75, 3.05)
        paste_center(canvas, l1, W / 2 + shake, 520, pop(t, 0.0) , out)
        paste_center(canvas, l2, W / 2 - shake, 690, pop(t, 0.25) * (1 + 0.03 * math.sin(t * 8)), out, rot=4)
        paste_center(canvas, l3, W / 2, 870, pop(t, 0.9), out)
        paste_center(canvas, l4, W / 2, 1020, pop(t, 1.25), out)
        paste_center(canvas, l5, W / 2, 1170, pop(t, 1.55), out)
        # signo de interrogación gigante de fondo
        q = text_img("?", 500, fill=(255, 255, 255), stroke=0, shadow=False)
        paste_center(canvas, q, W / 2 + 330, 360, 1.0, 0.10 * out, rot=-12 + t * 4)

    # ---------- mapa B–D (3–19.5 s) ----------
    if 3.0 <= t < 19.6:
        draw = prog(t, 3.0, 4.6)
        fill = prog(t, 4.2, 4.9)
        morph = prog(t, 16.4, 18.0)
        extra = prog(t, 17.6, 18.2)
        route = prog(t, 9.2, 12.6) if t < 14.4 else 1 - prog(t, 14.4, 14.8)
        route = route if t < 14.8 else 0
        ship = 1.0 if 9.2 <= t < 14.6 else 0
        lab_fl = prog(t, 4.7, 5.05) if t < 8.0 else (1 - prog(t, 7.6, 7.9))
        cross = prog(t, 5.4, 5.8) if t < 7.9 else 0
        lab_le = prog(t, 5.9, 6.25) if t < 7.9 else 0
        mp = render_map(t, draw, fill, morph, extra, route, ship, lab_fl if t < 7.9 else 0, cross, lab_le)
        # zoom suave + salida
        zin = ease_out(prog(t, 3.0, 3.6))
        zout = 1 - prog(t, 19.2, 19.6)
        # durante la ecuación, el mapa se reduce y baja
        shrink = ease_in_out(prog(t, 14.5, 15.1))
        sc = lerp(0.5, 0.82, zin) * lerp(1.0, 0.9, shrink) * (1 + 0.04 * math.sin(t * 1.3))
        cy = lerp(MAP_CY, 1000, shrink)
        paste_center(canvas, mp, MAP_CX, cy, sc, zout)

    # ---------- C. Ponce de León (7.5–14.5) ----------
    if 7.5 <= t < 14.6:
        out = 1 - prog(t, 14.2, 14.5)
        tag = text_img("TEORÍA", 64, fill=BLACK, stroke=0, shadow=False)
        # badge
        bw, bh = tag.width + 30, tag.height + 6
        badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(badge).rounded_rectangle((0, 0, bw - 1, bh - 1), 22, fill=YELLOW + (255,), outline=BLACK + (255,), width=5)
        badge.alpha_composite(tag, ((bw - tag.width) // 2, (bh - tag.height) // 2))
        paste_center(canvas, badge, W / 2, 250, pop(t, 7.5), out, rot=-4)
        if t >= 10.4:
            n1 = text_img("JUAN PONCE DE LEÓN", 86, fill=WHITE, stroke=10)
            paste_center(canvas, n1, W / 2, 380, pop(t, 10.4), out)
        if t >= 11.8:
            n2 = text_img("explorador español", 60, fill=TEAL, stroke=7, path=FONT_BLACK_IT)
            paste_center(canvas, n2, W / 2, 475, pop(t, 11.8), out)
        if t >= 12.6:
            yr = int(round(lerp(1492, 1513, ease_out(prog(t, 12.6, 13.4)))))
            y_img = text_img(str(yr), 210, fill=YELLOW, stroke=14)
            paste_center(canvas, y_img, W / 2 + 230, 1120, pop(t, 12.6) * (1.12 if 13.4 <= t < 13.55 else 1), out, rot=-6)
        f_src = text_img("Fuente: EssentiallySports", 34, fill=(255, 255, 255), stroke=4, path=FONT_BOLD, shadow=False)
        paste_center(canvas, f_src, W / 2, 1520, 1.0, 0.75 * out * prog(t, 7.6, 8.0))

    # ---------- D. Ecuación LEÓN + FLORIDA = LEONIDA (14.5–19.5) ----------
    if 14.5 <= t < 19.6:
        out = 1 - prog(t, 19.25, 19.55)
        y = 300
        a = text_img("LEÓN", 130, fill=YELLOW, stroke=12)
        plus = text_img("+", 120, fill=WHITE, stroke=10)
        b = text_img("FLORIDA", 130, fill=TEAL, stroke=12)
        merge = ease_in_out(prog(t, 16.3, 16.75))
        if merge < 1:
            ax = lerp(W / 2 - 330, W / 2, merge)
            bx = lerp(W / 2 + 175, W / 2, merge)
            paste_center(canvas, a, ax, y, pop(t, 14.5) * (1 - 0.5 * merge), (1 - merge) * out)
            paste_center(canvas, plus, W / 2 - 145, y, pop(t, 15.1) * (1 - merge), (1 - merge) * out)
            paste_center(canvas, b, bx, y, pop(t, 15.4) * (1 - 0.5 * merge), (1 - merge) * out)
        if t >= 16.6:
            # LEON en amarillo + IDA en cian -> resultado
            word = two_tone("LEON", "IDA", 190)
            s = pop(t, 16.6, 0.45) * (1 + 0.025 * math.sin(t * 7))
            paste_center(canvas, word, W / 2, y + 10, s, out, rot=3)
            eq = text_img("LEÓN + FLORIDA = LEONIDA", 56, fill=WHITE, stroke=6)
            paste_center(canvas, eq, W / 2, y + 170, pop(t, 17.3), out)

    # ---------- E. Rockstar nunca da puntada sin hilo (19.5–22) ----------
    if 19.4 <= t < 22.2:
        out = 1 - prog(t, 21.9, 22.15)
        l1 = text_img("ROCKSTAR", 170, fill=PINK, stroke=13, path=FONT_BLACK_IT)
        l2 = text_img("NUNCA DA", 110, fill=WHITE, stroke=10)
        l3 = text_img("PUNTADA", 150, fill=YELLOW, stroke=12)
        l4 = text_img("SIN HILO", 150, fill=YELLOW, stroke=12)
        paste_center(canvas, l1, W / 2, 560, pop(t, 19.5), out, rot=-3)
        paste_center(canvas, l2, W / 2, 740, pop(t, 19.9), out)
        paste_center(canvas, l3, W / 2, 900, pop(t, 20.3), out)
        paste_center(canvas, l4, W / 2, 1060, pop(t, 20.6), out)
        # hilo cosiendo
        p = ease_in_out(prog(t, 20.6, 21.6))
        if p > 0:
            d = ImageDraw.Draw(canvas)
            xs = np.linspace(80, W - 80, 15)
            yb = 1200
            n = int(len(xs) * p)
            for i in range(0, max(0, n - 1), 2):
                d.line((xs[i], yb, xs[i + 1], yb), fill=WHITE + (int(255 * out),), width=10)
            if n > 0:
                nx = xs[min(n, len(xs) - 1)]
                # aguja
                d.polygon([(nx - 6, yb - 50), (nx + 6, yb - 50), (nx, yb + 40)], fill=(220, 220, 235, int(255 * out)),
                          outline=BLACK + (int(255 * out),))
                d.ellipse((nx - 3, yb - 44, nx + 3, yb - 32), fill=BLACK + (int(255 * out),))

    # ---------- F. CTA (22–26) ----------
    if t >= 22.0:
        l1 = text_img("¿QUÉ OTRO NOMBRE", 96, fill=WHITE, stroke=9)
        l2 = text_img("CREES QUE", 96, fill=WHITE, stroke=9)
        l3 = text_img("ESCONDE ALGO?", 124, fill=YELLOW, stroke=12, path=FONT_BLACK_IT)
        paste_center(canvas, l1, W / 2, 470, pop(t, 22.0), 1)
        paste_center(canvas, l2, W / 2, 590, pop(t, 22.25), 1)
        paste_center(canvas, l3, W / 2, 740, pop(t, 22.5), 1, rot=-3)
        # burbuja de comentario
        if t >= 23.2:
            s = pop(t, 23.2, 0.4)
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
            paste_center(canvas, bub, W / 2, 1060, s * (1 + 0.02 * math.sin(t * 6)), 1)
        # flecha que apunta abajo (hacia comentarios)
        if t >= 23.8:
            d = ImageDraw.Draw(canvas)
            bounce = abs(math.sin((t - 23.8) * 5)) * 40
            ax, ay = W / 2, 1290 + bounce
            a = int(255 * prog(t, 23.8, 24.0))
            d.polygon([(ax - 40, ay), (ax + 40, ay), (ax + 40, ay + 70), (ax + 85, ay + 70), (ax, ay + 150),
                       (ax - 85, ay + 70), (ax - 40, ay + 70)], fill=YELLOW + (a,), outline=BLACK + (a,), width=8)

# transiciones: destellos en los cortes
CUTS = [3.0, 7.5, 14.5, 16.6, 19.5, 22.0]

def draw_flash(canvas, t):
    for c in CUTS:
        if c <= t < c + 0.18:
            a = int(200 * (1 - (t - c) / 0.18))
            canvas.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, a)))

def punch_zoom(t):
    z = 1.0
    for c in CUTS + [0.0]:
        if c <= t < c + 0.25:
            z = 1 + 0.06 * (1 - ease_out((t - c) / 0.25))
    return z

# --------------------------------------------------------------------------
# barra de progreso + vignette
# --------------------------------------------------------------------------
def make_vignette():
    y, x = np.mgrid[0:H, 0:W]
    dx, dy = (x - W / 2) / (W / 2), (y - H / 2) / (H / 2)
    r = np.sqrt(dx ** 2 * 1.0 + dy ** 2 * 0.8)
    a = np.clip((r - 0.7) / 0.6, 0, 1) * 170
    v = np.zeros((H, W, 4), np.uint8)
    v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")

# --------------------------------------------------------------------------
# audio: base musical sintetizada + whooshes (sin copyright)
# --------------------------------------------------------------------------
SR = 44100

def synth_audio(path):
    n = int(DUR * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    bpm = 112
    beat = 60 / bpm
    rng = np.random.default_rng(1)
    # bajo (Am - F - C - G)
    roots = [55.0, 43.65, 65.41, 49.0]
    for i in range(int(DUR / beat) + 1):
        st = i * beat
        bar = int(i // 4) % 4
        f = roots[bar]
        s0, s1 = int(st * SR), int(min(DUR, st + beat * 0.9) * SR)
        tt = t[s0:s1] - st
        env = np.exp(-tt * 3)
        out[s0:s1] += 0.22 * np.sign(np.sin(2 * np.pi * f * tt)) * env * 0.5 + 0.18 * np.sin(2 * np.pi * f * tt) * env
        # kick
        k1 = int(min(DUR, st + 0.25) * SR)
        kt = t[s0:k1] - st
        out[s0:k1] += 0.55 * np.sin(2 * np.pi * (50 + 120 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 12)
        # hats en contratiempo
        hs = st + beat / 2
        h0, h1 = int(hs * SR), int(min(DUR, hs + 0.05) * SR)
        if h1 > h0:
            ht = t[h0:h1] - hs
            out[h0:h1] += 0.08 * rng.standard_normal(h1 - h0) * np.exp(-ht * 80)
        # clap en 2 y 4
        if i % 2 == 1:
            c1 = int(min(DUR, st + 0.15) * SR)
            ct = t[s0:c1] - st
            out[s0:c1] += 0.15 * rng.standard_normal(c1 - s0) * np.exp(-ct * 25)
    # pad sintetizado
    chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    for b in range(int(DUR / (beat * 4)) + 1):
        st = b * beat * 4
        s0, s1 = int(st * SR), int(min(DUR, st + beat * 4) * SR)
        tt = t[s0:s1] - st
        env = np.minimum(1, tt / 0.3) * np.minimum(1, (beat * 4 - tt) / 0.3)
        for f in chords[b % 4]:
            out[s0:s1] += 0.035 * (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.005 * tt)) * env
    # whoosh en cortes
    for c in CUTS:
        s0, s1 = int(max(0, c - 0.35) * SR), int(min(DUR, c + 0.15) * SR)
        nz = rng.standard_normal(s1 - s0)
        env = np.sin(np.linspace(0, np.pi, s1 - s0)) ** 2
        # filtro paso-bajo móvil simple
        y = np.zeros_like(nz); acc = 0
        for j in range(len(nz)):
            a = 0.02 + 0.3 * j / len(nz)
            acc += a * (nz[j] - acc); y[j] = acc
        out[s0:s1] += 0.5 * y * env
    # "ding" al formar LEONIDA y al 1513
    for c, f in [(16.6, 1318.5), (13.4, 987.8)]:
        s0, s1 = int(c * SR), int(min(DUR, c + 1.2) * SR)
        tt = t[s0:s1] - c
        out[s0:s1] += 0.18 * (np.sin(2 * np.pi * f * tt) + 0.4 * np.sin(2 * np.pi * f * 2 * tt)) * np.exp(-tt * 4)
    # fade final
    fo = int(1.2 * SR)
    out[-fo:] *= np.linspace(1, 0, fo)
    out = out / np.max(np.abs(out)) * 0.6   # deja margen para la voz
    data = (out * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())

# --------------------------------------------------------------------------
def main():
    bg = make_gradient()
    vig = make_vignette()
    silent = os.path.join(HERE, "short1_leonida_sin_musica.mp4")
    music = os.path.join(HERE, "musica.wav")
    final = os.path.join(HERE, "short1_leonida.mp4")
    only = os.environ.get("FRAMES")  # p.ej. FRAMES=90,300 para previsualizar
    if only:
        for fi in map(int, only.split(",")):
            render_frame(fi / FPS, bg, vig).convert("RGB").save(os.path.join(HERE, f"preview_{fi:04d}.png"))
        return
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                           "-movflags", "+faststart", silent], stdin=subprocess.PIPE)
    for fi in range(NFRAMES):
        fr = render_frame(fi / FPS, bg, vig)
        ff.stdin.write(fr.convert("RGB").tobytes())
        if fi % 60 == 0:
            print(f"frame {fi}/{NFRAMES}", flush=True)
    ff.stdin.close(); ff.wait()
    synth_audio(music)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", music,
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", final], check=True)
    print("OK ->", final)

def render_frame(t, bg, vig):
    c = bg.copy()
    draw_particles(c, t)
    draw_grid(c, t)
    scene(c, t)
    draw_caption(c, t)
    c.alpha_composite(vig)
    # barra de progreso arriba
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, int(W * t / DUR), 10), fill=YELLOW + (255,))
    z = punch_zoom(t)
    if z != 1.0:
        cw, ch = int(W / z), int(H / z)
        c = c.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
    draw_flash(c, t)
    return c

if __name__ == "__main__":
    main()
