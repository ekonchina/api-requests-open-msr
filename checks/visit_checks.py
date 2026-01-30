# checks/visit_checks.py

def assert_valid_visit_response(visit: dict, *, patient_uuid: str, visit_type_uuid: str, location_uuid: str) -> None:
    assert isinstance(visit, dict)
    assert isinstance(visit.get("uuid"), str) and visit["uuid"]

    # common flags
    assert visit.get("voided") in (False, None)  # обычно False, но зависит от representation

    # patient
    patient = visit.get("patient")
    if isinstance(patient, dict):
        assert patient.get("uuid") == patient_uuid
    else:
        # иногда API возвращает строкой UUID в зависимости от v=...
        assert patient == patient_uuid

    # visitType
    vt = visit.get("visitType")
    if isinstance(vt, dict):
        assert vt.get("uuid") == visit_type_uuid
    else:
        assert vt == visit_type_uuid

    # startDatetime
    assert isinstance(visit.get("startDatetime"), str)
    assert visit["startDatetime"].strip() != ""

    # location (в примере payload присутствует; чаще всего ожидается в ответе)
    loc = visit.get("location")
    if loc is not None:
        if isinstance(loc, dict):
            assert loc.get("uuid") == location_uuid
        else:
            assert loc == location_uuid
