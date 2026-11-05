from app.routes.crud_factory import build_crud_router
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogResponse

router = build_crud_router(
    prefix="/audit-logs", tag="Audit Logs", model=AuditLog,
    create_schema=AuditLogCreate, response_schema=AuditLogResponse, 
    allow_delete=False, immutable=True, field_aliases={},
    read_roles=("admin",), write_roles=("admin",),
)
