from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.db.models import ProductCatalog, ProductPrice, ProductWeight, ProductCategory, Inventory
from backend.app.schemas.product import ProductCreate, ProductUpdate, ProductOut

router = APIRouter()

@router.get("", response_model=List[ProductOut])
def get_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ProductCatalog).filter(ProductCatalog.is_active == True)
    if category:
        query = query.join(ProductCategory).filter(ProductCategory.code == category.upper())
    if search:
        query = query.filter(ProductCatalog.name.ilike(f"%{search}%") | ProductCatalog.sku.ilike(f"%{search}%"))

    products = query.all()
    results = []
    for p in products:
        price_rec = next((pr for pr in p.price_records if pr.is_current), None)
        base_price = price_rec.base_price if price_rec else 0.0
        exp_w = p.weight_record.expected_weight_grams if p.weight_record else 100.0
        tol_w = p.weight_record.weight_tolerance_grams if p.weight_record else 10.0
        cat_name = p.category.name if p.category else "General"
        results.append(ProductOut(
            id=p.id,
            sku=p.sku,
            name=p.name,
            brand=p.brand,
            category_name=cat_name,
            barcode=p.barcode,
            description=p.description,
            image_url=p.image_url,
            base_price=base_price,
            expected_weight_grams=exp_w,
            weight_tolerance_grams=tol_w,
            is_active=p.is_active
        ))
    return results

@router.get("/{sku}", response_model=ProductOut)
def get_product_by_sku(sku: str, db: Session = Depends(get_db)):
    p = db.query(ProductCatalog).filter(ProductCatalog.sku == sku).first()
    if not p:
        raise HTTPException(status_code=404, detail=f"Product SKU {sku} not found")
    price_rec = next((pr for pr in p.price_records if pr.is_current), None)
    base_price = price_rec.base_price if price_rec else 0.0
    exp_w = p.weight_record.expected_weight_grams if p.weight_record else 100.0
    tol_w = p.weight_record.weight_tolerance_grams if p.weight_record else 10.0
    cat_name = p.category.name if p.category else "General"
    return ProductOut(
        id=p.id,
        sku=p.sku,
        name=p.name,
        brand=p.brand,
        category_name=cat_name,
        barcode=p.barcode,
        description=p.description,
        image_url=p.image_url,
        base_price=base_price,
        expected_weight_grams=exp_w,
        weight_tolerance_grams=tol_w,
        is_active=p.is_active
    )

@router.post("", response_model=ProductOut)
def create_product(product_in: ProductCreate, db: Session = Depends(get_db)):
    existing = db.query(ProductCatalog).filter(ProductCatalog.sku == product_in.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU {product_in.sku} already exists")

    prod = ProductCatalog(
        sku=product_in.sku,
        name=product_in.name,
        brand=product_in.brand,
        category_id=product_in.category_id,
        barcode=product_in.barcode,
        description=product_in.description,
        image_url=product_in.image_url,
        is_active=True
    )
    db.add(prod)
    db.flush()

    price = ProductPrice(product_id=prod.id, store_id=1, base_price=product_in.base_price, is_current=True)
    weight = ProductWeight(product_id=prod.id, expected_weight_grams=product_in.expected_weight_grams, weight_tolerance_grams=product_in.weight_tolerance_grams)
    inv = Inventory(product_id=prod.id, store_id=1, current_stock=product_in.initial_stock)
    db.add_all([price, weight, inv])
    db.commit()
    db.refresh(prod)

    return ProductOut(
        id=prod.id,
        sku=prod.sku,
        name=prod.name,
        brand=prod.brand,
        category_name=prod.category.name if prod.category else "General",
        barcode=prod.barcode,
        description=prod.description,
        image_url=prod.image_url,
        base_price=product_in.base_price,
        expected_weight_grams=product_in.expected_weight_grams,
        weight_tolerance_grams=product_in.weight_tolerance_grams,
        is_active=prod.is_active
    )

@router.put("/{sku}", response_model=ProductOut)
def update_product(sku: str, update_in: ProductUpdate, db: Session = Depends(get_db)):
    prod = db.query(ProductCatalog).filter(ProductCatalog.sku == sku).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")

    if update_in.name is not None:
        prod.name = update_in.name
    if update_in.brand is not None:
        prod.brand = update_in.brand
    if update_in.is_active is not None:
        prod.is_active = update_in.is_active

    if update_in.base_price is not None:
        curr_price = next((pr for pr in prod.price_records if pr.is_current), None)
        if curr_price:
            curr_price.base_price = update_in.base_price

    if update_in.expected_weight_grams is not None and prod.weight_record:
        prod.weight_record.expected_weight_grams = update_in.expected_weight_grams
    if update_in.weight_tolerance_grams is not None and prod.weight_record:
        prod.weight_record.weight_tolerance_grams = update_in.weight_tolerance_grams

    db.commit()
    db.refresh(prod)
    return get_product_by_sku(sku, db)
