from pydantic import BaseModel, ConfigDict


class ReorderRuleCreate(BaseModel):
    product_id: int
    warehouse_id: int
    reorder_level: int
    safety_stock: int
    maximum_stock: int


class ReorderRuleUpdate(BaseModel):
    reorder_level: int | None = None
    safety_stock: int | None = None
    maximum_stock: int | None = None


class ReorderRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    warehouse_id: int
    reorder_level: int
    safety_stock: int
    maximum_stock: int
