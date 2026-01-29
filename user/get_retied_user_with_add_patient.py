import requests
from requests.auth import HTTPBasicAuth

#TODO: не работает - во
BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"

TARGET_PRIVILEGE = "Add Patients"


def get_retired_users(limit=100):
    url = f"{BASE_URL}/user"
    params = {
        "retired": "true",
        "v": "full",
        "limit": limit,
    }

    r = requests.get(
        url,
        params=params,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=10,
    )

    if not r.ok:
        print("HTTP:", r.status_code)
        print("URL :", r.url)
        print("BODY:", (r.text or "")[:2000])
        r.raise_for_status()

    return r.json().get("results", [])


def privilege_name(priv: dict) -> str:
    return priv.get("display") or priv.get("name") or ""


def role_name(role: dict) -> str:
    return role.get("display") or role.get("name") or "-"


def has_privilege(user: dict, target_priv: str) -> bool:
    for role in user.get("roles", []):
        for priv in role.get("privileges", []):
            if privilege_name(priv) == target_priv:
                return True
    return False


def roles_granting_privilege(user: dict, target_priv: str) -> str:
    granting = []
    for role in user.get("roles", []):
        role_privs = {
            privilege_name(p)
            for p in role.get("privileges", [])
            if privilege_name(p)
        }
        if target_priv in role_privs:
            granting.append(role_name(role))
    return ", ".join(granting) or "-"


def print_table(users):
    headers = ["Username", "Person", "Roles", "Granting roles", "User UUID", "Retired"]
    rows = []

    for user in users:
        if not has_privilege(user, TARGET_PRIVILEGE):
            continue

        person = user.get("person") or {}
        roles = ", ".join(role_name(r) for r in user.get("roles", [])) or "-"

        rows.append([
            user.get("username", "-"),
            person.get("display", "-"),
            roles,
            roles_granting_privilege(user, TARGET_PRIVILEGE),
            user.get("uuid", "-"),      # ← ЯВНО user UUID
            str(user.get("retired", "-")),
        ])

    if not rows:
        print(f"\nRetired пользователей с привилегией '{TARGET_PRIVILEGE}' не найдено.\n")
        return

    col_widths = [
        max(len(str(row[i])) for row in ([headers] + rows))
        for i in range(len(headers))
    ]

    def format_row(row):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * w for w in col_widths)

    print(f"\nRetired пользователи С привилегией '{TARGET_PRIVILEGE}': {len(rows)}\n")
    print(format_row(headers))
    print(separator)

    for row in rows:
        print(format_row(row))


if __name__ == "__main__":
    users = get_retired_users(limit=100)
    print_table(users)
