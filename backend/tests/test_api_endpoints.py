import pytest
from fastapi.testclient import TestClient

def test_api_products(client: TestClient):
    res = client.get("/api/products")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 5
    skus = [p["sku"] for p in data]
    assert "TW-MILK-001" in skus

def test_api_trolley_lifecycle(client: TestClient):
    # Register trolley
    reg_res = client.post("/api/trolley/register", json={
        "device_uuid": "TROLLEY-TEST-01",
        "store_code": "TW-STORE-001",
        "ip_address": "192.168.1.150"
    })
    assert reg_res.status_code == 200
    assert reg_res.json()["status"] == "REGISTERED"

    # Ingest sensor telemetry
    sensor_res = client.post("/api/trolley/TROLLEY-TEST-01/sensor-data", json={
        "device_uuid": "TROLLEY-TEST-01",
        "raw_weight_grams": 450.0,
        "filtered_weight_grams": 450.0,
        "is_stable": True,
        "imu": {
            "accel_x": 0.01,
            "accel_y": 0.02,
            "accel_z": 9.81,
            "is_moving": False
        }
    })
    assert sensor_res.status_code == 200
    assert sensor_res.json()["status"] == "INGESTED"

    # Status check
    status_res = client.get("/api/trolley/TROLLEY-TEST-01/status")
    assert status_res.status_code == 200
    assert status_res.json()["current_weight"] == 450.0

def test_api_shopping_session_and_billing(client: TestClient):
    # Start session
    sess_res = client.post("/api/sessions", json={
        "trolley_uuid": "TROLLEY-01",
        "store_code": "TW-STORE-001",
        "budget_limit": 500.0
    })
    assert sess_res.status_code == 200
    sess_id = sess_res.json()["id"]

    # Evaluate verified insertion via API
    eval_res = client.post("/api/verification/evaluate", json={
        "session_id": sess_id,
        "visual_event": {
            "sku": "TW-BREAD-002",
            "confidence": 0.94,
            "direction": "INWARD",
            "frames_tracked": 3
        },
        "sensor_reading_pre": {"filtered_weight_grams": 0.0, "is_stable": True},
        "sensor_reading_post": {
            "filtered_weight_grams": 405.0,
            "is_stable": True,
            "imu": {"is_moving": False}
        }
    })
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert eval_data["evaluation"]["event_type"] == "VERIFIED_INSERTION"
    assert eval_data["cart_updated"] is True

    # Check cart
    cart_res = client.get(f"/api/sessions/{sess_id}/cart")
    assert cart_res.status_code == 200
    cart_data = cart_res.json()
    assert cart_data["items_count"] == 1
    assert cart_data["subtotal"] == "30.00"

    # Checkout
    chk_res = client.post(f"/api/billing/{sess_id}/checkout", json={"payment_method": "UPI"})
    assert chk_res.status_code == 200
    order_data = chk_res.json()
    assert "upi_intent_url" in order_data
    assert order_data["amount"] == cart_data["final_amount"]

def test_api_retailer_endpoints(client: TestClient):
    dash_res = client.get("/api/retailer/dashboard-stats")
    assert dash_res.status_code == 200
    assert "total_revenue" in dash_res.json()

    inv_res = client.get("/api/inventory")
    assert inv_res.status_code == 200
    assert len(inv_res.json()) >= 5
