"""Orquestación del agente: prompt, loop de function-calling y confirmación de escrituras."""
import base64
import json

from google.genai import types

from . import code_access, registry, settings as S
from .models import ActionLog, Conversation, Message
from .vertex import FUNCTIONS as CRUD_FUNCTIONS, vertex

WRITE_OPS = registry.WRITE_OPS

SYSTEM = """Sos un asistente embebido en el panel de administración (Django admin) de un
servicio de Seenka. Ayudás al staff a consultar y modificar los datos de la aplicación —y a
entender cómo funciona— llamando a las funciones disponibles. Operás siempre con los permisos
del usuario; el sistema bloquea lo que no puede hacer.

# Cómo trabajás
- Usá la página actual como contexto: si corresponde a un modelo, asumí que el usuario se
  refiere a ESE modelo salvo que aclare otro (no lo confundas con modelos de nombre parecido).
- Entendé el dominio antes de actuar: si no conocés un modelo o sus campos, llamá describe_models.
- Para operar sobre datos existentes, buscalos primero con query/get. No le pidas al usuario
  IDs internos (pk): si te da un nombre u otro dato, encontrá el registro vos con query.
- Elegí la operación correcta:
  · query / get para leer.
  · create solo para dar de alta un registro nuevo.
  · update para cambiar uno que ya existe (renombrar, corregir, completar, mover…): buscalo
    primero y actualizalo, no lo recrees.
  · delete para eliminar.
- Vos producís los valores: podés calcular, reformatear, normalizar, separar o combinar datos y
  pasar el valor final a create/update. No te niegues asumiendo que "no podés manipular datos".
- Foreign keys: pasá el valor por pk o por un nombre natural (el sistema lo resuelve). Si el
  dato vive en un modelo relacionado, operá sobre ese modelo.

# Escrituras y confirmación
- create / update / delete las decidís llamando la función directamente. El sistema le muestra
  al usuario una confirmación con el detalle y la ejecuta solo si acepta.
- No pidas la confirmación por texto ni esperes un "sí": llamá la función.
- Si una acción figura como no confirmada o cancelada, no es un error ni un rechazo del sistema:
  el usuario simplemente no confirmó. Si lo vuelve a pedir, volvé a llamarla.

# Ante la duda
- Si el pedido es ambiguo —no queda claro a qué registro se refiere, si hay que crear o
  modificar, o qué valor poner— hacé una pregunta breve antes de actuar. Preguntar es mejor
  que adivinar mal en una escritura.

# Formato
- `data` y `filters` viajan como string JSON.
- Respondé en el idioma del usuario, con la profundidad que la pregunta pida: breve para datos
  simples, más completo cuando aporte.

Página actual: {page}
Modelos disponibles: {models}"""

CODE_NOTE = """

# Código fuente
Podés leer el código del proyecto para explicar cómo funciona algo: ubicá con search_code, mirá
la estructura con outline y leé solo el rango necesario con read_file. Traé la porción justa (no
archivos enteros) y citá archivo y líneas."""


def conversation_for(user):
    conv, _ = Conversation.objects.get_or_create(user=user)
    return conv


def reset(user):
    conversation_for(user).messages.all().delete()


def history(conv):
    return [_public(m) for m in conv.messages.exclude(role="tool")]


def _public(m):
    if m.tool_name and m.role == "model":
        return {"role": "tool_call", "op": m.tool_name, "args": m.tool_args, "status": m.status}
    return {"role": m.role, "text": m.text}


def _system(user, page_context):
    models = ", ".join(registry.model_label(m) for m in registry.available_models(user))
    base = SYSTEM.format(page=json.dumps(page_context or {}, ensure_ascii=False), models=models)
    return base + CODE_NOTE if S.code_enabled() else base


def _functions():
    return CRUD_FUNCTIONS + code_access.FUNCTIONS if S.code_enabled() else CRUD_FUNCTIONS


def handle_message(user, text, page_context):
    conv = conversation_for(user)
    _drop_pending(conv)
    Message.objects.create(conversation=conv, role="user", text=text)
    return _run(conv, user, page_context)


def confirm(user, accept, page_context):
    conv = conversation_for(user)
    pending = conv.messages.filter(status="pending").last()
    if not pending:
        return {"reply": "No hay nada pendiente de confirmar."}
    if not accept:
        pending.status = "rejected"; pending.save(update_fields=["status"])
        _tool_message(conv, pending.tool_name, {"rejected": True})
        return _run(conv, user, page_context)
    pending.status = "ok"; pending.save(update_fields=["status"])
    result = _execute(user, conv, pending.tool_name, pending.tool_args)
    _tool_message(conv, pending.tool_name, result)
    return _run(conv, user, page_context)


def _run(conv, user, page_context):
    system = _system(user, page_context)
    functions = _functions()
    for _ in range(S.max_steps()):
        resp = vertex.generate(system, _contents(conv), functions)
        kind, name, args, sig = _extract(resp)
        if kind == "text":
            Message.objects.create(conversation=conv, role="model", text=name)
            return {"reply": name}
        Message.objects.create(conversation=conv, role="model", tool_name=name, tool_args=args,
                               thought_signature=_enc(sig),
                               status="pending" if name in WRITE_OPS else "ok")
        if name in WRITE_OPS:
            return {"confirm": {"op": name, "args": _coerce(args), "preview": _preview(name, args)}}
        result = _execute(user, conv, name, args)
        _tool_message(conv, name, result)
    return {"reply": "Alcancé el máximo de pasos sin terminar."}


def _execute(user, conv, op, args):
    kwargs = _coerce(args)
    try:
        result = code_access.run(op, **kwargs) if op in code_access.OPS else registry.run(op, user, **kwargs)
        ok = True
    except Exception as exc:
        result = {"error": f"{type(exc).__name__}: {exc}"}; ok = False
    if op in WRITE_OPS:
        ActionLog.objects.create(user=user, conversation=conv, tool_name=op, args=kwargs, result=result, ok=ok)
    return result


def _coerce(args):
    out = dict(args or {})
    for key in ("data", "filters"):
        if isinstance(out.get(key), str):
            out[key] = json.loads(out[key] or "{}")
    return out


def _preview(op, args):
    coerced = _coerce(args)
    label, pk = coerced.get("model"), coerced.get("pk")
    preview = {"op": op, "model": label, "model_verbose": registry.verbose(label),
               "pk": pk, "data": coerced.get("data")}
    if op in ("update", "delete") and label and pk is not None:
        preview["current"] = registry.snapshot(label, pk)
    return preview


def _tool_message(conv, name, result):
    Message.objects.create(conversation=conv, role="tool", tool_name=name, tool_result=result)


def _drop_pending(conv):
    for m in conv.messages.filter(status="pending"):
        m.status = "rejected"; m.save(update_fields=["status"])
        _tool_message(conv, m.tool_name, {"status": "no confirmada",
            "note": "El usuario mandó otro mensaje sin confirmar. NO es un error ni un rechazo "
                    "del sistema; simplemente no confirmó. Atendé el nuevo pedido y, si sigue "
                    "siendo necesaria, volvé a llamar la función."})


def _contents(conv):
    out = []
    for m in conv.messages.all():
        out.append(_content(m))
    return out


def _content(m):
    if m.role == "user":
        return types.Content(role="user", parts=[types.Part(text=m.text)])
    if m.role == "tool":
        resp = m.tool_result if isinstance(m.tool_result, dict) else {"result": m.tool_result}
        return types.Content(role="user", parts=[types.Part.from_function_response(name=m.tool_name, response=resp)])
    if m.tool_name:
        part = types.Part(function_call=types.FunctionCall(name=m.tool_name, args=m.tool_args or {}))
        if m.thought_signature:
            part.thought_signature = base64.b64decode(m.thought_signature)
        return types.Content(role="model", parts=[part])
    return types.Content(role="model", parts=[types.Part(text=m.text)])


def _enc(sig):
    return base64.b64encode(sig).decode() if sig else ""


def _extract(resp):
    call, sig, texts = None, None, []
    for part in resp.candidates[0].content.parts:
        if getattr(part, "function_call", None):
            call, sig = part.function_call, getattr(part, "thought_signature", None)
        elif getattr(part, "text", None):
            texts.append(part.text)
    if call:
        return "call", call.name, dict(call.args or {}), sig
    return "text", "".join(texts), None, None
