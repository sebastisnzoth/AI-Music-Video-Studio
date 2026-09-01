# AI Music Video Studio

Aplicación web local y gratuita para transformar una canción + foto/video en un videoclip, con arquitectura preparada para storyboard, análisis musical, ComfyUI, lip-sync y render final.

## Objetivo

```text
canción + foto/video + letra opcional
→ análisis musical local
→ transcripción / timestamps
→ storyboard sincronizado al beat
→ escenas
→ generación IA local (ComfyUI)
→ lip-sync
→ montaje al ritmo
→ MP4 final
```

## Estado actual

El proyecto ya permite:

- Crear proyectos desde el navegador.
- Subir canción (MP3/WAV/M4A/etc.).
- Subir una foto o video de referencia.
- Pegar letra opcional.
- Elegir 16:9 o 9:16 y calidad Preview / Final / Master.
- Analizar duración del audio con ffprobe.
- Analizar BPM, beats, energía y cambios aproximados de sección con librosa cuando está instalado.
- Crear storyboard sincronizado con beats/energía, con fallback temporal.
- Preparar fragmentos WAV exactos por escena para generación y lip-sync.
- Aprobar escenas individualmente.
- Renderizar un MP4 local con FFmpeg usando la foto/video y el audio original.
- Guardar cada proyecto y consultar su progreso.
- Detectar un servidor ComfyUI local.
- Cargar workflows ComfyUI con variables para prompt, duración y referencia.
- Transcribir localmente con faster-whisper cuando está instalado, incluyendo timestamps por palabra.
- Inferir una estructura inicial intro / verso / estribillo / puente / outro sin usar un LLM pago.

No requiere ninguna API paga para funcionar en modo local.

## Requisitos

- Python 3.10+
- FFmpeg + ffprobe
- Opcional: ComfyUI ejecutándose en `http://127.0.0.1:8188`

### macOS

```bash
brew install ffmpeg
```

## Instalación básica

```bash
git clone https://github.com/sebastisnzoth/AI-Music-Video-Studio.git
cd AI-Music-Video-Studio

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python -m app.main
```

Abrir:

```text
http://127.0.0.1:8080
```

## Activar análisis IA local

Para BPM/energía + Whisper local:

```bash
source .venv/bin/activate
pip install -r requirements-ai.txt
```

`faster-whisper` se ejecuta con CPU/int8 por defecto para mantener compatibilidad con equipos sin CUDA. En una GPU compatible podrá añadirse después un perfil acelerado.

## Próximas etapas

1. Conectar la transcripción local al flujo automático del proyecto.
2. Mejorar detección de verso/estribillo/puente combinando Whisper + repetición de letra + energía.
3. Director musical inspirado en Maestro.
4. ComfyUI para imágenes y clips generativos.
5. Identidad consistente a partir de foto/video.
6. Lip-sync local por fragmento exacto de audio.
7. Regeneración y control de calidad por escena.
8. Upscale y export 1080p/4K.
9. Reels/Shorts automáticos.

## Repos evaluados

- VocaVid: referencia principal para storyboard, ComfyUI, generación por escena y flujo resumible.
- Maestro: referencia para Director musical, BPM, secciones y energía.
- MusicVision: referencia para lip-sync, continuidad y export profesional; requiere GPU NVIDIA potente en su implementación actual.
- MiniMax CLI (`sebastisnzoth/cli`): útil solo como integración opcional. Requiere Token Plan/API key, por lo que no forma parte del camino 100% gratuito.

## Filosofía

Software gratis y open source. Los modos principales no deben depender de Sora, Veo, Kling, Runway, MuAPI, MiniMax API u otras APIs pagas.
