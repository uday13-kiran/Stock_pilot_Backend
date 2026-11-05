from pydantic import BaseModel, ConfigDict


class BrandCreate(BaseModel):
    name: str
    description: str | None = None


class BrandUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class BrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
