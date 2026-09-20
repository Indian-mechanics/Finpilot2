def calculate_surplus(income, expenses):
    return income - expenses


def calculate_savings_rate(income, expenses):

    if income <= 0:
        return 0

    return ((income - expenses) / income) * 100


def calculate_emi(
    principal,
    annual_interest,
    months
):

    if principal <= 0 or months <= 0:
        return 0

    monthly_rate = annual_interest / 12 / 100

    if monthly_rate == 0:
        return principal / months

    emi = (
        principal
        * monthly_rate
        * (1 + monthly_rate) ** months
        / (
            (1 + monthly_rate) ** months - 1
        )
    )

    return emi


def calculate_total_payment(
    emi,
    months
):

    return emi * months


def calculate_total_interest(
    emi,
    months,
    principal
):

    return (emi * months) - principal


def calculate_goal_months(
    target,
    saved,
    monthly_saving
):

    remaining = target - saved

    if remaining <= 0:
        return 0

    if monthly_saving <= 0:
        return None

    months = remaining / monthly_saving

    return int(months) if months.is_integer() else int(months) + 1


def calculate_what_if(
    income,
    expenses,
    expense_change=0,
    income_change=0
):

    new_income = income + income_change
    new_expenses = expenses + expense_change

    old_surplus = income - expenses
    new_surplus = new_income - new_expenses

    return {
        "old_income": income,
        "old_expenses": expenses,
        "old_surplus": old_surplus,
        "new_income": new_income,
        "new_expenses": new_expenses,
        "new_surplus": new_surplus,
        "difference": new_surplus - old_surplus
    }