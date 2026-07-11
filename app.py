import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import hashlib
import os

# ======================================================================================
# --- CONFIGURATION & CITY MAPPING (تعديل المدن والملفات من هنا) ---
# ======================================================================================
# يمكنك تعديل أسماء ملفات الاكسل هنا لتطابق ما ترفعه على GitHub
CITIES_DATA = {
    "Paris": {
        "file": "paris 10-7.xlsx", 
        "emoji": "🗼", 
        "country": "France"
    },
    "Dubai": {
        "file": "dubai_hotels.xlsx", 
        "emoji": "🏙️", 
        "country": "UAE"
    },
    "Istanbul": {
        "file": "istanbul_hotels.xlsx", 
        "emoji": "🕌", 
        "country": "Turkey"
    },
    "Cairo": {
        "file": "cairo_hotels.xlsx", 
        "emoji": "🏛️", 
        "country": "Egypt"
    },
    "New York": {
        "file": "newyork_hotels.xlsx", 
        "emoji": "🗽", 
        "country": "USA"
    }
}

# ======================================================================================
# --- USER CREDENTIALS (قاعدة بيانات المستخدمين) ---
# ======================================================================================
USERS_DB = {
    "test1": "password123",
    "admin": "admin123",
    "company_a": "company@123",
    "blogger_pro": "blogger2024",
    "travel_agency": "travel@2024"
}

# ======================================================================================
# --- PAGE CONFIG & THEME ---
# ======================================================================================
st.set_page_config(
    page_title="Hotel Analytics Pro | تحليلات الفنادق الاحترافية",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 30px;
    }
    h2 {
        color: #34495e;
        border-bottom: 3px solid #667eea;
        padding-bottom: 10px;
    }
    .booking-platform {
        background: #f8f9fa;
        padding: 10px;
        border-left: 4px solid #667eea;
        margin: 5px 0;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# ======================================================================================
# --- HELPER FUNCTIONS ---
# ======================================================================================
def verify_login(username, password):
    if username in USERS_DB:
        return USERS_DB[username] == password
    return False

def find_column(df, possible_names):
    """البحث عن اسم العمود بغض النظر عن حالة الأحرف أو المسافات"""
    for name in possible_names:
        # البحث عن تطابق تام (تجاهل حالة الأحرف)
        for col in df.columns:
            if col.strip().lower() == name.lower():
                return col
    return None

# ======================================================================================
# --- DATA LOADING & PROCESSING ---
# ======================================================================================
@st.cache_data
def load_and_process_data(file_path):
    if not os.path.exists(file_path):
        return None, f"File not found: {file_path}"
    
    try:
        df = pd.read_excel(file_path)
        
        # 1. توحيد أسماء الأعمدة (Mapping)
        col_map = {
            'Hotel_Name': find_column(df, ['Hotel_Name', 'Hotel Name', 'hotel', 'الاسم']),
            'Price1': find_column(df, ['Price1', 'price 1', 'سعر 1']),
            'Price2': find_column(df, ['price2', 'Price2', 'price 2', 'سعر 2']),
            'Price3': find_column(df, ['price3', 'Price3', 'price 3', 'سعر 3']),
            'Rate': find_column(df, ['Rate', 'rate', 'التقييم', 'Rating']),
            'Star': find_column(df, ['Star', 'star', 'النجوم', 'Stars']),
            'Arrival_Date': find_column(df, ['date of arrival', 'Date of Arrival', 'arrival date', 'تاريخ الوصول']),
            'Booking_Date': find_column(df, ['date of creat booking', 'Date of Creation', 'booking date', 'تاريخ الحجز']),
            'Place1': find_column(df, ['Place1', 'place 1', 'منصة 1']),
            'Place3': find_column(df, ['place3', 'Place3', 'place 3', 'منصة 3']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف'])
        }
        
        # التحقق من وجود الأعمدة الأساسية
        if not col_map['Hotel_Name'] or not col_map['Price1']:
            return None, "Essential columns (Hotel Name or Price) are missing in the Excel file."

        # 2. تنظيف البيانات
        # تنظيف الأسعار
        price_cols = [col_map['Price1'], col_map['Price2'], col_map['Price3']]
        price_cols = [c for c in price_cols if c is not None]
        
        for col in price_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[price_cols].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce') if col_map['Rate'] else 0
        df['Star'] = pd.to_numeric(df[col_map['Star']], errors='coerce') if col_map['Star'] else 0
        
        # تنظيف التواريخ
        if col_map['Arrival_Date']:
            df['arrival_date_dt'] = pd.to_datetime(df[col_map['Arrival_Date']], errors='coerce')
            df['Arrival_Month'] = df['arrival_date_dt'].dt.strftime('%B')
            df['Arrival_Day_Name'] = df['arrival_date_dt'].dt.strftime('%A')
        else:
            df['arrival_date_dt'] = pd.NaT
            df['Arrival_Month'] = "Unknown"
            df['Arrival_Day_Name'] = "Unknown"
            
        # حفظ أسماء الأعمدة الأصلية للاستخدام لاحقاً
        df._col_map = col_map
        
        return df, None
    except Exception as e:
        return None, f"Error processing data: {str(e)}"

# ======================================================================================
# --- LOGIN PAGE ---
# ======================================================================================
def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("<h1>🏨 Hotel Analytics Pro</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #667eea;'>تحليلات الفنادق الاحترافية</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        username = st.text_input("👤 Username", placeholder="Enter your username")
        password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
        
        if st.button("🚀 Login", use_container_width=True):
            if verify_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("❌ Invalid username or password!")
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; font-size: 12px; color: #95a5a6;'>Demo: test1 / password123</p>", unsafe_allow_html=True)

# ======================================================================================
# --- MAIN DASHBOARD ---
# ======================================================================================
def show_dashboard():
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    
    st.markdown("---")
    
    # City Selection
    st.markdown("### 🌍 Select Your City | اختر المدينة")
    selected_city = st.selectbox(
        "Choose a city to analyze:",
        list(CITIES_DATA.keys()),
        format_func=lambda x: f"{CITIES_DATA[x]['emoji']} {x} - {CITIES_DATA[x]['country']}"
    )
    
    # Load data
    file_path = CITIES_DATA[selected_city]['file']
    df, error = load_and_process_data(file_path)
    
    if error:
        st.error(f"⚠️ {error}")
        st.info(f"Please make sure the file '{file_path}' is uploaded to GitHub and has the correct columns.")
        return
    
    st.success(f"✅ Loaded {len(df)} records for {selected_city}")
    st.markdown("---")
    
    # ==================== TABS ====================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "💎 Market Extremes",
        "📈 Trends & Seasonality",
        "🏆 Top Rankings",
        "🔍 Hotel Tracker"
    ])
    
    col_map = df._col_map
    hotel_col = col_map['Hotel_Name']
    
    # ==================== TAB 1: DASHBOARD ====================
    with tab1:
        st.markdown("### 📊 Market Overview | نظرة عامة على السوق")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📍 Total Hotels", len(df[hotel_col].unique()))
        with col2:
            st.metric("💰 Avg Price", f"${df['Best_Price'].mean():.0f}")
        with col3:
            st.metric("⭐ Avg Rating", f"{df['Rate'].mean():.1f}")
        with col4:
            st.metric("🌟 Avg Stars", f"{df['Star'].mean():.1f}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            fig_price = px.histogram(df, x='Best_Price', nbins=30, title="Price Distribution", color_discrete_sequence=['#667eea'])
            st.plotly_chart(fig_price, use_container_width=True)
        with col2:
            fig_rating = px.histogram(df, x='Rate', nbins=20, title="Rating Distribution", color_discrete_sequence=['#764ba2'])
            st.plotly_chart(fig_rating, use_container_width=True)
    
    # ==================== TAB 2: MARKET EXTREMES ====================
    with tab2:
        st.markdown("### 💎 Market Extremes | أبطال السوق")
        
        abs_cheapest = df.loc[df['Best_Price'].idxmin()]
        abs_expensive = df.loc[df['Best_Price'].idxmax()]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Cheapest Deal Ever")
            st.info(f"""
            **Hotel:** {abs_cheapest[hotel_col]}
            **Price:** ${abs_cheapest['Best_Price']:.0f}
            **Rating:** {abs_cheapest['Rate']} ⭐
            **Arrival:** {abs_cheapest['arrival_date_dt'].strftime('%d %B %Y') if pd.notnull(abs_cheapest['arrival_date_dt']) else 'N/A'}
            """)
            if col_map['Place1'] and pd.notnull(abs_cheapest[col_map['Place1']]):
                st.markdown(f"<div class='booking-platform'><strong>Platform 1:</strong> {abs_cheapest[col_map['Place1']]}</div>", unsafe_allow_html=True)
            if col_map['Place3'] and pd.notnull(abs_cheapest[col_map['Place3']]):
                st.markdown(f"<div class='booking-platform'><strong>Platform 2:</strong> {abs_cheapest[col_map['Place3']]}</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 🔴 Most Expensive Record")
            st.warning(f"""
            **Hotel:** {abs_expensive[hotel_col]}
            **Price:** ${abs_expensive['Best_Price']:.0f}
            **Rating:** {abs_expensive['Rate']} ⭐
            **Arrival:** {abs_expensive['arrival_date_dt'].strftime('%d %B %Y') if pd.notnull(abs_expensive['arrival_date_dt']) else 'N/A'}
            """)
            if col_map['Place1'] and pd.notnull(abs_expensive[col_map['Place1']]):
                st.markdown(f"<div class='booking-platform'><strong>Platform 1:</strong> {abs_expensive[col_map['Place1']]}</div>", unsafe_allow_html=True)
            if col_map['Place3'] and pd.notnull(abs_expensive[col_map['Place3']]):
                st.markdown(f"<div class='booking-platform'><strong>Platform 2:</strong> {abs_expensive[col_map['Place3']]}</div>", unsafe_allow_html=True)

    # ==================== TAB 3: TRENDS ====================
    with tab3:
        st.markdown("### 📈 Trends & Seasonality")
        if 'Arrival_Month' in df.columns and df['Arrival_Month'].iloc[0] != "Unknown":
            monthly_avg = df.groupby('Arrival_Month')['Best_Price'].mean().sort_values()
            fig_monthly = px.bar(x=monthly_avg.index, y=monthly_avg.values, title="Avg Price by Month")
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            daily_avg = df.groupby('Arrival_Day_Name')['Best_Price'].mean()
            fig_daily = px.bar(x=daily_avg.index, y=daily_avg.values, title="Avg Price by Day of Week")
            st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.info("Date information is missing to show trends.")

    # ==================== TAB 4: TOP RANKINGS ====================
    with tab4:
        st.markdown("### 🏆 Top Rankings")
        df_unique = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[hotel_col])
        for star in [5, 4, 3]:
            st.markdown(f"#### ⭐ {star} Stars")
            top = df_unique[df_unique['Star'] == star].head(5)
            if not top.empty:
                st.table(top[[hotel_col, 'Best_Price', 'Rate']])
            else:
                st.write("No data for this category")

    # ==================== TAB 5: HOTEL TRACKER ====================
    with tab5:
        st.markdown("### 🔍 Hotel Tracker")
        hotel_list = sorted(df[hotel_col].unique())
        target = st.selectbox("Select Hotel:", hotel_list)
        h_data = df[df[hotel_col] == target].sort_values('arrival_date_dt')
        
        if not h_data.empty:
            st.line_chart(h_data.set_index('arrival_date_dt')['Best_Price'])
            st.write(f"**Best Price Found:** ${h_data['Best_Price'].min():.0f}")
            st.write(f"**Highest Price Found:** ${h_data['Best_Price'].max():.0f}")

# ======================================================================================
# --- MAIN APP LOGIC ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
    
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
