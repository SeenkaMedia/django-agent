"""Acceso al código: búsqueda/lectura + barandas de seguridad (sin Vertex)."""
from django.test import SimpleTestCase

from django_agent import code_access as C


class CodeAccessTests(SimpleTestCase):
    def test_search_finds_own_code(self):
        files = [m["file"] for m in C.search_code("def search_code", "*.py")["matches"]]
        self.assertTrue(any("code_access.py" in f for f in files))

    def test_outline_lists_functions(self):
        names = [s["name"] for s in C.outline("django_agent/registry.py")["symbols"]]
        self.assertIn("create", names)

    def test_read_file_returns_requested_range_only(self):
        result = C.read_file("django_agent/__init__.py", 1, 1)
        self.assertEqual(result["start"], 1)
        self.assertEqual(result["end"], 1)
        self.assertTrue(result["content"].startswith("1: "))

    def test_denylist_blocks_env_and_settings(self):
        with self.assertRaises(ValueError):
            C.read_file(".env")
        with self.assertRaises(ValueError):
            C.read_file("service/settings/local.py")

    def test_path_traversal_blocked(self):
        with self.assertRaises(ValueError):
            C.read_file("../../../../etc/passwd")

    def test_secret_line_is_redacted(self):
        self.assertIn("redactada", C._scrub('API_KEY = "abc123"'))
        self.assertIn("redactada", C._scrub("password: hunter2"))
        self.assertEqual(C._scrub("total = a + b"), "total = a + b")
