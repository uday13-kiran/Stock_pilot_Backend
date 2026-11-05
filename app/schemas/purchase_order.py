from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.purchase_order_item import PurchaseOrderItemResponse


class PurchaseOrderWorkflowLine(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)


class PurchaseOrderWorkflowCreate(BaseModel):
    supplier_id: int = Field(gt=0)
    warehouse_id: int = Field(gt=0)
    items: list[PurchaseOrderWorkflowLine] = Field(min_length=1)
    expected_delivery_date: datetime | None = None
    notes: str | None = Field(default=None, max_length=500)


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    warehouse_id: int | None = None
    user_id: int
    order_date: datetime
    expected_delivery_date: datetime | None = None
    status: Literal["DRAFT"] = "DRAFT"
    total_amount: float = 0
    notes: str | None = None


class PurchaseOrderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    warehouse_id: int | None = None
    expected_delivery_date: datetime | None = None
    total_amount: float | None = None
    notes: str | None = None


class PurchaseOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    warehouse_id: int | None = None
    user_id: int
    order_date: datetime
    expected_delivery_date: datetime | None
    status: str
    total_amount: float
    notes: str | None


class PurchaseOrderWorkflowResponse(PurchaseOrderResponse):
    items: list[PurchaseOrderItemResponse]
