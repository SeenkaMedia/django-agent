"""Settings con defaults; se sobrescriben con AGENT_* en el settings del proyecto."""
from django.conf import settings


def _get(name, default):
    return getattr(settings, f"AGENT_{name}", default)


def model():
    return _get("MODEL", "gemini-3.5-flash")


def project():
    return _get("VERTEX_PROJECT", None)


def location():
    return _get("VERTEX_LOCATION", "us-central1")


def temperature():
    return _get("TEMPERATURE", 0.2)


def max_steps():
    return _get("MAX_STEPS", 8)


def staff_only():
    return _get("STAFF_ONLY", True)


def path_prefix():
    return _get("PATH_PREFIX", "/admin")

