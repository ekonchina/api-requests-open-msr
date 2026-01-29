import uuid

from src.openmrs_patient import OpenMRSClient, PatientPayload, Person, PersonName, Address, Identifier

#Создание пациента пользователем у которого есть права на создание пациента
#Эти пользователи есть по умолчанию
#- Privilege Level: Full (ab2160f6-0941-430c-9752-6714353fbd3c)
#username: user124
#password: Password123
#- Privilege Level: High (f089471c-e00b-468e-96e8-46aea1b339af)
#username: user125
#password: Password123

#Создание пациента пользователем у которого есть нет прав на создание пациента
#Эти пользователи есть по умолчанию
#- Organizational: Doctor (4ef1f0f9-fee6-414b-910d-28e17df345c2)
#username: user220
#password: Password123


#Создание пациента пользователем у которого есть права на создание но он retied:
#user224
#password: Password123
#288cd575-1134-46d5-aa1b-2e11d79ca13f


# Локация LOCATION_UUID
# c удаленной локацией 6d49188b-2bdf-4c6e-bdff-7eeed3e15a64
# c существующей локацией 1ce1b7d4-c865-4178-82b0-5932e51503d6

# Локация IDENTIFIER_TYPE_UUID
# Required: True
# Required: False
# Name: SSN Format: ^[A-Z]{1}-[0-9]{7}$
# c существующей локацией 1ce1b7d4-c865-4178-82b0-5932e51503d6

#Create patient with new Person
#Create patient with existing Person



def test_create_patient_real():
    # --- config ---
    USERNAME = "admin"
    PASSWORD = "Admin123"

    IDENTIFIER_TYPE_UUID = "PUT-REAL-IDENTIFIER-TYPE-UUID"
    LOCATION_UUID = "PUT-REAL-LOCATION-UUID"

    # уникальный идентификатор, чтобы тесты не конфликтовали
    patient_identifier = f"TEST-{uuid.uuid4()}"

    client = OpenMRSClient(
        username=USERNAME,
        password=PASSWORD,
    )

    payload = PatientPayload(
        person=Person(
            names=[PersonName(givenName="Test", familyName="Patient")],
            gender="M",
            birthdate="1990-01-01",
            addresses=[
                Address(
                    address1="Integration test street",
                    cityVillage="TestCity",
                    country="TestLand",
                )
            ],
        ),
        identifiers=[
            Identifier(
                identifier=patient_identifier,
                identifierType=IDENTIFIER_TYPE_UUID,
                location=LOCATION_UUID,
            )
        ],
    )

    # --- real HTTP call ---
    result = client.create_patient(payload)

    # --- asserts ---
    assert "uuid" in result
    assert result["uuid"]
