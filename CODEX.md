# CODEX.md — Protocolo operativo autónomo

Este archivo define cómo debe trabajar Codex dentro de este repositorio sin depender de prompts largos.

## Fuente de autoridad

Leer siempre, en este orden:

1. `CTO_MASTER.md`
2. `AGENTS.md`
3. `CODEX.md`
4. `HANDOFF.md`
5. `README.md`
6. `docs/REPO_ASSESSMENT.md`
7. `docs/CTO_AUDIT_2026-09-12.md`
8. los `SKILL.md` aplicables bajo `.agents/skills/`

Si hay conflicto:
- `CTO_MASTER.md` define objetivo y arquitectura;
- `AGENTS.md` define reglas y prioridades;
- `CODEX.md` define cómo ejecutar;
- `HANDOFF.md` define dónde continuar ahora.

## Modo de ejecución

Cuando el usuario diga algo equivalente a:

> seguí con los P0 según `AGENTS.md` y `CODEX.md`

Codex debe:

1. inspeccionar `HANDOFF.md`;
2. revisar el estado real del repo, tests, CI y deploy relevante;
3. tomar el primer item `NEXT` o el bloqueo P0 más importante;
4. moverlo a `IN PROGRESS` antes de trabajar si corresponde;
5. implementar el cambio mínimo suficiente;
6. ejecutar tests/verificaciones aplicables;
7. corregir regresiones encontradas;
8. actualizar `HANDOFF.md` con evidencia;
9. actualizar roadmap/audit solo si cambió el estado real;
10. commitear con mensaje claro;
11. continuar con el siguiente P0 mientras no exista un bloqueo real.

No pedir confirmación entre pasos normales.

## Política de autonomía

Codex puede decidir y ejecutar sin preguntar:
- refactors pequeños y medianos;
- tests;
- validaciones;
- manejo de errores;
- logging/observabilidad;
- contratos internos compatibles;
- documentación operativa;
- correcciones de build/CI;
- implementación P0/P1 ya aprobada por `AGENTS.md`;
- creación/modificación de archivos necesarios para completar el P0;
- commits en `main` cuando el usuario haya pedido explícitamente trabajar de forma autónoma en `main`.

Codex debe frenar y pedir decisión únicamente si aparece alguno de estos casos:
- costo nuevo o servicio pago obligatorio;
- compra o contratación;
- credenciales/tokens que el usuario deba crear o entregar;
- borrado irreversible de datos;
- cambio de proveedor principal;
- cambio incompatible de API pública;
- cambio del objetivo central del producto;
- acción de producción irreversible o de seguridad sensible;
- publicación/release que requiera una decisión comercial explícita.

## Regla del P0

Antes de cada bloque de trabajo responder internamente:

> ¿Qué impide hoy que una persona real suba una canción, una referencia visual y obtenga un videoclip terminado sin intervención técnica?

Trabajar primero sobre el impedimento más cercano al happy path real.

No abrir frentes P2/P3 mientras exista un P0 que bloquee producto usable.

## Estados de trabajo

Usar exclusivamente estos estados en `HANDOFF.md`:

- `NEXT` — listo para tomar.
- `IN PROGRESS` — trabajo activo.
- `IMPLEMENTED` — código terminado pero todavía no suficientemente validado.
- `VALIDATED` — pruebas/verificaciones relevantes pasaron.
- `RELEASED` — cambio desplegado/liberado y verificado en el entorno objetivo.
- `BLOCKED` — existe una dependencia externa real.

No marcar `VALIDATED` sin evidencia. No marcar `RELEASED` solamente porque hubo commit o deploy automático.

## Handoff obligatorio

Antes de terminar una sesión, actualizar `HANDOFF.md` con:
- tarea actual;
- estado;
- último commit relevante;
- archivos principales tocados;
- pruebas ejecutadas y resultado;
- deploy verificado o no;
- bloqueo real, si existe;
- `NEXT` exacto para el siguiente agente/sesión.

El `NEXT` debe ser accionable y específico. Evitar frases vagas como “seguir mejorando”.

## Commits

Preferir commits pequeños, coherentes y trazables.

Formato recomendado:

```text
fix(scope): descripción
feat(scope): descripción
test(scope): descripción
refactor(scope): descripción
docs(scope): descripción
chore(scope): descripción
```

No mezclar cambios no relacionados si pueden separarse con bajo riesgo.

## Verificación mínima por tipo de cambio

### Backend/API
- import/build;
- tests unitarios/contractuales relevantes;
- respuesta/error estructurado;
- compatibilidad con cliente existente.

### Worker/render
- health/capabilities;
- job/status;
- idempotencia;
- persistencia/reanudación;
- fallo claro si dependencia externa no está disponible.

### Vercel/control plane
- build/deploy;
- endpoint de health;
- worker configured/online/offline correctamente distinguido;
- no secretos hardcodeados.

### Pipeline
- estado persistido;
- escena regenerable sin perder aprobadas;
- audio original preservado en assembly;
- error recuperable y visible.

## Regla de bloqueo externo

Si falta una credencial, token, servicio local encendido o recurso que Codex no puede crear por sí mismo:

1. marcar ese item `BLOCKED` en `HANDOFF.md`;
2. dejar instrucciones exactas y mínimas para destrabarlo;
3. continuar con otros P0 independientes si existen;
4. no detener todo el proyecto por un único bloqueo externo.

## Cierre de sesión

El resumen final debe contener solo información operativa útil:
- qué quedó implementado;
- qué quedó validado;
- qué quedó released;
- qué está blocked;
- cuál es el siguiente `NEXT`.

El repo debe contener suficiente contexto para que otra sesión de Codex continúe sin necesitar reconstruir la conversación anterior.
