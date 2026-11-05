from pydantic import BaseModel, ConfigDict, Field


class PurchaseOrderItemCreate(BaseModel):
    purchase_order_id: int
    product_id: int
    quantity: int = Field(gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    total_price: float | None = Field(default=None, ge=0)


class PurchaseOrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    purchase_order_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
