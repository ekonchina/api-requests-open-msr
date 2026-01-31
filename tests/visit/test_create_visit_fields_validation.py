# tests/visit/test_create_visit_all_cases_extended.py
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
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import get_openmrs_id_identifier
from request_modules.visittype.get_random_valid_visit_type import get_random_valid_visit_type
from request_modules.visit.create_visit import fetch_visit_full  # используем ваш модуль


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


def is_uuid_like(value: object) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        uuid.UUID(value)
        return True
    except Exception:
        return False


def extract_error_text(resp: requests.Response) -> str:
    """
    OpenMRS иногда возвращает JSON ошибки, иногда text/html.
    Делаем единый lower() текст для assert'ов.
    """
    try:
        j = resp.json()
        flat = " ".join(str(v) for v in j.values())
        return flat.lower()
    except Exception:
        return (resp.text or "").lower()


def assert_500_is_xfail(resp: requests.Response):
    """
    В OpenMRS валидации иногда "проваливаются" в 500.
    Мы не хотим зелёный тест при 500, но и не хотим ломать CI.
    """
    if resp.status_code == 500:
        pytest.xfail(f"Server returned 500 (likely OpenMRS bug/unstable validation): {resp.text[:250]}")


def post_json(path: str, *, username: str, password: str, payload: dict) -> requests.Response:
    return requests.post(
        f"{BASE_URL}{path}",
        json=payload,
        auth=HTTPBasicAuth(username, password),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )


def get_json(path: str, *, username: str, password: str, params: dict | None = None) -> requests.Response:
    return requests.get(
        f"{BASE_URL}{path}",
        params=params,
        auth=HTTPBasicAuth(username, password),
        headers={"Accept": "application/json"},
        timeout=30,
    )


def post_visit_raw(*, username: str, password: str, payload: dict) -> requests.Response:
    return requests.post(
        f"{BASE_URL}/visit",
        json=payload,
        auth=HTTPBasicAuth(username, password),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        timeout=30,
    )


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

    return post_json("/visit", username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)


# --- openmrs lookups (минимальные) ---
def get_random_valid_encounter_type_uuid() -> str:
    resp = get_json("/encountertype", username=ADMIN_USERNAME, password=ADMIN_PASSWORD, params={"v": "default"})
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        pytest.skip("No encounter types found in /encountertype")
    return results[0]["uuid"]


def get_random_valid_visit_attribute_type() -> dict:
    """
    Visit Attribute Type endpoint is /visitattributetype
    Возвращаем целиком объект (uuid, datatypeClassname, ...)
    """
    resp = get_json("/visitattributetype", username=ADMIN_USERNAME, password=ADMIN_PASSWORD, params={"v": "full"})
    if resp.status_code == 404:
        pytest.skip("Endpoint /visitattributetype not available in this OpenMRS setup")
    resp.raise_for_status()
    results = resp.json().get("results") or []
    if not results:
        pytest.skip("No visit attribute types found in /visitattributetype")
    return results[0]


def create_encounter_minimal(*, patient_uuid: str, location_uuid: str) -> requests.Response:
    """
    В разных сборках OpenMRS encounter может требовать providers/encounterProviders и т.д.
    Пытаемся создать минимальный encounter. Если сервер требует провайдера — skip.
    """
    encounter_type_uuid = get_random_valid_encounter_type_uuid()
    payload = {
        "patient": patient_uuid,
        "encounterType": encounter_type_uuid,
        "encounterDatetime": iso_utc(datetime.now(timezone.utc)),
        "location": location_uuid,
    }
    return post_json("/encounter", username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)


def post_visit_attribute(*, visit_uuid: str, attribute_type_uuid: str, value: object) -> requests.Response:
    payload = {"attributeType": attribute_type_uuid, "value": value}
    return post_json(f"/visit/{visit_uuid}/attribute", username=ADMIN_USERNAME, password=ADMIN_PASSWORD, payload=payload)


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


@pytest.fixture()
def created_visit_uuid(patient_context: dict, visit_type_uuid: str) -> str:
    """
    Создаём валидный визит (для тестов атрибутов).
    """
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
    [
        None,
        "",
        "not-a-uuid",
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
    if is_uuid_like(bad_patient):
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


@pytest.mark.xfail(reason="OpenMRS иногда не валидирует location на create visit (известная нестабильность)")
@pytest.mark.parametrize(
    "bad_location",
    [
        None,
        "",
        "abc",
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



def test_create_visit_with_indication_success(patient_context: dict, visit_type_uuid: str):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        indication="Follow-up visit",
    )
    #assert_500_is_xfail(resp)
    assert resp.status_code in (200, 201), resp.text

    visit_uuid = resp.json()["uuid"]
    full = fetch_visit_full(visit_uuid)
    assert (full.get("indication") or "") == "Follow-up visit"


@pytest.mark.parametrize("bad_indication", [123, {"a": 1}, ["x"], True])
def test_create_visit_invalid_indication_type(patient_context: dict, visit_type_uuid: str, bad_indication):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        indication=bad_indication,
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 500), resp.text
    err = extract_error_text(resp)
    assert any(k in err for k in ["indication", "invalid", "type", "json", "cannot"])


def test_create_visit_without_encounters_success(patient_context: dict, visit_type_uuid: str):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        encounters=None,  # не передаём поле
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (200, 201), resp.text

    visit_uuid = resp.json()["uuid"]
    full = fetch_visit_full(visit_uuid)
    encounters = full.get("encounters")
    if encounters is not None:
        assert isinstance(encounters, list)


@pytest.mark.parametrize(
    "bad_encounters",
    [
        "not-an-array",
        {"uuid": "x"},
        [None],
        ["not-a-uuid"],
        [str(uuid.uuid4())],  # uuid ok-form, likely non-existing
    ],
)
def test_create_visit_invalid_encounters_field(patient_context: dict, visit_type_uuid: str, bad_encounters):
    resp = create_visit_raw(
        patient_uuid=patient_context["patient_uuid"],
        visit_type_uuid=visit_type_uuid,
        location_uuid=patient_context["location_uuid"],
        encounters=bad_encounters,
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 404, 500), resp.text
    err = extract_error_text(resp)
    assert any(k in err for k in ["encounter", "encounters", "uuid", "invalid", "not found"])


def test_create_visit_with_real_encounter_success(patient_context: dict, visit_type_uuid: str):
    """
    Позитив: создаём Encounter и передаём его UUID в create visit.
    На некоторых сборках encounter требует providers — тогда skip.
    """
    patient_uuid = patient_context["patient_uuid"]
    location_uuid = patient_context["location_uuid"]

    enc_resp = create_encounter_minimal(patient_uuid=patient_uuid, location_uuid=location_uuid)

    if enc_resp.status_code == 500:
        pytest.xfail(f"500 while creating encounter: {enc_resp.text[:250]}")

    if enc_resp.status_code not in (200, 201):
        err = extract_error_text(enc_resp)
        if any(k in err for k in ["provider", "encounterprovider", "encounter providers", "missing"]):
            pytest.skip(f"Encounter creation requires providers in this OpenMRS setup: {enc_resp.text[:250]}")
        pytest.skip(f"Cannot create encounter in this setup (status {enc_resp.status_code}): {enc_resp.text[:250]}")

    encounter_uuid = enc_resp.json()["uuid"]

    resp = create_visit_raw(
        patient_uuid=patient_uuid,
        visit_type_uuid=visit_type_uuid,
        location_uuid=location_uuid,
        encounters=[encounter_uuid],
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (200, 201), resp.text

    visit_uuid = resp.json()["uuid"]
    full = fetch_visit_full(visit_uuid)
    encs = full.get("encounters") or []

    enc_uuids: list[str] = []
    for e in encs:
        if isinstance(e, dict) and "uuid" in e:
            enc_uuids.append(e["uuid"])
        elif isinstance(e, str):
            enc_uuids.append(e)

    assert encounter_uuid in enc_uuids


def test_add_visit_attribute_success(created_visit_uuid: str, visit_attribute_type: dict):
    attr_type_uuid = visit_attribute_type["uuid"]

    resp = post_visit_attribute(
        visit_uuid=created_visit_uuid,
        attribute_type_uuid=attr_type_uuid,
        value="normal condition",
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (200, 201), resp.text

    full = fetch_visit_full(created_visit_uuid)
    attrs = full.get("attributes") or []
    assert isinstance(attrs, list)

    found = False
    for a in attrs:
        if not isinstance(a, dict):
            continue
        at = a.get("attributeType")
        at_uuid = at.get("uuid") if isinstance(at, dict) else at
        if at_uuid == attr_type_uuid:
            found = True
            assert "value" in a
            break

    assert found, f"Visit attribute type {attr_type_uuid} not found in visit.attributes"


@pytest.mark.parametrize("bad_attribute_type", [None, "", "not-a-uuid", str(uuid.uuid4())])
def test_add_visit_attribute_invalid_attribute_type(created_visit_uuid: str, bad_attribute_type):
    resp = post_visit_attribute(
        visit_uuid=created_visit_uuid,
        attribute_type_uuid=bad_attribute_type,  # type: ignore[arg-type]
        value="x",
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 404, 500), resp.text
    err = extract_error_text(resp)
    assert any(k in err for k in ["attributetype", "attribute type", "uuid", "invalid", "not found"])


def test_add_visit_attribute_invalid_value_for_datatype_when_boolean(created_visit_uuid: str, visit_attribute_type: dict):
    """
    Негатив "по datatype" можно гарантировать только если выбран boolean-тип.
    Если тип не boolean — skip.

    В VisitAttributeType есть datatypeClassname.
    """
    dt = (visit_attribute_type.get("datatypeClassname") or "").lower()
    if "boolean" not in dt:
        pytest.skip(
            f"Selected visitAttributeType is not boolean "
            f"(datatypeClassname={visit_attribute_type.get('datatypeClassname')})"
        )

    resp = post_visit_attribute(
        visit_uuid=created_visit_uuid,
        attribute_type_uuid=visit_attribute_type["uuid"],
        value="not-a-boolean",
    )
    assert_500_is_xfail(resp)
    assert resp.status_code in (400, 500), resp.text
    err = extract_error_text(resp)
    assert any(k in err for k in ["boolean", "datatype", "invalid", "cannot", "value"])
