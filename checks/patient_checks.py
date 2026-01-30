def assert_valid_patient_response(patient: dict) -> None:
    # --- patient ---
    assert isinstance(patient, dict)
    assert "uuid" in patient and isinstance(patient["uuid"], str)
    assert patient.get("voided") is False

    # --- person ---
    person = patient.get("person")
    assert isinstance(person, dict)

    assert "uuid" in person
    assert person["uuid"] == patient["uuid"]

    assert person.get("gender") in {"M", "F", "O", "U"}
    assert "birthdate" in person
    assert isinstance(person["birthdate"], str)

    preferred_name = person.get("preferredName")
    assert isinstance(preferred_name, dict)
    assert isinstance(preferred_name.get("display"), str)
    assert preferred_name["display"].strip() != ""

    # --- identifiers ---
    identifiers = patient.get("identifiers")
    assert isinstance(identifiers, list)
    assert len(identifiers) > 0

    openmrs_ids = [
        i for i in identifiers
        if "OpenMRS ID" in i.get("display", "")
    ]
    assert len(openmrs_ids) >= 1

    for identifier in openmrs_ids:
        assert "uuid" in identifier
        assert isinstance(identifier["uuid"], str)
        assert "display" in identifier
        assert isinstance(identifier["display"], str)