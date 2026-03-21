import sys
import os
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


# --- Helpers for building mock InfluxDB responses ---

def make_tag_record(value: str):
    r = MagicMock()
    r.get_value.return_value = value
    return r


def make_table(records):
    t = MagicMock()
    t.records = records
    return t


def make_pivot_record(fields: dict):
    r = MagicMock()
    r.values = fields
    return r


# --- Session-scoped client with InfluxDB mocked out ---

@pytest.fixture(scope="session")
def client():
    with patch("influxdb_client.InfluxDBClient") as mock_cls:
        mock_cls.return_value = MagicMock()
        import main
        with TestClient(main.app) as c:
            yield c


@pytest.fixture(autouse=True)
def reset_influx_mocks():
    import main
    if main.write_api:
        main.write_api.reset_mock()
    if main.query_api:
        main.query_api.reset_mock()
    yield


# --- Tests ---

def test_post_sensor_data(client):
    import main
    res = client.post("/sensors", json={
        "device_id": "dev1",
        "timestamp_ms": 1000,
        "temperature_c": 20.0,
        "humidity_pct": 50.0,
    }, headers={"x-client-secret": "mysecret"})
    assert res.status_code == 200
    assert "id" in res.json()
    main.write_api.write.assert_called_once()


def test_list_devices(client):
    import main
    main.query_api.query.return_value = [
        make_table([make_tag_record("dev1"), make_tag_record("dev2")])
    ]
    res = client.get("/devices")
    assert res.status_code == 200
    assert res.json() == ["dev1", "dev2"]


def test_get_values_returns_records(client):
    import main
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    main.query_api.query.return_value = [
        make_table([make_pivot_record({
            "device_id": "dev1",
            "id": "abc-123",
            "timestamp_ms": now_ms,
            "temperature_c": 22.5,
            # metadata columns that should be stripped
            "result": "_result",
            "table": 0,
            "_start": None,
            "_stop": None,
            "_time": None,
            "_measurement": "sensor_readings",
        })])
    ]
    res = client.get("/devices/dev1/values")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["device_id"] == "dev1"
    assert data[0]["temperature_c"] == 22.5
    assert "timestamp_iso_aest" in data[0]
    assert "T" in data[0]["timestamp_iso_aest"]
    # metadata columns must not appear in response
    assert "_measurement" not in data[0]
    assert "result" not in data[0]


def test_get_values_aest_offset(client):
    import main
    # Use a fixed UTC timestamp and verify the AEST (+10h) ISO string
    fixed_ms = int(datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
    main.query_api.query.return_value = [
        make_table([make_pivot_record({
            "device_id": "dev1",
            "id": "x",
            "timestamp_ms": fixed_ms,
        })])
    ]
    res = client.get("/devices/dev1/values")
    assert res.status_code == 200
    iso = res.json()[0]["timestamp_iso_aest"]
    # 2024-01-01 00:00 UTC → 2024-01-01 10:00 AEST
    assert iso.startswith("2024-01-01T10:00:00")


def test_get_values_device_not_found(client):
    import main
    # Both the values query and the existence check return empty
    main.query_api.query.return_value = []
    res = client.get("/devices/unknown/values")
    assert res.status_code == 404


def test_get_values_empty_range_device_exists(client):
    import main
    # Values query returns empty but existence check finds the device
    main.query_api.query.side_effect = [
        [],  # main pivot query — no results in time range
        [make_table([make_tag_record("dev1")])],  # _device_exists
    ]
    res = client.get("/devices/dev1/values")
    assert res.status_code == 200
    assert res.json() == []


def test_get_values_zero_limit(client):
    res = client.get("/devices/dev1/values", params={"limit": 0})
    assert res.status_code == 200
    assert res.json() == []


def test_get_values_negative_limit(client):
    res = client.get("/devices/dev1/values", params={"limit": -5})
    assert res.status_code == 200
    assert res.json() == []


def test_unauthorized(client):
    res = client.post("/sensors", json={
        "device_id": "dev1",
        "timestamp_ms": 1000,
    }, headers={"x-client-secret": "wrong"})
    assert res.status_code == 401


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert "server_datetime" in body
    # verify it parses as a valid ISO 8601 datetime
    datetime.fromisoformat(body["server_datetime"])
