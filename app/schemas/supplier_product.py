from pydantic import BaseModel, ConfigDict


class SupplierProductCreate(BaseModel):
    supplier_id: int
    product_id: int
    supplier_price: float | None = None


class SupplierProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    product_id: int
    supplier_price: float | None
