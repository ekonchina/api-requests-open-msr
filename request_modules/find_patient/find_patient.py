import requests
from requests.auth import HTTPBasicAuth
from typing import Optional

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


def find_patient_by_identifier(identifier: str) -> Optional[dict]:
    """
    Ищет пациента по identifier.
    Возвращает patient object (dict) или None.
    """
    url = f"{BASE_URL}/patient"

    response = requests.get(
        url,
        params={
            "q": identifier,
            "v": "default",
        },
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=30,
    )

    response.raise_for_status()
    data = response.json()

    results = data.get("results", [])
    if not results:
        return None

    # обычно identifier уникален → берём первого
    return results[0]
