import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# === 密碼驗證 ===
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

# === Google Sheets 授權 ===
keyfile_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict, scope)
gc = gspread.authorize(credentials)

# === Google Sheet 連結 ===
SHEET_URL = "https://docs.google.com/spreadsheets/d/1F2SDyauxsE229BuM8mv7kkfIuWz6LPGnFQNCjzKyKp8/edit"
worksheet = gc.open_by_url(SHEET_URL).sheet1

# === 讀取現有資料 ===
records = worksheet.get_all_records()
df = pd.DataFrame(records)

st.title("💰 Lab Budget Tracker")

# === 資料輸入表單 ===
with st.form("input_form"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("發票日期")
        plan = st.text_input("計畫名稱")
    with col2:
        item = st.text_input("經費項目")
        amount = st.number_input("花費金額", min_value=0)
        invoice = st.number_input("發票金額", min_value=0)
    submitted = st.form_submit_button("新增紀錄")

# === 新增至 Google Sheets ===
if submitted:
    new_row = {
        "發票日期": date.strftime("%Y-%m-%d"),
        "計畫名稱": plan,
        "經費項目": item,
        "花費金額": amount,
        "發票金額": invoice,
        "新增時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    worksheet.append_row(list(new_row.values()))
    st.success("✅ 新增成功！頁面即將更新")
    st.experimental_rerun()

# === 顯示目前資料 ===
st.subheader("📋 所有紀錄")
if not df.empty:
    st.dataframe(df)

    # === 資料刪除 ===
    st.subheader("❌ 刪除特定資料")
    row_to_delete = st.number_input("輸入要刪除的列號（從第 2 列起）", min_value=2, step=1)
    if st.button("刪除該列"):
        worksheet.delete_row(row_to_delete)
        st.warning(f"🗑️ 已刪除第 {row_to_delete} 列")
        st.experimental_rerun()
else:
    st.info("目前尚無任何紀錄。請先新增。")
