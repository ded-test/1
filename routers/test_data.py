from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..models import Building, Category, Company, company_category_association

router = APIRouter(prefix="/test-data", tags=["Test Data"])

# Configure logging
logger = logging.getLogger(__name__)


@router.post("/generate")
async def generate_test_data(db: Session = Depends(get_db)):
    """Генерация тестовых данных для демонстрации API"""
    try:
        # Clear existing data in proper order due to foreign key constraints
        db.execute(company_category_association.delete())
        db.query(Company).delete()
        db.query(Category).delete()
        db.query(Building).delete()
        db.commit()

        # Create test buildings
        buildings_data = [
            {
                "address": "ул. Блюхера, 32/1",
                "latitude": 55.751244,
                "longitude": 37.618423,
            },
            {
                "address": "ул. Ленина, 15",
                "latitude": 55.752244,
                "longitude": 37.619423,
            },
            {"address": "пр. Мира, 100", "latitude": 55.753244, "longitude": 37.620423},
            {"address": "ул. Арбат, 25", "latitude": 55.750244, "longitude": 37.617423},
            {
                "address": "Тверская ул., 12",
                "latitude": 55.754244,
                "longitude": 37.621423,
            },
        ]

        buildings = []
        for building_data in buildings_data:
            building = Building(**building_data)
            db.add(building)
            buildings.append(building)
        db.commit()

        # Create category hierarchy
        # Root categories
        food_cat = Category(name="Еда", level=0, path="1")
        auto_cat = Category(name="Автомобили", level=0, path="2")
        sport_cat = Category(name="Спорт", level=0, path="3")

        db.add_all([food_cat, auto_cat, sport_cat])
        db.commit()

        # Update paths with real IDs
        food_cat.path = str(food_cat.id)
        auto_cat.path = str(auto_cat.id)
        sport_cat.path = str(sport_cat.id)

        # Food subcategories
        meat_cat = Category(name="Мясная продукция", parent_id=food_cat.id, level=1)
        semifinished_cat = Category(
            name="Полуфабрикаты оптом", parent_id=food_cat.id, level=1
        )
        vegetables_cat = Category(name="Овощи", parent_id=food_cat.id, level=1)

        db.add_all([meat_cat, semifinished_cat, vegetables_cat])
        db.commit()

        # Update paths
        meat_cat.path = f"{food_cat.id}/{meat_cat.id}"
        semifinished_cat.path = f"{food_cat.id}/{semifinished_cat.id}"
        vegetables_cat.path = f"{food_cat.id}/{vegetables_cat.id}"

        # Auto subcategories
        truck_cat = Category(name="Грузовые", parent_id=auto_cat.id, level=1)
        car_cat = Category(name="Легковые", parent_id=auto_cat.id, level=1)
        parts_cat = Category(name="Запчасти", parent_id=auto_cat.id, level=1)

        db.add_all([truck_cat, car_cat, parts_cat])
        db.commit()

        # Update paths
        truck_cat.path = f"{auto_cat.id}/{truck_cat.id}"
        car_cat.path = f"{auto_cat.id}/{car_cat.id}"
        parts_cat.path = f"{auto_cat.id}/{parts_cat.id}"

        # Parts subcategories
        suspension_cat = Category(
            name="Запчасти для подвески", parent_id=parts_cat.id, level=2
        )
        tires_cat = Category(name="Шины/Диски", parent_id=parts_cat.id, level=2)

        db.add_all([suspension_cat, tires_cat])
        db.commit()

        # Update paths
        suspension_cat.path = f"{auto_cat.id}/{parts_cat.id}/{suspension_cat.id}"
        tires_cat.path = f"{auto_cat.id}/{parts_cat.id}/{tires_cat.id}"

        db.commit()

        # Create test companies
        companies_data = [
            {
                "name": 'ООО "Рога и Копыта"',
                "phones": "2-222-222,3-333-333,8-923-666-13-13",
                "description": "Мясоперерабатывающее предприятие",
                "website": "https://roga-kopyta.ru",
                "email": "info@roga-kopyta.ru",
                "building_id": buildings[0].id,
                "categories": [meat_cat, semifinished_cat],
            },
            {
                "name": 'Автосалон "Премиум"',
                "phones": "8-800-555-35-35,495-123-45-67",
                "description": "Продажа легковых автомобилей премиум класса",
                "website": "https://premium-auto.ru",
                "email": "sales@premium-auto.ru",
                "building_id": buildings[1].id,
                "categories": [car_cat],
            },
            {
                "name": 'Грузоперевозки "Быстро"',
                "phones": "8-912-345-67-89",
                "description": "Грузоперевозки по всей России",
                "website": "https://bistro-gruz.ru",
                "email": "order@bistro-gruz.ru",
                "building_id": buildings[2].id,
                "categories": [truck_cat],
            },
            {
                "name": 'Шинный центр "Колесо"',
                "phones": "8-495-111-22-33,8-495-444-55-66",
                "description": "Продажа и установка шин и дисков",
                "website": "https://koleso-center.ru",
                "email": "info@koleso-center.ru",
                "building_id": buildings[3].id,
                "categories": [tires_cat],
            },
            {
                "name": 'Фермерские продукты "Эко"',
                "phones": "8-916-777-88-99",
                "description": "Натуральные овощи и фрукты",
                "website": "https://eco-farm.ru",
                "email": "contact@eco-farm.ru",
                "building_id": buildings[4].id,
                "categories": [vegetables_cat],
            },
            {
                "name": 'Автозапчасти "Подвеска+"',
                "phones": "8-499-123-45-67",
                "description": "Специализированный магазин запчастей для подвески",
                "building_id": buildings[0].id,
                "categories": [suspension_cat],
            },
        ]

        for company_data in companies_data:
            categories = company_data.pop("categories")
            company = Company(**company_data)
            company.categories = categories
            db.add(company)

        db.commit()

        # Count created records
        buildings_count = db.query(Building).count()
        categories_count = db.query(Category).count()
        companies_count = db.query(Company).count()

        return {
            "message": "Test data generated successfully",
            "created": {
                "buildings": buildings_count,
                "categories": categories_count,
                "companies": companies_count,
            },
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error generating test data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error generating test data: {str(e)}"
        )
