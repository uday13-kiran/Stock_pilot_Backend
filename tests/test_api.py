import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from app.core.database import Base, SessionLocal, engine
from app.core.security import create_access_token
from app.models.user import User
from app.models.roles import Role


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    email = f"test-{uuid.uuid4().hex}@example.com"
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role is None:
        admin_role = Role(name="admin", description="Full access")
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
    user = User(name="Test Admin", email=email, password_hash="test-only-hash", role_id=admin_role.id, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, "admin")
    db.close()
    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client
    cleanup = SessionLocal()
    stale = cleanup.query(User).filter(User.email == email).first()
    if stale is not None:
        cleanup.delete(stale)
        cleanup.commit()
    cleanup.close()


def test_health():
    with TestClient(app) as test_client:
        response = test_client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_business_routes_require_authentication():
    with TestClient(app) as test_client:
        response = test_client.get('/api/v1/categories/')
    assert response.status_code == 401


def test_category_crud(client):
    created = client.post('/api/v1/categories/', json={'name': 'Test category', 'description': 'for tests'})
    assert created.status_code == 201, created.text
    category_id = created.json()['id']
    fetched = client.get(f'/api/v1/categories/{category_id}')
    assert fetched.status_code == 200
    assert fetched.json()['name'] == 'Test category'
    updated = client.put(f'/api/v1/categories/{category_id}', json={'name': 'Updated category'})
    assert updated.status_code == 200
    assert updated.json()['name'] == 'Updated category'
    deleted = client.delete(f'/api/v1/categories/{category_id}')
    assert deleted.status_code == 204


def test_product_listing_accepts_receiving_page_limit(client):
    response = client.get("/api/v1/products/?skip=0&limit=200")
    assert response.status_code == 200, response.text

    over_limit = client.get("/api/v1/products/?skip=0&limit=500")
    assert over_limit.status_code == 422


def test_inventory_listing_supports_warehouse_filter(client):
    all_inventory = client.get("/api/v1/inventory/?skip=0&limit=500")
    assert all_inventory.status_code == 200, all_inventory.text
    assert isinstance(all_inventory.json(), list)

    warehouse_inventory = client.get("/api/v1/inventory/?warehouse_id=1&skip=0&limit=500")
    assert warehouse_inventory.status_code == 200, warehouse_inventory.text
    assert all(
        row["warehouse_id"] == 1 for row in warehouse_inventory.json()
    )


def test_required_project_routes_are_registered():
    paths = set(app.openapi()["paths"])
    required = {
        "/api/v1/auth/login",
        "/api/v1/auth/me",
        "/api/v1/suppliers/",
        "/api/v1/customers/",
        "/api/v1/warehouses/",
        "/api/v1/purchase-orders/",
        "/api/v1/purchase-orders/{purchase_order_id}/approve",
        "/api/v1/purchase-orders/{purchase_order_id}/receive",
        "/api/v1/sales/checkout",
        "/api/v1/invoices/",
        "/api/v1/payments/",
        "/api/v1/stock-transfers/{transfer_id}/dispatch",
        "/api/v1/stock-transfers/{transfer_id}/receive",
        "/api/v1/sales-returns/{return_id}/approve",
        "/api/v1/inventory/stock-in",
        "/api/v1/inventory/stock-out",
        "/api/v1/reports/inventory-summary",
        "/api/v1/notifications/low-stock",
        "/api/v1/reports/forecast/{product_id}",
        "/api/v1/planning/stockout-predictions",
        "/api/v1/planning/dead-stock",
        "/api/v1/planning/purchase-recommendations/refresh",
        "/api/v1/planning/demand-forecast/{product_id}",
        "/api/v1/planning/product-trends",
        "/api/v1/planning/purchase-planning",
        "/api/v1/planning/assistant/insights",
        "/api/v1/planning/assistant/query",
        "/api/v1/planning/forecast-backtest/{product_id}",
        "/api/v1/assistant/ask",
    }
    assert required.issubset(paths), f"Missing routes: {sorted(required - paths)}"


def test_authenticated_planning_endpoints_return_consistent_results(client):
    stockout = client.get("/api/v1/planning/stockout-predictions")
    assert stockout.status_code == 200, stockout.text
    assert stockout.json()["count"] == len(stockout.json()["predictions"])

    dead_stock_response = client.get("/api/v1/planning/dead-stock")
    assert dead_stock_response.status_code == 200, dead_stock_response.text
    assert dead_stock_response.json()["count"] == len(dead_stock_response.json()["items"])

    refresh = client.post("/api/v1/planning/purchase-recommendations/refresh")
    assert refresh.status_code == 200, refresh.text
    assert isinstance(refresh.json()["created_or_updated"], int)

    trends = client.get("/api/v1/planning/product-trends")
    assert trends.status_code == 200, trends.text
    assert isinstance(trends.json()["items"], list)

    purchasing = client.get("/api/v1/planning/purchase-planning")
    assert purchasing.status_code == 200, purchasing.text
    assert isinstance(purchasing.json()["recommendations"], list)

    answer = client.post(
        "/api/v1/planning/assistant/query",
        json={"question": "Which products should we purchase this week?"},
    )
    assert answer.status_code == 200, answer.text
    assert answer.json()["intent"] == "purchase_planning"
    assert "recommendations" in answer.json()

    insights = client.get("/api/v1/planning/assistant/insights")
    assert insights.status_code == 200, insights.text
    assert "stockout_predictions" in insights.json()


def test_ai_assistant_requires_provider_configuration(client, monkeypatch):
    from app.services import assistant_service

    monkeypatch.setattr(assistant_service.settings, "llm_api_key", None)
    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Which products should we order?"},
    )
    assert response.status_code == 503
    assert "LLM_API_KEY" in response.json()["detail"]


def test_ai_assistant_rejects_placeholder_model_before_provider_call(client, monkeypatch):
    from app.services import assistant_service

    monkeypatch.setattr(assistant_service.settings, "llm_api_key", "test-key-not-real")
    monkeypatch.setattr(assistant_service.settings, "llm_model", "your-groq-tool-capable-model-id")

    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Which products should we order?"},
    )
    assert response.status_code == 503
    assert "LLM_MODEL is still a placeholder" in response.json()["detail"]


def test_current_user_endpoint(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200, response.text
    assert response.json()["email"].endswith("@example.com")


def test_low_stock_notification_endpoint_returns_live_alerts(client):
    response = client.get("/api/v1/notifications/low-stock")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload["count"], int)
    assert isinstance(payload["items"], list)


def test_admin_can_access_identity_administration(client):
    response = client.get("/api/v1/users/")
    assert response.status_code == 200


def test_staff_cannot_access_identity_administration():
    from app.core.security import hash_password

    db = SessionLocal()
    role = db.query(Role).filter(Role.name == "sales_staff").first()
    if role is None:
        role = Role(name="sales_staff", description="Sales staff")
        db.add(role)
        db.commit()
        db.refresh(role)
    email = f"staff-{uuid.uuid4().hex}@example.com"
    user = User(name="Test Staff", email=email, password_hash=hash_password("Strong-Test-Password-123"), role_id=role.id, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.id, "sales_staff")
    db.close()

    with TestClient(app) as test_client:
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        response = test_client.get("/api/v1/users/")
    assert response.status_code == 403
    # Sales staff may view the catalog but cannot create master data.
    with TestClient(app) as read_client:
        read_client.headers.update({"Authorization": f"Bearer {token}"})
        assert read_client.get("/api/v1/products/").status_code == 200
        assert read_client.get("/api/v1/inventory/").status_code == 200
        forbidden_write = read_client.post("/api/v1/categories/", json={"name": "Staff must not create", "description": "RBAC test"})
        assert forbidden_write.status_code == 403
        assert read_client.get("/api/v1/payments/").status_code == 403

    cleanup = SessionLocal()
    stale = cleanup.query(User).filter(User.email == email).first()
    if stale:
        cleanup.delete(stale)
        cleanup.commit()
    cleanup.close()


def test_admin_can_create_staff_with_role(client):
    response = client.post(
        "/api/v1/users/",
        json={
            "name": "Sales Tester",
            "email": f"sales-{uuid.uuid4().hex}@example.com",
            "password": "Strong-Test-Password-123",
            "role_name": "sales_staff",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["role_name"] == "sales_staff"
    cleanup = SessionLocal()
    created = cleanup.query(User).filter(User.email == response.json()["email"]).first()
    if created:
        cleanup.delete(created)
        cleanup.commit()
    cleanup.close()


def test_public_registration_is_disabled():
    with TestClient(app) as test_client:
        response = test_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Self Registered",
                "email": f"public-{uuid.uuid4().hex}@example.com",
                "password": "Strong-Test-Password-123",
                "role_name": "admin",
            },
        )
    assert response.status_code == 403


def test_linear_regression_forecast_detects_increasing_demand():
    from app.services.forecast_service import forecast_from_history

    result = forecast_from_history([1, 2, 3, 4, 5, 6, 7], 3, "linear_regression")
    assert result["method"] == "linear_regression"
    assert result["predicted_demand"] > 0
    assert result["predicted_daily_demand"] == sorted(result["predicted_daily_demand"])


def test_forecast_methods_are_available():
    from app.services.forecast_service import forecast_from_history

    moving = forecast_from_history([2, 4, 6, 8], 5, "moving_average")
    weighted = forecast_from_history([2, 4, 6, 8], 5, "weighted_moving_average")
    assert moving["predicted_demand"] == 25
    assert weighted["predicted_demand"] > moving["predicted_demand"]


def test_payment_workflow_routes_are_registered():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/invoices/{invoice_id}/payments" in paths
    assert "/api/v1/payments/" in paths


def test_purchase_order_schema_accepts_destination_warehouse():
    from app.schemas.purchase_order import PurchaseOrderCreate
    payload = PurchaseOrderCreate(
        supplier_id=1,
        warehouse_id=3,
        user_id=1,
        order_date="2026-10-26T00:00:00",
        status="DRAFT",
        total_amount=100,
    )
    assert payload.warehouse_id == 3


def test_mongo_event_logger_is_optional_when_unconfigured(monkeypatch):
    from app.core import operational_events
    operational_events._collection.cache_clear()
    monkeypatch.setattr(operational_events.settings, "mongodb_url", None)
    assert operational_events.record_event("test.event", "test", 1) is False
    operational_events._collection.cache_clear()
