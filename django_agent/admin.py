# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
import json

from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import ActionLog, Conversation, Message


def _short(value, limit=80):
    if value in (None, "", {}):
        return ""
    text = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _pretty(value):
    if value in (None, "", {}):
        return "—"
    dumped = json.dumps(value, ensure_ascii=False, indent=2) if not isinstance(value, str) else value
    return format_html('<pre style="margin:0;white-space:pre-wrap;font-size:12px">{}</pre>', dumped)


class _ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


_BUBBLE = ("display:inline-block;max-width:78%;padding:7px 11px;border-radius:12px;"
           "white-space:pre-wrap;word-wrap:break-word;font-size:13px;line-height:1.5;")
_NOTE = "margin:3px 0;font-family:ui-monospace,monospace;font-size:11px;color:#8a93a3"
_TIME = "font-size:10px;color:#aab2c0;margin-top:2px"


def _message_html(m):
    ts = m.created_at.strftime("%Y-%m-%d %H:%M")
    if m.role == "tool":
        return format_html('<div style="{}">↩ {} → {}</div>', _NOTE, m.tool_name, _short(m.tool_result))
    if m.tool_name:
        return format_html('<div style="{}">⚙ {}({})</div>', _NOTE, m.tool_name, _short(m.tool_args))
    if m.role == "user":
        return format_html(
            '<div style="text-align:right;margin:8px 0">'
            '<span style="{}background:#2b6cff;color:#fff;text-align:left">{}</span>'
            '<div style="{}">{}</div></div>', _BUBBLE, m.text, _TIME, ts)
    return format_html(
        '<div style="text-align:left;margin:8px 0">'
        '<span style="{}background:#eef1f6;color:#1a1f29">{}</span>'
        '<div style="{}">{}</div></div>', _BUBBLE, m.text, _TIME, ts)


@admin.register(Conversation)
class ConversationAdmin(_ReadOnly):
    list_display = ["user", "messages", "last_message", "updated_at"]
    search_fields = ["user__username"]
    fields = ["user", "created_at", "updated_at", "transcript"]
    readonly_fields = fields

    @admin.display(description="Messages")
    def messages(self, obj):
        return obj.messages.count()

    @admin.display(description="Last message")
    def last_message(self, obj):
        last = obj.messages.exclude(text="").last()
        return _short(last.text, 60) if last else ""

    @admin.display(description="Transcript")
    def transcript(self, obj):
        rows = obj.messages.all()
        if not rows:
            return "—"
        body = format_html_join("", "{}", ((_message_html(m),) for m in rows))
        return format_html(
            '<div style="max-width:700px;background:#f6f8fb;border:1px solid #e2e6ee;'
            'border-radius:10px;padding:14px">{}</div>', body)


@admin.register(ActionLog)
class ActionLogAdmin(_ReadOnly):
    list_display = ["created_at", "user", "summary", "result_badge"]
    list_filter = ["tool_name", "ok"]
    search_fields = ["user__username", "tool_name"]
    fields = ["created_at", "user", "conversation", "tool_name", "ok", "args_pretty", "result_pretty"]
    readonly_fields = fields

    @admin.display(description="Action")
    def summary(self, obj):
        args = obj.args or {}
        detail = _short(args.get("data") or args.get("pk") or args.get("filters") or "", 50)
        return f"{obj.tool_name} · {args.get('model', '')} {detail}".strip()

    @admin.display(description="Result")
    def result_badge(self, obj):
        color, label = ("#16a34a", "ok") if obj.ok else ("#dc2626", "failed")
        return format_html('<b style="color:{}">{}</b>', color, label)

    @admin.display(description="Arguments")
    def args_pretty(self, obj):
        return _pretty(obj.args)

    @admin.display(description="Result")
    def result_pretty(self, obj):
        return _pretty(obj.result)


@admin.register(Message)
class MessageAdmin(_ReadOnly):
    list_display = ["created_at", "conversation", "role", "tool_name", "preview", "status"]
    list_filter = ["role", "status", "tool_name"]
    search_fields = ["conversation__user__username", "text", "tool_name"]
    readonly_fields = [f.name for f in Message._meta.fields]

    @admin.display(description="Preview")
    def preview(self, obj):
        return _short(obj.text or obj.tool_args or obj.tool_result, 60)
