import streamlit as st
import json
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import plotly.express as px
import numpy as np

# ====== 設定頁面 ======
st.set_page_config(
    page_title="實驗室經費管理系統",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
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

# ====== 登入驗證 ======
st.markdown("<h1 class='main-header'>🧪 實驗室經費管理系統</h1>", unsafe_allow_html=True)

# 可以設定多個使用者和權限
USERS = {
    "admin": {"password": "IC203", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["username"] = None
    st.session_state["role"] = None

if not st.session_state["authenticated"]:
    st.markdown("<div class='info-box'>請登入系統以繼續</div>", unsafe_allow_html=True)
    username = st.text_input("使用者名稱：")
    password = st.text_input("密碼：", type="password")
    if st.button("登入"):
        if username in USERS and password == USERS[username]["password"]:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.session_state["role"] = USERS[username]["role"]
            st.success(f"歡迎回來，{username}！")
            st.rerun()
        else:
            st.error("使用者名稱或密碼錯誤！")
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
    SHEET_URL = "https://docs.google.com/spreadsheets/d/1F2SDyauxsE229BuM8mv7kkfIuWz6LPGnFQNCjzKyKp8/edit?usp=sharing"
    
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
    st.markdown(f"### 歡迎, {st.session_state['username']} ({st.session_state['role']})")
    
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
        st.session_state["username"] = None
        st.session_state["role"] = None
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
    
    # 圖表展示區
    st.markdown("<h3>預算使用概況</h3>", unsafe_allow_html=True)
    
    if not records_df.empty and not budgets_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # 計畫預算使用比例
            projects_spending = records_df.groupby("計畫名稱")["花費金額"].sum().reset_index()
            projects_budget = budgets_df.set_index("計畫名稱")["總預算"].to_dict()
            
            projects_spending["總預算"] = projects_spending["計畫名稱"].map(projects_budget)
            projects_spending["剩餘預算"] = projects_spending["總預算"] - projects_spending["花費金額"]
            projects_spending["使用比例"] = (projects_spending["花費金額"] / projects_spending["總預算"] * 100).round(1)
            
            fig1 = px.bar(
                projects_spending,
                x="計畫名稱",
                y=["花費金額", "剩餘預算"],
                title="各計畫預算使用情況",
                labels={"value": "金額", "variable": "類型"},
                color_discrete_map={"花費金額": "#1E88E5", "剩餘預算": "#B3E5FC"}
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            # 經費類別分佈
            if "經費項目" in records_df.columns:
                category_spending = records_df.groupby("經費項目")["花費金額"].sum().reset_index()
                fig2 = px.pie(
                    category_spending, 
                    values="花費金額", 
                    names="經費項目", 
                    title="經費類別分佈",
                    hole=0.4
                )
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown("<div class='info-box'>尚無足夠數據以顯示圖表分析。請先添加計畫預算和經費記錄。</div>", unsafe_allow_html=True)
    
    # 最近記錄
    st.markdown("<h3>最近經費記錄</h3>", unsafe_allow_html=True)
    if not records_df.empty:
        st.dataframe(records_df.head(5), use_container_width=True)
    else:
        st.markdown("<div class='info-box'>尚無經費記錄。</div>", unsafe_allow_html=True)

elif menu == "💰 經費記錄":
    st.markdown("<h2 class='sub-header'>💰 經費記錄</h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📝 新增記錄", "🔍 查看與管理"])
    
    with tab1:
        st.markdown("<h3>新增經費記錄</h3>", unsafe_allow_html=True)
        
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
        
        # 篩選器
        col1, col2, col3 = st.columns(3)
        with col1:
            filter_project = st.selectbox(
                "依計畫篩選", 
                options=["全部"] + (records_df["計畫名稱"].unique().tolist() if not records_df.empty else [])
            )
        
        with col2:
            filter_category = st.selectbox(
                "依經費項目篩選", 
                options=["全部"] + (records_df["經費項目"].unique().tolist() if not records_df.empty else [])
            )
        
        with col3:
            if not records_df.empty and "發票日期" in records_df.columns:
                min_date = records_df["發票日期"].min() if not pd.isna(records_df["發票日期"].min()) else datetime.now().date()
                max_date = records_df["發票日期"].max() if not pd.isna(records_df["發票日期"].max()) else datetime.now().date()
                date_range = st.date_input(
                    "日期範圍",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
        
        # 應用篩選
        filtered_df = records_df.copy() if not records_df.empty else pd.DataFrame()
        
        if not filtered_df.empty:
            if filter_project != "全部":
                filtered_df = filtered_df[filtered_df["計畫名稱"] == filter_project]
            
            if filter_category != "全部":
                filtered_df = filtered_df[filtered_df["經費項目"] == filter_category]
            
            if len(date_range) == 2 and "發票日期" in filtered_df.columns:
                filtered_df = filtered_df[
                    (filtered_df["發票日期"] >= date_range[0]) & 
                    (filtered_df["發票日期"] <= date_range[1])
                ]
        
        # 顯示篩選結果
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
            
            # 刪除與編輯功能
            st.markdown("<h4>管理記錄</h4>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
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
            
            with col2:
                st.subheader("編輯紀錄")
                edit_index = st.number_input(
                    "選擇要編輯的記錄索引", 
                    min_value=0, 
                    max_value=len(records_df)-1 if not records_df.empty else 0,
                    key="edit_record_index"
                )
                
                if st.button("載入此紀錄"):
                    if not records_df.empty and edit_index < len(records_df):
                        record_to_edit = records_df.iloc[edit_index]
                        st.session_state["record_to_edit"] = record_to_edit
                        st.rerun()
            
            # 編輯表單
            if "record_to_edit" in st.session_state:
                st.markdown("<h4>編輯記錄</h4>", unsafe_allow_html=True)
                record = st.session_state["record_to_edit"]
                
                with st.form("edit_record_form"):
                    edit_plan = st.text_input("計畫名稱", value=record["計畫名稱"] if "計畫名稱" in record else "")
                    edit_item = st.text_input("經費項目", value=record["經費項目"] if "經費項目" in record else "")
                    edit_amount = st.number_input(
                        "花費金額", 
                        min_value=0, 
                        value=int(record["花費金額"]) if "花費金額" in record else 0
                    )
                    
                    edit_date = st.date_input(
                        "發票日期", 
                        value=record["發票日期"] if "發票日期" in record else datetime.now().date()
                    )
                    
                    edit_invoice = st.number_input(
                        "發票金額", 
                        min_value=0, 
                        value=int(record["發票金額"]) if "發票金額" in record else 0
                    )
                    
                    edit_remark = st.text_area(
                        "備註", 
                        value=record["備註"] if "備註" in record else "",
                        height=100
                    )
                    
                    update_submitted = st.form_submit_button("更新記錄")
                    
                    if update_submitted:
                        updated_record = [
                            edit_plan,
                            edit_item,
                            int(edit_amount),
                            str(edit_date),
                            int(edit_invoice),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            edit_remark
                        ]
                        
                        update_record(edit_index, updated_record)
                        st.success("記錄已更新！")
                        del st.session_state["record_to_edit"]
                        st.cache_data.clear()
                        st.rerun()
                
                if st.button("取消編輯"):
                    del st.session_state["record_to_edit"]
                    st.rerun()
        else:
            st.markdown("<div class='info-box'>沒有符合條件的紀錄或資料庫中尚無資料。</div>", unsafe_allow_html=True)

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
                
                # 使用 plotly 創建進度條
                def budget_progress_bar(row):
                    percentage = min(100, row["使用百分比"])
                    color = "green" if percentage < 70 else "orange" if percentage < 90 else "red"
                    return f"<div style='width:100%;background-color:#e0e0e0;height:20px;border-radius:10px;'><div style='width:{percentage}%;background-color:{color};height:20px;border-radius:10px;'></div></div>"
                
                budgets_df["預算使用率"] = budgets_df.apply(budget_progress_bar, axis=1)
            
            # 顯示預算表格（使用 Pandas 樣式或自定義 HTML）
            if "使用百分比" in budgets_df.columns:
                display_df = budgets_df[["計畫名稱", "總預算", "已使用預算", "剩餘預算", "使用百分比", "設定日期", "備註"]]
            else:
                display_df = budgets_df
            
            st.dataframe(display_df, use_container_width=True)
            
            # 管理預算
            st.markdown("<h4>管理預算設定</h4>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("刪除預算")
                budget_index = st.number_input(
                    "選擇要刪除的預算索引", 
                    min_value=0, 
                    max_value=len(budgets_df)-1,
                    help="請根據表格中的順序輸入索引值（從0開始計算）"
                )
                
                if st.button("刪除此預算"):
                    delete_budget(budget_index)
                    st.success(f"已刪除索引 {budget_index} 的預算設定！")
                    st.cache_data.clear()
                    st.rerun()
            
            with col2:
                st.subheader("編輯預算")
                edit_budget_index = st.number_input(
                    "選擇要編輯的預算索引", 
                    min_value=0, 
                    max_value=len(budgets_df)-1,
                    key="edit_budget_index"
                )
                
                if st.button("載入此預算"):
                    if not budgets_df.empty and edit_budget_index < len(budgets_df):
                        budget_to_edit = budgets_df.iloc[edit_budget_index]
                        st.session_state["budget_to_edit"] = budget_to_edit
                        st.rerun()
            
            # 編輯預算表單
            if "budget_to_edit" in st.session_state:
                st.markdown("<h4>編輯預算</h4>", unsafe_allow_html=True)
                budget = st.session_state["budget_to_edit"]
                
                with st.form("edit_budget_form"):
                    edit_project_name = st.text_input("計畫名稱", value=budget["計畫名稱"])
                    edit_total_budget = st.number_input(
                        "總預算", 
                        min_value=0, 
                        value=int(budget["總預算"]),
                        step=10000
                    )
                    edit_budget_remark = st.text_area(
                        "備註", 
                        value=budget["備註"] if "備註" in budget else ""
                    )
                    
                    if st.form_submit_button("更新預算"):
                        updated_budget = [
                            edit_project_name,
                            edit_total_budget,
                            datetime.now().strftime("%Y-%m-%d"),
                            edit_budget_remark
                        ]
                        
                        update_budget(edit_budget_index, updated_budget)
                        st.success("預算已更新！")
                        del st.session_state["budget_to_edit"]
                        st.cache_data.clear()
                        st.rerun()
                
                if st.button("取消編輯", key="cancel_budget_edit"):
                    del st.session_state["budget_to_edit"]
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
                max_value=len(categories_df)-1,
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
        # 分析選項
        analysis_type = st.selectbox(
            "選擇分析類型", 
            options=[
                "按計畫分析",
                "按經費項目分析",
                "按時間分析",
                "自訂分析"
            ]
        )
        
        if analysis_type == "按計畫分析":
            # 計畫花費分析
            st.markdown("<h3>各計畫經費使用狀況</h3>", unsafe_allow_html=True)
            
            # 計算計畫總支出
            project_spending = records_df.groupby("計畫名稱")["花費金額"].sum().reset_index()
            
            # 取得預算數據
            if not budgets_df.empty:
                project_budget = budgets_df.set_index("計畫名稱")["總預算"].to_dict()
                project_spending["總預算"] = project_spending["計畫名稱"].map(lambda x: project_budget.get(x, 0))
                project_spending["剩餘預算"] = project_spending["總預算"] - project_spending["花費金額"]
                project_spending["使用比例"] = (project_spending["花費金額"] / project_spending["總預算"] * 100).round(1)
                
                # 顯示圖表
                col1, col2 = st.columns(2)
                
                with col1:
                    fig1 = px.bar(
                        project_spending, 
                        x="計畫名稱", 
                        y=["花費金額", "剩餘預算"],
                        title="各計畫預算使用狀況",
                        labels={"value": "金額", "variable": "類別"},
                        color_discrete_map={"花費金額": "#1E88E5", "剩餘預算": "#B3E5FC"}
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    fig2 = px.pie(
                        project_spending, 
                        values="花費金額", 
                        names="計畫名稱",
                        title="計畫經費使用分佈",
                        hole=0.4
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # 顯示詳細數據
                st.markdown("<h4>各計畫經費詳細數據</h4>", unsafe_allow_html=True)
                st.dataframe(project_spending, use_container_width=True)
                
                # 計畫內部經費分析
                st.markdown("<h4>計畫內部經費分佈</h4>", unsafe_allow_html=True)
                selected_project = st.selectbox(
                    "選擇要分析的計畫", 
                    options=project_spending["計畫名稱"].tolist()
                )
                
                if selected_project:
                    project_data = records_df[records_df["計畫名稱"] == selected_project]
                    project_categories = project_data.groupby("經費項目")["花費金額"].sum().reset_index()
                    
                    fig3 = px.pie(
                        project_categories, 
                        values="花費金額", 
                        names="經費項目",
                        title=f"{selected_project} 經費項目分佈"
                    )
                    st.plotly_chart(fig3, use_container_width=True)
            else:
                st.markdown("<div class='warning-box'>尚未設定計畫預算，無法完成完整分析。</div>", unsafe_allow_html=True)
                
                # 只顯示基本數據
                fig = px.bar(
                    project_spending, 
                    x="計畫名稱", 
                    y="花費金額",
                    title="各計畫經費使用"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        elif analysis_type == "按經費項目分析":
            st.markdown("<h3>經費項目分析</h3>", unsafe_allow_html=True)
            
            # 按類別分析支出
            category_spending = records_df.groupby("經費項目")["花費金額"].sum().reset_index()
            category_spending = category_spending.sort_values("花費金額", ascending=False)
            
            # 顯示圖表
            col1, col2 = st.columns(2)
            
            with col1:
                fig1 = px.bar(
                    category_spending, 
                    x="經費項目", 
                    y="花費金額",
                    title="各經費項目總支出",
                    color="花費金額",
                    color_continuous_scale="Blues"
                )
                st.plotly_chart(fig1, use_container_width=True)
            
            with col2:
                fig2 = px.pie(
                    category_spending, 
                    values="花費金額", 
                    names="經費項目",
                    title="經費項目分佈比例"
                )
                st.plotly_chart(fig2, use_container_width=True)
            
            # 各計畫內的類別分佈
            st.markdown("<h4>各計畫的經費項目分佈</h4>", unsafe_allow_html=True)
            
            # 建立交叉分析表
            pivot_df = pd.pivot_table(
                records_df,
                values="花費金額",
                index="計畫名稱",
                columns="經費項目",
                aggfunc="sum",
                fill_value=0
            )
            
            # 增加總計列
            pivot_df["總計"] = pivot_df.sum(axis=1)
            
            st.dataframe(pivot_df, use_container_width=True)
            
            # 熱力圖
            fig3 = px.imshow(
                pivot_df.drop(columns=["總計"]) if "總計" in pivot_df.columns else pivot_df,
                text_auto=True,
                aspect="auto",
                color_continuous_scale="Blues",
                title="計畫與經費項目支出熱力圖"
            )
            st.plotly_chart(fig3, use_container_width=True)
        
        elif analysis_type == "按時間分析":
            st.markdown("<h3>經費時間趨勢分析</h3>", unsafe_allow_html=True)
            
            # 確保發票日期欄位存在且為日期格式
            if "發票日期" in records_df.columns:
                # 如果發票日期不是日期格式，則嘗試轉換
                if records_df["發票日期"].dtype != "datetime64[ns]":
                    try:
                        time_df = records_df.copy()
                        time_df["發票日期"] = pd.to_datetime(time_df["發票日期"])
                    except:
                        st.error("發票日期格式無法轉換為日期格式，請確認資料正確性。")
                        time_df = records_df
                else:
                    time_df = records_df
                
                # 設定時間粒度
                time_grain = st.selectbox(
                    "選擇時間粒度",
                    options=["日", "週", "月", "季", "年"]
                )
                
                # 根據選擇的時間粒度設定時間分組
                if time_grain == "日":
                    time_df["時間"] = time_df["發票日期"]
                    time_format = "%Y-%m-%d"
                elif time_grain == "週":
                    time_df["時間"] = time_df["發票日期"].dt.to_period("W").dt.start_time
                    time_format = "%Y-%U"
                elif time_grain == "月":
                    time_df["時間"] = time_df["發票日期"].dt.to_period("M").dt.start_time
                    time_format = "%Y-%m"
                elif time_grain == "季":
                    time_df["時間"] = time_df["發票日期"].dt.to_period("Q").dt.start_time
                    time_format = "%Y-Q%q"
                else:  # 年
                    time_df["時間"] = time_df["發票日期"].dt.to_period("Y").dt.start_time
                    time_format = "%Y"
                
                # 按時間分組計算支出
                time_spending = time_df.groupby("時間")["花費金額"].sum().reset_index()
                time_spending = time_spending.sort_values("時間")
                
                # 時間趨勢圖
                fig1 = px.line(
                    time_spending,
                    x="時間",
                    y="花費金額",
                    title=f"經費支出時間趨勢 ({time_grain})",
                    markers=True
                )
                st.plotly_chart(fig1, use_container_width=True)
                
                # 按計畫和時間的多線圖
                project_time_df = time_df.groupby(["時間", "計畫名稱"])["花費金額"].sum().reset_index()
                
                fig2 = px.line(
                    project_time_df,
                    x="時間",
                    y="花費金額",
                    color="計畫名稱",
                    title=f"各計畫經費支出時間趨勢 ({time_grain})",
                    markers=True
                )
                st.plotly_chart(fig2, use_container_width=True)
                
                # 時間和類別的堆疊圖
                category_time_df = time_df.groupby(["時間", "經費項目"])["花費金額"].sum().reset_index()
                
                fig3 = px.area(
                    category_time_df,
                    x="時間",
                    y="花費金額",
                    color="經費項目",
                    title=f"各經費項目支出時間趨勢 ({time_grain})"
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.markdown("<div class='warning-box'>數據中缺少發票日期欄位，無法進行時間分析。</div>", unsafe_allow_html=True)
        
        elif analysis_type == "自訂分析":
            st.markdown("<h3>自訂分析</h3>", unsafe_allow_html=True)
            
            # 選擇分析維度
            col1, col2 = st.columns(2)
            
            with col1:
                x_axis = st.selectbox(
                    "選擇 X 軸維度",
                    options=records_df.columns.tolist()
                )
            
            with col2:
                available_y_columns = [col for col in records_df.columns if records_df[col].dtype in [np.int64, np.float64]]
                y_axis = st.selectbox(
                    "選擇 Y 軸維度 (數值)",
                    options=available_y_columns
                )
            
            # 選擇圖表類型
            chart_type = st.selectbox(
                "選擇圖表類型",
                options=["長條圖", "圓餅圖", "折線圖", "散點圖", "箱形圖"]
            )
            
            # 選擇顏色分組(可選)
            color_by = st.selectbox(
                "選擇顏色分組 (可選)",
                options=["無"] + records_df.columns.tolist()
            )
            
            # 生成自訂圖表
            if chart_type == "長條圖":
                if color_by != "無":
                    custom_df = records_df.groupby([x_axis, color_by])[y_axis].sum().reset_index()
                    fig = px.bar(
                        custom_df,
                        x=x_axis,
                        y=y_axis,
                        color=color_by,
                        title=f"{x_axis} vs {y_axis} (按 {color_by} 分組)"
                    )
                else:
                    custom_df = records_df.groupby(x_axis)[y_axis].sum().reset_index()
                    fig = px.bar(
                        custom_df,
                        x=x_axis,
                        y=y_axis,
                        title=f"{x_axis} vs {y_axis}"
                    )
            
            elif chart_type == "圓餅圖":
                custom_df = records_df.groupby(x_axis)[y_axis].sum().reset_index()
                fig = px.pie(
                    custom_df,
                    values=y_axis,
                    names=x_axis,
                    title=f"{x_axis} 的 {y_axis} 分佈"
                )
            
            elif chart_type == "折線圖":
                if color_by != "無":
                    custom_df = records_df.groupby([x_axis, color_by])[y_axis].sum().reset_index()
                    fig = px.line(
                        custom_df,
                        x=x_axis,
                        y=y_axis,
                        color=color_by,
                        markers=True,
                        title=f"{x_axis} vs {y_axis} (按 {color_by} 分組)"
                    )
                else:
                    custom_df = records_df.groupby(x_axis)[y_axis].sum().reset_index()
                    fig = px.line(
                        custom_df,
                        x=x_axis,
                        y=y_axis,
                        markers=True,
                        title=f"{x_axis} vs {y_axis}"
                    )
            
            elif chart_type == "散點圖":
                if color_by != "無":
                    fig = px.scatter(
                        records_df,
                        x=x_axis,
                        y=y_axis,
                        color=color_by,
                        size=y_axis,
                        title=f"{x_axis} vs {y_axis} (按 {color_by} 分組)"
                    )
                else:
                    fig = px.scatter(
                        records_df,
                        x=x_axis,
                        y=y_axis,
                        size=y_axis,
                        title=f"{x_axis} vs {y_axis}"
                    )
            
            elif chart_type == "箱形圖":
                fig = px.box(
                    records_df,
                    x=x_axis,
                    y=y_axis,
                    title=f"{x_axis} 的 {y_axis} 分佈"
                )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # 顯示分析數據
            st.markdown("<h4>分析數據表</h4>", unsafe_allow_html=True)
            
            if chart_type in ["長條圖", "圓餅圖", "折線圖"]:
                if color_by != "無" and chart_type != "圓餅圖":
                    summary_df = records_df.pivot_table(
                        values=y_axis,
                        index=x_axis,
                        columns=color_by,
                        aggfunc="sum",
                        fill_value=0
                    )
                    st.dataframe(summary_df, use_container_width=True)
                else:
                    summary_df = records_df.groupby(x_axis)[y_axis].agg(["sum", "mean", "count"]).reset_index()
                    summary_df.columns = [x_axis, f"{y_axis}_總和", f"{y_axis}_平均", "記錄數"]
                    st.dataframe(summary_df, use_container_width=True)
            else:
                # 散點圖和箱形圖顯示原始數據
                st.dataframe(records_df[[x_axis, y_axis]], use_container_width=True)
    else:
        st.markdown("<div class='info-box'>目前尚無經費記錄，無法進行統計分析。</div>", unsafe_allow_html=True)

elif menu == "⚙️ 設定":
    st.markdown("<h2 class='sub-header'>⚙️ 系統設定</h2>", unsafe_allow_html=True)
    
    st.markdown("<h3>數據備份</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<h4>下載資料備份</h4>", unsafe_allow_html=True)
        
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
        
        # 下載類別設定
        csv_categories = categories_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載類別設定 CSV",
            data=csv_categories,
            file_name="lab_categories.csv",
            mime="text/csv",
        )
    
    with col2:
        st.markdown("<h4>Google Sheets 連結</h4>", unsafe_allow_html=True)
        
        st.markdown(f"[點擊開啟 Google Sheets 資料表]({SHEET_URL})")
        
        st.info("若需要進行大量數據編輯，可直接在 Google Sheets 中操作。")
    
    # 系統資訊
    st.markdown("<h3>系統資訊</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**系統版本**: v1.0.0")
        st.markdown("**最後更新**: 2025-05-02")
        st.markdown("**開發者**: IC Lab")
    
    with col2:
        st.markdown("**資料統計**:")
        st.markdown(f"- 計畫數量: {len(budgets_df) if not budgets_df.empty else 0}")
        st.markdown(f"- 經費記錄: {len(records_df) if not records_df.empty else 0}")
        st.markdown(f"- 經費類別: {len(categories_df) if not categories_df.empty else 0}")
    
    # 使用說明
    st.markdown("<h3>使用說明</h3>", unsafe_allow_html=True)
    
    with st.expander("系統功能說明"):
        st.markdown("""
        ### 實驗室經費管理系統功能說明
        
        #### 📊 儀表板
        - 顯示關鍵數據摘要與圖表
        - 提供快速預算使用概況
        
        #### 💰 經費記錄
        - 新增實驗室經費支出紀錄
        - 管理和編輯現有記錄
        
        #### 📝 預算管理
        - 設定各研究計畫預算
        - 追蹤預算使用情況
        
        #### 🏷️ 類別管理
        - 定義經費支出類別
        - 自訂經費分類方式
        
        #### 📈 統計分析
        - 多維度經費使用分析
        - 生成各種分析圖表
        
        #### ⚙️ 設定
        - 備份與還原數據
        - 查看系統資訊
        """)
        
    with st.expander("常見問題"):
        st.markdown("""
        ### 常見問題解答
        
        #### Q: 如何重置密碼？
        A: 請聯絡系統管理員重置密碼。
        
        #### Q: 如何備份所有資料？
        A: 在「設定」頁面中可以下載所有數據的CSV檔案。
        
        #### Q: 資料是否安全？
        A: 所有資料都儲存在 Google Sheets 中，受 Google 安全機制保護。
        
        #### Q: 如何批量編輯資料？
        A: 可以直接在 Google Sheets 中編輯資料，系統會自動同步。
        """)