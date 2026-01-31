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


# TC-110
# https://app.testiny.io/p/1/testcases/tcf/46/tc/110/
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


# TC-111
# https://app.testiny.io/p/1/testcases/tcf/46/tc/111/
def test_create_visit_in_far_future(patient_context: dict, visit_type_uuid: str):

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


# TC-112
# https://app.testiny.io/p/1/testcases/tcf/46/tc/112/
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


# TC-118, TC-119, TC-120, TC-121
# https://app.testiny.io/p/1/testcases/tcf/46/tc/118/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/119/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/120/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/121/
@pytest.mark.xfail
@pytest.mark.parametrize(
    "bad_start",
    [
        None,
        "",
        "2020-01-01",
        "01-01-2020T10:00:00.000Z",
        "not-a-date",
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


# TC-113, TC-114, TC-115, TC-116, TC-117
# https://app.testiny.io/p/1/testcases/tcf/46/tc/113/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/114/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/115/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/116/
# https://app.testiny.io/p/1/testcases/tcf/46/tc/117/
@pytest.mark.parametrize(
    "bad_stop",
    [
        None,
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
