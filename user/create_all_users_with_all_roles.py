import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
auth = HTTPBasicAuth("admin", "Admin123")

ROLE_UUIDS = [
    "246f8412-01fb-4e55-86d7-6441cd1b81a5",
    "a142aa96-772a-4d09-b80c-b3a78687b189",
    "d8ddab2c-20a5-4a3c-b209-856c7fe839cd",
    "7f04f24c-e433-4bc7-95cd-975b6f003207",
    "66fa1ec4-5d30-4127-a693-d8b1f9519a14",
    "9873dba9-484f-42c2-a98d-f224bd65117a",
    "dc978fe8-b574-4e11-be54-626ae2d28ed8",
    "eba658df-fa88-4dab-b000-57e1e5cb2e43",
    "fb393086-d6ec-4bcb-a300-5815a554c4ae",
    "2d09a0e2-240a-4dd7-9c3e-9e2cd2cb2d1f",
    "58f60da3-03bd-4b57-bb3c-429b50f6939b",
    "564b560e-3fe8-4829-8be4-68ddb40cf106",
    "93a9c2f8-9296-488f-9451-43667e1c4d7f",
    "f7fd42ef-880e-40c5-972d-e4ae7c990de2",
    "2083fd40-3391-11ed-a667-507b9dea1806",
    "d210eb66-2188-11ed-9dff-507b9dea1806",
    "84bdd876-4694-11ed-8109-00155dcc3fc0",
    "cca4be4b-2188-11ed-9dff-507b9dea1806",
    "8ee2f2ac-467f-11ed-8109-00155dcc3fc0",
    "a49be648-6b0a-11ed-93a2-806d973f13a9",
    "4ef1f0f9-fee6-414b-910d-28e17df345c2",
    "2749cd1b-251a-4d8b-bc35-0165f2b1af3e",
    "fab43ac4-79bc-4f3d-805b-bd3a82ce41e9",
    "2f087f90-9c47-4262-bfce-23c7862e727e",
    "ab2160f6-0941-430c-9752-6714353fbd3c",
    "f089471c-e00b-468e-96e8-46aea1b339af",
    "8d94f280-c2cc-11de-8d13-0010c6dffd0f",
    "7d8d214d-2188-11ed-9dff-507b9dea1806",
    "8d94f852-c2cc-11de-8d13-0010c6dffd0f",
]

START_USER = 200  # user100


def create_user(user_number: int, role_uuid: str):
    payload = {
        "username": f"user{user_number}",
        "password": "Password123",
        "systemId": str(user_number),
        "person": {
            "names": [{"givenName": f"Demo{user_number}", "familyName": "User"}],
            "gender": "M",
            "birthdate": "1997-09-02",
        },
        # ✅ РОВНО ОДНА РОЛЬ на пользователя
        "roles": [{"uuid": role_uuid}],
    }

    r = requests.post(
        f"{BASE_URL}/user",
        json=payload,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        auth=auth,
        timeout=30,
    )

    print(f"user{user_number} (role {role_uuid}) -> status {r.status_code}")
    if r.status_code == 409:
        print("User already exists, skipping.\n")
        return

    print(r.text)
    r.raise_for_status()
    print()


if __name__ == "__main__":
    for i, role_uuid in enumerate(ROLE_UUIDS):
        user_number = START_USER + i
        create_user(user_number, role_uuid)
