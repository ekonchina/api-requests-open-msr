import requests
from requests.auth import HTTPBasicAuth

# ==== НАСТРОЙКИ ====
BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"

LOCATION_UUID = "6d49188b-2bdf-4c6e-bdff-7eeed3e15a64"
REASON = "Location is no longer in use"

URL = f"{BASE_URL}/location/{LOCATION_UUID}"

# ==== ЗАПРОС ====
response = requests.delete(
    URL,
    auth=HTTPBasicAuth(USERNAME, PASSWORD),
    headers={"Accept": "application/json"},
    params={"reason": REASON}
)

response.raise_for_status()

print(f"✅ Location {LOCATION_UUID} помечена как retired")
