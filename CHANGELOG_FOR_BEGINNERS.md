# Change log — plain English

This file compares this revision with the **uploaded `stockpiolet_backend.zip` snapshot**. Your newest local files may differ from that snapshot.

## Existing structure preserved

Kept the project split into `app/models`, `app/schemas`, `app/routes`, `app/services`, `app/repositories`, `app/rules`, and `app/core`. I did not replace the whole architecture with a single `models.py`/`schemas.py` file.

## Fixed or improved

1. **Configuration:** removed hardcoded database credentials and the hardcoded JWT secret from settings. Settings now come from environment variables / `.env`; added `.env.example`.
2. **Database sessions:** introduced conventional `SessionLocal` while keeping `sessionlocal` as an alias for compatibility; added SQLite connection options for local development.
3. **User model:** fixed `app/models/user.py`, which incorrectly declared a second `Category` class while referencing `users.id` elsewhere.
4. **Model registration:** `app/models/__init__.py` now imports the model classes so SQLAlchemy can discover all model tables.
5. **Missing model:** implemented `UserRole` and `PurchaseOrderItem`, which had schema/model references but no complete model.
6. **Relationships and table names:** repaired several mismatched relationship definitions and supplier/purchase-order foreign-key targets discovered while configuring SQLAlchemy mappers.
7. **Product data types:** barcode is now optional text (matching the API schema), description can be optional, product names allow more than 25 characters, and SKU uniqueness is enforced at the database layer.
8. **Inventory constraints:** added a unique product+warehouse constraint and a non-negative quantity check.
9. **Product service:** added get/list/update/deactivate operations and duplicate-SKU checks.
10. **Product routes:** corrected the broken `/{product.id}` path, added list/get/deactivate endpoints, and aligned update response schema.
11. **Category routes:** added list/get/update/delete endpoints and consistent response schemas.
12. **Application startup:** added `/health`, CORS configuration, API version prefix `/api/v1`, and development-only schema creation. Production database changes should use migrations.
13. **Repository hygiene:** excluded `.git`, `.venv`, bytecode caches, and the original `.env` from the delivered ZIP. Never distribute real secrets.
14. **Additional route modules:** added endpoints for authentication/users, roles, brands, suppliers, customers, warehouses, units, purchasing, goods receipts, sales, invoices, payments, transfers, returns, alerts, notifications, reorder rules, forecasting, recommendations, audit logs and reports.
15. **Transaction workflows:** added atomic stock movement/ledger endpoints, partial purchase receiving, sales checkout with stock deduction/invoice/optional payment, staged transfer actions and return approval.
16. **MVC layering:** added shared CRUD service and repository helpers for simple resource endpoints.
17. **Dependencies and docs:** added setup instructions, route inventory, smoke tests and an explicit production-readiness checklist.

## What was not silently claimed as complete

This revision adds many of the missing route modules and core workflows, but production authorization is not yet consistently enforced on every route. Payment reconciliation/idempotency, transfer cancellation and partial receiving, full audit coverage, external delivery integrations, trained forecasting, Alembic migration history and broad PostgreSQL integration tests remain work items. Those need implementation and testing, not just route definitions.

## API behavior changes to note

- Category path is now `/api/v1/categories/` (lowercase and versioned).
- Product path is now `/api/v1/products/` (plural and versioned).
- Product DELETE is a soft deactivation (`is_active=false`) so historical records can remain.
- Workflow endpoints are listed in `ROUTES_AND_WORKFLOWS.md`; some resource CRUD endpoints intentionally do not replace full business workflows.
- Local development defaults to SQLite. PostgreSQL is configured with `DATABASE_URL` in `.env`.

## Revision: security and planning hardening

- Business routes now require a JWT bearer token; identity and role administration also requires the `admin` role.
- Added a trusted CLI utility to create the first administrator after migrations.
- Added stockout estimates, dead-stock detection, a daily-demand forecast baseline, and demand-based purchase recommendation refresh.
- Checkout now derives product price/tax from the product master and uses the authenticated user ID. Purchase receiving uses the PO line's price.
- Added an initial Alembic migration and expanded the smoke tests.
- Important: the system is not production-certified. Granular role/warehouse permissions, payment idempotency/reconciliation, PostgreSQL concurrency tests, tax-policy confirmation, and operational monitoring remain required. See `PRODUCTION_READINESS.md`.


## Role-based access and forecasting update

- The initial Admin is created with `python -m scripts.create_admin`; the script seeds the six canonical roles from the project PDF.
- Public registration is disabled. Admin creates users and assigns `admin`, `inventory_manager`, `purchase_manager`, `sales_staff`, `warehouse_staff`, or `finance_billing_staff`.
- The database-assigned role is checked for each request. Admin has full access; staff permissions are restricted by module and selected write/workflow actions.
- Added `app/services/forecast_service.py`: daily sales series includes zero-sale days and supports linear regression, weighted moving average, and moving average.
- Purchase recommendation refresh now uses the linear-regression demand forecast plus safety stock, current available stock, and known incoming purchase quantities where the current schema supports them.
- Verification in this revision: `pytest -q` — 12 passed; Python compilation passed; initial Alembic migration passed on a disposable SQLite database. Date/time deprecation warnings remain.
- This is still not production-certified. Review `PRODUCTION_READINESS.md`, especially PostgreSQL concurrency, full action-by-action RBAC, warehouse scoping, payment lifecycle, and forecast backtesting.

## Follow-up hardening revision (2026-10-26)

- Added a destination warehouse to purchase orders and a migration; warehouse-specific stockout and reorder planning can now account for outstanding quantities assigned to that warehouse.
- Added a manual invoice-payment workflow that checks the remaining balance, updates invoice payment state, and supports an optional `Idempotency-Key` header. This is not a payment-gateway integration.
- Replaced unrestricted generic payment writes with a purpose-specific record-payment endpoint and a finance-only payment list.
- Added optional MongoDB operational-event history for successful sales, receipts, transfers, returns, and payments. PostgreSQL remains the source of truth; MongoDB event writes are best-effort and non-authoritative.
- Added Docker Compose configuration for PostgreSQL, MongoDB, and the FastAPI service, including health checks and migration execution.
- Added regression tests for the new route/schema contracts and optional MongoDB behavior.
- Verified `python -m compileall -q .`, `pytest -q` (15 passed), and the Alembic migration chain against a fresh SQLite database. PostgreSQL concurrency and full production deployment still require separate verification.
