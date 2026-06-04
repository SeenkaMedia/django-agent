# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Live tests against real Gemini. Opt-in: run with `python runtests.py --live`
and GOOGLE_APPLICATION_CREDENTIALS + AGENT_VERTEX_PROJECT set."""
import os
import unittest

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import TestCase

from django_agent import agent
from django_agent.models import Message

LIVE = os.environ.get("AGENT_LIVE_TESTS") == "1"


@unittest.skipUnless(LIVE, "live (Gemini): run with --live + Vertex credentials")
class LiveVertexTests(TestCase):
    def setUp(self):
        try:
            admin.site.register(Group)
        except admin.sites.AlreadyRegistered:
            pass
        self.user = User.objects.create_superuser("live", "live@test.local", "x")

    def test_function_calling_creates_after_confirm(self):
        result = agent.handle_message(self.user, "Create a group named SupportQA.", {"url": "/admin/"})
        self.assertIn("confirm", result)
        agent.confirm(self.user, True, {"url": "/admin/"})
        self.assertTrue(Group.objects.filter(name="SupportQA").exists())

    def test_agent_reads_source_code(self):
        agent.handle_message(self.user, "Looking at the code, what does search_code do? Cite the file.", {"url": "/admin/"})
        self.assertTrue(Message.objects.filter(role="model", tool_name="search_code").exists())
