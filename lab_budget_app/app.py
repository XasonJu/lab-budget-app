import streamlit as st
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
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

# ====== Google Sheets 認證 ======
keyfile_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict, scope)
gc = gspread.authorize(credentials)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1F2SDyauxsE229BuM8mv7kkfIuWz6LPGnFQNCjzKyKp8/edit?usp=sharing"

try:
    worksheet = gc.open_by_url(SHEET_URL).sheet1
except Exception as e:
    st.error("❌ 無法讀取 Google Sheets。請確認 Service Account 有被授權。")
    st.stop()

# ====== 資料初始化 ======
def load_records():
    records = worksheet.get_all_records()
    df = pd.DataFrame(records)
    return df

def save_record(record):
    worksheet.append_row(record)

def delete_record(index):
    worksheet.delete_rows(index + 2)  # +2 因為有 header

df = load_records()
st.subheader("📋 現有紀錄")
st.dataframe(df)

# ====== 新增資料表單 ======
st.subheader("➕ 新增資料")
with st.form("new_record_form"):
    plan = st.text_input("計畫名稱")
    item = st.text_input("經費項目")
    amount = st.number_input("花費金額", min_value=0)
    invoice_date = st.date_input("發票日期")
    invoice_amount = st.number_input("發票金額", min_value=0)
    submitted = st.form_submit_button("新增")

    if submitted:
        new_row = [
            plan,
            item,
            int(amount),
            str(invoice_date),
            int(invoice_amount),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ]
        save_record(new_row)
        st.success("已新增資料！請重新整理查看最新紀錄。")

# ====== 刪除功能 ======
st.subheader("🗑️ 刪除資料")
if len(df) > 0:
    to_delete = st.number_input("輸入要刪除的資料編號（從 0 開始）", min_value=0, max_value=len(df)-1)
    if st.button("確認刪除"):
        delete_record(to_delete)
        st.success(f"已刪除第 {to_delete} 筆資料。請重新整理查看更新結果。")
else:
    st.info("尚無資料可刪除。")
