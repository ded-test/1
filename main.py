from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import uvicorn
import logging

from .database import get_db, engine
from .models import Base, Building, Category, Company
from .routers import buildings, categories, companies, test_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create all tables
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title="Catalog API",
    description="REST API для справочника компаний, зданий и рубрик",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(buildings.router)
app.include_router(categories.router)
app.include_router(companies.router)
app.include_router(test_data.router)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API health check"""
    return {
        "message": "Catalog API Service",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


# Statistics endpoint
@app.get("/stats/", tags=["Statistics"])
async def get_statistics(db: Session = Depends(get_db)):
    """Получить статистику по системе"""
    stats = {
        "buildings": db.query(Building).count(),
        "categories": db.query(Category).count(),
        "companies": {
            "total": db.query(Company).count(),
            "active": db.query(Company).filter(Company.is_active == 1).count(),
            "inactive": db.query(Company).filter(Company.is_active == 0).count(),
        },
    }
    return stats


# Health check endpoint
@app.get("/health/", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """Проверка состояния API и базы данных"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
