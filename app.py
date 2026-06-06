from flask import Flask, render_template, request, redirect, url_for, jsonify
import mailtm
import db

app = Flask(__name__)
db.init_db()


# ---------- helpers ----------

def _token(acc):
    token = acc["token"] if acc["token"] else None
    if not token:
        token = mailtm.get_token(acc["address"], acc["password"])
        db.update_token(acc["id"], token)
    return token


# ---------- pages ----------

@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    accounts = db.search_accounts(q) if q else db.get_all_accounts()
    stats = db.stats()
    return render_template("index.html", accounts=accounts, stats=stats, q=q)


@app.route("/create", methods=["POST"])
def create():
    address = request.form.get("address", "").strip() or None
    password = request.form.get("password", "Senha@1234").strip()
    acc = mailtm.create_account(address, password)
    token = mailtm.get_token(acc["address"], acc["password"])
    acc["token"] = token
    db.save_account(acc)
    return redirect(url_for("inbox", account_id=acc["id"]))


@app.route("/inbox/<account_id>")
def inbox(account_id):
    acc = db.get_account(account_id)
    if not acc:
        return redirect(url_for("index"))
    try:
        token = _token(acc)
        remote_msgs = mailtm.list_messages(token)
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
        token = _token(acc)
        msg = mailtm.read_message(token, message_id)
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
            token = _token(acc)
            remote_msgs = mailtm.list_messages(token)
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
            token = _token(acc)
            mailtm.delete_account_api(token, account_id)
        except Exception:
            pass
        db.delete_account_db(account_id)
    return redirect(url_for("index"))


@app.route("/delete-message/<account_id>/<message_id>", methods=["POST"])
def delete_message(account_id, message_id):
    acc = db.get_account(account_id)
    if acc:
        try:
            token = _token(acc)
            mailtm.delete_message_api(token, message_id)
        except Exception:
            pass
        db.delete_message_db(message_id)
    return redirect(url_for("inbox", account_id=account_id))


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    results = db.search_messages(q) if q else []
    return render_template("search.html", results=results, q=q)


# ---------- API JSON (para uso externo/scripts) ----------

@app.route("/api/accounts")
def api_accounts():
    return jsonify([dict(a) for a in db.get_all_accounts()])


@app.route("/api/create", methods=["POST"])
def api_create():
    data = request.json or {}
    acc = mailtm.create_account(data.get("address"), data.get("password", "Senha@1234"))
    token = mailtm.get_token(acc["address"], acc["password"])
    acc["token"] = token
    db.save_account(acc)
    return jsonify(acc)


@app.route("/api/messages/<account_id>")
def api_messages(account_id):
    return jsonify([dict(m) for m in db.get_messages(account_id)])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
