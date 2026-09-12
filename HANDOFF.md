# HANDOFF.md — Estado operativo persistente

Este archivo es la memoria corta entre sesiones de Codex/GPT.

Reglas:
- mantenerlo breve y actualizado;
- registrar solo estado comprobable;
- usar los estados definidos en `CODEX.md`;
- cada sesión debe dejar un `NEXT` accionable.

## Estado actual

### BLOCKED — Worker público estable

**Objetivo:** que Vercel pueda comunicarse con el render worker mediante una URL estable.

**Estado real:**
- el control plane Vercel existe y responde;
- se eliminó del repo la URL temporal hardcodeada de `trycloudflare.com`;
- el worker necesita una URL pública estable configurada vía `RENDER_WORKER_URL`;
- la solución prevista es Cloudflare Named Tunnel;
- para completarlo hace falta una credencial/token de Cloudflare y el worker local encendido.

**Bloqueo externo:** credencial/token del Named Tunnel + proceso worker disponible.

**No bloquear por esto otros P0 independientes.**

### IMPLEMENTED — Contrato worker v1

**Hecho:**
- `app/worker_contract.py`;
- `/api/v1/health`;
- `/api/v1/capabilities`;
- `/api/v1/comfyui/checkpoints`;
- `X-Request-ID`;
- `X-Worker-Version`;
- errores estructurados para ComfyUI no disponible.

**Pendiente de validación:** revisar que las rutas anunciadas en `capabilities` coincidan exactamente con las rutas reales o crear aliases estables.

### IMPLEMENTED — CI y tests básicos

**Hecho:**
- `requirements-dev.txt`;
- `tests/test_worker_contract.py`;
- `.github/workflows/ci.yml`.

**Pendiente:** confirmar workflow de GitHub Actions y corregir cualquier fallo real.

### IMPLEMENTED — Configuración deploy sin URL temporal

**Hecho:**
- `vercel.json` sin `RENDER_WORKER_URL` hardcodeada;
- `APP_VERSION` actualizado;
- `scripts/start-stable-tunnel.sh` para Named Tunnel.

**Pendiente:** configurar `RENDER_WORKER_URL` en Vercel cuando exista URL estable.

## NEXT

### P0-1 — Validar CI y contrato publicado

1. revisar el workflow CI más reciente;
2. corregir fallos si existen;
3. comparar `app/worker_contract.py` con las rutas reales de `pipeline_api.py`;
4. corregir las rutas anunciadas o crear aliases compatibles;
5. agregar tests contractuales para impedir nueva divergencia;
6. mover a `VALIDATED` solo con evidencia.

### P0-2 — Persistencia atómica

Después de P0-1:

1. inspeccionar `save_json`/persistencia en `app/pipeline.py`;
2. implementar escritura atómica con archivo temporal + replace si todavía no existe;
3. probar que una escritura interrumpida no corrompa `project.json`;
4. mantener compatibilidad del formato actual.

### P0-3 — Jobs idempotentes y recuperables

Después de P0-2:

1. asignar `job_id` estable;
2. soportar `Idempotency-Key` en inicio de generación;
3. persistir estado del job en `project.json`;
4. evitar duplicar generación por retry;
5. permitir recuperar estado después de refresh/restart;
6. agregar tests de duplicate/retry/reload.

## Últimos commits relevantes

- `f64669daf27379644f0ecb9117441e6836404ddf` — agrega `CODEX.md`.
- `6a76ee8239490a591f4da746f82f9db190609bf6` — CI GitHub Actions.
- `35e90caf9e65da4c3a3dffc4e60f00dbb121fa13` — script de Named Tunnel estable.
- `a70b845e87061333651e29d83139fd8563555ea6` — elimina worker URL temporal de `vercel.json`.
- `65c25d4131e5fb4c57edf9d8824cb7aff3df6abb` — tests de contrato worker.
- `ddff81ffdeb1089eba1f05ec263d1e245718fbbb` — dependencias de desarrollo.

## Comando humano mínimo

Una vez que este protocolo existe, el usuario no debería necesitar reenviar contexto técnico extenso.

Prompt recomendado para Codex:

```text
Seguí con los P0 según AGENTS.md, CODEX.md y HANDOFF.md. Trabajá de forma autónoma y frená solo ante los bloqueos críticos definidos ahí.
```
