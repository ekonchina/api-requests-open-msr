# не работает

import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
auth = HTTPBasicAuth("admin", "Admin123")

ROLE_NAME = "Custom: Add Patients Only"
DESCRIPTION = "Can add patients but cannot add people/identifiers"

def create_role():
    r = requests.post(
        f"{BASE_URL}/role",
        json={
            "name": ROLE_NAME,
            "description": DESCRIPTION,
        },
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        auth=auth,
        timeout=30,
    )
    print("create role status:", r.status_code)
    print(r.text)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    created = create_role()
    print("role uuid:", created.get("uuid"))
