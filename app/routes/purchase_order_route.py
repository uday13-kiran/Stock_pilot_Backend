from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.routes.crud_factory import build_crud_router
from app.models.purchase_order import PurchaseOrder
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.products import Product
from app.models.supplier import Supplier
from app.models.supplier_products import SupplierProduct
from app.models.user import User
from app.models.warehouse import Warehouse
from app.schemas.purchase_order import (
    PurchaseOrderCreate,
    PurchaseOrderResponse,
    PurchaseOrderUpdate,
    PurchaseOrderWorkflowCreate,
    PurchaseOrderWorkflowResponse,
)

router = build_crud_router(
    prefix="/purchase-orders", tag="Purchase Orders", model=PurchaseOrder,
    create_schema=PurchaseOrderCreate, response_schema=PurchaseOrderResponse,
    allow_delete=False, immutable=False, field_aliases={'expected_date': 'expected_delivery_date'},
    read_roles=("purchase_manager", "inventory_manager"), write_roles=("purchase_manager",),
)


@router.post("/workflow", status_code=201)
def create_purchase_order_workflow(
    payload: PurchaseOrderWorkflowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _authorized=Depends(require_roles("purchase_manager")),
):
    supplier = db.get(Supplier, payload.supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Supplier not found")
    if not supplier.is_active:
        raise HTTPException(status_code=409, detail="Supplier is inactive")

    warehouse = db.get(Warehouse, payload.warehouse_id)
    if warehouse is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    if not warehouse.is_active:
        raise HTTPException(status_code=409, detail="Warehouse is inactive")

    product_ids = [line.product_id for line in payload.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=422, detail="Each product may appear only once per purchase order")

    try:
        normalized_items = []
        for line in payload.items:
            product = db.get(Product, line.product_id)
            if product is None:
                raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
            if not product.is_active or product.status.upper() != "ACTIVE":
                raise HTTPException(status_code=409, detail=f"Product {line.product_id} is inactive")

            association = db.scalar(
                select(SupplierProduct).where(
                    SupplierProduct.supplier_id == supplier.id,
                    SupplierProduct.product_id == product.id,
                )
            )
            source_price = (
                association.supplier_price
                if association is not None and association.supplier_price is not None
                else line.unit_price
            )
            if source_price is None:
                source_price = product.purchase_price

            unit_price = Decimal(str(source_price)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_price = (unit_price * line.quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            normalized_items.append((product, association, line, unit_price, total_price))

        order = PurchaseOrder(
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            user_id=current_user.id,
            order_date=datetime.utcnow(),
            expected_delivery_date=payload.expected_delivery_date,
            status="DRAFT",
            total_amount=sum((item[4] for item in normalized_items), Decimal("0.00")),
            notes=payload.notes,
        )
        db.add(order)
        db.flush()

        for product, association, line, unit_price, total_price in normalized_items:
            if association is None:
                db.add(
                    SupplierProduct(
                        supplier_id=supplier.id,
                        product_id=product.id,
                        supplier_price=unit_price,
                    )
                )
            order.items.append(
                PurchaseOrderItem(
                    purchase_order_id=order.id,
                    product_id=product.id,
                    quantity=line.quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                )
            )

        db.flush()
        response = PurchaseOrderWorkflowResponse.model_validate(order).model_dump(mode="json")
        db.commit()
        return response
    except Exception:
        db.rollback()
        raise


@router.patch("/{purchase_order_id}")
@router.put("/{purchase_order_id}")
def update_purchase_order(
    purchase_order_id: int,
    payload: PurchaseOrderUpdate,
    db: Session = Depends(get_db),
    _authorized=Depends(require_roles("purchase_manager")),
):
    try:
        order = db.scalar(select(PurchaseOrder).where(
            PurchaseOrder.id == purchase_order_id,
        ).with_for_update())
        if order is None:
            raise HTTPException(status_code=404, detail="Purchase order not found")
        if order.status.upper() != "DRAFT":
            raise HTTPException(status_code=409, detail="Only draft purchase orders can be edited")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(order, field, value)
        db.commit()
        db.refresh(order)
        return PurchaseOrderResponse.model_validate(order).model_dump(mode="json")
    except Exception:
        db.rollback()
        raise
