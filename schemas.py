from pydantic import BaseModel, Field, validator
from typing import List, Optional
from datetime import datetime


# Building schemas
class BuildingBase(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class BuildingCreate(BuildingBase):
    pass


class BuildingUpdate(BaseModel):
    address: Optional[str] = Field(None, min_length=1, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class BuildingResponse(BuildingBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Category schemas
class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[int] = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    parent_id: Optional[int] = None


class CategoryResponse(CategoryBase):
    id: int
    level: int
    path: Optional[str]
    created_at: datetime
    updated_at: datetime
    children: Optional[List["CategoryResponse"]] = None

    class Config:
        from_attributes = True


# Company schemas
class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    phones: List[str] = Field(..., min_items=1)
    description: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    building_id: int
    category_ids: List[int] = Field(..., min_items=1)
    is_active: bool = True

    @validator("phones")
    def validate_phones(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one phone number is required")
        return v

    @validator("email")
    def validate_email(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email format")
        return v


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    phones: Optional[List[str]] = None
    description: Optional[str] = None
    website: Optional[str] = None
    email: Optional[str] = None
    building_id: Optional[int] = None
    category_ids: Optional[List[int]] = None
    is_active: Optional[bool] = None


class CompanyResponse(BaseModel):
    id: int
    name: str
    phones: List[str]
    description: Optional[str]
    website: Optional[str]
    email: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    building: BuildingResponse
    categories: List[CategoryResponse]

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    id: int
    name: str
    phones: List[str]
    is_active: bool
    building: BuildingResponse
    categories: List[CategoryResponse]

    class Config:
        from_attributes = True
