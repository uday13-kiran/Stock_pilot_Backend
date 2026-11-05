from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services import product_service

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductCreate, db: Session = Depends(get_db), _admin = Depends(require_roles("admin"))):
    try:
        item = product_service.create_product(data, db)
        db.commit(); db.refresh(item)
        return item
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Product conflicts with an existing record") from exc

@router.get("/", response_model=list[ProductResponse])
def list_products(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200), db: Session = Depends(get_db)):
    return product_service.list_products(db, skip, limit)

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    try: return product_service.get_product(product_id, db)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db), _admin = Depends(require_roles("admin"))):
    try:
        item = product_service.update_product(data, db, product_id)
        db.commit(); db.refresh(item)
        return item
    except ValueError as exc:
        db.rollback()
        code = 404 if str(exc) == "Product not found" else 409
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="Product conflicts with an existing record") from exc

@router.delete("/{product_id}", response_model=ProductResponse)
def deactivate_product(product_id: int, db: Session = Depends(get_db), _admin = Depends(require_roles("admin"))):
    try:
        item = product_service.deactivate_product(product_id, db)
        db.commit(); db.refresh(item)
        return item
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc
