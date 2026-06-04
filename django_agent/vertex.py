# Copyright 2026 Seenka
# SPDX-License-Identifier: Apache-2.0
"""Gemini client on Vertex AI plus the generic (CRUD) function declarations.

Auth via ADC (the pod's service account). `filters`/`data` are passed as JSON
strings to avoid relying on free-form object support in the function-calling schema.
"""
from google import genai
from google.genai import types

from . import settings as S

_MODEL = {"type": "string", "description": "app_label.modelname identifier (e.g. panelists.account)."}
_JSON = {"type": "string", "description": "JSON object serialized as a string."}

FUNCTIONS = [
    {"name": "describe_models", "description": "Lists the available models and their fields. Use this first if you don't know the model or its fields.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "query", "description": "Lists or searches records of a model.",
     "parameters": {"type": "object", "properties": {
         "model": _MODEL, "filters": _JSON, "order": {"type": "string"}, "limit": {"type": "integer"}},
         "required": ["model"]}},
    {"name": "get", "description": "Fetches a single record by its pk.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "pk": {"type": "string"}}, "required": ["model", "pk"]}},
    {"name": "create", "description": "Creates a record. Requires user confirmation.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "data": _JSON}, "required": ["model", "data"]}},
    {"name": "update", "description": "Updates a record by pk. Requires user confirmation.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "pk": {"type": "string"}, "data": _JSON}, "required": ["model", "pk", "data"]}},
    {"name": "delete", "description": "Deletes a record by pk. Requires user confirmation.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "pk": {"type": "string"}}, "required": ["model", "pk"]}},
]


class Vertex:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = genai.Client(vertexai=True, project=S.project(), location=S.location())
        return self._client

    def generate(self, system, contents, functions):
        tool = types.Tool(function_declarations=functions)
        return self.client.models.generate_content(
            model=S.model(), contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system, tools=[tool], temperature=S.temperature()),
        )


vertex = Vertex()
