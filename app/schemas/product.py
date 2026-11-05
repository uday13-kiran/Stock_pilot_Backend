from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductCreate(BaseModel):
    sku: str
    barcode: str | None = None
    name: str
    description: str | None = None
    category_id: int
    brand_id: int
    unit_id: int
    selling_price: float
    purchase_price: float
    tax_percent: float
    reorder_level: int
    safety_stock: int
    maximum_stock: int
    lead_time: int
    status: str = "ACTIVE"


class ProductUpdate(BaseModel):
    sku: str | None = None
    barcode: str | None = None
    name: str | None = None
    description: str | None = None
    category_id: int | None = None
    brand_id: int | None = None
    unit_id: int | None = None
    selling_price: float | None = None
    purchase_price: float | None = None
    tax_percent: float | None = None
    reorder_level: int | None = None
    safety_stock: int | None = None
    maximum_stock: int | None = None
    lead_time: int | None = None
    status: str | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    barcode: str | None
    name: str
    description: str | None
    category_id: int
    brand_id: int
    unit_id: int
    selling_price: float
    purchase_price: float
    tax_percent: float
    reorder_level: int
    safety_stock: int
    maximum_stock: int
    lead_time: int
    status: str
    created_at: datetime
