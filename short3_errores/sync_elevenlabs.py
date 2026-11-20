"""
Extrae de la locución de ElevenLabs solo las frases de narración (🎙️) y las
monta en la línea de tiempo del Short 2.

Entrada: voz/elevenlabs_raw.mp3 + voz/elevenlabs_raw_words.json (faster-whisper,
         tiempos por palabra).
Salida:  voz/voz.wav + voz/timeline.json (los lee render.py).
"""
import difflib, json, os, subprocess, unicodedata, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(HERE, "voz")
SR = 44100
GAP, LEAD, TAIL = 0.35, 0.15, 1.6

PHRASES = [
    ("hook", "Seis curiosidades de GTA seis que seguro no sabías. La última es una locura."),
    ("c1", "Leonida viene de León más Florida, por el explorador español Ponce de León."),
    ("c2", "Los Everglades del juego se llaman Grass Rivers. Y sí, hay caimanes."),
    ("c3", "Por primera vez puedes ponerte auriculares y escuchar podcasts andando."),
    ("c4", "El primer tráiler se estrenó antes de tiempo por culpa de una filtración."),
    ("c5", "En Xbox es el juego más reservado de la historia de la Microsoft Store."),
    ("c6", "Se retrasó dos veces... y hoy tiene un 99 sobre 100 en Metacritic."),
    ("cta", "¿Cuál no sabías? Te leo en comentarios."),
]

def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.strip(",.…¿?¡!:; ")
    return {"vi": "seis", "6": "seis"}.get(s, s)

def load_words():
    ws = json.load(open(os.path.join(V, "elevenlabs_raw_words.json")))
    out, i = [], 0
    while i < len(ws):   # «noventa y nueve» -> 99, «cien» -> 100
        if i + 2 < len(ws) and [norm(w["w"]) for w in ws[i:i + 3]] == ["noventa", "y", "nueve"]:
            out.append({"w": "99", "s": ws[i]["s"], "e": ws[i + 2]["e"]}); i += 3; continue
        w = dict(ws[i])
        if norm(w["w"]) == "cien":
            w["w"] = "100"
        out.append(w); i += 1
    return out

def find_phrase(words, toks, start_from):
    """Busca la secuencia de la frase (comparación difusa) a partir de start_from."""
    nt = [norm(t) for t in toks]
    best = None
    for i in range(start_from, len(words)):
        if norm(words[i]["w"]) != nt[0]:
            continue
        cand = [norm(w["w"]) for w in words[i:i + len(nt) + 3]]
        sm = difflib.SequenceMatcher(None, nt, cand)
        r = sm.ratio()
        if r > 0.75:
            best = (i, sm); break
    if not best:
        raise SystemExit(f"No encuentro la frase: {' '.join(toks)}")
    i, sm = best
    times = [None] * len(nt)
    last_j = 0
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            w = words[i + b + k]
            times[a + k] = (w["s"], w["e"]); last_j = max(last_j, b + k)
    # interpola huecos
    for k in range(len(times)):
        if times[k] is None:
            prev = next((times[j] for j in range(k - 1, -1, -1) if times[j]), None)
            nxt = next((times[j] for j in range(k + 1, len(times)) if times[j]), None)
            s = prev[1] if prev else nxt[0] - 0.2
            e = nxt[0] if nxt else s + 0.25
            times[k] = (s, max(s + 0.05, e))
    return times, i + last_j + 1

def decode(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def quiet_point(a, t, lo, hi):
    """instante de menor energía entre lo y hi (para cortar sin comerse sílabas)."""
    i0, i1 = int(max(0, lo) * SR), int(min(len(a) / SR, hi) * SR)
    if i1 - i0 < 400:
        return t
    win = 441
    e = np.convolve(np.abs(a[i0:i1]), np.ones(win) / win, "same")
    return (i0 + int(np.argmin(e))) / SR

def main():
    words = load_words()
    a = decode(os.path.join(V, "elevenlabs_raw.mp3"))
    pos, cur, chunks, tl = 0, 0.0, [], []
    for pid, text in PHRASES:
        toks = text.split(" ")
        times, pos = find_phrase(words, toks, pos)
        # límites de corte: buscar silencio cerca del inicio/fin
        s0 = quiet_point(a, times[0][0], times[0][0] - 0.35, times[0][0] + 0.03)
        e0 = quiet_point(a, times[-1][1], times[-1][1] - 0.02, times[-1][1] + 0.35)
        seg = a[int(s0 * SR):int(e0 * SR)].copy()
        f = int(0.01 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        start = cur + (LEAD if pid == "hook" else GAP)
        off = start - s0
        tl.append({"id": pid, "text": text, "start": start, "end": start + len(seg) / SR,
                   "words": [{"w": tok.strip(",.…¿?¡!"), "s": ts + off, "e": te + off} for tok, (ts, te) in zip(toks, times)]})
        chunks.append((start, seg))
        cur = start + len(seg) / SR
        print(f"{pid:5s} fuente {s0:7.2f}-{e0:7.2f}  ->  {start:6.2f}-{cur:6.2f}")
    dur = round(cur + TAIL, 2)
    out = np.zeros(int(dur * SR), np.float32)
    for st, seg in chunks:
        i = int(st * SR); out[i:i + len(seg)] += seg
    out = out / max(1e-6, np.abs(out).max()) * 0.95
    with wave.open(os.path.join(V, "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    json.dump({"voice": "ElevenLabs Roger", "duration": dur, "phrases": tl},
              open(os.path.join(V, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print("duración", dur)

if __name__ == "__main__":
    main()
