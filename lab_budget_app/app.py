
import streamlit as st
import pandas as pd
from datetime import datetime, date

BUDGET_CATEGORIES = ['人事費', '業務費', '雜支費', '設備費', '國外差旅費']

@st.cache_data
def init_data():
    return pd.DataFrame(columns=[
        '計畫名稱', '花費金額', '經費項目', '預計/實際', '發票日期', '發票金額', '備註'
    ])

if 'records' not in st.session_state:
    st.session_state.records = init_data()
if 'budgets' not in st.session_state:
    st.session_state.budgets = {}

st.set_page_config(layout="wide")
st.title("💰 實驗室經費紀錄與預算追蹤")

# === 各計畫統計放最上面 ===
st.header("📊 各計畫經費統計與到期狀態")
summary_rows = []
today = date.today()

for project, info in st.session_state.budgets.items():
    budget_dict = info['預算']
    due_date = info['到期日']
    days_left = (due_date - today).days

    if days_left <= 30:
        alert = f"🔥 剩 {days_left} 天"
    elif days_left <= 90:
        alert = f"⚠️ 剩 {days_left} 天"
    else:
        alert = f"✅ 剩 {days_left} 天"

    project_records = st.session_state.records[st.session_state.records['計畫名稱'] == project]
    total_budget = sum(budget_dict.values())
    planned = project_records[project_records['預計/實際'] == '預計']['花費金額'].sum()
    actual = project_records[project_records['預計/實際'] == '實際']['花費金額'].sum()
    total_spent = planned + actual
    remaining = total_budget - total_spent
    execution_rate = (total_spent / total_budget * 100) if total_budget > 0 else 0.0

    summary_rows.append({
        '計畫名稱': project,
        '預算數': round(total_budget, 2),
        '預計花費': round(planned, 2),
        '實際花費': round(actual, 2),
        '總花費': round(total_spent, 2),
        '總餘額': round(remaining, 2),
        '執行率(%)': f"{execution_rate:.1f}%",
        '到期日': due_date.strftime('%Y-%m-%d'),
        '剩餘天數': alert
    })

summary_df = pd.DataFrame(summary_rows)
st.dataframe(summary_df, use_container_width=True)

# === 匯出選擇 ===
st.header("📤 匯出資料")
export_type = st.radio("選擇匯出類型", ["統計報表", "每筆紀錄"])
if export_type == "統計報表":
    if "剩餘天數" in summary_df.columns:
    export_df = summary_df.drop(columns=["剩餘天數"])
else:
    export_df = summary_df.copy()
    st.download_button(
        label="⬇️ 下載統計報表 CSV",
        data=export_df.to_csv(index=False).encode('utf-8-sig'),
        file_name='lab_budget_summary.csv',
        mime='text/csv'
    )
else:
    st.download_button(
        label="⬇️ 下載紀錄明細 CSV",
        data=st.session_state.records.to_csv(index=False).encode('utf-8-sig'),
        file_name='lab_budget_records.csv',
        mime='text/csv'
    )

# === 經費紀錄輸入 ===
st.header("➕ 新增經費紀錄")
if st.session_state.budgets:
    with st.form("add_record_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected_project = st.selectbox("選擇計畫", options=list(st.session_state.budgets.keys()))
            amount = st.text_input("花費金額", placeholder="輸入金額", key="amount_input")
            category = st.selectbox("經費項目", options=BUDGET_CATEGORIES)
            note = st.text_input("備註", placeholder="如：掃描電鏡耗材")
        with col2:
            is_planned = st.selectbox("預計/實際", options=['預計', '實際'])
            invoice_date = st.date_input("發票日期（可為空）", value=date.today())
            invoice_amount = st.text_input("發票金額（可為空）", placeholder="輸入金額", key="invoice_input")

        add_clicked = st.form_submit_button("新增紀錄")
        if add_clicked:
            try:
                amount_val = float(amount)
                invoice_val = float(invoice_amount) if invoice_amount else None
                new_record = {
                    '計畫名稱': selected_project,
                    '花費金額': amount_val,
                    '經費項目': category,
                    '預計/實際': is_planned,
                    '發票日期': invoice_date if is_planned == '實際' else None,
                    '發票金額': invoice_val if is_planned == '實際' else None,
                    '備註': note
                }
                st.session_state.records = pd.concat([
                    st.session_state.records, pd.DataFrame([new_record])
                ], ignore_index=True)
                st.success("✅ 經費紀錄已新增")
            except ValueError:
                st.error("金額欄位請輸入數字")

# === 所有紀錄 ===
st.header("📋 所有經費紀錄")
st.dataframe(st.session_state.records, use_container_width=True)

# === 預算設定放最下方 ===
st.header("🗂️ 設定計畫預算與到期日")
with st.form("budget_form"):
    project_name = st.text_input("計畫名稱", placeholder="例如：科技部112年度計畫")
    budget_cols = st.columns(len(BUDGET_CATEGORIES))
    budget_values = {}
    for i, cat in enumerate(BUDGET_CATEGORIES):
        with budget_cols[i]:
            budget_values[cat] = st.text_input(f"{cat}", placeholder="輸入金額", key=f"budget_{cat}")
    due_date = st.date_input("計畫到期日", value=date.today())
    submitted = st.form_submit_button("新增 / 更新預算")
    if submitted and project_name:
        try:
            clean_budget = {k: float(v) if v else 0.0 for k, v in budget_values.items()}
            st.session_state.budgets[project_name] = {
                '預算': clean_budget,
                '到期日': due_date
            }
            st.success(f"✅ {project_name} 已儲存")
        except ValueError:
            st.error("請確認每一筆預算都輸入為數字")
