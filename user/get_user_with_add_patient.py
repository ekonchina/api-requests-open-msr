import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost/openmrs/ws/rest/v1"
USERNAME = "admin"
PASSWORD = "Admin123"

TARGET_PRIVILEGE = "Add Patients"
SHOW_ALL_PRIVILEGES = False


def get_json(url, *, params=None, timeout=10):
    r = requests.get(
        url,
        params=params,
        auth=HTTPBasicAuth(USERNAME, PASSWORD),
        headers={"Accept": "application/json"},
        timeout=timeout,
    )
    if not r.ok:
        print("HTTP:", r.status_code)
        print("URL :", r.url)
        print("BODY:", (r.text or "")[:2000])
        r.raise_for_status()
    return r.json()


def get_active_users(limit=100):
    url = f"{BASE_URL}/user"
    params = {"retired": "false", "v": "full", "limit": limit}
    return get_json(url, params=params).get("results", [])


def get_current_session_location_display() -> str:
    """
    Возвращает локацию ТЕКУЩЕЙ сессии (то, что выбирают при логине в RefApp),
    если установлен модуль appui.
    """
    # Обрати внимание: appui - это НЕ под BASE_URL (/ws/rest/v1), но в том же REST-префиксе.
    url = BASE_URL.replace("/ws/rest/v1", "/ws/rest/v1/appui/session")
    data = get_json(url, params={"v": "full"})

    # Обычно структура содержит 'sessionLocation' (объект location) или похожее поле.
    loc = data.get("sessionLocation") or data.get("location") or {}
    if isinstance(loc, dict):
        return loc.get("display") or loc.get("name") or loc.get("uuid") or "-"
    return str(loc) if loc else "-"


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


def has_privilege(user: dict, target_priv: str) -> bool:
    return target_priv in extract_privileges_set(user)


def filter_users_with_privilege(users: list[dict], target_priv: str) -> list[dict]:
    return [u for u in users if has_privilege(u, target_priv)]


def print_table(users: list[dict], target_priv: str, session_location: str):
    if SHOW_ALL_PRIVILEGES:
        headers = ["Username", "Person", "Roles", "Granting roles", "Privileges", "User UUID"]
    else:
        headers = ["Username", "Person", "Roles", "Granting roles", "Priv count", "User UUID"]

    rows = []
    for user in users:
        person = user.get("person") or {}
        privs = sorted(extract_privileges_set(user))
        granting = roles_granting_privilege(user, target_priv)

        rows.append([
            user.get("username", "-"),
            person.get("display", "-"),
            extract_roles(user),
            granting,
            ", ".join(privs) if SHOW_ALL_PRIVILEGES else str(len(privs)),
            user.get("uuid", "-"),
        ])

    print(f"\nSession Location (для текущих кредов): {session_location}\n")

    if not rows:
        print(f"Пользователей с привилегией '{target_priv}' не найдено.\n")
        return

    col_widths = [max(len(str(row[i])) for row in ([headers] + rows)) for i in range(len(headers))]

    def format_row(row):
        return " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    separator = "-+-".join("-" * w for w in col_widths)

    print(f"Пользователи с привилегией '{target_priv}': {len(rows)}\n")
    print(format_row(headers))
    print(separator)
    for row in rows:
        print(format_row(row))


if __name__ == "__main__":
    session_loc = "-"
    try:
        session_loc = get_current_session_location_display()
    except requests.HTTPError:
        # если appui не установлен или запрещён доступ — просто покажем "-"
        session_loc = "-"

    users = get_active_users(limit=100)
    filtered = filter_users_with_privilege(users, TARGET_PRIVILEGE)
    print_table(filtered, TARGET_PRIVILEGE, session_loc)
