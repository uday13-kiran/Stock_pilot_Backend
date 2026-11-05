from pydantic import BaseModel, ConfigDict


class UserRoleCreate(BaseModel):
    user_id: int
    role_id: int


class UserRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    role_id: int
