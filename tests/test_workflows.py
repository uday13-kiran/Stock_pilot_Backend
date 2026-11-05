from datetime import date, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import main
from app.core.database import Base
from app.models.customer import Customer
from app.models.inventory import Inventory
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.products import Product
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_recommendation import PurchaseRecommendation
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.reorder_rule import ReorderRule
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.stock_alert import StockAlert
from app.models.supplier import Supplier
from app.models.supplier_products import SupplierProduct
from app.models.user import User
from app.models.warehouse import Warehouse
from app.routes import workflow_route
from app.routes.planning_route import (
    AssistantQuery,
    assistant_query,
    forecast_backtest,
    product_trends,
    purchase_planning,
    refresh_purchase_recommendations,
    stockout_predictions,
)
from app.routes.reports_route import inventory_summary
from app.routes.inventory_route import list_inventory
from app.routes.low_stock_notification_route import low_stock_notifications
from app.routes.purchase_order_item_route import create_purchase_order_item
from app.routes.purchase_order_route import (
    create_purchase_order_workflow,
    update_purchase_order,
)
from app.services.forecast_service import forecast_product_demand
from app.schemas.purchase_order_item import PurchaseOrderItemCreate
from app.schemas.purchase_order import PurchaseOrderUpdate, PurchaseOrderWorkflowCreate
from app.routes.workflow_route import (
    CheckoutLine,
    CheckoutRequest,
    ReceivePurchaseRequest,
    ReceiptLine,
    approve_purchase_order,
    checkout_sale,
    receive_purchase_order,
)
from app.services import assistant_service


@pytest.fixture
def workflow_db(monkeypatch) -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = session_factory()
    monkeypatch.setattr(workflow_route, "record_event", lambda *args, **kwargs: False)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_purchase_to_sale_to_replenishment_flow(workflow_db: Session) -> None:
    db = workflow_db
    supplier = Supplier(name="Flow supplier")
    warehouse = Warehouse(name="Flow warehouse", location="Test")
    user = User(name="Flow user", email="flow@example.test", password_hash="test-hash")
    customer = Customer(name="Flow customer")
    product = Product(
        sku="FLOW-001",
        name="Flow product",
        category_id=1,
        brand_id=1,
        unit_id=1,
        selling_price=10,
        purchase_price=5,
        tax_percent=0,
        reorder_level=40,
        safety_stock=10,
        maximum_stock=100,
        lead_time=7,
    )
    db.add_all([supplier, warehouse, user, customer, product])
    db.flush()
    db.add(SupplierProduct(supplier_id=supplier.id, product_id=product.id, supplier_price=5))
    db.flush()

    order = PurchaseOrder(
        supplier_id=supplier.id,
        warehouse_id=warehouse.id,
        user_id=user.id,
        order_date=datetime.utcnow(),
        status="DRAFT",
        total_amount=0,
    )
    db.add(order)
    db.commit()
    create_purchase_order_item(
        PurchaseOrderItemCreate(
            purchase_order_id=order.id,
            product_id=product.id,
            quantity=100,
        ),
        db,
    )
    assert order.total_amount == 500
    assert db.scalar(select(PurchaseOrderItem).where(
        PurchaseOrderItem.purchase_order_id == order.id,
        PurchaseOrderItem.product_id == product.id,
    )).unit_price == 5

    receive_request = ReceivePurchaseRequest(
        warehouse_id=warehouse.id,
        items=[ReceiptLine(product_id=product.id, quantity=100)],
    )
    with pytest.raises(HTTPException) as draft_receive:
        receive_purchase_order(order.id, receive_request, db)
    assert draft_receive.value.status_code == 409

    assert approve_purchase_order(order.id, db)["status"] == "APPROVED"
    with pytest.raises(HTTPException) as approved_edit:
        update_purchase_order(order.id, PurchaseOrderUpdate(notes="should not change"), db)
    assert approved_edit.value.status_code == 409
    with pytest.raises(HTTPException) as late_item:
        create_purchase_order_item(
            PurchaseOrderItemCreate(
                purchase_order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price=5,
                total_price=5,
            ),
            db,
        )
    assert late_item.value.status_code == 409

    receive_purchase_order(order.id, receive_request, db)
    inventory = db.scalar(select(Inventory).where(
        Inventory.product_id == product.id,
        Inventory.warehouse_id == warehouse.id,
    ))
    assert inventory is not None and inventory.available_quantity == 100

    checkout = checkout_sale(
        CheckoutRequest(
            customer_id=customer.id,
            warehouse_id=warehouse.id,
            items=[CheckoutLine(product_id=product.id, quantity=70)],
            payment_method="CASH",
        ),
        db,
        user,
    )
    invoice = db.get(Invoice, checkout["invoice_id"])
    assert invoice is not None and invoice.status == "PAID"
    assert db.scalar(select(Payment).where(Payment.invoice_id == invoice.id)).status == "PAID"
    assert checkout["warehouse_id"] == warehouse.id
    assert checkout["inventory_updates"] == [{
        "product_id": product.id,
        "quantity": 30,
        "reserved_quantity": 0,
        "available_quantity": 30,
    }]
    assert inventory.quantity == 30
    assert inventory.available_quantity == 30
    refreshed_inventory = list_inventory(warehouse.id, 0, 500, db)
    assert len(refreshed_inventory) == 1
    assert refreshed_inventory[0].quantity == 30
    assert refreshed_inventory[0].available_quantity == 30

    alert = db.scalar(select(StockAlert).where(
        StockAlert.product_id == product.id,
        StockAlert.warehouse_id == warehouse.id,
        StockAlert.is_resolved.is_(False),
    ))
    assert alert is not None and alert.current_stock == 30

    refresh_purchase_recommendations(planning_days=30, lookback_days=90, warehouse_id=None, db=db)
    recommendation = db.scalar(select(PurchaseRecommendation).where(
        PurchaseRecommendation.product_id == product.id,
        PurchaseRecommendation.warehouse_id == warehouse.id,
    ))
    assert recommendation is not None and recommendation.suggested_quantity >= 10
    prediction = stockout_predictions(warehouse_id=warehouse.id, lookback_days=30, db=db)
    assert prediction["count"] == 1
    assert prediction["predictions"][0]["available_stock"] == 30

    replenishment = PurchaseOrder(
        supplier_id=supplier.id,
        warehouse_id=warehouse.id,
        user_id=user.id,
        order_date=datetime.utcnow(),
        status="DRAFT",
        total_amount=0,
    )
    db.add(replenishment)
    db.commit()
    create_purchase_order_item(
        PurchaseOrderItemCreate(
            purchase_order_id=replenishment.id,
            product_id=product.id,
            quantity=70,
        ),
        db,
    )
    assert replenishment.total_amount == 350
    approve_purchase_order(replenishment.id, db)
    receive_purchase_order(
        replenishment.id,
        ReceivePurchaseRequest(
            warehouse_id=warehouse.id,
            items=[ReceiptLine(product_id=product.id, quantity=70)],
        ),
        db,
    )

    assert inventory.available_quantity == 100
    assert alert.is_resolved is True
    refresh_purchase_recommendations(planning_days=30, lookback_days=90, warehouse_id=None, db=db)
    assert recommendation.suggested_quantity == 0


def test_planning_assistant_reports_trends_stockout_orders_and_overstock(
    workflow_db: Session,
) -> None:
    db = workflow_db
    today = date.today()
    current_month_start = today.replace(day=1)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    month_before_start = (last_month_start - timedelta(days=1)).replace(day=1)
    warehouse = Warehouse(name="Planning warehouse", location="Test")
    customer = Customer(name="Planning customer")
    user = User(name="Planning user", email="planning@example.test", password_hash="test-hash")
    trend_product = Product(
        sku="TREND-001", name="Trend product", category_id=1, brand_id=1, unit_id=1,
        selling_price=10, purchase_price=5, tax_percent=0, reorder_level=10,
        safety_stock=3, maximum_stock=200, lead_time=7,
    )
    fast_product = Product(
        sku="FAST-001", name="Fast product", category_id=1, brand_id=1, unit_id=1,
        selling_price=10, purchase_price=5, tax_percent=0, reorder_level=10,
        safety_stock=3, maximum_stock=200, lead_time=7,
    )
    overstock_product = Product(
        sku="OVER-001", name="Overstock product", category_id=1, brand_id=1, unit_id=1,
        selling_price=10, purchase_price=5, tax_percent=0, reorder_level=10,
        safety_stock=3, maximum_stock=100, lead_time=7,
    )
    db.add_all([warehouse, customer, user, trend_product, fast_product, overstock_product])
    db.flush()
    db.add_all([
        Inventory(
            product_id=fast_product.id, warehouse_id=warehouse.id, quantity=18,
            reserved_quantity=0, available_quantity=18,
        ),
        Inventory(
            product_id=overstock_product.id, warehouse_id=warehouse.id, quantity=500,
            reserved_quantity=0, available_quantity=500,
        ),
    ])

    def add_sale(product: Product, sold_at: datetime, quantity: int, status: str = "COMPLETED"):
        sale = Sale(
            customer_id=customer.id, user_id=user.id, warehouse_id=warehouse.id,
            sale_date=sold_at, subtotal=quantity * 10, discount_amount=0,
            tax_amount=0, total_amount=quantity * 10, status=status,
        )
        db.add(sale)
        db.flush()
        db.add(
            SaleItem(
                sale_id=sale.id, product_id=product.id, quantity=quantity,
                unit_price=10, discount_amount=0, tax_amount=0,
                total_price=quantity * 10,
            )
        )

    add_sale(
        trend_product,
        datetime.combine(month_before_start + timedelta(days=5), datetime.min.time()),
        20,
    )
    add_sale(
        trend_product,
        datetime.combine(last_month_start + timedelta(days=5), datetime.min.time()),
        23,
    )
    for days_ago in range(1, 29):
        sold_at = datetime.combine(today - timedelta(days=days_ago), datetime.min.time())
        add_sale(fast_product, sold_at, 3)
    add_sale(
        fast_product,
        datetime.combine(today - timedelta(days=1), datetime.min.time()),
        500,
        "CANCELLED",
    )
    db.commit()

    trends = product_trends(warehouse_id=None, db=db)
    trend = next(item for item in trends["items"] if item["product_id"] == trend_product.id)
    assert trend["month_over_month_percent"] == 15.0
    assert trend["trend"] == "INCREASING"

    forecast = forecast_product_demand(
        db, fast_product.id, warehouse.id, lookback_days=90, forecast_days=7,
        method="moving_average",
    )
    assert forecast["historical_units"] == 84
    backtest = forecast_backtest(
        fast_product.id,
        warehouse.id,
        lookback_days=30,
        test_days=14,
        method="moving_average",
        db=db,
    )
    assert backtest["actual_units"] == 42
    assert backtest["mean_absolute_error_units_per_day"] >= 0
    assert backtest["weighted_absolute_percentage_error"] is not None

    planning = purchase_planning(
        planning_days=7, lookback_days=90, warehouse_id=warehouse.id, db=db,
    )
    fast_recommendation = next(
        item for item in planning["recommendations"] if item["product_id"] == fast_product.id
    )
    assert fast_recommendation["estimated_stockout_days"] <= fast_product.lead_time
    assert fast_recommendation["priority"] == "HIGH"
    assert fast_recommendation["suggested_quantity"] > 0
    assert planning["overstock"][0]["product_id"] == overstock_product.id

    answer = assistant_query(
        AssistantQuery(
            question="Which products should we purchase this week?",
            warehouse_id=warehouse.id,
        ),
        db,
    )
    assert answer["intent"] == "purchase_planning"
    assert answer["recommendations"][0]["product_id"] == fast_product.id


def test_llm_assistant_calls_only_read_only_analytics_tools(
    workflow_db: Session,
    monkeypatch,
) -> None:
    class FakeResponse:
        def __init__(self, data):
            self.data = data

        def raise_for_status(self):
            return None

        def json(self):
            return self.data

    class FakeClient:
        calls = []

        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            self.calls.append({"url": url, "headers": headers, "payload": json})
            if len(self.calls) == 1:
                return FakeResponse(
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "call-sales",
                                            "type": "function",
                                            "function": {
                                                "name": "get_sales_summary",
                                                "arguments": '{"days":30}',
                                            },
                                        }
                                    ],
                                }
                            }
                        ]
                    }
                )
            return FakeResponse(
                {"choices": [{"message": {"role": "assistant", "content": "Sales data shows no completed sales in this period."}}]}
            )

    FakeClient.calls = []
    monkeypatch.setattr(assistant_service.settings, "llm_api_key", "test-key-not-real")
    monkeypatch.setattr(assistant_service.settings, "llm_model", "test-tool-model")
    monkeypatch.setattr(
        assistant_service.settings,
        "llm_base_url",
        "https://api.groq.com/openai/v1",
    )
    monkeypatch.setattr(assistant_service.httpx, "Client", FakeClient)
    result = assistant_service.ask_llm(
        "How were sales this month?",
        None,
        workflow_db,
    )

    assert result["answer"] == "Sales data shows no completed sales in this period."
    assert result["evidence"][0]["tool"] == "get_sales_summary"
    assert result["evidence"][0]["data"]["completed_sale_count"] == 0
    assert len(FakeClient.calls) == 2
    assert FakeClient.calls[0]["url"] == (
        "https://api.groq.com/openai/v1/chat/completions"
    )
    assert FakeClient.calls[0]["headers"]["Authorization"] == "Bearer test-key-not-real"
    system_prompt = FakeClient.calls[0]["payload"]["messages"][0]["content"]
    assert "simple, clear, and concise" in system_prompt
    assert "do not use tables" in system_prompt
    assert FakeClient.calls[1]["payload"]["tool_choice"] == "none"


def test_create_purchase_order_workflow_creates_lines_and_supplier_links(
    workflow_db: Session,
) -> None:
    db = workflow_db
    supplier = Supplier(name="Workflow supplier")
    warehouse = Warehouse(name="Workflow warehouse", location="Test")
    other_warehouse = Warehouse(name="Other workflow warehouse", location="Other test")
    user = User(name="Workflow user", email="workflow@example.test", password_hash="test-hash")
    products = [
        Product(
            sku=f"WORKFLOW-{index}",
            name=f"Workflow product {index}",
            category_id=1,
            brand_id=1,
            unit_id=1,
            selling_price=10,
            purchase_price=3,
            tax_percent=0,
            reorder_level=0,
            safety_stock=0,
            maximum_stock=100,
            lead_time=7,
        )
        for index in (1, 2)
    ]
    db.add_all([supplier, warehouse, other_warehouse, user, *products])
    db.flush()
    db.add(
        SupplierProduct(
            supplier_id=supplier.id,
            product_id=products[0].id,
            supplier_price=5,
        )
    )
    db.commit()

    result = create_purchase_order_workflow(
        PurchaseOrderWorkflowCreate(
            supplier_id=supplier.id,
            warehouse_id=warehouse.id,
            items=[
                {"product_id": products[0].id, "quantity": 2},
                {"product_id": products[1].id, "quantity": 4},
            ],
        ),
        db,
        user,
    )

    order = db.get(PurchaseOrder, result["id"])
    assert order is not None
    assert order.user_id == user.id
    assert order.warehouse_id == warehouse.id
    assert order.status == "DRAFT"
    assert order.total_amount == 22
    assert len(result["items"]) == 2
    assert {item["product_id"]: item["unit_price"] for item in result["items"]} == {
        products[0].id: 5,
        products[1].id: 3,
    }
    new_supplier_link = db.scalar(
        select(SupplierProduct).where(
            SupplierProduct.supplier_id == supplier.id,
            SupplierProduct.product_id == products[1].id,
        )
    )
    assert new_supplier_link is not None
    assert new_supplier_link.supplier_price == 3

    assert approve_purchase_order(order.id, db)["status"] == "APPROVED"
    with pytest.raises(HTTPException) as wrong_destination:
        receive_purchase_order(
            order.id,
            ReceivePurchaseRequest(
                warehouse_id=other_warehouse.id,
                items=[
                    ReceiptLine(product_id=products[0].id, quantity=2),
                ],
            ),
            db,
        )
    assert wrong_destination.value.status_code == 409

    receive_purchase_order(
        order.id,
        ReceivePurchaseRequest(
            warehouse_id=warehouse.id,
            items=[
                ReceiptLine(product_id=products[0].id, quantity=2),
                ReceiptLine(product_id=products[1].id, quantity=4),
            ],
        ),
        db,
    )
    assert db.scalar(
        select(Inventory).where(
            Inventory.product_id == products[0].id,
            Inventory.warehouse_id == warehouse.id,
        )
    ).available_quantity == 2
    assert db.scalar(
        select(Inventory).where(
            Inventory.product_id == products[0].id,
            Inventory.warehouse_id == other_warehouse.id,
        )
    ) is None
    summary = inventory_summary(db)
    assert summary["product_count"] == 2
    assert summary["stocked_product_count"] == 2
    assert summary["total_units"] == 6
    assert summary["total_available_units"] == 6


def test_create_purchase_order_workflow_does_not_create_partial_order(
    workflow_db: Session,
) -> None:
    db = workflow_db
    supplier = Supplier(name="Atomic supplier")
    warehouse = Warehouse(name="Atomic warehouse", location="Test")
    user = User(name="Atomic user", email="atomic@example.test", password_hash="test-hash")
    product = Product(
        sku="ATOMIC-001",
        name="Atomic product",
        category_id=1,
        brand_id=1,
        unit_id=1,
        selling_price=10,
        purchase_price=3,
        tax_percent=0,
        reorder_level=0,
        safety_stock=0,
        maximum_stock=100,
        lead_time=7,
    )
    db.add_all([supplier, warehouse, user, product])
    db.commit()

    with pytest.raises(HTTPException) as missing_product:
        create_purchase_order_workflow(
            PurchaseOrderWorkflowCreate(
                supplier_id=supplier.id,
                warehouse_id=warehouse.id,
                items=[
                    {"product_id": product.id, "quantity": 1},
                    {"product_id": 99999, "quantity": 1},
                ],
            ),
            db,
            user,
        )

    assert missing_product.value.status_code == 404
    assert db.scalar(select(PurchaseOrder.id)) is None
    assert db.scalar(select(SupplierProduct.id)) is None


def test_inventory_listing_filters_to_selected_warehouse(workflow_db: Session) -> None:
    db = workflow_db
    warehouse, other_warehouse = (
        Warehouse(name="Inventory A", location="A"),
        Warehouse(name="Inventory B", location="B"),
    )
    product = Product(
        sku="INVENTORY-FILTER-1",
        name="Warehouse-specific product",
        category_id=1,
        brand_id=1,
        unit_id=1,
        selling_price=10,
        purchase_price=5,
        tax_percent=0,
        reorder_level=0,
        safety_stock=0,
        maximum_stock=100,
        lead_time=7,
    )
    db.add_all([warehouse, other_warehouse, product])
    db.flush()
    db.add_all([
        Inventory(
            product_id=product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reserved_quantity=1,
            available_quantity=4,
        ),
        Inventory(
            product_id=product.id,
            warehouse_id=other_warehouse.id,
            quantity=8,
            reserved_quantity=0,
            available_quantity=8,
        ),
    ])
    db.flush()

    rows = list_inventory(warehouse.id, 0, 500, db)

    assert len(rows) == 1
    assert rows[0].warehouse_id == warehouse.id
    assert rows[0].quantity == 5
    assert rows[0].available_quantity == 4


def test_low_stock_notifications_include_product_warehouse_and_live_levels(
    workflow_db: Session,
) -> None:
    db = workflow_db
    warehouse = Warehouse(name="Low stock warehouse", location="East")
    critical_product = Product(
        sku="LOW-CRITICAL",
        name="Critical product",
        category_id=1,
        brand_id=1,
        unit_id=1,
        selling_price=10,
        purchase_price=5,
        tax_percent=0,
        reorder_level=10,
        safety_stock=4,
        maximum_stock=100,
        lead_time=7,
    )
    warning_product = Product(
        sku="LOW-WARNING",
        name="Warning product",
        category_id=1,
        brand_id=1,
        unit_id=1,
        selling_price=10,
        purchase_price=5,
        tax_percent=0,
        reorder_level=10,
        safety_stock=4,
        maximum_stock=100,
        lead_time=7,
    )
    normal_product = Product(
        sku="LOW-NORMAL",
        name="Normal product",
        category_id=1,
        brand_id=1,
        unit_id=1,
        selling_price=10,
        purchase_price=5,
        tax_percent=0,
        reorder_level=10,
        safety_stock=4,
        maximum_stock=100,
        lead_time=7,
    )
    db.add_all([warehouse, critical_product, warning_product, normal_product])
    db.flush()
    db.add_all([
        Inventory(
            product_id=critical_product.id,
            warehouse_id=warehouse.id,
            quantity=5,
            reserved_quantity=1,
            available_quantity=4,
        ),
        Inventory(
            product_id=warning_product.id,
            warehouse_id=warehouse.id,
            quantity=8,
            reserved_quantity=0,
            available_quantity=8,
        ),
        Inventory(
            product_id=normal_product.id,
            warehouse_id=warehouse.id,
            quantity=11,
            reserved_quantity=0,
            available_quantity=11,
        ),
    ])
    db.add(
        ReorderRule(
            product_id=warning_product.id,
            warehouse_id=warehouse.id,
            reorder_level=12,
            safety_stock=6,
            maximum_stock=100,
        )
    )
    db.flush()

    result = low_stock_notifications(db)

    assert result["count"] == 2
    alerts = {item["product_id"]: item for item in result["items"]}
    assert alerts[critical_product.id]["severity"] == "CRITICAL"
    assert alerts[critical_product.id]["available_quantity"] == 4
    assert alerts[critical_product.id]["warehouse_name"] == warehouse.name
    assert alerts[critical_product.id]["product_name"] == critical_product.name
    assert alerts[warning_product.id]["severity"] == "LOW"
    assert alerts[warning_product.id]["reorder_level"] == 12
    assert alerts[warning_product.id]["message"] == (
        "Low stock warehouse has 8 units available; the reorder level is 12."
    )