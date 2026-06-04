# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
from django.apps import AppConfig


class DjangoAgentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "django_agent"
    verbose_name = "Agent"
