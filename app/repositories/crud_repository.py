"""Shared low-level persistence helpers for simple CRUD resources."""
from sqlalchemy import select
from sqlalchemy.orm import Session


def create_record(db: Session, model, data: dict):
    record = model(**data)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_records(db: Session, model, *, skip: int = 0, limit: int = 100):
    return db.scalars(select(model).offset(skip).limit(limit)).all()


def get_record(db: Session, model, record_id: int):
    return db.get(model, record_id)


def update_record(db: Session, record, data: dict):
    for key, value in data.items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def deactivate_record(db: Session, record):
    record.is_active = False
    db.commit()
    db.refresh(record)
    return record
