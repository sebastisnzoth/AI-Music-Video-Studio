from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="AI Music Video Studio Control", version="0.12.3")


def _worker_url() -> str:
    return os.getenv("RENDER_WORKER_URL", "").strip().rstrip("/")


def _worker_json(path: str, timeout: float = 4.0) -> dict:
    base = _worker_url()
    if not base:
        raise RuntimeError("RENDER_WORKER_URL no configurado")
    req = urllib.request.Request(
        f"{base}/{path.lstrip('/')}",
        headers={"User-Agent": "AI-Music-Video-Studio-Vercel/0.12.3"},
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
        return JSONResponse({"worker_configured": False, "online": False, "checkpoints": [], "count": 0, "error": "Worker no configurado en servidor"})
    try:
        payload = _worker_json("/api/comfyui/checkpoints", timeout=5.0)
        return JSONResponse({"worker_configured": True, **payload})
    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return JSONResponse({"worker_configured": True, "online": False, "checkpoints": [], "count": 0, "error": str(exc)})


@app.get("/api/control/config")
def control_config():
    base = _worker_url()
    return JSONResponse({"worker_configured": bool(base), "worker_url": base or None, "version": app.version})


PAGE = r'''<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI Music Video Studio</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#080a10;color:#f7f7fb;font-family:Inter,system-ui,-apple-system,sans-serif}.shell{max-width:1240px;margin:auto;padding:34px 20px 70px}.hero{padding:10px 0 24px}.eyebrow{font-size:12px;font-weight:850;letter-spacing:.16em;text-transform:uppercase;color:#8e97b4}h1{font-size:clamp(40px,6vw,74px);line-height:.98;letter-spacing:-.055em;margin:8px 0 14px}.hero p{max-width:820px;color:#aeb5c9;font-size:17px;line-height:1.55}.badge{display:inline-block;border:1px solid #30364a;background:#111522;border-radius:999px;padding:7px 10px;margin:5px 6px 0 0;font-size:12px;color:#d2d5ed}.layout{display:grid;grid-template-columns:.9fr 1.1fr;gap:22px}.card{background:linear-gradient(180deg,#121620,#0d1018);border:1px solid #242a39;border-radius:22px;padding:21px;box-shadow:0 24px 70px rgba(0,0,0,.24)}h2{margin:0 0 16px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.full{grid-column:1/-1}label{display:block;font-size:12px;font-weight:850;color:#dce0ed;margin:0 0 6px}input,select,textarea{width:100%;padding:12px 13px;border-radius:12px;border:1px solid #343a4d;background:#090c13;color:white;font:inherit}textarea{min-height:100px;resize:vertical}button{border:0;border-radius:12px;padding:11px 13px;background:#282e42;color:white;font-weight:800;cursor:pointer}button:disabled{opacity:.45;cursor:not-allowed}.primary{width:100%;padding:14px;background:linear-gradient(135deg,#7258ff,#d84fc7)}.auto{background:linear-gradient(135deg,#6f58ff,#b449d2)}.ok{background:#174c3b}.danger{background:#4b2028}.muted{font-size:12px;color:#8991a7;line-height:1.5}.status{margin-top:12px;background:#090c13;border:1px solid #272d3d;border-radius:12px;padding:12px;white-space:pre-wrap;color:#cad0e1;min-height:58px}.storyboard{display:grid;gap:10px;max-height:760px;overflow:auto}.scene{border:1px solid #292f40;border-radius:14px;padding:13px;background:#0a0d14}.scene .top{display:flex;justify-content:space-between;gap:10px}.scene b{font-size:12px}.scene p{font-size:12px;line-height:1.45;color:#929aaf;margin:9px 0}.scene button{font-size:11px;padding:7px 9px;margin:3px 5px 0 0}.meta{font-size:11px;color:#a38fff}.preview video{width:100%;margin-top:14px;border-radius:14px;background:#000}a{color:#bc9cff}.notice{border:1px solid #32384a;background:#101521;border-radius:14px;padding:14px;color:#b7bed2;margin:12px 0 18px;font-size:13px;line-height:1.5}.connect{display:grid;grid-template-columns:1fr auto auto;gap:8px;margin-top:10px}.modelhint{margin:6px 0 0;color:#8991a7;font-size:11px}.inline{display:flex;gap:8px;align-items:center}.inline select{flex:1}.small{padding:9px 11px;font-size:12px}.progressbox{margin-top:14px;border:1px solid #30364a;background:#0a0d14;border-radius:14px;padding:13px}.progresshead{display:flex;justify-content:space-between;gap:10px;align-items:center;font-size:12px}.progressstage{font-weight:850;color:#e8e9f4}.progressmeta{color:#9fa6ba;font-variant-numeric:tabular-nums}.track{height:11px;border-radius:999px;background:#1c2130;margin-top:10px;overflow:hidden}.fill{height:100%;width:0%;background:linear-gradient(90deg,#7258ff,#d84fc7);transition:width .35s ease}.progressdetail{font-size:11px;color:#929aaf;margin-top:8px;min-height:16px}@media(max-width:900px){.layout{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.full{grid-column:auto}.connect{grid-template-columns:1fr}.inline{align-items:stretch;flex-direction:column}}
</style></head>
<body><main class="shell"><section class="hero"><div class="eyebrow">Vercel control plane · render worker externo</div><h1>AI Music Video Studio</h1><p>Subí una canción y una foto/video. Vercel maneja la interfaz; tu worker ejecuta ComfyUI, FFmpeg, identidad, lip-sync y upscale.</p><span class="badge">Vercel</span><span class="badge">ComfyUI</span><span class="badge">Auto Pipeline</span><span class="badge" id="workerBadge">Worker: desconectado</span></section>
<div class="notice"><b>Conectar render worker</b><br>Iniciá el worker en tu Mac y pegá aquí la URL HTTPS de Cloudflare Tunnel. La URL se guarda solamente en este navegador.
<div class="connect"><input id="workerUrl" placeholder="https://xxxxx.trycloudflare.com"><button id="connectBtn" type="button">Conectar</button><button id="disconnectBtn" type="button" class="danger">Desconectar</button></div><div id="connectionHint" class="modelhint">También podés configurar RENDER_WORKER_URL en Vercel; el valor del navegador tiene prioridad.</div></div>
<div class="layout"><section class="card"><h2>Nuevo videoclip</h2><form id="form" class="grid"><div><label>Canción</label><input type="file" name="song" accept="audio/*" required></div><div><label>Foto o video</label><input type="file" name="visual" accept="image/*,video/*" required></div><div><label>Título</label><input name="title" placeholder="Mi videoclip"></div><div><label>Estilo</label><select name="style"><option value="cinematic rock">Cinematic Rock</option><option value="romantic film">Romántico</option><option value="urban night">Urbano nocturno</option><option value="live performance">Performance</option><option value="dreamlike surreal">Surreal / Dream</option></select></div><div><label>Formato</label><select name="aspect"><option>16:9</option><option>9:16</option></select></div><div><label>Calidad</label><select name="quality"><option value="preview" selected>Preview</option><option value="final">Final 1080p</option><option value="master">Master</option></select></div><div class="full"><label>Letra (opcional)</label><textarea name="lyrics" placeholder="Pegá la letra..."></textarea></div><div class="full"><label>Modelo / Checkpoint ComfyUI</label><div class="inline"><select id="checkpoint" disabled><option value="">Conectá el worker para ver modelos</option></select><button id="refreshModels" class="small" type="button" disabled>Actualizar modelos</button></div><p id="modelHint" class="modelhint">Los modelos se leen automáticamente desde CheckpointLoaderSimple.</p></div><div class="full"><button id="createBtn" class="primary" disabled>Crear proyecto en worker</button></div></form>
<div class="progressbox"><div class="progresshead"><span id="progressStage" class="progressstage">En espera</span><span id="progressMeta" class="progressmeta">0% · 00:00</span></div><div class="track"><div id="progressFill" class="fill"></div></div><div id="progressDetail" class="progressdetail">El progreso aparecerá aquí cuando comience una tarea.</div></div>
<div id="status" class="status">Conectá el worker para comenzar.</div><div id="preview" class="preview"></div></section><section class="card"><h2>Storyboard</h2><div id="storyboard" class="storyboard"><p class="muted">Creá un proyecto para ver las escenas.</p></div></section></div></main>
<script>
const SERVER_WORKER=__SERVER_WORKER__;
const f=document.querySelector('#form'),s=document.querySelector('#status'),sb=document.querySelector('#storyboard'),pv=document.querySelector('#preview'),cp=document.querySelector('#checkpoint'),badge=document.querySelector('#workerBadge'),modelHint=document.querySelector('#modelHint'),workerInput=document.querySelector('#workerUrl'),connectBtn=document.querySelector('#connectBtn'),disconnectBtn=document.querySelector('#disconnectBtn'),createBtn=document.querySelector('#createBtn'),refreshModels=document.querySelector('#refreshModels'),connectionHint=document.querySelector('#connectionHint'),progressStage=document.querySelector('#progressStage'),progressMeta=document.querySelector('#progressMeta'),progressFill=document.querySelector('#progressFill'),progressDetail=document.querySelector('#progressDetail');
let current=null,WORKER='';const running=new Set();let progressStarted=0,progressTimer=null,currentPct=0;
function esc(x){const d=document.createElement('div');d.textContent=String(x??'');return d.innerHTML}
function normalizeWorker(value){let v=String(value||'').trim();if(!v)return'';if(!/^https?:\/\//i.test(v))v='https://'+v;return v.replace(/\/+$/,'')}
function w(path){return WORKER+path}
function elapsed(){if(!progressStarted)return'00:00';const sec=Math.max(0,Math.floor((Date.now()-progressStarted)/1000));return String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%60).padStart(2,'0')}
function renderProgress(){progressFill.style.width=Math.max(0,Math.min(100,currentPct))+'%';progressMeta.textContent=Math.round(currentPct)+'% · '+elapsed()}
function beginProgress(stage,detail='',pct=0){progressStarted=Date.now();currentPct=pct;progressStage.textContent=stage;progressDetail.textContent=detail;clearInterval(progressTimer);progressTimer=setInterval(renderProgress,500);renderProgress()}
function setProgress(pct,stage,detail=''){currentPct=Math.max(currentPct,Math.min(100,pct));if(stage)progressStage.textContent=stage;if(detail)progressDetail.textContent=detail;renderProgress()}
function endProgress(stage='Completado',detail=''){currentPct=100;progressStage.textContent=stage;if(detail)progressDetail.textContent=detail;renderProgress();clearInterval(progressTimer);progressTimer=null}
function failProgress(detail){progressStage.textContent='Error';progressDetail.textContent=detail||'La tarea falló.';clearInterval(progressTimer);progressTimer=null;renderProgress()}
function resetModels(message='Conectá el worker para ver modelos'){cp.disabled=true;refreshModels.disabled=true;cp.innerHTML=`<option value="">${esc(message)}</option>`}
async function loadCheckpoints(){if(!WORKER){resetModels();return}cp.disabled=true;refreshModels.disabled=true;cp.innerHTML='<option value="">Cargando modelos…</option>';modelHint.textContent='Consultando CheckpointLoaderSimple en ComfyUI…';try{const r=await fetch(w('/api/comfyui/checkpoints'),{cache:'no-store'});const j=await r.json();if(!r.ok)throw Error(j.detail||j.error||'No se pudieron leer modelos');if(!j.online){resetModels('ComfyUI offline');modelHint.textContent=j.error||'El worker está online pero ComfyUI no responde.';refreshModels.disabled=false;return}const models=Array.isArray(j.checkpoints)?j.checkpoints:[];if(!models.length){resetModels('No hay checkpoints detectados');modelHint.textContent=j.error||'Colocá un checkpoint en ComfyUI/models/checkpoints.';refreshModels.disabled=false;return}cp.disabled=false;refreshModels.disabled=false;cp.innerHTML='<option value="">Elegí un modelo…</option>'+models.map(name=>`<option value="${esc(name)}">${esc(name)}</option>`).join('');if(models.length===1)cp.value=models[0];modelHint.textContent=`${models.length} modelo${models.length===1?'':'s'} detectado${models.length===1?'':'s'} en ComfyUI.`}catch(err){resetModels('Error cargando modelos');refreshModels.disabled=false;modelHint.textContent=err.message}}
async function connectWorker(silent=false){const candidate=normalizeWorker(workerInput.value||localStorage.getItem('renderWorkerUrl')||SERVER_WORKER);if(!candidate){WORKER='';badge.textContent='Worker: desconectado';createBtn.disabled=true;resetModels();if(!silent)s.textContent='Pegá la URL HTTPS del worker.';return false}workerInput.value=candidate;badge.textContent='Worker: conectando…';connectBtn.disabled=true;try{const r=await fetch(candidate+'/api/health',{cache:'no-store'});const j=await r.json();if(!r.ok||!j.ok)throw Error(j.detail||'Health check inválido');WORKER=candidate;localStorage.setItem('renderWorkerUrl',candidate);badge.textContent='Worker: online';createBtn.disabled=false;connectionHint.textContent=`Conectado a ${candidate}`;s.textContent=`Worker online · versión ${j.version||'n/d'}\nCargando modelos de ComfyUI…`;await loadCheckpoints();return true}catch(err){WORKER='';badge.textContent='Worker: offline';createBtn.disabled=true;resetModels('Worker offline');connectionHint.textContent='No se pudo conectar: '+err.message;if(!silent)s.textContent='No se pudo conectar al worker: '+err.message;return false}finally{connectBtn.disabled=false}}
function disconnectWorker(){WORKER='';localStorage.removeItem('renderWorkerUrl');workerInput.value='';badge.textContent='Worker: desconectado';createBtn.disabled=true;resetModels();modelHint.textContent='Los modelos se leen automáticamente desde CheckpointLoaderSimple.';connectionHint.textContent='Pegá una nueva URL del worker para volver a conectar.';s.textContent='Worker desconectado.'}
connectBtn.addEventListener('click',()=>connectWorker(false));disconnectBtn.addEventListener('click',disconnectWorker);refreshModels.addEventListener('click',loadCheckpoints);workerInput.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();connectWorker(false)}});
function createProject(){return new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST',w('/api/projects'));xhr.upload.onprogress=e=>{if(e.lengthComputable){const uploadPct=Math.min(30,(e.loaded/e.total)*30);setProgress(uploadPct,'Subiendo archivos',`${Math.round(e.loaded/1024/1024)} MB de ${Math.round(e.total/1024/1024)} MB`)}};xhr.upload.onload=()=>setProgress(35,'Procesando en el worker','Analizando audio, creando storyboard y render base…');xhr.onload=()=>{let j={};try{j=JSON.parse(xhr.responseText||'{}')}catch{}if(xhr.status>=200&&xhr.status<300)resolve(j);else reject(Error(j.detail||'Error del worker'))};xhr.onerror=()=>reject(Error('Se perdió la conexión con el worker'));xhr.send(new FormData(f))})}
f.addEventListener('submit',async e=>{e.preventDefault();if(!WORKER){s.textContent='Conectá el worker primero.';return}beginProgress('Preparando subida','Enviando canción y referencia directamente a tu Mac…',1);s.textContent='Procesando proyecto…';sb.innerHTML='';pv.innerHTML='';createBtn.disabled=true;try{const j=await createProject();current=j.id;endProgress('Proyecto listo',`${j.storyboard?.length||0} escenas creadas`);s.textContent=`Proyecto ${j.id}\nBPM: ${j.analysis?.bpm??'n/d'}\nDuración: ${Number(j.duration||0).toFixed(1)}s\nEscenas: ${j.storyboard?.length||0}`;draw(j.storyboard||[]);pv.innerHTML=`<video controls src="${w(j.video_url)}"></video><p><a href="${w(j.download_url)}" target="_blank">Descargar render base</a></p>`}catch(err){failProgress(err.message);s.textContent='Error: '+err.message}finally{createBtn.disabled=false}});
function draw(rows){sb.innerHTML=rows.map(x=>`<div class="scene"><div class="top"><b>ESCENA ${x.id} · ${x.start}s–${x.end}s</b><span class="meta">${x.status||'planned'}</span></div><p>${esc(x.lyrics||x.director_prompt||x.prompt)}</p><button class="auto" onclick="autoPipeline(${x.id})">✨ Auto Pipeline</button><button class="${x.approved?'ok':''}" onclick="approve(${x.id},${!x.approved})">${x.approved?'OK ✓':'Aprobar'}</button></div>`).join('')}
async function reload(){if(!current||!WORKER)return;const p=await fetch(w(`/api/projects/${current}`)).then(r=>r.json());draw(p.storyboard||[])}
function pipelineProgress(j){const last=(j.log||[]).slice(-1)[0]||{};const stage=last.stage||'';const state=j.auto_state||j.status||'';if(state==='ready_for_review')return[100,'Lista para revisar'];if(state==='failed'||state==='blocked')return[100,'Pipeline detenido'];if(stage==='upscale')return[90,'Upscale'];if(stage==='lipsync')return[78,'Lip-sync'];if(stage==='face_refine')return[65,'Refinando identidad'];if(state==='waiting_video'||stage==='video')return[50,'Generando video'];if(state==='waiting_image'||stage==='image')return[25,'Generando imagen'];if(stage==='prepare')return[10,'Preparando escena'];return[5,'Iniciando escena']}
async function autoPipeline(id){if(!current||running.has(id))return;if(!cp.value.trim()){s.textContent='Elegí primero un modelo/checkpoint de ComfyUI.';return}running.add(id);beginProgress(`Escena ${id}`,'Iniciando Auto Pipeline…',2);try{for(let i=0;i<900;i++){const r=await fetch(w(`/api/projects/${current}/scenes/${id}/auto-pipeline`),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({checkpoint:cp.value.trim(),fps:24,use_face_refine:true,mouth_mask:true,enhance_face:true,use_lipsync:true,use_upscale:true,upscale_scale:2,strict_optional:false})});const j=await r.json();if(!r.ok)throw Error(j.detail||JSON.stringify(j));const last=(j.log||[]).slice(-1)[0];const [pct,stage]=pipelineProgress(j);setProgress(pct,stage,last?(last.status+(last.detail?' · '+last.detail:'')):j.auto_state||'procesando');s.textContent=`Escena ${id}: ${j.auto_state||j.status}${last?'\n'+last.stage+': '+last.status+(last.detail?' — '+last.detail:''):''}`;await reload();if(j.auto_state==='ready_for_review'){endProgress('Escena lista para revisar',`Versión ${j.review_version||'-'}`);s.textContent=`Escena ${id} lista para revisar ✓\nVersión: ${j.review_version||'-'}`;return}if(j.auto_state==='blocked'||j.auto_state==='failed')throw Error(j.last_error||j.auto_state);await new Promise(r=>setTimeout(r,(j.auto_state==='waiting_video'||j.auto_state==='waiting_image')?2500:500))}throw Error('Seguimiento agotado; pulsá Auto Pipeline para reanudar.')}catch(err){failProgress(err.message);s.textContent='Auto Pipeline: '+err.message}finally{running.delete(id)}}
async function approve(id,value){if(!current||!WORKER)return;await fetch(w(`/api/projects/${current}/scenes/${id}`),{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved:value})});reload()}
workerInput.value=localStorage.getItem('renderWorkerUrl')||SERVER_WORKER||'';if(workerInput.value)connectWorker(true);
</script></body></html>'''


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return PAGE.replace("__SERVER_WORKER__", json.dumps(_worker_url()))
