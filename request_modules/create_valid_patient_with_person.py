
import requests
from requests.auth import HTTPBasicAuth

from src.openmrs_patient import PatientPayload, Person, PersonName, Address, Identifier




def create_valid_patient_with_person(username:str, password: str, person: Person, location: str, identifier_type: str, patient_identifier: str):
    # --- config ---
    BASE_URL = "http://localhost/openmrs/ws/rest/v1"



    patient_identifier = patient_identifier


    payload = PatientPayload(
        person=person,
        identifiers=[
            Identifier(
                identifier=patient_identifier,
                identifierType=identifier_type,
                location=location,
            )
        ],
    )


    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


    auth = HTTPBasicAuth(username, password)


    resp = requests.post(
        f"{BASE_URL}/patient",
        headers=headers,
        json=payload.to_dict(),
        auth=auth,
    )

    assert resp.status_code == 201


    return resp.json()


def create_in_valid_patient_with_person(username:str, password: str, person: Person, location: str, identifier_type: str, patient_identifier: str):
    # --- config ---
    BASE_URL = "http://localhost/openmrs/ws/rest/v1"



    patient_identifier = patient_identifier


    payload = PatientPayload(
        person=person,
        identifiers=[
            Identifier(
                identifier=patient_identifier,
                identifierType=identifier_type,
                location=location,
            )
        ],
    )


    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


    auth = HTTPBasicAuth(username, password)


    resp = requests.post(
        f"{BASE_URL}/patient",
        headers=headers,
        json=payload.to_dict(),
        auth=auth,
    )

    assert resp.status_code == 400


    return resp

