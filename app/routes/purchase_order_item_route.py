from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.purchase_order import PurchaseOrder
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.supplier_products import SupplierProduct
from app.schemas.purchase_order_item import PurchaseOrderItemCreate, PurchaseOrderItemResponse

router = APIRouter(prefix="/purchase-order-items", tags=["Purchase Order Items"])


@router.post("/", status_code=201)
def create_purchase_order_item(
    payload: PurchaseOrderItemCreate,
    db: Session = Depends(get_db),
    _authorized=Depends(require_roles("purchase_manager")),
):
    purchase_order = db.scalar(select(PurchaseOrder).where(
        PurchaseOrder.id == payload.purchase_order_id,
    ).with_for_update())
    if purchase_order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    if purchase_order.status.upper() != "DRAFT":
        raise HTTPException(status_code=409, detail="Purchase order items can only be added to a draft order")
    association = db.scalar(select(SupplierProduct).where(
        SupplierProduct.supplier_id == purchase_order.supplier_id,
        SupplierProduct.product_id == payload.product_id,
    ))
    if association is None:
        raise HTTPException(status_code=409, detail="Product is not associated with this purchase order's supplier")
    existing_item = db.scalar(select(PurchaseOrderItem.id).where(
        PurchaseOrderItem.purchase_order_id == purchase_order.id,
        PurchaseOrderItem.product_id == payload.product_id,
    ))
    if existing_item is not None:
        raise HTTPException(status_code=409, detail="Product is already on this purchase order")

    source_price = association.supplier_price if association.supplier_price is not None else payload.unit_price
    if source_price is None:
        raise HTTPException(status_code=422, detail="A supplier price or unit price is required")
    unit_price = Decimal(str(source_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total_price = (unit_price * payload.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    item = PurchaseOrderItem(
        purchase_order_id=purchase_order.id,
        product_id=payload.product_id,
        quantity=payload.quantity,
        unit_price=unit_price,
        total_price=total_price,
    )
    try:
        existing_total = db.scalar(select(func.coalesce(func.sum(PurchaseOrderItem.total_price), 0)).where(
            PurchaseOrderItem.purchase_order_id == purchase_order.id,
        ))
        purchase_order.total_amount = Decimal(str(existing_total or 0)) + total_price
        db.add(item)
        db.commit()
        db.refresh(item)
        return PurchaseOrderItemResponse.model_validate(item).model_dump(mode="json")
    except Exception:
        db.rollback()
        raise


@router.get("/")
def list_purchase_order_items(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _authorized=Depends(require_roles("purchase_manager", "inventory_manager")),
):
    items = db.scalars(select(PurchaseOrderItem).offset(skip).limit(limit)).all()
    return [PurchaseOrderItemResponse.model_validate(item).model_dump(mode="json") for item in items]


@router.get("/{item_id}")
def get_purchase_order_item(
    item_id: int,
    db: Session = Depends(get_db),
    _authorized=Depends(require_roles("purchase_manager", "inventory_manager")),
):
    item = db.get(PurchaseOrderItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Purchase order item not found")
    return PurchaseOrderItemResponse.model_validate(item).model_dump(mode="json")
