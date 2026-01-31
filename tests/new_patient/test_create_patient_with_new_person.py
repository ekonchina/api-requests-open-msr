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
    # Сценарий: формируем валидный объект Person для вложенного создания (POST /patient).
    # Ожидаемый результат: возвращается словарь person с обязательными полями names/gender/birthdate.
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
    # Сценарий: формируем валидный payload для POST /patient (создаём и patient, и person вместе).
    # Ожидаемый результат: payload содержит корректные person + identifiers (с валидными type/value/location).
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
    # Сценарий: отправляем POST /patient с указанным payload.
    # Ожидаемый результат: получаем Response от OpenMRS (успех или ошибка валидации).
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
# Create new person validation
# ============================================================

@pytest.mark.parametrize(
    "person_value, description",
    [
        #https://app.testiny.io/p/1/testcases/tcf/44/tc/78
        # Сценарий: поле person передано как null.
        # Ожидаемый результат: HTTP 400 или 500, в тексте ошибки есть person/null.
        (None, "person is null"),
        #https://app.testiny.io/p/1/testcases/tcf/44/tc/79
        # Сценарий: поле person передано пустой строкой (не объект).
        # Ожидаемый результат: HTTP 400 или 500.
        ("", "person is empty string"),
        #https://app.testiny.io/p/1/testcases/tcf/44/tc/80
        # Сценарий: поле person передано строкой (например uuid-like), но мы ожидаем объект person при одновременном создании.
        # Ожидаемый результат: HTTP 400 или 500.
        ("uuid-like-string", "person is string instead of object"),

    ],
)
def test_create_patient_with_invalid_person_root(person_value, description):
    # Сценарий: берём валидный payload и портим поле person одним из вариантов выше.
    # Ожидаемый результат: OpenMRS не создаёт пациента (ошибка валидации).
    payload = build_valid_patient_payload_dict()

    if person_value == "__MISSING__":
        payload.pop("person", None)
    else:
        payload["person"] = person_value

    response = post_patient(payload)

    assert response.status_code in (400, 500), (
        f"{description}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )
    assert "person" in (response.text or "").lower() or "null" in (response.text or "").lower()


# ============================================================
# 2) person.names validation
# ============================================================

@pytest.mark.parametrize(
    "invalid_names",
    [   # https://app.testiny.io/p/1/testcases/tcf/45/tc/81
        # Сценарий: person.names = null.
        # Ожидаемый результат: HTTP 400 (валидация обязательного списка имён).
        None,
        # https://app.testiny.io/p/1/testcases/tcf/45/tc/82
        # Сценарий: person.names = "" (неверный тип).
        # Ожидаемый результат: HTTP 400.
        "",
        # https://app.testiny.io/p/1/testcases/tcf/45/tc/83
        # Сценарий: person.names = {} (неверный тип — объект вместо списка).
        # Ожидаемый результат: HTTP 400.
        {},
        # https://app.testiny.io/p/1/testcases/tcf/45/tc/84
        # Сценарий: person.names = [] (пустой список имён).
        # Ожидаемый результат: HTTP 400.
        [],
        # https://app.testiny.io/p/1/testcases/tcf/45/tc/85
        # Сценарий: в names[0] отсутствует givenName.
        # Ожидаемый результат: HTTP 400 (givenName обязателен).
        [{"familyName": "X"}],

        # https://app.testiny.io/p/1/testcases/tcf/45/tc/86
        # Сценарий: givenName пустая строка.
        # Ожидаемый результат: HTTP 400.
        [{"givenName": "", "familyName": "X"}],
        # https://app.testiny.io/p/1/testcases/tcf/45/tc/87
        # Сценарий: элемент списка names не объект (неверный тип).
        # Ожидаемый результат: HTTP 400.
        [123],
    ],
)
def test_create_patient_with_invalid_person_names(invalid_names):
    # Сценарий: создаём валидный payload и подставляем невалидный person.names.
    # Ожидаемый результат: OpenMRS отклоняет запрос → HTTP 400.
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
    [   #https://app.testiny.io/p/1/testcases/tcf/45/tc/88/
        # Сценарий: указан только givenName, familyName отсутствует.
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как в вашей системе familyName считается необязательным.
        [{"givenName": "X"}],

        #https://app.testiny.io/p/1/testcases/tcf/45/tc/89
        # Сценарий: familyName задан пустой строкой.
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как система не валидирует familyName как обязательный/непустой.
        [{"givenName": "X", "familyName": ""}],
    ],
)
def test_create_patient_with_person_names_familyname_optional_positive(names_payload):
    # Сценарий: подменяем person.names на “позитивный” кейс, где familyName не обязателен.
    # Ожидаемый результат: успешное создание пациента.
    payload = build_valid_patient_payload_dict()
    payload["person"]["names"] = names_payload

    response = post_patient(payload)

    assert response.status_code in (200, 201), (
        f"names_payload={names_payload!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )

    # Ожидаемый результат: в ответе есть базовая структура Patient.
    data = response.json()
    assert isinstance(data, dict)
    assert "uuid" in data and isinstance(data["uuid"], str)
    assert data.get("voided") is False
    assert isinstance(data.get("person"), dict)


# ============================================================
# 3) person.gender validation (type/empty)
# ============================================================

@pytest.mark.parametrize(
    "invalid_gender",
    [
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/90
        # Сценарий: gender = null.
        # Ожидаемый результат: HTTP 400 (обязательное поле).
        None,
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/91
        # Сценарий: gender = "" (пустая строка).
        # Ожидаемый результат: HTTP 400.
        "",
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/92
        # Сценарий: gender неверного типа (число).
        # Ожидаемый результат: HTTP 400.
        123,
    ],
)
def test_create_patient_with_invalid_gender(invalid_gender):
    # Сценарий: подставляем невалидный gender (пусто/неверный тип).
    # Ожидаемый результат: OpenMRS отклоняет запрос → HTTP 400.
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


# ============================================================
# 3b) person.gender custom values — POSITIVE (сейчас работает, но не должно)
# ============================================================

@pytest.mark.parametrize(
    "gender_value",
    [
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/93
        # Сценарий: gender = "X" (нестандартное значение).
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как в вашей системе gender не валидируется строго по enum M/F/U.
        "X",
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/94
        # Сценарий: gender = "M" (нестандартное значение).
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как в вашей системе gender не валидируется строго по enum M/F/U.
        "M",
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/95
        # Сценарий: gender = "F" .
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как в вашей системе gender не валидируется строго по enum M/F/U.
        "F",
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/96
        # Сценарий: gender = "U"
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как в вашей системе gender не валидируется строго по enum M/F/U.
        "U",
        #https://app.testiny.io/p/1/testcases/tcf/45/tc/97
        # Сценарий: gender = "male" (нестандартная строка).
        # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
        # так как в вашей системе gender принимает произвольные строки.
        "male",
    ],
)
def test_create_patient_with_custom_gender_positive(gender_value):
    # Сценарий: подставляем кастомный gender, который система неожиданно принимает.
    # Ожидаемый результат: успешное создание пациента.
    payload = build_valid_patient_payload_dict()
    payload["person"]["gender"] = gender_value

    response = post_patient(payload)

    assert response.status_code in (200, 201), (
        f"gender_value={gender_value!r}\n"
        f"Response body: {(response.text or '')[:2000]}"
    )

    # Ожидаемый результат: в ответе есть базовая структура Patient.
    data = response.json()
    assert isinstance(data, dict)
    assert "uuid" in data and isinstance(data["uuid"], str)
    assert data.get("voided") is False
    assert isinstance(data.get("person"), dict)

    # Ожидаемый результат: если gender возвращается в этом представлении — он совпадает с отправленным.
    returned_gender = (data.get("person") or {}).get("gender")
    if returned_gender is not None:
        assert returned_gender == gender_value


# ============================================================
# 4) person.birthdate validation — NEGATIVE
# ============================================================

@pytest.mark.parametrize(
    "invalid_birthdate",
    [
        # Сценарий: birthdate = "" (пустая строка).
        # Ожидаемый результат: HTTP 400.
        "",

        # Сценарий: birthdate = "   " (пробелы).
        # Ожидаемый результат: HTTP 400.
        "   ",

        # Сценарий: birthdate в неправильном формате (не ISO YYYY-MM-DD).
        # Ожидаемый результат: HTTP 400.
        "31-12-1990",

        # Сценарий: birthdate — не дата.
        # Ожидаемый результат: HTTP 400.
        "not-a-date",

        # Сценарий: birthdate в будущем.
        # Ожидаемый результат: HTTP 400 (обычно запрещено).
        "3000-01-01",

        # Сценарий: birthdate неверного типа (число).
        # Ожидаемый результат: HTTP 400.
        12345,

        # Сценарий: birthdate неверного типа (list).
        # Ожидаемый результат: HTTP 400.
        [],

        # Сценарий: birthdate неверного типа (dict).
        # Ожидаемый результат: HTTP 400.
        {},
    ],
)
def test_create_patient_with_invalid_birthdate(invalid_birthdate):
    # Сценарий: подставляем невалидный birthdate.
    # Ожидаемый результат: OpenMRS отклоняет запрос → HTTP 400.
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
    # Сценарий: birthdate передаётся как null.
    # Ожидаемый результат: пациент создаётся успешно (HTTP 200/201),
    # так как в вашей системе birthdate допускается неизвестной (null).
    payload = build_valid_patient_payload_dict()
    payload["person"]["birthdate"] = None

    response = post_patient(payload)

    assert response.status_code in (200, 201), (
        "birthdate=None\n"
        f"Response body: {(response.text or '')[:2000]}"
    )

    # Ожидаемый результат: в ответе есть базовая структура Patient.
    data = response.json()
    assert isinstance(data, dict)
    assert "uuid" in data and isinstance(data["uuid"], str)
    assert data.get("voided") is False

    # Ожидаемый результат: birthdate либо null, либо отсутствует/пустое в ответе (в зависимости от representation).
    returned_birthdate = (data.get("person") or {}).get("birthdate")
    assert returned_birthdate in (None, "")
