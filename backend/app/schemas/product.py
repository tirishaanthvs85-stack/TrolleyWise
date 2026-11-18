from typing import Optional
from decimal import Decimal
from pydantic import BaseModel

class ProductCreate(BaseModel):
    sku: str
    name: str
    brand: str = "General"
    category_id: int
    barcode: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = ""
    base_price: Decimal
    expected_weight_grams: float
    weight_tolerance_grams: float = 15.0
    initial_stock: int = 50

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand: Optional[str] = None
    base_price: Optional[Decimal] = None
    expected_weight_grams: Optional[float] = None
    weight_tolerance_grams: Optional[float] = None
    is_active: Optional[bool] = None

class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    brand: str
    category_name: str
    barcode: Optional[str]
    description: Optional[str]
    image_url: Optional[str]
    base_price: Decimal
    expected_weight_grams: float
    weight_tolerance_grams: float
    is_active: bool

    class Config:
        from_attributes = True
