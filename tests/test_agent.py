# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Agent loop with Vertex mocked: confirmation, audit, pending, reads."""
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase

from django_agent import agent
from django_agent.models import ActionLog, Message


class _FakeCall:
    def __init__(self, name, args):
        self.name = name
        self.args = args


class _FakePart:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


def _resp(parts):
    content = type("Content", (), {"parts": parts})()
    return type("Response", (), {"candidates": [type("C", (), {"content": content})()]})()


def call(name, **args):
    return _resp([_FakePart(function_call=_FakeCall(name, args))])


def text(value):
    return _resp([_FakePart(text=value)])


def _sequence(*responses):
    it = iter(responses)
    return lambda system, contents, functions: next(it)


class AgentMockedTests(TestCase):
    def setUp(self):
        try:
            admin.site.register(Group)
        except admin.sites.AlreadyRegistered:
            pass
        self.user = User.objects.create_user("u", is_staff=True)
        for code in ["add_group", "change_group", "delete_group", "view_group"]:
            self.user.user_permissions.add(Permission.objects.get(codename=code))
        self.user = User.objects.get(pk=self.user.pk)

    def test_write_asks_confirmation_before_executing(self):
        with patch.object(agent.vertex, "generate",
                          _sequence(call("create", model="auth.group", data='{"name":"X"}'))):
            result = agent.handle_message(self.user, "create X", {})
        self.assertIn("confirm", result)
        self.assertFalse(Group.objects.filter(name="X").exists())

    def test_confirm_executes_and_audits(self):
        with patch.object(agent.vertex, "generate",
                          _sequence(call("create", model="auth.group", data='{"name":"X"}'))):
            agent.handle_message(self.user, "create X", {})
        with patch.object(agent.vertex, "generate", _sequence(text("done"))):
            result = agent.confirm(self.user, True, {})
        self.assertTrue(Group.objects.filter(name="X").exists())
        self.assertEqual(result.get("reply"), "done")
        self.assertTrue(ActionLog.objects.filter(tool_name="create", ok=True).exists())

    def test_reject_does_not_execute(self):
        with patch.object(agent.vertex, "generate",
                          _sequence(call("create", model="auth.group", data='{"name":"Y"}'))):
            agent.handle_message(self.user, "create Y", {})
        with patch.object(agent.vertex, "generate", _sequence(text("cancelled"))):
            agent.confirm(self.user, False, {})
        self.assertFalse(Group.objects.filter(name="Y").exists())

    def test_read_op_runs_inline(self):
        Group.objects.create(name="Existente")
        with patch.object(agent.vertex, "generate",
                          _sequence(call("query", model="auth.group"), text("there is 1 group"))):
            result = agent.handle_message(self.user, "how many groups", {})
        self.assertEqual(result.get("reply"), "there is 1 group")

    def test_update_preview_has_verbose_and_diff(self):
        group = Group.objects.create(name="Old")
        with patch.object(agent.vertex, "generate",
                          _sequence(call("update", model="auth.group", pk=str(group.pk), data='{"name":"New"}'))):
            result = agent.handle_message(self.user, "rename", {})
        preview = result["confirm"]["preview"]
        self.assertEqual(preview["model_verbose"], "group")
        self.assertEqual(preview["current"]["name"], "Old")
        self.assertEqual(preview["data"]["name"], "New")

    def test_reset_clears_history(self):
        with patch.object(agent.vertex, "generate", _sequence(text("hi"))):
            agent.handle_message(self.user, "hi", {})
        self.assertTrue(Message.objects.exists())
        agent.reset(self.user)
        self.assertFalse(Message.objects.exists())

    def test_new_message_drops_pending_write(self):
        with patch.object(agent.vertex, "generate",
                          _sequence(call("create", model="auth.group", data='{"name":"Z"}'))):
            agent.handle_message(self.user, "create Z", {})
        with patch.object(agent.vertex, "generate", _sequence(text("ok"))):
            agent.handle_message(self.user, "never mind", {})
        self.assertFalse(Message.objects.filter(status="pending").exists())
        self.assertFalse(Group.objects.filter(name="Z").exists())
