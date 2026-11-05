"""Reusable CRUD route builder for simple/master-data resources.

Complex inventory, sales and receiving workflows should use dedicated service functions.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from app.services import crud_service
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles


def build_crud_router(*, prefix, tag, model, create_schema, response_schema, update_schema=None,
                      allow_delete=False, field_aliases=None, immutable=False,
                      read_roles=None, write_roles=None, delete_roles=None):
    router = APIRouter(prefix=prefix, tags=[tag])
    read_dependencies = [Depends(require_roles(*read_roles))] if read_roles else []
    write_dependencies = [Depends(require_roles(*write_roles))] if write_roles else []
    delete_dependencies = [Depends(require_roles(*delete_roles))] if delete_roles else []
    aliases = field_aliases or {}

    def dump(obj):
        try:
            return response_schema.model_validate(obj).model_dump(mode="json")
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Response schema/model mismatch for {tag}: {exc}") from exc

    def create(payload: dict, db: Session = Depends(get_db)):
        try:
            data = crud_service.validate_create_payload(model, create_schema, payload, aliases)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            obj = crud_service.create(db, model, data)
            return dump(obj)
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(status_code=409, detail="The record conflicts with an existing record or related database constraint.") from exc

    def list_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
        if skip < 0 or limit < 1 or limit > 500:
            raise HTTPException(status_code=422, detail="skip must be non-negative and limit must be between 1 and 500")
        rows = crud_service.list_all(db, model, skip=skip, limit=limit)
        return [dump(row) for row in rows]

    def get_item(item_id: int, db: Session = Depends(get_db)):
        obj = crud_service.get_one(db, model, item_id)
        if obj is None:
            raise HTTPException(status_code=404, detail=f"{tag.rstrip('s')} not found")
        return dump(obj)

    router.add_api_route("/", create, methods=["POST"], dependencies=write_dependencies, name=f"create_{tag.lower().replace(' ', '_')}")
    router.add_api_route("/", list_items, methods=["GET"], dependencies=read_dependencies, name=f"list_{tag.lower().replace(' ', '_')}")
    router.add_api_route("/{item_id}", get_item, methods=["GET"], dependencies=read_dependencies, name=f"get_{tag.lower().replace(' ', '_')}")

    if update_schema is not None and not immutable:
        def update(item_id: int, payload: dict, db: Session = Depends(get_db)):
            obj = crud_service.get_one(db, model, item_id)
            if obj is None:
                raise HTTPException(status_code=404, detail=f"{tag.rstrip('s')} not found")
            try:
                data = crud_service.validate_update_payload(model, update_schema, payload, aliases)
            except Exception as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            try:
                obj = crud_service.update(db, obj, data)
                return dump(obj)
            except IntegrityError as exc:
                db.rollback()
                raise HTTPException(status_code=409, detail="Update conflicts with an existing record or database constraint.") from exc
        router.add_api_route("/{item_id}", update, methods=["PATCH"], dependencies=write_dependencies, name=f"update_{tag.lower().replace(' ', '_')}")
        router.add_api_route("/{item_id}", update, methods=["PUT"], dependencies=write_dependencies, name=f"replace_{tag.lower().replace(' ', '_')}")

    if allow_delete:
        def delete(item_id: int, db: Session = Depends(get_db)):
            obj = crud_service.get_one(db, model, item_id)
            if obj is None:
                raise HTTPException(status_code=404, detail=f"{tag.rstrip('s')} not found")
            if hasattr(obj, "is_active"):
                crud_service.deactivate(db, obj)
                return {"message": "Record deactivated", "id": item_id}
            raise HTTPException(status_code=409, detail="Hard deletion is disabled for this resource to preserve history.")
        router.add_api_route("/{item_id}", delete, methods=["DELETE"], dependencies=delete_dependencies, name=f"deactivate_{tag.lower().replace(' ', '_')}")
    return router
