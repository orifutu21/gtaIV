"""
Monta la locución de ElevenLabs sobre la línea de tiempo del Short.

Entrada: voz/elevenlabs.mp3 + voz/elevenlabs_words.json (transcripción con
         tiempos por palabra, hecha con faster-whisper).
Salida:  voz/voz.wav y voz/timeline.json (los lee render.py).

La locución no incluye el gancho ni el CTA: esas partes van solo con texto
animado y música. Se añade una pausa antes de «Rockstar…» para que la
transformación del mapa en Leonida tenga tiempo.
"""
import json, os, subprocess, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(HERE, "voz")
SR = 44100
LEAD = 3.0            # la voz entra tras el gancho de 3 s
SPLIT, EXTRA = 14.8, 0.9   # pausa extra antes de «Rockstar»
CTA_LEN = 4.2

TEXTS = {
    "b": "GTA seis no pasa en Florida, sino en Leonida.",
    "c": "La teoría más extendida es que el nombre viene de Juan Ponce de León, "
         "el explorador español que llegó a Florida en 1513.",
    "d": "León, más Florida... Leonida.",
    "e": "Rockstar nunca da puntada sin hilo.",
}
COUNTS = {"b": 9, "c": 23, "d": 4, "e": 6}

def shift(t):
    return t + LEAD + (EXTRA if t >= SPLIT else 0.0)

def main():
    words = json.load(open(os.path.join(V, "elevenlabs_words.json")))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", os.path.join(V, "elevenlabs.mp3"),
                          "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    phrases, i = [], 0
    for pid in ("b", "c", "d", "e"):
        ws = words[i:i + COUNTS[pid]]; i += COUNTS[pid]
        ws = [{"w": w["w"].strip(",.…¿?¡! "), "s": shift(w["s"]), "e": shift(w["e"])} for w in ws]
        phrases.append({"id": pid, "text": TEXTS[pid], "start": ws[0]["s"] - 0.05, "end": ws[-1]["e"], "words": ws})
    # gancho y CTA sin voz: tiempos de diseño
    hook = {"id": "hook", "text": "", "start": 0.0, "end": 2.9,
            "words": [{"w": w, "s": s + 0.12, "e": s + 0.4} for w, s in
                      [("El", 0.0), ("Leonida", 0.25), ("esconde", 0.9), ("explorador", 1.25), ("español", 1.55)]]}
    f_start = phrases[-1]["end"] + 0.6
    cta = {"id": "f", "text": "", "start": f_start, "end": f_start + CTA_LEN - 0.6, "words": []}
    dur = round(f_start + CTA_LEN, 2)
    # audio
    out = np.zeros(int(dur * SR), np.float32)
    cut = int(SPLIT * SR)
    p1, p2 = a[:cut], a[cut:]
    o1, o2 = int(LEAD * SR), int((LEAD + SPLIT + EXTRA) * SR)
    out[o1:o1 + len(p1)] += p1[: len(out) - o1]
    out[o2:o2 + len(p2)] += p2[: max(0, len(out) - o2)]
    out = out / max(1e-6, np.abs(out).max()) * 0.95
    with wave.open(os.path.join(V, "voz.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    json.dump({"voice": "ElevenLabs Roger", "duration": dur, "phrases": [hook] + phrases + [cta]},
              open(os.path.join(V, "timeline.json"), "w"), ensure_ascii=False, indent=1)
    for p in [hook] + phrases + [cta]:
        print(f'{p["id"]:5s} {p["start"]:6.2f} -> {p["end"]:6.2f}')
    print("duración", dur)

if __name__ == "__main__":
    main()
