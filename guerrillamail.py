import requests
import random
import string

BASE = "https://api.guerrillamail.com/ajax.php"

DOMAINS = [
    "guerrillamail.com", "guerrillamail.net", "guerrillamail.org",
    "guerrillamail.biz", "guerrillamail.de", "guerrillamail.info",
    "grr.la", "sharklasers.com", "spam4.me", "guerrillamailblock.com",
]


def _rand(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def get_domains():
    return DOMAINS


def create_account(address=None, password=None):
    # step 1: get a session token
    r = requests.get(BASE, params={"f": "get_email_address"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    sid = data["sid_token"]

    if address:
        user, domain = address.split("@") if "@" in address else (address, DOMAINS[0])
    else:
        user = _rand()
        domain = random.choice(DOMAINS)

    # step 2: set the desired username + domain
    r2 = requests.get(BASE, params={
        "f": "set_email_user",
        "email_user": user,
        "sid_token": sid,
        "lang": "en"
    }, timeout=10)
    r2.raise_for_status()
    data2 = r2.json()

    final_address = data2.get("email_addr", f"{user}@{domain}")

    return {
        "id": sid,          # guerrilla uses sid as session identifier
        "address": final_address,
        "password": "",     # guerrilla has no password — session-based
        "token": sid,
        "provider": "guerrilla",
    }


def get_token(address, password):
    # guerrilla is session-based; token == sid_token stored at creation
    return password  # we store sid in token field


def list_messages(token):
    r = requests.get(BASE, params={
        "f": "check_email",
        "seq": 0,
        "sid_token": token,
    }, timeout=10)
    r.raise_for_status()
    items = r.json().get("list", [])
    # normalize to same shape as mail.tm
    return [
        {
            "id": str(m["mail_id"]),
            "from": {"address": m.get("mail_from", "")},
            "subject": m.get("mail_subject", ""),
            "intro": m.get("mail_excerpt", ""),
            "createdAt": m.get("mail_date", ""),
        }
        for m in items
    ]


def read_message(token, message_id):
    r = requests.get(BASE, params={
        "f": "fetch_email",
        "email_id": message_id,
        "sid_token": token,
    }, timeout=10)
    r.raise_for_status()
    m = r.json()
    return {
        "id": str(m.get("mail_id", message_id)),
        "from": {"address": m.get("mail_from", "")},
        "subject": m.get("mail_subject", ""),
        "text": m.get("mail_body", ""),
        "html": m.get("mail_body", "") if m.get("content_type", "") == "text/html" else None,
        "createdAt": m.get("mail_date", ""),
    }


def delete_account_api(token, account_id):
    # guerrilla sessions expire automatically — no delete endpoint
    pass


def delete_message_api(token, message_id):
    requests.get(BASE, params={
        "f": "del_email",
        "email_ids[]": message_id,
        "sid_token": token,
    }, timeout=10)
