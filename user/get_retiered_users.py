import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"


def get_active_users():
    url = f"{BASE_URL}/user"
    params = {
        "retired": "true",
        "v": "full",   # роли и привилегии есть только тут
        "limit": 100,
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


def extract_roles(user):
    roles = user.get("roles", [])
    return ", ".join(
        role.get("display", role.get("name", "-")) for role in roles
    ) or "-"


def extract_privileges(user):
    privileges = set()

    for role in user.get("roles", []):
        for priv in role.get("privileges", []):
            name = priv.get("display") or priv.get("name")
            if name:
                privileges.add(name)

    return ", ".join(sorted(privileges)) or "-"


def print_table(users):
    headers = ["Username", "Person", "Roles", "Privileges", "UUID", "Retired"]
    rows = []

    for user in users:
        person = user.get("person") or {}
        rows.append([
            user.get("username", "-"),
            person.get("display", "-"),
            extract_roles(user),
            extract_privileges(user),
            user.get("uuid", "-"),
            str(user.get("retired", "-")),
        ])

    col_widths = [
        max(len(str(row[i])) for row in ([headers] + rows))
        for i in range(len(headers))
    ]

    def format_row(row):
        return " | ".join(
            str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
        )

    separator = "-+-".join("-" * w for w in col_widths)

    print(f"\nАктивные пользователи: {len(rows)}\n")
    print(format_row(headers))
    print(separator)

    for row in rows:
        print(format_row(row))


if __name__ == "__main__":
    users = get_active_users()
    print_table(users)
