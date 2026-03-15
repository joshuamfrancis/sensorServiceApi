import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "my-super-secret-token")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "sensor_org")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "sensor_data")
CLIENT_SECRET = os.getenv("CLIENT_SECRET", "mysecret")
MEASUREMENT = "sensor_readings"

influx_client: InfluxDBClient | None = None
write_api = None
query_api = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global influx_client, write_api, query_api
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    query_api = influx_client.query_api()
    yield
    influx_client.close()


app = FastAPI(lifespan=lifespan)


class SensorData(BaseModel):
    model_config = ConfigDict(extra="allow")
    device_id: str
    timestamp_ms: int


def _ms_to_flux_time(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _device_exists(device_id: str) -> bool:
    query = f'''
        import "influxdata/influxdb/schema"
        schema.tagValues(bucket: "{INFLUXDB_BUCKET}", tag: "device_id")
          |> filter(fn: (r) => r._value == "{device_id}")
    '''
    tables = query_api.query(query)
    return any(True for table in tables for _ in table.records)


@app.post("/sensors")
def post_sensor_data(data: SensorData, x_client_secret: Optional[str] = Header(None)):
    if x_client_secret != CLIENT_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")

    record_id = str(uuid4())
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    point = (
        Point(MEASUREMENT)
        .tag("device_id", data.device_id)
        .field("id", record_id)
        .field("timestamp_ms", now_ms)
        .time(now_ms * 1_000_000, WritePrecision.NS)
    )
    for key, value in data.model_dump(exclude={"device_id", "timestamp_ms"}).items():
        if isinstance(value, (int, float, str, bool)):
            point = point.field(key, value)

    write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    return {"id": record_id}


@app.get("/devices")
def list_devices():
    query = f'''
        import "influxdata/influxdb/schema"
        schema.tagValues(bucket: "{INFLUXDB_BUCKET}", tag: "device_id")
    '''
    tables = query_api.query(query)
    return [record.get_value() for table in tables for record in table.records]


@app.get("/devices/{device_id}/values")
def get_device_values(
    device_id: str,
    start_ts: Optional[int] = None,
    end_ts: Optional[int] = None,
    limit: Optional[int] = None,
):
    if limit is not None and limit <= 0:
        return []

    start = _ms_to_flux_time(start_ts) if start_ts is not None else "1970-01-01T00:00:00Z"
    stop_part = f", stop: {_ms_to_flux_time(end_ts)}" if end_ts is not None else ""
    tail_part = f"\n  |> tail(n: {limit})" if limit is not None else ""

    query = f'''
        from(bucket: "{INFLUXDB_BUCKET}")
          |> range(start: {start}{stop_part})
          |> filter(fn: (r) => r._measurement == "{MEASUREMENT}" and r["device_id"] == "{device_id}")
          |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["timestamp_ms"]){tail_part}
    '''
    tables = query_api.query(query)
    rows = [record.values for table in tables for record in table.records]

    if not rows:
        if not _device_exists(device_id):
            raise HTTPException(status_code=404, detail="Device not found")
        return []

    meta_cols = {"result", "table", "_start", "_stop", "_time", "_measurement"}
    result = []
    for row in rows:
        rec = {k: v for k, v in row.items() if k not in meta_cols}
        ts_ms = int(rec.get("timestamp_ms", 0))
        dt_utc = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        rec["timestamp_iso_aest"] = (dt_utc + timedelta(hours=10)).isoformat()
        result.append(rec)

    return result


@app.get("/health")
def health_check():
    return {"status": "ok"}
