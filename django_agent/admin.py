# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
from django.contrib import admin

from .models import ActionLog, Conversation, Message


class _ReadOnly(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    can_delete = False
    fields = ["role", "text", "tool_name", "tool_args", "tool_result", "status", "created_at"]
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Conversation)
class ConversationAdmin(_ReadOnly):
    list_display = ["user", "message_count", "created_at", "updated_at"]
    search_fields = ["user__username"]
    readonly_fields = [f.name for f in Conversation._meta.fields]
    inlines = [MessageInline]

    @admin.display(description="Messages")
    def message_count(self, obj):
        return obj.messages.count()


@admin.register(Message)
class MessageAdmin(_ReadOnly):
    list_display = ["created_at", "conversation", "role", "tool_name", "status"]
    list_filter = ["role", "status", "tool_name"]
    search_fields = ["conversation__user__username", "text", "tool_name"]
    readonly_fields = [f.name for f in Message._meta.fields]


@admin.register(ActionLog)
class ActionLogAdmin(_ReadOnly):
    list_display = ["created_at", "user", "tool_name", "ok"]
    list_filter = ["tool_name", "ok"]
    search_fields = ["user__username", "tool_name"]
    readonly_fields = [f.name for f in ActionLog._meta.fields]
