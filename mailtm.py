import requests
import random
import string

BASE = "https://api.mail.tm"


def _rand(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def get_domains():
    r = requests.get(f"{BASE}/domains", timeout=10)
    r.raise_for_status()
    return [d["domain"] for d in r.json()["hydra:member"]]


def create_account(address=None, password="Senha@1234"):
    if not address:
        domain = get_domains()[0]
        address = f"{_rand()}@{domain}"
    r = requests.post(f"{BASE}/accounts", json={"address": address, "password": password}, timeout=10)
    r.raise_for_status()
    return {"id": r.json()["id"], "address": address, "password": password}


def get_token(address, password):
    r = requests.post(f"{BASE}/token", json={"address": address, "password": password}, timeout=10)
    r.raise_for_status()
    return r.json()["token"]


def list_messages(token):
    r = requests.get(f"{BASE}/messages", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()
    return r.json()["hydra:member"]


def read_message(token, message_id):
    r = requests.get(f"{BASE}/messages/{message_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()
    return r.json()


def delete_account_api(token, account_id):
    r = requests.delete(f"{BASE}/accounts/{account_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()


def delete_message_api(token, message_id):
    r = requests.delete(f"{BASE}/messages/{message_id}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    r.raise_for_status()


def refresh_token(address, password):
    return get_token(address, password)
