# tests/test_create_visit.py

from __future__ import annotations

from datetime import datetime, timezone
import uuid
import pytest
import requests
from requests.auth import HTTPBasicAuth

from checks.visit_checks import assert_valid_visit_response

from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_valid_patient_with_person
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import get_openmrs_id_identifier
from request_modules.visittype.get_random_valid_visit_type import get_random_valid_visit_type
from request_modules.visit.create_visit import create_visit, fetch_visit_full


USERNAME = "admin"
PASSWORD = "Admin123"


def iso_utc_now() -> str:
    # пример в доках: 2016-10-08T04:09:25.000Z
    # делаем ISO8601 с миллисекундами и Z
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.000Z")


#TODO: NEED WORK!
#TODO: CREATE USERS FOR DEMO

@pytest.fixture()
def patient_context() -> dict:
    # 1) создаём Person
    person = create_valid_person()

    # 2) берём локацию
    location = get_random_valid_location()
    location_uuid = location["uuid"]

    # 3) берём корректный OpenMRS ID тип + значение (LuhnMod30)
    identifier_type_uuid, identifier_value = get_openmrs_id_identifier()

    # 4) создаём Patient на базе person
    patient_json = create_valid_patient_with_person(
        username=USERNAME,
        password=PASSWORD,
        person=person,
        location=location_uuid,
        identifier_type=identifier_type_uuid,
        patient_identifier=identifier_value,
    )

    return {
        "patient_uuid": patient_json["uuid"],
        "location_uuid": location_uuid,
    }


@pytest.fixture()
def visit_type_uuid() -> str:
    return get_random_valid_visit_type()["uuid"]

#TODO: все валидные типы полей
#TODO: проверить роли
def test_create_visit_success(patient_context: dict, visit_type_uuid: str):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    resp = create_visit(
        username=USERNAME,
        password=PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc_now(),
        location_uuid=location_uuid,
    )

    assert resp.status_code == 201, resp.text
    visit = resp.json()

    assert_valid_visit_response(
        visit,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
    )

    # дополнительно: GET full и проверка консистентности
    full = fetch_visit_full(username=USERNAME, password=PASSWORD, visit_uuid=visit["uuid"])
    assert_valid_visit_response(
        full,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
    )


@pytest.mark.parametrize(
    "mutator",
    [
        lambda p: {k: v for k, v in p.items() if k != "patient"},
        lambda p: {k: v for k, v in p.items() if k != "visitType"},
        lambda p: {k: v for k, v in p.items() if k != "startDatetime"},
    ],
)
def test_create_visit_missing_required_fields_returns_400(patient_context: dict, visit_type_uuid: str, mutator):
    """
    В REST доках patient и visitType помечены как Required,
    а startDatetime — core-required для Visit (см. Visit constructor).
    :contentReference[oaicite:2]{index=2}
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc_now(),
        "location": location_uuid,
    }

    bad_payload = mutator(payload)



    resp = requests.post(
        "http://localhost/openmrs/ws/rest/v1/visit",
        json=bad_payload,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )

    assert resp.status_code == 400, resp.text


def test_create_visit_invalid_patient_uuid_returns_400_or_404(visit_type_uuid: str):
    """
    В зависимости от версии/валидации ресурс может вернуть 400 (bad ref) или 404.
    """
    fake_patient_uuid = str(uuid.uuid4())

    location_uuid = get_random_valid_location()["uuid"]
    resp = create_visit(
        username=USERNAME,
        password=PASSWORD,
        patient_uuid=fake_patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc_now(),
        location_uuid=location_uuid,
    )

    assert resp.status_code in (400, 404), resp.text


def test_create_visit_unauthorized_returns_401(patient_context: dict, visit_type_uuid: str):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    resp = create_visit(
        username=USERNAME,
        password="WRONG_PASSWORD",
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc_now(),
        location_uuid=location_uuid,
    )

    assert resp.status_code == 401, resp.text
