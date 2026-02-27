# Sensor Service API

A simple Python REST API for collecting and querying sensor data.

## Features

- POST `/sensors` to submit sensor readings (with client secret authentication)
- GET `/devices` to list known device IDs
- GET `/devices/{device_id}/values` to query readings for a device
  - support filtering by `start_ts`, `end_ts`, and `limit` via query parameters
- GET `/health` returns a simple status JSON indicating the service is running

## Getting Started

```bash
python -m venv .venv
source .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Running the app

```bash
uvicorn main:app --reload
```

### Testing

```bash
pytest
```

## Docker

Build:

```bash
docker build -t sensor-service .
```

Run:

```bash
docker run -p 8000:8000 sensor-service
```

## License

MIT
