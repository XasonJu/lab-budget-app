
import streamlit as st
import pandas as pd
import gspread
from datetime import datetime, date
from oauth2client.service_account import ServiceAccountCredentials

# --- 登入驗證 ---
PASSWORD = "IC203"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("請輸入密碼以登入", type="password")
    if pwd == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# --- Google Sheets 設定 ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("lab_budget_app/gspread_key.json", scope)
gc = gspread.authorize(credentials)

SHEET_URL = "https://docs.google.com/spreadsheets/d/1F2SDyauxsE229BuM8mv7kkfIuWz6LPGnFQNCjzKyKp8/edit#gid=0"
sheet = gc.open_by_url(SHEET_URL)
ws = sheet.sheet1

# --- 資料欄位 ---
columns = ['計畫名稱', '人事費', '業務費', '雜支費', '設備費', '國外差旅費', '總預算', '到期日', '建立時間']
try:
    records = pd.DataFrame(ws.get_all_records())
except:
    records = pd.DataFrame(columns=columns)

st.title("實驗室預算追蹤 App（Google Sheets 同步）")

# --- 顯示目前所有計畫資料 ---
if not records.empty:
    st.subheader("📊 所有計畫預算與狀態")
    records['到期日'] = pd.to_datetime(records['到期日'], errors='coerce')
    records['剩餘天數'] = (records['到期日'] - pd.to_datetime(date.today())).dt.days

    def color_deadline(row):
        days = row['剩餘天數']
        if days <= 30:
            return '🔴'
        elif days <= 60:
            return '🟡'
        else:
            return '🟢'

    records['狀態'] = records.apply(color_deadline, axis=1)
    st.dataframe(records[columns + ['剩餘天數', '狀態']], use_container_width=True)

# --- 新增預算計畫 ---
st.subheader("➕ 新增或更新預算計畫")
with st.form("new_budget"):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("計畫名稱")
        salary = st.number_input("人事費", 0)
        work = st.number_input("業務費", 0)
        misc = st.number_input("雜支費", 0)
    with col2:
        equip = st.number_input("設備費", 0)
        travel = st.number_input("國外差旅費", 0)
        deadline = st.date_input("到期日", value=date.today())
    submitted = st.form_submit_button("✅ 儲存計畫")

    if submitted and name:
        total = salary + work + misc + equip + travel
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = [name, salary, work, misc, equip, travel, total, str(deadline), now]

        # 若計畫已存在，則先刪除
        existing = records[records['計畫名稱'] == name]
        if not existing.empty:
            row_index = existing.index[0] + 2
            ws.delete_rows(row_index)

        ws.append_row(new_row)
        st.success("✅ 資料已儲存，請重新整理以更新畫面")

# --- 刪除功能 ---
st.subheader("🗑 刪除資料")
if not records.empty:
    delete_target = st.selectbox("選擇要刪除的計畫", records['計畫名稱'].tolist())
    if st.button("刪除這筆計畫"):
        del_row = records[records['計畫名稱'] == delete_target].index[0] + 2
        ws.delete_rows(del_row)
        st.success("❌ 已刪除，請重新整理")
