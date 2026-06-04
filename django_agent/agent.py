# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Agent orchestration: prompt, function-calling loop and write confirmation."""
import base64
import json

from google.genai import types

from . import code_access, registry, settings as S
from .models import ActionLog, Conversation, Message
from .vertex import FUNCTIONS as CRUD_FUNCTIONS, vertex

WRITE_OPS = registry.WRITE_OPS

SYSTEM = """You are an assistant embedded in the Django admin of a web application.
You help staff query and modify the application's data —and understand how it works— by
calling the available functions. You always act with the user's own permissions; the system
blocks anything they are not allowed to do.

# How you work
- Use the current page as context: if it maps to a model, assume the user is talking about
  THAT model unless they say otherwise (do not confuse it with similarly named models).
- Understand the domain before acting: if you do not know a model or its fields, call
  describe_models.
- To operate on existing data, find it first with query/get. Never ask the user for internal
  IDs (pk): if they give you a name or other value, locate the record yourself with query.
- Pick the right operation:
  · query / get to read.
  · create only to add a brand-new record.
  · update to change one that already exists (rename, fix, complete, move…): find it first
    and update it, do not recreate it.
  · delete to remove.
- You produce the values: you may compute, reformat, normalize, split or combine data and
  pass the final value to create/update. Do not refuse a task by assuming you "can't edit data".
- Foreign keys: pass the value by pk or by a natural name (the system resolves it). If the
  data lives in a related model, operate on that model.

# Writes and confirmation
- You decide create / update / delete by calling the function directly. The system shows the
  user a confirmation with the details and executes it only if they accept.
- Do not ask for confirmation in text or wait for a "yes": just call the function.
- If an action shows up as not confirmed or cancelled, it is not an error or a system
  rejection: the user simply did not confirm. If they ask again, call it again.

# When in doubt
- If the request is ambiguous —it is unclear which record it refers to, whether to create or
  update, or what value to use— ask a short clarifying question before acting. Asking is
  better than guessing wrong on a write.

# Format
- `data` and `filters` travel as a JSON string.
- Reply in the user's language, with the depth the question calls for: brief for simple data,
  more thorough when it helps.

Current page: {page}
Available models: {models}"""

CODE_NOTE = """

# Source code
You can read the project's source to explain how something works: locate it with search_code,
inspect structure with outline and read only the range you need with read_file. Bring just the
relevant slice (not whole files) and cite file and lines."""


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
        return {"reply": "There is nothing pending confirmation."}
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
    return {"reply": "Reached the maximum number of steps without finishing."}


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
        _tool_message(conv, m.tool_name, {"status": "not confirmed",
            "note": "The user sent another message without confirming. This is NOT an error or a "
                    "system rejection; they simply did not confirm. Handle the new request and, if "
                    "the action is still needed, call the function again."})


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
