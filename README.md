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
→ generación IA local (ComfyUI / LocalAI)
→ image-to-video
→ identidad / face refinement
→ lip-sync local
→ upscale
→ revisión por versiones
→ montaje con audio original
→ MP4 final
```

## Estado actual

El proyecto ya permite:

- Crear proyectos desde el navegador.
- Subir canción y foto/video de referencia.
- Pegar letra opcional.
- Elegir 16:9 o 9:16 y calidad Preview / Final / Master.
- Analizar BPM, beats, energía y cambios aproximados de sección con librosa.
- Crear storyboard sincronizado con beats y energía.
- Director local para estrategia, cámara, iluminación, paleta y lip-sync.
- Preparar WAV exactos y `package.json` por escena.
- Perfil de identidad reutilizable por proyecto.
- Catálogo de motores locales.
- Generación de imagen mediante ComfyUI.
- Image-to-video mediante workflow ComfyUI configurable.
- Backend alternativo LocalAI configurable.
- Deep-Live-Cam opcional para refinamiento facial.
- Wav2Lip y Real-ESRGAN como adapters locales opcionales.
- Versiones, comentarios y aprobación por escena.
- Subtítulos SRT y burn-in con FFmpeg.
- Ensamblado final conservando la canción original como audio master.
- Importar automáticamente el clip generado desde la carpeta `output` de ComfyUI.

No requiere ninguna API paga para funcionar en modo local.

## Requisitos

- Python 3.10+
- FFmpeg + ffprobe
- Opcional para IA: ComfyUI en `http://127.0.0.1:8188`

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
bash run.sh
```

Abrir:

```text
http://127.0.0.1:8080
```

## Análisis IA local

```bash
source .venv/bin/activate
pip install -r requirements-ai.txt
```

`faster-whisper` usa CPU/int8 por defecto.

## Generación de imágenes con ComfyUI

Workflow base:

```text
workflows/scene-image-api.json
```

Variables:

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

## Image-to-video con ComfyUI

Exportá desde ComfyUI un workflow en formato **API JSON** que produzca video y configurá:

```bash
export COMFYUI_VIDEO_WORKFLOW="/ruta/scene-video-api.json"
```

El workflow puede ser LTX, Wan u otro motor instalado localmente, siempre que use las variables que necesite de esta lista:

```text
{{prompt}}
{{negative_prompt}}
{{reference_path}}
{{audio_path}}
{{duration}}
{{fps}}
{{frame_count}}
{{seed}}
{{scene_id}}
```

### Carpeta output de ComfyUI

Si ComfyUI está en `~/ComfyUI`, la app detecta automáticamente:

```text
~/ComfyUI/output
```

Si está en otro lugar, definí una de estas variables:

```bash
export COMFYUI_DIR="/ruta/a/ComfyUI"
```

o directamente:

```bash
export COMFYUI_OUTPUT_DIR="/ruta/a/ComfyUI/output"
```

Cuando `/history` informa que el video terminó, la app:

1. resuelve `filename + subfolder` dentro de `output`;
2. copia el archivo a `projects/<id>/scenes/<scene>/clip-generated.*`;
3. registra automáticamente `generated_clip`;
4. cambia la escena a `clip_ready`.

A partir de ahí puede continuar automáticamente por:

```text
generated_clip
→ Deep-Live-Cam opcional
→ Wav2Lip si necesita canto
→ Real-ESRGAN
→ revisión/aprobación
→ master
```

## Backends opcionales

- ComfyUI: imagen + image-to-video.
- LocalAI: backend multimodal/video alternativo.
- Deep-Live-Cam: refinamiento/consistencia facial.
- Wav2Lip/MuseTalk: lip-sync.
- Real-ESRGAN: upscale.
- HyperFrames: overlays, captions y motion graphics deterministas.
- SRS: preview/live streaming opcional.
- Duix Avatar: digital human opcional para hardware NVIDIA potente.

## Filosofía

Software gratis y open source. El modo principal no debe depender de Sora, Veo, Kling, Runway, MuAPI, MiniMax API, Higgsfield u otras APIs pagas.
