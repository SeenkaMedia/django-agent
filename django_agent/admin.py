# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
from django.contrib import admin

from .models import ActionLog


@admin.register(ActionLog)
class ActionLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "user", "tool_name", "ok"]
    list_filter = ["tool_name", "ok"]
    search_fields = ["user__username", "tool_name"]
    readonly_fields = [f.name for f in ActionLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
