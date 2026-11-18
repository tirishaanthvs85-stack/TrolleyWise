from decimal import Decimal
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.core.security import hash_password
from backend.app.db.models import (
    User, Customer, Retailer, Store, TrolleyDevice,
    ProductCategory, ProductCatalog, ProductPrice, ProductWeight,
    Inventory, Promotion, DiscountRule, LoyaltyAccount
)

def seed_database():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        # 1. Check if already seeded
        if db.query(ProductCatalog).first():
            print("Database already contains product catalogue.")
            return

        print("Seeding database with initial TrolleyWise configuration...")

        # 2. Users & Roles
        admin_user = User(
            username="admin",
            email="admin@trolleywise.io",
            hashed_password=hash_password("admin123"),
            role="ADMIN"
        )
        manager_user = User(
            username="manager",
            email="manager@trolleywise.io",
            hashed_password=hash_password("manager123"),
            role="STORE_MANAGER"
        )
        customer_user = User(
            username="john_doe",
            email="john@example.com",
            hashed_password=hash_password("customer123"),
            role="CUSTOMER"
        )
        db.add_all([admin_user, manager_user, customer_user])
        db.flush()

        # Customer Profile
        customer = Customer(
            user_id=customer_user.id,
            phone_number="+919876543210",
            full_name="John Doe",
            loyalty_member=True,
            preferences='{"budget_limit": 1000.0, "notify_discounts": true}'
        )
        db.add(customer)
        db.flush()

        loyalty = LoyaltyAccount(
            customer_id=customer.id,
            points_balance=150,
            tier="SILVER"
        )
        db.add(loyalty)

        # 3. Retailer & Store
        retailer = Retailer(
            name="TrolleyWise Retail Systems India Pvt Ltd",
            legal_name="TrolleyWise Retail Technologies Private Limited",
            tax_identifier="29AAAAA0000A1Z5",
            address="Level 4, Orion Tech Park, Electronic City, Bengaluru, Karnataka 560100",
            contact_email="contact@trolleywise.io"
        )
        db.add(retailer)
        db.flush()

        store = Store(
            retailer_id=retailer.id,
            store_code="TW-STORE-001",
            name="TrolleyWise Hypermarket - Bangalore Flagship",
            address="Plot 12, Outer Ring Road, Bellandur, Bengaluru, Karnataka 560103",
            currency="INR",
            tax_rate_default=0.18
        )
        db.add(store)
        db.flush()

        # 4. Trolley Devices
        trolley1 = TrolleyDevice(
            device_uuid="TROLLEY-01",
            store_id=store.id,
            mac_address="24:6F:28:AB:CD:10",
            ip_address="192.168.1.101",
            status="IDLE",
            firmware_version="v2.4.1",
            battery_level=98.5
        )
        trolley2 = TrolleyDevice(
            device_uuid="TROLLEY-02",
            store_id=store.id,
            mac_address="24:6F:28:AB:CD:12",
            ip_address="192.168.1.102",
            status="IDLE",
            firmware_version="v2.4.1",
            battery_level=94.0
        )
        db.add_all([trolley1, trolley2])

        # 5. Product Categories
        categories = {
            "DAIRY": ProductCategory(code="DAIRY", name="Dairy & Milk", hsn_code="0401", default_tax_pct=0.05),
            "BAKERY": ProductCategory(code="BAKERY", name="Bakery & Bread", hsn_code="1905", default_tax_pct=0.05),
            "GRAINS": ProductCategory(code="GRAINS", name="Rice & Staples", hsn_code="1006", default_tax_pct=0.05),
            "PERSONAL_CARE": ProductCategory(code="PERSONAL_CARE", name="Personal Care & Soaps", hsn_code="3401", default_tax_pct=0.18),
            "CONFECTIONERY": ProductCategory(code="CONFECTIONERY", name="Chocolates & Snacks", hsn_code="1806", default_tax_pct=0.18),
        }
        db.add_all(list(categories.values()))
        db.flush()

        # 6. Products Catalog, Weights, Prices, and Inventory
        # Preserving and mapping the 5 classes: 0: Milk, 1: Bread, 2: Rice, 3: Soap, 4: Chocolate
        products_data = [
            {
                "sku": "TW-MILK-001",
                "name": "Amul Taaza Fresh Toned Milk 500ml",
                "brand": "Amul",
                "category": categories["DAIRY"],
                "barcode": "8901262010053",
                "price": Decimal("45.00"),
                "weight_g": 515.0,
                "tolerance_g": 15.0,
                "stock": 100,
                "image": "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=300"
            },
            {
                "sku": "TW-BREAD-002",
                "name": "Britannia 100% Whole Wheat Bread 400g",
                "brand": "Britannia",
                "category": categories["BAKERY"],
                "barcode": "8901063142211",
                "price": Decimal("30.00"),
                "weight_g": 405.0,
                "tolerance_g": 15.0,
                "stock": 80,
                "image": "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=300"
            },
            {
                "sku": "TW-RICE-003",
                "name": "India Gate Feast Rozzana Basmati Rice 1kg",
                "brand": "India Gate",
                "category": categories["GRAINS"],
                "barcode": "8901725181121",
                "price": Decimal("65.00"),
                "weight_g": 1020.0,
                "tolerance_g": 25.0,
                "stock": 120,
                "image": "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=300"
            },
            {
                "sku": "TW-SOAP-004",
                "name": "Dettol Original Germ Protection Bathing Soap 125g",
                "brand": "Dettol",
                "category": categories["PERSONAL_CARE"],
                "barcode": "8901396112211",
                "price": Decimal("25.00"),
                "weight_g": 128.0,
                "tolerance_g": 8.0,
                "stock": 150,
                "image": "https://images.unsplash.com/photo-1607006314187-c7943f07a4a9?w=300"
            },
            {
                "sku": "TW-CHOC-005",
                "name": "Cadbury Dairy Milk Silk Chocolate Bar 50g",
                "brand": "Cadbury",
                "category": categories["CONFECTIONERY"],
                "barcode": "7622201732219",
                "price": Decimal("20.00"),
                "weight_g": 52.0,
                "tolerance_g": 5.0,
                "stock": 200,
                "image": "https://images.unsplash.com/photo-1549007994-cb92caebd54b?w=300"
            }
        ]

        for p in products_data:
            cat = p["category"]
            prod = ProductCatalog(
                sku=p["sku"],
                name=p["name"],
                brand=p["brand"],
                category_id=cat.id,
                barcode=p["barcode"],
                description=f"Authentic {p['brand']} {p['name']}. Store verified.",
                image_url=p["image"],
                is_active=True
            )
            db.add(prod)
            db.flush()

            # Price
            price = ProductPrice(
                product_id=prod.id,
                store_id=store.id,
                base_price=p["price"],
                currency="INR",
                is_current=True
            )
            db.add(price)

            # Weight
            weight = ProductWeight(
                product_id=prod.id,
                expected_weight_grams=p["weight_g"],
                weight_tolerance_grams=p["tolerance_g"]
            )
            db.add(weight)

            # Inventory
            inv = Inventory(
                product_id=prod.id,
                store_id=store.id,
                current_stock=p["stock"],
                reserved_stock=0,
                min_threshold=15
            )
            db.add(inv)

        # 7. Promotions & Discounts
        promo1 = Promotion(
            store_id=store.id,
            name="Weekend Smart Shopper - Flat 10% Off on Cart > Rs 100",
            promo_code="SMART10",
            promo_type="PERCENTAGE",
            value=10.0,
            is_active=True
        )
        db.add(promo1)
        db.flush()

        rule1 = DiscountRule(
            promo_id=promo1.id,
            min_cart_value=Decimal("100.00"),
            discount_pct=10.0,
            max_discount_amount=Decimal("50.00")
        )
        db.add(rule1)

        db.commit()
        print("Database initialized and seeded successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
