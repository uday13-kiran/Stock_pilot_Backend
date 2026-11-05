from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    user_id: int
    action: str
    entity_type: str
    entity_id: int | None = None
    details: str | None = None


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    action: str
    entity_type: str
    entity_id: int | None
    timestamp: datetime
    details: str | None
