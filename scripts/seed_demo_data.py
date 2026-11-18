"""Seed realistic, repeatable catalog, inventory, and six-month activity for local demos.

Run from the project root after applying database migrations:
    python -m scripts.seed_demo_data
Preview without committing:
    python -m scripts.seed_demo_data --dry-run
"""
import argparse
import calendar
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models.brands import Brand
from app.models.category import Category
from app.models.customer import Customer
from app.models.goods_receipt import GoodsReceipt
from app.models.goods_receipt_item import GoodsReceiptItem
from app.models.invoice import Invoice
from app.models.invoice_item import InvoiceItem
from app.models.inventory import Inventory
from app.models.payment import Payment
from app.models.products import Product
from app.models.purchase_order import PurchaseOrder
from app.models.purchaseorder_item import PurchaseOrderItem
from app.models.roles import Role
from app.models.sales import Sale
from app.models.sales_item import SaleItem
from app.models.stock_transaction import StockTransaction
from app.models.supplier import Supplier
from app.models.supplier_products import SupplierProduct
from app.models.units import Unit
from app.models.user import User
from app.models.warehouse import Warehouse

HISTORY_MARKER = "STOCKPILOT DEMO HISTORY V1"
OPENING_STOCK_REFERENCE_ID = 20261026
PAYMENT_METHODS = ("CASH", "CARD", "UPI")


CATEGORIES = {
    "Ceiling Fans": "Residential ceiling fans and air circulation products",
    "Kitchen Appliances": "Mixers, induction cooktops and small kitchen appliances",
    "Water Heaters": "Instant and storage water heaters for home use",
    "Lighting": "LED bulbs and energy-efficient home lighting",
    "Air Coolers": "Room air coolers and seasonal cooling appliances",
}

BRANDS = {
    "Bajaj Electricals": "Indian consumer electricals and home appliances manufacturer",
    "Havells": "Electrical equipment, lighting and home appliances",
    "Crompton": "Fans, pumps and consumer electrical products",
    "Orient Electric": "Fans, lighting and home appliances",
    "Usha": "Fans and household appliances",
    "Philips": "Lighting and consumer electronics",
    "Prestige": "Kitchen appliances and cookware",
    "Symphony": "Residential and commercial air coolers",
}

UNITS = {
    "piece": "One boxed retail appliance or electrical product",
}

PRODUCTS = [
    {"sku": "DEMO26-FAN-001", "barcode": None, "name": "Bajaj Frore Fan 1200mm", "description": "Frore three-blade ceiling fan in white for everyday residential use; 1200 mm sweep.", "category": "Ceiling Fans", "brand": "Bajaj Electricals", "unit": "piece", "selling": "2499.00", "purchase": "1830.00", "tax": "18.00", "reorder": 12, "safety": 5, "maximum": 80, "lead": 7, "stock": (24, 8), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-FAN-002", "barcode": None, "name": "Bajaj Ivora Fan 1200mm", "description": "Ivora decorative three-blade ceiling fan in brown with a 1200 mm sweep.", "category": "Ceiling Fans", "brand": "Bajaj Electricals", "unit": "piece", "selling": "3299.00", "purchase": "2450.00", "tax": "18.00", "reorder": 8, "safety": 3, "maximum": 55, "lead": 7, "stock": (18, 6), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-FAN-003", "barcode": None, "name": "Havells Efficiencia Neo", "description": "1200 mm energy-efficient BLDC ceiling fan with remote control.", "category": "Ceiling Fans", "brand": "Havells", "unit": "piece", "selling": "5499.00", "purchase": "4210.00", "tax": "18.00", "reorder": 6, "safety": 2, "maximum": 35, "lead": 8, "stock": (11, 3), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-FAN-004", "barcode": None, "name": "Crompton Hyperjet Fan", "description": "Energion Hyperjet 1200 mm BLDC ceiling fan with remote and multiple speed settings.", "category": "Ceiling Fans", "brand": "Crompton", "unit": "piece", "selling": "4799.00", "purchase": "3660.00", "tax": "18.00", "reorder": 7, "safety": 3, "maximum": 40, "lead": 8, "stock": (9, 4), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-FAN-005", "barcode": None, "name": "Orient Apex-FX Fan 1200mm", "description": "Apex-FX standard three-blade 1200 mm ceiling fan for home and small office use.", "category": "Ceiling Fans", "brand": "Orient Electric", "unit": "piece", "selling": "2199.00", "purchase": "1610.00", "tax": "18.00", "reorder": 10, "safety": 4, "maximum": 65, "lead": 7, "stock": (21, 7), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-KIT-001", "barcode": None, "name": "Bajaj Rex 500W Mixer", "description": "Rex 500 W mixer grinder with three stainless-steel jars for daily kitchen use.", "category": "Kitchen Appliances", "brand": "Bajaj Electricals", "unit": "piece", "selling": "2699.00", "purchase": "1960.00", "tax": "18.00", "reorder": 10, "safety": 4, "maximum": 60, "lead": 6, "stock": (17, 6), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-KIT-002", "barcode": None, "name": "Bajaj Majesty RX11 Mixer", "description": "Majesty RX11 750 W mixer grinder supplied with multiple jars for wet and dry grinding.", "category": "Kitchen Appliances", "brand": "Bajaj Electricals", "unit": "piece", "selling": "3899.00", "purchase": "2880.00", "tax": "18.00", "reorder": 8, "safety": 3, "maximum": 45, "lead": 6, "stock": (14, 5), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-KIT-003", "barcode": None, "name": "Prestige PIC 20 Cooktop", "description": "PIC 20 1200 W induction cooktop with preset cooking menus and timer.", "category": "Kitchen Appliances", "brand": "Prestige", "unit": "piece", "selling": "2799.00", "purchase": "2030.00", "tax": "18.00", "reorder": 8, "safety": 3, "maximum": 45, "lead": 6, "stock": (16, 5), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-KIT-004", "barcode": None, "name": "Bajaj SWX 3 Toaster", "description": "Majesty New SWX 3 compact two-slice pop-up toaster with browning control.", "category": "Kitchen Appliances", "brand": "Bajaj Electricals", "unit": "piece", "selling": "1799.00", "purchase": "1280.00", "tax": "18.00", "reorder": 7, "safety": 3, "maximum": 40, "lead": 6, "stock": (13, 4), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-WH-001", "barcode": None, "name": "Bajaj Flora 3L Heater", "description": "Flora 3 L instant water heater for kitchens and compact bathrooms.", "category": "Water Heaters", "brand": "Bajaj Electricals", "unit": "piece", "selling": "3299.00", "purchase": "2440.00", "tax": "18.00", "reorder": 6, "safety": 2, "maximum": 35, "lead": 9, "stock": (10, 3), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-WH-002", "barcode": None, "name": "Bajaj Shakti 15L Heater", "description": "New Shakti 15 L storage water heater with insulated tank for family bathrooms.", "category": "Water Heaters", "brand": "Bajaj Electricals", "unit": "piece", "selling": "8999.00", "purchase": "6740.00", "tax": "18.00", "reorder": 4, "safety": 2, "maximum": 24, "lead": 10, "stock": (7, 2), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-WH-003", "barcode": None, "name": "Havells Instanio Heater", "description": "Instanio 3 L instant water heater with LED temperature indicator.", "category": "Water Heaters", "brand": "Havells", "unit": "piece", "selling": "3999.00", "purchase": "2980.00", "tax": "18.00", "reorder": 5, "safety": 2, "maximum": 30, "lead": 10, "stock": (8, 3), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-LGT-001", "barcode": None, "name": "Philips Stellar Bright 9W", "description": "Stellar Bright 9 W cool daylight energy-saving LED bulb with B22 base for home fixtures.", "category": "Lighting", "brand": "Philips", "unit": "piece", "selling": "149.00", "purchase": "91.00", "tax": "18.00", "reorder": 30, "safety": 12, "maximum": 220, "lead": 4, "stock": (76, 26), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-LGT-002", "barcode": None, "name": "Bajaj Ivora LED Bulb 12W", "description": "Ivora 12 W cool white LED bulb for standard household B22 fittings.", "category": "Lighting", "brand": "Bajaj Electricals", "unit": "piece", "selling": "129.00", "purchase": "78.00", "tax": "18.00", "reorder": 24, "safety": 10, "maximum": 180, "lead": 4, "stock": (62, 21), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-LGT-003", "barcode": None, "name": "Havells Adore Bulb 15W", "description": "Adore 15 W B22 LED bulb for bright general-purpose room lighting.", "category": "Lighting", "brand": "Havells", "unit": "piece", "selling": "189.00", "purchase": "119.00", "tax": "18.00", "reorder": 18, "safety": 7, "maximum": 140, "lead": 4, "stock": (44, 15), "supplier": "Western Electrical Distributors"},
    {"sku": "DEMO26-COOL-001", "barcode": None, "name": "Bajaj DMH 65 Cooler", "description": "DMH 65 large-room desert cooler with high-capacity water tank and multi-speed fan.", "category": "Air Coolers", "brand": "Bajaj Electricals", "unit": "piece", "selling": "12999.00", "purchase": "9870.00", "tax": "18.00", "reorder": 3, "safety": 1, "maximum": 18, "lead": 12, "stock": (5, 2), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-COOL-002", "barcode": None, "name": "Symphony Diet 55i Cooler", "description": "Diet 3D 55i compact personal air cooler with remote control and multi-directional airflow.", "category": "Air Coolers", "brand": "Symphony", "unit": "piece", "selling": "10999.00", "purchase": "8290.00", "tax": "18.00", "reorder": 3, "safety": 1, "maximum": 16, "lead": 12, "stock": (4, 1), "supplier": "Deccan Home Appliances"},
    {"sku": "DEMO26-FAN-006", "barcode": None, "name": "Usha Striker Galaxy Fan", "description": "Striker Galaxy decorative ceiling fan with 1200 mm sweep for residential rooms.", "category": "Ceiling Fans", "brand": "Usha", "unit": "piece", "selling": "3499.00", "purchase": "2580.00", "tax": "18.00", "reorder": 7, "safety": 3, "maximum": 40, "lead": 7, "stock": (12, 4), "supplier": "Western Electrical Distributors"},
]

SUPPLIERS = [
    {"name": "Western Electrical Distributors", "contact": "Nikhil Deshmukh", "email": "orders@western-electrical.example", "phone": "+91-90000-31001", "address": "Market Yard, Gultekdi, Pune, Maharashtra"},
    {"name": "Deccan Home Appliances", "contact": "Sneha Patil", "email": "sales@deccan-appliances.example", "phone": "+91-90000-31002", "address": "Bhosari MIDC, Pune, Maharashtra"},
    {"name": "National Lighting Supply", "contact": "Rahul Joshi", "email": "supply@national-lighting.example", "phone": "+91-90000-31003", "address": "Nana Peth Electrical Market, Pune, Maharashtra"},
]

WAREHOUSES = [
    {"name": "Hyderabad Central Distribution Centre", "location": "Hyderabad, Telangana", "address": "Sector 7, Bhosari MIDC, Pune 411026"},
    {"name": "Pune Camp Electronics Store", "location": "Pune, Maharashtra", "address": "M.G. Road, Camp, Pune 411001"},
]

CUSTOMERS = [
    {"name": "Aarav Kulkarni", "email": "aarav.kulkarni@demo.stockpilot.example", "phone": "+91-90000-41001", "address": "Kothrud, Pune, Maharashtra"},
    {"name": "Isha Deshpande", "email": "isha.deshpande@demo.stockpilot.example", "phone": "+91-90000-41002", "address": "Aundh, Pune, Maharashtra"},
    {"name": "Rohan Mehta", "email": "rohan.mehta@demo.stockpilot.example", "phone": "+91-90000-41003", "address": "Baner, Pune, Maharashtra"},
    {"name": "Sana Shaikh", "email": "sana.shaikh@demo.stockpilot.example", "phone": "+91-90000-41004", "address": "Kondhwa, Pune, Maharashtra"},
    {"name": "Aditya Joshi", "email": "aditya.joshi@demo.stockpilot.example", "phone": "+91-90000-41005", "address": "Viman Nagar, Pune, Maharashtra"},
    {"name": "Neha Patil", "email": "neha.patil@demo.stockpilot.example", "phone": "+91-90000-41006", "address": "Wakad, Pune, Maharashtra"},
]

HISTORY_CUSTOMERS = [
    {"name": "Kavya Rao", "email": "history.01@demo.stockpilot.example", "address": "Shivajinagar, Pune, Maharashtra"},
    {"name": "Vikram Nair", "email": "history.02@demo.stockpilot.example", "address": "Kalyani Nagar, Pune, Maharashtra"},
    {"name": "Meera Iyer", "email": "history.03@demo.stockpilot.example", "address": "Pashan, Pune, Maharashtra"},
    {"name": "Arjun Shah", "email": "history.04@demo.stockpilot.example", "address": "Hadapsar, Pune, Maharashtra"},
    {"name": "Diya Menon", "email": "history.05@demo.stockpilot.example", "address": "Kharadi, Pune, Maharashtra"},
    {"name": "Kabir Sethi", "email": "history.06@demo.stockpilot.example", "address": "Deccan, Pune, Maharashtra"},
    {"name": "Ananya Bose", "email": "history.07@demo.stockpilot.example", "address": "Pimple Saudagar, Pune, Maharashtra"},
    {"name": "Ishaan Kapoor", "email": "history.08@demo.stockpilot.example", "address": "Vishrantwadi, Pune, Maharashtra"},
]


def _six_full_months(reference: datetime) -> tuple[datetime, datetime, list[datetime]]:
    period_end = datetime(reference.year, reference.month, 1)
    start_index = period_end.year * 12 + period_end.month - 1 - 6
    period_start = datetime(start_index // 12, start_index % 12 + 1, 1)
    months = []
    for offset in range(6):
        month_index = start_index + offset
        months.append(datetime(month_index // 12, month_index % 12 + 1, 1))
    return period_start, period_end, months


def _monthly_demand(product_index: int, warehouse_index: int, category: str) -> tuple[int, ...]:
    seasonal_factors = {
        "Ceiling Fans": (1.45, 1.30, 1.12, 0.96, 0.82, 0.72),
        "Air Coolers": (1.65, 1.42, 1.08, 0.72, 0.48, 0.36),
        "Kitchen Appliances": (0.78, 0.84, 0.92, 1.00, 1.12, 1.27),
        "Water Heaters": (0.72, 0.80, 0.90, 1.00, 1.16, 1.38),
        "Lighting": (0.80, 0.86, 0.94, 1.04, 1.18, 1.34),
    }
    base = 2 + product_index % 3 + warehouse_index
    return tuple(
        max(1, int(base * factor + 0.5))
        for factor in seasonal_factors[category]
    )


def _seed_history(
    db: Session,
    counts: dict[str, int],
    warehouses: dict[str, Warehouse],
    suppliers: dict[str, Supplier],
) -> bool:
    print("Checking demo history and preparing historical activity...", flush=True)
    email_values = [customer["email"] for customer in HISTORY_CUSTOMERS]
    history_customers = db.scalars(
        select(Customer)
        .where(Customer.email.in_(email_values))
        .order_by(Customer.id)
    ).all()
    history_customer_ids = [customer.id for customer in history_customers]
    has_history_sales = bool(
        history_customer_ids
        and db.scalar(
            select(Sale.id)
            .where(Sale.customer_id.in_(history_customer_ids))
            .limit(1)
        )
    )
    has_history_purchase_orders = bool(
        db.scalar(
            select(PurchaseOrder.id)
            .where(PurchaseOrder.notes.like(f"{HISTORY_MARKER}%"))
            .limit(1)
        )
    )
    if has_history_sales and has_history_purchase_orders:
        print("Historical demo activity is already present; skipping it.", flush=True)
        return False
    if has_history_sales or has_history_purchase_orders:
        raise RuntimeError(
            "A partial StockPilot demo history already exists. "
            "No new records were added; inspect the marked demo sales and purchase orders."
        )

    admin = db.scalar(
        select(User)
        .join(Role, User.role_id == Role.id)
        .where(Role.name == "admin", User.is_active.is_(True))
        .order_by(User.id)
        .limit(1)
    )
    if admin is None:
        raise RuntimeError(
            "Create an active administrator after database migrations before loading demo history."
        )

    customers_by_email = {
        details["email"]: _get_or_create(
            db,
            Customer,
            "email",
            details["email"],
            {
                "name": details["name"],
                "phone": None,
                "address": details["address"],
                "is_active": True,
            },
            counts,
        )[0]
        for details in HISTORY_CUSTOMERS
    }

    period_start, period_end, months = _six_full_months(datetime.now())
    item_by_sku = {item["sku"]: item for item in PRODUCTS}
    products = db.scalars(
        select(Product)
        .where(Product.sku.in_(item_by_sku))
        .order_by(Product.sku)
    ).all()
    product_by_sku = {product.sku: product for product in products}
    product_by_id = {product.id: product for product in products}
    if len(product_by_sku) != len(PRODUCTS):
        raise RuntimeError("The demo catalog is incomplete; seed products before demo history.")

    warehouse_list = list(warehouses.values())
    inventory_rows = db.scalars(
        select(Inventory).where(
            Inventory.product_id.in_([product.id for product in products]),
            Inventory.warehouse_id.in_([warehouse.id for warehouse in warehouse_list]),
        )
    ).all()
    inventory_by_pair = {
        (row.product_id, row.warehouse_id): row for row in inventory_rows
    }
    expected_pairs = len(products) * len(warehouse_list)
    if len(inventory_by_pair) != expected_pairs:
        raise RuntimeError(
            "Demo inventory is incomplete; create inventory rows for every demo product and warehouse first."
        )

    print(
        f"Planning six months of activity for {len(products)} products "
        f"across {len(warehouse_list)} warehouses...",
        flush=True,
    )
    monthly_units: dict[tuple[int, int], tuple[int, ...]] = {}
    for warehouse_index, warehouse in enumerate(warehouse_list):
        for product_index, product in enumerate(products):
            item = item_by_sku[product.sku]
            monthly_units[(product.id, warehouse.id)] = _monthly_demand(
                product_index,
                warehouse_index,
                item["category"],
            )

    planned_sales: list[dict] = []
    for month_index, month_start in enumerate(months):
        month_end_day = calendar.monthrange(month_start.year, month_start.month)[1]
        for warehouse_index, warehouse in enumerate(warehouse_list):
            rng = random.Random(
                month_start.year * 10000 + month_start.month * 100 + warehouse_index
            )
            products_for_warehouse = [
                product
                for product in products
                if (product.id, warehouse.id) in monthly_units
            ]
            total_units = sum(
                monthly_units[(product.id, warehouse.id)][month_index]
                for product in products_for_warehouse
            )
            order_count = max(6, min(18, round(total_units / 3)))
            order_lines: list[dict[int, int]] = [dict() for _ in range(order_count)]
            for product in products_for_warehouse:
                quantity = monthly_units[(product.id, warehouse.id)][month_index]
                for _ in range(quantity):
                    order_index = rng.randrange(order_count)
                    order_lines[order_index][product.id] = (
                        order_lines[order_index].get(product.id, 0) + 1
                    )

            for lines in order_lines:
                if not lines:
                    continue
                sale_date = month_start.replace(
                    day=rng.randint(2, month_end_day),
                    hour=rng.randint(10, 20),
                    minute=rng.randint(0, 59),
                )
                customer = rng.choice(list(customers_by_email.values()))
                planned_sales.append(
                    {
                        "sale_date": sale_date,
                        "customer_id": customer.id,
                        "warehouse_id": warehouse.id,
                        "lines": lines,
                    }
                )

    receipt_lines: dict[tuple[int, int, int], list[tuple[Product, int]]] = {}
    for warehouse in warehouse_list:
        for product_index, product in enumerate(products):
            item = item_by_sku[product.sku]
            supplier = suppliers[item["supplier"]]
            inventory = inventory_by_pair[(product.id, warehouse.id)]
            buffer_quantity = min(max(product.safety_stock, 1), inventory.quantity)
            demand = monthly_units[(product.id, warehouse.id)]
            for month_index in range(1, 6):
                quantity = demand[month_index]
                if month_index == 5:
                    quantity += inventory.quantity - buffer_quantity
                receipt_lines.setdefault(
                    (month_index, warehouse.id, supplier.id), []
                ).append((product, quantity))

    product_ids = [product.id for product in products]
    existing_transactions = db.scalars(
        select(StockTransaction)
        .where(
            StockTransaction.product_id.in_(product_ids),
            StockTransaction.created_at >= period_start,
        )
        .order_by(StockTransaction.created_at, StockTransaction.id)
    ).all()
    opening_rows = db.scalars(
        select(StockTransaction).where(
            StockTransaction.product_id.in_(product_ids),
            StockTransaction.transaction_type == "OPENING_STOCK",
            StockTransaction.reference_type == "demo_seed",
        )
    ).all()
    opening_rows_by_pair: dict[tuple[int, int], list[StockTransaction]] = {}
    for row in opening_rows:
        opening_rows_by_pair.setdefault((row.product_id, row.warehouse_id), []).append(row)

    movements_by_pair: dict[tuple[int, int], list[tuple[datetime, int]]] = {}
    post_period_net: dict[tuple[int, int], int] = {}
    for transaction in existing_transactions:
        if (
            transaction.transaction_type == "OPENING_STOCK"
            and transaction.reference_type == "demo_seed"
        ):
            continue
        pair = (transaction.product_id, transaction.warehouse_id)
        if transaction.created_at < period_end:
            movements_by_pair.setdefault(pair, []).append(
                (transaction.created_at, transaction.quantity)
            )
        else:
            post_period_net[pair] = (
                post_period_net.get(pair, 0) + transaction.quantity
            )

    for (month_index, warehouse_id, _supplier_id), lines in list(receipt_lines.items()):
        if month_index != 5:
            continue
        adjusted_lines = []
        for product, _quantity in lines:
            pair = (product.id, warehouse_id)
            target_close = (
                inventory_by_pair[pair].quantity - post_period_net.get(pair, 0)
            )
            if target_close < 0:
                raise RuntimeError(
                    f"Post-period demo stock movements for product {product.id} "
                    f"in warehouse {warehouse_id} exceed its current inventory."
                )
            buffer_quantity = min(max(product.safety_stock, 1), target_close)
            quantity = (
                monthly_units[pair][month_index]
                + target_close
                - buffer_quantity
            )
            adjusted_lines.append((product, quantity))
        receipt_lines[(month_index, warehouse_id, _supplier_id)] = adjusted_lines

    for planned in planned_sales:
        for product_id, quantity in planned["lines"].items():
            movements_by_pair.setdefault(
                (product_id, planned["warehouse_id"]), []
            ).append((planned["sale_date"], -quantity))
    for (month_index, warehouse_id, _supplier_id), lines in receipt_lines.items():
        receipt_date = months[month_index]
        for product, quantity in lines:
            movements_by_pair.setdefault((product.id, warehouse_id), []).append(
                (receipt_date, quantity)
            )

    opening_quantities: dict[tuple[int, int], int] = {}
    for pair, inventory in inventory_by_pair.items():
        transactions = movements_by_pair.get(pair, [])
        target_close = inventory.quantity - post_period_net.get(pair, 0)
        opening_quantity = target_close - sum(quantity for _, quantity in transactions)
        if opening_quantity < 0:
            raise RuntimeError(
                f"Demo stock history for product {pair[0]} in warehouse {pair[1]} "
                "would require negative opening inventory."
            )
        balance = opening_quantity
        for _, quantity in sorted(
            transactions,
            key=lambda movement: (movement[0], movement[1] < 0),
        ):
            balance += quantity
            if balance < 0:
                raise RuntimeError(
                    f"Demo stock history for product {pair[0]} in warehouse {pair[1]} "
                    "would go below zero before a restock."
                )
        if balance != target_close:
            raise RuntimeError("Demo stock history does not reconcile to current inventory.")
        opening_quantities[pair] = opening_quantity

    for pair, opening_quantity in opening_quantities.items():
        rows = opening_rows_by_pair.get(pair, [])
        if len(rows) > 1:
            raise RuntimeError(
                f"Multiple demo opening-stock entries exist for product {pair[0]} "
                f"in warehouse {pair[1]}."
            )
        if rows:
            rows[0].quantity = opening_quantity
            rows[0].created_at = period_start
            counts["StockTransactionUpdated"] = (
                counts.get("StockTransactionUpdated", 0) + 1
            )
        else:
            db.add(
                StockTransaction(
                    product_id=pair[0],
                    warehouse_id=pair[1],
                    transaction_type="OPENING_STOCK",
                    quantity=opening_quantity,
                    reference_type="demo_seed",
                    reference_id=OPENING_STOCK_REFERENCE_ID,
                    created_at=period_start,
                )
            )
            counts["StockTransaction"] = counts.get("StockTransaction", 0) + 1

    print("Adding historical purchase orders and goods receipts...", flush=True)
    receipt_batches = sorted(
        receipt_lines.items(),
        key=lambda entry: (entry[0][0], entry[0][1], entry[0][2]),
    )
    for batch_number, ((month_index, warehouse_id, supplier_id), lines) in enumerate(
        receipt_batches, start=1
    ):
        lines = [(product, quantity) for product, quantity in lines if quantity > 0]
        if not lines:
            continue
        receipt_date = months[month_index]
        lead_time = max(item_by_sku[product.sku]["lead"] for product, _ in lines)
        total_amount = sum(
            (
                Decimal(str(product.purchase_price)) * quantity
                for product, quantity in lines
            ),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        purchase_order = PurchaseOrder(
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            user_id=admin.id,
            order_date=receipt_date - timedelta(days=lead_time),
            expected_delivery_date=receipt_date,
            status="RECEIVED",
            total_amount=total_amount,
            notes=f"{HISTORY_MARKER}: {receipt_date:%Y-%m}",
        )
        db.add(purchase_order)
        db.flush()
        counts["PurchaseOrder"] = counts.get("PurchaseOrder", 0) + 1

        receipt = GoodsReceipt(
            purchase_order_id=purchase_order.id,
            warehouse_id=warehouse_id,
            received_date=receipt_date,
            status="POSTED",
            notes=HISTORY_MARKER,
        )
        db.add(receipt)
        db.flush()
        counts["GoodsReceipt"] = counts.get("GoodsReceipt", 0) + 1
        for product, quantity in lines:
            unit_price = Decimal(str(product.purchase_price)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            line_total = (unit_price * quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            db.add(
                PurchaseOrderItem(
                    purchase_order_id=purchase_order.id,
                    product_id=product.id,
                    quantity=quantity,
                    received_quantity=quantity,
                    unit_price=unit_price,
                    total_price=line_total,
                )
            )
            db.add(
                GoodsReceiptItem(
                    goods_receipt_id=receipt.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=float(unit_price),
                    total_price=float(line_total),
                )
            )
            db.add(
                StockTransaction(
                    product_id=product.id,
                    warehouse_id=warehouse_id,
                    transaction_type="PURCHASE_RECEIPT",
                    quantity=quantity,
                    reference_type="goods_receipt",
                    reference_id=receipt.id,
                    created_at=receipt_date,
                )
            )
            counts["PurchaseOrderItem"] = counts.get("PurchaseOrderItem", 0) + 1
            counts["GoodsReceiptItem"] = counts.get("GoodsReceiptItem", 0) + 1
            counts["StockTransaction"] = counts.get("StockTransaction", 0) + 1
        if batch_number % 3 == 0 or batch_number == len(receipt_batches):
            print(
                f"  Purchase/receipt batches: {batch_number}/{len(receipt_batches)}",
                flush=True,
            )

    print(f"Adding {len(planned_sales)} historical sales...", flush=True)
    ordered_sales = sorted(planned_sales, key=lambda sale: sale["sale_date"])
    for sale_number, planned in enumerate(ordered_sales, start=1):
        lines = []
        subtotal = Decimal("0.00")
        tax_total = Decimal("0.00")
        for product_id, quantity in sorted(planned["lines"].items()):
            product = product_by_id[product_id]
            unit_price = Decimal(str(product.selling_price)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            line_subtotal = (unit_price * quantity).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            line_tax = (
                line_subtotal * Decimal(str(product.tax_percent)) / Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal += line_subtotal
            tax_total += line_tax
            lines.append((product, quantity, unit_price, line_subtotal, line_tax))

        total = subtotal + tax_total
        sale = Sale(
            customer_id=planned["customer_id"],
            user_id=admin.id,
            warehouse_id=planned["warehouse_id"],
            sale_date=planned["sale_date"],
            subtotal=float(subtotal),
            discount_amount=0,
            tax_amount=float(tax_total),
            total_amount=float(total),
            status="COMPLETED",
        )
        db.add(sale)
        db.flush()
        counts["Sale"] = counts.get("Sale", 0) + 1

        invoice = Invoice(
            sale_id=sale.id,
            invoice_date=planned["sale_date"],
            subtotal=float(subtotal),
            tax_amount=float(tax_total),
            total_amount=float(total),
            status="PAID",
        )
        db.add(invoice)
        db.flush()
        counts["Invoice"] = counts.get("Invoice", 0) + 1
        for product, quantity, unit_price, line_subtotal, line_tax in lines:
            line_total = line_subtotal + line_tax
            db.add(
                SaleItem(
                    sale_id=sale.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=float(unit_price),
                    discount_amount=0,
                    tax_amount=float(line_tax),
                    total_price=float(line_total),
                )
            )
            db.add(
                InvoiceItem(
                    invoice_id=invoice.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=float(unit_price),
                    total_price=float(line_total),
                )
            )
            db.add(
                StockTransaction(
                    product_id=product.id,
                    warehouse_id=planned["warehouse_id"],
                    transaction_type="SALE",
                    quantity=-quantity,
                    reference_type="sale",
                    reference_id=sale.id,
                    created_at=planned["sale_date"],
                )
            )
            counts["SaleItem"] = counts.get("SaleItem", 0) + 1
            counts["InvoiceItem"] = counts.get("InvoiceItem", 0) + 1
            counts["StockTransaction"] = counts.get("StockTransaction", 0) + 1
        db.add(
            Payment(
                idempotency_key=f"demo-history-v1-{sale.id}",
                invoice_id=invoice.id,
                amount=float(total),
                payment_method=PAYMENT_METHODS[sale.id % len(PAYMENT_METHODS)],
                payment_date=planned["sale_date"],
                status="PAID",
            )
        )
        counts["Payment"] = counts.get("Payment", 0) + 1
        if sale_number % 25 == 0 or sale_number == len(ordered_sales):
            print(
                f"  Sales: {sale_number}/{len(ordered_sales)} "
                f"({sale_number * 100 // len(ordered_sales)}%)",
                flush=True,
            )

    return True


def _get_or_create(
    db: Session,
    model: type,
    field: str,
    value: str,
    defaults: dict,
    created_counts: dict[str, int],
):
    instance = db.scalar(select(model).where(getattr(model, field) == value))
    if instance is not None:
        return instance, False
    instance = model(**{field: value}, **defaults)
    db.add(instance)
    db.flush()
    created_counts[model.__name__] = created_counts.get(model.__name__, 0) + 1
    return instance, True


def seed(db: Session) -> dict[str, int]:
    print("Checking database schema...", flush=True)
    counts: dict[str, int] = {}
    schema = inspect(engine)
    tables = set(schema.get_table_names())
    required_tables = {
        "categories",
        "brands",
        "units",
        "products",
        "suppliers",
        "supplier_products",
        "warehouses",
        "inventory",
        "stock_transactions",
        "customers",
        "users",
        "roles",
        "sales",
        "sale_items",
        "invoices",
        "invoice_items",
        "payments",
        "purchase_order",
        "purchase_order_items",
        "goods_receipts",
        "goods_receipt_items",
    }
    missing_tables = required_tables - tables
    if missing_tables:
        raise RuntimeError(
            f"Database tables are missing: {', '.join(sorted(missing_tables))}. "
            "Apply migrations first with `alembic upgrade head`."
        )
    product_name_length = next(
        column["type"].length
        for column in schema.get_columns("products")
        if column["name"] == "name"
    )
    too_long_names = [
        item["name"] for item in PRODUCTS if len(item["name"]) > product_name_length
    ]
    if too_long_names:
        raise ValueError(
            f"Product names exceed this database's {product_name_length}-character limit: "
            f"{', '.join(too_long_names)}"
        )

    print(
        "Preparing categories, brands, units, suppliers, warehouses, and customers...",
        flush=True,
    )
    categories = {
        name: _get_or_create(db, Category, "name", name, {"description": description}, counts)[0]
        for name, description in CATEGORIES.items()
    }
    brands = {
        name: _get_or_create(db, Brand, "name", name, {"description": description}, counts)[0]
        for name, description in BRANDS.items()
    }
    units = {
        name: _get_or_create(db, Unit, "name", name, {"description": description}, counts)[0]
        for name, description in UNITS.items()
    }
    suppliers = {
        details["name"]: _get_or_create(
            db, Supplier, "email", details["email"],
            {
                "name": details["name"],
                "contact_person": details["contact"],
                "phone": details["phone"],
                "address": details["address"],
                "is_active": True,
            },
            counts,
        )[0]
        for details in SUPPLIERS
    }
    warehouses = {
        details["name"]: _get_or_create(
            db, Warehouse, "name", details["name"],
            {"location": details["location"], "address": details["address"], "is_active": True},
            counts,
        )[0]
        for details in WAREHOUSES
    }
    customers = {
        details["email"]: _get_or_create(
            db, Customer, "email", details["email"],
            {
                "name": details["name"],
                "phone": details["phone"],
                "address": details["address"],
                "is_active": True,
            },
            counts,
        )[0]
        for details in CUSTOMERS
    }

    print(f"Adding or checking {len(PRODUCTS)} demo products and inventory...", flush=True)
    for product_number, item in enumerate(PRODUCTS, start=1):
        product, _ = _get_or_create(
            db,
            Product,
            "sku",
            item["sku"],
            {
                "barcode": item["barcode"] or f"DEMO-{item['sku']}",
                "name": item["name"],
                "description": item["description"],
                "category_id": categories[item["category"]].id,
                "brand_id": brands[item["brand"]].id,
                "unit_id": units[item["unit"]].id,
                "selling_price": Decimal(item["selling"]),
                "purchase_price": Decimal(item["purchase"]),
                "tax_percent": Decimal(item["tax"]),
                "reorder_level": item["reorder"],
                "safety_stock": item["safety"],
                "maximum_stock": item["maximum"],
                "lead_time": item["lead"],
                "status": "ACTIVE",
                "is_active": True,
            },
            counts,
        )

        supplier = suppliers[item["supplier"]]
        supplier_link = db.scalar(
            select(SupplierProduct).where(
                SupplierProduct.supplier_id == supplier.id,
                SupplierProduct.product_id == product.id,
            )
        )
        if supplier_link is None:
            db.add(
                SupplierProduct(
                    supplier_id=supplier.id,
                    product_id=product.id,
                    supplier_price=float(item["purchase"]),
                )
            )
            counts["SupplierProduct"] = counts.get("SupplierProduct", 0) + 1

        for warehouse, quantity in zip(warehouses.values(), item["stock"]):
            inventory = db.scalar(
                select(Inventory).where(
                    Inventory.product_id == product.id,
                    Inventory.warehouse_id == warehouse.id,
                )
            )
            if inventory is None:
                reserved = 2 if quantity > 10 and item["reorder"] > 15 else 0
                db.add(
                    Inventory(
                        product_id=product.id,
                        warehouse_id=warehouse.id,
                        quantity=quantity,
                        reserved_quantity=reserved,
                        available_quantity=quantity - reserved,
                    )
                )
                db.flush()
                counts["Inventory"] = counts.get("Inventory", 0) + 1

                existing_opening = db.scalar(
                    select(StockTransaction.id).where(
                        StockTransaction.product_id == product.id,
                        StockTransaction.warehouse_id == warehouse.id,
                        StockTransaction.reference_type == "demo_seed",
                        StockTransaction.reference_id == 20261026,
                    )
                )
                if existing_opening is None:
                    db.add(
                        StockTransaction(
                            product_id=product.id,
                            warehouse_id=warehouse.id,
                            transaction_type="OPENING_STOCK",
                            quantity=quantity,
                            reference_type="demo_seed",
                            reference_id=OPENING_STOCK_REFERENCE_ID,
                            created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=14),
                        )
                    )
                    counts["StockTransaction"] = counts.get("StockTransaction", 0) + 1
        if product_number % 5 == 0 or product_number == len(PRODUCTS):
            print(
                f"  Products and inventory: {product_number}/{len(PRODUCTS)} "
                f"({product_number * 100 // len(PRODUCTS)}%)",
                flush=True,
            )

    print("Preparing historical sales and purchasing data...", flush=True)
    _seed_history(db, counts, warehouses, suppliers)
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Load repeatable StockPilot demo data.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the records that would be added, then roll back all changes.",
    )
    args = parser.parse_args()
    db = SessionLocal()
    try:
        print("Starting demo data seed...", flush=True)
        counts = seed(db)
        db.flush()
        if args.dry_run:
            print("Dry run: rolling back previewed changes...", flush=True)
            db.rollback()
        else:
            print("Committing demo data...", flush=True)
            db.commit()
            print("Database commit complete.", flush=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    if counts:
        print("Demo data to be added:" if args.dry_run else "Demo data added:")
        for model, count in sorted(counts.items()):
            print(f"  {model}: {count}")
    else:
        print("Demo data is already present; no records would be added.")
    print(f"Products defined: {len(PRODUCTS)}")
    print(f"Demo customers: {len(CUSTOMERS)}")
    print(f"Warehouses: {len(WAREHOUSES)}")
    period_start, period_end, _ = _six_full_months(datetime.now())
    print(
        "Historical activity period: "
        f"{period_start.date()} through {(period_end - timedelta(days=1)).date()}"
    )
    if args.dry_run:
        print("Dry run complete; no database changes were committed.")


if __name__ == "__main__":
    main()
