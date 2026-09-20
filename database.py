# F:\FinPilot\database.py

import sqlite3
from pathlib import Path
from datetime import date


# ============================================================
# DATABASE LOCATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "finpilot.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    conn = sqlite3.connect(
        str(DB_FILE)
    )

    return conn


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():

    conn = get_connection()

    cursor = conn.cursor()

    # ========================================================
    # TRANSACTIONS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            transaction_type TEXT NOT NULL,

            category TEXT NOT NULL,

            amount REAL NOT NULL,

            description TEXT,

            date TEXT NOT NULL

        )
        """
    )

    # ========================================================
    # GOALS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS goals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            target_amount REAL NOT NULL,

            saved_amount REAL DEFAULT 0,

            monthly_saving REAL DEFAULT 0,

            deadline TEXT

        )
        """
    )

    # ========================================================
    # LOANS
    # ========================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS loans (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            principal REAL NOT NULL,

            annual_interest REAL NOT NULL,

            months INTEGER NOT NULL

        )
        """
    )

    # ========================================================
    # CHECK OLD TRANSACTIONS TABLE
    # ========================================================

    cursor.execute(
        "PRAGMA table_info(transactions)"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    # If an old FinPilot database was created
    # without the date column, add it.

    if "date" not in columns:

        cursor.execute(
            """
            ALTER TABLE transactions
            ADD COLUMN date TEXT
            """
        )

        today = date.today().isoformat()

        cursor.execute(
            """
            UPDATE transactions
            SET date = ?
            WHERE date IS NULL
            """,
            (today,)
        )

    conn.commit()

    conn.close()


# ============================================================
# ADD TRANSACTION
# ============================================================

def add_transaction(
    transaction_type,
    category,
    amount,
    description="",
    transaction_date=None
):

    if transaction_date is None:

        transaction_date = (
            date.today().isoformat()
        )

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO transactions
        (
            transaction_type,
            category,
            amount,
            description,
            date
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            transaction_type,
            category,
            amount,
            description,
            transaction_date
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# GET TRANSACTIONS
# ============================================================

def get_transactions(
    month=None,
    transaction_type=None,
    category=None
):

    conn = get_connection()

    cursor = conn.cursor()

    query = """
        SELECT
            id,
            transaction_type,
            category,
            amount,
            description,
            date
        FROM transactions
        WHERE 1 = 1
    """

    params = []

    # --------------------------------------------------------
    # MONTH FILTER
    # --------------------------------------------------------

    if month:

        query += """
            AND date LIKE ?
        """

        params.append(
            month + "%"
        )

    # --------------------------------------------------------
    # TYPE FILTER
    # --------------------------------------------------------

    if transaction_type:

        query += """
            AND transaction_type = ?
        """

        params.append(
            transaction_type
        )

    # --------------------------------------------------------
    # CATEGORY FILTER
    # --------------------------------------------------------

    if category:

        query += """
            AND category = ?
        """

        params.append(
            category
        )

    query += """
        ORDER BY date DESC, id DESC
    """

    cursor.execute(
        query,
        params
    )

    results = cursor.fetchall()

    conn.close()

    return results

# ============================================================
# TOTALS RESULT
# Supports BOTH:
# totals["income"]
# totals.get("income")
# income, expenses = totals
# ============================================================

class TotalsResult(dict):

    def __iter__(self):
        """
        Allows:

            income, expenses = result

        while still allowing:

            result.get("income")
            result["income"]
        """

        yield self["income"]
        yield self["expenses"]


# ============================================================
# GET TOTALS
# ============================================================

def get_totals(month=None):

    conn = get_connection()

    cursor = conn.cursor()

    if month:

        cursor.execute(
            """
            SELECT

                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'income'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'expense'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                )

            FROM transactions

            WHERE date LIKE ?
            """,
            (month + "%",)
        )

    else:

        cursor.execute(
            """
            SELECT

                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'income'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                ),

                COALESCE(
                    SUM(
                        CASE
                            WHEN transaction_type = 'expense'
                            THEN amount
                            ELSE 0
                        END
                    ),
                    0
                )

            FROM transactions
            """
        )

    result = cursor.fetchone()

    conn.close()

    income = 0.0
    expenses = 0.0

    if result:

        income = float(
            result[0] or 0
        )

        expenses = float(
            result[1] or 0
        )

    return TotalsResult(
        income=income,
        expenses=expenses,
        surplus=income - expenses
    )
# ============================================================
# GET CATEGORY TOTALS
# ============================================================

def get_category_totals(
    month=None,
    transaction_type="expense"
):

    conn = get_connection()
    cursor = conn.cursor()

    if month:

        cursor.execute(
            """
            SELECT
                category,
                COALESCE(SUM(amount), 0)

            FROM transactions

            WHERE transaction_type = ?

            AND date LIKE ?

            GROUP BY category

            ORDER BY SUM(amount) DESC
            """,
            (
                transaction_type,
                month + "%"
            )
        )

    else:

        cursor.execute(
            """
            SELECT
                category,
                COALESCE(SUM(amount), 0)

            FROM transactions

            WHERE transaction_type = ?

            GROUP BY category

            ORDER BY SUM(amount) DESC
            """,
            (
                transaction_type,
            )
        )

    results = cursor.fetchall()

    conn.close()

    return results
# ============================================================
# ADD GOAL
# ============================================================

def add_goal(
    name,
    target_amount,
    saved_amount=0,
    monthly_saving=0,
    deadline=None
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO goals
        (
            name,
            target_amount,
            saved_amount,
            monthly_saving,
            deadline
        )

        VALUES (?, ?, ?, ?, ?)
        """,
        (
            name,
            target_amount,
            saved_amount,
            monthly_saving,
            deadline
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# GET GOALS
# ============================================================

def get_goals():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            target_amount,
            saved_amount,
            monthly_saving,
            deadline

        FROM goals

        ORDER BY id DESC
        """
    )

    results = cursor.fetchall()

    conn.close()

    return results


# ============================================================
# ADD LOAN
# ============================================================

def add_loan(
    name,
    principal,
    annual_interest,
    months
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO loans
        (
            name,
            principal,
            annual_interest,
            months
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            principal,
            annual_interest,
            months
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# GET LOANS
# ============================================================

def get_loans():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            principal,
            annual_interest,
            months

        FROM loans

        ORDER BY id DESC
        """
    )

    results = cursor.fetchall()

    conn.close()

    return results


# ============================================================
# DELETE TRANSACTION
# ============================================================

def delete_transaction(
    transaction_id
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM transactions
        WHERE id = ?
        """,
        (
            transaction_id,
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# DELETE GOAL
# ============================================================

def delete_goal(
    goal_id
):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM goals
        WHERE id = ?
        """,
        (
            goal_id,
        )
    )

    conn.commit()

    conn.close()


# ============================================================
# DATABASE TEST
# ============================================================

if __name__ == "__main__":

    initialize_database()

    print(
        "FinPilot database initialized successfully."
    )

    print(
        f"Database location: {DB_FILE}"
    )