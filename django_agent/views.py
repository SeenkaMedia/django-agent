import json

from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from . import agent, settings as S


def _allowed(user):
    return bool(user and user.is_authenticated and (user.is_staff or not S.staff_only()))


def _guard(request):
    return None if _allowed(request.user) else HttpResponseForbidden("forbidden")


@require_GET
def history(request):
    return _guard(request) or JsonResponse(
        {"messages": agent.history(agent.conversation_for(request.user))})


@require_POST
def message(request):
    guard = _guard(request)
    if guard:
        return guard
    body = json.loads(request.body or "{}")
    return JsonResponse(agent.handle_message(request.user, body.get("text", ""), body.get("page_context")))


@require_POST
def confirm(request):
    guard = _guard(request)
    if guard:
        return guard
    body = json.loads(request.body or "{}")
    return JsonResponse(agent.confirm(request.user, bool(body.get("accept")), body.get("page_context")))


@require_POST
def reset(request):
    guard = _guard(request)
    if guard:
        return guard
    agent.reset(request.user)
    return JsonResponse({"ok": True})
