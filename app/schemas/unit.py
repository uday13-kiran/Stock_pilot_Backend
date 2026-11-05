from pydantic import BaseModel, ConfigDict


class UnitCreate(BaseModel):
    name: str
    description: str | None = None


class UnitUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class UnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
