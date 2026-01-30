import random
import uuid
import requests
from requests.auth import HTTPBasicAuth
from faker import Faker

from src.openmrs_patient import Person, Address, PersonName

fake = Faker("ru_RU")

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


def _fetch_person_full(person_uuid: str) -> dict:
    url = f"{BASE_URL}/person/{person_uuid}"
    r = requests.get(
        url,
        params={"v": "full"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def person_from_json(data: dict) -> Person:
    def parse_names(obj: dict) -> list[PersonName]:
        names_local: list[PersonName] = []

        preferred = obj.get("preferredName")
        if isinstance(preferred, dict) and preferred.get("givenName") and preferred.get("familyName"):
            names_local.append(PersonName(givenName=preferred["givenName"], familyName=preferred["familyName"]))

        for n in obj.get("names", []) or []:
            if isinstance(n, dict) and n.get("givenName") and n.get("familyName"):
                if not any(x.givenName == n["givenName"] and x.familyName == n["familyName"] for x in names_local):
                    names_local.append(PersonName(givenName=n["givenName"], familyName=n["familyName"]))

        return names_local

    names = parse_names(data)

    if not names:
        person_uuid = data.get("uuid")
        if person_uuid:
            full_data = _fetch_person_full(person_uuid)
            names = parse_names(full_data)
            data = full_data

    if not names:
        raise ValueError(
            "OpenMRS returned Person without parseable names. "
            f"uuid={data.get('uuid')}, keys={list(data.keys())}"
        )

    raw_addresses = data.get("addresses") or []
    addresses: list[Address] = [
        Address(address1=a.get("address1", ""), cityVillage=a.get("cityVillage", ""))
        for a in raw_addresses
        if isinstance(a, dict)
    ]

    return Person(
        names=names,
        gender=data.get("gender", ""),
        birthdate=data.get("birthdate", ""),
        addresses=addresses,
    )


def generate_person_payload() -> dict:
    gender = random.choice(["M", "F"])
    return {
        "names": [
            {
                "givenName": fake.first_name_male() if gender == "M" else fake.first_name_female(),
                "familyName": fake.last_name(),
                "preferred": True,
            }
        ],
        "gender": gender,
        "birthdate": fake.date_of_birth(minimum_age=18, maximum_age=80).isoformat(),
    }


def create_valid_person() -> Person:
    url = f"{BASE_URL}/person"
    payload = generate_person_payload()

    response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )

    print("Payload:", payload)
    print("Status:", response.status_code)
    print("Response:", response.text)

    response.raise_for_status()
    return person_from_json(response.json())


# =======================
# ✅ ДОБАВЛЕНО ПО ОШИБКЕ MissingRequiredIdentifierException
# =======================

def get_required_identifier_type_uuid(required_name: str = "OpenMRS ID") -> str:
    """
    Находит UUID обязательного identifier type (по умолчанию OpenMRS ID).
    """
    url = f"{BASE_URL}/patientidentifiertype"
    r = requests.get(
        url,
        params={"v": "default"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()

    for item in r.json().get("results", []):
        if item.get("required") is True and item.get("name") == required_name:
            return item["uuid"]

    raise RuntimeError(f"Required identifier type '{required_name}' not found")


def generate_required_identifier_value() -> str:
    """
    Генерирует значение для required идентификатора.
    (Если в системе настроен строгий формат для OpenMRS ID — подстроим генерацию.)
    """
    # универсально для тестов: уникальная строка
    return str(uuid.uuid4())


def get_required_openmrs_id() -> tuple[str, str]:
    """
    Возвращает (openmrs_id_type_uuid, generated_openmrs_id_value)
    """
    id_type_uuid = get_required_identifier_type_uuid("OpenMRS ID")
    value = generate_required_identifier_value()
    return id_type_uuid, value
