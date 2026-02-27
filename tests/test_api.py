import sys
import os
import pytest
from fastapi.testclient import TestClient

# ensure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from main import app, storage

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_storage():
    storage.clear()
    yield

def test_post_and_get_device_list():
    res = client.post("/sensors", json={
        "device_id": "dev1",
        "timestamp_ms": 1000,
        "temperature_c": 20.0,
        "temperature_f": 68.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1000.0,
        "altitude_m": 10.0
    }, headers={"x-client-secret": "mysecret"})
    assert res.status_code == 200
    assert "id" in res.json()

    res2 = client.get("/devices")
    assert res2.status_code == 200
    assert res2.json() == ["dev1"]

def test_get_values_filters_and_limit():
    # insert multiple records
    for ts in [100, 200, 300, 400]:
        client.post("/sensors", json={
            "device_id": "dev2",
            "timestamp_ms": ts,
            "temperature_c": 20.0,
            "temperature_f": 68.0,
            "humidity_pct": 50.0,
            "pressure_hpa": 1000.0,
            "altitude_m": 10.0
        }, headers={"x-client-secret": "mysecret"})
    # retrieve all
    res_all = client.get("/devices/dev2/values")
    assert res_all.status_code == 200
    assert len(res_all.json()) == 4
    # start_ts filter
    res_start = client.get("/devices/dev2/values", params={"start_ts": 200})
    assert len(res_start.json()) == 3
    # end_ts filter
    res_end = client.get("/devices/dev2/values", params={"end_ts": 300})
    assert len(res_end.json()) == 3
    # limit
    res_lim = client.get("/devices/dev2/values", params={"limit": 2})
    assert len(res_lim.json()) == 2
    # zero and negative limits should return empty
    assert client.get("/devices/dev2/values", params={"limit": 0}).json() == []
    assert client.get("/devices/dev2/values", params={"limit": -5}).json() == []

def test_unauthorized():
    res = client.post("/sensors", json={
        "device_id": "dev1",
        "timestamp_ms": 1000,
        "temperature_c": 20.0,
        "temperature_f": 68.0,
        "humidity_pct": 50.0,
        "pressure_hpa": 1000.0,
        "altitude_m": 10.0
    }, headers={"x-client-secret": "wrong"})
    assert res.status_code == 401


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
