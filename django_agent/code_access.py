"""Acceso read-only y acotado al código: search / outline / read.

Confinado a AGENT_CODE_ROOT, con denylist, redacción de líneas con secrets y topes.
Trae solo la porción que el agente necesita, nunca el repo entero.
"""
import ast
import fnmatch
import os
import re

from . import settings as S

DENY_DEFAULT = ["*.env", ".env", "*secret*", "*credential*", "*.key", "*.pem",
                "*/settings/*", "settings/*", "*.sqlite3", "*.pyc", "*/.git/*"]
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".idea", ".vscode"}
SECRET_LINE = re.compile(r"(?i)(secret|password|passwd|api[_-]?key|token|authorization|private[_-]?key)\s*[:=]")
MAX_BYTES = 20000
MAX_MATCHES = 40

FUNCTIONS = [
    {"name": "search_code", "description": "Busca texto en el código del proyecto. Devuelve archivo:línea + snippet (no archivos enteros).",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string"}, "glob": {"type": "string", "description": "patrón de archivos, ej *.py"}},
         "required": ["query"]}},
    {"name": "outline", "description": "Estructura (funciones/clases con rangos de línea) de un archivo Python, para saber qué leer.",
     "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "read_file", "description": "Lee SOLO un rango de líneas de un archivo del proyecto.",
     "parameters": {"type": "object", "properties": {
         "path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "required": ["path"]}},
]


def _root():
    return os.path.realpath(S.code_root())


def _deny():
    return S.code_deny() or DENY_DEFAULT


def _blocked(rel):
    return any(fnmatch.fnmatch(rel, p) for p in _deny())


def _match(rel, glob):
    return (fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(rel, "*" + glob)
            or fnmatch.fnmatch(os.path.basename(rel), glob))


def _safe(path):
    full = os.path.realpath(os.path.join(_root(), path))
    if not (full == _root() or full.startswith(_root() + os.sep)):
        raise ValueError("path fuera del root permitido")
    rel = os.path.relpath(full, _root())
    if _blocked(rel):
        raise ValueError("path bloqueado por la denylist")
    return full, rel


def _scrub(line):
    return "‹línea con secreto redactada›" if SECRET_LINE.search(line) else line


def search_code(query, glob="*.py"):
    root, hits = _root(), []
    needle = query.lower()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            if not _match(rel, glob) or _blocked(rel):
                continue
            hits += _scan(os.path.join(dirpath, name), rel, needle, MAX_MATCHES - len(hits))
            if len(hits) >= MAX_MATCHES:
                return {"matches": hits, "truncated": True}
    return {"matches": hits, "truncated": False}


def _scan(full, rel, needle, remaining):
    out = []
    try:
        for i, line in enumerate(open(full, encoding="utf-8", errors="ignore"), 1):
            if needle in line.lower():
                out.append({"file": rel, "line": i, "text": _scrub(line.rstrip())[:200]})
                if len(out) >= remaining:
                    break
    except OSError:
        pass
    return out


def outline(path):
    full, rel = _safe(path)
    src = open(full, encoding="utf-8", errors="ignore").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return {"file": rel, "symbols": [], "note": "no es Python parseable"}
    syms = [{"kind": type(n).__name__.replace("Def", "").lower(), "name": n.name,
             "start": n.lineno, "end": getattr(n, "end_lineno", n.lineno)}
            for n in ast.walk(tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    return {"file": rel, "symbols": sorted(syms, key=lambda s: s["start"])}


def read_file(path, start=None, end=None):
    full, rel = _safe(path)
    lines = open(full, encoding="utf-8", errors="ignore").read().splitlines()
    s = max(1, int(start or 1))
    e = min(len(lines), int(end or len(lines)))
    body = "\n".join(f"{i}: {_scrub(lines[i - 1])}" for i in range(s, e + 1))
    return {"file": rel, "start": s, "end": e, "content": body[:MAX_BYTES]}


OPS = {"search_code": search_code, "outline": outline, "read_file": read_file}


def run(op, **kwargs):
    return OPS[op](**kwargs)
