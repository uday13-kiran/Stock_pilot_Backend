from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.inventory import Inventory
from app.models.stock_transaction import StockTransaction
from app.models.products import Product
from app.models.warehouse import Warehouse
from app.models.stock_transfer import StockTransfer
from app.models.stock_transfer_item import StockTransferItem
from app.models.goods_receipt import GoodsReceipt
from app.models.goods_receipt_item import GoodsReceiptItem
from app.models.purchase_order import PurchaseOrder
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.customer import Customer
from datetime import datetime

router = APIRouter(prefix="/inventory", tags=["Inventory Movements"])
class MovementIn(BaseModel):
    product_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    reason: str | None = None
class TransferIn(BaseModel):
    from_warehouse_id: int = Field(gt=0)
    to_warehouse_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    notes: str | None = None

def _row(db, product_id, warehouse_id):
    row=db.scalar(select(Inventory).where(Inventory.product_id==product_id, Inventory.warehouse_id==warehouse_id).with_for_update())
    if row is None:
        row=Inventory(product_id=product_id, warehouse_id=warehouse_id, quantity=0, reserved_quantity=0, available_quantity=0)
        db.add(row); db.flush()
    return row
def _move(db, product_id, warehouse_id, delta, kind, reason=None, ref_type=None, ref_id=None):
    if not db.get(Product, product_id): raise HTTPException(status_code=404, detail="Product not found")
    if not db.get(Warehouse, warehouse_id): raise HTTPException(status_code=404, detail="Warehouse not found")
    row=_row(db,product_id,warehouse_id)
    if row.quantity + delta < 0: raise HTTPException(status_code=409, detail="Insufficient stock; negative inventory is prohibited")
    row.quantity += delta; row.available_quantity=max(0,row.quantity-row.reserved_quantity)
    db.add(StockTransaction(product_id=product_id, warehouse_id=warehouse_id, transaction_type=kind, quantity=delta, reference_type=ref_type or reason, reference_id=ref_id))
    return row
@router.post("/stock-in")
def stock_in(payload: MovementIn, db: Session = Depends(get_db)):
    try:
        row=_move(db,payload.product_id,payload.warehouse_id,payload.quantity,"STOCK_IN",payload.reason); db.commit(); db.refresh(row); return {"message":"Stock added","inventory_id":row.id,"quantity":row.quantity}
    except Exception: db.rollback(); raise
@router.post("/stock-out")
def stock_out(payload: MovementIn, db: Session = Depends(get_db)):
    try:
        row=_move(db,payload.product_id,payload.warehouse_id,-payload.quantity,"STOCK_OUT",payload.reason); db.commit(); db.refresh(row); return {"message":"Stock deducted","inventory_id":row.id,"quantity":row.quantity}
    except Exception: db.rollback(); raise
@router.post("/adjust")
def adjust_stock(payload: MovementIn, db: Session = Depends(get_db)):
    try:
        row=_row(db,payload.product_id,payload.warehouse_id); delta=payload.quantity-row.quantity
        _move(db,payload.product_id,payload.warehouse_id,delta,"ADJUSTMENT",payload.reason); db.commit(); db.refresh(row); return {"message":"Stock adjusted","inventory_id":row.id,"quantity":row.quantity}
    except Exception: db.rollback(); raise
@router.post("/transfers")
def transfer_stock(payload: TransferIn, db: Session = Depends(get_db)):
    if payload.from_warehouse_id == payload.to_warehouse_id: raise HTTPException(status_code=422, detail="Source and destination warehouses must differ")
    try:
        transfer=StockTransfer(from_warehouse_id=payload.from_warehouse_id,to_warehouse_id=payload.to_warehouse_id,transfer_date=datetime.utcnow(),status="RECEIVED",notes=payload.notes); db.add(transfer); db.flush()
        _move(db,payload.product_id,payload.from_warehouse_id,-payload.quantity,"TRANSFER_OUT",payload.notes,"stock_transfer",transfer.id)
        _move(db,payload.product_id,payload.to_warehouse_id,payload.quantity,"TRANSFER_IN",payload.notes,"stock_transfer",transfer.id)
        db.add(StockTransferItem(transfer_id=transfer.id,product_id=payload.product_id,requested_quantity=payload.quantity,dispatched_quantity=payload.quantity,received_quantity=payload.quantity))
        db.commit(); db.refresh(transfer); return {"transfer_id":transfer.id,"status":transfer.status,"quantity":payload.quantity}
    except Exception: db.rollback(); raise
@router.get("/transactions")
def transactions(product_id: int | None = None, warehouse_id: int | None = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    if skip < 0 or not 1 <= limit <= 500: raise HTTPException(status_code=422, detail="Invalid pagination")
    stmt=select(StockTransaction).order_by(StockTransaction.created_at.desc()).offset(skip).limit(limit)
    if product_id is not None: stmt=stmt.where(StockTransaction.product_id==product_id)
    if warehouse_id is not None: stmt=stmt.where(StockTransaction.warehouse_id==warehouse_id)
    rows=db.scalars(stmt).all()
    return [{"id":r.id,"product_id":r.product_id,"warehouse_id":r.warehouse_id,"transaction_type":r.transaction_type,"quantity":r.quantity,"reference_type":r.reference_type,"reference_id":r.reference_id,"created_at":r.created_at} for r in rows]
