from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SalesReturnCreate(BaseModel):
    sale_id: int
    return_date: datetime
    status: str = "REQUESTED"
    reason: str | None = None


class SalesReturnUpdate(BaseModel):
    status: str | None = None
    reason: str | None = None


class SalesReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sale_id: int
    return_date: datetime
    status: str
    reason: str | None
