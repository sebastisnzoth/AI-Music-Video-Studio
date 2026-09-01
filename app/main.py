from __future__ import annotations

from pathlib import Path

import requests
import uvicorn
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .audio_analysis import analyze_audio
from .director import direct_storyboard
from .model_catalog import catalog
from .scene_package import prepare_all_scenes, prepare_scene_package
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
    update_scene,
)

app = FastAPI(title="AI Music Video Studio", version="0.4.0")

PAGE = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Music Video Studio</title><style>
*{box-sizing:border-box}body{margin:0;background:#090b12;color:#f5f7fb;font-family:Inter,system-ui,-apple-system,sans-serif}.shell{max-width:1180px;margin:auto;padding:38px 20px 80px}.hero{padding:30px 0 24px}.eyebrow{color:#9ca3c7;font-weight:700;letter-spacing:.16em;text-transform:uppercase;font-size:12px}.hero h1{font-size:clamp(38px,6vw,72px);line-height:.98;letter-spacing:-.055em;margin:10px 0 16px}.hero p{max-width:780px;color:#aeb4c7;font-size:18px;line-height:1.6}.badge{display:inline-flex;border:1px solid #343952;border-radius:999px;padding:7px 11px;color:#c9cceb;background:#111522;margin:4px 7px 0 0}.layout{display:grid;grid-template-columns:1fr 1fr;gap:22px}.card{background:linear-gradient(180deg,#121621,#0e111a);border:1px solid #242a3b;border-radius:22px;padding:22px;box-shadow:0 24px 70px rgba(0,0,0,.25)}h2{margin:0 0 18px;font-size:22px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.full{grid-column:1/-1}label{display:block;font-size:13px;font-weight:800;color:#d9dceb;margin-bottom:7px}input,select,textarea{width:100%;border:1px solid #343b50;border-radius:13px;background:#0b0e16;color:#fff;padding:13px 14px;font:inherit}textarea{min-height:128px;resize:vertical}button{border:0;border-radius:14px;background:linear-gradient(135deg,#7457ff,#db4fc6);color:#fff;font-weight:900;padding:15px 18px;font-size:15px;cursor:pointer}.muted{color:#858ca5;font-size:13px;line-height:1.5}.status{margin-top:15px;border-radius:14px;padding:14px;background:#0a0d15;border:1px solid #252b3c;min-height:54px;color:#cbd0e3;white-space:pre-wrap}.storyboard{display:grid;gap:10px;margin-top:14px;max-height:620px;overflow:auto}.scene{padding:12px;border:1px solid #282e40;border-radius:13px;background:#0b0e16}.scene b{font-size:12px;color:#b9bee0}.scene p{font-size:12px;color:#8990a7;margin:7px 0;line-height:1.4}.scene .energy{font-size:11px;color:#c79cff}.scene .director{font-size:11px;color:#8dd7c5}.scene .toolchain{font-size:11px;color:#9ca3c7}.scene button{padding:7px 10px;font-size:11px;background:#262c42;margin-right:6px}.preview{margin-top:16px}.preview video{width:100%;border-radius:15px;border:1px solid #293047;background:#000}@media(max-width:850px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style></head><body><main class="shell"><section class="hero"><div class="eyebrow">local · gratis · storyboard musical</div><h1>AI Music Video Studio</h1><p>Subí canción + foto/video. La app analiza BPM, beats y energía, crea un storyboard dirigido y prepara cada escena para una cadena local de imagen, video, lip-sync y upscale.</p><div><span class="badge">1080p</span><span class="badge">Beat-aware</span><span class="badge">Director local</span><span class="badge">Model catalog</span><span class="badge" id="comfy">ComfyUI: comprobando…</span></div></section><div class="layout"><section class="card"><h2>Nuevo videoclip</h2><form id="form" class="grid"><div><label>Canción</label><input type="file" name="song" accept="audio/*" required></div><div><label>Foto o video</label><input type="file" name="visual" accept="image/*,video/*" required></div><div><label>Título</label><input name="title" placeholder="Mi videoclip"></div><div><label>Estilo</label><select name="style"><option value="cinematic rock">Cinematic Rock</option><option value="romantic film">Romántico</option><option value="urban night">Urbano nocturno</option><option value="live performance">Performance</option><option value="dreamlike surreal">Surreal / Dream</option></select></div><div><label>Formato</label><select name="aspect"><option>16:9</option><option>9:16</option></select></div><div><label>Calidad</label><select name="quality"><option value="preview">Preview rápido</option><option value="final" selected>Final 1080p</option><option value="master">Master</option></select></div><div class="full"><label>Letra (opcional)</label><textarea name="lyrics" placeholder="Pegá la letra para relacionar cada escena con la canción."></textarea></div><div class="full"><button>Analizar y crear videoclip</button><p class="muted">El Director decide estrategia, cámara y lip-sync. Después podés preparar cada escena para los motores locales.</p><div id="status" class="status">Listo para empezar.</div></div></form></section><aside class="card"><h2>Storyboard musical</h2><div id="storyboard" class="storyboard"><p class="muted">Las escenas aparecerán acá.</p></div><div id="preview" class="preview"></div></aside></div></main><script>
const f=document.querySelector('#form'),s=document.querySelector('#status'),sb=document.querySelector('#storyboard'),pv=document.querySelector('#preview');let current=null;
fetch('/api/health').then(r=>r.json()).then(j=>{document.querySelector('#comfy').textContent='ComfyUI: '+(j.comfyui?'online':'offline')}).catch(()=>{});
f.addEventListener('submit',async e=>{e.preventDefault();s.textContent='Analizando audio, beats y dirección visual…';sb.innerHTML='';pv.innerHTML='';const data=new FormData(f);try{const r=await fetch('/api/projects',{method:'POST',body:data});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Error');current=j.id;s.textContent=`Proyecto ${j.id}\nDuración: ${j.duration.toFixed(1)} s\nBPM: ${j.analysis.bpm??'no detectado'}\nEscenas: ${j.storyboard.length}\nRender base: completo`;draw(j.storyboard);pv.innerHTML=`<video controls src="${j.video_url}"></video><p><a style="color:#bc9cff" href="${j.download_url}">Descargar MP4</a></p>`;}catch(err){s.textContent='Error: '+err.message}});
function draw(rows){sb.innerHTML=rows.map(x=>`<div class="scene"><b>ESCENA ${x.id} · ${x.start}s–${x.end}s</b><div class="energy">energía: ${x.energy_band||x.energy||'medium'}</div><div class="director">${x.strategy||'narrative'} ${x.needs_lipsync?'· lip-sync':''}</div><div class="toolchain">${x.toolchain?`${x.toolchain.image_model} → ${x.toolchain.video_model} → ${x.toolchain.lipsync_model}`:'sin preparar'}</div><p>${esc(x.lyrics||x.director_prompt||x.prompt)}</p><button onclick="prepareScene(${x.id})">Preparar</button><button onclick="approve(${x.id},${!x.approved})">${x.approved?'Quitar OK':'Aprobar'}</button></div>`).join('')}
async function prepareScene(id){if(!current)return;const r=await fetch(`/api/projects/${current}/scenes/${id}/prepare`,{method:'POST'});const j=await r.json();if(!r.ok){s.textContent='Error preparando escena: '+(j.detail||'');return}const p=await fetch(`/api/projects/${current}`).then(x=>x.json());draw(p.storyboard);s.textContent=`Escena ${id} preparada\nAudio: ${j.audio_path}\nVideo: ${j.toolchain.video_model}\nLip-sync: ${j.toolchain.lipsync_model}`}
async function approve(id,value){if(!current)return;const r=await fetch(`/api/projects/${current}/scenes/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved:value})});if(r.ok){const p=await fetch(`/api/projects/${current}`).then(x=>x.json());draw(p.storyboard)}}
function esc(x){return String(x).replace(/[&<>'\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[c]||c))}
</script></body></html>'''


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE


@app.get("/api/health")
def health():
    comfy = False
    try:
        comfy = requests.get("http://127.0.0.1:8188/system_stats", timeout=0.8).ok
    except requests.RequestException:
        pass
    return {"ok": True, "comfyui": comfy, "version": app.version}


@app.get("/api/models")
def models():
    return catalog()


@app.get("/api/projects")
def projects():
    items = []
    for path in sorted(PROJECTS.glob("*/project.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            meta = __import__("json").loads(path.read_text(encoding="utf-8"))
            items.append({k: meta.get(k) for k in ("id", "title", "status", "progress", "duration", "aspect", "quality")})
        except Exception:
            continue
    return items


@app.post("/api/projects")
async def create_project(song: UploadFile = File(...), visual: UploadFile = File(...), title: str = Form("Mi videoclip"), style: str = Form("cinematic rock"), aspect: str = Form("16:9"), quality: str = Form("final"), lyrics: str = Form("")):
    if aspect not in {"16:9", "9:16"}:
        raise HTTPException(400, "Formato inválido")
    if quality not in {"preview", "final", "master"}:
        raise HTTPException(400, "Calidad inválida")
    if not song.content_type or not song.content_type.startswith("audio/"):
        raise HTTPException(400, "La canción debe ser un archivo de audio")
    visual_type = visual.content_type or ""
    if visual_type.startswith("image/"):
        visual_kind, visual_fallback = "image", ".jpg"
    elif visual_type.startswith("video/"):
        visual_kind, visual_fallback = "video", ".mp4"
    else:
        raise HTTPException(400, "La referencia debe ser una foto o video")

    project_id, project_dir, meta = create_project_files(title, style, aspect, quality, lyrics)
    song_path = project_dir / f"song{safe_suffix(song.filename, '.mp3')}"
    visual_path = project_dir / f"reference{safe_suffix(visual.filename, visual_fallback)}"
    copy_upload(song.file, song_path); copy_upload(visual.file, visual_path)
    try:
        d = duration(song_path)
        analysis = analyze_audio(song_path)
        analysis.setdefault("duration", round(d, 3))
        meta.update({"status":"analyzed","progress":30,"duration":d,"analysis":analysis,"song":song_path.name,"visual":visual_path.name,"visual_kind":visual_kind})
        base_storyboard = make_storyboard(d, lyrics, style, analysis)
        meta["storyboard"] = direct_storyboard(base_storyboard, style)
        meta.update({"status":"storyboard_ready","progress":55}); save_json(project_dir/"project.json",meta)
        output = render_reference(project_dir, song_path, visual_path, visual_kind, aspect, quality)
        meta.update({"status":"complete","progress":100,"output":output.name}); save_json(project_dir/"project.json",meta)
    except Exception as exc:
        meta.update({"status":"failed","error":str(exc)}); save_json(project_dir/"project.json",meta)
        raise HTTPException(500, f"No se pudo procesar el proyecto: {exc}") from exc
    return JSONResponse({"id":project_id,"duration":d,"analysis":analysis,"storyboard":meta["storyboard"],"status":meta["status"],"video_url":f"/api/projects/{project_id}/video","download_url":f"/api/projects/{project_id}/download"})


@app.get("/api/projects/{project_id}")
def project(project_id: str):
    try:
        return load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Proyecto no encontrado")


@app.patch("/api/projects/{project_id}/scenes/{scene_id}")
def patch_scene(project_id: str, scene_id: int, payload: dict = Body(...)):
    try:
        return update_scene(project_id, scene_id, payload)
    except FileNotFoundError:
        raise HTTPException(404, "Proyecto no encontrado")
    except KeyError:
        raise HTTPException(404, "Escena no encontrada")


@app.post("/api/projects/{project_id}/scenes/{scene_id}/prepare")
def prepare_scene(project_id: str, scene_id: int):
    try:
        return prepare_scene_package(project_id, scene_id)
    except FileNotFoundError:
        raise HTTPException(404, "Proyecto o audio no encontrado")
    except KeyError:
        raise HTTPException(404, "Escena no encontrada")


@app.post("/api/projects/{project_id}/prepare-all")
def prepare_all(project_id: str):
    try:
        return {"project_id": project_id, "scenes": prepare_all_scenes(project_id)}
    except FileNotFoundError:
        raise HTTPException(404, "Proyecto no encontrado")


@app.get("/api/projects/{project_id}/video")
def video(project_id: str):
    path = PROJECTS / project_id / "final.mp4"
    if not path.exists(): raise HTTPException(404, "Video no disponible")
    return FileResponse(path, media_type="video/mp4")


@app.get("/api/projects/{project_id}/download")
def download(project_id: str):
    path = PROJECTS / project_id / "final.mp4"
    if not path.exists(): raise HTTPException(404, "Video no disponible")
    return FileResponse(path, media_type="video/mp4", filename=f"{project_id}-music-video.mp4")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=True)
