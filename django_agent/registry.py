"""CRUD genérico sobre los modelos registrados en el admin, con permisos Django.

Plug-and-play: lo que está en admin.site._registry es lo que el agente ve. Cada
operación chequea el permiso del modelo (view/add/change/delete) contra el usuario.
"""
import datetime
from decimal import Decimal

from django.apps import apps as django_apps
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.db import transaction

ACTION_BY_OP = {"query": "view", "get": "view", "create": "add",
                "update": "change", "delete": "delete"}
WRITE_OPS = {"create", "update", "delete"}
FK_LOOKUP_FIELDS = ("name", "code", "username", "email", "title", "slug")


def model_label(model):
    return f"{model._meta.app_label}.{model._meta.model_name}"


def get_model(label):
    return django_apps.get_model(*label.split("."))


def _perm(user, model, action):
    return user.has_perm(f"{model._meta.app_label}.{action}_{model._meta.model_name}")


def _require(user, model, action):
    if not _perm(user, model, action):
        raise PermissionDenied(f"Sin permiso {action} sobre {model_label(model)}")


def available_models(user):
    return [m for m in admin.site._registry if _perm(user, m, "view")]


def describe_models(user):
    return [{"model": model_label(m), "verbose": str(m._meta.verbose_name),
             "can": [a for a in ("view", "add", "change", "delete") if _perm(user, m, a)],
             "fields": _fields(m)}
            for m in available_models(user)]


def _fields(model):
    out = []
    for f in model._meta.concrete_fields:
        if f.auto_created and f.primary_key:
            continue
        info = {"name": f.name, "type": f.get_internal_type(),
                "required": not (f.blank or f.null or f.has_default())}
        if getattr(f, "choices", None):
            info["choices"] = [c[0] for c in f.choices]
        if f.is_relation and f.related_model is not None:
            info["fk"] = model_label(f.related_model)
        out.append(info)
    return out


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool, dict, list)):
        return value
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)  # FieldFile, UUID, etc.


def _serialize(obj):
    data = {"pk": obj.pk, "_str": str(obj)}
    for f in obj._meta.concrete_fields:
        if f.is_relation:
            rel_id = getattr(obj, f.attname)
            data[f.name] = {"pk": rel_id, "_str": str(getattr(obj, f.name))} if rel_id is not None else None
        else:
            data[f.name] = _jsonable(getattr(obj, f.attname))
    return data


def _resolve_fk(rel_model, value):
    if isinstance(value, dict):
        value = value.get("pk", value.get("_str"))
    try:
        return rel_model.objects.get(pk=value)
    except Exception:
        names = {f.name for f in rel_model._meta.concrete_fields}
        for field in FK_LOOKUP_FIELDS:
            if field in names:
                try:
                    return rel_model.objects.get(**{f"{field}__iexact": value})
                except rel_model.DoesNotExist:
                    continue
        raise rel_model.DoesNotExist(f"No encontré {model_label(rel_model)} = {value!r}")


def _resolve_fields(model, data):
    out = {}
    for f in model._meta.concrete_fields:
        if f.name not in data:
            continue
        value = data[f.name]
        if f.is_relation and value is not None and not isinstance(value, f.related_model):
            value = _resolve_fk(f.related_model, value)
        out[f.name] = value
    return out


def query(user, model, filters=None, order=None, limit=50):
    model = get_model(model); _require(user, model, "view")
    qs = model.objects.filter(**(filters or {}))
    if order:
        qs = qs.order_by(*([order] if isinstance(order, str) else order))
    return [_serialize(o) for o in qs[:min(int(limit or 50), 200)]]


def get(user, model, pk):
    model = get_model(model); _require(user, model, "view")
    return _serialize(model.objects.get(pk=pk))


@transaction.atomic
def create(user, model, data):
    model = get_model(model); _require(user, model, "add")
    obj = model(**_resolve_fields(model, data)); obj.save()
    return _serialize(obj)


@transaction.atomic
def update(user, model, pk, data):
    model = get_model(model); _require(user, model, "change")
    obj = model.objects.get(pk=pk)
    for key, value in _resolve_fields(model, data).items():
        setattr(obj, key, value)
    obj.save()
    return _serialize(obj)


@transaction.atomic
def delete(user, model, pk):
    model = get_model(model); _require(user, model, "delete")
    obj = model.objects.get(pk=pk); info = _serialize(obj); obj.delete()
    return {"deleted": info}


def _describe(user):
    return {"models": describe_models(user)}


OPS = {"describe_models": _describe, "query": query, "get": get,
       "create": create, "update": update, "delete": delete}


def run(op, user, **kwargs):
    return OPS[op](user, **kwargs)
