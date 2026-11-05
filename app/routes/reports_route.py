from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models.inventory import Inventory
from app.models.products import Product
from app.models.sales import Sale
from app.models.purchase_order import PurchaseOrder
from app.models.stock_transaction import StockTransaction
from app.models.demand_forecast import DemandForecast
from app.routes.planning_route import refresh_purchase_recommendations as refresh_demand_based_recommendations

router=APIRouter(prefix="/reports",tags=["Reports & Planning"])
@router.get("/inventory-summary")
def inventory_summary(db: Session=Depends(get_db)):
    rows=db.execute(select(Inventory.product_id,Inventory.warehouse_id,Inventory.quantity,Inventory.reserved_quantity,Inventory.available_quantity)).all()
    product_count=db.scalar(select(func.count(Product.id))) or 0
    stocked_product_count=db.scalar(
        select(func.count(func.distinct(Inventory.product_id))).where(Inventory.available_quantity > 0)
    ) or 0
    return {"record_count":len(rows),"product_count":product_count,"stocked_product_count":stocked_product_count,"total_units":sum(r.quantity for r in rows),"total_available_units":sum(r.available_quantity for r in rows),"items":[{"product_id":r.product_id,"warehouse_id":r.warehouse_id,"quantity":r.quantity,"reserved_quantity":r.reserved_quantity,"available_quantity":r.available_quantity} for r in rows]}
@router.get("/sales-summary")
def sales_summary(db: Session=Depends(get_db)):
    row=db.execute(select(func.count(Sale.id),func.coalesce(func.sum(Sale.total_amount),0))).one()
    return {"sales_count":row[0],"sales_total":float(row[1] or 0)}
@router.get("/purchase-summary")
def purchase_summary(db: Session=Depends(get_db)):
    row=db.execute(select(func.count(PurchaseOrder.id),func.coalesce(func.sum(PurchaseOrder.total_amount),0))).one()
    return {"purchase_order_count":row[0],"purchase_order_total":float(row[1] or 0)}
@router.get("/stock-movements")
def stock_movements(db: Session=Depends(get_db)):
    rows=db.execute(select(StockTransaction.transaction_type,func.count(StockTransaction.id),func.coalesce(func.sum(StockTransaction.quantity),0)).group_by(StockTransaction.transaction_type)).all()
    return [{"transaction_type":r[0],"count":r[1],"net_quantity":r[2]} for r in rows]
@router.post("/refresh-reorder-recommendations")
def refresh_reorder_recommendations(db: Session=Depends(get_db), _authorized=Depends(require_roles("inventory_manager", "purchase_manager"))):
    result = refresh_demand_based_recommendations(
        planning_days=7,
        lookback_days=90,
        warehouse_id=None,
        db=db,
    )
    return {
        "message": result["message"],
        "new_or_updated_recommendations": result["created_or_updated"],
        "method": result["method"],
    }
@router.post("/forecast/{product_id}")
def forecast_product(product_id: int, warehouse_id: int | None = None, periods: int = 1, db: Session=Depends(get_db)):
    if periods < 1 or periods > 24: raise HTTPException(status_code=422,detail="periods must be between 1 and 24")
    if not db.get(Product,product_id): raise HTTPException(status_code=404,detail="Product not found")
    # Baseline forecast: mean historical sale quantity per sale record; explicitly not ML.
    from app.models.sales_item import SaleItem
    from app.models.sales import Sale
    stmt=select(func.avg(SaleItem.quantity)).join(Sale,SaleItem.sale_id==Sale.id).where(SaleItem.product_id==product_id)
    if warehouse_id is not None: stmt=stmt.where(Sale.warehouse_id==warehouse_id)
    average=float(db.scalar(stmt) or 0)
    outputs=[]
    for n in range(1,periods+1):
        obj=DemandForecast(product_id=product_id,warehouse_id=warehouse_id,forecast_period=f"period_{n}",predicted_demand=round(average,2),forecast_method="historical_mean_baseline"); db.add(obj); outputs.append({"period":obj.forecast_period,"predicted_demand":obj.predicted_demand})
    db.commit(); return {"product_id":product_id,"warehouse_id":warehouse_id,"method":"historical_mean_baseline","warning":"Baseline estimate, not a trained ML forecast","forecasts":outputs}
