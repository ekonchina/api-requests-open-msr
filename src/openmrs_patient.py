"""
openmrs_patient.py

Минимальный клиент OpenMRS REST API для integration-тестов.
BASE_URL зашит в OpenMRSClient.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

import requests
from requests.auth import HTTPBasicAuth


# -----------------------------
# dataclasses
# -----------------------------

@dataclass
class PersonName:
    givenName: str
    familyName: str
    middleName: Optional[str] = None


@dataclass
class Address:
    address1: str
    cityVillage: str
    country: str


@dataclass
class Person:
    names: List[PersonName]
    gender: str
    birthdate: str
    addresses: Optional[List[Address]] = None


@dataclass
class Identifier:
    identifier: str
    identifierType: str
    location: str
    preferred: bool = True


@dataclass
class PatientPayload:
    person: Person
    identifiers: List[Identifier]

    def to_dict(self) -> Dict:
        return asdict(self)


# -----------------------------
# client
# -----------------------------

class OpenMRSClient:
    """
    Простой клиент OpenMRS REST API.

    BASE_URL фиксирован под локальный OpenMRS.
    """

    BASE_URL = "http://localhost/openmrs/ws/rest/v1"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


    def __init__(self, username: str, password: str) -> None:
        self.auth = HTTPBasicAuth(username, password)


    def create_patient(self, payload: PatientPayload) -> Dict:
        resp = requests.post(
            f"{self.BASE_URL}/patient",
            headers=self.headers,
            json=payload.to_dict(),
            auth=self.auth,
        )

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"OpenMRS error {resp.status_code}: {resp.text}"
            )

        return resp.json()
