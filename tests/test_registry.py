# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Generic CRUD, permissions, serialization and FK resolution (without Vertex)."""
import datetime
import decimal

from django.contrib import admin
from django.contrib.auth.models import Group, Permission, User
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from django_agent import registry


def _register(model):
    try:
        admin.site.register(model)
    except admin.sites.AlreadyRegistered:
        pass


class RegistryTests(TestCase):
    def setUp(self):
        _register(Group)
        self.staff = self._user("staff", ["add_group", "change_group", "delete_group", "view_group"])

    def _user(self, name, codenames, **flags):
        user = User.objects.create_user(name, is_staff=True, **flags)
        for code in codenames:
            user.user_permissions.add(Permission.objects.get(codename=code))
        return User.objects.get(pk=user.pk)

    def test_describe_includes_registered_model(self):
        labels = [m["model"] for m in registry.describe_models(self.staff)]
        self.assertIn("auth.group", labels)

    def test_describe_excludes_models_without_view_perm(self):
        nobody = User.objects.create_user("nobody", is_staff=True)
        self.assertEqual(registry.describe_models(nobody), [])

    def test_crud_happy_path(self):
        pk = registry.create(self.staff, "auth.group", {"name": "Editors"})["pk"]
        self.assertEqual(registry.get(self.staff, "auth.group", pk)["name"], "Editors")
        self.assertEqual(len(registry.query(self.staff, "auth.group", filters={"name": "Editors"})), 1)
        registry.update(self.staff, "auth.group", pk, {"name": "Editors2"})
        self.assertEqual(registry.get(self.staff, "auth.group", pk)["name"], "Editors2")
        registry.delete(self.staff, "auth.group", pk)
        self.assertEqual(registry.query(self.staff, "auth.group", filters={"name": "Editors2"}), [])

    def test_create_denied_without_perm(self):
        viewer = self._user("viewer", ["view_group"])
        with self.assertRaises(PermissionDenied):
            registry.create(viewer, "auth.group", {"name": "x"})

    def test_fk_resolution_by_name_and_pk(self):
        group = Group.objects.create(name="Admins")
        self.assertEqual(registry._resolve_fk(Group, "admins"), group)  # iexact
        self.assertEqual(registry._resolve_fk(Group, group.pk), group)

    def test_jsonable_handles_odd_types(self):
        self.assertEqual(registry._jsonable(datetime.date(2020, 1, 2)), "2020-01-02")
        self.assertEqual(registry._jsonable(decimal.Decimal("1.5")), 1.5)
        self.assertEqual(registry._jsonable({"a": 1}), {"a": 1})

        class Weird:
            def __str__(self):
                return "weird"

        self.assertEqual(registry._jsonable(Weird()), "weird")

    def test_jsonable_recurses_into_nested_containers(self):
        import json
        import zoneinfo

        aware = datetime.datetime(2020, 1, 2, 3, 4, tzinfo=zoneinfo.ZoneInfo("UTC"))
        value = {"when": aware, "tags": [aware, {"amount": decimal.Decimal("1.5")}]}
        result = registry._jsonable(value)
        self.assertEqual(result["when"], aware.isoformat())
        self.assertEqual(result["tags"][0], aware.isoformat())
        self.assertEqual(result["tags"][1]["amount"], 1.5)
        json.dumps(result)
