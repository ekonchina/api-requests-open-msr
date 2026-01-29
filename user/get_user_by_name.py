import json
import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
API_USERNAME = "admin"
API_PASSWORD = "Admin123"

# 👇 просто меняешь здесь
TARGET_USERNAME = "doctor"


def get_user_by_username(username: str) -> dict:
    """
    GET /user/{username}?v=full
    Возвращает полный объект пользователя.
    """
    url = f"{BASE_URL}/user/{username}"
    params = {"v": "full"}

    r = requests.get(
        url,
        params=params,
        auth=HTTPBasicAuth(API_USERNAME, API_PASSWORD),
        headers={"Accept": "application/json"},
        timeout=15,
    )

    if r.status_code == 404:
        raise ValueError(f"Пользователь '{username}' не найден")

    if not r.ok:
        print("HTTP:", r.status_code)
        print("URL :", r.url)
        print("BODY:", (r.text or "")[:4000])
        r.raise_for_status()

    return r.json()


if __name__ == "__main__":
    user_data = get_user_by_username(TARGET_USERNAME)

    # красивый вывод ВСЕЙ информации о пользователе
    print(json.dumps(user_data, ensure_ascii=False, indent=2))
