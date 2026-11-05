
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def create_category(data: CategoryCreate, db: Session):
    category = Category(
        name=data.name,
        description=data.description
    )

    db.add(category)
    db.flush()

    return category


def get_categories(db: Session):
    return db.query(Category).all()


def get_category_by_id(category_id: int, db: Session):
    category = db.query(Category).filter(
        Category.id == category_id
    ).first()

    if category is None:
        raise ValueError("Category not found")

    return category


def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Session
):
    category = get_category_by_id(category_id, db)

    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "description":
            setattr(category, "description", value)
        else:
            setattr(category, field, value)

    db.flush()
    return category


def delete_category(category_id: int, db: Session):
    category = get_category_by_id(category_id, db)

    db.delete(category)
    db.flush()

    return True
