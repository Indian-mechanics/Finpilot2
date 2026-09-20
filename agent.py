import json
import re
from collections import defaultdict
from datetime import date, datetime
from statistics import mean

import database
import finance
from ollama_client import ask_ollama


MAX_REASONING_STEPS = 8


# ============================================================
# TOOL DEFINITIONS
# ============================================================

TOOLS = {
    "get_financial_context": {
        "description": (
            "Get a broad financial overview including recorded "
            "income, expenses, surplus, expense categories, income "
            "categories, recent transactions, goals, loans, and "
            "Python-calculated financial insights."
        ),
        "arguments": {
            "month": "Optional YYYY-MM month filter."
        }
    },

    "get_totals": {
        "description": (
            "Get recorded income, recorded expenses, recorded "
            "surplus, and calculated savings rate."
        ),
        "arguments": {
            "month": "Optional YYYY-MM month filter."
        }
    },

    "get_transactions": {
        "description": (
            "Get individual financial transactions. Use this when "
            "the question requires transaction-level details, dates, "
            "categories, or descriptions."
        ),
        "arguments": {
            "month": "Optional YYYY-MM month filter.",
            "type": "Optional income or expense.",
            "category": "Optional category."
        }
    },

    "get_category_totals": {
        "description": (
            "Get the total amount grouped by category for income "
            "or expenses."
        ),
        "arguments": {
            "month": "Optional YYYY-MM month filter.",
            "type": "income or expense."
        }
    },

    "get_goals": {
        "description": (
            "Get all recorded financial goals, their progress, "
            "monthly saving amount, deadline, and estimated months."
        ),
        "arguments": {}
    },

    "get_loans": {
        "description": (
            "Get recorded loans together with EMI, total payment, "
            "and total interest calculated by Python."
        ),
        "arguments": {}
    },

    "calculate_loan": {
        "description": (
            "Calculate EMI, total payment, and total interest for "
            "a supplied loan."
        ),
        "arguments": {
            "principal": "Loan principal.",
            "annual_interest": "Annual interest percentage.",
            "months": "Loan duration in months."
        }
    },

    "calculate_goal": {
        "description": (
            "Calculate goal progress and estimated months required "
            "from target, saved amount, and monthly saving."
        ),
        "arguments": {
            "target": "Goal target amount.",
            "saved": "Current saved amount.",
            "monthly_saving": "Monthly saving amount."
        }
    }
}


# ============================================================
# BASIC HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def format_money(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def format_date_human(value):
    if not value:
        return ""

    text = str(value)

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d"
    ):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime("%d %B %Y")
        except ValueError:
            pass

    return text


def get_month_from_date(value):
    if not value:
        return None

    match = re.match(
        r"^(\d{4}-\d{2})",
        str(value)
    )

    if match:
        return match.group(1)

    return None


def current_month():
    return date.today().strftime("%Y-%m")


def previous_month():
    today = date.today()

    year = today.year
    month = today.month

    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1

    return f"{year:04d}-{month:02d}"


# ============================================================
# FINANCIAL DERIVED INSIGHTS
# ============================================================

def calculate_derived_insights(
    totals,
    transactions,
    expense_categories,
    goals,
    loans
):
    income = safe_float(
        totals.get("income")
    )

    expenses = safe_float(
        totals.get("expenses")
    )

    surplus = safe_float(
        totals.get("surplus")
    )

    transaction_count = len(
        transactions
    )

    income_transaction_count = 0
    expense_transaction_count = 0

    amounts = []

    monthly = defaultdict(
        lambda: {
            "income": 0.0,
            "expenses": 0.0,
            "transactions": 0
        }
    )

    category_months = defaultdict(
        set
    )

    for tx in transactions:

        amount = safe_float(
            tx.get("amount")
        )

        amounts.append(
            amount
        )

        tx_type = str(
            tx.get("type", "")
        ).lower()

        tx_month = get_month_from_date(
            tx.get("date")
        )

        if tx_type == "income":
            income_transaction_count += 1

        elif tx_type == "expense":
            expense_transaction_count += 1

        if tx_month:

            monthly[
                tx_month
            ]["transactions"] += 1

            if tx_type == "income":

                monthly[
                    tx_month
                ]["income"] += amount

            elif tx_type == "expense":

                monthly[
                    tx_month
                ]["expenses"] += amount

                category = str(
                    tx.get(
                        "category",
                        ""
                    )
                ).strip()

                if category:
                    category_months[
                        category
                    ].add(
                        tx_month
                    )

    monthly_summary = []

    for month in sorted(monthly):

        month_income = monthly[
            month
        ]["income"]

        month_expenses = monthly[
            month
        ]["expenses"]

        month_surplus = (
            month_income
            - month_expenses
        )

        month_savings_rate = (
            finance.calculate_savings_rate(
                month_income,
                month_expenses
            )
        )

        monthly_summary.append({
            "month": month,
            "income": month_income,
            "expenses": month_expenses,
            "surplus": month_surplus,
            "savings_rate": month_savings_rate,
            "transactions":
                monthly[
                    month
                ]["transactions"]
        })

    largest_category = None
    largest_expense = 0.0
    largest_percentage = 0.0

    if expense_categories:

        category_name = expense_categories[0][
            0
        ]

        category_amount = safe_float(
            expense_categories[0][1]
        )

        largest_category = category_name
        largest_expense = category_amount

        if expenses > 0:

            largest_percentage = (
                category_amount
                / expenses
            ) * 100

    recurring_categories = [
        category
        for category, months in category_months.items()
        if len(months) >= 2
    ]

    expense_to_income_ratio = 0.0

    if income > 0:
        expense_to_income_ratio = (
            expenses / income
        ) * 100

    average_transaction = (
        mean(amounts)
        if amounts
        else 0.0
    )

    average_monthly_income = 0.0
    average_monthly_expenses = 0.0

    if monthly_summary:

        average_monthly_income = mean(
            item["income"]
            for item in monthly_summary
        )

        average_monthly_expenses = mean(
            item["expenses"]
            for item in monthly_summary
        )

    trend = {
        "available": False,
        "direction": "not enough data",
        "details": ""
    }

    if len(monthly_summary) >= 3:

        first = monthly_summary[0]
        last = monthly_summary[-1]

        trend["available"] = True

        income_difference = (
            last["income"]
            - first["income"]
        )

        expense_difference = (
            last["expenses"]
            - first["expenses"]
        )

        if income_difference > 0:
            income_direction = "increased"
        elif income_difference < 0:
            income_direction = "decreased"
        else:
            income_direction = "remained similar"

        if expense_difference > 0:
            expense_direction = "increased"
        elif expense_difference < 0:
            expense_direction = "decreased"
        else:
            expense_direction = "remained similar"

        trend["direction"] = (
            f"Income {income_direction}; "
            f"expenses {expense_direction}."
        )

        trend["details"] = (
            f"From {first['month']} to {last['month']}, "
            f"recorded income changed by "
            f"{format_money(abs(income_difference))} "
            f"and recorded expenses changed by "
            f"{format_money(abs(expense_difference))}."
        )

    goal_analysis = []

    for goal in goals:

        target = safe_float(
            goal.get("target")
        )

        saved = safe_float(
            goal.get("saved")
        )

        monthly_saving = safe_float(
            goal.get("monthly")
        )

        progress = 0.0

        if target > 0:
            progress = (
                saved / target
            ) * 100

        remaining = max(
            target - saved,
            0
        )

        goal_analysis.append({
            "name":
                goal.get("name", ""),

            "target":
                target,

            "saved":
                saved,

            "remaining":
                remaining,

            "monthly_saving":
                monthly_saving,

            "progress_percentage":
                progress,

            "months_remaining":
                finance.calculate_goal_months(
                    target,
                    saved,
                    monthly_saving
                ),

            "deadline":
                goal.get("deadline")
        })

    loan_analysis = []

    total_emi = 0.0
    total_interest = 0.0

    for loan in loans:

        principal = safe_float(
            loan.get("principal")
        )

        annual_interest = safe_float(
            loan.get("annual_interest")
        )

        months = safe_int(
            loan.get("months")
        )

        emi = finance.calculate_emi(
            principal,
            annual_interest,
            months
        )

        loan_total_payment = (
            finance.calculate_total_payment(
                emi,
                months
            )
        )

        loan_total_interest = (
            finance.calculate_total_interest(
                emi,
                months,
                principal
            )
        )

        total_emi += emi
        total_interest += loan_total_interest

        loan_analysis.append({
            "name":
                loan.get("name", ""),

            "principal":
                principal,

            "annual_interest":
                annual_interest,

            "months":
                months,

            "emi":
                emi,

            "total_payment":
                loan_total_payment,

            "total_interest":
                loan_total_interest
        })

    # Data quality
    data_quality = "limited"

    if transaction_count >= 20:
        data_quality = "good"
    elif transaction_count >= 10:
        data_quality = "moderate"
    elif transaction_count >= 3:
        data_quality = "limited"

    return {

        "expense_to_income_ratio":
            expense_to_income_ratio,

        "income_transaction_count":
            income_transaction_count,

        "expense_transaction_count":
            expense_transaction_count,

        "average_transaction_amount":
            average_transaction,

        "average_monthly_income":
            average_monthly_income,

        "average_monthly_expenses":
            average_monthly_expenses,

        "largest_expense_category":
            largest_category,

        "largest_expense_amount":
            largest_expense,

        "largest_expense_percentage":
            largest_percentage,

        "recurring_expense_categories":
            recurring_categories,

        "monthly_summary":
            monthly_summary[-6:],

        "trend":
            trend,

        "goal_analysis":
            goal_analysis,

        "loan_analysis":
            loan_analysis,

        "total_monthly_emi":
            total_emi,

        "total_loan_interest":
            total_interest,

        "data_quality":
            data_quality,

        "transaction_count":
            transaction_count,

        "income":
            income,

        "expenses":
            expenses,

        "surplus":
            surplus,

        "calculated_savings_rate":
            finance.calculate_savings_rate(
                income,
                expenses
            )
    }


# ============================================================
# COMPLETE FINANCIAL CONTEXT
# ============================================================

def build_financial_context(
    month=None
):
    totals = database.get_totals(
        month
    )

    expense_rows = database.get_category_totals(
        month=month,
        transaction_type="expense"
    )

    income_rows = database.get_category_totals(
        month=month,
        transaction_type="income"
    )

    all_transactions = database.get_transactions(
        month=month
    )

    goals_rows = database.get_goals()
    loans_rows = database.get_loans()

    transactions = []

    for row in all_transactions:

        transactions.append({
            "id": row[0],
            "type": row[1],
            "category": row[2],
            "amount": safe_float(row[3]),
            "description": row[4] or "",
            "date": row[5]
        })

    goals = []

    for row in goals_rows:

        goals.append({
            "id": row[0],
            "name": row[1],
            "target": safe_float(row[2]),
            "saved": safe_float(row[3]),
            "monthly": safe_float(row[4]),
            "deadline": row[5]
        })

    loans = []

    for row in loans_rows:

        loans.append({
            "id": row[0],
            "name": row[1],
            "principal": safe_float(row[2]),
            "annual_interest": safe_float(row[3]),
            "months": safe_int(row[4])
        })

    # Recent transactions are enough for general reasoning.
    recent_transactions = transactions[:10]

    context = {

        "period":
            month or "all recorded data",

        "totals": {
            "income":
                safe_float(
                    totals["income"]
                ),

            "expenses":
                safe_float(
                    totals["expenses"]
                ),

            "surplus":
                safe_float(
                    totals["surplus"]
                )
        },

        "expense_categories": [
            {
                "category": row[0],
                "amount": safe_float(row[1])
            }
            for row in expense_rows
        ],

        "income_categories": [
            {
                "category": row[0],
                "amount": safe_float(row[1])
            }
            for row in income_rows
        ],

        "transaction_count":
            len(transactions),

        "recent_transactions": [
            {
                **tx,
                "date":
                    format_date_human(
                        tx["date"]
                    )
            }
            for tx in recent_transactions
        ],

        "goals":
            goals,

        "loans":
            loans
    }

    # Derived insights should use original transaction dates,
    # not the human-formatted dates above.
    raw_for_analysis = {
        "totals": context["totals"],
        "transactions": transactions
    }

    context[
        "derived_insights"
    ] = calculate_derived_insights(
        totals=context["totals"],
        transactions=transactions,
        expense_categories=expense_rows,
        goals=goals,
        loans=loans
    )

    # Include only compact monthly history in main context.
    context[
        "monthly_summary"
    ] = context[
        "derived_insights"
    ]["monthly_summary"]

    return context


# ============================================================
# TOOL EXECUTION
# ============================================================

def execute_tool(
    tool_name,
    arguments=None
):
    arguments = arguments or {}

    try:

        if tool_name == "get_financial_context":

            return build_financial_context(
                arguments.get("month")
            )

        if tool_name == "get_totals":

            month = arguments.get(
                "month"
            )

            result = database.get_totals(
                month
            )

            income = safe_float(
                result["income"]
            )

            expenses = safe_float(
                result["expenses"]
            )

            return {

                "period":
                    month or
                    "all recorded data",

                "income":
                    income,

                "expenses":
                    expenses,

                "surplus":
                    safe_float(
                        result["surplus"]
                    ),

                "savings_rate":
                    finance.calculate_savings_rate(
                        income,
                        expenses
                    )
            }

        if tool_name == "get_transactions":

            rows = database.get_transactions(

                month=arguments.get(
                    "month"
                ),

                transaction_type=arguments.get(
                    "type"
                ),

                category=arguments.get(
                    "category"
                )
            )

            return [

                {
                    "id": row[0],

                    "type": row[1],

                    "category": row[2],

                    "amount":
                        safe_float(row[3]),

                    "description":
                        row[4] or "",

                    "date":
                        format_date_human(
                            row[5]
                        )
                }

                for row in rows
            ]

        if tool_name == "get_category_totals":

            transaction_type = (
                arguments.get(
                    "type",
                    "expense"
                )
            )

            if transaction_type not in {
                "income",
                "expense"
            }:

                transaction_type = "expense"

            rows = database.get_category_totals(

                month=arguments.get(
                    "month"
                ),

                transaction_type=
                    transaction_type
            )

            return [

                {
                    "category":
                        row[0],

                    "amount":
                        safe_float(row[1])
                }

                for row in rows
            ]

        if tool_name == "get_goals":

            rows = database.get_goals()

            result = []

            for row in rows:

                target = safe_float(
                    row[2]
                )

                saved = safe_float(
                    row[3]
                )

                monthly = safe_float(
                    row[4]
                )

                result.append({

                    "id": row[0],

                    "name": row[1],

                    "target":
                        target,

                    "saved":
                        saved,

                    "monthly_saving":
                        monthly,

                    "deadline":
                        row[5],

                    "progress_percentage":
                        (
                            saved / target * 100
                            if target > 0
                            else 0.0
                        ),

                    "months_remaining":
                        finance.calculate_goal_months(
                            target,
                            saved,
                            monthly
                        )
                })

            return result

        if tool_name == "get_loans":

            rows = database.get_loans()

            result = []

            for row in rows:

                principal = safe_float(
                    row[2]
                )

                annual_interest = safe_float(
                    row[3]
                )

                months = safe_int(
                    row[4]
                )

                emi = finance.calculate_emi(
                    principal,
                    annual_interest,
                    months
                )

                result.append({

                    "id": row[0],

                    "name": row[1],

                    "principal":
                        principal,

                    "annual_interest":
                        annual_interest,

                    "months":
                        months,

                    "emi":
                        emi,

                    "total_payment":
                        finance.calculate_total_payment(
                            emi,
                            months
                        ),

                    "total_interest":
                        finance.calculate_total_interest(
                            emi,
                            months,
                            principal
                        )
                })

            return result

        if tool_name == "calculate_loan":

            principal = safe_float(
                arguments.get(
                    "principal"
                )
            )

            annual_interest = safe_float(
                arguments.get(
                    "annual_interest"
                )
            )

            months = safe_int(
                arguments.get(
                    "months"
                )
            )

            if principal <= 0:

                return {
                    "error":
                        "Principal must be greater than zero."
                }

            if annual_interest < 0:

                return {
                    "error":
                        "Interest cannot be negative."
                }

            if months <= 0:

                return {
                    "error":
                        "Months must be greater than zero."
                }

            emi = finance.calculate_emi(
                principal,
                annual_interest,
                months
            )

            return {

                "principal":
                    principal,

                "annual_interest":
                    annual_interest,

                "months":
                    months,

                "emi":
                    emi,

                "total_payment":
                    finance.calculate_total_payment(
                        emi,
                        months
                    ),

                "total_interest":
                    finance.calculate_total_interest(
                        emi,
                        months,
                        principal
                    )
            }

        if tool_name == "calculate_goal":

            target = safe_float(
                arguments.get(
                    "target"
                )
            )

            saved = safe_float(
                arguments.get(
                    "saved"
                )
            )

            monthly_saving = safe_float(
                arguments.get(
                    "monthly_saving"
                )
            )

            if target <= 0:

                return {
                    "error":
                        "Target must be greater than zero."
                }

            if saved < 0:

                return {
                    "error":
                        "Saved amount cannot be negative."
                }

            if monthly_saving < 0:

                return {
                    "error":
                        "Monthly saving cannot be negative."
                }

            return {

                "target":
                    target,

                "saved":
                    saved,

                "remaining":
                    max(
                        target - saved,
                        0
                    ),

                "monthly_saving":
                    monthly_saving,

                "progress_percentage":
                    saved / target * 100,

                "months_remaining":
                    finance.calculate_goal_months(
                        target,
                        saved,
                        monthly_saving
                    )
            }

        return {
            "error":
                f"Unknown tool '{tool_name}'."
        }

    except Exception as error:

        return {
            "error":
                str(error)
        }


# ============================================================
# JSON PARSER
# ============================================================

def parse_json_object(text):

    if not text:
        return None

    cleaned = str(
        text
    ).strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    try:

        result = json.loads(
            cleaned
        )

        if isinstance(
            result,
            dict
        ):
            return result

    except json.JSONDecodeError:
        pass

    start = cleaned.find(
        "{"
    )

    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(
        start,
        len(cleaned)
    ):

        char = cleaned[index]

        if in_string:

            if escaped:
                escaped = False

            elif char == "\\":
                escaped = True

            elif char == '"':
                in_string = False

            continue

        if char == '"':
            in_string = True

        elif char == "{":
            depth += 1

        elif char == "}":

            depth -= 1

            if depth == 0:

                candidate = cleaned[
                    start:index + 1
                ]

                try:

                    result = json.loads(
                        candidate
                    )

                    if isinstance(
                        result,
                        dict
                    ):
                        return result

                except json.JSONDecodeError:
                    return None

    return None


# ============================================================
# TOOL PROMPT
# ============================================================

def get_tool_text():

    parts = []

    for name, info in TOOLS.items():

        parts.append(
            f"TOOL: {name}\n"
            f"PURPOSE: {info['description']}\n"
            f"ARGUMENTS: "
            f"{json.dumps(info['arguments'], ensure_ascii=False)}"
        )

    return "\n\n".join(
        parts
    )


# ============================================================
# HUMAN STYLE RULES
# ============================================================

HUMAN_STYLE_RULES = """
Write like a smart, patient human financial assistant.

Do NOT sound like:
- a database
- a programming script
- an academic paper
- a corporate report
- a chatbot reading raw numbers

Prefer natural wording such as:
"From what you've recorded..."
"One thing that stands out..."
"That matters because..."
"Right now, I wouldn't draw a strong conclusion from this because..."
"The next useful step is..."

Avoid wording such as:
"the individual"
"the dataset"
"the subject"
"the database indicates"
"the provided data suggests" repeated over and over.

Do not use dollar signs. Use ₹.

Do not repeat the same number unnecessarily.

Do not dump all transactions unless the user asks for them.

Use headings only when they improve readability.

Use short paragraphs.

Use bullets when comparing several points.

Explain the meaning of important numbers rather than merely repeating them.

Recommendations must be specific to the user's actual records.

When data is limited, say so naturally without refusing to analyze it.

Do not make the user feel judged.

Do not make guaranteed claims about future financial outcomes.
"""


# ============================================================
# REASONING PROMPT
# ============================================================

def build_reasoning_prompt(
    question,
    base_context,
    history
):

    return f"""
You are FinPilot, an intelligent personal finance assistant.

Your job is to understand the user's question, inspect their
recorded finances, reason over the numbers, and produce useful
financial guidance.

{HUMAN_STYLE_RULES}

IMPORTANT FACTUAL RULES:

1. Recorded financial data is the source of truth.
2. Python-calculated numbers are authoritative.
3. Never invent transactions.
4. Never invent amounts.
5. Never invent dates.
6. Never invent categories.
7. Never invent descriptions.
8. Never invent income sources.
9. Never invent expenses.
10. Never invent goals.
11. Never invent loans.
12. Do not call an income transaction "salary" unless the actual
    recorded category or description says salary.
13. Do not turn a recorded surplus into a claim that the user
    definitely saved that amount.
14. A 100% recorded savings rate is only a calculation from
    recorded income and expenses.
15. Missing expenses mean missing information, not proof that
    the user has no real-world expenses.
16. Logical conclusions are allowed when clearly supported by
    the data.
17. When making an inference, phrase it naturally as an inference.
18. Recommendations should be tied to evidence.
19. Do not give random generic advice.
20. Do not recommend investing unless it is relevant to the
    question and supported by the context.
21. Do not recommend increasing income without a reason.
22. Do not make guaranteed predictions.
23. Use Indian Rupees (₹).
24. Final answers must be human-readable.
25. Never expose internal tool names or JSON to the user.

You can use more than one tool.

AVAILABLE TOOLS:

{get_tool_text()}

BASE FINANCIAL CONTEXT:

{json.dumps(
    base_context,
    indent=2,
    ensure_ascii=False
)}

PREVIOUS TOOL HISTORY:

{history if history else "(No additional tools have been used.)"}

USER QUESTION:

{question}

Your job at this stage is to decide whether another tool is needed.

When another tool is needed, return ONLY:

{{
  "action": "tool",
  "tool": "tool_name",
  "arguments": {{}}
}}

When enough information has been collected, return ONLY:

{{
  "action": "final",
  "answer": "brief internal summary of the reasoning"
}}
"""


# ============================================================
# FINAL HUMAN-READABLE ANSWER
# ============================================================

def build_final_prompt(
    question,
    context
):

    return f"""
You are FinPilot's final response writer.

The user asked:

{question}

Here is VERIFIED financial information retrieved from FinPilot:

{json.dumps(
    context,
    indent=2,
    ensure_ascii=False
)}

{HUMAN_STYLE_RULES}

Now answer the user's actual question.

Your answer should feel like a real person who has looked at
the user's finances and thought about them.

QUALITY RULES:

- Start by directly answering the question.
- Explain what the important numbers mean.
- Point out meaningful patterns.
- Explain why those patterns matter.
- Mention limitations only when they materially affect the answer.
- Give 2 to 4 practical next actions when appropriate.
- Prioritize actions rather than listing generic advice.
- Keep the tone calm, useful, and realistic.
- Do not shame or praise the user unnecessarily.
- Do not say "the individual".
- Do not say "the dataset".
- Do not expose database/tool details.
- Do not output JSON.
- Do not output analysis instructions.
- Do not repeat the full raw transaction list.
- Use ₹, never $.
- Never invent information.

IMPORTANT INTERPRETATION RULES:

If recorded expenses are zero:
say that no expenses are currently recorded.
Do NOT say there are definitely no expenses.

If savings rate is 100%:
explain that this is based on recorded income and expenses,
not proof that the user has actually saved 100% of their income.

If there is only one or very few transactions:
explain that there is not enough history to identify reliable
long-term spending behaviour.

If a transaction category says salary, you may say salary.
Otherwise, do not invent the source.

If a financial recommendation depends on missing information,
say what information is missing.

Do not force a recommendation if the data does not support one.

Return ONLY the final answer in clean Markdown.
"""


# ============================================================
# CLEAN ANSWER
# ============================================================

def clean_answer(text):

    if not text:
        return ""

    text = str(
        text
    ).strip()

    # Remove code fences
    text = re.sub(
        r"```(?:markdown|text|json)?",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = text.replace(
        "```",
        ""
    )

    # If Qwen accidentally returned JSON,
    # extract the answer field.
    parsed = parse_json_object(
        text
    )

    if parsed:

        answer = parsed.get(
            "answer"
        )

        if isinstance(
            answer,
            str
        ):

            text = answer

    # Make common robotic wording more natural.
    replacements = {
        "the individual":
            "you",

        "the user's":
            "your",

        "the user’s":
            "your",

        "the dataset":
            "your recorded transactions",

        "the provided data":
            "your recorded data",

        "the database indicates":
            "your records show"
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    # Avoid accidental dollar currency.
    text = re.sub(
        r"\$(\s*[\d,]+(?:\.\d+)?)",
        r"₹\1",
        text
    )

    # Remove excessive blank lines.
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# ============================================================
# FALLBACK HUMAN ANSWER
# ============================================================

def fallback_answer(
    context
):

    totals = context.get(
        "totals",
        {}
    )

    derived = context.get(
        "derived_insights",
        {}
    )

    income = safe_float(
        totals.get("income")
    )

    expenses = safe_float(
        totals.get("expenses")
    )

    surplus = safe_float(
        totals.get("surplus")
    )

    savings_rate = safe_float(
        derived.get(
            "calculated_savings_rate"
        )
    )

    transaction_count = safe_int(
        derived.get(
            "transaction_count"
        )
    )

    lines = []

    lines.append(
        "## Here's what your records show"
    )

    lines.append("")

    lines.append(
        f"You've recorded "
        f"{format_money(income)} of income "
        f"and {format_money(expenses)} of expenses."
    )

    lines.append(
        f"That leaves a recorded surplus of "
        f"{format_money(surplus)}."
    )

    lines.append("")

    if expenses == 0:

        lines.append(
            "### What stands out"
        )

        lines.append("")

        lines.append(
            "No expenses are currently recorded. "
            f"Because of that, the calculated savings rate "
            f"is {savings_rate:.1f}%, but that should not be "
            "treated as proof that you have actually saved "
            "100% of your income."
        )

    else:

        largest_category = derived.get(
            "largest_expense_category"
        )

        largest_amount = safe_float(
            derived.get(
                "largest_expense_amount"
            )
        )

        if largest_category:

            lines.append(
                "### What stands out"
            )

            lines.append("")

            lines.append(
                f"Your biggest recorded expense category "
                f"is {largest_category} at "
                f"{format_money(largest_amount)}."
            )

    lines.append("")

    lines.append(
        "### What I'd do next"
    )

    lines.append("")

    if expenses == 0:

        lines.append(
            "1. Start recording your regular expenses."
        )

        lines.append(
            "2. Keep adding transactions for a few weeks "
            "so FinPilot can identify real spending patterns."
        )

    else:

        lines.append(
            "1. Keep recording transactions consistently."
        )

        lines.append(
            "2. Review your largest expense categories "
            "before making any major changes."
        )

    if transaction_count <= 2:

        lines.append(
            "3. Build up more transaction history before "
            "drawing strong conclusions about your finances."
        )

    return "\n".join(
        lines
    )


# ============================================================
# MAIN FINPILOT
# ============================================================

def ask_finpilot(
    user_question
):

    question = (
        user_question or ""
    ).strip()

    if not question:

        return "Please enter a question."

    # --------------------------------------------------------
    # Always give Qwen a broad verified overview first.
    # This makes the AI much less dependent on guessing which
    # tool it needs at the beginning.
    # --------------------------------------------------------

    try:

        base_context = (
            build_financial_context()
        )

    except Exception as error:

        return (
            "I couldn't read your financial records right now.\n\n"
            f"Error: {error}"
        )

    collected_context = {

        "initial_overview":
            base_context
    }

    history = []

    # --------------------------------------------------------
    # QWEN REASONING LOOP
    # --------------------------------------------------------

    for step in range(
        MAX_REASONING_STEPS
    ):

        prompt = build_reasoning_prompt(
            question,
            base_context,
            "\n".join(history)
        )

        try:

            response = ask_ollama(
                prompt
            )

        except Exception as error:

            return (
                "I couldn't connect to Qwen through Ollama.\n\n"
                f"Error: {error}"
            )

        if not response:

            break

        decision = parse_json_object(
            response
        )

        # ----------------------------------------------------
        # Qwen sometimes answers naturally instead of returning
        # JSON. In that case, don't throw away the answer.
        # ----------------------------------------------------

        if not decision:

            history.append(
                "Qwen did not return valid tool JSON. "
                "Use the verified context and produce the "
                "final answer."
            )

            continue

        action = str(
            decision.get(
                "action",
                ""
            )
        ).lower().strip()

        # ----------------------------------------------------
        # TOOL
        # ----------------------------------------------------

        if action == "tool":

            tool_name = decision.get(
                "tool"
            )

            if tool_name not in TOOLS:

                history.append(
                    f"Unknown tool '{tool_name}'. "
                    "Choose one of the available tools."
                )

                continue

            arguments = decision.get(
                "arguments",
                {}
            )

            if not isinstance(
                arguments,
                dict
            ):

                arguments = {}

            result = execute_tool(
                tool_name,
                arguments
            )

            history.append(
                f"TOOL: {tool_name}\n"
                f"ARGUMENTS: "
                f"{json.dumps(arguments, ensure_ascii=False)}\n"
                f"RESULT: "
                f"{json.dumps(result, ensure_ascii=False)}"
            )

            collected_context[
                f"tool_{step + 1}_{tool_name}"
            ] = result

            continue

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        if action == "final":

            break

        history.append(
            "Invalid action. Decide whether to use another "
            "tool or finish the answer."
        )

    # --------------------------------------------------------
    # FINAL HUMAN-READABLE SYNTHESIS
    # --------------------------------------------------------

    try:

        final_prompt = build_final_prompt(
            question,
            collected_context
        )

        final_response = ask_ollama(
            final_prompt
        )

        final_answer = clean_answer(
            final_response
        )

        if final_answer:

            return final_answer

    except Exception:
        pass

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    return fallback_answer(
        base_context
    )