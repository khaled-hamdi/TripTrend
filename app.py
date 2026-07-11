import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os

# ======================================================================================
# --- CONFIGURATION & CITY MAPPING (تعديل المدن والملفات من هنا) ---
# ======================================================================================
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
    }
}

# ======================================================================================
# --- USER CREDENTIALS ---
# ======================================================================================
USERS_DB = {
    "test1": "password123",
    "admin": "admin123",
    "company_a": "company@123",
    "blogger_pro": "blogger2024",
    "travel_agency": "travel@2024"
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(
    page_title="Hotel Analytics Pro",
    page_icon="🏨",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .metric-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin: 10px 0; }
    .booking-platform { background: #f8f9fa; padding: 10px; border-left: 4px solid #667eea; margin: 5px 0; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

# ======================================================================================
# --- HELPER FUNCTIONS ---
# ======================================================================================
def find_column(df, possible_names):
    for name in possible_names:
        for col in df.columns:
            if str(col).strip().lower() == name.lower():
                return col
    return None

@st.cache_data
def load_and_process_data(file_path):
    if not os.path.exists(file_path):
        return None, None, f"File not found: {file_path}"
    
    try:
        df = pd.read_excel(file_path)
        
        # Mapping columns
        col_map = {
            'Hotel_Name': find_column(df, ['Hotel_Name', 'Hotel Name', 'hotel', 'الاسم']),
            'Price1': find_column(df, ['Price1', 'price 1', 'سعر 1']),
            'Price2': find_column(df, ['price2', 'Price2', 'price 2', 'سعر 2']),
            'Price3': find_column(df, ['price3', 'Price3', 'price 3', 'سعر 3']),
            'Rate': find_column(df, ['Rate', 'rate', 'التقييم', 'Rating']),
            'Star': find_column(df, ['Star', 'star', 'النجوم', 'Stars']),
            'Arrival_Date': find_column(df, ['date of arrival', 'Date of Arrival', 'arrival date', 'تاريخ الوصول']),
            'Place1': find_column(df, ['Place1', 'place 1', 'منصة 1']),
            'Place3': find_column(df, ['place3', 'Place3', 'place 3', 'منصة 3'])
        }
        
        if not col_map['Hotel_Name'] or not col_map['Price1']:
            return None, None, f"Essential columns missing. Found columns: {list(df.columns)}"

        # Clean Prices
        price_cols = [col_map['Price1'], col_map['Price2'], col_map['Price3']]
        price_cols = [c for c in price_cols if c is not None]
        for col in price_cols:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[price_cols].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce') if col_map['Rate'] else 0
        df['Star'] = pd.to_numeric(df[col_map['Star']], errors='coerce') if col_map['Star'] else 0
        
        if col_map['Arrival_Date']:
            df['arrival_date_dt'] = pd.to_datetime(df[col_map['Arrival_Date']], errors='coerce')
            df['Arrival_Month'] = df['arrival_date_dt'].dt.strftime('%B')
            df['Arrival_Day_Name'] = df['arrival_date_dt'].dt.strftime('%A')
        else:
            df['arrival_date_dt'] = pd.NaT
            df['Arrival_Month'] = "Unknown"
            df['Arrival_Day_Name'] = "Unknown"
            
        return df, col_map, None
    except Exception as e:
        return None, None, f"Error: {str(e)}"

# ======================================================================================
# --- DASHBOARD ---
# ======================================================================================
def show_dashboard():
    # Header & Logout
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1: st.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
    with col_h2: 
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
    
    st.markdown("---")
    
    # City Selection
    selected_city = st.selectbox("🌍 Select City:", list(CITIES_DATA.keys()), 
                                format_func=lambda x: f"{CITIES_DATA[x]['emoji']} {x}")
    
    file_path = CITIES_DATA[selected_city]['file']
    df, col_map, error = load_and_process_data(file_path)
    
    if error:
        st.error(error)
        return
    
    hotel_col = col_map['Hotel_Name']
    
    # Tabs
    t1, t2, t3, t4, t5 = st.tabs(["📊 Dashboard", "💎 Extremes", "📈 Trends", "🏆 Rankings", "🔍 Tracker"])
    
    with t1:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hotels", len(df[hotel_col].unique()))
        c2.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c3.metric("Avg Rate", f"{df['Rate'].mean():.1f}")
        c4.metric("Avg Stars", f"{df['Star'].mean():.1f}")
        
        fig_p = px.histogram(df, x='Best_Price', title="Price Distribution")
        st.plotly_chart(fig_p, use_container_width=True)
    
    with t2:
        cheapest = df.loc[df['Best_Price'].idxmin()]
        expensive = df.loc[df['Best_Price'].idxmax()]
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.info(f"🟢 **Cheapest:** {cheapest[hotel_col]}\n\nPrice: ${cheapest['Best_Price']:.0f}")
            if col_map['Place1']: st.markdown(f"**Platform 1:** {cheapest[col_map['Place1']]}")
            if col_map['Place3']: st.markdown(f"**Platform 2:** {cheapest[col_map['Place3']]}")
        with col_b:
            st.warning(f"🔴 **Expensive:** {expensive[hotel_col]}\n\nPrice: ${expensive['Best_Price']:.0f}")
            if col_map['Place1']: st.markdown(f"**Platform 1:** {expensive[col_map['Place1']]}")
            if col_map['Place3']: st.markdown(f"**Platform 2:** {expensive[col_map['Place3']]}")

    with t3:
        if df['Arrival_Month'].iloc[0] != "Unknown":
            m_avg = df.groupby('Arrival_Month')['Best_Price'].mean().sort_values()
            st.plotly_chart(px.bar(x=m_avg.index, y=m_avg.values, title="Monthly Avg Price"), use_container_width=True)
        else: st.info("No date data available.")

    with t4:
        df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[hotel_col])
        for s in [5, 4, 3]:
            st.write(f"### ⭐ {s} Stars")
            st.table(df_u[df_u['Star'] == s].head(5)[[hotel_col, 'Best_Price', 'Rate']])

    with t5:
        target = st.selectbox("Select Hotel:", sorted(df[hotel_col].unique()))
        h_data = df[df[hotel_col] == target].sort_values('arrival_date_dt')
        if not h_data.empty:
            st.line_chart(h_data.set_index('arrival_date_dt')['Best_Price'])

# ======================================================================================
# --- MAIN ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u in USERS_DB and USERS_DB[u] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else: st.error("Invalid login")
    else: show_dashboard()

if __name__ == "__main__": main()
