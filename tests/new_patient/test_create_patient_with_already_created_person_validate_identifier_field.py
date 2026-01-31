import uuid
import pytest

from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import create_in_valid_patient_with_person
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import get_openmrs_id_identifier
from src.openmrs_patient import Person


@pytest.mark.parametrize(
    "invalid_patient_identifier",
    [
        #https://app.testiny.io/p/1/testcases/tcf/59
        # Сценарий: identifier отсутствует (null) / не задан.
        # Ожидаемый результат: OpenMRS отклоняет запрос на создание пациента → HTTP 400,
        #                      в тексте ошибки упоминается identifier.
        None,
        #https://app.testiny.io/p/1/testcases/tcf/51
        # Сценарий: identifier задан пустой строкой.
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        "",
        #https://app.testiny.io/p/1/testcases/tcf/52
        # Сценарий: identifier состоит только из пробелов (проверка trim/blank).
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        "   ",
        #https://app.testiny.io/p/1/testcases/tcf/53
        # Сценарий: identifier слишком короткий (пограничное значение по длине).
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        "a",
        #https://app.testiny.io/p/1/testcases/tcf/54
        # Сценарий: identifier содержит недопустимые символы (например #),
        #           проверка валидации по формату.
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        "MRN#123",
        #https://app.testiny.io/p/1/testcases/tcf/55
        # Сценарий: identifier содержит Unicode/не-ASCII символы (кириллица),
        #           проверка допустимого алфавита в идентификаторе.
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        "тест123",
        #https://app.testiny.io/p/1/testcases/tcf/56
        # Сценарий: identifier слишком длинный (проверка верхней границы длины / overflow risk).
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        "A" * 256,
        #https://app.testiny.io/p/1/testcases/tcf/57
        # Сценарий: identifier неправильного типа (int вместо строки),
        #           проверка сериализации/типов.
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        123456,
        #https://app.testiny.io/p/1/testcases/tcf/58
        # Сценарий: identifier неправильного типа (list вместо строки),
        #           проверка что значение должно быть скалярным.
        # Ожидаемый результат: HTTP 400 + ошибка про identifier.
        [],
    ],
)
def test_create_patient_with_invalid_patient_identifier(invalid_patient_identifier):
    """
    Сценарий (общий): создать пациента по API /patient с уже созданной Person,
    но подставить НЕвалидный patient identifier.

    Ожидаемый результат (общий): OpenMRS НЕ создаёт пациента и возвращает HTTP 400,
    в тексте ответа присутствует упоминание identifier/Identifier.
    """
    # Берём UUID типа идентификатора "OpenMRS ID" (и валидный пример значения),
    # но в тесте мы ПЕРЕЗАТРЁМ значение на invalid_patient_identifier.
    identifier_type, _valid_identifier = get_openmrs_id_identifier()

    # Берём случайную валидную локацию (в OpenMRS identifier обычно привязан к location)
    location = get_random_valid_location()

    # Создаём валидную Person заранее (сценарий: patient создаётся на базе уже созданной person)
    person: Person = create_valid_person()

    # Пытаемся создать пациента с НЕвалидным identifier
    response = create_in_valid_patient_with_person(
        username="admin",
        password="Admin123",
        location=location,
        identifier_type=identifier_type,
        patient_identifier=invalid_patient_identifier,
        person=person,
    )

    # Ожидаем отказ валидации на стороне OpenMRS
    assert response.status_code == 400
    assert "identifier" in response.text or "Identifier" in response.text
