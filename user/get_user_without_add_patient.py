import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"

MISSING_PRIVILEGE = "Add Users"
SHOW_ALL_PRIVILEGES = False


def get_active_users(limit=100):
    url = f"{BASE_URL}/user"
    params = {
        "retired": "false",
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


def role_name(role: dict) -> str:
    return role.get("display") or role.get("name") or "-"


def privilege_name(priv: dict) -> str:
    return priv.get("display") or priv.get("name") or ""


def extract_roles(user: dict) -> str:
    return ", ".join(role_name(r) for r in user.get("roles", [])) or "-"


def extract_privileges_set(user: dict) -> set[str]:
    privs = set()
    for role in user.get("roles", []):
        for priv in role.get("privileges", []):
            name = privilege_name(priv)
            if name:
                privs.add(name)
    return privs


def roles_granting_privilege(user: dict, target_priv: str) -> str:
    granting = []
    for role in user.get("roles", []):
        role_privs = {privilege_name(p) for p in role.get("privileges", []) if privilege_name(p)}
        if target_priv in role_privs:
            granting.append(role_name(role))
    return ", ".join(granting) or "-"


def lacks_privilege(user: dict, missing_priv: str) -> bool:
    return missing_priv not in extract_privileges_set(user)


def filter_users_without_privilege(users: list[dict], missing_priv: str) -> list[dict]:
    return [u for u in users if lacks_privilege(u, missing_priv)]


def print_table(users: list[dict], missing_priv: str):
    if SHOW_ALL_PRIVILEGES:
        headers = ["Username", "Person", "Roles", "Has privilege via roles", "Privileges", "User UUID"]
    else:
        headers = ["Username", "Person", "Roles", "Has privilege via roles", "Priv count", "User UUID"]

    rows = []
    for user in users:
        person = user.get("person") or {}
        privs = sorted(extract_privileges_set(user))
        granting = roles_granting_privilege(user, missing_priv)

        rows.append([
            user.get("username", "-"),
            person.get("display", "-"),
            extract_roles(user),
            granting if granting != "-" else "❌ none",
            ", ".join(privs) if SHOW_ALL_PRIVILEGES else str(len(privs)),
            user.get("uuid", "-"),   # ← ЯВНО user UUID
        ])

    if not rows:
        print(f"\nВсе пользователи имеют привилегию '{missing_priv}'.\n")
        return

    col_widths = [
        max(len(str(row[i])) for row in ([headers] + rows))
        for i in range(len(headers))
    ]

    def format_row(row):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * w for w in col_widths)

    print(f"\nПользователи БЕЗ привилегии '{missing_priv}': {len(rows)}\n")
    print(format_row(headers))
    print(separator)
    for row in rows:
        print(format_row(row))


if __name__ == "__main__":
    users = get_active_users(limit=100)
    filtered = filter_users_without_privilege(users, MISSING_PRIVILEGE)
    print_table(filtered, MISSING_PRIVILEGE)
