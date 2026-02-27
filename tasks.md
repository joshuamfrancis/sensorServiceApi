Aim is to generate a Python REST API service that takes sensor values as HTTP POST method with a sample body  
{
  "device_id": "esp32c5-bme280-01",
  "timestamp_ms": 12345678,
  "temperature_c": 23.45,
  "temperature_f": 74.21,
  "humidity_pct": 48.30,
  "pressure_hpa": 1012.75,
  "altitude_m": 5.2
}
The API will use client secret authentication with values passed in the header.
The API will use JSON serialization with content-Type Application/json

Tasks:
[x] Create a VENV for the project
[x] Generate a python REST api handle POST method that takes payload mentioned above.
[x] Generate a unique id when processing new senosr data in the POST request and store it in memory (for now)
[x] Generate a GET method to return a list of devices
[x] generate a GET method to return values for specific sensor passed as path parameter
[x] generate a GET method to return specific sensor values with query parameters on date AND , OR number recent values to return.
[x] Create unit test for the project.
[x] Generate a README.md for the project.
[x] Create requirement.txt
[x] Create a docker file to containerize the application.
[x] generate github CICD workflow to unit test the API, build docker image, publish the image to dockerhub