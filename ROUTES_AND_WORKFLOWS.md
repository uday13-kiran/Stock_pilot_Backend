# StockPilot API route inventory

All endpoints below are mounted under `/api/v1`. Use `/docs` for the live OpenAPI contract.

## Authentication and users
- `POST /auth/register` (disabled; returns 403), `POST /auth/login`, `GET /auth/me`
- Admin-only `POST /users/` creates a user and assigns one of the six canonical roles; Admin-only `GET /users/`, `GET /users/{id}`, and `PATCH /users/{id}` manage staff.

## Master data
- Categories: `/categories` (existing route module)
- Products: `/product` (existing route module)
- `/roles` is read-only for the canonical roles; brands/units/catalog writes are Admin-only; supplier/purchasing, customer/sales, inventory/warehouse and billing modules have role guards. Delete requests deactivate records when the model has `is_active`; history-oriented records are not hard-deleted.

## Purchasing and receiving
- `/purchase-orders`, `/purchase-order-items`, `/goods-receipts`, `/goods-receipt-items`
- `POST /purchase-orders/workflow` creates a `DRAFT` order and its product lines atomically. Required fields are `supplier_id`, `warehouse_id`, and one or more `items` containing `product_id` and positive `quantity`. The authenticated user is recorded as the creator; order date, status, and total are calculated by the server. Supplier-linked prices are used when available, then an optional line `unit_price`, then the product purchase price. Missing supplier-product links are created for the selected supplier.
- The purchase-order screen allows the user to create missing suppliers, products, and warehouses inline. A new product still requires its category, brand, and unit; these can also be created from the product form.
- Approve a draft with `POST /purchase-orders/{purchase_order_id}/approve`. Approval checks for a destination warehouse, at least one valid line, and a supplier-product association. Existing endpoints for creating orders and adding lines separately remain available.
- Only draft orders can be edited or have lines added. Receiving requires an `APPROVED`, `ORDERED`, or `PARTIALLY_RECEIVED` order and posts receipt rows, inventory balances, and stock ledger transactions atomically through `POST /purchase-orders/{purchase_order_id}/receive`.
- The selected warehouse is the inventory destination. Receipts for an order with a destination warehouse must use that warehouse.

## Sales and billing
- `/sales`, `/sale-items`, `/invoices`, `/invoice-items`, `/payments`, `/sales-returns`, `/sales-return-items`
- `POST /sales/checkout` creates the sale and invoice, deducts inventory, writes stock ledger entries, and can record a full payment in one transaction. When checkout records payment, the invoice is marked `PAID`; use `/invoices/{invoice_id}/payments` for partial or later payments.

## Inventory and transfer
- `GET /inventory/?warehouse_id=<id>&skip=0&limit=500` lists warehouse inventory balances for inventory, warehouse, and sales roles; `POST /inventory/` creates inventory records for inventory managers. Also `POST /inventory/stock-in`, `/stock-out`, `/adjust`, `/transfers`; `GET /inventory/transactions`.
- Sales checkout lists only products with available stock in the selected warehouse. The checkout transaction rechecks stock and atomically deducts it from that warehouse; the inventory dashboard shows balances grouped by warehouse and product detail.
- Movement endpoints write a stock ledger entry in the same transaction and reject negative inventory. Transfer endpoint performs immediate source-to-destination movement; it is not the multi-stage approval lifecycle specified in the brief.

## Planning, alerts, reporting and audit
- `/stock-adjustments`, `/stock-transfers`, `/stock-transfer-items`, `/reorder-rules`, `/demand-forecasts`, `/purchase-recommendations`, `/stock-alerts`, `/notifications`, `/audit-logs`
- `/reports/inventory-summary`, `/sales-summary`, `/purchase-summary`, `/stock-movements`, `/refresh-reorder-recommendations`, `/forecast/{product_id}`
- `/reports/inventory-summary` includes total product catalogue count and the distinct number of products with available stock, alongside unit and inventory-record totals.
- `GET /notifications/low-stock` returns live alerts when a warehouse's available quantity is at or below its warehouse reorder rule or the product's default reorder level. Each alert includes product/SKU, warehouse/location, available/total/reserved stock, reorder/safety levels, and severity. The header bell shows the active count and opens the low-stock notification center.
- `GET /planning/product-trends` compares net completed sales in the last two full calendar months and reports month-over-month units, percentage change, and trend direction. Approved sales returns reduce demand; cancelled/non-completed sales are excluded.
- `GET /planning/purchase-planning` ranks this week's purchase candidates by stockout urgency and supplier lead time. Suggested quantities use forecast demand across lead time plus the review window, safety/reorder/maximum levels, available stock, and outstanding destination-warehouse purchase orders; overstock is returned separately. Open inbound quantities are currently treated as immediately available; expected receipt dates are not modeled yet.
- `POST /planning/assistant/query` provides explainable, deterministic answers for supported purchase, trend, stockout, and dead-stock questions. `GET /planning/assistant/insights` returns all of those insight sets together. These endpoints do not invoke an external language model or place purchase orders.
- `GET /planning/forecast-backtest/{product_id}` evaluates a selected forecast method on a historical holdout and returns MAE and weighted absolute percentage error.
- `POST /api/v1/assistant/ask` sends a question to the configured Groq-compatible Chat Completions API with only read-only sales, purchase-planning, trends, stockout, and dead-stock tools. The response includes the analytics evidence used. Configure `LLM_API_KEY` with a Groq API key, `LLM_MODEL`, `LLM_BASE_URL`, and `LLM_TIMEOUT_SECONDS` in the ignored backend `.env`; do not commit the key.
- `GET /planning/demand-forecast/{product_id}` supports `linear_regression` (default), `weighted_moving_average`, and `moving_average`. Linear regression is integrated into purchase recommendation refresh; the forecast is explainable decision support, not a guaranteed prediction.
- Purchase receipts, checkout, staged transfers, and approved returns create/update low-stock alerts at the product reorder level and resolve them when stock recovers. `POST /planning/purchase-recommendations/refresh` refreshes purchase recommendations from inventory, product thresholds or reorder rules, demand forecasts, and incoming orders. It does not create purchase orders; a purchase manager creates, approves, and receives the recommended replenishment through the purchasing workflow.

## Production hardening still required
- Add and run Alembic migrations against a disposable test database, not `create_all` on existing production data.
- All business routers require authentication and major module groups now enforce role policies. Some legacy CRUD routers still group multiple actions under one module policy; review every method and warehouse scope before production.
- Add service-level workflows and integration tests for purchase receipt posting, sale/stock/invoice/payment atomicity, return caps, transfer approval lifecycle, concurrency, idempotency and audit event completeness.
- Configure a strong `JWT_SECRET_KEY`, database credentials, HTTPS, restricted CORS and secrets management before deployment.

## Added payment workflow

- `POST /api/v1/invoices/{invoice_id}/payments` — finance staff records a confirmed payment. Body: `{"amount": 100.00, "payment_method": "UPI"}`. Optional header: `Idempotency-Key: <unique-request-key>`. The API rejects payments above the remaining balance and updates invoice status to `PARTIALLY_PAID` or `PAID`.
- `GET /api/v1/payments/` — finance-only payment listing.

This is a manual payment-recording feature, not a payment processor. Never treat a client request as proof that an external payment succeeded.

## Purchase destination warehouse

Purchase orders now accept optional `warehouse_id`. New orders should set this to the intended destination warehouse. Warehouse-specific stockout/reorder planning accounts for outstanding quantities on matching orders. Legacy orders without a warehouse are assigned the receiving warehouse when their first goods receipt is posted.

## MongoDB operational events

If `MONGODB_URL` is configured, selected successful workflows write supplementary event history to MongoDB. PostgreSQL remains authoritative. When running locally without MongoDB, leave `MONGODB_URL` blank. Docker Compose configures MongoDB for the API automatically.
