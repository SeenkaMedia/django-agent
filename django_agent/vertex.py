"""Cliente Gemini en Vertex AI + declaración de las funciones genéricas (CRUD).

Auth por ADC (service account del pod). `filters`/`data` viajan como string JSON
para no depender del soporte de objetos libres en el schema de function-calling.
"""
from google import genai
from google.genai import types

from . import settings as S

_MODEL = {"type": "string", "description": "Identificador app_label.modelname (ej. panelists.account)."}
_JSON = {"type": "string", "description": "Objeto JSON serializado como string."}

FUNCTIONS = [
    {"name": "describe_models", "description": "Lista los modelos disponibles y sus campos. Usalo primero si no conocés el modelo o sus campos.",
     "parameters": {"type": "object", "properties": {}}},
    {"name": "query", "description": "Lista o busca registros de un modelo.",
     "parameters": {"type": "object", "properties": {
         "model": _MODEL, "filters": _JSON, "order": {"type": "string"}, "limit": {"type": "integer"}},
         "required": ["model"]}},
    {"name": "get", "description": "Trae un registro por su pk.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "pk": {"type": "string"}}, "required": ["model", "pk"]}},
    {"name": "create", "description": "Crea un registro. Requiere confirmación del usuario.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "data": _JSON}, "required": ["model", "data"]}},
    {"name": "update", "description": "Modifica un registro por pk. Requiere confirmación del usuario.",
     "parameters": {"type": "object", "properties": {"model": _MODEL, "pk": {"type": "string"}, "data": _JSON}, "required": ["model", "pk", "data"]}},
    {"name": "delete", "description": "Borra un registro por pk. Requiere confirmación del usuario.",
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

    def generate(self, system, contents):
        tool = types.Tool(function_declarations=FUNCTIONS)
        return self.client.models.generate_content(
            model=S.model(), contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system, tools=[tool], temperature=S.temperature()),
        )


vertex = Vertex()
