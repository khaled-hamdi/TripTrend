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
    "admin": {"password": "admin123", "created_at": "2026-01-01", "role": "admin"},
    "test1": {"password": "password123", "created_at": "2026-07-01", "role": "user"},
    "company_a": {"password": "company@123", "created_at": "2026-07-10", "role": "user"},
    "blogger_pro": {"password": "blogger2024", "created_at": "2026-07-11", "role": "user"},
    "new_client": {"password": "test@2024", "created_at": "2026-07-12", "role": "user"}
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
st.set_page_config(page_title="Hotel Analytics Pro V10", page_icon="🚀", layout="wide")

# ======================================================================================
# --- CORE FUNCTIONS ---
# ======================================================================================
def find_column(df, possible_names):
    for name in possible_names:
        for col in df.columns:
            if str(col).strip().lower() == name.lower(): return col
    return None

@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, "File not found"
    try:
        df = pd.read_excel(file_path)
        col_map = {
            'Hotel': find_column(df, ['Hotel_Name', 'Hotel Name', 'hotel', 'الاسم']),
            'P1': find_column(df, ['Price1', 'price 1', 'سعر 1']),
            'P2': find_column(df, ['price2', 'Price2', 'price 2', 'سعر 2']),
            'P3': find_column(df, ['price3', 'Price3', 'price 3', 'سعر 3']),
            'Rate': find_column(df, ['Rate', 'rate', 'التقييم', 'Rating']),
            'Star': find_column(df, ['Star', 'star', 'النجوم', 'Stars']),
            'Arrival': find_column(df, ['date of arrival', 'Date of Arrival', 'arrival date', 'تاريخ الوصول', 'arrival']),
            'Place1': find_column(df, ['Place1', 'place 1', 'منصة 1']),
            'Place3': find_column(df, ['place3', 'Place3', 'place 3', 'منصة 3']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة'])
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
            
        return df, col_map, None
    except Exception as e: return None, None, str(e)

def show_hotel_card(row, col_map, city):
    # استخدام st.container بدلاً من HTML المباشر لتجنب مشاكل العرض
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            st.subheader(f"🏨 {row[col_map['Hotel']]}")
        with c2:
            if row['Best_Price'] < 150:
                st.error("🔥 HOT DEAL")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Price", f"${row['Best_Price']:.0f}")
        m2.metric("⭐ Rate", f"{row['Rate']}/10")
        m3.metric("🌟 Stars", f"{int(row['Star'])}")
        
        st.write(f"📍 **Dist:** {row[col_map['Dist']] if col_map['Dist'] else 'N/A'}")
        st.write(f"🔗 **Platforms:** {row[col_map['Place1']]} / {row[col_map['Place3']]}")
        
        with st.expander("🤳 Blogger AI Assistant"):
            lang = st.radio("Select Language", ["Arabic", "English"], key=f"lang_{row.name}", horizontal=True)
            hotel = row[col_map['Hotel']]
            price = row['Best_Price']
            stars = "⭐" * int(row['Star'])
            
            if lang == "Arabic":
                post = f"🌟 عرض لا يفوت في {city}! 🌟\n\nفندق {hotel} {stars}\n💰 السعر: ${price:.0f} فقط!\n⭐ التقييم: {row['Rate']}/10\n📍 الموقع: {row[col_map['Dist']] if col_map['Dist'] else 'ممتاز'}\n\nاحجز الآن قبل فوات الأوان! ✈️ #سياحة #فنادق #{city}"
            else:
                post = f"🌟 Unmissable Deal in {city}! 🌟\n\n{hotel} {stars}\n💰 Price: ${price:.0f} only!\n⭐ Rating: {row['Rate']}/10\n📍 Location: {row[col_map['Dist']] if col_map['Dist'] else 'Prime Location'}\n\nBook now before it's gone! ✈️ #Travel #Hotels #{city}"
            st.code(post, language="text")

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V10")
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if u in USERS_DB and USERS_DB[u]['password'] == p:
                st.session_state.logged_in = True
                st.session_state.username = u
                st.session_state.role = USERS_DB[u]['role']
                st.rerun()
            else: st.error("Invalid Login")
        return

    # Sidebar
    st.sidebar.title(f"🚀 {st.session_state.username}")
    if st.session_state.role == 'admin':
        if st.sidebar.checkbox("👑 Admin Panel"):
            st.markdown("### ⏳ Subscription Tracker")
            for user, data in USERS_DB.items():
                if data['role'] == 'admin': continue
                created = datetime.strptime(data['created_at'], "%Y-%m-%d")
                days = (datetime.now() - created).days
                st.info(f"👤 {user} | Joined: {data['created_at']} | Days: {days % 30}/30")

    city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
    df, col_map, err = load_data(CITIES_DATA[city]['file'])
    if err: st.error(err); return

    # Tabs
    t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Dashboard", "🔥 Deal Radar", "📈 Trends", "🏆 Rankings", "🔍 Tracker", "🌍 City Compare"])

    with t1:
        st.markdown(f"### 📊 {city} Market Insights")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Price Gap", f"${df['Best_Price'].max() - df['Best_Price'].min():.0f}")
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution", color_discrete_sequence=['#667eea']), use_container_width=True)

    with t2:
        st.markdown("### 🔥 Deal Radar")
        avg_p = df['Best_Price'].mean()
        deals = df[df['Best_Price'] < (avg_p * 0.8)].sort_values('Best_Price')
        if not deals.empty:
            for _, row in deals.head(10).iterrows(): show_hotel_card(row, col_map, city)
        else: st.info("No extreme deals found today.")

    with t3:
        st.markdown("### 📅 Best Arrival Days")
        # محاولة ذكية لإيجاد التواريخ إذا كانت مفقودة
        if 'Day' in df.columns and not df['Day'].isnull().all() and df['Day'].iloc[0] != "Unknown":
            day_avg = df.groupby('Day')['Best_Price'].mean().sort_values()
            cols = st.columns(len(day_avg))
            for i, (d, p) in enumerate(day_avg.items()):
                cols[i].metric(d, f"${p:.0f}")
            st.plotly_chart(px.bar(x=day_avg.index, y=day_avg.values, title="Price by Day"), use_container_width=True)
        else:
            st.warning("⚠️ Date information missing or invalid in Excel file.")
            st.info("Please ensure your Excel has a column named 'date of arrival'.")

    with t4:
        st.markdown("### 🏆 Top Rankings")
        df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
        for s in [5, 4, 3]:
            st.markdown(f"#### ⭐ {s} Star Excellence")
            stars_df = df_u[df_u['Star'] == s]
            if not stars_df.empty:
                for _, row in stars_df.head(3).iterrows(): show_hotel_card(row, col_map, city)
            else: st.info(f"No {s}-star hotels found.")

    with t5:
        st.markdown("### 🔍 Professional Tracker")
        target = st.selectbox("Select Hotel", sorted(df[col_map['Hotel']].unique()))
        h_data = df[df[col_map['Hotel']] == target].sort_values('arrival_dt')
        if not h_data.empty and not h_data['arrival_dt'].isnull().all():
            st.plotly_chart(px.line(h_data, x='arrival_dt', y='Best_Price', markers=True), use_container_width=True)
        st.dataframe(h_data[[col_map['Hotel'], 'Best_Price', col_map['Place1'], col_map['Place3']]], use_container_width=True)

    with t6:
        st.markdown("### 🌍 City vs City Comparison")
        city2 = st.selectbox("Compare with:", [c for c in CITIES_DATA.keys() if c != city])
        df2, _, _ = load_data(CITIES_DATA[city2]['file'])
        if df2 is not None:
            comp_data = pd.DataFrame({
                'City': [city, city2],
                'Avg Price': [df['Best_Price'].mean(), df2['Best_Price'].mean()]
            })
            st.plotly_chart(px.bar(comp_data, x='City', y='Avg Price', color='City'), use_container_width=True)

if __name__ == "__main__": main()
