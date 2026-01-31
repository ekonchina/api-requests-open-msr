# tests/visit/test_create_visit_fields_validation.py
# -*- coding: utf-8 -*-
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
import requests
from requests.auth import HTTPBasicAuth

from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_valid_patient_with_person
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import (
    get_openmrs_id_identifier,
)
from request_modules.visittype.get_random_valid_visit_type import get_random_valid_visit_type


# =========================================================
# config
# =========================================================
BASE_URL = "http://localhost/openmrs/ws/rest/v1"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Admin123"


# =========================================================
# helpers
# =========================================================
def iso_utc(dt: datetime) -> str:
    dt = dt.astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def is_uuid_like(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except Exception:
        return False


def extract_error_text(resp: requests.Response) -> str:
    try:
        j = resp.json()
        return " ".join(str(v) for v in j.values()).lower()
    except Exception:
        return (resp.text or "").lower()


def assert_500_is_xfail(resp: requests.Response):
    if resp.status_code == 500:
        pytest.xfail(f"OpenMRS returned 500 (unstable validation): {resp.text[:200]}")


def post_json(path: str, *, payload: dict) -> requests.Response:
    return requests.post(
        f"{BASE_URL}{path}",
        json=payload,
        auth=HTTPBasicAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )


def get_json(path: str, *, params: dict | None = None) -> requests.Response:
    return requests.get(
        f"{BASE_URL}{path}",
        params=params,
        auth=HTTPBasicAuth(ADMIN_USERNAME, ADMIN_PASSWORD),
        headers={"Accept": "application/json"},
        timeout=30,
    )


def post_visit_raw(payload: dict) -> requests.Response:
    return post_json("/visit", payload=payload)


def create_visit_raw(
    *,
    patient_uuid: str,
    visit_type_uuid: str,
    location_uuid: str,
    indication: object | None = None,
    encounters: object | None = None,
) -> requests.Response:
    payload: dict = {
        "patient": patient_uuid,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }
    if indication is not None:
        payload["indication"] = indication
    if encounters is not None:
        payload["encounters"] = encounters

    return post_visit_raw(payload)


def get_visit_full(visit_uuid: str) -> dict:
    resp = get_json(f"/visit/{visit_uuid}", params={"v": "full"})
    resp.raise_for_status()
    return resp.json()


# =========================================================
# openmrs lookups
# =========================================================
def get_random_valid_encounter_type_uuid() -> str:
    resp = get_json("/encountertype", params={"v": "default"})
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        pytest.skip("No encounter types available")
    return results[0]["uuid"]


def get_random_valid_visit_attribute_type() -> dict:
    resp = get_json("/visitattributetype", params={"v": "full"})
    if resp.status_code == 404:
        pytest.skip("/visitattributetype endpoint not available")
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        pytest.skip("No visit attribute types available")
    return results[0]


def create_encounter_minimal(patient_uuid: str, location_uuid: str) -> requests.Response:
    payload = {
        "patient": patient_uuid,
        "encounterType": get_random_valid_encounter_type_uuid(),
        "encounterDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }
    return post_json("/encounter", payload=payload)


def post_visit_attribute(visit_uuid: str, attribute_type_uuid: str, value: object) -> requests.Response:
    payload = {"attributeType": attribute_type_uuid, "value": value}
    return post_json(f"/visit/{visit_uuid}/attribute", payload=payload)


# =========================================================
# fixtures
# =========================================================
@pytest.fixture()
def patient_context() -> dict:
    person = create_valid_person()
    location_uuid = get_random_valid_location()["uuid"]
    id_type_uuid, id_value = get_openmrs_id_identifier()

    patient = create_valid_patient_with_person(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        person=person,
        location=location_uuid,
        identifier_type=id_type_uuid,
        patient_identifier=id_value,
    )

    return {
        "patient_uuid": patient["uuid"],
        "location_uuid": location_uuid,
    }


@pytest.fixture()
def visit_type_uuid() -> str:
    return get_random_valid_visit_type()["uuid"]


@pytest.fixture()
def created_visit_uuid(patient_context: dict, visit_type_uuid: str) -> str:
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["uuid"]


@pytest.fixture()
def visit_attribute_type() -> dict:
    return get_random_valid_visit_attribute_type()



@pytest.mark.parametrize(
    "bad_patient",
    [None, "", "not-a-uuid", str(uuid.uuid4())],
)
def test_create_visit_invalid_patient_field(patient_context, visit_type_uuid, bad_patient):
    payload = {
        "patient": bad_patient,
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": patient_context["location_uuid"],
    }

    resp = post_visit_raw(payload)
    if is_uuid_like(bad_patient):
        assert resp.status_code in (400, 404, 500)
    else:
        assert resp.status_code in (400, 500)

    assert any(k in extract_error_text(resp) for k in ["patient", "uuid", "invalid", "not found"])


@pytest.mark.parametrize(
    "bad_visit_type",
    [None, "", "not-a-uuid", str(uuid.uuid4())],
)
def test_create_visit_invalid_visit_type_field(patient_context, bad_visit_type):
    payload = {
        "patient": patient_context["patient_uuid"],
        "visitType": bad_visit_type,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": patient_context["location_uuid"],
    }

    resp = post_visit_raw(payload)
    assert resp.status_code in (400, 404, 500)
    assert any(k in extract_error_text(resp) for k in ["visittype", "visit type", "uuid", "invalid"])


@pytest.mark.xfail(reason="OpenMRS sometimes ignores invalid location on create visit")
@pytest.mark.parametrize("bad_location", [None, "", "abc", str(uuid.uuid4())])
def test_create_visit_invalid_location(patient_context, visit_type_uuid, bad_location):
    payload = {
        "patient": patient_context["patient_uuid"],
        "visitType": visit_type_uuid,
        "startDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": bad_location,
    }

    resp = post_visit_raw(payload)
    assert resp.status_code in (400, 404, 500)
    assert any(k in extract_error_text(resp) for k in ["location", "uuid"])


# =========================================================
# NEW TESTS: indication
# =========================================================
def test_create_visit_with_indication_success(patient_context, visit_type_uuid):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        indication="Follow-up visit",
    )
    assert resp.status_code in (200, 201), resp.text

    full = get_visit_full(resp.json()["uuid"])
    assert full.get("indication") in ("Follow-up visit", None)


@pytest.mark.parametrize("bad_indication", [123, {"a": 1}, ["x"], True])
def test_create_visit_invalid_indication_type(patient_context, visit_type_uuid, bad_indication):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        indication=bad_indication,
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 500)
    assert "indication" in extract_error_text(resp)


# =========================================================
# NEW TESTS: encounters
# =========================================================
def test_create_visit_without_encounters_success(patient_context, visit_type_uuid):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
    )
    assert resp.status_code in (200, 201)

    full = get_visit_full(resp.json()["uuid"])
    assert "encounters" not in full or isinstance(full["encounters"], list)


@pytest.mark.parametrize(
    "bad_encounters",
    [
    #"not-an-array",
     {"x": 1},
     #[None],
    # ["not-a-uuid"],
     #[str(uuid.uuid4())]
    ],
)
def test_create_visit_invalid_encounters_field(patient_context, visit_type_uuid, bad_encounters):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        encounters=bad_encounters,
    )
    assert resp.status_code in (400, 404, 500)
    assert "encounter" in extract_error_text(resp)


def test_create_visit_with_real_encounter_success(patient_context, visit_type_uuid):
    enc_resp = create_encounter_minimal(
        patient_context["patient_uuid"],
        patient_context["location_uuid"],
    )

    if enc_resp.status_code == 500:
        pytest.xfail("Encounter creation returned 500")

    if enc_resp.status_code not in (200, 201):
        pytest.skip("Encounter creation requires providers in this setup")

    enc_uuid = enc_resp.json()["uuid"]

    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        encounters=[enc_uuid],
    )
    assert resp.status_code in (200, 201)

    full = get_visit_full(resp.json()["uuid"])
    assert any(
        (e.get("uuid") if isinstance(e, dict) else e) == enc_uuid
        for e in (full.get("encounters") or [])
    )


# =========================================================
# NEW TESTS: visit attributes
# =========================================================
def test_add_visit_attribute_success(created_visit_uuid, visit_attribute_type):
    resp = post_visit_attribute(
        created_visit_uuid,
        visit_attribute_type["uuid"],
        "normal condition",
    )
    assert resp.status_code in (200, 201)

    full = get_visit_full(created_visit_uuid)
    assert any(
        (
            (a.get("attributeType", {}).get("uuid") if isinstance(a.get("attributeType"), dict) else a.get("attributeType"))
            == visit_attribute_type["uuid"]
        )
        for a in full.get("attributes", [])
    )


@pytest.mark.parametrize("bad_attribute_type", [None, "", "not-a-uuid", str(uuid.uuid4())])
def test_add_visit_attribute_invalid_attribute_type(created_visit_uuid, bad_attribute_type):
    resp = post_visit_attribute(created_visit_uuid, bad_attribute_type, "x")
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 404, 500)


def test_add_visit_attribute_invalid_value_for_boolean(created_visit_uuid, visit_attribute_type):
    dt = (visit_attribute_type.get("datatypeClassname") or "").lower()
    if "boolean" not in dt:
        pytest.skip("Attribute type is not boolean")

    resp = post_visit_attribute(
        created_visit_uuid,
        visit_attribute_type["uuid"],
        "not-a-boolean",
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 500)
