import requests
import random
import string
import re
import xml.etree.ElementTree as ET
from html import unescape

BASE = "https://mailnesia.com"
DOMAIN = "mailnesia.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; EmailManager/1.0)"}


def _rand(n=10):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _strip_html(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    text = unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def get_domains():
    return [DOMAIN]


def create_account(address=None, password=None):
    user = address.split("@")[0] if address and "@" in address else (address or _rand())
    full = f"{user}@{DOMAIN}"
    return {
        "id": user,           # user == id no mailnesia (sem registro)
        "address": full,
        "password": "",
        "token": user,        # token == username
        "provider": "mailnesia",
    }


def get_token(address, password):
    return address.split("@")[0]


def _get(url, retries=3):
    import time
    for i in range(retries):
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 503 and i < retries - 1:
            time.sleep(1.5)
            continue
        r.raise_for_status()
        return r
    return r


def list_messages(token):
    user = token.split("@")[0] if "@" in token else token
    r = _get(f"{BASE}/rss/{user}")

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return []

    msgs = []
    for item in root.findall(".//item"):
        title = item.findtext("title", "")
        link  = item.findtext("link", "")
        desc  = item.findtext("description", "")

        # título formato: "Assunto – De <email>"
        subject, from_addr = title, ""
        if " – " in title:
            parts = title.rsplit(" – ", 1)
            subject = parts[0].strip()
            from_part = parts[1].strip()
            m = re.search(r'<([^>]+)>', from_part)
            from_addr = m.group(1) if m else from_part

        msg_id = link.rsplit("/", 1)[-1] if link else _rand(8)
        body_text = _strip_html(desc)[:300] if desc else ""

        msgs.append({
            "id": msg_id,
            "from": {"address": from_addr},
            "subject": subject,
            "intro": body_text,
            "createdAt": "",
        })

    return msgs


def read_message(token, message_id):
    user = token.split("@")[0] if "@" in token else token
    r = _get(f"{BASE}/mailbox/{user}/{message_id}")
    html = r.text

    # extrair corpo
    m = re.search(rf'id="text_html_{message_id}"[^>]*>(.*?)</(?:div|span|p)', html, re.DOTALL)
    body = _strip_html(m.group(1)) if m else ""

    # extrair from / subject do header da página
    from_m   = re.search(r'From[:\s]*</td>\s*<td[^>]*>([^<]+)', html)
    subj_m   = re.search(r'Subject[:\s]*</td>\s*<td[^>]*>([^<]+)', html)
    date_m   = re.search(r'<time[^>]*datetime="([^"]+)"', html)

    return {
        "id": message_id,
        "from": {"address": from_m.group(1).strip() if from_m else ""},
        "subject": subj_m.group(1).strip() if subj_m else "",
        "text": body,
        "html": None,
        "createdAt": date_m.group(1) if date_m else "",
    }


def delete_account_api(token, account_id):
    pass  # mailnesia não tem registro — nada a deletar


def delete_message_api(token, message_id):
    user = token.split("@")[0] if "@" in token else token
    try:
        requests.get(f"{BASE}/mailbox/{user}/{message_id}/delete",
                     headers=HEADERS, timeout=10)
    except Exception:
        pass
