import pytest
import requests
from requests.auth import HTTPBasicAuth
from faker import Faker

from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import get_openmrs_id_identifier

fake = Faker("ru_RU")

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


def build_valid_person_dict() -> dict:
    return {
        "names": [{"givenName": fake.first_name_male(), "familyName": fake.last_name()}],
        "gender": "M",
        "birthdate": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
        # addresses опциональны в большинстве конфигов, но если нужны — раскомментируй
        # "addresses": [{"address1": fake.street_address(), "cityVillage": fake.city(), "country": "Russia"}],
    }


def build_valid_patient_payload_dict() -> dict:
    location_uuid = get_random_valid_location()["uuid"]
    id_type_uuid, id_value = get_openmrs_id_identifier()

    return {
        "person": build_valid_person_dict(),
        "identifiers": [
            {
                "identifier": id_value,
                "identifierType": id_type_uuid,
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
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )


def set_by_path(obj: dict, path: str, value) -> None:
    """
    Устанавливает значение по простому пути:
      - "person.gender"
      - "person.birthdate"
      - "person.names[0].givenName"
    Если value == "__MISSING__", поле удаляется.
    """
    parts = path.split(".")
    cur = obj
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1

        # names[0]
        if "[" in part and part.endswith("]"):
            key = part[:part.index("[")]
            idx = int(part[part.index("[") + 1 : -1])
            cur = cur[key][idx]
            continue

        if is_last:
            if value == "__MISSING__":
                cur.pop(part, None)
            else:
                cur[part] = value
        else:
            cur = cur[part]


@pytest.mark.parametrize(
    "field_path, invalid_value",
    [
        # person root
        ("person", "__MISSING__"),

        # names
        ("person.names", "__MISSING__"),
        ("person.names", []),
        ("person.names", "not-a-list"),

        ("person.names[0].givenName", "__MISSING__"),
        ("person.names[0].givenName", None),
        ("person.names[0].givenName", ""),
        ("person.names[0].givenName", "   "),

        ("person.names[0].familyName", "__MISSING__"),
        ("person.names[0].familyName", None),
        ("person.names[0].familyName", ""),
        ("person.names[0].familyName", "   "),

        # gender
        ("person.gender", "__MISSING__"),
        ("person.gender", None),
        ("person.gender", ""),
        ("person.gender", "X"),     # invalid enum
        ("person.gender", 123),     # wrong type

        # birthdate
        ("person.birthdate", "__MISSING__"),
        ("person.birthdate", None),
        ("person.birthdate", ""),
        ("person.birthdate", "31-12-1990"),   # wrong format
        ("person.birthdate", "not-a-date"),
        ("person.birthdate", 12345),          # wrong type
    ],
    ids=lambda x: str(x),
)
def test_create_patient_with_new_person_invalid_person_fields(field_path, invalid_value):
    payload = build_valid_patient_payload_dict()

    # person удаляем целиком отдельным кейсом
    if field_path == "person" and invalid_value == "__MISSING__":
        payload.pop("person", None)
    else:
        set_by_path(payload, field_path, invalid_value)

    r = post_patient(payload)

    assert r.status_code == 400, f"{field_path}={invalid_value!r}\nBODY: {(r.text or '')[:2000]}"
    # базовая проверка, что ошибка про person/имя/пол может встретиться
    assert any(k in (r.text or "").lower() for k in ["person", "name", "gender", "birthdate"]), (r.text or "")[:2000]
