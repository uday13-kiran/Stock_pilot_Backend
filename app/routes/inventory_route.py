
from fastapi import APIRouter, Depends, HTTPException, Query, status

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.inventory import Inventory
from app.schemas.inventory import InventoryCreate, InventoryResponse
from app.services import inventory_services

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
)


@router.get("/", response_model=list[InventoryResponse])
def list_inventory(
    warehouse_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(get_db),
):
    statement = select(Inventory).order_by(Inventory.warehouse_id, Inventory.product_id)
    if warehouse_id is not None:
        statement = statement.where(Inventory.warehouse_id == warehouse_id)
    return list(db.scalars(statement.offset(skip).limit(limit)).all())


@router.post("/",response_model=InventoryResponse,status_code=status.HTTP_201_CREATED,)
def create_inventory(
    data: InventoryCreate,
    db: Session = Depends(get_db),
    _authorized=Depends(require_roles("inventory_manager")),
):
    try:
        inventory = inventory_services.create_inventory(db, data)

        db.commit()
        db.refresh(inventory)

        return inventory

    except ValueError as exc:
        db.rollback()
        message = str(exc)

        if message == "Product not found":
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        if message == "Warehouse not found":
            raise HTTPException(
                status_code=404,
                detail=message,
            ) from exc

        raise HTTPException(
            status_code=409,
            detail=message,
        ) from exc

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Inventory conflicts with an existing record",
        ) from exc

    except Exception:
        db.rollback()
        raise