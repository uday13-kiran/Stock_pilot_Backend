"""Transaction-oriented workflows for StockPilot.

These endpoints coordinate parent records, line items, inventory balances and the stock ledger.
All writes are committed atomically within one SQLAlchemy transaction.
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.stock_transaction import StockTransaction
from app.models.products import Product
from app.models.warehouse import Warehouse
from app.models.purchase_order import PurchaseOrder
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.supplier_products import SupplierProduct
from app.models.goods_receipt import GoodsReceipt
from app.models.goods_receipt_item import GoodsReceiptItem
from app.models.reorder_rule import ReorderRule
from app.models.stock_alert import StockAlert
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.payment import Payment
from app.models.sales_return import SalesReturn
from app.models.sales_return_item import SalesReturnItem
from app.models.stock_transfer import StockTransfer
from app.models.stock_transfer_item import StockTransferItem
from app.models.customer import Customer
from app.models.user import User
from app.core.dependencies import get_current_user, require_roles
from app.core.operational_events import record_event

router = APIRouter(tags=["Business Workflows"])

class ReceiptLine(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)  # accepted for compatibility; server uses PO price
class ReceivePurchaseRequest(BaseModel):
    warehouse_id: int = Field(gt=0)
    items: list[ReceiptLine] = Field(min_length=1)
    notes: str | None = None

class CheckoutLine(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
class CheckoutRequest(BaseModel):
    customer_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    items: list[CheckoutLine] = Field(min_length=1)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    payment_method: str | None = None

class TransferLine(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
class TransferItemsRequest(BaseModel):
    items: list[TransferLine] = Field(min_length=1)

class ReturnLine(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
class ApproveReturnRequest(BaseModel):
    warehouse_id: int = Field(gt=0)
    items: list[ReturnLine] = Field(min_length=1)

def _inventory(db: Session, product_id: int, warehouse_id: int) -> Inventory:
    row = db.scalar(select(Inventory).where(Inventory.product_id == product_id, Inventory.warehouse_id == warehouse_id).with_for_update())
    if row is None:
        row = Inventory(product_id=product_id, warehouse_id=warehouse_id, quantity=0, reserved_quantity=0, available_quantity=0)
        db.add(row); db.flush()
    return row

def _ledger(db: Session, product_id: int, warehouse_id: int, kind: str, quantity: int, ref_type: str, ref_id: int):
    db.add(StockTransaction(product_id=product_id, warehouse_id=warehouse_id, transaction_type=kind, quantity=quantity, reference_type=ref_type, reference_id=ref_id))

def _change_stock(db: Session, product_id: int, warehouse_id: int, delta: int, kind: str, ref_type: str, ref_id: int):
    product = db.get(Product, product_id)
    if product is None: raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    if db.get(Warehouse, warehouse_id) is None: raise HTTPException(status_code=404, detail=f"Warehouse {warehouse_id} not found")
    row = _inventory(db, product_id, warehouse_id)
    if delta < 0 and -delta > row.available_quantity:
        raise HTTPException(status_code=409, detail=f"Insufficient unreserved stock for product {product_id}")
    if row.quantity + delta < row.reserved_quantity:
        raise HTTPException(status_code=409, detail=f"Movement would consume reserved stock for product {product_id}")
    row.quantity += delta
    row.available_quantity = row.quantity - row.reserved_quantity
    rule = db.scalar(select(ReorderRule).where(
        ReorderRule.product_id == product_id,
        ReorderRule.warehouse_id == warehouse_id,
    ))
    reorder_level = rule.reorder_level if rule else product.reorder_level
    safety_stock = rule.safety_stock if rule else product.safety_stock
    alert = db.scalar(select(StockAlert).where(
        StockAlert.product_id == product_id,
        StockAlert.warehouse_id == warehouse_id,
        StockAlert.is_resolved.is_(False),
    ).with_for_update())
    if row.available_quantity <= reorder_level:
        severity = "CRITICAL" if row.available_quantity <= safety_stock else "LOW"
        if alert is None:
            db.add(StockAlert(
                product_id=product_id,
                warehouse_id=warehouse_id,
                current_stock=row.available_quantity,
                reorder_level=reorder_level,
                severity=severity,
                alert_type="LOW_STOCK",
                is_resolved=False,
            ))
        else:
            alert.current_stock = row.available_quantity
            alert.reorder_level = reorder_level
            alert.severity = severity
    elif alert is not None:
        alert.is_resolved = True
    _ledger(db, product_id, warehouse_id, kind, delta, ref_type, ref_id)
    return row

@router.post("/purchase-orders/{purchase_order_id}/approve")
def approve_purchase_order(purchase_order_id: int, db: Session = Depends(get_db), _authorized = Depends(require_roles("purchase_manager"))):
    try:
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id).with_for_update())
        if po is None: raise HTTPException(status_code=404, detail="Purchase order not found")
        if po.status.upper() != "DRAFT": raise HTTPException(status_code=409, detail=f"Only draft purchase orders can be approved; current status is {po.status}")
        if po.warehouse_id is None: raise HTTPException(status_code=409, detail="Purchase order must have a destination warehouse before approval")
        if db.get(Warehouse, po.warehouse_id) is None: raise HTTPException(status_code=404, detail="Purchase order warehouse not found")
        items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id).with_for_update()).all()
        if not items: raise HTTPException(status_code=409, detail="Purchase order has no line items")
        for item in items:
            if item.quantity <= 0 or item.received_quantity != 0:
                raise HTTPException(status_code=409, detail=f"Purchase order item for product {item.product_id} is invalid for approval")
            association = db.scalar(select(SupplierProduct.id).where(
                SupplierProduct.supplier_id == po.supplier_id,
                SupplierProduct.product_id == item.product_id,
            ))
            if association is None:
                raise HTTPException(status_code=409, detail=f"Product {item.product_id} is not associated with this supplier")
        po.status = "APPROVED"
        db.commit()
        return {"purchase_order_id": po.id, "status": po.status}
    except Exception:
        db.rollback()
        raise

@router.post("/purchase-orders/{purchase_order_id}/receive")
def receive_purchase_order(purchase_order_id: int, payload: ReceivePurchaseRequest, db: Session = Depends(get_db), _authorized = Depends(require_roles(*("purchase_manager", "inventory_manager", "warehouse_staff")))):
    """Receive some/all remaining quantities on a PO and post inventory atomically."""
    try:
        po = db.scalar(select(PurchaseOrder).where(PurchaseOrder.id == purchase_order_id).with_for_update())
        if po is None: raise HTTPException(status_code=404, detail="Purchase order not found")
        if po.status.upper() not in {"APPROVED", "ORDERED", "PARTIALLY_RECEIVED"}: raise HTTPException(status_code=409, detail=f"Purchase order must be approved before receiving; current status is {po.status}")
        warehouse = db.get(Warehouse, payload.warehouse_id)
        if warehouse is None: raise HTTPException(status_code=404, detail="Warehouse not found")
        if po.warehouse_id is not None and po.warehouse_id != payload.warehouse_id:
            raise HTTPException(status_code=409, detail="Receipt warehouse must match the purchase order destination warehouse")
        if po.warehouse_id is None:
            po.warehouse_id = payload.warehouse_id
        po_items = {item.product_id: item for item in db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id).with_for_update()).all()}
        if not po_items: raise HTTPException(status_code=409, detail="Purchase order has no line items")
        receipt = GoodsReceipt(purchase_order_id=po.id, warehouse_id=payload.warehouse_id, received_date=datetime.utcnow(), status="POSTED", notes=payload.notes)
        db.add(receipt); db.flush()
        for line in payload.items:
            po_item = po_items.get(line.product_id)
            if po_item is None: raise HTTPException(status_code=422, detail=f"Product {line.product_id} is not on this purchase order")
            remaining = po_item.quantity - po_item.received_quantity
            if line.quantity > remaining: raise HTTPException(status_code=409, detail=f"Receipt quantity exceeds remaining ordered quantity for product {line.product_id}")
            price = Decimal(str(po_item.unit_price))
            total = (price * line.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            db.add(GoodsReceiptItem(goods_receipt_id=receipt.id, product_id=line.product_id, quantity=line.quantity, unit_price=price, total_price=total))
            po_item.received_quantity += line.quantity
            _change_stock(db, line.product_id, payload.warehouse_id, line.quantity, "PURCHASE_RECEIPT", "goods_receipt", receipt.id)
        db.flush()
        all_items = db.scalars(select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)).all()
        po.status = "RECEIVED" if all(i.received_quantity >= i.quantity for i in all_items) else "PARTIALLY_RECEIVED"
        db.commit(); db.refresh(receipt)
        record_event("purchase.received", "goods_receipt", receipt.id, {"purchase_order_id": po.id, "warehouse_id": payload.warehouse_id, "item_count": len(payload.items), "status": po.status})
        return {"goods_receipt_id": receipt.id, "purchase_order_id": po.id, "purchase_order_status": po.status, "message": "Goods received and stock ledger updated"}
    except Exception:
        db.rollback(); raise

@router.post("/sales/checkout")
def checkout_sale(payload: CheckoutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), _authorized = Depends(require_roles(*("sales_staff",)))):
    """Create sale, invoice and optional payment in one transaction using server-side prices/tax."""
    try:
        if db.get(Customer, payload.customer_id) is None:
            raise HTTPException(status_code=404, detail="Customer not found")
        if not current_user.is_active:
            raise HTTPException(status_code=403, detail="Inactive users cannot create sales")
        if db.get(Warehouse, payload.warehouse_id) is None:
            raise HTTPException(status_code=404, detail="Warehouse not found")

        product_ids = [line.product_id for line in payload.items]
        if len(product_ids) != len(set(product_ids)):
            raise HTTPException(status_code=422, detail="Each product may appear only once per checkout")

        subtotal = Decimal("0.00")
        line_discounts = Decimal("0.00")
        tax_total = Decimal("0.00")
        normalized = []
        for line in payload.items:
            product = db.get(Product, line.product_id)
            if product is None:
                raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
            inv = db.scalar(select(Inventory).where(
                Inventory.product_id == line.product_id,
                Inventory.warehouse_id == payload.warehouse_id,
            ).with_for_update())
            if inv is None or inv.available_quantity < line.quantity:
                raise HTTPException(status_code=409, detail=f"Insufficient available stock for product {line.product_id}")

            # Price and tax rate are taken from the product master, never trusted from the client.
            unit_price = Decimal(str(product.selling_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gross = (unit_price * line.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            discount = Decimal(str(line.discount_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if discount > gross:
                raise HTTPException(status_code=422, detail=f"Discount exceeds line amount for product {line.product_id}")
            taxable = gross - discount
            tax_rate = Decimal(str(product.tax_percent))
            line_tax = (taxable * tax_rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            line_total = taxable + line_tax
            subtotal += gross
            line_discounts += discount
            tax_total += line_tax
            normalized.append((line, unit_price, discount, line_tax, line_total))

        global_discount = Decimal(str(payload.discount_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if global_discount + line_discounts > subtotal:
            raise HTTPException(status_code=422, detail="Total discounts cannot exceed the subtotal")
        # Apply a global discount after line-level tax calculation; its tax treatment is intentionally
        # conservative and should be confirmed against the business's jurisdictional tax rules.
        total = (subtotal - line_discounts - global_discount + tax_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if total < 0:
            raise HTTPException(status_code=422, detail="Sale total cannot be negative")

        sale = Sale(
            customer_id=payload.customer_id,
            user_id=current_user.id,
            warehouse_id=payload.warehouse_id,
            sale_date=datetime.utcnow(),
            subtotal=float(subtotal),
            discount_amount=float(line_discounts + global_discount),
            tax_amount=float(tax_total),
            total_amount=float(total),
            status="COMPLETED",
        )
        db.add(sale)
        db.flush()
        inventory_updates = []
        for line, unit_price, discount, line_tax, line_total in normalized:
            db.add(SaleItem(
                sale_id=sale.id, product_id=line.product_id, quantity=line.quantity,
                unit_price=float(unit_price), discount_amount=float(discount),
                tax_amount=float(line_tax), total_price=float(line_total),
            ))
            inventory = _change_stock(
                db, line.product_id, payload.warehouse_id, -line.quantity, "SALE", "sale", sale.id
            )
            inventory_updates.append({
                "product_id": line.product_id,
                "quantity": inventory.quantity,
                "reserved_quantity": inventory.reserved_quantity,
                "available_quantity": inventory.available_quantity,
            })

        invoice = Invoice(
            sale_id=sale.id, invoice_date=datetime.utcnow(), subtotal=float(subtotal),
            tax_amount=float(tax_total), total_amount=float(total), status="ISSUED",
        )
        db.add(invoice)
        db.flush()
        for line, unit_price, discount, line_tax, line_total in normalized:
            db.add(InvoiceItem(invoice_id=invoice.id, product_id=line.product_id, quantity=line.quantity,
                               unit_price=float(unit_price), total_price=float(line_total)))
        if payload.payment_method:
            method = payload.payment_method.strip().upper()
            allowed_methods = {"CASH", "CARD", "UPI", "BANK_TRANSFER", "CREDIT"}
            if method not in allowed_methods:
                raise HTTPException(status_code=422, detail="Unsupported payment method")
            db.add(Payment(invoice_id=invoice.id, amount=float(total), payment_method=method,
                           payment_date=datetime.utcnow(), status="PAID"))
            invoice.status = "PAID"
        db.commit()
        record_event("sale.completed", "sale", sale.id, {"invoice_id": invoice.id, "warehouse_id": payload.warehouse_id, "item_count": len(payload.items), "total_amount": str(total)})
        return {
            "sale_id": sale.id, "invoice_id": invoice.id, "subtotal": str(subtotal),
            "discount_amount": str(line_discounts + global_discount), "tax_amount": str(tax_total),
            "total_amount": str(total), "status": sale.status,
            "invoice_status": invoice.status,
            "payment_recorded": bool(payload.payment_method),
            "pricing_source": "product master", "tax_source": "product tax_percent",
            "warehouse_id": payload.warehouse_id,
            "inventory_updates": inventory_updates,
        }
    except Exception:
        db.rollback()
        raise

@router.post("/stock-transfers/{transfer_id}/items")
def add_transfer_items(transfer_id: int, payload: TransferItemsRequest, db: Session = Depends(get_db), _authorized = Depends(require_roles(*("inventory_manager", "warehouse_staff")))):
    try:
        transfer = db.scalar(select(StockTransfer).where(StockTransfer.id == transfer_id).with_for_update())
        if transfer is None: raise HTTPException(status_code=404, detail="Stock transfer not found")
        if transfer.status.upper() not in {"REQUESTED", "APPROVED"}: raise HTTPException(status_code=409, detail="Items can only be added before dispatch")
        for line in payload.items:
            if db.get(Product, line.product_id) is None: raise HTTPException(status_code=404, detail=f"Product {line.product_id} not found")
            existing = db.scalar(select(StockTransferItem).where(StockTransferItem.transfer_id == transfer_id, StockTransferItem.product_id == line.product_id))
            if existing: existing.requested_quantity += line.quantity
            else: db.add(StockTransferItem(transfer_id=transfer_id, product_id=line.product_id, requested_quantity=line.quantity, dispatched_quantity=0, received_quantity=0))
        db.commit(); return {"transfer_id": transfer_id, "message": "Transfer items saved"}
    except Exception: db.rollback(); raise

@router.post("/stock-transfers/{transfer_id}/approve")
def approve_transfer(transfer_id: int, db: Session = Depends(get_db), _authorized = Depends(require_roles(*("inventory_manager",)))):
    transfer=db.scalar(select(StockTransfer).where(StockTransfer.id==transfer_id).with_for_update())
    if transfer is None: raise HTTPException(status_code=404,detail="Stock transfer not found")
    if transfer.status.upper() != "REQUESTED": raise HTTPException(status_code=409,detail="Only requested transfers can be approved")
    if not db.scalar(select(StockTransferItem.id).where(StockTransferItem.transfer_id==transfer_id).limit(1)): raise HTTPException(status_code=409,detail="Add transfer items before approval")
    transfer.status="APPROVED"; db.commit(); return {"transfer_id":transfer_id,"status":transfer.status}

@router.post("/stock-transfers/{transfer_id}/dispatch")
def dispatch_transfer(transfer_id: int, db: Session = Depends(get_db), _authorized = Depends(require_roles(*("inventory_manager", "warehouse_staff")))):
    try:
        transfer=db.scalar(select(StockTransfer).where(StockTransfer.id==transfer_id).with_for_update())
        if transfer is None: raise HTTPException(status_code=404,detail="Stock transfer not found")
        if transfer.status.upper() != "APPROVED": raise HTTPException(status_code=409,detail="Transfer must be approved before dispatch")
        items=db.scalars(select(StockTransferItem).where(StockTransferItem.transfer_id==transfer_id).with_for_update()).all()
        if not items: raise HTTPException(status_code=409,detail="Transfer has no items")
        for item in items:
            _change_stock(db,item.product_id,transfer.from_warehouse_id,-item.requested_quantity,"TRANSFER_OUT","stock_transfer",transfer.id)
            item.dispatched_quantity=item.requested_quantity
        transfer.status="IN_TRANSIT"; db.commit()
        record_event("transfer.dispatched", "stock_transfer", transfer.id, {"from_warehouse_id": transfer.from_warehouse_id, "to_warehouse_id": transfer.to_warehouse_id, "item_count": len(items)})
        return {"transfer_id":transfer_id,"status":transfer.status}
    except Exception: db.rollback(); raise

@router.post("/stock-transfers/{transfer_id}/receive")
def receive_transfer(transfer_id: int, db: Session = Depends(get_db), _authorized = Depends(require_roles(*("inventory_manager", "warehouse_staff")))):
    try:
        transfer=db.scalar(select(StockTransfer).where(StockTransfer.id==transfer_id).with_for_update())
        if transfer is None: raise HTTPException(status_code=404,detail="Stock transfer not found")
        if transfer.status.upper() != "IN_TRANSIT": raise HTTPException(status_code=409,detail="Transfer must be in transit before receiving")
        items=db.scalars(select(StockTransferItem).where(StockTransferItem.transfer_id==transfer_id).with_for_update()).all()
        for item in items:
            _change_stock(db,item.product_id,transfer.to_warehouse_id,item.dispatched_quantity,"TRANSFER_IN","stock_transfer",transfer.id)
            item.received_quantity=item.dispatched_quantity
        transfer.status="RECEIVED"; db.commit()
        record_event("transfer.received", "stock_transfer", transfer.id, {"from_warehouse_id": transfer.from_warehouse_id, "to_warehouse_id": transfer.to_warehouse_id, "item_count": len(items)})
        return {"transfer_id":transfer_id,"status":transfer.status}
    except Exception: db.rollback(); raise

@router.post("/sales-returns/{return_id}/approve")
def approve_sales_return(return_id: int, payload: ApproveReturnRequest, db: Session = Depends(get_db), _authorized = Depends(require_roles(*("sales_staff", "finance_billing_staff")))):
    try:
        ret=db.scalar(select(SalesReturn).where(SalesReturn.id==return_id).with_for_update())
        if ret is None: raise HTTPException(status_code=404,detail="Sales return not found")
        if ret.status.upper() not in {"REQUESTED", "PENDING"}: raise HTTPException(status_code=409,detail="Return is not awaiting approval")
        sale=db.get(Sale,ret.sale_id)
        if sale is None: raise HTTPException(status_code=404,detail="Original sale not found")
        if len({line.product_id for line in payload.items}) != len(payload.items):
            raise HTTPException(status_code=422, detail="Each product may appear only once per return approval")
        for line in payload.items:
            sold=int(db.scalar(select(func.coalesce(func.sum(SaleItem.quantity),0)).where(SaleItem.sale_id==sale.id,SaleItem.product_id==line.product_id)) or 0)
            previously_returned=int(db.scalar(select(func.coalesce(func.sum(SalesReturnItem.quantity),0)).join(SalesReturn,SalesReturn.id==SalesReturnItem.return_id).where(SalesReturn.sale_id==sale.id,SalesReturnItem.product_id==line.product_id,SalesReturn.status=="APPROVED")) or 0)
            if line.quantity > sold-previously_returned: raise HTTPException(status_code=409,detail=f"Return quantity exceeds remaining sold quantity for product {line.product_id}")
            sold_item=db.scalar(select(SaleItem).where(SaleItem.sale_id==sale.id,SaleItem.product_id==line.product_id))
            db.add(SalesReturnItem(return_id=ret.id,product_id=line.product_id,quantity=line.quantity,unit_price=sold_item.unit_price,total_price=sold_item.unit_price*line.quantity))
            _change_stock(db,line.product_id,payload.warehouse_id,line.quantity,"SALES_RETURN","sales_return",ret.id)
        ret.status="APPROVED"; db.commit()
        record_event("sales_return.approved", "sales_return", ret.id, {"sale_id": sale.id, "warehouse_id": payload.warehouse_id, "item_count": len(payload.items)})
        return {"return_id":return_id,"status":ret.status,"message":"Returned goods added back to stock"}
    except Exception: db.rollback(); raise
