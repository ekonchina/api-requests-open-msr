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





import pytest

@pytest.mark.parametrize(
    "invalid_patient_identifier",
    [
        None,                       # null (missing value)
        "",                         # empty string
        "   ",                      # whitespace-only (trim/blank case)

        "a",                        # too short / минимальная длина (boundary)

        "MRN#123",                  # invalid characters (special char)
        "тест123",                  # non-ASCII / unicode

        "A" * 256,                  # too long (upper boundary / overflow risk)

        123456,                     # wrong type: int (serialization/type validation)
        [],                         # wrong type: list (non-scalar)
    ]
)
def test_create_patient_with_invalid_patient_identifier(invalid_patient_identifier):
    identifier_type, patient_identifier = get_openmrs_id_identifier()
    location = get_random_valid_location()
    person: Person = create_valid_person()

    response = create_in_valid_patient_with_person(
        username="admin",
        password="Admin123",
        location=location,
        identifier_type=identifier_type,
        patient_identifier=invalid_patient_identifier,
        person=person,
    )

    assert response.status_code == 400
    assert "identifier" in response.text or "Identifier" in response.text





