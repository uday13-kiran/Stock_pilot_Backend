from app.routes.crud_factory import build_crud_router
from app.models.goods_receipt import GoodsReceipt
from app.schemas.goods_receipt import GoodsReceiptCreate, GoodsReceiptResponse, GoodsReceiptUpdate

router = build_crud_router(
    prefix="/goods-receipts", tag="Goods Receipts", model=GoodsReceipt,
    create_schema=GoodsReceiptCreate, response_schema=GoodsReceiptResponse, update_schema=GoodsReceiptUpdate,
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("purchase_manager", "inventory_manager", "warehouse_staff"), write_roles=("purchase_manager", "inventory_manager", "warehouse_staff"),
)
