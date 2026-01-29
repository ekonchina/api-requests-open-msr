import requests

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
AUTH = ("admin", "Admin123")

USERNAME_TO_RETIRE = "user224"
user_uuid = '288cd575-1134-46d5-aa1b-2e11d79ca13f'
REASON = "No longer active"
#user224  | Demo224 User | Privilege Level: Full | Privilege Level: Full | 288cd575-1134-46d5-aa1b-2e11d79ca13f | False

# найти uuid по username
r = requests.get(f"{BASE_URL}/user", auth=AUTH, params={"q": USERNAME_TO_RETIRE})
r.raise_for_status()
results = r.json().get("results", [])
if not results:
    raise RuntimeError(f"User '{USERNAME_TO_RETIRE}' not found")
user_uuid = results[0]["uuid"]

print("uuid:", user_uuid)

# retire через DELETE + reason
r = requests.delete(
    f"{BASE_URL}/user/{user_uuid}",
    auth=AUTH,
    params={"reason": REASON},
    headers={"Accept": "application/json"},
)

print("status:", r.status_code)
print(r.text)
r.raise_for_status()