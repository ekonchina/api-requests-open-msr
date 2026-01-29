import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
auth = HTTPBasicAuth("admin", "Admin123")

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}


def get_user_uuid(username: str) -> str | None:
    """Получить UUID пользователя по username"""
    r = requests.get(
        f"{BASE_URL}/user",
        params={"q": username},
        headers=HEADERS,
        auth=auth,
        timeout=30,
    )
    r.raise_for_status()

    results = r.json().get("results", [])
    if not results:
        return None

    return results[0]["uuid"]


def delete_user(username: str):
    user_uuid = get_user_uuid(username)

    if not user_uuid:
        print(f"❌ User '{username}' not found")
        return

    r = requests.delete(
        f"{BASE_URL}/user/{user_uuid}",
        headers=HEADERS,
        auth=auth,
        timeout=30,
    )

    if r.status_code in (200, 204):
        print(f"✅ User '{username}' deleted")
    else:
        print(f"⚠️ Failed to delete '{username}': {r.status_code}")
        print(r.text)


if __name__ == "__main__":
    delete_user("user11")
