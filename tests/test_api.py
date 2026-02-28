import sys
import os
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

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
    # insert multiple records and capture the server-generated timestamps
    timestamps = []
    for _ in range(4):
        resp = client.post("/sensors", json={
            "device_id": "dev2",
            "timestamp_ms": 123,  # value will be ignored by server
            "temperature_c": 20.0,
            "temperature_f": 68.0,
            "humidity_pct": 50.0,
            "pressure_hpa": 1000.0,
            "altitude_m": 10.0
        }, headers={"x-client-secret": "mysecret"})
        assert resp.status_code == 200
        # grab the timestamp from storage directly
        timestamps.append(storage["dev2"][-1].timestamp_ms)
    # ensure we have increasing values
    assert sorted(timestamps) == timestamps
    # retrieve all
    res_all = client.get("/devices/dev2/values")
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert len(data_all) == 4
    # each record should include ISO AEST timestamp derived from timestamp_ms
    for item in data_all:
        assert "timestamp_iso_aest" in item
        # verify conversion: parse back and check offset (rough check by splitting)
        ts = item["timestamp_ms"]
        iso = item["timestamp_iso_aest"]
        # simple sanity: iso string starts with year and contains 'T'
        assert iso.startswith(str(datetime.fromtimestamp(ts/1000).year))
        assert "T" in iso
    # start_ts filter should return records >= second timestamp
    res_start = client.get("/devices/dev2/values", params={"start_ts": timestamps[1]})
    data_start = res_start.json()
    assert len(data_start) == 3
    for item in data_start:
        assert "timestamp_iso_aest" in item
    # end_ts filter should return records <= third timestamp
    res_end = client.get("/devices/dev2/values", params={"end_ts": timestamps[2]})
    data_end = res_end.json()
    assert len(data_end) == 3
    for item in data_end:
        assert "timestamp_iso_aest" in item
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
