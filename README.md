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

## Instalación (plug-and-play)

```bash
pip install "git+ssh://git@github.com/SeenkaMedia/django-agent.git@main"
```

En `settings.py`:

```python
INSTALLED_APPS += ["django_agent"]
MIDDLEWARE += ["django_agent.middleware.WidgetMiddleware"]   # inyecta el widget en el admin

AGENT_VERTEX_PROJECT = "infoxel-tagx"   # requerido
# Opcionales (defaults):
# AGENT_MODEL = "gemini-3.5-flash"
# AGENT_VERTEX_LOCATION = "us-central1"
# AGENT_STAFF_ONLY = True
# AGENT_PATH_PREFIX = "/admin"
```

En `urls.py`:

```python
path("agent/", include("django_agent.urls")),
```

```bash
python manage.py migrate
```

**Prerequisito de infra:** la service account de los pods necesita el rol `roles/aiplatform.user` en `infoxel-tagx` (ADC → Vertex). Sin eso el agente no puede hablar con Gemini.

Listo: el widget aparece abajo a la derecha en el admin para usuarios `is_staff`, con CRUD sobre los modelos registrados (respetando permisos) y confirmación + audit log en toda escritura.

## Tests (manuales)

No corren en CI; se invocan a mano:

```bash
python runtests.py            # rápidos, sin Vertex (deterministas, ~0.05s)
GOOGLE_APPLICATION_CREDENTIALS=/ruta/cred.json python runtests.py --live   # + Gemini real
```

Cubre: CRUD + permisos + serialización + resolución de FK (`test_registry`), búsqueda/lectura de código + denylist + traversal + redacción de secrets (`test_code_access`), loop del agente con Vertex mockeado — confirmación/audit/pending/lecturas (`test_agent`), y end-to-end contra Gemini real — function-calling, create+confirm, lectura de código (`test_live`, opt-in con `--live`).

## Estado

🚧 MVP implementado (rama `feat/mvp`). Pendiente: validación end-to-end (instalar en panelists + rol de Vertex) y tests con mock del cliente Vertex.

### Componentes
| Archivo | Qué hace |
|---|---|
| `registry.py` | CRUD genérico sobre modelos del admin + permisos + schemas |
| `vertex.py` | Cliente Gemini/Vertex + declaración de funciones |
| `agent.py` | Loop de function-calling + confirmación + audit |
| `views.py` / `urls.py` | Endpoints `history` / `message` / `confirm` |
| `middleware.py` | Inyecta el widget en el admin |
| `static/.../widget.{js,css}` | Widget flotante (vanilla) |
| `models.py` | `Conversation` / `Message` / `ActionLog` |
