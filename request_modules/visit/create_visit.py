# request_modules/visit/create_visit.py

import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"


def create_visit(
    *,
    username: str,
    password: str,
    patient_uuid: str,
    visit_type_uuid: str,
    start_datetime_iso: str,
    location_uuid: str | None = None,
    stop_datetime_iso: str | None = None,
) -> requests.Response:
    """
    POST /visit
    payload в соответствии с REST docs: patient, visitType, startDatetime, location, stopDatetime...
    :contentReference[oaicite:1]{index=1}
    """
    payload: dict = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": start_datetime_iso,
    }
    if location_uuid is not None:
        payload["location"] = location_uuid
    if stop_datetime_iso is not None:
        payload["stopDatetime"] = stop_datetime_iso

    resp = requests.post(
        f"{BASE_URL}/visit",
        json=payload,
        auth=HTTPBasicAuth(username, password),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )
    return resp


def fetch_visit_full(*, username: str, password: str, visit_uuid: str) -> dict:
    r = requests.get(
        f"{BASE_URL}/visit/{visit_uuid}",
        params={"v": "full"},
        auth=HTTPBasicAuth(username, password),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()
