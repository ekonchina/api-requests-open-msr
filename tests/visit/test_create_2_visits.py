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

def test_create_second_active_visit_overlapping(patient_context: dict, visit_type_uuid: str):

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

    assert r2.status_code in (400), r2.text
    assert any(
        k in (r2.text or "").lower()
        for k in ["overlap", "active", "visit", "already", "startdatetime"]
    )