import uuid
import pytest

from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_in_valid_patient_with_person
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import get_openmrs_id_identifier


@pytest.mark.parametrize(
    "invalid_identifier_type",
    [
        # Сценарий: identifierType передан пустой строкой.
        # Ожидаемый результат: OpenMRS отклоняет запрос → HTTP 400,
        #                      в тексте ошибки есть упоминание identifierType/identifier type.
        "",

        # Сценарий: identifierType передан строкой из одних пробелов (trim/blank).
        # Ожидаемый результат: HTTP 400 + ошибка по identifierType.
        "    ",

        # Сценарий: identifierType передан строкой, не соответствующей формату UUID.
        # Ожидаемый результат: HTTP 400 + ошибка по identifierType.
        "not-a-uuid",

        # Сценарий: identifierType передан строкой некорректной длины (не UUID).
        # Ожидаемый результат: HTTP 400 + ошибка по identifierType.
        "12345",

        # Сценарий: identifierType имеет форму UUID, но такого типа идентификатора НЕ существует в системе.
        # Ожидаемый результат: HTTP 400 + ошибка по identifierType (ссылка на несуществующий ресурс).
        "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",

        # Сценарий: identifierType передан неверного типа (число вместо строки/UUID).
        # Ожидаемый результат: HTTP 400 + ошибка по identifierType.
        123456,
    ],
)
def test_create_patient_with_invalid_identifier_type(invalid_identifier_type):
    """
    Общий сценарий:
    Создать пациента по API /patient с уже созданной Person,
    с валидным значением identifier (patient_identifier),
    но подставить НЕвалидный identifierType.

    Ожидаемый результат:
    - OpenMRS НЕ создаёт пациента и возвращает HTTP 400.
    - В тексте ответа присутствует упоминание identifierType / identifier type.
    """
    # Берём валидный тип "OpenMRS ID" и валидное значение identifier.
    # В этом тесте валидное значение identifier мы сохраняем,
    # а ломаем только поле identifierType.
    valid_identifier_type, valid_patient_identifier = get_openmrs_id_identifier()

    # Берём случайную валидную локацию (в OpenMRS identifier обычно привязан к location)
    location = get_random_valid_location()

    # Создаём валидную Person заранее
    person = create_valid_person()

    # Пытаемся создать пациента с НЕвалидным identifierType
    response = create_in_valid_patient_with_person(
        username="admin",
        password="Admin123",
        location=location,
        identifier_type=invalid_identifier_type,
        patient_identifier=valid_patient_identifier,
        person=person,
    )

    # Ожидаем отказ валидации на стороне OpenMRS
    assert response.status_code == 400

    # Ожидаем, что API вернёт ошибку именно из-за неверного identifierType
    assert ("identifierType" in response.text) or ("identifier type" in response.text.lower())
