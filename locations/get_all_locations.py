import requests
from requests.auth import HTTPBasicAuth

# ==== НАСТРОЙКИ ====
BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"

URL = f"{BASE_URL}/location"

# ==== ЗАПРОС ====
response = requests.get(
    URL,
    auth=HTTPBasicAuth(USERNAME, PASSWORD),
    headers={"Accept": "application/json"}
)

response.raise_for_status()
data = response.json()

# ==== ВЫВОД ====
print("\n📍 Список локаций OpenMRS\n" + "=" * 40)

for idx, loc in enumerate(data.get("results", []), start=1):
    name = loc.get("name", "—")
    print(f"\n{idx}. {name}")
    print("-" * (len(name) + 4))
    print(f"UUID       : {loc.get('uuid')}")
    print(f"Описание  : {loc.get('description') or '—'}")
    print(f"Retired   : {loc.get('retired')}")

print("\n✅ Готово")
