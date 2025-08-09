from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Category
from ..schemas import CategoryCreate, CategoryResponse
from ..utils import update_category_path

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/", response_model=CategoryResponse)
async def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Создать новую рубрику"""
    if category.parent_id:
        parent = db.query(Category).filter(Category.id == category.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")

    db_category = Category(name=category.name, parent_id=category.parent_id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)

    # Update path after commit to get the ID
    update_category_path(db, db_category)
    db.commit()
    db.refresh(db_category)

    return db_category


@router.get("/", response_model=List[CategoryResponse])
async def list_categories(
    flat: bool = Query(False, description="Return flat list instead of tree structure"),
    db: Session = Depends(get_db),
):
    """Получить рубрикатор каталога"""
    if flat:
        # Return flat list of all categories
        categories = db.query(Category).order_by(Category.level, Category.name).all()
        return categories

    # Return hierarchical structure (root categories with children)
    root_categories = (
        db.query(Category)
        .filter(Category.parent_id.is_(None))
        .order_by(Category.name)
        .all()
    )

    def populate_children(category):
        children = (
            db.query(Category)
            .filter(Category.parent_id == category.id)
            .order_by(Category.name)
            .all()
        )
        for child in children:
            populate_children(child)
        category.children = children
        return category

    return [populate_children(cat) for cat in root_categories]


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int = Path(..., gt=0), db: Session = Depends(get_db)
):
    """Получить информацию о рубрике"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Load children
    children = (
        db.query(Category)
        .filter(Category.parent_id == category.id)
        .order_by(Category.name)
        .all()
    )
    category.children = children

    return category
