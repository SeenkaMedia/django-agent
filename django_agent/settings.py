# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Settings with defaults; override them with AGENT_* in the project's settings."""
from django.conf import settings


def _get(name, default):
    return getattr(settings, f"AGENT_{name}", default)


def model():
    return _get("MODEL", "gemini-3.5-flash")


def project():
    return _get("VERTEX_PROJECT", None)


def location():
    return _get("VERTEX_LOCATION", "global")  # gemini-3.5-flash lives in global


def temperature():
    return _get("TEMPERATURE", 0.2)


def max_steps():
    return _get("MAX_STEPS", 8)


def staff_only():
    return _get("STAFF_ONLY", True)


def path_prefix():
    return _get("PATH_PREFIX", "/admin")


def code_enabled():
    return _get("CODE_ENABLED", False)


def code_root():
    return _get("CODE_ROOT", "")


def code_deny():
    return _get("CODE_DENY", None)

