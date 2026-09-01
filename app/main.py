from __future__ import annotations

import json
from pathlib import Path

import requests
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .pipeline import (
    PROJECTS,
    copy_upload,
    create_project_files,
    duration,
    load_project,
    make_storyboard,
    render_reference,
    safe_suffix,
    save_json,
)

app = FastAPI(title="AI Music Video Studio", version="0.1.0")

PAGE = r'''<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Music Video Studio</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#090b12;color:#f5f7fb;font-family:Inter,system-ui,-apple-system,sans-serif}.shell{max-width:1180px;margin:auto;padding:38px 20px 80px}.hero{padding:30px 0 24px}.eyebrow{color:#9ca3c7;font-weight:700;letter-spacing:.16em;text-transform:uppercase;font-size:12px}.hero h1{font-size:clamp(38px,6vw,72px);line-height:.98;letter-spacing:-.055em;margin:10px 0 16px}.hero p{max-width:760px;color:#aeb4c7;font-size:18px;line-height:1.6}.badge{display:inline-flex;border:1px solid #343952;border-radius:999px;padding:7px 11px;color:#c9cceb;background:#111522;margin-right:7px}.layout{display:grid;grid-template-columns:1.05fr .95fr;gap:22px}.card{background:linear-gradient(180deg,#121621,#0e111a);border:1px solid #242a3b;border-radius:22px;padding:22px;box-shadow:0 24px 70px rgba(0,0,0,.25)}h2{margin:0 0 18px;font-size:22px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.full{grid-column:1/-1}label{display:block;font-size:13px;font-weight:800;color:#d9dceb;margin-bottom:7px}input,select,textarea{width:100%;border:1px solid #343b50;border-radius:13px;background:#0b0e16;color:#fff;padding:13px 14px;font:inherit}textarea{min-height:128px;resize:vertical}button{appearance:none;border:0;border-radius:14px;background:linear-gradient(135deg,#7457ff,#db4fc6);color:#fff;font-weight:900;padding:15px 18px;font-size:15px;cursor:pointer}.muted{color:#858ca5;font-size:13px;line-height:1.5}.status{margin-top:15px;border-radius:14px;padding:14px;background:#0a0d15;border:1px solid #252b3c;min-height:54px;color:#cbd0e3;white-space:pre-wrap}.stages{display:grid;gap:10px}.stage{display:flex;gap:12px;align-items:center;padding:13px;border:1px solid #252c3c;border-radius:14px}.dot{width:10px;height:10px;border-radius:50%;background:#4b536d}.stage strong{display:block}.stage span{display:block;color:#858da6;font-size:12px;margin-top:3px}.active .dot{background:#b36cff;box-shadow:0 0 18px #b36cff}.preview{margin-top:16px}.preview video{width:100%;border-radius:15px;border:1px solid #293047;background:#000}.storyboard{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:14px}.scene{padding:12px;border:1px solid #282e40;border-radius:13px;background:#0b0e16}.scene b{font-size:12px;color:#b9bee0}.scene p{font-size:12px;color:#8990a7;margin:7px 0 0;line-height:1.4}@media(max-width:850px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
</head>
<body><main class="shell">
<section class="hero"><div class="eyebrow">100% local · sin APIs pagas obligatorias</div><h1>AI Music Video Studio</h1><p>Subí tu canción y una foto o video. La app crea un proyecto, prepara storyboard y renderiza un primer videoclip local. La arquitectura ya queda preparada para ComfyUI, lip-sync y generación por escenas.</p><div><span class="badge">1080p</span><span class="badge">16:9 / 9:16</span><span class="badge" id="comfy">ComfyUI: comprobando…</span></div></section>
<div class="layout"><section class="card"><h2>Nuevo videoclip</h2><form id="form" class="grid">
<div><label>Canción</label><input type="file" name="song" accept="audio/*" required></div>
<div><label>Foto o video</label><input type="file" name="visual" accept="image/*,video/*" required></div>
<div><label>Título</label><input name="title" placeholder="Mi videoclip"></div>
<div><label>Estilo</label><select name="style"><option value="cinematic rock">Cinematic Rock</option><option value="romantic film">Romántico</option><option value="urban night">Urbano nocturno</option><option value="live performance">Performance</option><option value="dreamlike surreal">Surreal / Dream</option></select></div>
<div><label>Formato</label><select name="aspect"><option>16:9</option><option>9:16</option></select></div>
<div><label>Calidad</label><select name="quality"><option value="preview">Preview rápido</option><option value="final" selected>Final 1080p</option><option value="master">Master</option></select></div>
<div class="full"><label>Letra (opcional)</label><textarea name="lyrics" placeholder="Pegá acá la letra. Si no la cargás, la app arma escenas por duración."></textarea></div>
<div class="full"><button>Crear proyecto y renderizar</button><p class="muted">El primer render usa tu material original con FFmpeg. Las siguientes versiones conectarán cada tarjeta del storyboard con modelos locales de ComfyUI.</p><div id="status" class="status">Listo para empezar.</div></div>
</form></section>
<aside class="card"><h2>Pipeline</h2><div class="stages"><div class="stage active"><div class="dot"></div><div><strong>1. Intake</strong><span>Canción, referencia, estilo y letra.</span></div></div><div class="stage"><div class="dot"></div><div><strong>2. Análisis musical</strong><span>Duración ahora; BPM/Whisper en próxima capa.</span></div></div><div class="stage"><div class="dot"></div><div><strong>3. Storyboard</strong><span>Escenas editables por letra/segmento.</span></div></div><div class="stage"><div class="dot"></div><div><strong>4. Generación IA local</strong><span>ComfyUI + identidad + clips + lip-sync.</span></div></div><div class="stage"><div class="dot"></div><div><strong>5. Master</strong><span>FFmpeg, audio original, upscale y export.</span></div></div></div><div id="storyboard" class="storyboard"></div><div id="preview" class="preview"></div></aside></div></main>
<script>
const f=document.querySelector('#form'),s=document.querySelector('#status'),sb=document.querySelector('#storyboard'),pv=document.querySelector('#preview');
fetch('/api/health').then(r=>r.json()).then(j=>{document.querySelector('#comfy').textContent='ComfyUI: '+(j.comfyui?'online':'offline')}).catch(()=>{});
f.addEventListener('submit',async e=>{e.preventDefault();s.textContent='Subiendo archivos y creando storyboard…';sb.innerHTML='';pv.innerHTML='';const data=new FormData(f);try{const r=await fetch('/api/projects',{method:'POST',body:data});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Error');s.textContent=`Proyecto ${j.id}\nDuración: ${j.duration.toFixed(1)} s\nEscenas: ${j.storyboard.length}\nRender: completo`;sb.innerHTML=j.storyboard.slice(0,8).map(x=>`<div class="scene"><b>ESCENA ${x.id} · ${x.start}s–${x.end}s</b><p>${escapeHtml(x.lyrics||x.prompt)}</p></div>`).join('');pv.innerHTML=`<video controls src="${j.video_url}"></video><p><a style="color:#bc9cff" href="${j.download_url}">Descargar MP4</a></p>`;}catch(err){s.textContent='Error: '+err.message}});
function escapeHtml(x){return String(x).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
</script></body></html>'''


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE


@app.get("/api/health")
def health():
    comfy = False
    try:
        r = requests.get("http://127.0.0.1:8188/system_stats", timeout=0.8)
        comfy = r.ok
    except requests.RequestException:
        pass
    return {"ok": True, "comfyui": comfy}


@app.post("/api/projects")
async def create_project(
    song: UploadFile = File(...),
    visual: UploadFile = File(...),
    title: str = Form("Mi videoclip"),
    style: str = Form("cinematic rock"),
    aspect: str = Form("16:9"),
    quality: str = Form("final"),
    lyrics: str = Form(""),
):
    if aspect not in {"16:9", "9:16"}:
        raise HTTPException(400, "Formato inválido")
    if quality not in {"preview", "final", "master"}:
        raise HTTPException(400, "Calidad inválida")
    if not song.content_type or not song.content_type.startswith("audio/"):
        raise HTTPException(400, "La canción debe ser un archivo de audio")
    visual_type = visual.content_type or ""
    if visual_type.startswith("image/"):
        visual_kind = "image"
        visual_fallback = ".jpg"
    elif visual_type.startswith("video/"):
        visual_kind = "video"
        visual_fallback = ".mp4"
    else:
        raise HTTPException(400, "La referencia debe ser una foto o video")

    project_id, project_dir, meta = create_project_files(title, style, aspect, quality, lyrics)
    song_path = project_dir / f"song{safe_suffix(song.filename, '.mp3')}"
    visual_path = project_dir / f"reference{safe_suffix(visual.filename, visual_fallback)}"
    copy_upload(song.file, song_path)
    copy_upload(visual.file, visual_path)

    try:
        d = duration(song_path)
        meta.update({"status": "analyzed", "progress": 25, "duration": d, "song": song_path.name, "visual": visual_path.name, "visual_kind": visual_kind})
        meta["storyboard"] = make_storyboard(d, lyrics, style)
        meta.update({"status": "storyboard_ready", "progress": 45})
        save_json(project_dir / "project.json", meta)

        output = render_reference(project_dir, song_path, visual_path, visual_kind, aspect, quality)
        meta.update({"status": "complete", "progress": 100, "output": output.name})
        save_json(project_dir / "project.json", meta)
    except Exception as exc:
        meta.update({"status": "failed", "error": str(exc)})
        save_json(project_dir / "project.json", meta)
        raise HTTPException(500, f"No se pudo procesar el proyecto: {exc}") from exc

    return JSONResponse({
        "id": project_id,
        "duration": d,
        "storyboard": meta["storyboard"],
        "status": meta["status"],
        "video_url": f"/api/projects/{project_id}/video",
        "download_url": f"/api/projects/{project_id}/download",
    })


@app.get("/api/projects/{project_id}")
def project(project_id: str):
    try:
        return load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Proyecto no encontrado")


@app.get("/api/projects/{project_id}/video")
def video(project_id: str):
    path = PROJECTS / project_id / "final.mp4"
    if not path.exists():
        raise HTTPException(404, "Video no disponible")
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/projects/{project_id}/download")
def download(project_id: str):
    path = PROJECTS / project_id / "final.mp4"
    if not path.exists():
        raise HTTPException(404, "Video no disponible")
    return FileResponse(path, media_type="video/mp4", filename=f"{project_id}-music-video.mp4")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=True)
