# AGENTS.md — AI Music Video Studio

Este archivo define cómo deben trabajar Codex/GPT/otros agentes dentro de este repositorio.

## Autoridad

Documento maestro: `CTO_MASTER.md`.

Protocolo operativo de Codex: `CODEX.md`.

Estado persistente entre sesiones: `HANDOFF.md`.

Antes de modificar arquitectura, pipeline o despliegue, leer:

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
- `AGENTS.md` define reglas, prioridades y límites;
- `CODEX.md` define el protocolo de ejecución autónoma;
- `HANDOFF.md` define el punto exacto donde continuar.

## Modo de trabajo

Trabajar de forma autónoma sobre `main` cuando el usuario lo pida explícitamente.

No detenerse a pedir autorización por cada archivo. Resolver primero los P0 y continuar con P1 cuando no existan bloqueos críticos.

Pregunta operativa obligatoria:

> ¿Qué impide hoy que esto produzca un videoclip real de punta a punta?

La respuesta determina la siguiente tarea.

Cuando el usuario indique simplemente que se continúe según `AGENTS.md`, `CODEX.md` o `HANDOFF.md`, no reconstruir el plan desde cero: leer el estado persistido, verificarlo contra el repo y continuar desde el primer `NEXT` válido.

## Orden de prioridad

```text
P0 funcionamiento real
P1 calidad y confiabilidad
P2 experiencia de producto
P3 escala/monetización
```

No saltar a P2/P3 si un P0 bloquea el flujo real.

## Routing de Skills

Usar las Skills especializadas:

- `studio-cto` → orquestación, arquitectura y prioridades.
- `render-worker` → ComfyUI, GPU, worker, jobs y capacidades.
- `music-video-pipeline` → audio, storyboard, escenas, identidad, lip-sync y assembly.
- `studio-qa` → tests, contratos, regresiones y smoke tests.
- `studio-deploy` → Vercel, variables de entorno, networking, seguridad y observabilidad.

Si una tarea cruza varias áreas, `studio-cto` coordina y las demás ejecutan por dominio.

## Reglas técnicas

### Mantener separación Control Plane / Worker

Vercel coordina. El worker renderiza.

No introducir cargas GPU, FFmpeg pesado o generación larga dentro de funciones serverless de Vercel.

### Idempotencia

Todo endpoint que inicia generación debe poder reintentarse sin duplicar resultados destructivamente.

### Persistencia

Nunca asumir que memoria RAM, proceso Python, navegador o filesystem temporal van a sobrevivir.

### API

Preferir respuestas estructuradas y estados explícitos. No usar parsing de mensajes de error como lógica de negocio.

### Uploads

Validar tipo, tamaño y path. Nunca confiar en el nombre enviado por el cliente.

### Secretos

Nunca commitear tokens, credenciales o URLs privadas sensibles.

### Dependencias

El core debe seguir siendo gratuito/local. Una integración paga puede existir solo como opcional y nunca reemplazar silenciosamente el camino gratuito.

## Política de preguntas

NO preguntar por:
- nombres internos;
- estructura de carpetas;
- pequeños refactors;
- tests;
- manejo de errores;
- logging;
- validaciones;
- implementación de P0/P1 ya definidos.

Preguntar solamente cuando la decisión:
- genere costo;
- borre datos;
- cambie el producto;
- reemplace el backend principal;
- requiera claves/servicios que el usuario deba contratar;
- implique una decisión irreversible o de seguridad relevante;
- requiera una acción de producción irreversible.

## Ciclo autónomo

Por cada iteración:

1. leer `HANDOFF.md`;
2. inspeccionar estado actual y validar que el handoff siga siendo cierto;
3. identificar el bloqueo más importante;
4. tomar el primer `NEXT` válido o reemplazarlo por un P0 más crítico si la evidencia cambió;
5. implementar cambio mínimo suficiente;
6. ejecutar/verificar tests disponibles;
7. agregar test si falta cobertura del cambio;
8. revisar seguridad/regresión;
9. actualizar `HANDOFF.md` con estado y evidencia;
10. documentar roadmap/audit solo si cambió el estado real;
11. commitear;
12. continuar con el siguiente P0.

No dejar un trabajo activo sin actualizar `HANDOFF.md`.

## Estados obligatorios de handoff

Usar los estados definidos en `CODEX.md`:

- `NEXT`
- `IN PROGRESS`
- `IMPLEMENTED`
- `VALIDATED`
- `RELEASED`
- `BLOCKED`

No marcar `VALIDATED` sin pruebas/verificación. No marcar `RELEASED` solo porque existe un commit o un deploy automático.

## Criterio para crear nuevas Skills

No crear agentes/Skills por cantidad.

Crear una nueva Skill solo si:
- existe un dominio repetitivo claramente separado;
- reduce errores o contexto;
- necesita checklist propio;
- será reutilizada en varias tareas.

## Estado inicial conocido

El repositorio ya contiene un pipeline local amplio, adapters para ComfyUI/LocalAI y una UI Vercel de control.

Problema operativo prioritario: la conectividad y estabilidad del render worker, seguida por contratos API, persistencia/reanudación y tests automatizados.

El estado operativo actualizado debe consultarse en `HANDOFF.md`; esta sección no reemplaza al handoff.

## Entrega

Al finalizar un bloque de trabajo:
- actualizar `HANDOFF.md`;
- informar qué se cambió;
- informar qué se verificó;
- indicar qué P0 sigue;
- indicar bloqueos reales, si existen.

No reportar como terminado algo que solo quedó documentado si el pedido era implementarlo.
