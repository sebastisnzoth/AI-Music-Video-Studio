# AGENTS.md — AI Music Video Studio

Este archivo define cómo deben trabajar Codex/GPT/otros agentes dentro de este repositorio.

## Autoridad

Documento maestro: `CTO_MASTER.md`.

Antes de modificar arquitectura, pipeline o despliegue, leer:

1. `CTO_MASTER.md`
2. `README.md`
3. `docs/REPO_ASSESSMENT.md`
4. los `SKILL.md` aplicables bajo `.agents/skills/`

## Modo de trabajo

Trabajar de forma autónoma sobre `main` cuando el usuario lo pida explícitamente.

No detenerse a pedir autorización por cada archivo. Resolver primero los P0 y continuar con P1 cuando no existan bloqueos críticos.

Pregunta operativa obligatoria:

> ¿Qué impide hoy que esto produzca un videoclip real de punta a punta?

La respuesta determina la siguiente tarea.

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
- implique una decisión irreversible o de seguridad relevante.

## Ciclo autónomo

Por cada iteración:

1. inspeccionar estado actual;
2. identificar bloqueo más importante;
3. implementar cambio mínimo suficiente;
4. ejecutar/verificar tests disponibles;
5. agregar test si falta cobertura del cambio;
6. revisar seguridad/regresión;
7. documentar solo lo necesario;
8. continuar con el siguiente P0.

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

## Entrega

Al finalizar un bloque de trabajo informar:
- qué se cambió;
- qué se verificó;
- qué P0 sigue;
- bloqueos reales, si existen.

No reportar como terminado algo que solo quedó documentado si el pedido era implementarlo.
