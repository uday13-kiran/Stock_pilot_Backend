# StockPilot hardening and readiness notes

This archive improves the previous baseline, but it is **not certified or guaranteed production-ready**. Inventory, payment, and purchasing software requires environment-specific security review, PostgreSQL integration testing, and business-owner acceptance before handling live data.

## Changes made in this revision

- Protected business API routers with bearer-token authentication; `/health`, login, and development registration remain public. Added `/api/v1/auth/me`.
- Disabled public registration outside development unless `ALLOW_PUBLIC_REGISTRATION=true` is explicitly configured.
- Added production settings checks that reject the sample JWT secret or short secrets and reject `DEBUG=true`.
- Restricted user, role, user-role, and warehouse-user administration endpoints to the `admin` role.
- Added a trusted-environment bootstrap script: `python -m scripts.create_admin`; it creates the canonical six role records.
- Disabled public registration in all environments. Admin creates users and assigns a validated database role through `POST /api/v1/users/`.
- Added role-based access policies for major module groups, Admin-only catalog writes and identity administration, and role checks on the multi-step purchase/sales/transfer workflows.
- Added a separate `app/services/forecast_service.py` with linear-regression trend forecasting, weighted moving average and moving-average baselines; the API returns explainable forecast metadata and persists generated forecasts.
- Added demand-planning endpoints for stockout estimates, dead-stock detection, daily-demand forecasting, and purchase-recommendation refresh.
- Improved checkout to use product-master prices and tax rates, calculate monetary values to two decimal places, use the authenticated user rather than a client-supplied user ID, reject duplicate products in a checkout, and update stock/ledger/invoice/payment within one database transaction.
- Purchase receiving now uses the purchase-order line price instead of trusting the receipt request's unit price.
- Stock deductions now reject movements that would consume reserved stock.
- Added Alembic configuration and an initial schema migration for new databases.
- Expanded automated tests to cover authentication requirements and planning endpoint empty states.

## Verification performed in this workspace

- `python -m compileall -q .` — passed.
- `pytest -q` — **12 passed** in the original uploaded workspace; re-run the suite after any changes. SQLAlchemy emits legacy-naive-UTC deprecation warnings; these should be resolved as part of the datetime/timezone migration.
- `DATABASE_URL=sqlite:////tmp/stockpilot_migration.db alembic upgrade head` on a disposable empty SQLite database — passed.
- FastAPI import/OpenAPI generation — exercised by the test suite.

## Still required before a real production deployment

1. **Finish action-by-action authorization review.** Role guards now cover major modules and selected writes/workflows, but some legacy generic CRUD endpoints still permit multiple actions to the same module role. Verify every HTTP method and add warehouse-scoped permissions before production.
2. **Payments:** generic payment CRUD has been replaced with a balance-checked manual recording endpoint and optional idempotency key. It is not a payment gateway integration; online payment provider callbacks, refund reconciliation, and provider-specific state transitions still require implementation before live payments.
3. **Database:** run the migration against a fresh PostgreSQL database and a disposable copy of any existing database. The initial migration is for a new schema; do not apply it blindly to a database whose tables already exist. Review generated migrations and establish a safe baseline for existing installations.
4. **Concurrency:** add PostgreSQL integration tests for concurrent sales, purchase receiving, transfers, return caps, and simultaneous adjustments. SQLite tests do not prove PostgreSQL row-locking behavior.
5. **Financial rules:** confirm tax treatment for global discounts, tax rounding, returns/refunds, invoice status, and currency precision with the actual business rules. Current checkout uses product tax percentages and applies global discounts after line-level tax calculation; jurisdiction-specific handling may differ.
6. **Purchase order location:** purchase orders now include an optional destination warehouse and a migration. Legacy orders may still have no warehouse until their first receipt assigns one; review those records before relying on warehouse-level incoming-stock estimates.
7. **Business lifecycle:** implement and test cancellation/reversal workflows with compensating ledger entries, adjustment approval thresholds, partial transfer receipt/cancellation, purchase order approval policy, credit limits, and return/refund accounting.
8. **Operational controls:** add a production-grade rate limiter, structured logs, monitoring/alerting, backups and restore drills, secret management, TLS, restricted CORS, deployment health checks, and dependency/security scanning.
9. **Forecast quality:** the forecast is a transparent historical daily-average baseline, not trained AI/ML. Backtest it against representative sales data and evaluate seasonal/trend-aware models before relying on recommendations.
10. **Acceptance tests:** add comprehensive automated tests for all required business rules and run the full suite against PostgreSQL in CI.

## Important limitations

- Dead-stock and stockout endpoints are heuristic planning aids, not guaranteed predictions.
- Purchase recommendations use current stock, historical daily demand, safety stock, and open inbound purchase-order quantities attributed to the purchase order destination warehouse. Legacy orders with no destination are excluded from warehouse-specific inbound estimates until assigned.
- The code keeps the existing route/service/repository layout, but some legacy endpoints still perform generic CRUD instead of full business workflows.
- Do not connect this revision directly to live financial or inventory operations until the remaining items above are resolved and verified.

## Added in this package revision

- Purchase orders now store a destination warehouse, and warehouse-specific planning can account for inbound quantities.
- Manual invoice payment recording validates remaining balance and supports an optional idempotency key.
- Optional MongoDB operational event history is wired for selected committed workflows. PostgreSQL remains authoritative.
- Docker Compose starts PostgreSQL, MongoDB, and the API, and runs Alembic migrations before serving requests.
