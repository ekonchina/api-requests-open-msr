import uuid
import pytest

from checks.patient_checks import assert_valid_patient_response
from request_modules.create_random_valid_person import create_valid_person
from request_modules.create_valid_patient_with_person import (
    create_valid_patient_with_person,
    create_in_valid_patient_with_person,
)
from request_modules.find_patient.find_patient import find_patient_by_identifier
from request_modules.locations.get_random_valid_location import get_random_valid_location
from request_modules.patientidentifiertype.get_random_valid_patient_identifier_type import (
    get_openmrs_id_identifier,
)
from src.openmrs_patient import Person


# ============================================================
# ТЕСТЫ АВТОРИЗАЦИИ/ПРАВ НА СОЗДАНИЕ ПАЦИЕНТА
# ============================================================



@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        # Сценарий:
        # Пользователь с уровнем привилегий Full создаёт пациента с валидной Person,
        # валидным OpenMRS ID и валидной location.
        #
        # Ожидаемый результат:
        # Создание пациента успешно (HTTP 201/200 внутри create_valid_patient_with_person),
        # ответ содержит валидную структуру пациента,
        # и пациента можно найти по identifier (GET /patient?q=...).
        ("user124", "Password123", "ab2160f6-0941-430c-9752-6714353fbd3c"),  # Full

        # Сценарий:
        # Пользователь с уровнем привилегий High создаёт пациента аналогично.
        #
        # Ожидаемый результат:
        # Создание пациента успешно, структура ответа валидна,
        # пациент находится по identifier.
        ("user125", "Password123", "f089471c-e00b-468e-96e8-46aea1b339af"),  # High

        # Сценарий:
        # Пользователь "Doctor" (не full), но с привилегиями Add Patients,
        # создаёт пациента.
        #
        # Ожидаемый результат:
        # Создание пациента успешно, структура ответа валидна,
        # пациент находится по identifier.
        ("user220", "Password123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),  # Doctor (Add Patients)
    ],
)
def test_create_patient_with_user_has_access_add_patient(username, password, privilege_level_uuid):
    """
    Общий сценарий:
    Проверяем, что пользователи с достаточными привилегиями могут создавать пациента.

    Ожидаемый результат:
    - Успешное создание пациента.
    - Ответ пациента проходит assert_valid_patient_response.
    - Пациент находится через поиск по identifier.
    """
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

    # Ожидаем валидную структуру пациента в ответе
    assert_valid_patient_response(patient)

    # Ожидаем, что пациента можно найти по identifier (GET /patient?q=identifier)
    found_patient = find_patient_by_identifier(identifier=patient_identifier)
    assert patient == found_patient


# ============================================================
# Создание пациента пользователем, у которого НЕТ прав на создание пациента
# ============================================================

@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        # Сценарий:
        # Пользователь без необходимых прав пытается создать пациента user215 - Inventory Clerk
        #
        # Ожидаемый результат:
        # Запрос должен быть отклонён из-за нехватки привилегий.

        ("user215", "Password123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),
    ]
)
def test_create_patient_with_user_has_no_access_add_patient(username, password, privilege_level_uuid):
    """
    Сценарий:
    Пользователь без прав Add Patients пытается создать пациента.

    Ожидаемый результат:
    - OpenMRS должен вернуть ошибку по привилегиям (обычно 401/403 или 400 с сообщением),
      и в сообщении должно быть указано, какие привилегии требуются.
    """
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

    # Ожидаемый результат по сценарию: НЕуспешно
    assert response.status_code == 400, (
        "Ожидали отказ по привилегиям, но получили успешное создание пациента.\n"
        f"Body: {(response.text or '')[:2000]}"
    )

    # Проверяем сообщение об ошибке (если структура такая)
    # В OpenMRS часто это будет 401/403, а тело зависит от инстанса.
    text = (response.text or "")
    assert "Privileges required" in text or "privilege" in text.lower()


# ============================================================
# Создание пациента пользователем, который disabled/retired (или сессия запрещена)
# ============================================================

@pytest.mark.parametrize(
    "username,password,privilege_level_uuid",
    [
        # Сценарий:
        # Пользователь потенциально имеет права, но аккаунт выключен/retired/disabled,
        # или в системе запрещены действия из-за статуса пользователя.
        #
        # Ожидаемый результат:
        # Ошибка (обычно 401/403/400) и сообщение о нехватке привилегий/доступа.
        ("user225", "Password123", "4ef1f0f9-fee6-414b-910d-28e17df345c2"),
    ]
)
def test_create_patient_with_disabled_user(username, password, privilege_level_uuid):
    """
    Сценарий:
    Пользователь (disabled/retired) пытается создать пациента.

    Ожидаемый результат:
    - Запрос отклонён (HTTP 400/401/403).
    - В тексте ответа есть сообщение о необходимых привилегиях
      (в данном тесте ожидается "Privileges required: Get Identifier Types").
    """
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

    # Ожидаем ошибку
    assert response.status_code == 400, (
        f"Ожидали отказ, но получили {response.status_code}\n"
        f"Body: {(response.text or '')[:2000]}"
    )

    # Ожидаем сообщение о необходимых привилегиях
    assert "Privileges required: Get Identifier Types" in (response.text or "")
