from fastapi import APIRouter, HTTPException, Depends, Query, Path
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_
from typing import List, Optional

from ..database import get_db
from ..models import Building, Company, Category
from ..schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyListResponse,
)
from ..utils import get_all_child_category_ids, calculate_distance_haversine

router = APIRouter(prefix="/companies", tags=["Companies"])


@router.post("/", response_model=CompanyResponse)
async def create_company(company: CompanyCreate, db: Session = Depends(get_db)):
    """Создать новую компанию"""
    # Validate building exists
    building = db.query(Building).filter(Building.id == company.building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    # Validate categories exist
    categories = db.query(Category).filter(Category.id.in_(company.category_ids)).all()
    if len(categories) != len(company.category_ids):
        missing_ids = set(company.category_ids) - {cat.id for cat in categories}
        raise HTTPException(
            status_code=404, detail=f"Categories not found: {list(missing_ids)}"
        )

    # Create company
    db_company = Company(
        name=company.name,
        phones=",".join(company.phones),
        description=company.description,
        website=company.website,
        email=company.email,
        building_id=company.building_id,
        is_active=1 if company.is_active else 0,
    )
    db_company.categories = categories

    db.add(db_company)
    db.commit()
    db.refresh(db_company)

    # Convert phones for response
    db_company.phones = db_company.phones.split(",")
    db_company.is_active = bool(db_company.is_active)

    return db_company


@router.get("/", response_model=List[CompanyListResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    active_only: bool = Query(True, description="Return only active companies"),
    db: Session = Depends(get_db),
):
    """Получить список компаний с пагинацией"""
    query = db.query(Company)

    if active_only:
        query = query.filter(Company.is_active == 1)

    companies = query.offset(skip).limit(limit).all()

    # Convert phones for response
    for company in companies:
        company.phones = company.phones.split(",") if company.phones else []
        company.is_active = bool(company.is_active)

    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    """Получить подробную информацию об организации по её идентификатору"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Convert phones for response
    company.phones = company.phones.split(",") if company.phones else []
    company.is_active = bool(company.is_active)

    return company


@router.get("/building/{building_id}", response_model=List[CompanyListResponse])
async def get_companies_by_building(
    building_id: int = Path(..., gt=0),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Получить все организации, находящиеся в конкретном здании"""
    building = db.query(Building).filter(Building.id == building_id).first()
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    query = db.query(Company).filter(Company.building_id == building_id)
    if active_only:
        query = query.filter(Company.is_active == 1)

    companies = query.all()

    # Convert phones for response
    for company in companies:
        company.phones = company.phones.split(",") if company.phones else []
        company.is_active = bool(company.is_active)

    return companies


@router.get("/category/{category_id}", response_model=List[CompanyListResponse])
async def get_companies_by_category(
    category_id: int = Path(..., gt=0),
    include_subcategories: bool = Query(
        True, description="Include companies from subcategories"
    ),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Получить список всех организаций, которые относятся к указанной рубрике"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if include_subcategories:
        # Get all child categories recursively
        category_ids = get_all_child_category_ids(db, category_id)
        query = (
            db.query(Company)
            .join(Company.categories)
            .filter(Category.id.in_(category_ids))
        )
    else:
        query = (
            db.query(Company)
            .join(Company.categories)
            .filter(Category.id == category_id)
        )

    if active_only:
        query = query.filter(Company.is_active == 1)

    companies = query.distinct().all()

    # Convert phones for response
    for company in companies:
        company.phones = company.phones.split(",") if company.phones else []
        company.is_active = bool(company.is_active)

    return companies


@router.get("/search/", response_model=List[CompanyListResponse])
async def search_companies_by_name(
    q: str = Query(..., min_length=1, description="Search query for company name"),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Поиск организаций по названию"""
    query = db.query(Company).filter(Company.name.contains(q))

    if active_only:
        query = query.filter(Company.is_active == 1)

    companies = query.all()

    # Convert phones for response
    for company in companies:
        company.phones = company.phones.split(",") if company.phones else []
        company.is_active = bool(company.is_active)

    return companies


@router.get("/location/", response_model=List[CompanyListResponse])
async def get_companies_by_location(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: Optional[float] = Query(
        None, gt=0, description="Search radius in kilometers"
    ),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lng: Optional[float] = Query(None, ge=-180, le=180),
    max_lng: Optional[float] = Query(None, ge=-180, le=180),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Получить список организаций в заданном радиусе или прямоугольной области
    относительно указанной точки на карте
    """

    base_query = db.query(Company).join(Building)

    if active_only:
        base_query = base_query.filter(Company.is_active == 1)

    if radius_km is not None:
        # Circular search using Haversine formula
        companies = base_query.all()
        filtered_companies = []

        for company in companies:
            distance = calculate_distance_haversine(
                latitude,
                longitude,
                company.building.latitude,
                company.building.longitude,
            )
            if distance <= radius_km:
                filtered_companies.append(company)

        companies = filtered_companies

    elif all(coord is not None for coord in [min_lat, max_lat, min_lng, max_lng]):
        # Rectangle search
        if min_lat >= max_lat or min_lng >= max_lng:
            raise HTTPException(status_code=400, detail="Invalid rectangle coordinates")

        companies = base_query.filter(
            and_(
                Building.latitude >= min_lat,
                Building.latitude <= max_lat,
                Building.longitude >= min_lng,
                Building.longitude <= max_lng,
            )
        ).all()

    else:
        raise HTTPException(
            status_code=400,
            detail="Either radius_km or all rectangle coordinates (min_lat, max_lat, min_lng, max_lng) must be provided",
        )

    # Convert phones for response
    for company in companies:
        company.phones = company.phones.split(",") if company.phones else []
        company.is_active = bool(company.is_active)

    return companies


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int = Path(..., gt=0),
    company_update: CompanyUpdate = None,
    db: Session = Depends(get_db),
):
    """Обновить информацию о компании"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = company_update.dict(exclude_unset=True)

    # Handle category updates
    if "category_ids" in update_data:
        category_ids = update_data.pop("category_ids")
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        if len(categories) != len(category_ids):
            missing_ids = set(category_ids) - {cat.id for cat in categories}
            raise HTTPException(
                status_code=404, detail=f"Categories not found: {list(missing_ids)}"
            )
        db_company.categories = categories

    # Handle phones update
    if "phones" in update_data:
        phones = update_data.pop("phones")
        update_data["phones"] = ",".join(phones)

    # Handle is_active conversion
    if "is_active" in update_data:
        update_data["is_active"] = 1 if update_data["is_active"] else 0

    # Update other fields
    for field, value in update_data.items():
        setattr(db_company, field, value)

    db.commit()
    db.refresh(db_company)

    # Convert for response
    db_company.phones = db_company.phones.split(",") if db_company.phones else []
    db_company.is_active = bool(db_company.is_active)

    return db_company


@router.delete("/{company_id}")
async def delete_company(
    company_id: int = Path(..., gt=0), db: Session = Depends(get_db)
):
    """Удалить компанию"""
    db_company = db.query(Company).filter(Company.id == company_id).first()
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(db_company)
    db.commit()
    return {"message": "Company deleted successfully"}
