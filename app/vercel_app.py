from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from html import escape

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="AI Music Video Studio Control", version="0.12.1")


def _worker_url() -> str:
    return os.getenv("RENDER_WORKER_URL", "").strip().rstrip("/")


def _worker_json(path: str, timeout: float = 4.0) -> dict:
    base = _worker_url()
    if not base:
        raise RuntimeError("RENDER_WORKER_URL no configurado")
    req = urllib.request.Request(
        f"{base}/{path.lstrip('/')}",
        headers={"User-Agent": "AI-Music-Video-Studio-Vercel/0.12.1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Respuesta inválida del worker")
    return payload


def _worker_health() -> dict:
    base = _worker_url()
    if not base:
        return {"configured": False, "online": False, "worker_url": None}
    try:
        payload = _worker_json("/api/health", timeout=3.0)
        return {"configured": True, "online": True, "worker_url": base, "worker": payload}
    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return {"configured": True, "online": False, "worker_url": base, "error": str(exc)}


@app.get("/api/control/health")
def control_health():
    return {"ok": True, "version": app.version, **_worker_health()}


@app.get("/api/control/checkpoints")
def control_checkpoints():
    if not _worker_url():
        return JSONResponse({"worker_configured": False, "online": False, "checkpoints": [], "count": 0, "error": "Worker no configurado"})
    try:
        payload = _worker_json("/api/comfyui/checkpoints", timeout=5.0)
        return JSONResponse({"worker_configured": True, **payload})
    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return JSONResponse({"worker_configured": True, "online": False, "checkpoints": [], "count": 0, "error": str(exc)})


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    worker = _worker_url()
    worker_js = json.dumps(worker)
    configured = bool(worker)
    setup_note = (
        "Worker configurado. La canción, la foto y los renders viajan directamente al worker; Vercel no procesa el video pesado."
        if configured
        else "Falta configurar RENDER_WORKER_URL en Vercel. El sitio ya está desplegado, pero no puede leer tus modelos de ComfyUI ni crear videoclips hasta conectar el worker."
    )
    checkpoint_option = "Cargando modelos de ComfyUI…" if configured else "Conectá el worker para ver modelos"
    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Music Video Studio</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#080a10;color:#f7f7fb;font-family:Inter,system-ui,-apple-system,sans-serif}}.shell{{max-width:1240px;margin:auto;padding:34px 20px 70px}}.hero{{padding:10px 0 24px}}.eyebrow{{font-size:12px;font-weight:850;letter-spacing:.16em;text-transform:uppercase;color:#8e97b4}}h1{{font-size:clamp(40px,6vw,74px);line-height:.98;letter-spacing:-.055em;margin:8px 0 14px}}.hero p{{max-width:820px;color:#aeb5c9;font-size:17px;line-height:1.55}}.badge{{display:inline-block;border:1px solid #30364a;background:#111522;border-radius:999px;padding:7px 10px;margin:5px 6px 0 0;font-size:12px;color:#d2d5ed}}.layout{{display:grid;grid-template-columns:.9fr 1.1fr;gap:22px}}.card{{background:linear-gradient(180deg,#121620,#0d1018);border:1px solid #242a39;border-radius:22px;padding:21px;box-shadow:0 24px 70px rgba(0,0,0,.24)}}h2{{margin:0 0 16px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:13px}}.full{{grid-column:1/-1}}label{{display:block;font-size:12px;font-weight:850;color:#dce0ed;margin:0 0 6px}}input,select,textarea{{width:100%;padding:12px 13px;border-radius:12px;border:1px solid #343a4d;background:#090c13;color:white;font:inherit}}textarea{{min-height:100px;resize:vertical}}button{{border:0;border-radius:12px;padding:11px 13px;background:#282e42;color:white;font-weight:800;cursor:pointer}}button:disabled{{opacity:.45;cursor:not-allowed}}.primary{{width:100%;padding:14px;background:linear-gradient(135deg,#7258ff,#d84fc7)}}.auto{{background:linear-gradient(135deg,#6f58ff,#b449d2)}}.ok{{background:#174c3b}}.muted{{font-size:12px;color:#8991a7;line-height:1.5}}.status{{margin-top:12px;background:#090c13;border:1px solid #272d3d;border-radius:12px;padding:12px;white-space:pre-wrap;color:#cad0e1;min-height:58px}}.storyboard{{display:grid;gap:10px;max-height:760px;overflow:auto}}.scene{{border:1px solid #292f40;border-radius:14px;padding:13px;background:#0a0d14}}.scene .top{{display:flex;justify-content:space-between;gap:10px}}.scene b{{font-size:12px}}.scene p{{font-size:12px;line-height:1.45;color:#929aaf;margin:9px 0}}.scene button{{font-size:11px;padding:7px 9px;margin:3px 5px 0 0}}.meta{{font-size:11px;color:#a38fff}}.preview video{{width:100%;margin-top:14px;border-radius:14px;background:#000}}a{{color:#bc9cff}}.notice{{border:1px solid #32384a;background:#101521;border-radius:14px;padding:12px 14px;color:#b7bed2;margin:12px 0 18px;font-size:13px;line-height:1.5}}.modelhint{{margin:6px 0 0;color:#8991a7;font-size:11px}}@media(max-width:900px){{.layout{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr}}.full{{grid-column:auto}}}}
</style></head>
<body><main class="shell"><section class="hero"><div class="eyebrow">Vercel control plane · render worker externo</div><h1>AI Music Video Studio</h1><p>Subí una canción y una foto/video. Vercel maneja la interfaz; tu worker ejecuta ComfyUI, FFmpeg, identidad, lip-sync y upscale.</p><span class="badge">Vercel</span><span class="badge">ComfyUI</span><span class="badge">Auto Pipeline</span><span class="badge" id="workerBadge">Worker…</span></section>
<div class="notice">{escape(setup_note)}</div>
<div class="layout"><section class="card"><h2>Nuevo videoclip</h2><form id="form" class="grid"><div><label>Canción</label><input type="file" name="song" accept="audio/*" required></div><div><label>Foto o video</label><input type="file" name="visual" accept="image/*,video/*" required></div><div><label>Título</label><input name="title" placeholder="Mi videoclip"></div><div><label>Estilo</label><select name="style"><option value="cinematic rock">Cinematic Rock</option><option value="romantic film">Romántico</option><option value="urban night">Urbano nocturno</option><option value="live performance">Performance</option><option value="dreamlike surreal">Surreal / Dream</option></select></div><div><label>Formato</label><select name="aspect"><option>16:9</option><option>9:16</option></select></div><div><label>Calidad</label><select name="quality"><option value="preview">Preview</option><option value="final" selected>Final 1080p</option><option value="master">Master</option></select></div><div class="full"><label>Letra (opcional)</label><textarea name="lyrics" placeholder="Pegá la letra..."></textarea></div><div class="full"><label>Modelo / Checkpoint ComfyUI</label><select id="checkpoint" {'disabled' if not configured else ''}><option value="">{escape(checkpoint_option)}</option></select><p id="modelHint" class="modelhint">Los modelos se leen automáticamente desde CheckpointLoaderSimple.</p></div><div class="full"><button id="createBtn" class="primary" {'disabled' if not configured else ''}>Crear proyecto en worker</button></div></form><div id="status" class="status">{'Consultando worker y modelos…' if configured else 'Configurá RENDER_WORKER_URL en Vercel.'}</div><div id="preview" class="preview"></div></section><section class="card"><h2>Storyboard</h2><div id="storyboard" class="storyboard"><p class="muted">Creá un proyecto para ver las escenas.</p></div></section></div></main>
<script>
const WORKER={worker_js};const f=document.querySelector('#form'),s=document.querySelector('#status'),sb=document.querySelector('#storyboard'),pv=document.querySelector('#preview'),cp=document.querySelector('#checkpoint'),badge=document.querySelector('#workerBadge'),modelHint=document.querySelector('#modelHint');let current=null;const running=new Set();
async function loadCheckpoints(){{
  try{{
    const j=await fetch('/api/control/checkpoints',{{cache:'no-store'}}).then(r=>r.json());
    cp.innerHTML='';
    if(!j.worker_configured){{cp.disabled=true;cp.innerHTML='<option value="">Worker no configurado</option>';modelHint.textContent='Conectá RENDER_WORKER_URL para leer los modelos reales.';return}}
    if(!j.online){{cp.disabled=true;cp.innerHTML='<option value="">ComfyUI offline</option>';modelHint.textContent=j.error||'El worker responde, pero ComfyUI no está accesible.';return}}
    const models=Array.isArray(j.checkpoints)?j.checkpoints:[];
    if(!models.length){{cp.disabled=true;cp.innerHTML='<option value="">No hay checkpoints detectados</option>';modelHint.textContent=j.error||'Colocá un .safetensors/.ckpt en ComfyUI/models/checkpoints y reiniciá/refresh ComfyUI.';return}}
    cp.disabled=false;
    cp.innerHTML='<option value="">Elegí un modelo…</option>'+models.map(name=>`<option value="${{esc(name)}}">${{esc(name)}}</option>`).join('');
    if(models.length===1)cp.value=models[0];
    modelHint.textContent=`${{models.length}} modelo${{models.length===1?'':'s'}} detectado${{models.length===1?'':'s'}} en ComfyUI.`;
  }}catch(err){{cp.disabled=true;cp.innerHTML='<option value="">Error cargando modelos</option>';modelHint.textContent=err.message}}
}}
async function health(){{try{{const j=await fetch('/api/control/health',{{cache:'no-store'}}).then(r=>r.json());badge.textContent='Worker: '+(j.online?'online':'offline');if(j.online)s.textContent='Worker online. Cargando modelos de ComfyUI…';}}catch{{badge.textContent='Worker: error'}}await loadCheckpoints();}}health();
function w(path){{return WORKER+path}}
f.addEventListener('submit',async e=>{{e.preventDefault();if(!WORKER)return;s.textContent='Subiendo directamente al worker y creando storyboard…';sb.innerHTML='';pv.innerHTML='';try{{const r=await fetch(w('/api/projects'),{{method:'POST',body:new FormData(f)}}),j=await r.json();if(!r.ok)throw Error(j.detail||'Error del worker');current=j.id;s.textContent=`Proyecto ${{j.id}}\nBPM: ${{j.analysis?.bpm??'n/d'}}\nDuración: ${{Number(j.duration||0).toFixed(1)}}s\nEscenas: ${{j.storyboard?.length||0}}`;draw(j.storyboard||[]);pv.innerHTML=`<video controls src="${{w(j.video_url)}}"></video><p><a href="${{w(j.download_url)}}" target="_blank">Descargar render base</a></p>`}}catch(err){{s.textContent='Error: '+err.message}}}});
function esc(x){{return String(x??'').replace(/[&<>'\"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','\"':'&quot;'}}[c]||c))}}
function draw(rows){{sb.innerHTML=rows.map(x=>`<div class="scene"><div class="top"><b>ESCENA ${{x.id}} · ${{x.start}}s–${{x.end}}s</b><span class="meta">${{x.status||'planned'}}</span></div><p>${{esc(x.lyrics||x.director_prompt||x.prompt)}}</p><button class="auto" onclick="autoPipeline(${{x.id}})">✨ Auto Pipeline</button><button class="${{x.approved?'ok':''}}" onclick="approve(${{x.id}},${{!x.approved}})">${{x.approved?'OK ✓':'Aprobar'}}</button></div>`).join('')}}
async function reload(){{if(!current)return;const p=await fetch(w(`/api/projects/${{current}}`)).then(r=>r.json());draw(p.storyboard||[])}}
async function autoPipeline(id){{if(!current||running.has(id))return;if(!cp.value.trim()){{s.textContent='Elegí primero un modelo/checkpoint de ComfyUI.';return}}running.add(id);try{{for(let i=0;i<900;i++){{const r=await fetch(w(`/api/projects/${{current}}/scenes/${{id}}/auto-pipeline`),{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{checkpoint:cp.value.trim(),fps:24,use_face_refine:true,mouth_mask:true,enhance_face:true,use_lipsync:true,use_upscale:true,upscale_scale:2,strict_optional:false}})}});const j=await r.json();if(!r.ok)throw Error(j.detail||JSON.stringify(j));const last=(j.log||[]).slice(-1)[0];s.textContent=`Escena ${{id}}: ${{j.auto_state||j.status}}${{last?'\n'+last.stage+': '+last.status+(last.detail?' — '+last.detail:''):''}}`;await reload();if(j.auto_state==='ready_for_review'){{s.textContent=`Escena ${{id}} lista para revisar ✓\nVersión: ${{j.review_version||'-'}}`;return}}if(j.auto_state==='blocked'||j.auto_state==='failed')throw Error(j.last_error||j.auto_state);await new Promise(r=>setTimeout(r,(j.auto_state==='waiting_video'||j.auto_state==='waiting_image')?2500:500));}}throw Error('Seguimiento agotado; pulsá Auto Pipeline para reanudar.')}}catch(err){{s.textContent='Auto Pipeline: '+err.message}}finally{{running.delete(id)}}}}
async function approve(id,value){{if(!current)return;await fetch(w(`/api/projects/${{current}}/scenes/${{id}}`),{{method:'PATCH',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{approved:value}})}});reload()}}
</script></body></html>'''


@app.get("/api/control/config")
def control_config():
    base = _worker_url()
    return JSONResponse({"worker_configured": bool(base), "worker_url": base or None, "version": app.version})
