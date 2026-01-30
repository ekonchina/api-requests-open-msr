# request_modules/visittype/get_random_valid_visit_type.py

import random
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


def get_random_valid_visit_type() -> dict:
    url = f"{BASE_URL}/visittype"
    r = requests.get(
        url,
        params={"v": "default"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()

    results = r.json().get("results", []) or []
    if not results:
        raise RuntimeError("VisitType list is empty")

    return random.choice(results)
