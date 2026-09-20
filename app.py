from flask import Flask, render_template, request, jsonify
from datetime import date

import database
import finance
import agent
import ollama_client


app = Flask(__name__)

database.initialize_database()


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/api/dashboard")
def dashboard():

    month = request.args.get("month")

    totals = database.get_totals(month)

    category_totals = database.get_category_totals(
        month=month,
        transaction_type="expense"
    )

    income = totals["income"]
    expenses = totals["expenses"]
    surplus = totals["surplus"]

    savings_rate = finance.calculate_savings_rate(
        income,
        expenses
    )

    categories = []

    for category, amount in category_totals:

        categories.append({
            "category": category,
            "amount": amount
        })

    return jsonify({
        "income": income,
        "expenses": expenses,
        "surplus": surplus,
        "savings_rate": savings_rate,
        "categories": categories
    })


# ============================================================
# TRANSACTIONS - GET
# ============================================================

@app.route("/api/transactions", methods=["GET"])
def get_transactions():

    month = request.args.get("month")
    transaction_type = request.args.get("type")
    category = request.args.get("category")

    rows = database.get_transactions(
        month=month,
        transaction_type=transaction_type,
        category=category
    )

    transactions = []

    for row in rows:

        transactions.append({
            "id": row[0],
            "type": row[1],
            "category": row[2],
            "amount": row[3],
            "description": row[4],
            "date": row[5]
        })

    return jsonify(transactions)


# ============================================================
# TRANSACTIONS - ADD
# ============================================================

@app.route("/api/transactions", methods=["POST"])
def add_transaction():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No data received."
        }), 400

    transaction_type = data.get("type")
    category = data.get("category")
    amount = data.get("amount")
    description = data.get(
        "description",
        ""
    )
    transaction_date = data.get("date")

    if transaction_type not in [
        "income",
        "expense"
    ]:
        return jsonify({
            "success": False,
            "error": "Invalid transaction type."
        }), 400

    if not category:
        return jsonify({
            "success": False,
            "error": "Category is required."
        }), 400

    try:
        amount = float(amount)
    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "error": "Amount must be a number."
        }), 400

    if amount <= 0:

        return jsonify({
            "success": False,
            "error": "Amount must be greater than zero."
        }), 400

    if not transaction_date:
        transaction_date = date.today().isoformat()

    database.add_transaction(
        transaction_type=transaction_type,
        category=category,
        amount=amount,
        description=description,
        transaction_date=transaction_date
    )

    return jsonify({
        "success": True,
        "message": "Transaction added successfully."
    })


# ============================================================
# TRANSACTION DELETE
# ============================================================

@app.route(
    "/api/transactions/<int:transaction_id>",
    methods=["DELETE"]
)
def delete_transaction(transaction_id):

    database.delete_transaction(
        transaction_id
    )

    return jsonify({
        "success": True,
        "message": "Transaction deleted."
    })


# ============================================================
# GOALS - GET
# ============================================================

@app.route("/api/goals", methods=["GET"])
def get_goals():

    rows = database.get_goals()

    goals = []

    for row in rows:

        goal_id = row[0]
        name = row[1]
        target = float(row[2])
        saved = float(row[3])
        monthly = float(row[4])
        deadline = row[5]

        percentage = 0

        if target > 0:
            percentage = (
                saved / target
            ) * 100

        months = finance.calculate_goal_months(
            target,
            saved,
            monthly
        )

        goals.append({
            "id": goal_id,
            "name": name,
            "target": target,
            "saved": saved,
            "monthly": monthly,
            "deadline": deadline,
            "percentage": percentage,
            "months_remaining": months
        })

    return jsonify(goals)


# ============================================================
# GOALS - ADD
# ============================================================

@app.route("/api/goals", methods=["POST"])
def add_goal():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No data received."
        }), 400

    name = data.get("name")
    target = data.get("target")
    saved = data.get("saved", 0)
    monthly = data.get("monthly", 0)
    deadline = data.get("deadline")

    if not name:

        return jsonify({
            "success": False,
            "error": "Goal name is required."
        }), 400

    try:
        target = float(target)
        saved = float(saved)
        monthly = float(monthly)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "error": "Goal amounts must be numbers."
        }), 400

    if target <= 0:

        return jsonify({
            "success": False,
            "error": "Target amount must be greater than zero."
        }), 400

    if saved < 0 or monthly < 0:

        return jsonify({
            "success": False,
            "error": "Amounts cannot be negative."
        }), 400

    database.add_goal(
        name=name,
        target_amount=target,
        saved_amount=saved,
        monthly_saving=monthly,
        deadline=deadline
    )

    return jsonify({
        "success": True,
        "message": "Goal added successfully."
    })


# ============================================================
# GOAL DELETE
# ============================================================

@app.route(
    "/api/goals/<int:goal_id>",
    methods=["DELETE"]
)
def delete_goal(goal_id):

    database.delete_goal(goal_id)

    return jsonify({
        "success": True,
        "message": "Goal deleted."
    })


# ============================================================
# EMI
# ============================================================

@app.route("/api/emi", methods=["POST"])
def calculate_emi():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No data received."
        }), 400

    try:
        principal = float(
            data.get("principal", 0)
        )

        annual_interest = float(
            data.get("annual_interest", 0)
        )

        months = int(
            data.get("months", 0)
        )

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "error": "Please enter valid numbers."
        }), 400

    if principal <= 0:

        return jsonify({
            "success": False,
            "error": "Principal must be greater than zero."
        }), 400

    if months <= 0:

        return jsonify({
            "success": False,
            "error": "Months must be greater than zero."
        }), 400

    if annual_interest < 0:

        return jsonify({
            "success": False,
            "error": "Interest cannot be negative."
        }), 400

    emi = finance.calculate_emi(
        principal,
        annual_interest,
        months
    )

    total_payment = finance.calculate_total_payment(
        emi,
        months
    )

    total_interest = finance.calculate_total_interest(
        emi,
        months,
        principal
    )

    return jsonify({
        "success": True,
        "principal": principal,
        "annual_interest": annual_interest,
        "months": months,
        "emi": emi,
        "total_payment": total_payment,
        "total_interest": total_interest
    })


# ============================================================
# WHAT IF
# ============================================================

@app.route("/api/whatif", methods=["POST"])
def what_if():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No data received."
        }), 400

    month = data.get("month")

    try:
        income_change = float(
            data.get("income_change", 0)
        )

        expense_change = float(
            data.get("expense_change", 0)
        )

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "error": "Changes must be numbers."
        }), 400

    totals = database.get_totals(
        month
    )

    result = finance.calculate_what_if(
        income=totals["income"],
        expenses=totals["expenses"],
        income_change=income_change,
        expense_change=expense_change
    )

    return jsonify({
        "success": True,
        **result
    })


# ============================================================
# AI
# ============================================================

@app.route("/api/ai", methods=["POST"])
def ai_assistant():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No data received."
        }), 400

    question = data.get(
        "question",
        ""
    ).strip()

    if not question:

        return jsonify({
            "success": False,
            "error": "Please enter a question."
        }), 400

    try:

        answer = agent.ask_finpilot(
            question
        )

        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ============================================================
# OLLAMA STATUS
# ============================================================

@app.route("/api/ollama")
def ollama_status():

    try:

        connected = (
            ollama_client.check_ollama()
        )

        models = (
            ollama_client.get_models()
        )

        return jsonify({
            "connected": connected,
            "models": models
        })

    except Exception as error:

        return jsonify({
            "connected": False,
            "models": [],
            "error": str(error)
        })


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print("                 FINPILOT WEB")
    print("=" * 60)
    print()
    print("Open in browser:")
    print("http://127.0.0.1:5000")
    print()
    print("Press CTRL+C to stop.")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )