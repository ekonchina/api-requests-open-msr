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
# 1) PERMISSIONS: create visit with users (has rights / no rights / retired / deleted)
# =====================================================================

# =====================================================================
# 1) PERMISSIONS: create visit with users
#    ✅ POSITIVE (parametrized)
#    ❌ NEGATIVE (parametrized)
# =====================================================================

@pytest.mark.parametrize(
    "username,password,comment",
    [
        #https://app.testiny.io/p/1/testcases/tcf/47/tc/104/
        ("user124", "Password123", "Full user should create visit"),
        #https://app.testiny.io/p/1/testcases/tcf/47/tc/105/
        ("user125", "Password123", "High user should create visit"),
        #https://app.testiny.io/p/1/testcases/tcf/47/tc/106/
        ("user220", "Password123", "Doctor might be allowed to create visits depending on roles"),
    ],
)
def test_create_visit_permissions_positive(
    patient_context: dict,
    visit_type_uuid: str,
    username: str,
    password: str,
    comment: str,
):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }

    resp = post_visit_raw(username=username, password=password, payload=payload)

    assert resp.status_code == 201, (
        f"{comment}\n"
        f"Expected 201, got {resp.status_code}\n"
        f"Body: {(resp.text or '')[:2000]}"
    )

    visit = resp.json()
    assert_valid_visit_response(
        visit,
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
    )


@pytest.mark.parametrize(
    "username,password,comment",
    [
        #https://app.testiny.io/p/1/testcases/tcf/47/tc/107/
        ("user215", "Password123", "User without visit privileges should be rejected"),
        #https://app.testiny.io/p/1/testcases/tcf/47/tc/108/
        ("user225", "Password123", "Retired/disabled user should be rejected"),
        #https://app.testiny.io/p/1/testcases/tcf/47/tc/109/
        ("deleted_user_does_not_exist_999", "Password123", "Non-existent (deleted) user should be rejected"),
    ],
)
def test_create_visit_permissions_negative(
    patient_context: dict,
    visit_type_uuid: str,
    username: str,
    password: str,
    comment: str,
):
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    payload = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }

    resp = post_visit_raw(username=username, password=password, payload=payload)

    # на разных инстансах может быть 401/403, а иногда 400 с сообщением "Privileges required"
    assert resp.status_code in (400, 401, 403), (
        f"{comment}\n"
        f"Expected rejection (400/401/403), got {resp.status_code}\n"
        f"Body: {(resp.text or '')[:2000]}"
    )

    text = (resp.text or "").lower()
    assert any(
        k in text
        for k in [
            "privilege",
            "privileges required",
            "not authorized",
            "unauthorized",
            "forbidden",
            "authentication",
            "access denied",
        ]
    ), f"{comment}\nBody did not look like auth/priv error:\n{text[:2000]}"


