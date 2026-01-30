import requests
from requests.auth import HTTPBasicAuth
import random



def get_random_valid_location():
    BASE_URL = "http://localhost/openmrs/ws/rest/v1"
    USERNAME = "admin"
    PASSWORD = "Admin123"

    url = f"{BASE_URL}/location"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=30,
    )

    locations = response.json().get("results", [])

    if not locations:
        raise RuntimeError("Список локаций пуст")

    return random.choice(locations)
