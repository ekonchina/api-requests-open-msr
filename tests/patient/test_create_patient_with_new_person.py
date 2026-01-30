# tests/test_create_patient_with_new_person_validation.py

import pytest
import requests
from requests.auth import HTTPBasicAuth
from faker import Faker

from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import (
    get_openmrs_id_identifier,
)

fake = Faker("ru_RU")

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


# ============================================================
# helpers
# ============================================================

def build_valid_person_dict() -> dict:
    return {
        "names": [
            {
                "givenName": fake.first_name_male(),
                "familyName": fake.last_name(),
            }
        ],
        "gender": "M",
        "birthdate": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
        # addresses обычно не обязательны в OpenMRS
        # если в вашем инстансе обязательны — добавьте сюда
    }


def build_valid_patient_payload_dict() -> dict:
    location_uuid = get_random_valid_location()["uuid"]
    identifier_type_uuid, identifier_value = get_openmrs_id_identifier()

    return {
        "person": build_valid_person_dict(),
        "identifiers": [
            {
                "identifier": identifier_value,
                "identifierType": identifier_type_uuid,
                "location": location_uuid,
                "preferred": True,
            }
        ],
    }


def post_patient(payload: dict) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/patient",
        json=payload,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30,
    )


# ============================================================
# 1) person root validation
# ============================================================

@pytest.mark.parametrize(
    "person_value, description",
    [
        ("__MISSING__", "person key missing"),
        (None, "person is null"),
        ("", "person is empty string"),
        ("uuid-like-string", "person is string instead of object"),
        (123, "person is int"),
        ([], "person is list"),
        ({}, "person is empty object"),
    ],
)
def test_create_patient_with_invalid_person_root(person_value, description):
    payload = build_valid_patient_payload_dict()

    if person_value == "__MISSING__":
        payload.pop("person", None)
    else:
        payload["person"] = person_value

    response = post_patient(payload)

    assert response.status_code in (400,500), (
        f"{description}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )
    assert "person" in (response.text or "").lower() or "null" in (response.text or "").lower()


# ============================================================
# 2) person.names validation
# ============================================================

@pytest.mark.parametrize(
    "invalid_names",
    [
        None,                               # null - негативный
        "",                                 # wrong type - негативный
        {},                                 # wrong type - негативный
        [],                                 # empty list - негативный
        [{"familyName": "X"}],              # missing givenName - негативный
        [{"givenName": "", "familyName": "X"}],     # blank givenName - негативный
        [{"givenName": "   ", "familyName": "X"}],  # whitespace givenName
        [123],                              # element wrong type
    ],
)
def test_create_patient_with_invalid_person_names(invalid_names):
    payload = build_valid_patient_payload_dict()
    payload["person"]["names"] = invalid_names

    response = post_patient(payload)

    assert response.status_code == 400, (
        f"invalid_names={invalid_names!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )
    assert any(
        key in (response.text or "").lower()
        for key in ["name", "names", "person"]
    )

# ============================================================
# 2b) person.names позитивные кейсы (familyName допускается пустым/отсутствующим)
# ============================================================

@pytest.mark.parametrize(
    "names_payload",
    [
        [{"givenName": "X"}],                         # missing familyName - позитивный кейс (по вашему ожиданию)
        [{"givenName": "X", "familyName": ""}],       # blank familyName - позитивный кейс
        [{"givenName": "X", "familyName": "   "}],    # whitespace familyName - позитивный кейс
    ],
)
def test_create_patient_with_person_names_familyname_optional_positive(names_payload):
    payload = build_valid_patient_payload_dict()

    # подменяем names на кейс
    payload["person"]["names"] = names_payload

    response = post_patient(payload)

    assert response.status_code in (200, 201), (
        f"names_payload={names_payload!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )

    # минимальные проверки структуры ответа (без привязки к твоим checks)
    assert isinstance(response.json(), dict)
    data = response.json()
    assert "uuid" in data and isinstance(data["uuid"], str)
    assert data.get("voided") is False
    assert isinstance(data.get("person"), dict)

# ============================================================
# 3) person.gender validation
# ============================================================

@pytest.mark.parametrize(
    "invalid_gender",
    [
        None,
        "",
        "   ",
        123,        # wrong type
        [],         # wrong type
        {},         # wrong type
    ],
)
def test_create_patient_with_invalid_gender(invalid_gender):
    payload = build_valid_patient_payload_dict()
    payload["person"]["gender"] = invalid_gender

    response = post_patient(payload)

    assert response.status_code == 400, (
        f"invalid_gender={invalid_gender!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )
    assert any(
        key in (response.text or "").lower()
        for key in ["gender", "person"]
    )


#TODO: it works but shouldn't
@pytest.mark.parametrize(
    "gender_value",
    [
        "X",        # EXPECTED: allowed string value (system does NOT strictly enforce M/F/O/U)
        "male",     # EXPECTED: allowed string value (system does NOT strictly enforce M/F/O/U)
    ],
)
def test_create_patient_with_custom_gender_positive(gender_value):
    payload = build_valid_patient_payload_dict()
    payload["person"]["gender"] = gender_value

    response = post_patient(payload)

    assert response.status_code in (200, 201), (
        f"gender_value={gender_value!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )

    data = response.json()
    assert isinstance(data, dict)
    assert "uuid" in data and isinstance(data["uuid"], str)
    assert data.get("voided") is False
    assert isinstance(data.get("person"), dict)

    # если сервер возвращает gender в этом же ответе — проверим, что значение сохранилось
    # (иногда в default representation gender есть, иногда нет — поэтому мягко)
    returned_gender = (data.get("person") or {}).get("gender")
    if returned_gender is not None:
        assert returned_gender == gender_value

# ============================================================
# 4) person.birthdate validation
# ============================================================

@pytest.mark.parametrize(
    "invalid_birthdate",
    [
        "",
        "   ",
        "31-12-1990",     # wrong format
        "not-a-date",
        "3000-01-01",     # future date
        12345,            # wrong type
        [],               # wrong type
        {},               # wrong type
    ],
)
def test_create_patient_with_invalid_birthdate(invalid_birthdate):
    payload = build_valid_patient_payload_dict()
    payload["person"]["birthdate"] = invalid_birthdate

    response = post_patient(payload)

    assert response.status_code == 400, (
        f"invalid_birthdate={invalid_birthdate!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )
    assert any(
        key in (response.text or "").lower()
        for key in ["birthdate", "date", "person"]
    )

# ============================================================
# 4b) person.birthdate = null — POSITIVE
# ============================================================

def test_create_patient_with_null_birthdate_positive():
    payload = build_valid_patient_payload_dict()
    payload["person"]["birthdate"] = None

    response = post_patient(payload)

    # EXPECTED:
    # - System allows birthdate to be null
    # - Patient creation succeeds
    assert response.status_code in (200, 201), (
        f"birthdate=None\n"
        f"Response body: {(response.text or '')[:2000]}"
    )

    data = response.json()
    assert isinstance(data, dict)
    assert "uuid" in data and isinstance(data["uuid"], str)
    assert data.get("voided") is False

    # EXPECTED:
    # - birthdate is either null or omitted in response
    returned_birthdate = (data.get("person") or {}).get("birthdate")
    assert returned_birthdate in (None, "")