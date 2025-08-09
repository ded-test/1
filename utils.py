import math
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy.sql import or_
from .models import Category


def update_category_path(db: Session, category: Category):
    """Update category path for hierarchical queries"""
    if category.parent_id:
        parent = db.query(Category).filter(Category.id == category.parent_id).first()
        if parent:
            category.path = (
                f"{parent.path}/{category.id}"
                if parent.path
                else f"{parent.id}/{category.id}"
            )
            category.level = parent.level + 1
    else:
        category.path = str(category.id)
        category.level = 0


def get_all_child_category_ids(db: Session, category_id: int) -> List[int]:
    """Recursively get all child category IDs"""
    result = [category_id]

    # Use path-based query for better performance
    category = db.query(Category).filter(Category.id == category_id).first()
    if category and category.path:
        # Find all categories whose path starts with this category's path
        children = (
            db.query(Category)
            .filter(
                or_(
                    Category.path.like(f"{category.path}/%"),
                    Category.path == category.path,
                )
            )
            .all()
        )
        result.extend([child.id for child in children if child.id != category_id])

    return result


def calculate_distance_haversine(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate the great circle distance between two points using Haversine formula"""
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in kilometers
    r = 6371
    return c * r
