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

### 1. Build the image

```bash
docker build -t sensor-service .
```

### 2. Run with Docker Compose

The compose file expects the `sensor-service` image to already exist (built above). It starts InfluxDB 2.7 and the sensor service:

```bash
docker compose up
```

| Service        | URL                        |
|----------------|----------------------------|
| Sensor API     | http://localhost:8001       |
| API docs       | http://localhost:8001/docs  |
| InfluxDB UI    | http://localhost:8086       |

InfluxDB default credentials: `admin` / `adminpassword`

To stop and remove containers:

```bash
docker compose down
```

To also delete persisted InfluxDB data:

```bash
docker compose down -v
```

### Environment variables

| Variable         | Default                  | Description                  |
|------------------|--------------------------|------------------------------|
| `INFLUXDB_URL`   | `http://localhost:8086`  | InfluxDB connection URL       |
| `INFLUXDB_TOKEN` | `my-super-secret-token`  | InfluxDB auth token           |
| `INFLUXDB_ORG`   | `sensor_org`             | InfluxDB organisation         |
| `INFLUXDB_BUCKET`| `sensor_data`            | InfluxDB bucket               |
| `CLIENT_SECRET`  | `mysecret`               | API auth header value         |

### Run the sensor service container only

```bash
docker run -p 8001:8000 \
  -e INFLUXDB_URL=http://<host>:8086 \
  -e INFLUXDB_TOKEN=<token> \
  sensor-service
```

## License

MIT
