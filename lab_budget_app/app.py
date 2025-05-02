import streamlit as st
import pandas as pd
from datetime import datetime

# ====== 登入驗證 ======
st.title("🐷 Lab Budget Tracker")
PASSWORD = "IC203"
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    password = st.text_input("請輸入密碼：", type="password")
    if password == PASSWORD:
        st.session_state["authenticated"] = True
        st.rerun()
    else:
        st.stop()

# ====== Session 初始化 ======
if "records" not in st.session_state:
    st.session_state["records"] = []

# ====== 資料顯示 ======
df = pd.DataFrame(
    st.session_state["records"],
    columns=["計畫名稱", "經費項目", "花費金額", "發票日期", "發票金額", "紀錄時間"]
)
st.subheader("📋 現有紀錄")
st.dataframe(df)

# ====== 新增資料 ======
st.subheader("➕ 新增資料")
with st.form("new_record_form"):
    plan = st.text_input("計畫名稱")
    item = st.text_input("經費項目")
    amount = st.number_input("花費金額", min_value=0)
    invoice_date = st.date_input("發票日期")
    invoice_amount = st.number_input("發票金額", min_value=0)
    submitted = st.form_submit_button("新增")

    if submitted:
        new_row = [plan, item, int(amount), str(invoice_date), int(invoice_amount), datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
        st.session_state["records"].append(new_row)
        st.success("✅ 已新增資料！請查看上方表格。")
        st.rerun()

# ====== 刪除功能 ======
st.subheader("🗑️ 刪除資料")
if len(df) > 0:
    to_delete = st.number_input("輸入要刪除的資料編號（從 0 開始）", min_value=0, max_value=len(df)-1)
    if st.button("確認刪除"):
        del st.session_state["records"][to_delete]
        st.success(f"✅ 已刪除第 {to_delete} 筆資料。")
        st.rerun()
else:
    st.info("尚無資料可刪除。")
