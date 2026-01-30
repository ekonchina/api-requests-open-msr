import random
import string
import re
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, Tuple

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


def generate_identifier_from_format(fmt: str) -> str:
    """
    Генерирует identifier_value для известного формата
    ^[A-Z]{1}-[0-9]{7}$
    """
    if fmt == "^[A-Z]{1}-[0-9]{7}$":
        letter = random.choice(string.ascii_uppercase)
        digits = "".join(random.choices(string.digits, k=7))
        return f"{letter}-{digits}"

    raise ValueError(f"Unsupported identifier format: {fmt}")


def get_identifier_type_with_generated_value() -> Optional[Tuple[str, str]]:
    """
    Возвращает (identifier_type_uuid, generated_identifier_value)
    """
    url = f"{BASE_URL}/patientidentifiertype"

    response = requests.get(
        url,
        params={"v": "default"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"}
    )
    response.raise_for_status()

    data = response.json()

    for item in data.get("results", []):
        fmt = item.get("format")
        if not fmt:
            continue

        identifier_value = generate_identifier_from_format(fmt)

        # финальная проверка (на всякий случай)
        if re.fullmatch(fmt, identifier_value):
            return item["uuid"], identifier_value

    return None

def generate_random_openmrs_identifier(length: int = 8) -> str:
    """
    Генерирует простой клиентский OpenMRS identifier
    (цифры, без проверки Luhn)
    """
    return "".join(random.choices(string.digits, k=length))



MOD30_ALPHABET = "0123456789ACDEFGHJKLMNPRTUVWXY"
MOD30_MAP = {c: i for i, c in enumerate(MOD30_ALPHABET)}

def _luhn_mod30_sum(chars: str, *, start_double: bool) -> int:
    total = 0
    double = start_double
    for ch in reversed(chars):
        if ch not in MOD30_MAP:
            raise ValueError(f"Unallowed character '{ch}' for OpenMRS Mod30")
        v = MOD30_MAP[ch]
        if double:
            v *= 2
            # "сумма цифр" в базе 30
            v = (v // 30) + (v % 30)
        total += v
        double = not double
    return total

def luhn_mod30_check_char(payload: str) -> str:
    # ВАЖНО: для payload начинаем с удвоения справа,
    # потому что в полном ID справа будет check digit (не удваивается),
    # а ближайший слева символ (правый символ payload) удваивается.
    total = _luhn_mod30_sum(payload, start_double=True)
    check_val = (30 - (total % 30)) % 30
    return MOD30_ALPHABET[check_val]

def generate_openmrs_id(payload_length: int = 7) -> str:
    payload = "".join(random.choices(MOD30_ALPHABET, k=payload_length))
    return payload + luhn_mod30_check_char(payload)

def get_openmrs_id_identifier() -> Tuple[str, str]:
    """
    Возвращает (uuid типа 'OpenMRS ID', generated_identifier_value),
    где identifier_value проходит LuhnMod30IdentifierValidator.
    """
    url = f"{BASE_URL}/patientidentifiertype"
    resp = requests.get(
        url,
        params={"v": "default"},
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
    )
    resp.raise_for_status()

    for item in resp.json().get("results", []):
        if item.get("name") == "OpenMRS ID":
            return item["uuid"], generate_openmrs_id(payload_length=7)

    raise RuntimeError("PatientIdentifierType 'OpenMRS ID' not found")
