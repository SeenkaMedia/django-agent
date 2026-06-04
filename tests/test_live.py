"""Tests en vivo contra Gemini real. Opt-in: correr con `python runtests.py --live`
y GOOGLE_APPLICATION_CREDENTIALS + AGENT_VERTEX_PROJECT seteados."""
import os
import unittest

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import TestCase

from django_agent import agent
from django_agent.models import Message

LIVE = os.environ.get("AGENT_LIVE_TESTS") == "1"


@unittest.skipUnless(LIVE, "vivo (Gemini): correr con --live + credenciales de Vertex")
class LiveVertexTests(TestCase):
    def setUp(self):
        try:
            admin.site.register(Group)
        except admin.sites.AlreadyRegistered:
            pass
        self.user = User.objects.create_superuser("live", "live@test.local", "x")

    def test_function_calling_creates_after_confirm(self):
        result = agent.handle_message(self.user, "Creá un grupo llamado SoporteQA.", {"url": "/admin/"})
        self.assertIn("confirm", result)
        agent.confirm(self.user, True, {"url": "/admin/"})
        self.assertTrue(Group.objects.filter(name="SoporteQA").exists())

    def test_agent_reads_source_code(self):
        agent.handle_message(self.user, "Mirando el código, ¿qué hace search_code? Citá el archivo.", {"url": "/admin/"})
        self.assertTrue(Message.objects.filter(role="model", tool_name="search_code").exists())
