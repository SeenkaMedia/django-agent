# Architecture

django-agent is a single Django app. Everything runs **in-process** inside your
project; the only network hop is to Vertex AI.

```
Browser (any admin page)
  └─ widget.js  ── reads page context, renders history & confirmations
        │  GET /agent/history   POST /agent/message   /agent/confirm   /agent/reset
        ▼
django_agent (in-process)
  views ─► agent (AgentService) ─► vertex (Gemini, function calling)
              │
              ├─ registry      CRUD over admin-registered models · Django permissions
              ├─ code_access   optional read-only source tools (sandboxed)
              ├─ confirmation + audit (ActionLog)
              └─ Conversation / Message (persistence)
                          │  ADC (service account)
                          ▼
                   Vertex AI · Gemini
```

## Why in-process (a package, not a service)

The defining feature is that the agent **acts on your data with the logged-in user's
permissions**. In-process that is trivial: direct ORM access, Django permission
checks, page context in the same request, and the existing session for auth. As an
external service it would require exposing per-app APIs or sharing databases, and
cross-service auth/permissions become a distributed problem.

## Request flow

1. The widget loads history (`GET /agent/history`) and sends each message with the
   current page context (`POST /agent/message`).
2. `agent` builds the prompt (instructions + page context + available models) and the
   function declarations the user is allowed to use, then calls Gemini.
3. Gemini replies with text or a function call. **Reads** (`query`, `get`,
   `describe_models`, and the code tools) run inline and loop back to the model.
   **Writes** (`create`, `update`, `delete`) pause and return a confirmation preview.
4. On `POST /agent/confirm`, the pending write runs with the user's permissions, is
   recorded in the audit log, and the model produces the final reply.
5. Every turn (user, model, tool) is persisted, so the conversation survives reloads.

## Model registry

`registry` discovers models from `admin.site._registry` — what is registered in the
admin is what the assistant can see. Field schemas come from each model's `_meta`.
Generic operations (`query`/`get`/`create`/`update`/`delete`) take the model label as
a parameter, so the interface scales to any number of models without per-model code.
Each operation checks the corresponding Django permission
(`view`/`add`/`change`/`delete`) against the request user.

## Gemini on Vertex AI

The backend uses the `google-genai` client with the Vertex AI backend, authenticated
through Application Default Credentials — no API keys. Gemini 3.x requires a
`thought_signature` on function-call parts when the history is replayed; the agent
captures, stores and re-attaches it.

## Security model

- Django permissions per operation; tools the user cannot use are not offered.
- Mandatory confirmation on a concrete preview before any write.
- Audit log of every executed write.
- Staff-only widget by default.
- Optional code access is read-only, sandboxed to `AGENT_CODE_ROOT`, blocks path
  traversal, redacts secret-looking lines, and is disabled by default.
