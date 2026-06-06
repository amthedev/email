from flask import Flask, render_template, request, redirect, url_for, jsonify
import mailtm
import guerrillamail
import db

app = Flask(__name__)
db.init_db()

PROVIDERS = {
    "mailtm": mailtm,
    "guerrilla": guerrillamail,
}


# ---------- helpers ----------

def _provider(acc):
    return PROVIDERS.get(acc["provider"] if acc["provider"] else "mailtm", mailtm)


def _token(acc):
    token = acc["token"] if acc["token"] else None
    if not token:
        p = _provider(acc)
        token = p.get_token(acc["address"], acc["password"])
        db.update_token(acc["id"], token)
    return token


def _all_domains():
    domains = []
    for name, p in PROVIDERS.items():
        for d in p.get_domains():
            domains.append({"provider": name, "domain": d})
    return domains


# ---------- pages ----------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    accounts = db.search_accounts(q) if q else db.get_all_accounts()
    stats = db.stats()
    domains = _all_domains()
    return render_template("index.html", accounts=accounts, stats=stats, q=q, domains=domains)


@app.route("/create", methods=["POST"])
def create():
    provider_name = request.form.get("provider", "mailtm")
    address = request.form.get("address", "").strip() or None
    password = request.form.get("password", "Senha@1234").strip()

    p = PROVIDERS.get(provider_name, mailtm)
    acc = p.create_account(address, password)
    acc["provider"] = provider_name
    db.save_account(acc)
    return redirect(url_for("inbox", account_id=acc["id"]))


@app.route("/inbox/<account_id>")
def inbox(account_id):
    acc = db.get_account(account_id)
    if not acc:
        return redirect(url_for("index"))
    try:
        p = _provider(acc)
        token = _token(acc)
        remote_msgs = p.list_messages(token)
        db.save_messages(account_id, remote_msgs)
    except Exception:
        pass
    messages = db.get_messages(account_id)
    return render_template("inbox.html", acc=acc, messages=messages)


@app.route("/message/<account_id>/<message_id>")
def message(account_id, message_id):
    acc = db.get_account(account_id)
    if not acc:
        return redirect(url_for("index"))
    try:
        p = _provider(acc)
        token = _token(acc)
        msg = p.read_message(token, message_id)
        db.save_full_message(account_id, msg)
    except Exception:
        msg = None
    msgs = db.get_messages(account_id)
    selected = next((m for m in msgs if m["id"] == message_id), None)
    return render_template("inbox.html", acc=acc, messages=msgs, selected=selected, full_msg=msg)


@app.route("/refresh/<account_id>")
def refresh(account_id):
    acc = db.get_account(account_id)
    if acc:
        try:
            p = _provider(acc)
            token = _token(acc)
            remote_msgs = p.list_messages(token)
            db.save_messages(account_id, remote_msgs)
        except Exception:
            pass
    return redirect(url_for("inbox", account_id=account_id))


@app.route("/label/<account_id>", methods=["POST"])
def label(account_id):
    lbl = request.form.get("label", "")
    note = request.form.get("note", "")
    db.update_label(account_id, lbl, note)
    return redirect(url_for("inbox", account_id=account_id))


@app.route("/delete-account/<account_id>", methods=["POST"])
def delete_account(account_id):
    acc = db.get_account(account_id)
    if acc:
        try:
            p = _provider(acc)
            token = _token(acc)
            p.delete_account_api(token, account_id)
        except Exception:
            pass
        db.delete_account_db(account_id)
    return redirect(url_for("index"))


@app.route("/delete-message/<account_id>/<message_id>", methods=["POST"])
def delete_message(account_id, message_id):
    acc = db.get_account(account_id)
    if acc:
        try:
            p = _provider(acc)
            token = _token(acc)
            p.delete_message_api(token, message_id)
        except Exception:
            pass
        db.delete_message_db(message_id)
    return redirect(url_for("inbox", account_id=account_id))


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = db.search_messages(q) if q else []
    return render_template("search.html", results=results, q=q)


# ---------- API JSON ----------

@app.route("/api/accounts")
def api_accounts():
    return jsonify([dict(a) for a in db.get_all_accounts()])


@app.route("/api/domains")
def api_domains():
    return jsonify(_all_domains())


@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.json or {}
    provider_name = data.get("provider", "mailtm")
    p = PROVIDERS.get(provider_name, mailtm)
    acc = p.create_account(data.get("address"), data.get("password", "Senha@1234"))
    acc["provider"] = provider_name
    db.save_account(acc)
    return jsonify(acc)


@app.route("/api/messages/<account_id>")
def api_messages(account_id):
    return jsonify([dict(m) for m in db.get_messages(account_id)])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
