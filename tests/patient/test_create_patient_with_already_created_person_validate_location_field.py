import uuid

import pytest
import uuid

from checks.patient_checks import assert_valid_patient_response
from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_in_valid_patient_with_person

from request_modules.find_patient.find_patient import find_patient_by_identifier
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import \
    get_identifier_type_with_generated_value, get_openmrs_id_identifier
from src.openmrs_patient import OpenMRSClient, PatientPayload, Person, PersonName, Address, Identifier






#TODO: location котрого не существует
@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        ("admin", "Admin123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),  # Full
    ]
)
def test_create_patient_with_person_and_random_location(username, password, privilege_level_uuid):
    identifier_type, patient_identifier = get_openmrs_id_identifier()
    location = str(uuid.uuid4())
    person: Person = create_valid_person()

    response = create_in_valid_patient_with_person(
        username=username,
        password=password,
        location=location,
        identifier_type=identifier_type,
        patient_identifier=patient_identifier,
        person=person,
    )



#Создание пациента c невалидной локацией
@pytest.mark.parametrize("location", [
    "10",
    " 10 ",
    "abc",
    "",
    "10.5",
    "b52ec6f9-0e26-424c-a4a1-c64f9d571eb3",
])
def test_create_patient_with_person_and_invalid_location(location):
    identifier_type, patient_identifier = get_openmrs_id_identifier()
    person: Person = create_valid_person()

    response = create_in_valid_patient_with_person(
        username="admin",
        password="Admin123",
        location=location,
        identifier_type=identifier_type,
        patient_identifier=patient_identifier,
        person=person,
    )

    assert response.status_code == 400
    assert "location" in response.text

