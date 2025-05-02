import streamlit as st
import json
import gspread
import pandas as pd
from datetime import date
from oauth2client.service_account import ServiceAccountCredentials

# ====== 登入驗證 ======
PASSWORD = "IC203"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("請輸入密碼", type="password")
    if pwd == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# ====== Google Sheets 授權設定 ======
keyfile_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    keyfile_dict,
    scopes=["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
)
gc = gspread.authorize(credentials)

# ====== Google Sheet ID 與名稱 ======
sheet_id = "1F2SDyauxsE229BuM8mv7kkfIuWz6LPGnFQNCjzKyKp8"
worksheet_name = "工作表1"

# ====== 連接工作表並讀取資料 ======
sheet = gc.open_by_key(sheet_id)
worksheet = sheet.worksheet(worksheet_name)

# 讀取資料為 DataFrame
data = worksheet.get_all_records()
df = pd.DataFrame(data)
st.header("📊 實驗室經費記錄")
st.dataframe(df)

# ====== 新增資料表單 ======
st.subheader("➕ 新增資料")
with st.form("add_row"):
    col1 = st.text_input("計畫名稱")
    col2 = st.number_input("花費金額", min_value=0)
    col3 = st.text_input("經費項目")
    col4 = st.date_input("發票日期", value=date.today())
    col5 = st.text_input("發票金額")
    submitted = st.form_submit_button("新增資料")
    if submitted:
        worksheet.append_row([col1, col2, col3, str(col4), col5])
        st.success("✅ 資料已新增，請重新整理查看最新結果")
