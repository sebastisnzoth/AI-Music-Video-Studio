from __future__ import annotations


def enhance_page(page: str) -> str:
    """Inject the resumable one-click pipeline into the existing lightweight UI."""
    button_needle = '<button onclick="prepareScene(${x.id})">Preparar</button>'
    button_replacement = (
        '<button class="ai" onclick="autoPipeline(${x.id})">✨ Auto Pipeline</button>'
        + button_needle
    )
    if button_needle in page:
        page = page.replace(button_needle, button_replacement)

    auto_script = r'''
<script>
const autoRunning = new Set();
function sleepAuto(ms){return new Promise(resolve=>setTimeout(resolve,ms))}
async function autoPipeline(id){
  if(!current || autoRunning.has(id)) return;
  autoRunning.add(id);
  try{
    s.textContent=`Escena ${id}: iniciando Auto Pipeline…`;
    for(let attempt=0; attempt<900; attempt++){
      const r=await fetch(`/api/projects/${current}/scenes/${id}/auto-pipeline`,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({
          fps:24,
          use_face_refine:true,
          mouth_mask:true,
          enhance_face:true,
          use_lipsync:true,
          use_upscale:true,
          upscale_scale:2,
          strict_optional:false
        })
      });
      const j=await r.json();
      if(!r.ok){throw new Error(j.detail||JSON.stringify(j))}
      const last=(j.log||[]).slice(-1)[0];
      const detail=last?`\n${last.stage}: ${last.status}${last.detail?' — '+last.detail:''}`:'';
      s.textContent=`Escena ${id}: ${j.auto_state||j.status}${detail}`;
      await reload();
      if(j.auto_state==='ready_for_review'){
        s.textContent=`Escena ${id} lista para revisar ✓\nVersión: ${j.review_version||'-'}\n${j.review_candidate||''}`;
        return;
      }
      if(j.auto_state==='blocked' || j.auto_state==='failed'){
        throw new Error(j.last_error||`Pipeline ${j.auto_state}`);
      }
      await sleepAuto(j.auto_state==='waiting_video'?2500:400);
    }
    throw new Error('El Auto Pipeline superó el límite de seguimiento en el navegador. Podés pulsarlo otra vez para reanudar.');
  }catch(err){
    s.textContent=`Auto Pipeline escena ${id}: ${err.message}`;
  }finally{
    autoRunning.delete(id);
  }
}
</script>
'''
    if "</body>" in page and "function autoPipeline(id)" not in page:
        page = page.replace("</body>", auto_script + "</body>")
    return page
