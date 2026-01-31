import uuid
import pytest

from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_in_valid_patient_with_person
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import (
    get_openmrs_id_identifier,
)
from src.openmrs_patient import Person


# TODO:
# В будущем можно заменить на реальный UUID локации,
# который был удалён/retired, если потребуется отдельный кейс.



# ============================================================
# Создание пациента с уже созданной Person
# и с НЕвалидными значениями location
# ============================================================

@pytest.mark.parametrize(
    "location",
    [   #https://app.testiny.io/p/1/testcases/tcf/41/tc/76
        # Сценарий: location отсутствует (null) / не задан.
        # Ожидаемый результат: OpenMRS отклоняет запрос на создание пациента → HTTP 400,
        #
        None,
        #https://app.testiny.io/p/1/testcases/tcf/41/tc/60
        # Сценарий: location передаётся как числовая строка
        # Ожидаемый результат: HTTP 400 (не UUID и не существующая локация)
        "10",

        #https://app.testiny.io/p/1/testcases/tcf/41/tc/62
        # Сценарий: location — произвольная строка
        # Ожидаемый результат: HTTP 400
        "abc",

        #https://app.testiny.io/p/1/testcases/tcf/41/tc/63
        # Сценарий: location — пустая строка
        # Ожидаемый результат: HTTP 400
        "",

        #https://app.testiny.io/p/1/testcases/tcf/41/tc/65
        # Сценарий: location имеет формат UUID,
        # но такого UUID НЕТ среди локаций OpenMRS
        # Ожидаемый результат: HTTP 400
        "b52ec6f9-0e26-424c-a4a1-c64f9d571eb3",
    ]
)
def test_create_patient_with_person_and_invalid_location(location):
    """
    Общий сценарий:
    Создать пациента с валидной Person и валидным identifier,
    но с НЕвалидным значением поля location.

    Ожидаемый результат:
    OpenMRS отклоняет запрос → HTTP 400,
    в тексте ответа присутствует упоминание location.
    """
    # Получаем UUID типа идентификатора OpenMRS ID
    # и валидное значение identifier
    identifier_type, patient_identifier = get_openmrs_id_identifier()

    # Создаём валидную Person
    person: Person = create_valid_person()

    # Пытаемся создать пациента с невалидной локацией
    response = create_in_valid_patient_with_person(
        username="admin",
        password="Admin123",
        location=location,
        identifier_type=identifier_type,
        patient_identifier=patient_identifier,
        person=person,
    )

    # Проверяем, что OpenMRS корректно отказал
    assert response.status_code == 400
    assert "location" in response.text.lower()
