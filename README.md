# django-agent

Asistente LLM embebible para los admin/apps Django de Seenka. Es un **paquete reutilizable** (Django app): se agrega a `INSTALLED_APPS` de cualquier servicio y aparece un **widget de chat flotante** abajo a la derecha, con un agente que entiende la página actual, recuerda la conversación y puede **ejecutar acciones** sobre los datos de la app.

## Por qué paquete y no servicio externo

La feature central es que el agente **ejecute acciones** sobre los modelos de cada app con **los permisos del usuario logueado**. In-process eso es trivial (ORM, admin y permisos directos, page-context en el mismo request, auth = sesión Django). Como servicio externo habría que exponer APIs por app o dar acceso a DBs ajenas, y la auth/permisos entre servicios se vuelven un problema distribuido.

→ **El agente vive in-process (paquete).** Si más adelante se quiere **memoria/conocimiento compartidos entre apps**, se externaliza solo el *storage* (una DB o mini-backend), no la ejecución.

## Requisitos y cómo se resuelve cada uno

| Requisito | Mecanismo |
|---|---|
| Widget abajo a la derecha en toda página | JS/CSS livianos inyectados vía context processor / base template |
| Reutilizable en toda app Django | Paquete pip + `INSTALLED_APPS` + include de URLs |
| Sabe en qué página estamos | El widget manda URL + vista resuelta + objeto en edición con cada mensaje |
| Estado no se pierde al navegar/recargar | Conversación server-side (`Conversation`/`Message` por usuario); el widget trae el historial en cada carga |
| Cargar contexto al bot | Store de conocimiento por app inyectado al system prompt; RAG/embeddings si crece |
| Que vaya aprendiendo | Memoria persistente de hechos + feedback (👍/👎) recuperado en cada turno |
| Que ejecute acciones | Tools registradas por app, con **permisos + confirmación explícita + audit log** |

## Seguridad (no negociable)

Un agente que escribe en la DB necesita barandas desde el día uno:
- Permisos por usuario (las tools respetan los permisos Django del request).
- **Confirmación explícita** antes de cualquier escritura.
- **Audit log** de toda acción ejecutada.

## Roadmap

1. **MVP** — widget + persistencia + page-context + backend Claude API + tool `crear_cuentas` (caso real de panelists).
2. **Conocimiento** — store de contexto por app + recuperación.
3. **Aprendizaje** — memoria de hechos + feedback.

## Backend LLM

Claude API (tool-use nativo y confiable para acciones). Alternativa evaluada: LLM interno del cluster (`llm-service`), descartado para v1 por menor fiabilidad del tool-use.

## Estado

🚧 Diseño. Sin código todavía — ver roadmap.
