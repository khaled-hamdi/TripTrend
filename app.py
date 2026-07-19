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
    "Paris": {"file": "Paris_updated.xlsx", "emoji": "🗼", "country": "France"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️", "country": "UAE"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌", "country": "Turkey"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️", "country": "Egypt"}
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V17", page_icon="🚀", layout="wide")

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
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel', 'الاسم', 'Hotel Name']),
            'Rate': find_column(df, ['Rate', 'rating', 'التقييم', 'Rating']),
            'Star': find_column(df, ['Star', 'stars', 'النجوم', 'Stars']),
            'P1': find_column(df, ['Price1', 'price1', 'سعر 1', 'Price 1']),
            'P2': find_column(df, ['price2', 'Price2', 'سعر 2', 'Price 2']),
            'P3': find_column(df, ['price3', 'Price3', 'سعر 3', 'Price 3']),
            'Place1': find_column(df, ['Place1', 'place1', 'منصة 1', 'Booking 1']),
            'Place2': find_column(df, ['Place2', 'place2', 'منصة 2', 'Booking 2']),
            'Place3': find_column(df, ['place3', 'Place3', 'منصة 3', 'Booking 3']),
            'Arrival': find_column(df, ['date of arrival', 'date_of_arrival', 'تاريخ الوصول', 'arrival', 'Arrival Date']),
            'Booking': find_column(df, ['day of book', 'day_of_book', 'تاريخ الحجز', 'booking', 'Booking Date']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة', 'Distance']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف', 'Description']),
            'Location': find_column(df, ['location', 'area', 'المنطقة', 'Location'])
        }
        
        # Robust Numeric Conversions
        for p in ['P1', 'P2', 'P3']:
            if col_map[p]:
                df[col_map[p]] = pd.to_numeric(df[col_map[p]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        # Calculate Best Price using available price columns
        price_cols = [col_map['P1'], col_map['P2'], col_map['P3']]
        valid_price_cols = [c for c in price_cols if c and c in df.columns]
        if valid_price_cols:
            df['Best_Price'] = df[valid_price_cols].min(axis=1)
        else:
            df['Best_Price'] = 0
            
        df['Rate'] = pd.to_numeric(df[col_map['Rate']] if col_map['Rate'] else 0, errors='coerce').fillna(0)
        
        if col_map['Star']:
            df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        else:
            df['Star'] = 0
            
        # Robust Date Parsing
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

def get_booking_company(row, col_map):
    for p_col in ['Place1', 'Place2', 'Place3']:
        if col_map.get(p_col) and pd.notnull(row[col_map[p_col]]):
            return row[col_map[p_col]]
    return "N/A"

def generate_fun_facts(df, col_map, city, lang="Arabic"):
    facts = []
    if df.empty: return ["لا توجد بيانات كافية" if lang=="Arabic" else "No data available"]
    hotel_col = col_map['Hotel']
    
    try:
        # Price Facts
        if not df['Best_Price'].empty:
            cheapest = df.loc[df['Best_Price'].idxmin()]
            expensive = df.loc[df['Best_Price'].idxmax()]
            if lang == "Arabic":
                facts.append(f"💰 أرخص خيار: **{cheapest[hotel_col]}** بـ ${cheapest['Best_Price']:.0f}.")
                facts.append(f"💎 أغلى خيار: **{expensive[hotel_col]}** بـ ${expensive['Best_Price']:.0f}.")
            else:
                facts.append(f"💰 Cheapest: **{cheapest[hotel_col]}** at ${cheapest['Best_Price']:.0f}.")
                facts.append(f"💎 Most expensive: **{expensive[hotel_col]}** at ${expensive['Best_Price']:.0f}.")
        
        # Rating Facts
        if not df['Rate'].empty:
            top_rated = df.loc[df['Rate'].idxmax()]
            if lang == "Arabic":
                facts.append(f"🌟 الأفضل تقييماً: **{top_rated[hotel_col]}** ({top_rated['Rate']}/10).")
            else:
                facts.append(f"🌟 Top rated: **{top_rated[hotel_col]}** ({top_rated['Rate']}/10).")
        
        # Cumulative/Time-based facts
        if 'arrival_dt' in df.columns and not df['arrival_dt'].dropna().empty:
            unique_dates = df['arrival_dt'].nunique()
            if lang == "Arabic":
                facts.append(f"📅 تم تحليل الأسعار عبر {unique_dates} تواريخ وصول مختلفة.")
            else:
                facts.append(f"📅 Prices analyzed across {unique_dates} different arrival dates.")
                
        # Booking Window
        if 'days_before' in df.columns and not df['days_before'].dropna().empty:
            best_window = df.groupby('days_before')['Best_Price'].mean().idxmin()
            if lang == "Arabic":
                facts.append(f"🎯 الحجز قبل {int(best_window)} يوم يمنحك أفضل سعر تاريخياً.")
            else:
                facts.append(f"🎯 Booking {int(best_window)} days in advance is historically cheapest.")

        # Platform analysis
        if col_map['Place1']:
            top_p = df[col_map['Place1']].value_counts().idxmax()
            if lang == "Arabic":
                facts.append(f"🌐 منصة **{top_p}** هي الأكثر تواجداً في العروض.")
            else:
                facts.append(f"🌐 Platform **{top_p}** appears most in offers.")

        # Dynamic expansion (Add 10 more varied facts)
        facts.append(f"📊 {len(df)} عرض فندقي تم معالجتها في {city}." if lang=="Arabic" else f"📊 {len(df)} hotel offers processed in {city}.")
        facts.append(f"🏆 {len(df[df['Rate'] > 9])} فندق حصلوا على تقييم أسطوري (>9)." if lang=="Arabic" else f"🏆 {len(df[df['Rate'] > 9])} hotels have legendary ratings (>9).")
        facts.append(f"✨ {len(df[df['Star'] == 5])} فندق 5 نجوم متاح." if lang=="Arabic" else f"✨ {len(df[df['Star'] == 5])} 5-star hotels available.")
        
    except Exception as e: facts.append(f"Note: {str(e)}")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V17")
        u, p = st.text_input("User"), st.text_input("Pass", type="password")
        if st.button("Login"):
            if u in USERS_DB and USERS_DB[u]['password'] == p:
                st.session_state.logged_in, st.session_state.username = True, u
                st.session_state.role, st.session_state.allowed_pages = USERS_DB[u]['role'], USERS_DB[u]['pages']
                st.rerun()
        return

    st.sidebar.title(f"🚀 {st.session_state.username}")
    city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
    df, col_map, err = load_data(CITIES_DATA[city]['file'])
    
    if err: st.warning(f"⚠️ {err}"); return

    page_map = {
        "dashboard": "📊 Dashboard", "trends": "📈 Trends", "rankings": "🏆 Rankings",
        "tracker": "🔍 Professional Tracker", "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location", "competitor": "⚔️ Competitor Analysis",
        "compare": "🌍 City Compare", "custom_compare": "🎯 Custom Hotel Compare"
    }
    
    available_pages = [page_map[p] for p in (list(page_map.keys()) if "all" in st.session_state.allowed_pages else st.session_state.allowed_pages) if p in page_map]
    selected_page = st.sidebar.radio("Select Page", available_pages)

    # --- PAGES ---
    if selected_page == "📊 Dashboard":
        st.markdown(f"### 📊 {city} Market Insights")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Offers Count", len(df))
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution"), use_container_width=True)

    elif selected_page == "📈 Trends":
        st.markdown("### 📅 Trends & Booking Analysis")
        if 'Day' in df.columns:
            st.plotly_chart(px.bar(df.groupby('Day')['Best_Price'].mean().sort_values(), title="Price by Day"), use_container_width=True)
        if 'days_before' in df.columns:
            st.plotly_chart(px.line(df.groupby('days_before')['Best_Price'].mean().reset_index(), x='days_before', y='Best_Price', title="Optimal Booking Window"), use_container_width=True)

    elif selected_page == "🏆 Rankings":
        st.markdown("### 🏆 Top Hotel Rankings")
        df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
        for s in [5, 4, 3]:
            st.markdown(f"#### ⭐ {s} Star Rankings")
            stars_df = df_u[df_u['Star'] == s].head(5)
            if not stars_df.empty:
                for _, row in stars_df.iterrows():
                    with st.container(border=True):
                        st.subheader(f"🏨 {row[col_map['Hotel']]}")
                        st.write(f"💰 Best Price: ${row['Best_Price']:.0f} | ⭐ Rate: {row['Rate']}/10")
            else: st.write("No data for this star rating.")

    elif selected_page == "🎉 Fun Facts":
        st.markdown("### 🎉 Fun Facts & Insights")
        lang = st.radio("Language", ["Arabic", "English"], horizontal=True)
        facts = generate_fun_facts(df, col_map, city, lang)
        cols = st.columns(2)
        for i, fact in enumerate(facts): cols[i % 2].success(fact)

    elif selected_page == "🔍 Professional Tracker":
        st.markdown("### 🔍 Professional Market Tracker")
        if 'arrival_dt' in df.columns and not df['arrival_dt'].dropna().empty:
            st.plotly_chart(px.line(df.groupby('arrival_dt')['Best_Price'].agg(['mean', 'min']).reset_index(), x='arrival_dt', y=['mean', 'min'], title="Market Trend"), use_container_width=True)
            hotel_opts = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']} | 📍{r[col_map['Location']]}", axis=1).unique()
            sel = st.selectbox("Track Hotel", hotel_opts)
            h_name = sel.split(" | ")[0]
            st.line_chart(df[df[col_map['Hotel']] == h_name].sort_values('arrival_dt').set_index('arrival_dt')['Best_Price'])
        else: st.info("Arrival dates missing for tracking.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location")
        if col_map['Location']:
            loc = st.selectbox("Select Area", df[col_map['Location']].dropna().unique())
            loc_df = df[df[col_map['Location']] == loc].copy()
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(loc_df[[col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['Arrival'], col_map['Desc']]].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "⚔️ Competitor Analysis":
        st.markdown("### ⚔️ Competitor Intelligence")
        hotel = st.selectbox("Select Hotel", df[col_map['Hotel']].unique())
        target = df[df[col_map['Hotel']] == hotel].iloc[0]
        with st.container(border=True):
            st.subheader(f"🏨 {hotel} | ${target['Best_Price']:.0f}")
            st.write(f"⭐ {target['Star']} Stars | 📍 {target[col_map['Location']]}")
            st.info(f"**Description:** {target[col_map['Desc']]}")
        
        comps = df[df[col_map['Hotel']] != hotel].copy()
        if target[col_map['Location']]: comps = comps[comps[col_map['Location']] == target[col_map['Location']]]
        comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
        st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate', 'Star', col_map['Arrival']]].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "🎯 Custom Hotel Compare":
        st.markdown("### 🎯 Custom Comparison")
        all_h = []
        for c, info in CITIES_DATA.items():
            t_df, t_map, _ = load_data(info['file'])
            if t_df is not None: t_df['City'] = c; t_df['Booking Company'] = t_df.apply(lambda r: get_booking_company(r, t_map), axis=1); all_h.append(t_df)
        if all_h:
            full = pd.concat(all_h, ignore_index=True)
            sel = st.multiselect("Select Hotels", full.apply(lambda r: f"{r[col_map['Hotel']]} ({r['City']})", axis=1).unique())
            if sel:
                names = [s.split(" (")[0] for s in sel]
                st.dataframe(full[full[col_map['Hotel']].isin(names)][['City', col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['Location'], col_map['Arrival'], col_map['Desc']]], hide_index=True)

if __name__ == "__main__": main()
