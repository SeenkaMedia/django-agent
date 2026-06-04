# django-agent

[![CI](https://github.com/SeenkaMedia/django-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/SeenkaMedia/django-agent/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/django-4.2%2B-092E20.svg)](https://www.djangoproject.com/)

An embeddable LLM assistant for the Django admin. Drop it into any project and a
floating chat widget appears in the admin: a Gemini-powered agent that understands
the page you are on, remembers the conversation, and can **act on your data** —
create, read, update and delete records across your registered models, always with
the logged-in user's permissions and an explicit confirmation step.

> Built and maintained by [Seenka](https://seenka.com). Licensed under Apache-2.0.

## Why

Most "AI in the admin" tools are read-only chatbots, or they require you to wire a
tool per model. `django-agent` is **plug-and-play**: it derives a generic CRUD
interface from the models you already registered in the admin, so the assistant can
operate on any of them out of the box — gated by Django permissions, a per-write
confirmation card, and an audit log.

## Features

- **Floating chat widget** injected into the admin (no template changes required).
- **Automatic CRUD** over admin-registered models — no per-model tool definitions.
- **Permission-aware**: every operation is checked against the user's Django
  permissions (`view`/`add`/`change`/`delete`).
- **Confirmation + audit**: every write shows a preview the user must confirm, and is
  recorded in an audit log.
- **Page-aware**: the assistant knows which page/model the user is looking at.
- **Persistent conversation**: stored server-side, survives navigation and reloads.
- **Optional source-code access**: read-only, sandboxed `search`/`read` tools so the
  assistant can explain how your code works (off by default).
- **Backed by Gemini on Vertex AI**, authenticated via Application Default
  Credentials — no API keys to manage.

## Requirements

- Python 3.10+
- Django 4.2+
- A Google Cloud project with Vertex AI enabled, and credentials available through
  [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
  (e.g. `GOOGLE_APPLICATION_CREDENTIALS`).

## Installation

```bash
pip install django-agent
```

Or directly from source:

```bash
pip install "git+https://github.com/SeenkaMedia/django-agent.git@main"
```

## Quick start

In `settings.py`:

```python
INSTALLED_APPS += ["django_agent"]
MIDDLEWARE += ["django_agent.middleware.WidgetMiddleware"]  # injects the widget

AGENT_VERTEX_PROJECT = "your-gcp-project"   # required
```

In your root `urls.py`:

```python
path("agent/", include("django_agent.urls")),
```

Then:

```bash
python manage.py migrate
```

That's it. Staff users now see the assistant in the bottom-right of the admin, with
CRUD over the registered models (respecting permissions) plus confirmation and audit
logging on every write.

## Configuration

All settings are optional except `AGENT_VERTEX_PROJECT`.

| Setting | Default | Description |
|---|---|---|
| `AGENT_VERTEX_PROJECT` | _(required)_ | Google Cloud project ID for Vertex AI. |
| `AGENT_VERTEX_LOCATION` | `"global"` | Vertex AI location. |
| `AGENT_MODEL` | `"gemini-3.5-flash"` | Gemini model name. |
| `AGENT_TEMPERATURE` | `0.2` | Sampling temperature. |
| `AGENT_MAX_STEPS` | `8` | Max tool-calling steps per turn. |
| `AGENT_STAFF_ONLY` | `True` | Show the widget only to `is_staff` users. |
| `AGENT_PATH_PREFIX` | `"/admin"` | URL prefix where the widget is injected. |
| `AGENT_CODE_ENABLED` | `False` | Enable read-only source-code access tools. |
| `AGENT_CODE_ROOT` | `""` | Repository root the code tools may read. |
| `AGENT_CODE_DENY` | _(built-in)_ | Glob denylist for the code tools. |

## How it works

1. The widget sends each message — plus the current page context — to the backend.
2. The agent exposes a small set of generic functions to the model (`describe_models`,
   `query`, `get`, `create`, `update`, `delete`), discovered from
   `admin.site._registry`. Field schemas are derived from each model's metadata.
3. The model calls functions; **reads** run inline, **writes** pause and return a
   confirmation card with a preview (and a diff for updates).
4. On confirmation, the operation runs with the user's permissions and is written to
   the audit log.

## Security

The assistant can modify data, so it is built around explicit guardrails:

- **Django permissions** are enforced per operation; tools the user can't use are not
  even offered to the model.
- **Every write requires confirmation** from the user on a concrete preview.
- **Audit log**: every executed write records the user, tool, arguments and result.
- **Staff-only** by default.
- The optional **code-access** tools are read-only, sandboxed to `AGENT_CODE_ROOT`,
  block path traversal, and redact lines that look like secrets — and are **off by
  default**.

See [SECURITY.md](SECURITY.md) to report a vulnerability.

## Development

```bash
git clone https://github.com/SeenkaMedia/django-agent.git
cd django-agent
pip install -e .
python runtests.py            # fast suite (no network)
python runtests.py --live     # also runs tests against real Gemini
```

Live tests need `GOOGLE_APPLICATION_CREDENTIALS` and `AGENT_VERTEX_PROJECT` set.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Licensed under the [Apache License 2.0](LICENSE). Copyright Seenka. When
redistributing, you must retain the copyright and the [NOTICE](NOTICE) attributing
Seenka as the original author, as required by the license.
