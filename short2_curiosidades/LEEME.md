# SHORT 2 — 6 cosas que no sabías de GTA 6 (43 s, 1080x1920)

- `short2_curiosidades.mp4` → versión final (voz ElevenLabs «Roger» + música), lista para subir.
- `short2_curiosidades_solo_voz.mp4` / `_sin_musica.mp4` → variantes.
- Cambiar textos de la voz: editar `PHRASES` en `gen_voz.py` y ejecutar `python3 gen_voz.py && python3 render.py`.
- Las animaciones se sincronizan solas con los tiempos de cada palabra (`voz/timeline.json`).

Fuentes en pantalla: EssentiallySports, GTABoom, PlayStation Blog, Windows Central, Xbox Wire, Yahoo Tech.

Voz: `sync_elevenlabs.py` recorta del audio completo de ElevenLabs (`voz/elevenlabs_raw.mp3`) solo las frases de narración, usando la transcripción con tiempos por palabra (`voz/elevenlabs_raw_words.json`), y genera `voz/voz.wav` + `voz/timeline.json`. La voz anterior (Álvaro, edge-tts) queda en `voz/voz_alvaro.wav` / `voz/timeline_alvaro.json`.
