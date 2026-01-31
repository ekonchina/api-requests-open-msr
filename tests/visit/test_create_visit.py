# tests/visit/test_create_visit_all_cases_one_module.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

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


# -------------------------
# config
# -------------------------
BASE_URL = "http://localhost/openmrs/ws/rest/v1"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin123"


# -------------------------
# helpers
# -------------------------
def iso_utc(dt: datetime) -> str:
    """
    OpenMRS docs example: 2016-10-08T04:09:25.000Z
    """
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def post_visit_raw(*, username: str, password: str, payload: dict) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/visit",
        json=payload,
        auth=HTTPBasicAuth(username, password),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )


# -------------------------
# fixtures
# -------------------------
@pytest.fixture()
def patient_context() -> dict:
    """
    Создаём пациента под админом (чтобы затем проверять права на /visit
    отдельно от прав на создание пациента).
    """
    person = create_valid_person()
    location_uuid = get_random_valid_location()["uuid"]
    identifier_type_uuid, identifier_value = get_openmrs_id_identifier()

    patient_json = create_valid_patient_with_person(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
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
    """
    Берём любой существующий visitType.
    """
    return get_random_valid_visit_type()["uuid"]





# =====================================================================
# 2) DATE/TIME EDGE CASES + 2 VISITS
# =====================================================================

def test_create_visit_in_the_past_success(patient_context: dict, visit_type_uuid: str):
    """
    Визит в прошлом обычно допустим (исторические визиты).
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    start = datetime(2000, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    resp = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(start),
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

    full = fetch_visit_full(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, visit_uuid=visit["uuid"])
    assert_valid_visit_response(
        full,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
    )


def test_create_visit_in_far_future_rejected(patient_context: dict, visit_type_uuid: str):
    """
    Визит в далёком будущем — часто должен отклоняться.
    Если ваш инстанс разрешает — поменяй этот тест на позитивный.
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    far_future = datetime(3000, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    resp = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(far_future),
        location_uuid=location_uuid,
    )

    if resp.status_code == 201:
        pytest.fail(
            "Ожидали отказ для визита в далёком будущем, но OpenMRS вернул 201.\n"
            "Если по требованиям так можно — сделай тест позитивным.\n"
            f"Body: {(resp.text or '')[:2000]}"
        )

    assert resp.status_code in (400, 500), resp.text
    assert any(
        k in (resp.text or "").lower()
        for k in ["startdatetime", "date", "datetime", "future"]
    )


def test_create_visit_stop_before_start_rejected(patient_context: dict, visit_type_uuid: str):
    """
    stopDatetime раньше startDatetime — неконсистентные даты.
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    start = datetime.now(timezone.utc)
    stop = start - timedelta(days=1)

    resp = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(start),
        stop_datetime_iso=iso_utc(stop),
        location_uuid=location_uuid,
    )

    assert resp.status_code in (400, 500), resp.text
    assert any(
        k in (resp.text or "").lower()
        for k in ["stopdatetime", "startdatetime", "end date", "before", "after", "date"]
    )


def test_create_two_visits_same_patient_sequential_success(patient_context: dict, visit_type_uuid: str):
    """
    2 визита у одного пациента — OK, если первый закрыт (есть stopDatetime).
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    start1 = datetime.now(timezone.utc) - timedelta(hours=2)
    stop1 = start1 + timedelta(hours=1)

    r1 = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(start1),
        stop_datetime_iso=iso_utc(stop1),
        location_uuid=location_uuid,
    )
    assert r1.status_code == 201, r1.text
    v1 = r1.json()

    assert_valid_visit_response(
        v1,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
    )

    start2 = stop1 + timedelta(minutes=10)

    r2 = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(start2),
        location_uuid=location_uuid,
    )
    assert r2.status_code == 201, r2.text
    v2 = r2.json()

    assert v2["uuid"] != v1["uuid"]
    assert_valid_visit_response(
        v2,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
    )


def test_create_second_active_visit_overlapping_rejected_or_allowed(patient_context: dict, visit_type_uuid: str):
    """
    Перекрывающиеся активные визиты: зависит от конфигурации.
    - если запрещено -> 400/409/500
    - если разрешено -> 201 и валидная структура
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    start1 = datetime.now(timezone.utc) - timedelta(minutes=30)

    r1 = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(start1),
        location_uuid=location_uuid,
    )
    assert r1.status_code == 201, r1.text
    v1 = r1.json()

    start2 = datetime.now(timezone.utc) - timedelta(minutes=10)

    r2 = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(start2),
        location_uuid=location_uuid,
    )

    if r2.status_code == 201:
        v2 = r2.json()
        assert v2["uuid"] != v1["uuid"]
        assert_valid_visit_response(
            v2,
            patient_uuid=patient_uuid,
            visit_type_uuid=visit_type_uuid,
            location_uuid=location_uuid,
        )
    else:
        assert r2.status_code in (400, 409, 500), r2.text
        assert any(
            k in (r2.text or "").lower()
            for k in ["overlap", "active", "visit", "already", "startdatetime"]
        )


# =====================================================================
# 3) FIELD VALIDATION: payload negative/positive + response(full) validation
# =====================================================================

@pytest.mark.parametrize(
    "bad_patient",
    [
        None,
        "",
        "not-a-uuid",
        123,
        str(uuid.uuid4()),  # uuid ok-form, likely non-existing -> 400/404/500
    ],
)
def test_create_visit_invalid_patient_field(patient_context: dict, visit_type_uuid: str, bad_patient):
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": bad_patient,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }

    resp = post_visit_raw(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)

    # для "uuid-like" допускаем 404
    if isinstance(bad_patient, str) and bad_patient and bad_patient.count("-") == 4:
        assert resp.status_code in (400, 404, 500), resp.text
    else:
        assert resp.status_code in (400, 500), resp.text

    assert any(k in (resp.text or "").lower() for k in ["patient", "uuid", "invalid", "not found"])


@pytest.mark.parametrize(
    "bad_visit_type",
    [
        None,
        "",
        "not-a-uuid",
        123,
        str(uuid.uuid4()),
    ],
)
def test_create_visit_invalid_visit_type_field(patient_context: dict, bad_visit_type):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": bad_visit_type,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }

    resp = post_visit_raw(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)
    assert resp.status_code in (400, 404, 500), resp.text
    assert any(k in (resp.text or "").lower() for k in ["visittype", "visit type", "uuid", "invalid", "not found"])


@pytest.mark.parametrize(
    "bad_start",
    [
        None,
        "",
        "2020-01-01",
        "01-01-2020T10:00:00.000Z",
        "not-a-date",
        123,
    ],
)
def test_create_visit_invalid_start_datetime(patient_context: dict, visit_type_uuid: str, bad_start):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": bad_start,
        "location": location_uuid,
    }

    resp = post_visit_raw(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)
    assert resp.status_code in (400, 500), resp.text
    assert any(k in (resp.text or "").lower() for k in ["startdatetime", "datetime", "date", "invalid"])


@pytest.mark.parametrize(
    "bad_stop",
    [
        "",
        "not-a-date",
        "2020-01-01",
        123,
    ],
)
def test_create_visit_invalid_stop_datetime_format(patient_context: dict, visit_type_uuid: str, bad_stop):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "stopDatetime": bad_stop,
        "location": location_uuid,
    }

    resp = post_visit_raw(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)
    assert resp.status_code in (400, 500), resp.text
    assert any(k in (resp.text or "").lower() for k in ["stopdatetime", "datetime", "date", "invalid"])


@pytest.mark.parametrize(
    "bad_location",
    [
        "",
        "abc",
        "10",
        123,
        str(uuid.uuid4()),
    ],
)
def test_create_visit_invalid_location(patient_context: dict, visit_type_uuid: str, bad_location):
    patient_uuid = patient_context["patient_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": bad_location,
    }

    resp = post_visit_raw(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)
    assert resp.status_code in (400, 404, 500), resp.text
    assert "location" in (resp.text or "").lower() or "uuid" in (resp.text or "").lower()


def test_create_visit_without_location_still_success(patient_context: dict, visit_type_uuid: str):
    """
    location часто OPTIONAL.
    Если у вас location обязателен — сделай этот тест негативным.
    """
    patient_uuid = patient_context["patient_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
    }

    resp = post_visit_raw(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)

    if resp.status_code != 201:
        pytest.fail(
            "Ожидали успешное создание визита без location, "
            f"но получили {resp.status_code}. "
            "Если в вашем инстансе location обязателен — поменяй ожидание.\n"
            f"Body: {(resp.text or '')[:2000]}"
        )

    data = resp.json()
    assert isinstance(data, dict)
    assert isinstance(data.get("uuid"), str) and data["uuid"]


def test_create_visit_full_representation_has_expected_fields(patient_context: dict, visit_type_uuid: str):
    """
    Проверяем поля ответа в full representation мягко:
    - uuid, startDatetime обязательны
    - patient/visitType существуют
    - encounters/auditInfo если присутствуют — корректных типов
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    resp = create_visit(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        start_datetime_iso=iso_utc(datetime.now(timezone.utc)),
        location_uuid=location_uuid,
    )
    assert resp.status_code == 201, resp.text
    visit = resp.json()

    full = fetch_visit_full(username=ADMIN_USERNAME, password=ADMIN_PASSWORD, visit_uuid=visit["uuid"])

    assert isinstance(full, dict)
    assert isinstance(full.get("uuid"), str) and full["uuid"]
    assert "startDatetime" in full and isinstance(full["startDatetime"], str) and full["startDatetime"].strip()

    assert full.get("patient") is not None
    assert full.get("visitType") is not None

    if "encounters" in full:
        assert isinstance(full["encounters"], list)

    if "auditInfo" in full:
        assert isinstance(full["auditInfo"], dict)
        assert any(k in full["auditInfo"] for k in ["creator", "createdBy", "dateCreated"])
