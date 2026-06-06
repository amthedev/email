import requests
import random
import string
import json

BASE_URL = "https://api.mail.tm"


def _random_string(length=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def get_domains():
    r = requests.get(f"{BASE_URL}/domains")
    r.raise_for_status()
    return [d["domain"] for d in r.json()["hydra:member"]]


def create_account(address=None, password="Senha@1234"):
    if address is None:
        domains = get_domains()
        address = f"{_random_string()}@{domains[0]}"

    r = requests.post(f"{BASE_URL}/accounts", json={"address": address, "password": password})
    r.raise_for_status()
    return {"address": address, "password": password, "id": r.json()["id"]}


def get_token(address, password):
    r = requests.post(f"{BASE_URL}/token", json={"address": address, "password": password})
    r.raise_for_status()
    return r.json()["token"]


def list_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/messages", headers=headers)
    r.raise_for_status()
    return r.json()["hydra:member"]


def read_message(token, message_id):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/messages/{message_id}", headers=headers)
    r.raise_for_status()
    return r.json()


def delete_account(token, account_id):
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.delete(f"{BASE_URL}/accounts/{account_id}", headers=headers)
    r.raise_for_status()


# --- CLI simples ---

def cmd_new():
    acc = create_account()
    token = get_token(acc["address"], acc["password"])
    print(f"\nEmail criado: {acc['address']}")
    print(f"Senha:        {acc['password']}")
    print(f"ID:           {acc['id']}")
    print(f"Token:        {token}")
    save = input("\nSalvar em contas.json? (s/n): ").strip().lower()
    if save == "s":
        _save_account(acc, token)


def cmd_list_accounts():
    contas = _load_accounts()
    if not contas:
        print("Nenhuma conta salva.")
        return
    for i, c in enumerate(contas):
        print(f"[{i}] {c['address']}")


def cmd_check():
    contas = _load_accounts()
    if not contas:
        print("Nenhuma conta salva.")
        return
    cmd_list_accounts()
    idx = int(input("Número da conta: "))
    c = contas[idx]
    token = get_token(c["address"], c["password"])
    msgs = list_messages(token)
    if not msgs:
        print("Caixa vazia.")
        return
    for i, m in enumerate(msgs):
        print(f"[{i}] De: {m['from']['address']} | Assunto: {m['subject']}")
    idx2 = int(input("Número da mensagem para ler (Enter para pular): ") or -1)
    if idx2 >= 0:
        msg = read_message(token, msgs[idx2]["id"])
        print("\n--- Mensagem ---")
        print(f"De:      {msg['from']['address']}")
        print(f"Assunto: {msg['subject']}")
        print(f"\n{msg.get('text', msg.get('html', ''))}")


def cmd_delete():
    contas = _load_accounts()
    if not contas:
        print("Nenhuma conta salva.")
        return
    cmd_list_accounts()
    idx = int(input("Número da conta para deletar: "))
    c = contas[idx]
    token = get_token(c["address"], c["password"])
    delete_account(token, c["id"])
    contas.pop(idx)
    _write_accounts(contas)
    print(f"Conta {c['address']} deletada.")


def _save_account(acc, token):
    contas = _load_accounts()
    contas.append(acc)
    _write_accounts(contas)
    print("Salvo em contas.json")


def _load_accounts():
    try:
        with open("contas.json") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _write_accounts(contas):
    with open("contas.json", "w") as f:
        json.dump(contas, f, indent=2)


MENU = {
    "1": ("Criar novo email", cmd_new),
    "2": ("Ver contas salvas", cmd_list_accounts),
    "3": ("Checar mensagens", cmd_check),
    "4": ("Deletar conta", cmd_delete),
    "5": ("Sair", None),
}

if __name__ == "__main__":
    while True:
        print("\n=== mail.tm Manager ===")
        for k, (label, _) in MENU.items():
            print(f"  {k}. {label}")
        choice = input("Opção: ").strip()
        if choice == "5":
            break
        if choice in MENU:
            MENU[choice][1]()
        else:
            print("Opção inválida.")
