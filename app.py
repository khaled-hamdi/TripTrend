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
st.set_page_config(page_title="Hotel Analytics Pro V13", page_icon="🚀", layout="wide")

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
            'Arrival': find_column(df, ['date of arrival', 'date_of_arrival', 'تاريخ الوصول', 'arrival']),
            'Booking': find_column(df, ['day of book', 'day_of_book', 'تاريخ الحجز', 'booking']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف']),
            'Location': find_column(df, ['location', 'area', 'المنطقة'])
        }
        
        for p in ['P1', 'P2', 'P3']:
            if col_map[p]: df[col_map[p]] = pd.to_numeric(df[col_map[p]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        
        # Robust Date Conversion
        if col_map['Arrival']:
            df['arrival_dt'] = pd.to_datetime(df[col_map['Arrival']], errors='coerce')
            df['Month'] = df['arrival_dt'].dt.strftime('%B')
            df['Day'] = df['arrival_dt'].dt.strftime('%A')
        
        if col_map['Booking']:
            df['booking_dt'] = pd.to_datetime(df[col_map['Booking']], errors='coerce')
            if col_map['Arrival']:
                df['days_before'] = (df['arrival_dt'] - df['booking_dt']).dt.days
        
        return df, col_map, None
    except Exception as e: return None, None, str(e)

def generate_fun_facts(df, col_map, city, lang):
    facts = []
    if lang == "Arabic":
        hotel_name_col = col_map.get('Hotel', 'Hotel_Name') # Fallback to 'Hotel_Name' if not in col_map
        cheapest_hotel = df.loc[df['Best_Price'].idxmin()][hotel_name_col] if not df['Best_Price'].empty and hotel_name_col in df.columns else 'فندق غير معروف'
        facts.append(f"💰 أرخص فندق في {city} هو {cheapest_hotel} بسعر ${df['Best_Price'].min():.0f} فقط!")
        if not df['Best_Price'].empty:
            facts.append(f"📈 فجوة السعر في {city} تصل إلى ${df['Best_Price'].max() - df['Best_Price'].min():.0f} بين أرخص وأغلى فندق.")
        else:
            facts.append(f"📈 لا توجد بيانات كافية لحساب فجوة السعر في {city}.")
        if not df['Rate'].empty:
            facts.append(f"⭐ متوسط تقييم الفنادق في {city} هو {df['Rate'].mean():.1f}/10.")
        else:
            facts.append(f"⭐ لا توجد بيانات تقييم للفنادق في {city}.")
        if 'days_before' in df.columns:
            best_window = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"🎯 نصيحة ذهبية: الحجز قبل {int(best_window)} يوم يمنحك أفضل سعر في {city}!")
    else:
        hotel_name_col = col_map.get('Hotel', 'Hotel_Name')
        cheapest_hotel = df.loc[df['Best_Price'].idxmin()][hotel_name_col] if not df['Best_Price'].empty and hotel_name_col in df.columns else 'Unknown Hotel'
        facts.append(f"💰 The cheapest hotel in {city} is {cheapest_hotel} for only ${df['Best_Price'].min():.0f}!")
        if not df['Best_Price'].empty:
            facts.append(f"📈 Price gap in {city} is ${df['Best_Price'].max() - df['Best_Price'].min():.0f} between min and max.")
        else:
            facts.append(f"📈 Not enough data to calculate price gap in {city}.")
        if not df['Rate'].empty:
            facts.append(f"⭐ Average hotel rating in {city} is {df['Rate'].mean():.1f}/10.")
        else:
            facts.append(f"⭐ No rating data available for hotels in {city}.")
        if 'days_before' in df.columns:
            best_window = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"🎯 Pro Tip: Booking {int(best_window)} days in advance gives you the best price in {city}!")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V13")
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

    # Sidebar
    st.sidebar.title(f"🚀 {st.session_state.username}")
    
    if st.session_state.role == 'admin':
        if st.sidebar.checkbox("👑 Admin Panel"):
            st.markdown("### 📊 Admin Dashboard")
            c1, c2 = st.columns(2)
            c1.metric("👥 Total Users", len(USERS_DB))
            c2.metric("👁️ Page Views", st.session_state.get('page_views', 0))
            
            st.markdown("#### 📂 File Status")
            for city, data in CITIES_DATA.items():
                status = "✅" if os.path.exists(data['file']) else "❌"
                st.write(f"{status} **{city}:** {data['file']}")

    city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
    df, col_map, err = load_data(CITIES_DATA[city]['file'])
    
    if err:
        st.warning(f"⚠️ {err}")
        return

    # Page Selection
    page_map = {
        "dashboard": "📊 Dashboard",
        "trends": "📈 Trends",
        "rankings": "🏆 Rankings",
        "tracker": "🔍 Tracker",
        "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location",
        "competitor": "⚔️ Competitor Price",
        "compare": "📊 Price Compare"
    }
    
    if "all" in st.session_state.allowed_pages:
        available_pages = list(page_map.values())
    else:
        # Map existing roles to include the new competitor page if they had 'all' access or similar
        allowed_p = list(st.session_state.allowed_pages)
        if "all" in allowed_p:
            available_pages = list(page_map.values())
        else:
            available_pages = [page_map[p] for p in allowed_p if p in page_map]

    selected_page = st.sidebar.radio("Select Page", available_pages)

    # ===================== PAGES =====================
    if selected_page == "📊 Dashboard":
        st.markdown(f"### 📊 {city} Market Insights")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Price Gap", f"${df['Best_Price'].max() - df['Best_Price'].min():.0f}")
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution", color_discrete_sequence=['#667eea']), use_container_width=True)

    elif selected_page == "📈 Trends":
        st.markdown("### 📅 Best Arrival Days & Booking Analysis")
        if 'Day' in df.columns and df['Day'].notnull().any():
            day_avg = df.groupby('Day')['Best_Price'].mean().sort_values()
            st.plotly_chart(px.bar(x=day_avg.index, y=day_avg.values, title="Price by Day"), use_container_width=True)
        
        if 'days_before' in df.columns:
            st.markdown("#### 🎯 Optimal Booking Window")
            df_valid = df[df['days_before'] >= 0]
            if not df_valid.empty:
                # Grouping by days before to see the trend
                window_avg = df_valid.groupby('days_before')['Best_Price'].mean().reset_index()
                st.plotly_chart(px.line(window_avg, x='days_before', y='Best_Price', title="Price vs Days Booked in Advance"), use_container_width=True)
                st.info("💡 Tip: Lower points on the graph indicate the best time to book!")
            else:
                st.info("No sufficient data available to determine the optimal booking window.")

    elif selected_page == "🏆 Rankings":
        st.markdown("### 🏆 Top Rankings by Stars")
        df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
        for s in [5, 4, 3]:
            st.markdown(f"#### ⭐ {s} Star Excellence")
            for _, row in df_u[df_u['Star'] == s].head(3).iterrows():
                with st.container(border=True):
                    st.subheader(f"🏨 {row[col_map['Hotel']]}")
                    st.write(f"💰 Price: ${row['Best_Price']:.0f} | ⭐ Rate: {row['Rate']}/10")

    elif selected_page == "🎉 Fun Facts":
        st.markdown("### 🎉 Fun Facts for Bloggers")
        lang = st.radio("Select Language | اختر اللغة", ["Arabic", "English"], horizontal=True)
        facts = generate_fun_facts(df, col_map, city, lang)
        for fact in facts:
            st.success(fact)

    elif selected_page == "🔍 Tracker":
        st.markdown("### 🔍 Professional Tracker")
        st.info("This section provides advanced tracking and monitoring tools for hotel performance and competitor analysis.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location/Area")
        if col_map['Location'] and df[col_map['Location']].notnull().any():
            locations = df[col_map['Location']].dropna().unique()
            selected_loc = st.selectbox("Select Location", locations)
            loc_df = df[df[col_map['Location']] == selected_loc].copy()
            
            # Select relevant columns including arrival date
            cols_to_show = [col_map['Hotel'], 'Best_Price', col_map['Rate']]
            if col_map['Arrival']:
                cols_to_show.append(col_map['Arrival'])
            
            # Remove duplicates: Keep the one with the best price for each hotel on each arrival date
            if col_map['Arrival']:
                loc_df = loc_df.sort_values('Best_Price').drop_duplicates(subset=[col_map['Hotel'], col_map['Arrival']], keep='first')
            else:
                loc_df = loc_df.sort_values('Best_Price').drop_duplicates(subset=[col_map['Hotel']], keep='first')
                
            st.dataframe(loc_df[cols_to_show])
        else:
            st.info("Location data not found in this file.")

    elif selected_page == "⚔️ Competitor Price":
        st.markdown("### ⚔️ Competitor Price Analysis")
        
        # Determine the booking company (first available from Place1, Place2, Place3)
        def get_booking_company(row):
            for p_col in ['Place1', 'Place2', 'Place3']:
                if col_map.get(p_col) and pd.notnull(row[col_map[p_col]]):
                    return row[col_map[p_col]]
            return "N/A"

        comp_df = df.copy()
        comp_df['Booking Company'] = comp_df.apply(get_booking_company, axis=1)
        
        cols_to_show = [col_map['Hotel'], 'Star', 'Best_Price', 'Booking Company']
        if col_map['Arrival']: cols_to_show.append(col_map['Arrival'])
        if col_map['Desc']: cols_to_show.append(col_map['Desc'])
        
        st.dataframe(comp_df[cols_to_show])

    elif selected_page == "📊 Price Compare":
        st.markdown("### 📊 Price Comparison Across Cities")
        comparison_data = []
        for city_name, city_info in CITIES_DATA.items():
            temp_df, _, _ = load_data(city_info['file'])
            if temp_df is not None:
                comparison_data.append({
                    "City": city_name,
                    "Avg Price": temp_df['Best_Price'].mean(),
                    "Min Price": temp_df['Best_Price'].min(),
                    "Max Price": temp_df['Best_Price'].max(),
                    "Hotel Count": len(temp_df)
                })
        
        if comparison_data:
            compare_df = pd.DataFrame(comparison_data)
            st.dataframe(compare_df)
            st.plotly_chart(px.bar(compare_df, x='City', y='Avg Price', title="Average Price by City"), use_container_width=True)
        else:
            st.info("No data available for comparison.")

if __name__ == "__main__": main()
