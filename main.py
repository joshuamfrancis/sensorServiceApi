from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import uuid4
from datetime import datetime

app = FastAPI()

# In-memory storage
# device_id -> list of records
storage = {}

class SensorData(BaseModel):
    device_id: str
    timestamp_ms: int
    temperature_c: float
    temperature_f: float
    humidity_pct: float
    pressure_hpa: float
    altitude_m: float

class StoredSensorData(SensorData):
    id: str = Field(default_factory=lambda: str(uuid4()))

@app.post("/sensors")
def post_sensor_data(data: SensorData, x_client_secret: Optional[str] = Header(None)):
    # Authentication placeholder: check x-client-secret
    if x_client_secret != "mysecret":
        raise HTTPException(status_code=401, detail="Unauthorized")
    # pydantic v2: use model_dump instead of dict
    record = StoredSensorData(**data.model_dump())
    storage.setdefault(record.device_id, []).append(record)
    return {"id": record.id}

@app.get("/devices")
def list_devices():
    return list(storage.keys())

@app.get("/devices/{device_id}/values")
def get_device_values(device_id: str, start_ts: Optional[int] = None, end_ts: Optional[int] = None, limit: Optional[int] = None):
    if device_id not in storage:
        raise HTTPException(status_code=404, detail="Device not found")
    values = storage[device_id]
    # filter by time
    if start_ts is not None:
        values = [v for v in values if v.timestamp_ms >= start_ts]
    if end_ts is not None:
        values = [v for v in values if v.timestamp_ms <= end_ts]
    # sort by timestamp
    values.sort(key=lambda v: v.timestamp_ms)
    if limit is not None:
        # negative or zero limit should return empty list
        try:
            l = int(limit)
        except ValueError:
            raise HTTPException(status_code=400, detail="limit must be an integer")
        if l <= 0:
            return []
        values = values[-l:]
    return values
