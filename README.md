# AI Music Video Studio

Aplicación web local y gratuita para transformar una canción + foto/video en un videoclip, con arquitectura preparada para storyboard, análisis musical, ComfyUI, lip-sync y render final.

## Objetivo

```text
canción + foto/video + letra opcional
→ análisis
→ storyboard
→ escenas
→ generación IA local (ComfyUI)
→ lip-sync
→ montaje al ritmo
→ MP4 final
```

## Estado actual

El MVP incluido en este repositorio ya permite:

- Crear proyectos desde el navegador.
- Subir canción (MP3/WAV/M4A/etc.).
- Subir una foto o video de referencia.
- Pegar letra opcional.
- Elegir 16:9 o 9:16 y calidad Preview / Final / Master.
- Analizar duración del audio con ffprobe.
- Crear un storyboard inicial basado en la letra o en segmentos temporales.
- Renderizar un MP4 local con FFmpeg usando la foto/video y el audio original.
- Guardar cada proyecto y consultar su progreso.
- Detectar un servidor ComfyUI local para la siguiente etapa de generación IA.

No requiere ninguna API paga para funcionar en modo local.

## Requisitos

- Python 3.10+
- FFmpeg + ffprobe
- Opcional: ComfyUI ejecutándose en `http://127.0.0.1:8188`

### macOS

```bash
brew install ffmpeg
```

## Instalación

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

## Próximas etapas

1. faster-whisper para timestamps de letra.
2. librosa para BPM, beats y energía.
3. Director musical inspirado en Maestro.
4. ComfyUI para imágenes y clips.
5. identidad consistente a partir de foto/video.
6. lip-sync local.
7. aprobación/regeneración por escena.
8. upscale y export 1080p/4K.
9. Reels/Shorts automáticos.

## Filosofía

Software gratis y open source. Los modos principales no deben depender de Sora, Veo, Kling, Runway, MuAPI u otras APIs pagas.
