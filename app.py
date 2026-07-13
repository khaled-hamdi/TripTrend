import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os

# ======================================================================================
# --- CONFIGURATION & USERS ---
# ======================================================================================
USERS_DB = {
    "admin": {"password": "admin123", "created_at": "2026-01-01", "role": "admin", "pages": ["all"]},
    "test1": {"password": "password123", "created_at": "2026-07-01", "role": "user", "pages": ["dashboard", "trends", "rankings", "tracker"]},
    "company_a": {"password": "company@123", "created_at": "2026-07-10", "role": "company", "pages": ["all"]},
    "blogger_pro": {"password": "blogger2024", "created_at": "2026-07-11", "role": "blogger", "pages": ["dashboard", "trends", "fun_facts", "rankings"]},
}

CITIES_DATA = {
    "Paris": {"file": "paris 10-7.xlsx", "emoji": "🗼", "country": "France"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️", "country": "UAE"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌", "country": "Turkey"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️", "country": "Egypt"}
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V12", page_icon="🚀", layout="wide")

# ======================================================================================
# --- CORE FUNCTIONS ---
# ======================================================================================
def find_column(df, possible_names):
    df.columns = df.columns.str.strip()
    for name in possible_names:
        for col in df.columns:
            if str(col).strip().lower() == name.lower(): return col
    return None

@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, f"File not found: {file_path}"
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        
        col_map = {
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel', 'الاسم']),
            'Rate': find_column(df, ['Rate', 'rating', 'التقييم']),
            'Star': find_column(df, ['Star', 'stars', 'النجوم']),
            'P1': find_column(df, ['Price1', 'price1', 'سعر 1']),
            'P2': find_column(df, ['price2', 'Price2', 'سعر 2']),
            'P3': find_column(df, ['price3', 'Price3', 'سعر 3']),
            'Place1': find_column(df, ['Place1', 'place1', 'منصة 1']),
            'Place3': find_column(df, ['place3', 'Place3', 'منصة 3']),
            'Arrival': find_column(df, ['date of arrival', 'date_of_arrival', 'تاريخ الوصول']),
            'Booking': find_column(df, ['day of book', 'day_of_book', 'تاريخ الحجز']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف']),
            'Location': find_column(df, ['location', 'area', 'المنطقة'])
        }
        
        for p in ['P1', 'P2', 'P3']:
            if col_map[p]: df[col_map[p]] = pd.to_numeric(df[col_map[p]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract('(\d+)')[0], errors='coerce').fillna(0)
        
        if col_map['Arrival']:
            df['arrival_dt'] = pd.to_datetime(df[col_map['Arrival']], errors='coerce')
            df['Month'] = df['arrival_dt'].dt.strftime('%B')
            df['Day'] = df['arrival_dt'].dt.strftime('%A')
        else:
            df['arrival_dt'] = pd.NaT
            df['Month'] = "Unknown"
            df['Day'] = "Unknown"
        
        if col_map['Booking'] and col_map['Arrival']:
            df['booking_dt'] = pd.to_datetime(df[col_map['Booking']], errors='coerce')
            df['days_before'] = (df['arrival_dt'] - df['booking_dt']).dt.days
        
        return df, col_map, None
    except Exception as e: return None, None, str(e)

def track_page_view():
    if 'page_views' not in st.session_state: st.session_state.page_views = 0
    st.session_state.page_views += 1

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🚀 Hotel Analytics Pro V12")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u in USERS_DB and USERS_DB[u]['password'] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = USERS_DB[u]['role']
                st.session_state.allowed_pages = USERS_DB[u]['pages']
                st.rerun()
            else: st.error("Invalid Login")
        return

    track_page_view()
    
    # Sidebar
    st.sidebar.title(f"🚀 {st.session_state.username}")
    
    # Admin Panel (Always accessible to admin even if files are missing)
    if st.session_state.role == 'admin':
        if st.sidebar.checkbox("👑 Admin Panel"):
            st.markdown("### 📊 Admin Dashboard")
            c1, c2, c3 = st.columns(3)
            c1.metric("👥 Total Users", len(USERS_DB))
            c2.metric("👁️ Page Views", st.session_state.page_views)
            c3.metric("📊 Active Sessions", 1)
            
            st.markdown("#### 📂 File Status Tracker")
            for city, data in CITIES_DATA.items():
                exists = os.path.exists(data['file'])
                status = "✅ Found" if exists else "❌ Missing"
                st.write(f"**{city}:** {data['file']} - {status}")
            
            st.markdown("#### ⏳ Subscription Tracker")
            for user, data in USERS_DB.items():
                if data['role'] == 'admin': continue
                created = datetime.strptime(data['created_at'], "%Y-%m-%d")
                days = (datetime.now() - created).days
                st.info(f"👤 {user} | Joined: {data['created_at']} | Days: {days % 30}/30")
            
            st.markdown("#### 🔐 User Permissions")
            for user, data in USERS_DB.items():
                if data['role'] == 'admin': continue
                st.write(f"**{user}** - Pages: {', '.join(data['pages'])}")
    
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

    # Data Loading Section
    city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
    df, col_map, err = load_data(CITIES_DATA[city]['file'])
    
    if err:
        st.warning(f"⚠️ {err}")
        st.info("Please upload the Excel file to GitHub to see the analytics.")
        return

    # Page Selection Logic
    page_map = {
        "dashboard": "📊 Dashboard",
        "trends": "📈 Trends",
        "rankings": "🏆 Rankings",
        "tracker": "🔍 Tracker",
        "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location",
        "competitor": "👁️ Competitor Watch",
        "compare": "🌍 City Compare"
    }
    
    if "all" in st.session_state.allowed_pages:
        available_pages = list(page_map.values())
    else:
        available_pages = [page_map[p] for p in st.session_state.allowed_pages if p in page_map]

    selected_page = st.sidebar.radio("Select Page", available_pages)

    # ===================== PAGES =====================
    if selected_page == "📊 Dashboard":
        st.markdown(f"### 📊 {city} Market Insights")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Price Gap", f"${df['Best_Price'].max() - df['Best_Price'].min():.0f}")
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution"), use_container_width=True)

    elif selected_page == "📈 Trends":
        st.markdown("### 📅 Best Arrival Days & Booking Analysis")
        if 'Day' in df.columns and df['Day'].iloc[0] != "Unknown":
            day_avg = df.groupby('Day')['Best_Price'].mean().sort_values()
            st.plotly_chart(px.bar(x=day_avg.index, y=day_avg.values, title="Price by Day"), use_container_width=True)
        
        if 'days_before' in df.columns:
            st.markdown("#### 🎯 Optimal Booking Window")
            df_valid = df[df['days_before'] > 0]
            if not df_valid.empty:
                st.info("Analysis: Booking earlier usually saves more!")
                st.bar_chart(df_valid.groupby('days_before')['Best_Price'].mean())

    elif selected_page == "🏆 Rankings":
        st.markdown("### 🏆 Top Rankings by Stars")
        df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
        for s in [5, 4, 3]:
            st.markdown(f"#### ⭐ {s} Star Excellence")
            for _, row in df_u[df_u['Star'] == s].head(3).iterrows():
                with st.container(border=True):
                    st.subheader(f"🏨 {row[col_map['Hotel']]}")
                    st.write(f"💰 Price: ${row['Best_Price']:.0f} | ⭐ Rate: {row['Rate']}/10")

    elif selected_page == "🔍 Tracker":
        st.markdown("### 🔍 Professional Tracker")
        target = st.selectbox("Select Hotel", sorted(df[col_map['Hotel']].unique()))
        h_data = df[df[col_map['Hotel']] == target].sort_values('arrival_dt')
        if not h_data.empty:
            st.plotly_chart(px.line(h_data, x='arrival_dt', y='Best_Price', markers=True), use_container_width=True)

    elif selected_page == "🎉 Fun Facts":
        st.markdown("### 🎉 Fun Facts for Bloggers")
        st.success(f"🤔 Did you know? The cheapest hotel in {city} is only ${df['Best_Price'].min():.0f}!")
        st.success(f"😱 Believe it or not! The most expensive hotel reaches ${df['Best_Price'].max():.0f}")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location/Area")
        if col_map['Location']:
            locations = df[col_map['Location']].dropna().unique()
            selected_loc = st.selectbox("Select Location", locations)
            loc_df = df[df[col_map['Location']] == selected_loc]
            st.dataframe(loc_df[[col_map['Hotel'], 'Best_Price', col_map['Rate']]])
        else:
            st.info("Location data not found in this file.")

    elif selected_page == "👁️ Competitor Watch":
        st.markdown("### 👁️ Competitor Price Monitoring")
        selected_hotels = st.multiselect("Select Hotels", sorted(df[col_map['Hotel']].unique()), max_selections=5)
        if selected_hotels:
            watch_df = df[df[col_map['Hotel']].isin(selected_hotels)]
            st.dataframe(watch_df[[col_map['Hotel'], 'Best_Price', col_map['Rate']]])

    elif selected_page == "🌍 City Compare":
        st.markdown("### 🌍 City Comparison")
        city2 = st.selectbox("Compare with:", [c for c in CITIES_DATA.keys() if c != city])
        df2, _, _ = load_data(CITIES_DATA[city2]['file'])
        if df2 is not None:
            st.write(f"**{city} Avg Price:** ${df['Best_Price'].mean():.0f}")
            st.write(f"**{city2} Avg Price:** ${df2['Best_Price'].mean():.0f}")

if __name__ == "__main__": main()
