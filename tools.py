import database
import finance
from collections import defaultdict


# ============================================================
# BASIC DATABASE HELPER
# ============================================================

def _transactions(
    month=None,
    transaction_type=None,
    category=None
):
    rows = database.get_transactions(
        month=month,
        transaction_type=transaction_type,
        category=category
    )

    result = []

    for row in rows:
        result.append({
            "id": row[0],
            "type": row[1],
            "category": row[2],
            "amount": float(row[3]),
            "description": row[4] or "",
            "date": row[5]
        })

    return result


# ============================================================
# 1. FINANCIAL SUMMARY
# ============================================================

def get_financial_summary(month=None):

    totals = database.get_totals(month)

    income = float(totals["income"])
    expenses = float(totals["expenses"])
    surplus = float(totals["surplus"])

    savings_rate = finance.calculate_savings_rate(
        income,
        expenses
    )

    return {
        "month": month,
        "income": income,
        "expenses": expenses,
        "surplus": surplus,
        "savings_rate": savings_rate
    }


# ============================================================
# 2. ALL TRANSACTIONS
# ============================================================

def get_all_transactions(
    month=None,
    category=None
):

    transactions = _transactions(
        month=month,
        category=category
    )

    return {
        "month": month,
        "category": category,
        "count": len(transactions),
        "transactions": transactions
    }


# ============================================================
# 3. INCOME
# ============================================================

def get_income(month=None):

    transactions = _transactions(
        month=month,
        transaction_type="income"
    )

    total = sum(
        transaction["amount"]
        for transaction in transactions
    )

    return {
        "month": month,
        "total": total,
        "count": len(transactions),
        "transactions": transactions
    }


# ============================================================
# 4. EXPENSES
# ============================================================

def get_expenses(
    month=None,
    category=None
):

    transactions = _transactions(
        month=month,
        transaction_type="expense",
        category=category
    )

    total = sum(
        transaction["amount"]
        for transaction in transactions
    )

    return {
        "month": month,
        "category": category,
        "total": total,
        "count": len(transactions),
        "transactions": transactions
    }


# ============================================================
# 5. CATEGORY BREAKDOWN
# ============================================================

def get_category_breakdown(month=None):

    rows = database.get_category_totals(
        month=month,
        transaction_type="expense"
    )

    categories = []

    for category, amount in rows:

        categories.append({
            "category": category,
            "amount": float(amount)
        })

    return {
        "month": month,
        "categories": categories
    }


# ============================================================
# 6. COMPLETE FINANCIAL BREAKDOWN
# ============================================================

def complete_financial_breakdown(
    month=None
):

    summary = get_financial_summary(month)

    category_data = get_category_breakdown(month)

    transactions = get_all_transactions(month)

    total_expenses = summary["expenses"]

    breakdown = []

    for item in category_data["categories"]:

        amount = float(item["amount"])

        percentage = 0

        if total_expenses > 0:
            percentage = (
                amount /
                total_expenses
            ) * 100

        breakdown.append({
            "category": item["category"],
            "amount": amount,
            "percentage": percentage
        })

    return {
        "month": month,

        "summary": summary,

        "expense_breakdown": breakdown,

        "transaction_count":
            transactions["count"],

        "transactions":
            transactions["transactions"]
    }


# ============================================================
# 7. MONTHLY COMPARISON
# ============================================================

def compare_months(
    month1,
    month2
):

    first = get_financial_summary(month1)

    second = get_financial_summary(month2)

    return {
        "month1": first,
        "month2": second,

        "income_difference":
            second["income"] -
            first["income"],

        "expense_difference":
            second["expenses"] -
            first["expenses"],

        "surplus_difference":
            second["surplus"] -
            first["surplus"]
    }


# ============================================================
# 8. SPENDING TRENDS
# ============================================================

def spending_trends():

    transactions = _transactions(
        transaction_type="expense"
    )

    monthly = defaultdict(float)

    for transaction in transactions:

        transaction_date = transaction["date"]

        if transaction_date:

            month = transaction_date[:7]

            monthly[month] += (
                transaction["amount"]
            )

    result = []

    for month in sorted(monthly):

        result.append({
            "month": month,
            "expenses": monthly[month]
        })

    return {
        "monthly_expenses": result
    }


# ============================================================
# 9. UNUSUAL EXPENSES
# ============================================================

def detect_unusual_expenses():

    transactions = _transactions(
        transaction_type="expense"
    )

    if not transactions:

        return {
            "unusual_expenses": []
        }

    category_amounts = defaultdict(list)

    for transaction in transactions:

        category_amounts[
            transaction["category"]
        ].append(
            transaction["amount"]
        )

    unusual = []

    for transaction in transactions:

        values = category_amounts[
            transaction["category"]
        ]

        if len(values) < 2:
            continue

        average = (
            sum(values) /
            len(values)
        )

        if (
            average > 0
            and transaction["amount"]
            >= average * 2
        ):

            unusual.append({
                **transaction,

                "category_average":
                    average,

                "multiple_of_average":
                    transaction["amount"] /
                    average
            })

    return {
        "unusual_expenses": unusual
    }


# ============================================================
# 10. RECURRING EXPENSES
# ============================================================

def detect_recurring_expenses():

    transactions = _transactions(
        transaction_type="expense"
    )

    groups = defaultdict(list)

    for transaction in transactions:

        key = (
            transaction["category"].lower(),
            round(
                transaction["amount"],
                2
            )
        )

        groups[key].append(transaction)

    recurring = []

    for key, items in groups.items():

        if len(items) >= 2:

            recurring.append({
                "category": key[0],
                "amount": key[1],
                "occurrences": len(items),
                "transactions": items
            })

    return {
        "recurring_expenses": recurring
    }


# ============================================================
# 11. GOALS
# ============================================================

def get_goals():

    rows = database.get_goals()

    goals = []

    for row in rows:

        target = float(row[2])
        saved = float(row[3])
        monthly = float(row[4])

        percentage = 0

        if target > 0:

            percentage = (
                saved /
                target
            ) * 100

        months = finance.calculate_goal_months(
            target,
            saved,
            monthly
        )

        goals.append({
            "id": row[0],
            "name": row[1],
            "target": target,
            "saved": saved,
            "monthly_saving": monthly,
            "deadline": row[5],
            "progress_percent": percentage,
            "months_remaining": months
        })

    return {
        "goals": goals
    }


# ============================================================
# 12. GOAL PROJECTION
# ============================================================

def goal_projection(
    target,
    saved,
    monthly_saving
):

    target = float(target)
    saved = float(saved)
    monthly_saving = float(monthly_saving)

    months = finance.calculate_goal_months(
        target,
        saved,
        monthly_saving
    )

    remaining = max(
        0,
        target - saved
    )

    return {
        "target": target,
        "saved": saved,
        "remaining": remaining,
        "monthly_saving":
            monthly_saving,
        "months_required": months
    }


# ============================================================
# 13. LOANS
# ============================================================

def get_loans():

    rows = database.get_loans()

    loans = []

    for row in rows:

        principal = float(row[2])
        interest = float(row[3])
        months = int(row[4])

        emi = finance.calculate_emi(
            principal,
            interest,
            months
        )

        total_payment = (
            finance.calculate_total_payment(
                emi,
                months
            )
        )

        total_interest = (
            finance.calculate_total_interest(
                emi,
                months,
                principal
            )
        )

        loans.append({
            "id": row[0],
            "name": row[1],
            "principal": principal,
            "annual_interest": interest,
            "months": months,
            "emi": emi,
            "total_payment":
                total_payment,
            "total_interest":
                total_interest
        })

    return {
        "loans": loans
    }


# ============================================================
# 14. LOAN ANALYSIS
# ============================================================

def loan_analysis():

    data = get_loans()

    loans = data["loans"]

    total_principal = sum(
        loan["principal"]
        for loan in loans
    )

    total_interest = sum(
        loan["total_interest"]
        for loan in loans
    )

    total_emi = sum(
        loan["emi"]
        for loan in loans
    )

    return {
        "loans": loans,
        "total_principal":
            total_principal,
        "total_interest":
            total_interest,
        "total_emi":
            total_emi
    }


# ============================================================
# 15. WHAT-IF
# ============================================================

def simulate_finances(
    income_change=0,
    expense_change=0,
    month=None
):

    totals = database.get_totals(month)

    return finance.calculate_what_if(
        income=float(
            totals["income"]
        ),

        expenses=float(
            totals["expenses"]
        ),

        income_change=float(
            income_change
        ),

        expense_change=float(
            expense_change
        )
    )


# ============================================================
# 16. FINANCIAL HEALTH
# ============================================================

def financial_health():

    summary = get_financial_summary()

    income = summary["income"]

    savings_rate = (
        summary["savings_rate"]
    )

    if income <= 0:

        health = (
            "No income recorded"
        )

    elif savings_rate >= 30:

        health = (
            "Strong savings position"
        )

    elif savings_rate >= 20:

        health = (
            "Healthy savings position"
        )

    elif savings_rate >= 10:

        health = (
            "Moderate savings position"
        )

    elif savings_rate >= 0:

        health = (
            "Low savings position"
        )

    else:

        health = (
            "Expenses exceed income"
        )

    return {
        "summary": summary,
        "health": health
    }


# ============================================================
# 17. ALERTS
# ============================================================

def generate_alerts():

    alerts = []

    summary = get_financial_summary()

    if summary["income"] <= 0:

        alerts.append({
            "type": "warning",
            "message":
                "No income is currently recorded."
        })

    if (
        summary["expenses"] >
        summary["income"]
        and summary["income"] > 0
    ):

        alerts.append({
            "type": "danger",
            "message":
                "Your expenses are higher "
                "than your income."
        })

    elif (
        summary["savings_rate"] < 10
        and summary["income"] > 0
    ):

        alerts.append({
            "type": "warning",
            "message":
                "Your current savings rate "
                "is below 10%."
        })

    unusual = detect_unusual_expenses()

    for transaction in (
        unusual["unusual_expenses"]
    ):

        alerts.append({
            "type": "warning",
            "message":
                f"Unusually high "
                f"{transaction['category']} "
                f"expense of "
                f"₹{transaction['amount']:,.2f}."
        })

    return {
        "alerts": alerts
    }


# ============================================================
# TOOL REGISTRY
# ============================================================

TOOLS = {

    "get_financial_summary":
        get_financial_summary,

    "get_all_transactions":
        get_all_transactions,

    "get_income":
        get_income,

    "get_expenses":
        get_expenses,

    "get_category_breakdown":
        get_category_breakdown,

    "complete_financial_breakdown":
        complete_financial_breakdown,

    "compare_months":
        compare_months,

    "spending_trends":
        spending_trends,

    "detect_unusual_expenses":
        detect_unusual_expenses,

    "detect_recurring_expenses":
        detect_recurring_expenses,

    "get_goals":
        get_goals,

    "goal_projection":
        goal_projection,

    "get_loans":
        get_loans,

    "loan_analysis":
        loan_analysis,

    "simulate_finances":
        simulate_finances,

    "financial_health":
        financial_health,

    "generate_alerts":
        generate_alerts
}