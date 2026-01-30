import uuid

import pytest

from checks.patient_checks import assert_valid_patient_response
from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_valid_patient_with_person, \
    create_in_valid_patient_with_person
from request_modules.find_patient.find_patient import find_patient_by_identifier
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import \
    get_identifier_type_with_generated_value, get_openmrs_id_identifier
from src.openmrs_patient import OpenMRSClient, PatientPayload, Person, PersonName, Address, Identifier






# TODO: генерировать такого пользователя
# - Privilege Level: Full (ab2160f6-0941-430c-9752-6714353fbd3c)
#   username: user124
#   password: Password123
# - Privilege Level: High (f089471c-e00b-468e-96e8-46aea1b339af)
#   username: user125
#   password: Password123


@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        ("user124", "Password123", "ab2160f6-0941-430c-9752-6714353fbd3c"),  # Full
        ("user125", "Password123", "f089471c-e00b-468e-96e8-46aea1b339af"),  # High
        ("user220", "Password123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),  # Doctor - not full, but add patient Privileges
    ]
)
def test_create_patient_with_user_have_asses_add_patient(username, password, privilege_level_uuid):
    identifier_type, patient_identifier = get_openmrs_id_identifier()
    location = get_random_valid_location()
    person: Person = create_valid_person()

    patient = create_valid_patient_with_person(
        username=username,
        password=password,
        location=location,
        identifier_type=identifier_type,
        patient_identifier=patient_identifier,
        person=person,
    )
    assert_valid_patient_response(patient)
    find_patient = find_patient_by_identifier(identifier=patient_identifier)
    assert patient == find_patient


#Создание пациента пользователем у которого есть нет прав на создание пациента
#- Inventory Clerk
#username: user220
#password: Password123
@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        ("user215", "Password123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),  # Full
    ]
)
def test_create_patient_with_user_have_no_asses_add_patient(username, password, privilege_level_uuid):
    identifier_type, patient_identifier = get_openmrs_id_identifier()
    location = get_random_valid_location()
    person: Person = create_valid_person()

    response = create_in_valid_patient_with_person(
        username=username,
        password=password,
        location=location,
        identifier_type=identifier_type,
        patient_identifier=patient_identifier,
        person=person,
    )
    assert response.status_code == 201
    message = response.json()["error"]["globalErrors"][0]["message"]
    assert 'Privileges required: Get Patients' in message



#Создание пациента пользователем у которого есть права на создание пациента но он disable
#- Inventory Clerk
#username: user220
#password: Password123
@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        ("user225", "Password123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),  # Full
    ]
)
def test_create_patient_with_user_have_no_asses_add_patient(username, password, privilege_level_uuid):
    identifier_type, patient_identifier = get_openmrs_id_identifier()
    location = get_random_valid_location()
    person: Person = create_valid_person()

    response = create_in_valid_patient_with_person(
        username=username,
        password=password,
        location=location,
        identifier_type=identifier_type,
        patient_identifier=patient_identifier,
        person=person,
    )

    assert response.status_code == 400

    assert "Privileges required: Get Identifier Types" in response.text

