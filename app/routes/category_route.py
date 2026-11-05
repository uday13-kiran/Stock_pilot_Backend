from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import require_roles
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import category_services

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_roles("admin"))
):
    try:
        item = category_services.create_category(data, db)
        db.commit()
        db.refresh(item)
        return item

    except IntegrityError as exc:
        db.rollback()
        print("ACTUAL DATABASE ERROR:", repr(exc.orig))

        raise HTTPException(
            status_code=409,
            detail="Database constraint violation"
        ) from exc

@router.get("/", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return category_services.get_categories(db)

@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: Session = Depends(get_db)):
    try: return category_services.get_category_by_id(category_id, db)
    except ValueError as exc: raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(category_id: int, data: CategoryUpdate, db: Session = Depends(get_db), _admin = Depends(require_roles("admin"))):
    try:
        item = category_services.update_category(category_id, data, db)
        db.commit(); db.refresh(item)
        return item
    except ValueError as exc: db.rollback(); raise HTTPException(status_code=404, detail=str(exc)) from exc

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db), _admin = Depends(require_roles("admin"))):
    try:
        category_services.delete_category(category_id, db); db.commit()
    except ValueError as exc: db.rollback(); raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="Category is in use and cannot be deleted") from exc
