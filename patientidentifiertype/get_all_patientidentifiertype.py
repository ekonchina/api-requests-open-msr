import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"  # замени на свой пароль

url = f"{BASE_URL}/patientidentifiertype"

response = requests.get(
    url,
    params={"v": "default"},
    auth=HTTPBasicAuth(USERNAME, PASSWORD),
    headers={"Accept": "application/json"}
)

response.raise_for_status()

data = response.json()

for item in data.get("results", []):
    print(f"Name: {item['name']}")
    print(f"UUID: {item['uuid']}")
    print(f"Required: {item.get('required')}")
    print(f"Format: {item.get('format')}")
    print("-" * 40)
