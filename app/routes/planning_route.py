"""Demand planning endpoints: forecast, stockout risk, dead stock and reorder guidance.

These are transparent statistical baselines, not claims of trained AI/ML.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.demand_forecast import DemandForecast
from app.models.inventory import Inventory
from app.models.products import Product
from app.models.purchase_order import PurchaseOrder
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.sales_return import SalesReturn
from app.models.sales_return_item import SalesReturnItem
from app.models.reorder_rule import ReorderRule
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.stock_alert import StockAlert
from app.models.purchase_recommendation import PurchaseRecommendation
from app.models.warehouse import Warehouse
from app.services.forecast_service import (
    SUPPORTED_METHODS,
    backtest_product_demand,
    forecast_product_demand,
)

router = APIRouter(prefix="/planning", tags=["Demand Planning"])
COMPLETED_SALE_STATUSES = ("COMPLETED", "COMPLETE", "PAID")


class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    warehouse_id: int | None = Field(default=None, gt=0)
    lookback_days: int = Field(default=90, ge=7, le=365)
    inactive_days: int = Field(default=90, ge=30, le=730)
    planning_days: int = Field(default=7, ge=1, le=180)


def _daily_demand(db: Session, product_id: int, warehouse_id: int | None, lookback_days: int) -> float:
    """Average net completed units sold per calendar day, including zero-sale days."""
    start = datetime.utcnow() - timedelta(days=lookback_days)
    stmt = (
        select(func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            SaleItem.product_id == product_id,
            Sale.sale_date >= start,
            Sale.status.in_(COMPLETED_SALE_STATUSES),
        )
    )
    if warehouse_id is not None:
        stmt = stmt.where(Sale.warehouse_id == warehouse_id)
    sold = float(db.scalar(stmt) or 0)
    returns_stmt = (
        select(func.coalesce(func.sum(SalesReturnItem.quantity), 0))
        .join(SalesReturn, SalesReturn.id == SalesReturnItem.return_id)
        .join(Sale, Sale.id == SalesReturn.sale_id)
        .where(
            SalesReturnItem.product_id == product_id,
            SalesReturn.return_date >= start,
            SalesReturn.status == "APPROVED",
            Sale.status.in_(COMPLETED_SALE_STATUSES),
        )
    )
    if warehouse_id is not None:
        returns_stmt = returns_stmt.where(Sale.warehouse_id == warehouse_id)
    returned = float(db.scalar(returns_stmt) or 0)
    return max(0.0, sold - returned) / max(lookback_days, 1)


def _month_starts(today: date) -> tuple[date, date, date]:
    current_start = today.replace(day=1)
    previous_end = current_start
    previous_start = (previous_end - timedelta(days=1)).replace(day=1)
    earlier_end = previous_start
    earlier_start = (earlier_end - timedelta(days=1)).replace(day=1)
    return earlier_start, previous_start, previous_end


def _monthly_net_units(
    db: Session,
    start: date,
    end: date,
    warehouse_id: int | None,
) -> dict[int, int]:
    """Return completed sales less approved returns in [start, end)."""
    sales_stmt = (
        select(SaleItem.product_id, func.coalesce(func.sum(SaleItem.quantity), 0))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .where(
            Sale.sale_date >= datetime.combine(start, datetime.min.time()),
            Sale.sale_date < datetime.combine(end, datetime.min.time()),
            Sale.status.in_(COMPLETED_SALE_STATUSES),
        )
        .group_by(SaleItem.product_id)
    )
    returns_stmt = (
        select(SalesReturnItem.product_id, func.coalesce(func.sum(SalesReturnItem.quantity), 0))
        .join(SalesReturn, SalesReturn.id == SalesReturnItem.return_id)
        .join(Sale, Sale.id == SalesReturn.sale_id)
        .where(
            SalesReturn.return_date >= datetime.combine(start, datetime.min.time()),
            SalesReturn.return_date < datetime.combine(end, datetime.min.time()),
            SalesReturn.status == "APPROVED",
            Sale.status.in_(COMPLETED_SALE_STATUSES),
        )
        .group_by(SalesReturnItem.product_id)
    )
    if warehouse_id is not None:
        sales_stmt = sales_stmt.where(Sale.warehouse_id == warehouse_id)
        returns_stmt = returns_stmt.where(Sale.warehouse_id == warehouse_id)
    units = {product_id: int(quantity) for product_id, quantity in db.execute(sales_stmt)}
    for product_id, quantity in db.execute(returns_stmt):
        units[product_id] = units.get(product_id, 0) - int(quantity)
    return {product_id: max(quantity, 0) for product_id, quantity in units.items()}


def _product_trends(
    db: Session,
    warehouse_id: int | None,
    today: date | None = None,
) -> list[dict]:
    today = today or date.today()
    earlier_start, previous_start, current_start = _month_starts(today)
    previous = _monthly_net_units(db, earlier_start, previous_start, warehouse_id)
    current = _monthly_net_units(db, previous_start, current_start, warehouse_id)
    products = db.scalars(
        select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
    ).all()
    results = []
    for product in products:
        prior_units = previous.get(product.id, 0)
        current_units = current.get(product.id, 0)
        if prior_units == 0 and current_units == 0:
            continue
        if prior_units == 0:
            change = None
            direction = "NEW_DEMAND"
            summary = "Sales were recorded this month after no sales in the previous month."
        else:
            change = round((current_units - prior_units) / prior_units * 100, 1)
            direction = "INCREASING" if change > 5 else "DECREASING" if change < -5 else "STABLE"
            summary = f"Demand is {direction.lower()} {abs(change):g}% month-over-month."
        results.append(
            {
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "previous_month_units": prior_units,
                "current_month_units": current_units,
                "month_over_month_percent": change,
                "trend": direction,
                "summary": summary,
            }
        )
    results.sort(
        key=lambda item: (
            item["month_over_month_percent"] is None,
            -(item["month_over_month_percent"] or 0),
        )
    )
    return results


def _forecast_stockout_days(available: int, forecast_daily: list[float], fallback_daily: float) -> float | None:
    if available <= 0:
        return 0.0
    remaining = float(available)
    for day_number, demand in enumerate(forecast_daily, start=1):
        demand = max(float(demand), 0.0)
        if demand == 0:
            continue
        before = remaining
        remaining -= demand
        if remaining <= 0:
            return round(day_number - before / demand, 1)
    if fallback_daily > 0:
        return round(available / fallback_daily, 1)
    return None


def _purchase_planning_rows(
    db: Session,
    planning_days: int,
    lookback_days: int,
    warehouse_id: int | None = None,
) -> list[dict]:
    rules_stmt = select(ReorderRule)
    inventory_stmt = select(Inventory)
    if warehouse_id is not None:
        rules_stmt = rules_stmt.where(ReorderRule.warehouse_id == warehouse_id)
        inventory_stmt = inventory_stmt.where(Inventory.warehouse_id == warehouse_id)
    targets = {
        (rule.product_id, rule.warehouse_id): {
            "reorder_level": rule.reorder_level,
            "safety_stock": rule.safety_stock,
            "maximum_stock": rule.maximum_stock,
        }
        for rule in db.scalars(rules_stmt).all()
    }
    inventories = {
        (row.product_id, row.warehouse_id): row
        for row in db.scalars(inventory_stmt).all()
    }
    for key in inventories:
        if key not in targets:
            product = db.get(Product, key[0])
            if product is not None:
                targets[key] = {
                    "reorder_level": product.reorder_level,
                    "safety_stock": product.safety_stock,
                    "maximum_stock": product.maximum_stock,
                }

    results = []
    for (product_id, target_warehouse_id), levels in targets.items():
        product = db.get(Product, product_id)
        warehouse = db.get(Warehouse, target_warehouse_id)
        if product is None or warehouse is None or not product.is_active:
            continue
        inventory = inventories.get((product_id, target_warehouse_id))
        available = inventory.available_quantity if inventory else 0
        incoming = _incoming_quantity(db, product_id, target_warehouse_id)
        daily = _daily_demand(db, product_id, target_warehouse_id, lookback_days)
        coverage_days = max(product.lead_time, 0) + planning_days
        forecast_days = min(max(coverage_days, 1), 180)
        forecast = forecast_product_demand(
            db=db,
            product_id=product_id,
            warehouse_id=target_warehouse_id,
            lookback_days=lookback_days,
            forecast_days=forecast_days,
            method="linear_regression",
        )
        projected_units = float(forecast["predicted_demand"])
        if coverage_days > forecast_days and forecast["predicted_daily_demand"]:
            projected_units += (
                coverage_days - forecast_days
            ) * forecast["predicted_daily_demand"][-1]
        forecast_units = int(
            Decimal(str(projected_units)).to_integral_value(
                rounding="ROUND_CEILING"
            )
        )
        target_stock = max(
            forecast_units + levels["safety_stock"], levels["reorder_level"]
        )
        if levels["maximum_stock"] > 0:
            target_stock = min(target_stock, levels["maximum_stock"])
        suggested = max(0, target_stock - available - incoming)
        stockout_days = _forecast_stockout_days(
            max(available + incoming, 0),
            forecast["predicted_daily_demand"],
            daily,
        )
        should_order_this_week = (
            suggested > 0
            and (
                available <= levels["reorder_level"]
                or stockout_days is not None
                and stockout_days <= product.lead_time + planning_days
            )
        )
        if available <= levels["safety_stock"] or (
            stockout_days is not None and stockout_days <= product.lead_time
        ):
            priority = "HIGH"
        elif available <= levels["reorder_level"] or should_order_this_week:
            priority = "MEDIUM"
        else:
            priority = "LOW"
        if stockout_days is None:
            stockout_date = None
        else:
            stockout_date = (date.today() + timedelta(days=stockout_days)).isoformat()
        if available <= levels["reorder_level"]:
            order_by_date = date.today().isoformat()
        elif stockout_days is None:
            order_by_date = None
        else:
            order_by_date = (
                date.today()
                + timedelta(days=max(0, stockout_days - product.lead_time))
            ).isoformat()
        results.append(
            {
                "product_id": product_id,
                "product_name": product.name,
                "sku": product.sku,
                "warehouse_id": target_warehouse_id,
                "warehouse_name": warehouse.name,
                "available_stock": available,
                "incoming_stock": incoming,
                "estimated_daily_demand": round(daily, 3),
                "forecast_demand": forecast_units,
                "coverage_days": coverage_days,
                "forecast_days": forecast_days,
                "lead_time_days": product.lead_time,
                "estimated_stockout_days": stockout_days,
                "estimated_stockout_date": stockout_date,
                "recommended_order_by_date": order_by_date,
                "suggested_quantity": suggested,
                "priority": priority,
                "should_order_this_week": should_order_this_week,
                "overstock": available > levels["maximum_stock"],
                "maximum_stock": levels["maximum_stock"],
                "reorder_level": levels["reorder_level"],
                "safety_stock": levels["safety_stock"],
                "reason": (
                    f"{forecast_units} units forecast over {coverage_days} days "
                    f"(including {product.lead_time}-day supplier lead time and "
                    f"{planning_days}-day review period); available {available}, "
                    f"incoming {incoming}, safety stock {levels['safety_stock']}."
                ),
            }
        )
    return results


def _dead_stock_items(
    db: Session, inactive_days: int, warehouse_id: int | None = None
) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=inactive_days)
    products = db.scalars(select(Product).where(Product.is_active.is_(True))).all()
    results = []
    for product in products:
        inventory_stmt = select(Inventory).where(Inventory.product_id == product.id)
        if warehouse_id is not None:
            inventory_stmt = inventory_stmt.where(Inventory.warehouse_id == warehouse_id)
        inventory_rows = db.scalars(inventory_stmt).all()
        for inventory in inventory_rows:
            if inventory.available_quantity <= 0:
                continue
            last_sale = db.scalar(
                select(func.max(Sale.sale_date))
                .join(SaleItem, SaleItem.sale_id == Sale.id)
                .where(
                    SaleItem.product_id == product.id,
                    Sale.warehouse_id == inventory.warehouse_id,
                    Sale.status.in_(COMPLETED_SALE_STATUSES),
                )
            )
            if last_sale is None or last_sale < cutoff:
                days_since = (datetime.utcnow() - last_sale).days if last_sale else None
                warehouse = db.get(Warehouse, inventory.warehouse_id)
                results.append(
                    {
                        "product_id": product.id,
                        "sku": product.sku,
                        "product_name": product.name,
                        "warehouse_id": inventory.warehouse_id,
                        "warehouse_name": warehouse.name if warehouse else None,
                        "available_stock": inventory.available_quantity,
                        "last_sale_at": last_sale.isoformat() if last_sale else None,
                        "days_since_last_sale": days_since,
                        "inactive_days_threshold": inactive_days,
                        "suggested_action": "Review discount, transfer, supplier return, or clearance options",
                    }
                )
    return results


def _incoming_quantity(db: Session, product_id: int, warehouse_id: int | None) -> int:
    """Sum outstanding quantities from open purchase orders for the destination warehouse."""
    stmt = (
        select(func.coalesce(func.sum(PurchaseOrderItem.quantity - PurchaseOrderItem.received_quantity), 0))
        .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderItem.purchase_order_id)
        .where(
            PurchaseOrderItem.product_id == product_id,
            PurchaseOrder.status.in_(["APPROVED", "ORDERED", "PARTIALLY_RECEIVED", "SUBMITTED"]),
            PurchaseOrderItem.quantity > PurchaseOrderItem.received_quantity,
        )
    )
    if warehouse_id is not None:
        stmt = stmt.where(PurchaseOrder.warehouse_id == warehouse_id)
    return int(db.scalar(stmt) or 0)


@router.get("/stockout-predictions")
def stockout_predictions(
    warehouse_id: int | None = Query(default=None, gt=0),
    lookback_days: int = Query(default=30, ge=7, le=365),
    db: Session = Depends(get_db),
):
    query = select(Inventory)
    if warehouse_id is not None:
        query = query.where(Inventory.warehouse_id == warehouse_id)
    inventory_rows = db.scalars(query).all()
    results = []
    for inv in inventory_rows:
        daily = _daily_demand(db, inv.product_id, inv.warehouse_id, lookback_days)
        incoming = _incoming_quantity(db, inv.product_id, inv.warehouse_id)
        effective = max(inv.available_quantity, 0) + incoming
        days_left = round(effective / daily, 1) if daily > 0 else None
        product = db.get(Product, inv.product_id)
        warehouse = db.get(Warehouse, inv.warehouse_id)
        lead_time = product.lead_time if product else 0
        results.append({
            "product_id": inv.product_id,
            "product_name": product.name if product else None,
            "warehouse_id": inv.warehouse_id,
            "warehouse_name": warehouse.name if warehouse else None,
            "available_stock": inv.available_quantity,
            "estimated_daily_demand": round(daily, 3),
            "known_incoming_stock": incoming,
            "estimated_days_until_stockout": days_left,
            "estimated_stockout_date": (date.today() + timedelta(days=days_left)).isoformat() if days_left is not None else None,
            "supplier_lead_time_days": product.lead_time if product else None,
            "recommended_order_now": bool(product and daily > 0 and days_left is not None and days_left <= lead_time + 7),
            "risk": "NO_RECENT_DEMAND" if daily == 0 else ("HIGH" if days_left is not None and days_left <= lead_time else "MEDIUM" if days_left is not None and days_left <= lead_time + 7 else "LOW"),
            "method": f"{lookback_days}-day net completed-sales daily average",
        })
    results.sort(key=lambda row: (row["estimated_days_until_stockout"] is None, row["estimated_days_until_stockout"] or float("inf")))
    return {"count": len(results), "predictions": results, "limitations": ["Estimates assume historical demand continues.", "Legacy purchase orders without a destination warehouse are not counted in warehouse-level incoming stock."]}


@router.get("/dead-stock")
def dead_stock(
    inactive_days: int = Query(default=90, ge=30, le=730),
    warehouse_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    results = _dead_stock_items(db, inactive_days, warehouse_id)
    return {"count": len(results), "items": results}


@router.post("/purchase-recommendations/refresh")
def refresh_purchase_recommendations(
    planning_days: int = Query(default=30, ge=1, le=180),
    lookback_days: int = Query(default=90, ge=7, le=365),
    warehouse_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    """Persist lead-time-aware suggestions using demand, inventory and incoming orders."""
    created_or_updated = 0
    try:
        rows = _purchase_planning_rows(db, planning_days, lookback_days, warehouse_id)
        for row in rows:
            product_id = row["product_id"]
            target_warehouse_id = row["warehouse_id"]
            recommendation = db.scalar(
                select(PurchaseRecommendation).where(
                    PurchaseRecommendation.product_id == product_id,
                    PurchaseRecommendation.warehouse_id == target_warehouse_id,
                )
            )
            should_save = (
                row["suggested_quantity"] > 0
                or recommendation is not None
            )
            if should_save:
                changed = False
                if recommendation is None:
                    recommendation = PurchaseRecommendation(
                        product_id=product_id,
                        warehouse_id=target_warehouse_id,
                        suggested_quantity=row["suggested_quantity"],
                        priority=row["priority"],
                        reason=row["reason"],
                    )
                    db.add(recommendation)
                    changed = True
                elif (
                    recommendation.suggested_quantity != row["suggested_quantity"]
                    or recommendation.priority != row["priority"]
                    or recommendation.reason != row["reason"]
                ):
                    recommendation.suggested_quantity = row["suggested_quantity"]
                    recommendation.priority = row["priority"]
                    recommendation.reason = row["reason"]
                    changed = True
                if changed:
                    created_or_updated += 1
            if row["available_stock"] <= row["reorder_level"]:
                alert = db.scalar(
                    select(StockAlert).where(
                        StockAlert.product_id == product_id,
                        StockAlert.warehouse_id == target_warehouse_id,
                        StockAlert.is_resolved.is_(False),
                    )
                )
                if alert is None:
                    db.add(
                        StockAlert(
                            product_id=product_id,
                            warehouse_id=target_warehouse_id,
                            current_stock=row["available_stock"],
                            reorder_level=row["reorder_level"],
                            severity="CRITICAL" if row["available_stock"] <= row["safety_stock"] else "LOW",
                            alert_type="LOW_STOCK",
                            is_resolved=False,
                        )
                    )
                else:
                    alert.current_stock = row["available_stock"]
                    alert.reorder_level = row["reorder_level"]
                    alert.severity = (
                        "CRITICAL"
                        if row["available_stock"] <= row["safety_stock"]
                        else "LOW"
                    )
        db.commit()
        return {
            "message": "Purchase recommendations refreshed",
            "created_or_updated": created_or_updated,
            "planning_days": planning_days,
            "lookback_days": lookback_days,
            "warehouse_id": warehouse_id,
            "method": "linear_regression_forecast + supplier_lead_time + safety_stock",
            "limitations": [
                "Legacy purchase orders without a destination warehouse are excluded from warehouse-specific incoming quantities.",
                "Forecasts assume future demand resembles recent net completed sales; backtest before relying on them.",
            ],
        }
    except Exception:
        db.rollback()
        raise


@router.get("/product-trends")
def product_trends(
    warehouse_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    earlier_start, previous_start, _ = _month_starts(date.today())
    return {
        "method": "completed monthly sales less approved returns",
        "comparison_periods": {
            "previous_month": earlier_start.strftime("%Y-%m"),
            "current_month": previous_start.strftime("%Y-%m"),
        },
        "warehouse_id": warehouse_id,
        "count": len(items := _product_trends(db, warehouse_id)),
        "items": items,
    }


@router.get("/purchase-planning")
def purchase_planning(
    planning_days: int = Query(default=7, ge=1, le=180),
    lookback_days: int = Query(default=90, ge=7, le=365),
    warehouse_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    rows = _purchase_planning_rows(db, planning_days, lookback_days, warehouse_id)
    recommendations = [
        row for row in rows
        if row["should_order_this_week"] and row["suggested_quantity"] > 0
    ]
    overstock = [row for row in rows if row["overstock"]]
    recommendations.sort(
        key=lambda row: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}[row["priority"]],
            row["estimated_stockout_days"] is None,
            row["estimated_stockout_days"] or float("inf"),
        )
    )
    return {
        "planning_days": planning_days,
        "lookback_days": lookback_days,
        "warehouse_id": warehouse_id,
        "recommendation_count": len(recommendations),
        "recommendations": recommendations,
        "overstock_count": len(overstock),
        "overstock": overstock,
        "method": "net completed sales forecast, supplier lead time, safety stock, current stock and open purchase orders",
        "limitations": [
            "Expected receipt dates are not modeled; known incoming quantities are treated as available for planning.",
            "Forecasts assume recent net completed-sales patterns continue.",
        ],
    }


@router.get("/assistant/insights")
def assistant_insights(
    warehouse_id: int | None = Query(default=None, gt=0),
    lookback_days: int = Query(default=90, ge=7, le=365),
    inactive_days: int = Query(default=90, ge=30, le=730),
    planning_days: int = Query(default=7, ge=1, le=180),
    db: Session = Depends(get_db),
):
    """Combined, rule-based inventory insights suitable for a chat/UI layer."""
    trends = _product_trends(db, warehouse_id)
    stockout = stockout_predictions(warehouse_id, lookback_days, db)["predictions"]
    dead = _dead_stock_items(db, inactive_days, warehouse_id)
    planning = purchase_planning(planning_days, lookback_days, warehouse_id, db)
    return {
        "assistant_type": "explainable_rules_and_statistical_forecasts",
        "warehouse_id": warehouse_id,
        "trends": trends,
        "stockout_predictions": stockout,
        "dead_stock": dead,
        "purchase_recommendations": planning["recommendations"],
        "overstock": planning["overstock"],
        "limitations": [
            "This endpoint does not use a language model; every statement is based on returned database values and documented planning rules.",
            "Demand estimates assume recent sales patterns continue and should be backtested.",
            "Open purchase-order quantities are treated as available without evaluating expected delivery dates.",
        ],
    }


@router.post("/assistant/query")
def assistant_query(payload: AssistantQuery, db: Session = Depends(get_db)):
    """Answer supported purchasing, demand-trend, stockout and dead-stock questions."""
    question = payload.question.casefold()
    common = {"warehouse_id": payload.warehouse_id}
    if any(word in question for word in ("dead stock", "clearance", "no sale", "not selling")):
        items = _dead_stock_items(db, payload.inactive_days, payload.warehouse_id)
        return {
            "intent": "dead_stock",
            "answer": f"Found {len(items)} products with stock and no sale within {payload.inactive_days} days.",
            "items": items,
            **common,
        }
    if any(word in question for word in ("trend", "increasing", "month-over-month", "demand")):
        items = _product_trends(db, payload.warehouse_id)
        return {
            "intent": "product_trends",
            "answer": f"Compared completed sales in the last two full months for {len(items)} products.",
            "items": items,
            **common,
        }
    if any(word in question for word in ("stockout", "run out", "stock out")):
        result = stockout_predictions(payload.warehouse_id, payload.lookback_days, db)
        return {
            "intent": "stockout_risk",
            "answer": f"Estimated stockout risk for {result['count']} inventory records.",
            **result,
            **common,
        }
    if any(word in question for word in ("purchase", "buy", "order", "procure")):
        result = purchase_planning(
            payload.planning_days,
            payload.lookback_days,
            payload.warehouse_id,
            db,
        )
        return {
            "intent": "purchase_planning",
            "answer": (
                f"{result['recommendation_count']} products are recommended for ordering "
                f"within the next {payload.planning_days} days; "
                f"{result['overstock_count']} products are over maximum stock."
            ),
            **result,
        }
    raise HTTPException(
        status_code=422,
        detail={
            "message": "This assistant supports purchasing, demand-trend, stockout-risk, and dead-stock questions.",
            "examples": [
                "Which products should we purchase this week?",
                "Which products have increasing demand?",
                "Which products are at stockout risk?",
                "Which products are dead stock?",
            ],
        },
    )


@router.get("/forecast-backtest/{product_id}")
def forecast_backtest(
    product_id: int,
    warehouse_id: int | None = Query(default=None, gt=0),
    lookback_days: int = Query(default=90, ge=7, le=365),
    test_days: int = Query(default=30, ge=1, le=90),
    method: str = Query(default="linear_regression"),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if method.lower() not in SUPPORTED_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported method. Choose one of: {', '.join(sorted(SUPPORTED_METHODS))}",
        )
    try:
        result = backtest_product_demand(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            lookback_days=lookback_days,
            test_days=test_days,
            method=method,
        )
        result["product_name"] = product.name
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/demand-forecast/{product_id}")
def demand_forecast(
    product_id: int,
    warehouse_id: int | None = Query(default=None, gt=0),
    lookback_days: int = Query(default=90, ge=7, le=365),
    forecast_days: int = Query(default=30, ge=1, le=180),
    method: str = Query(default="linear_regression", description="linear_regression, weighted_moving_average, or moving_average"),
    db: Session = Depends(get_db),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    if method.lower() not in SUPPORTED_METHODS:
        raise HTTPException(status_code=422, detail=f"Unsupported method. Choose one of: {', '.join(sorted(SUPPORTED_METHODS))}")
    try:
        result = forecast_product_demand(
            db=db,
            product_id=product_id,
            warehouse_id=warehouse_id,
            lookback_days=lookback_days,
            forecast_days=forecast_days,
            method=method,
        )
        row = DemandForecast(
            product_id=product_id,
            warehouse_id=warehouse_id,
            forecast_period=f"next_{forecast_days}_days",
            predicted_demand=result["predicted_demand"],
            forecast_method=method.lower(),
        )
        db.add(row)
        db.commit()
        result.update({"product_name": product.name, "forecast_record_id": row.id})
        return result
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
