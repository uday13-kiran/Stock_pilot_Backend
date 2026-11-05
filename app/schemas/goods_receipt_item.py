from pydantic import BaseModel, ConfigDict


class GoodsReceiptItemCreate(BaseModel):
    goods_receipt_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float


class GoodsReceiptItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goods_receipt_id: int
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
