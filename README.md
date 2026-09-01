# AI Music Video Studio

Aplicación web local y gratuita para transformar una canción + foto/video en un videoclip con análisis musical, storyboard, generación por escenas, lip-sync y master final.

## Objetivo

```text
canción + foto/video + letra opcional
→ análisis musical local
→ transcripción / timestamps
→ storyboard sincronizado al beat
→ Director visual
→ escenas independientes
→ generación IA local (ComfyUI)
→ lip-sync local
→ upscale
→ montaje con audio original
→ MP4 final
```

## Estado actual

El proyecto ya permite:

- Crear proyectos desde el navegador.
- Subir canción (MP3/WAV/M4A/etc.).
- Subir una foto o video de referencia.
- Pegar letra opcional.
- Elegir 16:9 o 9:16 y calidad Preview / Final / Master.
- Analizar duración con ffprobe.
- Analizar BPM, beats, energía y cambios aproximados de sección con librosa.
- Crear storyboard sincronizado con beats y energía.
- Aplicar un Director local que decide estrategia, cámara, iluminación, paleta y si una escena necesita lip-sync.
- Preparar fragmentos WAV exactos por escena.
- Crear `package.json` por escena con prompt, negative prompt, referencia, audio y toolchain.
- Catálogo local de motores: ComfyUI, Wav2Lip, MuseTalk, Real-ESRGAN y FFmpeg.
- Aprobar escenas individualmente.
- Renderizar un MP4 base con FFmpeg usando el audio original.
- Guardar proyectos y estados.
- Detectar un servidor ComfyUI local.
- Enviar un workflow API real a ComfyUI por escena y guardar su `prompt_id`.
- Consultar el historial de ComfyUI y registrar los archivos generados.
- Transcribir localmente con faster-whisper cuando está instalado.

No requiere ninguna API paga para funcionar en modo local.

## Requisitos

- Python 3.10+
- FFmpeg + ffprobe
- Opcional para IA: ComfyUI ejecutándose en `http://127.0.0.1:8188`

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

```bash
source .venv/bin/activate
pip install -r requirements-ai.txt
```

`faster-whisper` usa CPU/int8 por defecto para conservar compatibilidad con equipos sin CUDA.

## Primera generación real con ComfyUI

1. Iniciar ComfyUI y comprobar que abre normalmente en `http://127.0.0.1:8188`.
2. Tener al menos un checkpoint compatible visible en `CheckpointLoaderSimple`.
3. Iniciar AI Music Video Studio.
4. Crear un proyecto con canción + foto/video.
5. En la web, escribir el nombre exacto del checkpoint, por ejemplo `modelo.safetensors`.
6. En una tarjeta del storyboard pulsar **Preparar**.
7. Pulsar **Generar IA**.
8. Pulsar **Estado** para consultar el resultado.

El workflow base está en:

```text
workflows/scene-image-api.json
```

Usa únicamente nodos estándar de ComfyUI:

```text
CheckpointLoaderSimple
→ CLIPTextEncode positivo/negativo
→ EmptyLatentImage
→ KSampler
→ VAEDecode
→ SaveImage
```

Variables sustituidas automáticamente:

```text
{{checkpoint}}
{{prompt}}
{{negative_prompt}}
{{width}}
{{height}}
{{seed}}
{{steps}}
{{cfg}}
{{scene_id}}
```

La generación base usa una resolución intermedia y deja el upscale para una etapa posterior. Esto reduce memoria y tiempo sin limitar el master final.

## API principal

```text
GET  /api/health
GET  /api/models
POST /api/projects
POST /api/projects/{id}/scenes/{scene}/prepare
POST /api/projects/{id}/scenes/{scene}/generate-image
GET  /api/projects/{id}/scenes/{scene}/generation-status
POST /api/projects/{id}/prepare-all
```

## Próximas etapas

1. Conectar faster-whisper automáticamente al alta del proyecto.
2. Mejorar detección verso/estribillo/puente.
3. Añadir workflow de referencia/identidad para mantener el rostro del artista.
4. Añadir image-to-video local mediante workflow ComfyUI.
5. Wav2Lip/MuseTalk sobre escenas `needs_lipsync`.
6. Control automático de calidad e identidad por escena.
7. Real-ESRGAN/otro upscale local y master 1080p/4K.
8. Montaje final de clips aprobados con el audio original.
9. Reels/Shorts automáticos.

## Repos evaluados

- VocaVid: referencia principal para storyboard, ComfyUI, generación por escena y flujo resumible.
- Maestro: referencia para Director musical, BPM, secciones y energía.
- MusicVision: referencia para lip-sync, continuidad y export profesional; su implementación actual requiere GPU NVIDIA potente.
- `higgsfield-seedance2-jineng`: útil como referencia de dirección, cámara, energía y prompting; Higgsfield/Seedance no es dependencia del modo gratuito.
- `open-higgsfield`: útil como referencia de catálogo de motores, estados e inputs por rol; su generación real usa platform key externa y no forma parte del motor gratuito.
- MiniMax CLI (`sebastisnzoth/cli`): opcional únicamente; requiere Token Plan/API key.

## Filosofía

Software gratis y open source. El modo principal no debe depender de Sora, Veo, Kling, Runway, MuAPI, MiniMax API, Higgsfield u otras APIs pagas.
