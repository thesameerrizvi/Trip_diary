import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Trip Diary", page_icon="", layout="centered")

st.title(" Trip Diary")
st.write("Add friends and their expenses, then get exact *who pays whom* settlement + download CSV/Excel.")

# Session state
if "expenses" not in st.session_state:
    st.session_state.expenses = {}  # {"Sameer": 500, "Aman": 200}

def add_expense(name, amount):
    st.session_state.expenses[name] = st.session_state.expenses.get(name, 0) + amount

def generate_transfers(expenses_dict):
    total = sum(expenses_dict.values())
    people = len(expenses_dict)
    per_person = total / people

    balances = {}
    for name, spent in expenses_dict.items():
        balances[name] = round(spent - per_person, 2)

    creditors = []
    debtors = []

    for name, bal in balances.items():
        if bal > 0:
            creditors.append([name, bal])
        elif bal < 0:
            debtors.append([name, abs(bal)])

    creditors.sort(key=lambda x: x[1], reverse=True)
    debtors.sort(key=lambda x: x[1], reverse=True)

    transfers = []
    i, j = 0, 0
    while i < len(debtors) and j < len(creditors):
        debtor_name, debtor_amt = debtors[i]
        creditor_name, creditor_amt = creditors[j]

        pay = round(min(debtor_amt, creditor_amt), 2)
        if pay > 0:
            transfers.append((debtor_name, creditor_name, pay))

        debtors[i][1] = round(debtors[i][1] - pay, 2)
        creditors[j][1] = round(creditors[j][1] - pay, 2)

        if debtors[i][1] == 0:
            i += 1
        if creditors[j][1] == 0:
            j += 1

    return total, per_person, balances, transfers

def create_csv(expenses, transfers, total, per_person):
    rows = []
    rows.append(["Trip Expence Report"])
    rows.append([])
    rows.append(["Total Expense", f"{total:.2f}"])
    rows.append(["Per Person Share", f"{per_person:.2f}"])
    rows.append([])

    rows.append(["Name", "Spent"])
    for n, s in expenses.items():
        rows.append([n, f"{s:.2f}"])

    rows.append([])
    rows.append(["Exact Transfers (Who Pays Who)"])
    rows.append(["Payer", "Receiver", "Amount"])
    if len(transfers) == 0:
        rows.append(["-", "-", "0"])
    else:
        for payer, receiver, amt in transfers:
            rows.append([payer, receiver, f"{amt:.2f}"])

    df = pd.DataFrame(rows)
    return df.to_csv(index=False, header=False).encode("utf-8")

def create_excel(expenses, transfers, total, per_person):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_exp = pd.DataFrame({"Name": list(expenses.keys()), "Spent": list(expenses.values())})
        df_trans = pd.DataFrame(transfers, columns=["Payer", "Receiver", "Amount"])

        summary = pd.DataFrame({
            "Metric": ["Total Expense", "Per Person Share"],
            "Value": [round(total, 2), round(per_person, 2)]
        })

        summary.to_excel(writer, index=False, sheet_name="Summary")
        df_exp.to_excel(writer, index=False, sheet_name="Expenses")
        if len(df_trans) == 0:
            pd.DataFrame([["-", "-", 0]], columns=["Payer", "Receiver", "Amount"]).to_excel(
                writer, index=False, sheet_name="Transfers"
            )
        else:
            df_trans.to_excel(writer, index=False, sheet_name="Transfers")

    return output.getvalue()

# UI: Add expense
st.subheader(" Add Expense")
col1, col2 = st.columns(2)

with col1:
    name = st.text_input("Friend Name")
with col2:
    amount = st.number_input("Amount Spent ()", min_value=0.0, step=10.0)

if st.button("Add Expense "):
    if name.strip() == "":
        st.error("Please enter a friend name!")
    else:
        add_expense(name.strip(), float(amount))
        st.success(f"Added {amount:.2f} for {name.strip()}")

# Show table
st.subheader(" Current Expenses")
if len(st.session_state.expenses) == 0:
    st.info("No expenses added yet.")
else:
    df = pd.DataFrame(list(st.session_state.expenses.items()), columns=["Name", "Spent (₹)"])
    st.dataframe(df, use_container_width=True)

# Calculate settlement
st.subheader(" Settlement Result")
if st.button("Calculate Settlement "):
    if len(st.session_state.expenses) < 2:
        st.error("Add at least 2 people to calculate settlement.")
    else:
        total, per_person, balances, transfers = generate_transfers(st.session_state.expenses)

        st.write(f" **Total Expense:** {total:.2f}")
        st.write(f" **Per Person Share:** {per_person:.2f}")

        st.markdown("###  Balance (GET / PAY)")
        for n, b in balances.items():
            if b > 0:
                st.write(f" **{n}** will GET **{b:.2f}**")
            elif b < 0:
                st.write(f" **{n}** will PAY **{abs(b):.2f}**")
            else:
                st.write(f" **{n}** is settled (₹0)")

        st.markdown("###  Exact Transfers (Who Pays Who)")
        if len(transfers) == 0:
            st.success("Everyone is settled. No transfers needed ")
        else:
            df_t = pd.DataFrame(transfers, columns=["Payer", "Receiver", "Amount "])
            st.table(df_t)

        # Download
        st.markdown("### ⬇ Download Report")
        csv_data = create_csv(st.session_state.expenses, transfers, total, per_person)
        excel_data = create_excel(st.session_state.expenses, transfers, total, per_person)

        st.download_button(" Download CSV", data=csv_data, file_name="trip_report.csv", mime="text/csv")
        st.download_button(" Download Excel", data=excel_data, file_name="trip_report.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# Reset
if st.button("Reset All "):
    st.session_state.expenses = {}
    st.success("Reset done ")
