import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
auth = HTTPBasicAuth("admin", "Admin123")

url = f"{BASE_URL}/role?v=default&limit=100"
data = requests.get(url, auth=auth, headers={"Accept": "application/json"}).json()

for r in data.get("results", []):
    print(r.get("display"), r.get("uuid"))
