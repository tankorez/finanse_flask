
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
import csv
from io import StringIO
from datetime import date

app = Flask(__name__)
app.secret_key = "finance-tracker-secret-key"
DB_NAME = "finance.db"

TYPE_RU = {"income": "Доход", "expense": "Расход"}
TYPE_DB = {"Доход": "income", "Расход": "expense"}

MONTHS_RU = {
    "01": "Январь", "02": "Февраль", "03": "Март", "04": "Апрель",
    "05": "Май", "06": "Июнь", "07": "Июль", "08": "Август",
    "09": "Сентябрь", "10": "Октябрь", "11": "Ноябрь", "12": "Декабрь"
}

CHART_COLORS = ["#3b82f6", "#22c55e", "#f97316", "#a855f7", "#64748b", "#ef4444", "#14b8a6", "#eab308"]


def db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def money(value):
    return f"{float(value):,.0f} ₸".replace(",", " ")


def ru_date(value):
    try:
        y, m, d = value.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return value


def month_label(month):
    if month == "all":
        return "Все"
    try:
        y, m = month.split("-")
        return f"{MONTHS_RU.get(m, m)} {y}"
    except Exception:
        return month


def get_months():
    conn = db()
    rows = conn.execute("SELECT DISTINCT substr(tr_date,1,7) AS m FROM transactions ORDER BY m DESC").fetchall()
    conn.close()
    months = [r["m"] for r in rows]
    return months or ["2026-05"]


def get_categories(kind=None):
    conn = db()
    if kind:
        rows = conn.execute("SELECT * FROM categories WHERE kind=? ORDER BY name", (kind,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM categories ORDER BY kind, name").fetchall()
    conn.close()
    return rows


def get_transactions(month="2026-05", kind=None, search=""):
    conn = db()
    q = "SELECT * FROM transactions WHERE 1=1"
    args = []
    if month and month != "all":
        q += " AND substr(tr_date,1,7)=?"
        args.append(month)
    if kind:
        q += " AND kind=?"
        args.append(kind)
    if search:
        q += " AND (description LIKE ? OR category LIKE ?)"
        args.extend([f"%{search}%", f"%{search}%"])
    q += " ORDER BY tr_date DESC, id DESC"
    rows = conn.execute(q, args).fetchall()
    conn.close()
    return rows


def totals(rows):
    income = sum(r["amount"] for r in rows if r["kind"] == "income")
    expense = sum(r["amount"] for r in rows if r["kind"] == "expense")
    return income, expense, income - expense


def expense_stats(rows):
    data = {}
    for r in rows:
        if r["kind"] == "expense":
            data[r["category"]] = data.get(r["category"], 0) + r["amount"]
    return data


def balance_points(rows):
    chronological = list(reversed(rows))
    balance = 0
    labels = []
    points = []
    for r in chronological:
        balance += r["amount"] if r["kind"] == "income" else -r["amount"]
        labels.append(ru_date(r["tr_date"])[:5])
        points.append(balance)
    return labels, points


def category_icon_map():
    return {c["name"]: c["icon"] or "" for c in get_categories()}


@app.context_processor
def inject_helpers():
    return dict(money=money, ru_date=ru_date, type_ru=TYPE_RU, month_label=month_label)


@app.route("/")
def index():
    month = request.args.get("month", get_months()[0])
    rows = get_transactions(month=month)
    income, expense, balance = totals(rows)
    stats = expense_stats(rows)
    labels, points = balance_points(rows)
    icon_map = category_icon_map()

    return render_template(
        "dashboard.html",
        active="dashboard",
        month=month,
        months=get_months(),
        rows=rows,
        recent=rows[:8],
        income=income,
        expense=expense,
        balance=balance,
        stats=stats,
        chart_colors=CHART_COLORS,
        balance_labels=labels,
        balance_points=points,
        icon_map=icon_map
    )


@app.route("/transactions")
def transactions():
    month = request.args.get("month", "all")
    kind = request.args.get("kind") or None
    search = request.args.get("search", "")
    rows = get_transactions(month=month, kind=kind, search=search)
    return render_template(
        "transactions.html",
        active="income" if kind == "income" else "expense" if kind == "expense" else "transactions",
        rows=rows,
        month=month,
        months=get_months(),
        kind=kind,
        search=search,
        categories=get_categories(),
        today=date.today().strftime("%Y-%m-%d")
    )


@app.post("/transaction/add")
def add_transaction():
    tr_date = request.form["tr_date"]
    description = request.form["description"].strip()
    category = request.form["category"]
    kind = TYPE_DB.get(request.form["kind"], request.form["kind"])
    amount = float(request.form["amount"].replace(" ", "").replace(",", "."))

    conn = db()
    conn.execute(
        "INSERT INTO transactions(tr_date, description, category, kind, amount) VALUES (?, ?, ?, ?, ?)",
        (tr_date, description, category, kind, amount)
    )
    conn.commit()
    conn.close()
    flash("Операция успешно добавлена", "success")
    return redirect(request.referrer or url_for("index"))


@app.post("/transaction/delete/<int:tr_id>")
def delete_transaction(tr_id):
    conn = db()
    conn.execute("DELETE FROM transactions WHERE id=?", (tr_id,))
    conn.commit()
    conn.close()
    flash("Операция удалена", "success")
    return redirect(request.referrer or url_for("transactions"))


@app.route("/categories")
def categories():
    return render_template("categories.html", active="categories", categories=get_categories())


@app.post("/category/add")
def add_category():
    name = request.form["name"].strip()
    kind = TYPE_DB.get(request.form["kind"], request.form["kind"])
    icon = request.form.get("icon", "").strip()
    if not name:
        flash("Введите название категории", "danger")
        return redirect(url_for("categories"))

    conn = db()
    try:
        conn.execute("INSERT INTO categories(name, kind, icon, icon_path) VALUES (?, ?, ?, '')", (name, kind, icon))
        conn.commit()
        flash("Категория добавлена", "success")
    except sqlite3.IntegrityError:
        flash("Такая категория уже существует", "danger")
    finally:
        conn.close()

    return redirect(url_for("categories"))


@app.post("/category/delete/<int:cat_id>")
def delete_category(cat_id):
    conn = db()
    cat = conn.execute("SELECT * FROM categories WHERE id=?", (cat_id,)).fetchone()
    if cat:
        used = conn.execute("SELECT COUNT(*) AS c FROM transactions WHERE category=?", (cat["name"],)).fetchone()["c"]
        if used:
            flash("Нельзя удалить категорию, которая используется в транзакциях", "danger")
        else:
            conn.execute("DELETE FROM categories WHERE id=?", (cat_id,))
            conn.commit()
            flash("Категория удалена", "success")
    conn.close()
    return redirect(url_for("categories"))


@app.route("/stats")
def stats():
    month = request.args.get("month", get_months()[0])
    rows = get_transactions(month=month)
    expense_data = expense_stats(rows)
    labels, points = balance_points(rows)
    return render_template(
        "stats.html",
        active="stats",
        month=month,
        months=get_months(),
        rows=rows,
        stats=expense_data,
        chart_colors=CHART_COLORS,
        balance_labels=labels,
        balance_points=points,
        icon_map=category_icon_map()
    )


@app.route("/about")
def about():
    return render_template("about.html", active="about")


@app.route("/settings")
def settings():
    return render_template("settings.html", active="settings")


@app.route("/export")
def export_csv():
    rows = get_transactions(month="all")
    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["Дата", "Описание", "Категория", "Тип", "Сумма"])
    for r in rows:
        writer.writerow([r["tr_date"], r["description"], r["category"], TYPE_RU.get(r["kind"], r["kind"]), r["amount"]])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=finance_export.csv"}
    )


if __name__ == "__main__":
    app.run(debug=True)
