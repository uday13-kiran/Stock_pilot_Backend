from app.routes.crud_factory import build_crud_router
from app.models.goods_receipt_item import GoodsReceiptItem
from app.schemas.goods_receipt_item import GoodsReceiptItemCreate, GoodsReceiptItemResponse

router = build_crud_router(
    prefix="/goods-receipt-items", tag="Goods Receipt Items", model=GoodsReceiptItem,
    create_schema=GoodsReceiptItemCreate, response_schema=GoodsReceiptItemResponse, 
    allow_delete=False, immutable=False, field_aliases={},
    read_roles=("purchase_manager", "inventory_manager", "warehouse_staff"), write_roles=("purchase_manager", "inventory_manager", "warehouse_staff"),
)
