"""
Genera la locución IA (edge-tts) frase a frase y guarda:
  voz/voz.wav        -> narración completa colocada en su línea de tiempo
  voz/timeline.json  -> inicio/fin de cada frase y de cada palabra (segundos)

Uso:  python3 gen_voz.py [VOZ]      (por defecto es-ES-AlvaroNeural)
"""
import asyncio, json, os, subprocess, sys
import numpy as np
import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "voz")
VOICE = sys.argv[1] if len(sys.argv) > 1 else "es-ES-AlvaroNeural"
RATE, PITCH = "+12%", "-2Hz"
SR = 44100

# (id, texto que se lee, pausa antes)
PHRASES = [
    ("hook", "Seis curiosidades de GTA seis que seguro no sabías. La última es una locura.", 0.15),
    ("c1", "Leonida viene de León más Florida, por el explorador español Ponce de León.", 0.35),
    ("c2", "Los Everglades del juego se llaman Grass Rivers. Y sí, hay caimanes.", 0.35),
    ("c3", "Por primera vez puedes ponerte auriculares y escuchar podcasts andando.", 0.35),
    ("c4", "El primer tráiler se estrenó antes de tiempo por culpa de una filtración.", 0.35),
    ("c5", "En Xbox es el juego más reservado de la historia de la Microsoft Store.", 0.35),
    ("c6", "Se retrasó dos veces... y hoy tiene un 99 sobre 100 en Metacritic.", 0.35),
    ("cta", "¿Cuál no sabías? Te leo en comentarios.", 0.45),
]

async def tts(text, path):
    kw = {"proxy": os.environ.get("HTTPS_PROXY")} if os.environ.get("HTTPS_PROXY") else {}
    c = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, boundary="WordBoundary", **kw)
    audio, words = b"", []
    async for ch in c.stream():
        if ch["type"] == "audio":
            audio += ch["data"]
        elif ch["type"] == "WordBoundary":
            words.append({"w": ch["text"], "s": ch["offset"] / 1e7, "e": (ch["offset"] + ch["duration"]) / 1e7})
    open(path, "wb").write(audio)
    return words

def decode(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768

def main():
    os.environ.setdefault("SSL_CERT_FILE", "/root/.ccr/ca-bundle.crt")
    os.makedirs(OUT, exist_ok=True)
    cur, chunks, tl = 0.0, [], []
    for pid, text, gap in PHRASES:
        mp3 = os.path.join(OUT, f"{pid}.mp3")
        words = asyncio.run(tts(text, mp3))
        a = decode(mp3)
        # recorta silencio final
        nz = np.nonzero(np.abs(a) > 0.01)[0]
        a = a[: nz[-1] + int(0.08 * SR)] if len(nz) else a
        start = cur + gap
        chunks.append((start, a))
        dur = len(a) / SR
        tl.append({"id": pid, "text": text, "start": start, "end": start + dur,
                   "words": [{"w": w["w"], "s": start + w["s"], "e": start + w["e"]} for w in words]})
        cur = start + dur
        print(f"{pid}: {start:6.2f} -> {start + dur:6.2f}  {text}")
    total = cur + 1.6
    out = np.zeros(int(total * SR), np.float32)
    for st, a in chunks:
        i = int(st * SR)
        out[i:i + len(a)] += a
    out = out / max(1e-6, np.abs(out).max()) * 0.95
    import wave
    with wave.open(os.path.join(OUT, "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    json.dump({"voice": VOICE, "duration": total, "phrases": tl},
              open(os.path.join(OUT, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    print(f"total {total:.2f}s")

if __name__ == "__main__":
    main()
