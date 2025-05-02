import streamlit as st
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ====== 頁面設定 ======
st.set_page_config(
    page_title="實驗室經費管理系統",
    page_icon="🧪",
    layout="wide"
)

# ====== 樣式設定 ======
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1E88E5;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #43A047;
    }
    .warning-box {
        background-color: #FFF8E1;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #FFA000;
    }
    .danger-box {
        background-color: #FFEBEE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #E53935;
    }
</style>
""", unsafe_allow_html=True)

# ====== 登入驗證 (只需密碼) ======
st.markdown("<h1 class='main-header'>🧪 實驗室經費管理系統</h1>", unsafe_allow_html=True)

# 設定系統密碼
PASSWORD = "IC203"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("<div class='info-box'>請輸入密碼以繼續</div>", unsafe_allow_html=True)
    password = st.text_input("密碼：", type="password")
    if st.button("登入"):
        if password == PASSWORD:
            st.session_state["authenticated"] = True
            st.success("登入成功！")
            st.rerun()
        else:
            st.error("密碼錯誤！")
    st.stop()

# ====== Google Sheets 認證 ======
@st.cache_resource
def get_gspread_client():
    keyfile_dict = json.loads(st.secrets["GOOGLE_SERVICE_ACCOUNT"])
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(keyfile_dict, scope)
    return gspread.authorize(credentials)

try:
    gc = get_gspread_client()
    SHEET_URL = "https://docs.google.com/spreadsheets/d/你的新Google表格ID/edit?usp=sharing"  # 替換為你的表格URL
    
    # 確保所有需要的工作表存在
    spreadsheet = gc.open_by_url(SHEET_URL)
    
    # 檢查並創建所需的工作表
    sheet_names = [sheet.title for sheet in spreadsheet.worksheets()]
    
    if "經費記錄" not in sheet_names:
        spreadsheet.add_worksheet(title="經費記錄", rows=1000, cols=20)
        records_sheet = spreadsheet.worksheet("經費記錄")
        records_sheet.append_row([
            "計畫名稱", "經費項目", "花費金額", "發票日期", "發票金額", "記錄時間", "備註"
        ])
    else:
        records_sheet = spreadsheet.worksheet("經費記錄")
    
    if "預算設定" not in sheet_names:
        spreadsheet.add_worksheet(title="預算設定", rows=100, cols=10)
        budget_sheet = spreadsheet.worksheet("預算設定")
        budget_sheet.append_row(["計畫名稱", "總預算", "設定日期", "備註"])
    else:
        budget_sheet = spreadsheet.worksheet("預算設定")
    
    if "類別設定" not in sheet_names:
        spreadsheet.add_worksheet(title="類別設定", rows=100, cols=10)
        category_sheet = spreadsheet.worksheet("類別設定")
        category_sheet.append_row(["經費類別", "說明"])
        # 預設類別
        default_categories = [
            ["耗材", "實驗室日常消耗品"],
            ["儀器設備", "實驗設備購買"],
            ["薪資", "研究助理、工讀生薪資"],
            ["差旅", "出差、會議費用"],
            ["其他", "其他支出"]
        ]
        for cat in default_categories:
            category_sheet.append_row(cat)
    else:
        category_sheet = spreadsheet.worksheet("類別設定")
        
except Exception as e:
    st.markdown("<div class='danger-box'>❌ 無法連接到 Google Sheets。請確認服務帳號設定正確。</div>", unsafe_allow_html=True)
    st.error(f"錯誤詳情: {e}")
    st.stop()

# ====== 資料處理函數 ======
@st.cache_data(ttl=60)  # 快取 60 秒
def load_records():
    records = records_sheet.get_all_records()
    df = pd.DataFrame(records)
    if not df.empty and "發票日期" in df.columns:
        df["發票日期"] = pd.to_datetime(df["發票日期"]).dt.date
    return df

@st.cache_data(ttl=60)
def load_budgets():
    budgets = budget_sheet.get_all_records()
    return pd.DataFrame(budgets)

@st.cache_data(ttl=60)
def load_categories():
    categories = category_sheet.get_all_records()
    return pd.DataFrame(categories)

def save_record(record):
    records_sheet.append_row(record)

def save_budget(budget):
    budget_sheet.append_row(budget)

def save_category(category):
    category_sheet.append_row(category)

def delete_record(index):
    records_sheet.delete_rows(index + 2)  # +2 因為有 header

def delete_budget(index):
    budget_sheet.delete_rows(index + 2)

def delete_category(index):
    category_sheet.delete_rows(index + 2)

def update_record(index, record):
    for i, value in enumerate(record):
        records_sheet.update_cell(index + 2, i + 1, value)

def update_budget(index, budget):
    for i, value in enumerate(budget):
        budget_sheet.update_cell(index + 2, i + 1, value)

# ====== 加載資料 ======
records_df = load_records()
budgets_df = load_budgets()
categories_df = load_categories()

# ====== 側邊欄選單 ======
with st.sidebar:
    st.image("https://i.imgur.com/CQoUZjC.png", width=100)  # 預設的實驗室圖標
    st.markdown(f"### 歡迎使用實驗室經費管理系統")
    
    menu = st.radio(
        "功能選單",
        ["📊 儀表板", "💰 經費記錄", "📝 預算管理", "🏷️ 類別管理", "📈 統計分析", "⚙️ 設定"]
    )
    
    st.markdown("---")
    if st.button("🔄 重新整理資料"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    st.info("系統版本: v1.0.0")
    if st.button("登出"):
        st.session_state["authenticated"] = False
        st.rerun()

# ====== 主內容 ======
if menu == "📊 儀表板":
    st.markdown("<h2 class='sub-header'>📊 儀表板</h2>", unsafe_allow_html=True)
    
    # 資料統計
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_projects = len(budgets_df["計畫名稱"].unique()) if not budgets_df.empty else 0
        st.metric("計畫總數", total_projects)
    
    with col2:
        total_records = len(records_df) if not records_df.empty else 0
        st.metric("紀錄總數", total_records)
    
    with col3:
        total_budget = budgets_df["總預算"].sum() if not budgets_df.empty else 0
        st.metric("預算總額", f"NT$ {total_budget:,.0f}")
    
    with col4:
        total_spent = records_df["花費金額"].sum() if not records_df.empty else 0
        remaining = total_budget - total_spent
        st.metric("剩餘預算", f"NT$ {remaining:,.0f}", delta=f"{remaining/total_budget*100:.1f}%" if total_budget > 0 else "0%")
    
    # 這裡可以添加更多儀表板元素，例如圖表和數據摘要
    # ...

elif menu == "💰 經費記錄":
    st.markdown("<h2 class='sub-header'>💰 經費記錄</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 新增記錄", "🔍 查看與管理"])
    
    with tab1:
        st.markdown("<h3>新增經費紀錄</h3>", unsafe_allow_html=True)
        
        # 取得可用的計畫和類別列表
        available_projects = budgets_df["計畫名稱"].tolist() if not budgets_df.empty else []
        available_categories = categories_df["經費類別"].tolist() if not categories_df.empty else []
        
        with st.form("new_record_form"):
            if available_projects:
                plan = st.selectbox("計畫名稱", options=[""] + available_projects)
            else:
                plan = st.text_input("計畫名稱")
                st.markdown("<div class='warning-box'>尚未設定計畫預算，請先在「預算管理」中新增計畫。</div>", unsafe_allow_html=True)
            
            if available_categories:
                item = st.selectbox("經費項目", options=[""] + available_categories)
            else:
                item = st.text_input("經費項目")
            
            amount = st.number_input("花費金額", min_value=0, step=100)
            invoice_date = st.date_input("發票日期")
            invoice_amount = st.number_input("發票金額", min_value=0, step=100)
            remark = st.text_area("備註", height=100)
            
            submitted = st.form_submit_button("新增紀錄")
            
            if submitted:
                if not plan or not item:
                    st.error("計畫名稱和經費項目為必填欄位！")
                else:
                    new_row = [
                        plan,
                        item,
                        int(amount),
                        str(invoice_date),
                        int(invoice_amount),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        remark
                    ]
                    save_record(new_row)
                    st.success("成功新增經費紀錄！")
                    st.cache_data.clear()
                    st.rerun()
    
    with tab2:
        st.markdown("<h3>經費紀錄管理</h3>", unsafe_allow_html=True)
        
        if not records_df.empty:
            st.dataframe(records_df, use_container_width=True)
            
            # 刪除功能
            st.subheader("刪除紀錄")
            record_index = st.number_input(
                "選擇要刪除的記錄索引", 
                min_value=0, 
                max_value=len(records_df)-1 if not records_df.empty else 0,
                help="請根據表格中的順序輸入索引值（從0開始計算）"
            )
            
            if st.button("刪除此紀錄"):
                delete_record(record_index)
                st.success(f"已刪除索引 {record_index} 的記錄！")
                st.cache_data.clear()
                st.rerun()
        else:
            st.markdown("<div class='info-box'>尚無經費記錄。</div>", unsafe_allow_html=True)

elif menu == "📝 預算管理":
    st.markdown("<h2 class='sub-header'>📝 預算管理</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ 新增預算", "📋 預算列表"])
    
    with tab1:
        st.markdown("<h3>新增計畫預算</h3>", unsafe_allow_html=True)
        
        with st.form("new_budget_form"):
            project_name = st.text_input("計畫名稱")
            total_budget = st.number_input("總預算", min_value=0, step=10000)
            budget_remark = st.text_area("備註", placeholder="選填")
            
            if st.form_submit_button("新增預算"):
                if not project_name:
                    st.error("計畫名稱為必填欄位！")
                else:
                    new_budget = [
                        project_name,
                        total_budget,
                        datetime.now().strftime("%Y-%m-%d"),
                        budget_remark
                    ]
                    save_budget(new_budget)
                    st.success("成功新增計畫預算！")
                    st.cache_data.clear()
                    st.rerun()
    
    with tab2:
        st.markdown("<h3>預算管理列表</h3>", unsafe_allow_html=True)
        
        if not budgets_df.empty:
            # 計算每個計畫的已使用預算
            if not records_df.empty:
                project_spending = records_df.groupby("計畫名稱")["花費金額"].sum().reset_index()
                spending_dict = project_spending.set_index("計畫名稱")["花費金額"].to_dict()
                
                budgets_df["已使用預算"] = budgets_df["計畫名稱"].map(lambda x: spending_dict.get(x, 0))
                budgets_df["剩餘預算"] = budgets_df["總預算"] - budgets_df["已使用預算"]
                budgets_df["使用百分比"] = (budgets_df["已使用預算"] / budgets_df["總預算"] * 100).round(2)
            
            # 顯示預算表格
            if "使用百分比" in budgets_df.columns:
                display_df = budgets_df[["計畫名稱", "總預算", "已使用預算", "剩餘預算", "使用百分比", "設定日期", "備註"]]
            else:
                display_df = budgets_df
            
            st.dataframe(display_df, use_container_width=True)
            
            # 刪除預算
            st.subheader("刪除預算")
            budget_index = st.number_input(
                "選擇要刪除的預算索引", 
                min_value=0, 
                max_value=len(budgets_df)-1 if not budgets_df.empty else 0,
                help="請根據表格中的順序輸入索引值（從0開始計算）"
            )
            
            if st.button("刪除此預算"):
                delete_budget(budget_index)
                st.success(f"已刪除索引 {budget_index} 的預算設定！")
                st.cache_data.clear()
                st.rerun()
        else:
            st.markdown("<div class='info-box'>目前尚未設定任何計畫預算。</div>", unsafe_allow_html=True)

elif menu == "🏷️ 類別管理":
    st.markdown("<h2 class='sub-header'>🏷️ 經費類別管理</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h3>新增經費類別</h3>", unsafe_allow_html=True)
        
        with st.form("new_category_form"):
            category_name = st.text_input("類別名稱")
            category_desc = st.text_input("類別說明")
            
            if st.form_submit_button("新增類別"):
                if not category_name:
                    st.error("類別名稱為必填欄位！")
                else:
                    new_category = [category_name, category_desc]
                    save_category(new_category)
                    st.success("成功新增經費類別！")
                    st.cache_data.clear()
                    st.rerun()
    
    with col2:
        st.markdown("<h3>現有類別列表</h3>", unsafe_allow_html=True)
        
        if not categories_df.empty:
            st.dataframe(categories_df, use_container_width=True)
            
            # 刪除類別
            category_index = st.number_input(
                "選擇要刪除的類別索引", 
                min_value=0, 
                max_value=len(categories_df)-1 if not categories_df.empty else 0,
                help="請根據表格中的順序輸入索引值（從0開始計算）"
            )
            
            if st.button("刪除此類別"):
                delete_category(category_index)
                st.success(f"已刪除索引 {category_index} 的類別！")
                st.cache_data.clear()
                st.rerun()
        else:
            st.markdown("<div class='info-box'>目前尚未設定任何經費類別。</div>", unsafe_allow_html=True)

elif menu == "📈 統計分析":
    st.markdown("<h2 class='sub-header'>📈 統計分析</h2>", unsafe_allow_html=True)
    
    if not records_df.empty:
        # 計畫總支出
        st.markdown("<h3>各計畫經費使用狀況</h3>", unsafe_allow_html=True)
        project_spending = records_df.groupby("計畫名稱")["花費金額"].sum().reset_index()
        
        # 取得預算數據
        if not budgets_df.empty:
            project_budget = budgets_df.set_index("計畫名稱")["總預算"].to_dict()
            project_spending["總預算"] = project_spending["計畫名稱"].map(lambda x: project_budget.get(x, 0))
            project_spending["剩餘預算"] = project_spending["總預算"] - project_spending["花費金額"]
            project_spending["使用比例"] = (project_spending["花費金額"] / project_spending["總預算"] * 100).round(1)
        
        st.dataframe(project_spending, use_container_width=True)
        
        # 經費類別分析
        st.markdown("<h3>經費類別統計</h3>", unsafe_allow_html=True)
        category_spending = records_df.groupby("經費項目")["花費金額"].sum().reset_index()
        st.dataframe(category_spending, use_container_width=True)
        
        # 時間分析
        if "發票日期" in records_df.columns:
            st.markdown("<h3>時間趨勢分析</h3>", unsafe_allow_html=True)
            try:
                time_df = records_df.copy()
                if time_df["發票日期"].dtype != 'datetime64[ns]':
                    time_df["發票日期"] = pd.to_datetime(time_df["發票日期"])
                
                time_df["月份"] = time_df["發票日期"].dt.strftime("%Y-%m")
                monthly_spending = time_df.groupby("月份")["花費金額"].sum().reset_index()
                st.dataframe(monthly_spending, use_container_width=True)
            except:
                st.error("無法進行時間分析，請確認日期格式正確")
    else:
        st.markdown("<div class='info-box'>目前尚無經費記錄，無法進行統計分析。</div>", unsafe_allow_html=True)

elif menu == "⚙️ 設定":
    st.markdown("<h2 class='sub-header'>⚙️ 系統設定</h2>", unsafe_allow_html=True)
    
    st.markdown("<h3>數據備份</h3>", unsafe_allow_html=True)
    
    # 下載經費記錄
    csv_records = records_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="下載經費記錄 CSV",
        data=csv_records,
        file_name="lab_budget_records.csv",
        mime="text/csv",
    )
    
    # 下載預算設定
    csv_budgets = budgets_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="下載預算設定 CSV",
        data=csv_budgets,
        file_name="lab_budget_settings.csv",
        mime="text/csv",
    )
    
    # 顯示 Google Sheets 連結
    st.markdown("<h3>Google Sheets 連結</h3>", unsafe_allow_html=True)
    st.markdown(f"[點擊開啟 Google Sheets 資料表]({SHEET_URL})")
    
    # 系統資訊
    st.markdown("<h3>系統資訊</h3>", unsafe_allow_html=True)
    st.markdown("**系統版本**: v1.0.0")
    st.markdown("**最後更新**: 2025-05-02")
    st.markdown("**開發者**: IC Lab")