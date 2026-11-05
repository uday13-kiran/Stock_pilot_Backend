"""Shared service layer for straightforward CRUD resources.

Domain workflows (inventory, purchasing and sales) have dedicated endpoints/services.
"""
from sqlalchemy.exc import IntegrityError
from app.repositories import crud_repository


def allowed_model_fields(model):
    return set(model.__table__.columns.keys())


def validate_create_payload(model, schema, payload, aliases=None):
    aliases = aliases or {}
    validated = schema.model_validate(payload)
    values = validated.model_dump(exclude_unset=True)
    values = {aliases.get(key, key): value for key, value in values.items()}
    fields = allowed_model_fields(model)
    return {key: value for key, value in values.items() if key in fields and key != "id"}


def validate_update_payload(model, schema, payload, aliases=None):
    aliases = aliases or {}
    validated = schema.model_validate(payload)
    values = validated.model_dump(exclude_unset=True, exclude_none=True)
    values = {aliases.get(key, key): value for key, value in values.items()}
    fields = allowed_model_fields(model)
    return {key: value for key, value in values.items() if key in fields and key != "id"}


def create(db, model, data):
    return crud_repository.create_record(db, model, data)


def list_all(db, model, skip=0, limit=100):
    return crud_repository.list_records(db, model, skip=skip, limit=limit)


def get_one(db, model, record_id):
    return crud_repository.get_record(db, model, record_id)


def update(db, record, data):
    return crud_repository.update_record(db, record, data)


def deactivate(db, record):
    return crud_repository.deactivate_record(db, record)
