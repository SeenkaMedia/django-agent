"""Inyecta el widget en las páginas del admin (plug-and-play, sin tocar templates)."""
import time

from django.templatetags.static import static
from django.urls import reverse

from . import settings as S

VERSION = str(int(time.time()))  # cache-busting de los assets (cambia en cada arranque)

SNIPPET = ('<link rel="stylesheet" href="{css}">'
           '<div id="agent-root" data-history="{h}" data-message="{m}" data-confirm="{c}" data-reset="{r}" data-logo="{logo}"></div>'
           '<script src="{js}" defer></script>')


class WidgetMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if self._should_inject(request, response):
            response.content = self._inject(response.content)
        return response

    def _should_inject(self, request, response):
        user = getattr(request, "user", None)
        allowed = user and user.is_authenticated and (user.is_staff or not S.staff_only())
        return bool(allowed
                    and request.path.startswith(S.path_prefix())
                    and "text/html" in response.get("Content-Type", "")
                    and hasattr(response, "content"))

    def _inject(self, content):
        try:
            html = content.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            return content
        if "</body>" not in html or 'id="agent-root"' in html:
            return content
        return html.replace("</body>", self._snippet() + "</body>", 1).encode("utf-8")

    def _snippet(self):
        v = "?v=" + VERSION
        return SNIPPET.format(
            css=static("django_agent/widget.css") + v, js=static("django_agent/widget.js") + v,
            logo=static("django_agent/logo.svg"),
            h=reverse("django_agent:history"), m=reverse("django_agent:message"),
            c=reverse("django_agent:confirm"), r=reverse("django_agent:reset"))
