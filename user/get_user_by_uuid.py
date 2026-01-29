import json
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
API_USERNAME = "admin"
API_PASSWORD = "Admin123"

# 👇 просто меняешь здесь
USER_UUID = "45ce6c2e-dd5a-11e6-9d9c-0242ac150002"


def get_user(user_uuid: str) -> dict:
    """
    GET /user/{uuid}?v=full
    Возвращает весь JSON пользователя (full representation).
    """
    url = f"{BASE_URL}/user/{user_uuid}"
    params = {"v": "full"}

    r = requests.get(
        url,
        params=params,
        auth=HTTPBasicAuth(API_USERNAME, API_PASSWORD),
        headers={"Accept": "application/json"},
        timeout=15,
    )

    if not r.ok:
        print("HTTP:", r.status_code)
        print("URL :", r.url)
        print("BODY:", (r.text or "")[:4000])
        r.raise_for_status()

    return r.json()


if __name__ == "__main__":
    user_data = get_user(USER_UUID)

    # красивый вывод всего объекта user
    print(json.dumps(user_data, ensure_ascii=False, indent=2))
