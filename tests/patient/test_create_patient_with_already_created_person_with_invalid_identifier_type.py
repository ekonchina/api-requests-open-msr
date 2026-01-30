import uuid
import pytest

from checks.patient_checks import assert_valid_patient_response
from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_in_valid_patient_with_person

from request_modules.find_patient.find_patient import find_patient_by_identifier
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import get_openmrs_id_identifier


@pytest.mark.parametrize(
    "invalid_identifier_type",
    [
        "",                         # пустая строка
        "    ",                     # только пробелы
        "not-a-uuid",              # строка не соответствующая формату UUID
        "12345",                    # некорректная длина – не UUID
        "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",  # валидная UUID-форма, но несуществующий тип
        123456,                     # неверный тип: число
    ],
)
def test_create_patient_with_invalid_identifier_type(invalid_identifier_type):
    # valid identifier (значение для идентификатора оставляем валидным здесь)
    valid_identifier_type, valid_patient_identifier = get_openmrs_id_identifier()
    location = get_random_valid_location()
    person = create_valid_person()

    response = create_in_valid_patient_with_person(
        username="admin",
        password="Admin123",
        location=location,
        identifier_type=invalid_identifier_type,
        patient_identifier=valid_patient_identifier,
        person=person,
    )
    assert response.status_code == 400

    # ожидаем, что API вернёт ошибку из-за неверного identifierType
    # проверяем, что в теле есть сообщение об ошибке именно по identifierType
    assert "identifierType" in response.text or "identifier type" in response.text.lower()
