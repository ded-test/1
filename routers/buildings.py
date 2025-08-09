from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import Building, Company
from ..schemas import BuildingCreate, BuildingUpdate, BuildingResponse

router = APIRouter(prefix="/buildings", tags=["Buildings"])


@router.post("/", response_model=BuildingResponse)
async def create_building(building: BuildingCreate, db: Session = Depends(get_db)):
    """Создать новое здание"""
    db_building = Building(**building.dict())
    db.add(db_building)
    db.commit()
    db.refresh(db_building)
    return db_building


@router.get("/", response_model=List[BuildingResponse])
async def list_buildings(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Получить список всех зданий с пагинацией"""
    buildings = db.query(Building).offset(skip).limit(limit).all()
    return buildings


@router.get("/{building_id}", response_model=BuildingResponse)
async def get_building(
    building_id: int = Path(..., gt=0), db: Session = Depends(get_db)
):
    """Получить информацию о конкретном здании"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")
    return building


@router.put("/{building_id}", response_model=BuildingResponse)
async def update_building(
    building_id: int = Path(..., gt=0),
    building_update: BuildingUpdate = None,
    db: Session = Depends(get_db),
):
    """Обновить информацию о здании"""
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        raise HTTPException(status_code=404, detail="Building not found")

    update_data = building_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_building, field, value)

    db.commit()
    db.refresh(db_building)
    return db_building


@router.delete("/{building_id}")
async def delete_building(
    building_id: int = Path(..., gt=0), db: Session = Depends(get_db)
):
    """Удалить здание"""
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Check if building has companies
    companies_count = (
        db.query(Company).filter(Company.building_id == building_id).count()
    )
    if companies_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete building. {companies_count} companies are associated with it.",
        )

    db.delete(db_building)
    db.commit()
    return {"message": "Building deleted successfully"}
