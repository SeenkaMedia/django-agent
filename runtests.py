#!/usr/bin/env python
# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Manual test suite for django-agent.

    python runtests.py            # fast, no Vertex (deterministic)
    python runtests.py --live     # + tests against real Gemini

Live tests require GOOGLE_APPLICATION_CREDENTIALS and AGENT_VERTEX_PROJECT to be
set in the environment, and google-genai installed.
"""
import os
import sys

import django
from django.conf import settings

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    sys.path.insert(0, ROOT)
    live = "--live" in sys.argv
    if live:
        os.environ["AGENT_LIVE_TESTS"] = "1"
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test",
        INSTALLED_APPS=[
            "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.admin",
            "django.contrib.sessions", "django.contrib.messages", "django_agent",
        ],
        DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
        DEFAULT_AUTO_FIELD="django.db.models.BigAutoField",
        USE_TZ=True,
        MIDDLEWARE=[
            "django.contrib.sessions.middleware.SessionMiddleware",
            "django.contrib.auth.middleware.AuthenticationMiddleware",
            "django.contrib.messages.middleware.MessageMiddleware",
        ],
        TEMPLATES=[{
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {"context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]},
        }],
        AGENT_VERTEX_PROJECT=os.environ.get("AGENT_VERTEX_PROJECT"),
        AGENT_MODEL=os.environ.get("AGENT_MODEL", "gemini-3.5-flash"),
        AGENT_CODE_ENABLED=True,
        AGENT_CODE_ROOT=ROOT,
    )
    django.setup()
    from django.test.utils import get_runner
    runner = get_runner(settings)(verbosity=2)
    sys.exit(1 if runner.run_tests(["tests"]) else 0)


if __name__ == "__main__":
    main()
