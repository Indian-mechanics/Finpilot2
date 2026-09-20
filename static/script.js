// ============================================================
// FINPILOT - SCRIPT.JS
// ============================================================


// ============================================================
// GLOBAL VARIABLES
// ============================================================

let dashboardChart = null;


// ============================================================
// DOM HELPER
// ============================================================

function getElement(id) {

    return document.getElementById(id);
}


// ============================================================
// FORMAT MONEY
// ============================================================

function formatMoney(value) {

    const number = Number(value);

    if (Number.isNaN(number)) {
        return "₹0.00";
    }

    return new Intl.NumberFormat(
        "en-IN",
        {
            style: "currency",
            currency: "INR",
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    ).format(number);
}


// ============================================================
// ESCAPE HTML
// ============================================================

function escapeHTML(value) {

    if (
        value === null ||
        value === undefined
    ) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================
// API HELPER
// ============================================================

async function fetchJSON(
    url,
    options = {}
) {

    const response = await fetch(
        url,
        options
    );

    let data = {};

    try {

        data = await response.json();

    } catch (error) {

        data = {};
    }

    if (!response.ok) {

        throw new Error(
            data.error ||
            `Server error: ${response.status}`
        );
    }

    return data;
}


// ============================================================
// NAVIGATION
// ============================================================

function showPage(pageId) {

    const pages =
        document.querySelectorAll(
            ".page"
        );

    pages.forEach(
        (page) => {

            page.classList.remove(
                "active"
            );

            page.style.display =
                "none";
        }
    );


    const selectedPage =
        getElement(pageId);

    if (!selectedPage) {

        console.error(
            `Page '${pageId}' not found.`
        );

        return;
    }


    selectedPage.classList.add(
        "active"
    );

    selectedPage.style.display =
        "block";


    const navLinks =
        document.querySelectorAll(
            ".nav-link"
        );

    navLinks.forEach(
        (link) => {

            link.classList.remove(
                "active"
            );

            if (
                link.dataset.page ===
                pageId
            ) {

                link.classList.add(
                    "active"
                );
            }
        }
    );


    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });


    // Refresh data whenever the page opens.
    if (
        pageId === "dashboard"
    ) {

        loadDashboard();
    }


    if (
        pageId === "transactions"
    ) {

        loadTransactions();
    }


    if (
        pageId === "goals"
    ) {

        loadGoals();
    }


    if (
        pageId === "settings"
    ) {

        checkOllama();
    }
}


// ============================================================
// NAVIGATION SETUP
// ============================================================

function setupNavigation() {

    const links =
        document.querySelectorAll(
            ".nav-link"
        );

    links.forEach(
        (link) => {

            link.addEventListener(
                "click",
                () => {

                    const pageId =
                        link.dataset.page;

                    if (pageId) {

                        showPage(
                            pageId
                        );
                    }
                }
            );
        }
    );
}


// ============================================================
// DASHBOARD
// ============================================================

async function loadDashboard() {

    try {

        const monthElement =
            getElement(
                "dashboardMonth"
            );

        const month =
            monthElement
                ? monthElement.value
                : "";


        let url =
            "/api/dashboard";


        if (month) {

            url +=
                `?month=${encodeURIComponent(month)}`;
        }


        const data =
            await fetchJSON(
                url
            );


        updateDashboardCards(
            data
        );


        updateExpenseBreakdown(
            data
        );


        updateDashboardChart(
            data
        );


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );
    }
}


// ============================================================
// DASHBOARD CARDS
// ============================================================

function updateDashboardCards(
    data
) {

    const incomeValue =
        getElement(
            "incomeValue"
        );

    const expenseValue =
        getElement(
            "expenseValue"
        );

    const surplusValue =
        getElement(
            "surplusValue"
        );

    const savingsRateValue =
        getElement(
            "savingsRateValue"
        );


    if (incomeValue) {

        incomeValue.textContent =
            formatMoney(
                data.income
            );
    }


    if (expenseValue) {

        expenseValue.textContent =
            formatMoney(
                data.expenses
            );
    }


    if (surplusValue) {

        surplusValue.textContent =
            formatMoney(
                data.surplus
            );
    }


    if (savingsRateValue) {

        savingsRateValue.textContent =
            `${Number(
                data.savings_rate || 0
            ).toFixed(1)}%`;
    }
}


// ============================================================
// EXPENSE BREAKDOWN
// ============================================================

function updateExpenseBreakdown(
    data
) {

    const container =
        getElement(
            "expenseBreakdown"
        );

    if (!container) {
        return;
    }


    const categories =
        Array.isArray(
            data.categories
        )
            ? data.categories
            : [];


    if (
        categories.length === 0
    ) {

        container.innerHTML = `

            <div class="empty-state">

                No expenses are recorded yet.

            </div>

        `;

        return;
    }


    container.innerHTML =
        categories
            .map(
                (item) => {

                    return `

                        <div class="category-row">

                            <span>
                                ${escapeHTML(
                                    item.category
                                )}
                            </span>

                            <strong>
                                ${formatMoney(
                                    item.amount
                                )}
                            </strong>

                        </div>

                    `;
                }
            )
            .join("");
}


// ============================================================
// DASHBOARD CHART
// ============================================================

function updateDashboardChart(
    data
) {

    const canvas =
        getElement(
            "expenseChart"
        );

    if (
        !canvas ||
        typeof Chart === "undefined"
    ) {

        return;
    }


    const categories =
        Array.isArray(
            data.categories
        )
            ? data.categories
            : [];


    if (
        categories.length === 0
    ) {

        if (dashboardChart) {

            dashboardChart.destroy();

            dashboardChart =
                null;
        }

        return;
    }


    const labels =
        categories.map(
            item =>
                item.category
        );


    const values =
        categories.map(
            item =>
                Number(
                    item.amount
                )
        );


    if (dashboardChart) {

        dashboardChart.destroy();
    }


    dashboardChart =
        new Chart(
            canvas,
            {
                type: "doughnut",

                data: {

                    labels: labels,

                    datasets: [

                        {
                            data: values
                        }

                    ]
                },

                options: {

                    responsive: true,

                    maintainAspectRatio:
                        false,

                    plugins: {

                        legend: {
                            position:
                                "bottom"
                        },

                        tooltip: {

                            callbacks: {

                                label:
                                    function (
                                        context
                                    ) {

                                        return (
                                            `${context.label}: ` +
                                            formatMoney(
                                                context.raw
                                            )
                                        );
                                    }
                            }
                        }
                    }
                }
            }
        );
}


// ============================================================
// TRANSACTIONS
// ============================================================

async function loadTransactions() {

    const tableBody =
        getElement(
            "transactionTableBody"
        );


    if (!tableBody) {

        console.error(
            "transactionTableBody not found."
        );

        return;
    }


    try {

        // IMPORTANT:
        // Transaction page has its OWN filters.
        // Dashboard month is never used here.

        const monthElement =
            getElement(
                "transactionMonth"
            );

        const typeElement =
            getElement(
                "transactionTypeFilter"
            );

        const categoryElement =
            getElement(
                "transactionCategoryFilter"
            );


        const params = [];


        // Month
        if (
            monthElement &&
            monthElement.value
        ) {

            params.push(
                "month=" +
                encodeURIComponent(
                    monthElement.value
                )
            );
        }


        // Type
        if (
            typeElement &&
            typeElement.value &&
            typeElement.value !== "all"
        ) {

            params.push(
                "type=" +
                encodeURIComponent(
                    typeElement.value
                )
            );
        }


        // Category
        if (
            categoryElement &&
            categoryElement.value.trim()
        ) {

            params.push(
                "category=" +
                encodeURIComponent(
                    categoryElement.value.trim()
                )
            );
        }


        let url =
            "/api/transactions";


        if (
            params.length > 0
        ) {

            url +=
                "?" +
                params.join("&");
        }


        console.log(
            "Loading transactions:",
            url
        );


        const response =
            await fetch(
                url,
                {
                    method: "GET",

                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `Server returned ${response.status}`
            );
        }


        const transactions =
            await response.json();


        console.log(
            "Transactions received:",
            transactions
        );


        if (
            !Array.isArray(
                transactions
            )
        ) {

            throw new Error(
                "Invalid transaction data received."
            );
        }


        renderTransactions(
            transactions,
            tableBody
        );


    } catch (error) {

        console.error(
            "Transaction error:",
            error
        );


        tableBody.innerHTML = `

            <tr>

                <td
                    colspan="6"
                    class="empty-state"
                >

                    Could not load transactions.

                    <br>

                    <small>
                        ${escapeHTML(
                            error.message
                        )}
                    </small>

                </td>

            </tr>

        `;
    }
}


// ============================================================
// RENDER TRANSACTIONS
// ============================================================

function renderTransactions(
    transactions,
    tableBody
) {

    if (
        !Array.isArray(
            transactions
        ) ||
        transactions.length === 0
    ) {

        tableBody.innerHTML = `

            <tr>

                <td
                    colspan="6"
                    class="empty-state"
                >

                    No transactions recorded.

                </td>

            </tr>

        `;

        return;
    }


    let html = "";


    transactions.forEach(
        (transaction) => {

            const type =
                String(
                    transaction.type || ""
                ).toLowerCase();


            const amount =
                Number(
                    transaction.amount || 0
                );


            const sign =
                type === "income"
                    ? "+"
                    : "-";


            const typeClass =
                type === "income"
                    ? "income"
                    : "expense";


            html += `

                <tr>

                    <td>
                        ${escapeHTML(
                            transaction.date || "-"
                        )}
                    </td>


                    <td>

                        <span
                            class="${typeClass}"
                        >
                            ${escapeHTML(
                                transaction.type || "-"
                            )}
                        </span>

                    </td>


                    <td>
                        ${escapeHTML(
                            transaction.category || "-"
                        )}
                    </td>


                    <td>

                        <strong>

                            ${sign}${formatMoney(
                                amount
                            )}

                        </strong>

                    </td>


                    <td>
                        ${escapeHTML(
                            transaction.description || "-"
                        )}
                    </td>


                    <td>

                        <button
                            type="button"
                            class="delete-button"
                            data-delete-id="${Number(
                                transaction.id
                            )}"
                        >
                            Delete
                        </button>

                    </td>

                </tr>

            `;
        }
    );


    tableBody.innerHTML =
        html;


    // Add delete button events
    const deleteButtons =
        tableBody.querySelectorAll(
            "[data-delete-id]"
        );


    deleteButtons.forEach(
        (button) => {

            button.addEventListener(
                "click",
                function () {

                    const id =
                        Number(
                            this.dataset.deleteId
                        );

                    deleteTransaction(
                        id
                    );
                }
            );
        }
    );
}


// ============================================================
// ADD TRANSACTION
// ============================================================

async function addTransaction(
    event
) {

    if (event) {

        event.preventDefault();
    }


    const typeElement =
        getElement(
            "transactionType"
        );

    const categoryElement =
        getElement(
            "transactionCategory"
        );

    const amountElement =
        getElement(
            "transactionAmount"
        );

    const descriptionElement =
        getElement(
            "transactionDescription"
        );

    const dateElement =
        getElement(
            "transactionDate"
        );


    if (
        !typeElement ||
        !categoryElement ||
        !amountElement ||
        !dateElement
    ) {

        console.error(
            "Transaction form is incomplete."
        );

        return;
    }


    const category =
        categoryElement.value.trim();


    const amount =
        Number(
            amountElement.value
        );


    if (!category) {

        alert(
            "Please enter a category."
        );

        return;
    }


    if (
        Number.isNaN(amount) ||
        amount <= 0
    ) {

        alert(
            "Please enter a valid amount."
        );

        return;
    }


    const payload = {

        type:
            typeElement.value,

        category:
            category,

        amount:
            amount,

        description:
            descriptionElement
                ? descriptionElement.value.trim()
                : "",

        date:
            dateElement.value
    };


    try {

        const result =
            await fetchJSON(
                "/api/transactions",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );


        alert(
            result.message ||
            "Transaction added successfully."
        );


        const form =
            getElement(
                "transactionForm"
            );


        if (form) {

            form.reset();
        }


        setDefaultDates();


        // Refresh dashboard and table
        await loadDashboard();

        await loadTransactions();


    } catch (error) {

        alert(
            error.message ||
            "Could not add transaction."
        );
    }
}


// ============================================================
// DELETE TRANSACTION
// ============================================================

async function deleteTransaction(
    transactionId
) {

    if (!transactionId) {
        return;
    }


    const confirmed =
        window.confirm(
            "Delete this transaction?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const result =
            await fetchJSON(
                `/api/transactions/${transactionId}`,
                {
                    method: "DELETE"
                }
            );


        alert(
            result.message ||
            "Transaction deleted."
        );


        await loadDashboard();

        await loadTransactions();


    } catch (error) {

        alert(
            error.message ||
            "Could not delete transaction."
        );
    }
}


// ============================================================
// CLEAR TRANSACTION FILTERS
// ============================================================

function clearTransactionFilters() {

    const monthElement =
        getElement(
            "transactionMonth"
        );

    const typeElement =
        getElement(
            "transactionTypeFilter"
        );

    const categoryElement =
        getElement(
            "transactionCategoryFilter"
        );


    if (monthElement) {

        monthElement.value =
            "";
    }


    if (typeElement) {

        typeElement.value =
            "all";
    }


    if (categoryElement) {

        categoryElement.value =
            "";
    }


    loadTransactions();
}


// ============================================================
// GOALS
// ============================================================

async function loadGoals() {

    const container =
        getElement(
            "goalsContainer"
        );


    if (!container) {
        return;
    }


    try {

        const goals =
            await fetchJSON(
                "/api/goals"
            );


        renderGoals(
            goals,
            container
        );


    } catch (error) {

        console.error(
            "Goals error:",
            error
        );


        container.innerHTML = `

            <div class="empty-state">
                Could not load goals.
            </div>

        `;
    }
}


// ============================================================
// RENDER GOALS
// ============================================================

function renderGoals(
    goals,
    container
) {

    if (
        !Array.isArray(
            goals
        ) ||
        goals.length === 0
    ) {

        container.innerHTML = `

            <div class="empty-state">

                No financial goals added yet.

            </div>

        `;

        return;
    }


    container.innerHTML =
        goals
            .map(
                (goal) => {

                    const percentage =
                        Math.max(
                            0,
                            Math.min(
                                100,
                                Number(
                                    goal.percentage || 0
                                )
                            )
                        );


                    let timeText =
                        "No monthly saving amount set.";


                    if (
                        goal.months_remaining !==
                            null &&
                        goal.months_remaining !==
                            undefined
                    ) {

                        if (
                            Number(
                                goal.months_remaining
                            ) === 0
                        ) {

                            timeText =
                                "Goal reached.";

                        } else {

                            timeText =
                                `${goal.months_remaining} month(s) estimated`;
                        }
                    }


                    return `

                        <div class="goal-card">

                            <div class="goal-header">

                                <div>

                                    <h3>
                                        ${escapeHTML(
                                            goal.name
                                        )}
                                    </h3>

                                    ${
                                        goal.deadline
                                            ? `
                                                <p>
                                                    Deadline:
                                                    ${escapeHTML(
                                                        goal.deadline
                                                    )}
                                                </p>
                                            `
                                            : ""
                                    }

                                </div>


                                <button
                                    type="button"
                                    class="delete-button"
                                    data-delete-goal="${Number(
                                        goal.id
                                    )}"
                                >
                                    Delete
                                </button>

                            </div>


                            <div class="goal-amounts">

                                <span>

                                    Saved:
                                    <strong>
                                        ${formatMoney(
                                            goal.saved
                                        )}
                                    </strong>

                                </span>


                                <span>

                                    Target:
                                    <strong>
                                        ${formatMoney(
                                            goal.target
                                        )}
                                    </strong>

                                </span>

                            </div>


                            <div class="progress-bar">

                                <div
                                    class="progress-fill"
                                    style="
                                        width: ${percentage}%;
                                    "
                                ></div>

                            </div>


                            <div class="goal-footer">

                                <span>
                                    ${percentage.toFixed(1)}%
                                </span>

                                <span>
                                    ${escapeHTML(
                                        timeText
                                    )}
                                </span>

                            </div>

                        </div>

                    `;
                }
            )
            .join("");


    const buttons =
        container.querySelectorAll(
            "[data-delete-goal]"
        );


    buttons.forEach(
        (button) => {

            button.addEventListener(
                "click",
                function () {

                    deleteGoal(
                        Number(
                            this.dataset.deleteGoal
                        )
                    );
                }
            );
        }
    );
}


// ============================================================
// ADD GOAL
// ============================================================

async function addGoal(
    event
) {

    if (event) {

        event.preventDefault();
    }


    const nameElement =
        getElement(
            "goalName"
        );

    const targetElement =
        getElement(
            "goalTarget"
        );

    const savedElement =
        getElement(
            "goalSaved"
        );

    const monthlyElement =
        getElement(
            "goalMonthlySaving"
        );

    const deadlineElement =
        getElement(
            "goalDeadline"
        );


    if (
        !nameElement ||
        !targetElement
    ) {

        return;
    }


    const name =
        nameElement.value.trim();


    const target =
        Number(
            targetElement.value
        );


    const saved =
        savedElement
            ? Number(
                savedElement.value || 0
            )
            : 0;


    const monthly =
        monthlyElement
            ? Number(
                monthlyElement.value || 0
            )
            : 0;


    if (!name) {

        alert(
            "Please enter a goal name."
        );

        return;
    }


    if (
        Number.isNaN(target) ||
        target <= 0
    ) {

        alert(
            "Please enter a valid target amount."
        );

        return;
    }


    try {

        const result =
            await fetchJSON(
                "/api/goals",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            name:
                                name,

                            target:
                                target,

                            saved:
                                saved,

                            monthly:
                                monthly,

                            deadline:
                                deadlineElement
                                    ? deadlineElement.value
                                    : ""
                        })
                }
            );


        alert(
            result.message ||
            "Goal added successfully."
        );


        const form =
            getElement(
                "goalForm"
            );


        if (form) {

            form.reset();
        }


        await loadGoals();


    } catch (error) {

        alert(
            error.message ||
            "Could not add goal."
        );
    }
}


// ============================================================
// DELETE GOAL
// ============================================================

async function deleteGoal(
    goalId
) {

    if (!goalId) {
        return;
    }


    const confirmed =
        window.confirm(
            "Delete this financial goal?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const result =
            await fetchJSON(
                `/api/goals/${goalId}`,
                {
                    method: "DELETE"
                }
            );


        alert(
            result.message ||
            "Goal deleted."
        );


        await loadGoals();


    } catch (error) {

        alert(
            error.message ||
            "Could not delete goal."
        );
    }
}


// ============================================================
// EMI
// ============================================================

async function calculateEMI(
    event
) {

    if (event) {

        event.preventDefault();
    }


    const principalElement =
        getElement(
            "principal"
        );

    const interestElement =
        getElement(
            "annualInterest"
        );

    const monthsElement =
        getElement(
            "loanMonths"
        );

    const resultElement =
        getElement(
            "emiResult"
        );


    if (
        !principalElement ||
        !interestElement ||
        !monthsElement ||
        !resultElement
    ) {

        return;
    }


    try {

        const data =
            await fetchJSON(
                "/api/emi",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            principal:
                                principalElement.value,

                            annual_interest:
                                interestElement.value,

                            months:
                                monthsElement.value
                        })
                }
            );


        resultElement.innerHTML = `

            <div class="emi-result">

                <h3>
                    Loan Summary
                </h3>


                <div class="result-row">

                    <span>
                        Loan Amount
                    </span>

                    <strong>
                        ${formatMoney(
                            data.principal
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Interest Rate
                    </span>

                    <strong>
                        ${Number(
                            data.annual_interest
                        ).toFixed(2)}%
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Duration
                    </span>

                    <strong>
                        ${data.months} months
                    </strong>

                </div>


                <div class="result-row highlight">

                    <span>
                        Monthly EMI
                    </span>

                    <strong>
                        ${formatMoney(
                            data.emi
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Total Payment
                    </span>

                    <strong>
                        ${formatMoney(
                            data.total_payment
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Total Interest
                    </span>

                    <strong>
                        ${formatMoney(
                            data.total_interest
                        )}
                    </strong>

                </div>

            </div>

        `;


    } catch (error) {

        resultElement.textContent =
            error.message ||
            "Could not calculate EMI.";
    }
}


// ============================================================
// WHAT-IF
// ============================================================

async function runWhatIf(
    event
) {

    if (event) {

        event.preventDefault();
    }


    const monthElement =
        getElement(
            "whatIfMonth"
        );

    const incomeElement =
        getElement(
            "incomeChange"
        );

    const expenseElement =
        getElement(
            "expenseChange"
        );

    const resultElement =
        getElement(
            "whatIfResult"
        );


    if (!resultElement) {
        return;
    }


    try {

        const data =
            await fetchJSON(
                "/api/whatif",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({

                            month:
                                monthElement
                                    ? monthElement.value
                                    : "",

                            income_change:
                                incomeElement
                                    ? incomeElement.value || 0
                                    : 0,

                            expense_change:
                                expenseElement
                                    ? expenseElement.value || 0
                                    : 0
                        })
                }
            );


        const difference =
            Number(
                data.difference || 0
            );


        let message;


        if (difference > 0) {

            message =
                "Your projected surplus would increase.";

        } else if (difference < 0) {

            message =
                "Your projected surplus would decrease.";

        } else {

            message =
                "Your projected surplus would remain unchanged.";
        }


        resultElement.innerHTML = `

            <div class="whatif-result">

                <h3>
                    What-If Result
                </h3>


                <div class="result-row">

                    <span>
                        Current Income
                    </span>

                    <strong>
                        ${formatMoney(
                            data.old_income
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Current Expenses
                    </span>

                    <strong>
                        ${formatMoney(
                            data.old_expenses
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Current Surplus
                    </span>

                    <strong>
                        ${formatMoney(
                            data.old_surplus
                        )}
                    </strong>

                </div>


                <hr>


                <div class="result-row">

                    <span>
                        New Income
                    </span>

                    <strong>
                        ${formatMoney(
                            data.new_income
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        New Expenses
                    </span>

                    <strong>
                        ${formatMoney(
                            data.new_expenses
                        )}
                    </strong>

                </div>


                <div class="result-row highlight">

                    <span>
                        New Surplus
                    </span>

                    <strong>
                        ${formatMoney(
                            data.new_surplus
                        )}
                    </strong>

                </div>


                <div class="result-row">

                    <span>
                        Change
                    </span>

                    <strong>
                        ${formatMoney(
                            difference
                        )}
                    </strong>

                </div>


                <p class="result-note">
                    ${escapeHTML(
                        message
                    )}
                </p>

            </div>

        `;


    } catch (error) {

        resultElement.textContent =
            error.message ||
            "Could not run What-If analysis.";
    }
}


// ============================================================
// AI ASSISTANT
// ============================================================

async function askAI() {

    const questionElement =
        getElement(
            "aiQuestion"
        );

    const resultElement =
        getElement(
            "aiResult"
        );


    if (
        !questionElement ||
        !resultElement
    ) {

        console.error(
            "AI elements not found."
        );

        return;
    }


    const question =
        questionElement.value.trim();


    if (!question) {

        resultElement.innerHTML = `

            <div class="ai-empty">

                Please enter a question about your finances.

            </div>

        `;

        questionElement.focus();

        return;
    }


    // --------------------------------------------------------
    // Loading
    // --------------------------------------------------------

    resultElement.innerHTML = `

        <div class="ai-loading">

            <div class="ai-loading-icon">
                🤖
            </div>

            <div>

                <strong>
                    FinPilot is thinking...
                </strong>

            </div>

            <div>

                I'm looking at your financial records
                and working through the numbers.

            </div>

        </div>

    `;


    const button =
        getElement(
            "askAIButton"
        );


    if (button) {

        button.disabled =
            true;

        button.textContent =
            "🤖 Thinking...";
    }


    try {

        const data =
            await fetchJSON(
                "/api/ai",
                {

                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            question:
                                question
                        })
                }
            );


        const answer =
            data.answer ||
            "FinPilot did not generate an answer.";


        resultElement.innerHTML =
            formatAIResponse(
                answer
            );


        resultElement.scrollTop =
            0;


    } catch (error) {

        console.error(
            "AI error:",
            error
        );


        resultElement.innerHTML = `

            <div class="ai-error">

                <h3>
                    FinPilot could not answer right now
                </h3>

                <p>
                    ${escapeHTML(
                        error.message ||
                        "Make sure Flask and Ollama are running."
                    )}
                </p>

            </div>

        `;

    } finally {

        if (button) {

            button.disabled =
                false;

            button.textContent =
                "🤖 Ask FinPilot";
        }
    }
}


// ============================================================
// AI ENTER KEY
// ============================================================

function handleAIEnter(
    event
) {

    // Enter = submit
    // Shift + Enter = new line

    if (
        event.key === "Enter" &&
        !event.shiftKey
    ) {

        event.preventDefault();

        askAI();
    }
}


// ============================================================
// AI MARKDOWN FORMATTER
// ============================================================

function formatAIResponse(
    text
) {

    if (!text) {

        return `
            <div class="ai-empty">
                No answer generated.
            </div>
        `;
    }


    let safeText =
        escapeHTML(
            String(text).trim()
        );


    const lines =
        safeText.split("\n");


    let html = "";


    let unorderedList =
        false;

    let orderedList =
        false;


    let paragraphLines =
        [];


    function closeLists() {

        if (unorderedList) {

            html += "</ul>";

            unorderedList =
                false;
        }


        if (orderedList) {

            html += "</ol>";

            orderedList =
                false;
        }
    }


    function closeParagraph() {

        if (
            paragraphLines.length === 0
        ) {

            return;
        }


        const paragraph =
            paragraphLines
                .join(" ")
                .trim();


        if (paragraph) {

            html += `
                <p>
                    ${paragraph}
                </p>
            `;
        }


        paragraphLines =
            [];
    }


    for (
        let line of lines
    ) {

        line =
            line.trim();


        // Empty line
        if (!line) {

            closeParagraph();

            closeLists();

            continue;
        }


        // H1
        if (
            line.startsWith(
                "# "
            )
        ) {

            closeParagraph();
            closeLists();

            html += `
                <h1>
                    ${line.substring(2)}
                </h1>
            `;

            continue;
        }


        // H2
        if (
            line.startsWith(
                "## "
            )
        ) {

            closeParagraph();
            closeLists();

            html += `
                <h2>
                    ${line.substring(3)}
                </h2>
            `;

            continue;
        }


        // H3
        if (
            line.startsWith(
                "### "
            )
        ) {

            closeParagraph();
            closeLists();

            html += `
                <h3>
                    ${line.substring(4)}
                </h3>
            `;

            continue;
        }


        // Horizontal rule
        if (
            line === "---" ||
            line === "***"
        ) {

            closeParagraph();
            closeLists();

            html += "<hr>";

            continue;
        }


        // Number list
        const numbered =
            line.match(
                /^(\d+)\.\s+(.*)$/
            );


        if (numbered) {

            closeParagraph();


            if (!orderedList) {

                if (unorderedList) {

                    html += "</ul>";

                    unorderedList =
                        false;
                }


                html += "<ol>";

                orderedList =
                    true;
            }


            html += `
                <li>
                    ${numbered[2]}
                </li>
            `;

            continue;
        }


        // Bullet list
        const bullet =
            line.match(
                /^[-*•]\s+(.*)$/
            );


        if (bullet) {

            closeParagraph();


            if (!unorderedList) {

                if (orderedList) {

                    html += "</ol>";

                    orderedList =
                        false;
                }


                html += "<ul>";

                unorderedList =
                    true;
            }


            html += `
                <li>
                    ${bullet[1]}
                </li>
            `;

            continue;
        }


        // Blockquote
        if (
            line.startsWith(
                "&gt; "
            )
        ) {

            closeParagraph();
            closeLists();

            html += `
                <blockquote>
                    ${line.substring(5)}
                </blockquote>
            `;

            continue;
        }


        // Regular paragraph
        closeLists();

        paragraphLines.push(
            line
        );
    }


    closeParagraph();

    closeLists();


    // Bold
    html =
        html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


    // Italic
    html =
        html.replace(
            /(?<!\*)\*([^*]+)\*(?!\*)/g,
            "<em>$1</em>"
        );


    // Inline code
    html =
        html.replace(
            /`([^`]+)`/g,
            "<code>$1</code>"
        );


    return html;
}


// ============================================================
// OLLAMA STATUS
// ============================================================

async function checkOllama() {

    const statusElement =
        getElement(
            "ollamaStatus"
        );

    const modelElement =
        getElement(
            "ollamaModel"
        );


    try {

        const data =
            await fetchJSON(
                "/api/ollama"
            );


        if (statusElement) {

            if (data.connected) {

                statusElement.textContent =
                    "Connected";

                statusElement.classList.add(
                    "connected"
                );

                statusElement.classList.remove(
                    "disconnected"
                );

            } else {

                statusElement.textContent =
                    "Disconnected";

                statusElement.classList.add(
                    "disconnected"
                );

                statusElement.classList.remove(
                    "connected"
                );
            }
        }


        if (modelElement) {

            if (
                Array.isArray(
                    data.models
                ) &&
                data.models.length > 0
            ) {

                modelElement.textContent =
                    data.models.join(
                        ", "
                    );

            } else {

                modelElement.textContent =
                    "No Qwen model found";
            }
        }


    } catch (error) {

        console.error(
            "Ollama error:",
            error
        );


        if (statusElement) {

            statusElement.textContent =
                "Unavailable";
        }


        if (modelElement) {

            modelElement.textContent =
                "Unable to detect model";
        }
    }
}


// ============================================================
// SET DEFAULT DATE
// ============================================================

function setDefaultDates() {

    const dateElement =
        getElement(
            "transactionDate"
        );


    if (
        dateElement &&
        !dateElement.value
    ) {

        dateElement.value =
            getTodayDate();
    }
}


// ============================================================
// TODAY DATE
// ============================================================

function getTodayDate() {

    const now =
        new Date();


    const year =
        now.getFullYear();


    const month =
        String(
            now.getMonth() + 1
        ).padStart(
            2,
            "0"
        );


    const day =
        String(
            now.getDate()
        ).padStart(
            2,
            "0"
        );


    return `${year}-${month}-${day}`;
}


// ============================================================
// SETUP FILTERS
// ============================================================

function setupFilters() {

    // Dashboard month
    const dashboardMonth =
        getElement(
            "dashboardMonth"
        );


    if (dashboardMonth) {

        dashboardMonth.addEventListener(
            "change",
            loadDashboard
        );
    }


    // Transaction month
    const transactionMonth =
        getElement(
            "transactionMonth"
        );


    if (transactionMonth) {

        transactionMonth.addEventListener(
            "change",
            loadTransactions
        );
    }


    // Transaction type
    const typeFilter =
        getElement(
            "transactionTypeFilter"
        );


    if (typeFilter) {

        typeFilter.addEventListener(
            "change",
            loadTransactions
        );
    }


    // Transaction category
    const categoryFilter =
        getElement(
            "transactionCategoryFilter"
        );


    if (categoryFilter) {

        categoryFilter.addEventListener(
            "input",
            debounce(
                loadTransactions,
                350
            )
        );
    }


    // Clear filters
    const clearButton =
        getElement(
            "clearTransactionFilters"
        );


    if (clearButton) {

        clearButton.addEventListener(
            "click",
            clearTransactionFilters
        );
    }
}


// ============================================================
// DEBOUNCE
// ============================================================

function debounce(
    callback,
    delay
) {

    let timer;


    return function () {

        clearTimeout(
            timer
        );


        timer =
            setTimeout(
                () => {

                    callback();

                },
                delay
            );
    };
}


// ============================================================
// SETUP FORMS
// ============================================================

function setupForms() {

    const transactionForm =
        getElement(
            "transactionForm"
        );


    if (transactionForm) {

        transactionForm.addEventListener(
            "submit",
            addTransaction
        );
    }


    const goalForm =
        getElement(
            "goalForm"
        );


    if (goalForm) {

        goalForm.addEventListener(
            "submit",
            addGoal
        );
    }


    const emiForm =
        getElement(
            "emiForm"
        );


    if (emiForm) {

        emiForm.addEventListener(
            "submit",
            calculateEMI
        );
    }


    const whatIfForm =
        getElement(
            "whatIfForm"
        );


    if (whatIfForm) {

        whatIfForm.addEventListener(
            "submit",
            runWhatIf
        );
    }


    const aiButton =
        getElement(
            "askAIButton"
        );


    if (aiButton) {

        aiButton.addEventListener(
            "click",
            askAI
        );
    }


    const aiQuestion =
        getElement(
            "aiQuestion"
        );


    if (aiQuestion) {

        aiQuestion.addEventListener(
            "keydown",
            handleAIEnter
        );
    }


    const refreshOllama =
        getElement(
            "refreshOllama"
        );


    if (refreshOllama) {

        refreshOllama.addEventListener(
            "click",
            checkOllama
        );
    }
}


// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    async function () {

        console.log(
            "FinPilot JavaScript loaded."
        );


        setupNavigation();

        setupFilters();

        setupForms();

        setDefaultDates();


        // ----------------------------------------------------
        // Show dashboard
        // ----------------------------------------------------

        showPage(
            "dashboard"
        );


        // ----------------------------------------------------
        // Load data
        // ----------------------------------------------------

        await loadDashboard();

        await loadTransactions();

        await loadGoals();

        await checkOllama();


        console.log(
            "FinPilot initialized successfully."
        );
    }
);


// ============================================================
// GLOBAL FUNCTIONS
// ============================================================

window.showPage =
    showPage;

window.loadDashboard =
    loadDashboard;

window.loadTransactions =
    loadTransactions;

window.addTransaction =
    addTransaction;

window.deleteTransaction =
    deleteTransaction;

window.loadGoals =
    loadGoals;

window.addGoal =
    addGoal;

window.deleteGoal =
    deleteGoal;

window.calculateEMI =
    calculateEMI;

window.runWhatIf =
    runWhatIf;

window.askAI =
    askAI;

window.handleAIEnter =
    handleAIEnter;

window.checkOllama =
    checkOllama;

window.formatMoney =
    formatMoney;