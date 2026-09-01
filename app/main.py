from __future__ import annotations

import json

import uvicorn
from fastapi import Body, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from .audio_analysis import analyze_audio
from .comfyui import ComfyUIError, is_online
from .director import direct_storyboard
from .generation_service import queue_scene_image, refresh_scene_generation
from .model_catalog import catalog
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
from .scene_package import prepare_all_scenes, prepare_scene_package

app = FastAPI(title="AI Music Video Studio", version="0.5.0")

PAGE = r'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Music Video Studio</title><style>
*{box-sizing:border-box}body{margin:0;background:#080a10;color:#f6f7fb;font-family:Inter,system-ui,-apple-system,sans-serif}.shell{max-width:1220px;margin:auto;padding:34px 20px 80px}.hero{padding:22px 0 26px}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.15em;color:#9299b4;text-transform:uppercase}.hero h1{font-size:clamp(40px,6vw,72px);line-height:1;letter-spacing:-.055em;margin:8px 0 14px}.hero p{max-width:800px;color:#aab1c5;font-size:17px;line-height:1.55}.badge{display:inline-block;border:1px solid #30364a;background:#111522;border-radius:999px;padding:7px 10px;margin:5px 6px 0 0;font-size:12px;color:#c8cceb}.layout{display:grid;grid-template-columns:.9fr 1.1fr;gap:22px}.card{background:linear-gradient(180deg,#121620,#0d1018);border:1px solid #242a39;border-radius:22px;padding:21px;box-shadow:0 24px 70px rgba(0,0,0,.24)}h2{margin:0 0 16px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.full{grid-column:1/-1}label{display:block;font-size:12px;font-weight:850;color:#dce0ed;margin:0 0 6px}input,select,textarea{width:100%;padding:12px 13px;border-radius:12px;border:1px solid #343a4d;background:#090c13;color:white;font:inherit}textarea{min-height:110px;resize:vertical}button{border:0;border-radius:12px;padding:11px 13px;background:#282e42;color:white;font-weight:800;cursor:pointer}.primary{width:100%;padding:14px;background:linear-gradient(135deg,#7258ff,#d84fc7)}.muted{font-size:12px;color:#8991a7;line-height:1.5}.status{margin-top:12px;background:#090c13;border:1px solid #272d3d;border-radius:12px;padding:12px;white-space:pre-wrap;color:#cad0e1;min-height:48px}.storyboard{display:grid;gap:10px;max-height:720px;overflow:auto}.scene{border:1px solid #292f40;border-radius:14px;padding:13px;background:#0a0d14}.scene .top{display:flex;justify-content:space-between;gap:10px}.scene b{font-size:12px}.meta{font-size:11px;color:#a38fff;margin-top:4px}.director{font-size:11px;color:#72d7be;margin-top:3px}.tool{font-size:11px;color:#969eb3;margin-top:3px}.scene p{font-size:12px;line-height:1.4;color:#929aaf;margin:9px 0}.scene button{font-size:11px;padding:7px 9px;margin:3px 5px 0 0}.scene button.ai{background:linear-gradient(135deg,#6f58ff,#b449d2)}.scene button.ok{background:#174c3b}.preview video{width:100%;margin-top:14px;border-radius:14px;background:black}.config{margin-top:15px;padding-top:14px;border-top:1px solid #262b3b}@media(max-width:900px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.full{grid-column:auto}}
</style></head><body><main class="shell"><section class="hero"><div class="eyebrow">100% local · sin API paga obligatoria</div><h1>AI Music Video Studio</h1><p>Canción + foto o video → análisis musical → Director → escenas → ComfyUI → lip-sync → upscale → master.</p><span class="badge">Beat-aware</span><span class="badge">Director local</span><span class="badge">1080p / 9:16</span><span class="badge" id="comfy">ComfyUI...</span></section><div class="layout"><section class="card"><h2>Nuevo videoclip</h2><form id="form" class="grid"><div><label>Canción</label><input type="file" name="song" accept="audio/*" required></div><div><label>Foto o video</label><input type="file" name="visual" accept="image/*,video/*" required></div><div><label>Título</label><input name="title" placeholder="Mi videoclip"></div><div><label>Estilo</label><select name="style"><option value="cinematic rock">Cinematic Rock</option><option value="romantic film">Romántico</option><option value="urban night">Urbano nocturno</option><option value="live performance">Performance</option><option value="dreamlike surreal">Surreal / Dream</option></select></div><div><label>Formato</label><select name="aspect"><option>16:9</option><option>9:16</option></select></div><div><label>Calidad</label><select name="quality"><option value="preview">Preview</option><option value="final" selected>Final 1080p</option><option value="master">Master</option></select></div><div class="full"><label>Letra (opcional)</label><textarea name="lyrics" placeholder="Pegá la letra..."></textarea></div><div class="full"><button class="primary">Analizar y crear proyecto</button></div></form><div class="config"><label>Checkpoint de ComfyUI instalado</label><input id="checkpoint" placeholder="ejemplo: v1-5-pruned-emaonly.safetensors"><p class="muted">Debe coincidir exactamente con un archivo visible en el nodo CheckpointLoaderSimple de tu ComfyUI. La app no descarga modelos pagos.</p></div><div id="status" class="status">Listo.</div><div id="preview" class="preview"></div></section><section class="card"><h2>Storyboard</h2><div id="storyboard" class="storyboard"><p class="muted">Creá un proyecto para ver las escenas.</p></div></section></div></main><script>
const f=document.querySelector('#form'),s=document.querySelector('#status'),sb=document.querySelector('#storyboard'),pv=document.querySelector('#preview'),cp=document.querySelector('#checkpoint');let current=null;
async function health(){try{const j=await fetch('/api/health').then(r=>r.json());document.querySelector('#comfy').textContent='ComfyUI: '+(j.comfyui?'online':'offline')}catch{}}health();
f.addEventListener('submit',async e=>{e.preventDefault();s.textContent='Analizando canción y creando storyboard…';sb.innerHTML='';pv.innerHTML='';try{const r=await fetch('/api/projects',{method:'POST',body:new FormData(f)}),j=await r.json();if(!r.ok)throw Error(j.detail||'Error');current=j.id;s.textContent=`Proyecto ${j.id}\nBPM: ${j.analysis.bpm??'no detectado'}\nDuración: ${j.duration.toFixed(1)}s\nEscenas: ${j.storyboard.length}`;draw(j.storyboard);pv.innerHTML=`<video controls src="${j.video_url}"></video><p><a style="color:#bc9cff" href="${j.download_url}">Descargar render base</a></p>`}catch(err){s.textContent='Error: '+err.message}});
function draw(rows){sb.innerHTML=rows.map(x=>`<div class="scene"><div class="top"><b>ESCENA ${x.id} · ${x.start}s–${x.end}s</b><span class="meta">${x.status||'planned'}</span></div><div class="director">${x.strategy||'narrative'} ${x.needs_lipsync?'· necesita lip-sync':''}</div><div class="tool">${x.toolchain?`${x.toolchain.image_model} → ${x.toolchain.video_model} → ${x.toolchain.lipsync_model}`:'sin preparar'}</div><p>${esc(x.lyrics||x.director_prompt||x.prompt)}</p><button onclick="prepareScene(${x.id})">Preparar</button><button class="ai" onclick="generateImage(${x.id})">Generar IA</button><button onclick="checkScene(${x.id})">Estado</button><button class="${x.approved?'ok':''}" onclick="approve(${x.id},${!x.approved})">${x.approved?'OK ✓':'Aprobar'}</button></div>`).join('')}
async function reload(){if(!current)return;const p=await fetch(`/api/projects/${current}`).then(r=>r.json());draw(p.storyboard)}
async function prepareScene(id){if(!current)return;const r=await fetch(`/api/projects/${current}/scenes/${id}/prepare`,{method:'POST'}),j=await r.json();if(!r.ok){s.textContent='Error: '+(j.detail||'preparación');return}s.textContent=`Escena ${id} preparada\nAudio exacto: ${j.audio_path}`;reload()}
async function generateImage(id){if(!current)return;if(!cp.value.trim()){s.textContent='Escribí primero el nombre exacto de tu checkpoint local de ComfyUI.';return}s.textContent=`Enviando escena ${id} a ComfyUI…`;const r=await fetch(`/api/projects/${current}/scenes/${id}/generate-image`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({checkpoint:cp.value.trim()})}),j=await r.json();if(!r.ok){s.textContent='Error ComfyUI: '+(j.detail||JSON.stringify(j));return}s.textContent=`Escena ${id} en cola\nprompt_id: ${j.prompt_id}\nseed: ${j.settings.seed}`;reload()}
async function checkScene(id){if(!current)return;const r=await fetch(`/api/projects/${current}/scenes/${id}/generation-status`),j=await r.json();if(!r.ok){s.textContent='Error: '+(j.detail||'estado');return}s.textContent=`Escena ${id}: ${j.status}\nResultados: ${(j.outputs||[]).map(x=>x.filename).join(', ')||'todavía ninguno'}`;reload()}
async function approve(id,value){if(!current)return;await fetch(`/api/projects/${current}/scenes/${id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved:value})});reload()}
function esc(x){return String(x).replace(/[&<>'\"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}[c]||c))}
</script></body></html>'''


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE


@app.get("/api/health")
def health():
    return {"ok": True, "comfyui": is_online(), "version": app.version}


@app.get("/api/models")
def models():
    return catalog()


@app.get("/api/projects")
def projects():
    items = []
    for path in sorted(PROJECTS.glob("*/project.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            meta = json.loads(path.read_text(encoding="utf-8"))
            items.append({k: meta.get(k) for k in ("id", "title", "status", "progress", "duration", "aspect", "quality")})
        except Exception:
            continue
    return items


@app.post("/api/projects")
async def create_project(song: UploadFile = File(...), visual: UploadFile = File(...), title: str = Form("Mi videoclip"), style: str = Form("cinematic rock"), aspect: str = Form("16:9"), quality: str = Form("final"), lyrics: str = Form("")):
    if aspect not in {"16:9", "9:16"}: raise HTTPException(400, "Formato inválido")
    if quality not in {"preview", "final", "master"}: raise HTTPException(400, "Calidad inválida")
    if not song.content_type or not song.content_type.startswith("audio/"): raise HTTPException(400, "La canción debe ser audio")
    visual_type = visual.content_type or ""
    if visual_type.startswith("image/"): visual_kind, visual_fallback = "image", ".jpg"
    elif visual_type.startswith("video/"): visual_kind, visual_fallback = "video", ".mp4"
    else: raise HTTPException(400, "La referencia debe ser foto o video")

    project_id, project_dir, meta = create_project_files(title, style, aspect, quality, lyrics)
    song_path = project_dir / f"song{safe_suffix(song.filename, '.mp3')}"
    visual_path = project_dir / f"reference{safe_suffix(visual.filename, visual_fallback)}"
    copy_upload(song.file, song_path); copy_upload(visual.file, visual_path)
    try:
        d = duration(song_path)
        analysis = analyze_audio(song_path); analysis.setdefault("duration", round(d, 3))
        meta.update({"status":"analyzed","progress":30,"duration":d,"analysis":analysis,"song":song_path.name,"visual":visual_path.name,"visual_kind":visual_kind})
        meta["storyboard"] = direct_storyboard(make_storyboard(d, lyrics, style, analysis), style)
        meta.update({"status":"storyboard_ready","progress":55}); save_json(project_dir/"project.json", meta)
        output = render_reference(project_dir, song_path, visual_path, visual_kind, aspect, quality)
        meta.update({"status":"complete","progress":100,"output":output.name}); save_json(project_dir/"project.json", meta)
    except Exception as exc:
        meta.update({"status":"failed","error":str(exc)}); save_json(project_dir/"project.json", meta)
        raise HTTPException(500, f"No se pudo procesar: {exc}") from exc
    return JSONResponse({"id":project_id,"duration":d,"analysis":analysis,"storyboard":meta["storyboard"],"status":meta["status"],"video_url":f"/api/projects/{project_id}/video","download_url":f"/api/projects/{project_id}/download"})


@app.get("/api/projects/{project_id}")
def project(project_id: str):
    try: return load_project(project_id)
    except FileNotFoundError: raise HTTPException(404, "Proyecto no encontrado")


@app.patch("/api/projects/{project_id}/scenes/{scene_id}")
def patch_scene(project_id: str, scene_id: int, payload: dict = Body(...)):
    try: return update_scene(project_id, scene_id, payload)
    except FileNotFoundError: raise HTTPException(404, "Proyecto no encontrado")
    except KeyError: raise HTTPException(404, "Escena no encontrada")


@app.post("/api/projects/{project_id}/scenes/{scene_id}/prepare")
def prepare_scene(project_id: str, scene_id: int):
    try: return prepare_scene_package(project_id, scene_id)
    except FileNotFoundError: raise HTTPException(404, "Proyecto o audio no encontrado")
    except KeyError: raise HTTPException(404, "Escena no encontrada")


@app.post("/api/projects/{project_id}/prepare-all")
def prepare_all(project_id: str):
    try: return {"project_id": project_id, "scenes": prepare_all_scenes(project_id)}
    except FileNotFoundError: raise HTTPException(404, "Proyecto no encontrado")


@app.post("/api/projects/{project_id}/scenes/{scene_id}/generate-image")
def generate_image(project_id: str, scene_id: int, payload: dict = Body(...)):
    checkpoint = str(payload.get("checkpoint", "")).strip()
    if not checkpoint: raise HTTPException(400, "checkpoint requerido")
    try:
        return queue_scene_image(
            project_id,
            scene_id,
            checkpoint=checkpoint,
            seed=payload.get("seed"),
            steps=int(payload.get("steps", 24)),
            cfg=float(payload.get("cfg", 6.0)),
        )
    except (FileNotFoundError, KeyError) as exc: raise HTTPException(404, str(exc)) from exc
    except ComfyUIError as exc: raise HTTPException(502, str(exc)) from exc


@app.get("/api/projects/{project_id}/scenes/{scene_id}/generation-status")
def generation_status(project_id: str, scene_id: int):
    try: return refresh_scene_generation(project_id, scene_id)
    except (FileNotFoundError, KeyError) as exc: raise HTTPException(404, str(exc)) from exc
    except ComfyUIError as exc: raise HTTPException(502, str(exc)) from exc


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
