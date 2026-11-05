# StockPilot Backend

FastAPI backend for StockPilot inventory, purchasing, sales, billing, and demand planning. The existing layout is retained: `routes`, `schemas`, `services`, `repositories`, `models`, `rules`, and `core`.

## Quick start (Windows Command Prompt)

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` for Swagger UI and `http://127.0.0.1:8000/health` for health status. Local development defaults to SQLite. For PostgreSQL, set `DATABASE_URL` in `.env`, for example:

```env
DATABASE_URL=postgresql+psycopg://stockpilot_user:your-password@localhost:5432/stockpilot_db
```

Do not commit `.env` or use sample secrets in a deployed environment. Set `ENVIRONMENT=production`, `DEBUG=false`, a unique randomly generated `JWT_SECRET_KEY` of at least 32 characters, a restricted `CORS_ORIGINS`, and `ALLOW_PUBLIC_REGISTRATION=false`.

## First administrator and staff accounts

For a new database, apply migrations first, then create the first administrator from a trusted terminal:

```bat
python -m scripts.create_admin
```

The script prompts for the administrator's name, email, and password, creates the six canonical roles if missing, and assigns `admin`. It is a trusted setup command, not a public API. Public registration is disabled in every environment. After login, the Admin creates staff through `POST /api/v1/users/` with `name`, `email`, `password` (minimum 12 characters), and `role_name`.

## Seed realistic demo data

After migrations and administrator creation, add sample data for local frontend development:

```bat
python -m scripts.seed_demo_data --dry-run
python -m scripts.seed_demo_data
```

The repeatable seed creates 18 Indian-market electrical and home-appliance products, three demo suppliers, two Pune warehouse/store locations, and synthetic customers. It also adds completed sales, invoices and payments, received purchase orders, goods receipts, and stock-ledger activity across the previous six complete calendar months. The dated ledger is reconciled to current on-hand inventory; loading historical activity does not change current inventory quantities. It uses `DEMO26-` SKUs, synthetic `DEMO-` barcodes, and reserved `.example` email addresses, skips records already present, and does not create or change user accounts. An active admin account and migrated database are required. Preview with `--dry-run`, then run without that flag to commit. Use a local development database only, never production.

Canonical role names are `admin`, `inventory_manager`, `purchase_manager`, `sales_staff`, `warehouse_staff`, and `finance_billing_staff`. The database's `users.role_id` is authoritative for the current single-role-per-user design; the legacy `user_roles` table remains for schema compatibility and is not used for authorization. Staff role changes are handled through the Admin-only `/api/v1/users/{user_id}` endpoint, so there is no separate multi-role assignment API. A user's role is read from the database on each request, so changing a role takes effect immediately even if the old token is still valid.

## Authentication

All business API routes require `Authorization: Bearer <access_token>`. Obtain a token from `POST /api/v1/auth/login`. `GET /api/v1/auth/me` returns the authenticated user and assigned role. User/role/role-assignment/warehouse-user administration is Admin-only. Catalog writes are Admin-only; sales, purchase, inventory, warehouse, billing, and planning modules have role-based access guards. Some legacy generic CRUD routes still group multiple actions under the same module-level role policy, so review `PRODUCTION_READINESS.md` and complete action-by-action acceptance tests before production.

## Important workflow endpoints

- `POST /api/v1/purchase-orders/workflow` — creates a draft purchase order with its supplier, destination warehouse, and one or more product/quantity lines atomically. The authenticated user is recorded as the creator; line pricing falls back from the supplier price to product purchase price. The purchase-order screen supports inline supplier, warehouse, product, category, brand, and unit creation.
- `POST /api/v1/purchase-orders/{purchase_order_id}/receive` — partial/full receiving, inventory increase, and stock ledger entry in one database transaction.
- `GET /api/v1/inventory/?warehouse_id=<id>&skip=0&limit=500` — warehouse-filtered inventory balances for sales, inventory, and warehouse views. Sale checkout validates availability and deducts sold quantities from the chosen warehouse in the same transaction as the sale.
- `GET /api/v1/notifications/low-stock` — live low-stock notifications with product, warehouse/location, quantity, reorder level, safety stock, and severity; the frontend bell displays the active alert count.
- `POST /api/v1/sales/checkout` — sale lines, server-side product prices/tax, stock deduction, invoice, and optional payment record in one database transaction.
- `POST /api/v1/stock-transfers/{transfer_id}/items`, `/approve`, `/dispatch`, `/receive` — staged transfer actions.
- `POST /api/v1/sales-returns/{return_id}/approve` — validates returned quantities against original sales and restores stock.
- `POST /api/v1/inventory/stock-in`, `/stock-out`, `/adjust`, `/transfers`; `GET /api/v1/inventory/transactions`.
- `GET /api/v1/planning/stockout-predictions` — stockout estimates from recent daily sales.
- `GET /api/v1/planning/dead-stock` — products with available stock and no recent sales.
- `GET /api/v1/planning/product-trends` — percentage change between the last two complete calendar months, using completed sales less approved returns; supports `warehouse_id`.
- `GET /api/v1/planning/purchase-planning` — ranked purchase candidates with priority, estimated stockout date, suggested quantity, order-by date, supplier lead time, inventory, incoming orders, and overstock records.
- `POST /api/v1/planning/assistant/query` — deterministic backend answers for supported purchase, demand-trend, stockout, and dead-stock questions. For example, send `{"question":"Which products should we purchase this week?"}`.
- `GET /api/v1/planning/assistant/insights` — combined trend, stockout, dead-stock, purchase, and overstock results for a chat or dashboard UI.
- `GET /api/v1/planning/forecast-backtest/{product_id}` — compares one chosen forecast method against a recent historical holdout and returns MAE and weighted absolute percentage error.
- `POST /api/v1/assistant/ask` — LLM-powered natural-language answers using read-only sales, purchase-planning, trends, stockout, and dead-stock analytics tools. Returns the evidence used.
- `GET /api/v1/planning/demand-forecast/{product_id}` — daily-demand forecasting. Supports `method=linear_regression` (default), `method=weighted_moving_average`, or `method=moving_average`; also supports `warehouse_id`, `lookback_days`, and `forecast_days`.
- `POST /api/v1/planning/purchase-recommendations/refresh` — demand/safety-stock purchase suggestions.
- `GET /api/v1/reports/*` — inventory, sales, purchase, movement summaries, and baseline forecast reporting.
- `GET /api/v1/reports/inventory-summary` — total units, available units, inventory records, catalogue product count, and distinct products with available stock.

The forecasting service includes a lightweight least-squares linear-regression trend model plus weighted and simple moving-average baselines. It fills zero-sale calendar days, uses completed sales net of approved returns, supports warehouse filters, stores each forecast result, and returns the method and historical summary for transparency. Purchase planning forecasts across supplier lead time plus the review period, then accounts for safety stock, reorder/maximum levels, available inventory, and outstanding incoming quantities. Inbound expected delivery dates are not modeled yet, so open PO quantities are assumed available for planning. Trends compare the last two complete calendar months. The deterministic planning assistant does not invoke an LLM; the separate `/api/v1/assistant/ask` endpoint can use an optional configured LLM to explain approved read-only analytics and returns the evidence used. It cannot place purchase orders. Forecasting is not a guarantee of future demand; run the holdout backtest and evaluate its error before relying on suggestions. Purchase orders now support a destination `warehouse_id`; warehouse-specific planning counts outstanding quantities only for matching orders. Legacy orders with no destination are assigned a warehouse when their first receipt is posted.

### Configure the optional LLM analytics assistant

The assistant uses Groq's OpenAI-compatible Chat Completions API with read-only analytics tools. Create a Groq API key, put it in `LLM_API_KEY`, then restart FastAPI. Never commit or share the real API key:

```env
LLM_API_KEY=your-groq-api-key
LLM_MODEL=openai/gpt-oss-20b
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_TIMEOUT_SECONDS=30
```

Confirm the selected model is available for your Groq API key and supports function calling. The assistant sends the question and relevant analytics results to Groq; review the provider's data-retention/privacy terms before using real business data.

## Payments and MongoDB event history

- `POST /api/v1/invoices/{invoice_id}/payments` records a confirmed payment, prevents payment totals from exceeding the invoice balance, and updates the invoice to `PARTIALLY_PAID` or `PAID`. An optional `Idempotency-Key` header makes safe retries possible. This is a manual recordkeeping endpoint, **not** a payment gateway; do not mark online card/UPI payments successful until a trusted provider confirms them.
- MongoDB is used only for supplementary operational events (sale, receipt, transfer, return, and payment history). PostgreSQL remains authoritative for inventory and finance. MongoDB being unavailable does not roll back business transactions.

## Run with Docker (PostgreSQL + MongoDB)

1. Install Docker Desktop and start it.
2. Copy `.env.example` to `.env`.
3. In `.env`, set `JWT_SECRET_KEY` to a unique random value of at least 32 characters, and change both `POSTGRES_PASSWORD` and `MONGO_PASSWORD` from their sample values.
4. Run `docker compose up --build -d` from this folder.
5. Create the first administrator with `docker compose exec api python -m scripts.create_admin`.
6. Open `http://localhost:8000/docs`.

Stop with `docker compose down`; persistent database volumes remain. To remove all local database data as well, use `docker compose down -v` (destructive). Do not expose database ports publicly or use the example passwords in a real deployment. For a hosted deployment, use a managed PostgreSQL/MongoDB service or private network, configure TLS/secrets/backups, and set `CORS_ORIGINS` to the actual frontend origin.

## Migrations

The included initial Alembic migration is for a **new, empty database**:

```bat
alembic upgrade head
```

For an existing database, do not run the initial migration blindly; review the current schema/data and establish a migration baseline or write a migration from the actual existing schema first. For future model changes, generate and review migrations before applying them.

## Tests

```bat
pytest -q
```

The current automated suite is a small smoke/regression suite. It is not a substitute for PostgreSQL concurrency, payment, permissions, migration, and business-rule integration tests.

## Project layout

```text
stockpiolet_backend/
├── main.py
├── app/
│   ├── core/          # settings, database sessions, authentication utilities
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic contracts
│   ├── routes/        # FastAPI endpoints
│   ├── services/      # business/use-case logic
│   ├── repositories/  # persistence/query helpers
│   └── rules/         # reusable validations
├── alembic/           # schema migrations
├── scripts/           # trusted admin bootstrap utility
├── tests/
├── requirements.txt
└── .env.example
```

This revision improves security and workflow behavior, but is **not certified production-ready**. See `PRODUCTION_READINESS.md` for the remaining implementation and deployment requirements.
