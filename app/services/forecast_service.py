"""Demand forecasting using transparent time-series baselines and linear regression.

This is a lightweight, explainable ML-style regression approach. It deliberately avoids
requiring a large ML runtime. Forecast quality must be backtested on the business's data.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from math import isfinite

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.sales_return import SalesReturn
from app.models.sales_return_item import SalesReturnItem


SUPPORTED_METHODS = {"linear_regression", "weighted_moving_average", "moving_average"}


def build_daily_series(sales: list[tuple[datetime, int]], lookback_days: int, today: date | None = None) -> list[float]:
    """Return one value per calendar day, filling days without sales with zero."""
    today = today or date.today()
    start = today - timedelta(days=lookback_days)
    totals: dict[date, int] = defaultdict(int)
    for sold_at, quantity in sales:
        sold_date = sold_at.date()
        if start <= sold_date < today:
            totals[sold_date] += int(quantity)
    return [float(max(totals[start + timedelta(days=i)], 0)) for i in range(lookback_days)]


def _linear_regression_forecast(history: list[float], forecast_days: int) -> list[float]:
    """Ordinary least-squares line over daily demand; forecasts are clipped at zero."""
    n = len(history)
    if n == 0:
        return [0.0] * forecast_days
    x_mean = (n - 1) / 2
    y_mean = sum(history) / n
    denominator = sum((x - x_mean) ** 2 for x in range(n))
    slope = (sum((x - x_mean) * (y - y_mean) for x, y in enumerate(history)) / denominator) if denominator else 0.0
    intercept = y_mean - slope * x_mean
    return [max(0.0, intercept + slope * (n + step)) for step in range(forecast_days)]


def _weighted_moving_average_forecast(history: list[float], forecast_days: int) -> list[float]:
    if not history:
        daily = 0.0
    else:
        window = history[-min(14, len(history)):]
        weights = list(range(1, len(window) + 1))
        daily = sum(value * weight for value, weight in zip(window, weights)) / sum(weights)
    return [max(0.0, daily)] * forecast_days


def forecast_from_history(history: list[float], forecast_days: int, method: str = "linear_regression") -> dict:
    """Pure forecasting function so it can be tested without a database."""
    method = method.strip().lower()
    if method not in SUPPORTED_METHODS:
        raise ValueError(f"Unsupported method. Choose one of: {', '.join(sorted(SUPPORTED_METHODS))}")
    if forecast_days < 1 or forecast_days > 180:
        raise ValueError("forecast_days must be between 1 and 180")
    clean = [max(0.0, float(value)) if isfinite(float(value)) else 0.0 for value in history]
    if method == "linear_regression":
        predicted_daily = _linear_regression_forecast(clean, forecast_days)
    elif method == "weighted_moving_average":
        predicted_daily = _weighted_moving_average_forecast(clean, forecast_days)
    else:
        average = sum(clean) / len(clean) if clean else 0.0
        predicted_daily = [average] * forecast_days

    return {
        "method": method,
        "history_days": len(clean),
        "historical_units": round(sum(clean), 2),
        "historical_daily_average": round(sum(clean) / len(clean), 4) if clean else 0.0,
        "predicted_daily_demand": [round(value, 2) for value in predicted_daily],
        "predicted_demand": round(sum(predicted_daily), 2),
    }


def forecast_product_demand(
    db: Session,
    product_id: int,
    warehouse_id: int | None,
    lookback_days: int,
    forecast_days: int,
    method: str,
) -> dict:
    if not 7 <= lookback_days <= 365:
        raise ValueError("lookback_days must be between 7 and 365")
    window_start = date.today() - timedelta(days=lookback_days)
    start = datetime.combine(window_start, datetime.min.time())
    end = datetime.combine(date.today(), datetime.min.time())
    sales = _net_sales_rows(db, product_id, warehouse_id, start, end)
    history = build_daily_series(sales, lookback_days, today=date.today())
    result = forecast_from_history(history, forecast_days, method)
    result.update({
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "lookback_days": lookback_days,
        "forecast_days": forecast_days,
        "zero_sale_days_included": True,
        "warning": "Forecast is an estimate. Backtest against actual sales before using for purchasing.",
    })
    return result


def _net_sales_rows(
    db: Session,
    product_id: int,
    warehouse_id: int | None,
    start: datetime,
    end: datetime,
) -> list[tuple[datetime, int]]:
    sales_stmt = (
        select(Sale.sale_date, SaleItem.quantity)
        .join(SaleItem, SaleItem.sale_id == Sale.id)
        .where(
            SaleItem.product_id == product_id,
            Sale.sale_date >= start,
            Sale.sale_date < end,
            Sale.status.in_(("COMPLETED", "COMPLETE", "PAID")),
        )
    )
    if warehouse_id is not None:
        sales_stmt = sales_stmt.where(Sale.warehouse_id == warehouse_id)
    sales = [(row[0], row[1]) for row in db.execute(sales_stmt).all()]
    returns_stmt = (
        select(SalesReturn.return_date, SalesReturnItem.quantity)
        .join(SalesReturnItem, SalesReturnItem.return_id == SalesReturn.id)
        .join(Sale, Sale.id == SalesReturn.sale_id)
        .where(
            SalesReturnItem.product_id == product_id,
            SalesReturn.return_date >= start,
            SalesReturn.return_date < end,
            SalesReturn.status == "APPROVED",
            Sale.status.in_(("COMPLETED", "COMPLETE", "PAID")),
        )
    )
    if warehouse_id is not None:
        returns_stmt = returns_stmt.where(Sale.warehouse_id == warehouse_id)
    sales.extend(
        (row[0], -row[1]) for row in db.execute(returns_stmt).all()
    )
    return sales


def backtest_product_demand(
    db: Session,
    product_id: int,
    warehouse_id: int | None,
    lookback_days: int,
    test_days: int,
    method: str,
) -> dict:
    if not 7 <= lookback_days <= 365:
        raise ValueError("lookback_days must be between 7 and 365")
    if not 1 <= test_days <= 90:
        raise ValueError("test_days must be between 1 and 90")
    today = date.today()
    test_start = today - timedelta(days=test_days)
    training_start = test_start - timedelta(days=lookback_days)
    training_rows = _net_sales_rows(
        db,
        product_id,
        warehouse_id,
        datetime.combine(training_start, datetime.min.time()),
        datetime.combine(test_start, datetime.min.time()),
    )
    actual_rows = _net_sales_rows(
        db,
        product_id,
        warehouse_id,
        datetime.combine(test_start, datetime.min.time()),
        datetime.combine(today, datetime.min.time()),
    )
    training = build_daily_series(training_rows, lookback_days, today=test_start)
    actual = build_daily_series(actual_rows, test_days, today=today)
    forecast = forecast_from_history(training, test_days, method)
    predicted = forecast["predicted_daily_demand"]
    errors = [abs(actual_value - predicted_value) for actual_value, predicted_value in zip(actual, predicted)]
    actual_units = sum(actual)
    return {
        "product_id": product_id,
        "warehouse_id": warehouse_id,
        "method": forecast["method"],
        "training_days": lookback_days,
        "test_days": test_days,
        "actual_units": round(actual_units, 2),
        "predicted_units": forecast["predicted_demand"],
        "mean_absolute_error_units_per_day": round(sum(errors) / test_days, 3),
        "weighted_absolute_percentage_error": round(sum(errors) / actual_units, 4) if actual_units > 0 else None,
        "actual_daily_demand": actual,
        "predicted_daily_demand": predicted,
        "warning": "Backtest metrics describe this historical test window; they do not guarantee future accuracy.",
    }
