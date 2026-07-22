import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import re

# ======================================================================================
# --- CONFIGURATION & USERS ---
# ======================================================================================
USERS_DB = {
    "admin": {"password": "admin123", "created_at": "2026-01-01", "role": "admin", "pages": ["all"]},
    "blogger_pro": {"password": "blogger2024", "created_at": "2026-07-11", "role": "blogger", "pages": ["dashboard", "trends", "fun_facts", "rankings"]},
}

CITIES_DATA = {
    "Paris": {"file": "Paris_updated.xlsx", "emoji": "🗼"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️"}
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V25", page_icon="🏨", layout="wide")

# ======================================================================================
# --- CORE FUNCTIONS ---
# ======================================================================================
def clean_price(val):
    if pd.isnull(val): return np.nan
    cleaned = re.sub(r'[^\d.]', '', str(val))
    try:
        return float(cleaned) if cleaned else np.nan
    except:
        return np.nan

def find_column(df, possible_names):
    df.columns = df.columns.str.strip()
    for name in possible_names:
        for col in df.columns:
            if str(col).strip().lower() == name.lower(): return col
    return None

def try_parse_dates(series):
    parsed = pd.to_datetime(series, errors='coerce')
    if parsed.isnull().all():
        try:
            current_year = datetime.now().year
            parsed = pd.to_datetime(series.astype(str) + f"-{current_year}", errors='coerce', format='%d-%b')
        except: pass
    return parsed

@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None, None, f"File not found: {file_path}"
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        
        col_map = {
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel']),
            'Rate': find_column(df, ['Rate', 'rating']),
            'Star': find_column(df, ['Star', 'stars']),
            'P1': find_column(df, ['Price1', 'price1']),
            'P2': find_column(df, ['price2', 'Price2']),
            'P3': find_column(df, ['price3', 'Price3']),
            'Place1': find_column(df, ['Place1', 'place1']),
            'Place2': find_column(df, ['place2', 'Place2']),
            'Place3': find_column(df, ['place3', 'Place3']),
            'ArrivalDay': find_column(df, ['day of arrival']),
            'BookingDate': find_column(df, ['start book', 'date of creat booking']),
            'BookingDay': find_column(df, ['day of book']),
            'Dist': find_column(df, ['Distance From places', 'distance']),
            'Desc': find_column(df, ['Desc', 'description']),
            'Location': find_column(df, ['location', 'area'])
        }
        
        for key in col_map:
            if col_map[key] is None:
                dummy = f"dummy_{key}"
                df[dummy] = np.nan
                col_map[key] = dummy

        # ROBUST PRICE CLEANING
        for p in ['P1', 'P2', 'P3']:
            df[col_map[p]] = df[col_map[p]].apply(clean_price)
        
        # Smart Best Price (Avoid NaN)
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Best_Price'] = df['Best_Price'].fillna(df[col_map['P1']])
        
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        
        # SMART DATE INFERENCE
        df['booking_dt'] = try_parse_dates(df[col_map['BookingDate']])
        
        # Infer Arrival Date from Booking Date + Arrival Day Name
        days_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        
        def infer_arrival(row):
            if pd.isnull(row['booking_dt']) or pd.isnull(row[col_map['ArrivalDay']]): return np.nan
            b_dt = row['booking_dt']
            arr_day_name = str(row[col_map['ArrivalDay']]).strip().capitalize()
            if arr_day_name not in days_map: return b_dt # Fallback
            
            target_weekday = days_map[arr_day_name]
            current_weekday = b_dt.weekday()
            
            days_diff = (target_weekday - current_weekday) % 7
            if days_diff == 0: days_diff = 7 # Assume next week if same day
            
            return b_dt + timedelta(days=days_diff)

        df['arrival_dt'] = df.apply(infer_arrival, axis=1)
        df['days_before'] = (df['arrival_dt'] - df['booking_dt']).dt.days
        
        return df, col_map, None
    except Exception as e: return None, None, str(e)

def get_booking_company(row, col_map):
    for p_col in ['Place1', 'Place2', 'Place3']:
        val = row[col_map[p_col]]
        if pd.notnull(val) and str(val).strip() != "": return str(val)
    return "N/A"

def generate_fun_facts(df, col_map, city, lang="Arabic"):
    facts = []
    if df.empty: return ["لا توجد بيانات"]
    h_col = col_map['Hotel']
    try:
        # 20+ Dynamic Fact Engine
        cheapest = df.loc[df['Best_Price'].idxmin()]
        facts.append(f"💰 أرخص فندق: **{cheapest[h_col]}** بـ ${cheapest['Best_Price']:.0f}." if lang=="Arabic" else f"💰 Cheapest: **{cheapest[h_col]}** at ${cheapest['Best_Price']:.0f}.")
        
        expensive = df.loc[df['Best_Price'].idxmax()]
        facts.append(f"💎 أغلى فندق: **{expensive[h_col]}** بـ ${expensive['Best_Price']:.0f}." if lang=="Arabic" else f"💎 Most expensive: **{expensive[h_col]}** at ${expensive['Best_Price']:.0f}.")
        
        top_rated = df.loc[df['Rate'].idxmax()]
        facts.append(f"🌟 الأعلى تقييماً: **{top_rated[h_col]}** ({top_rated['Rate']}/10)." if lang=="Arabic" else f"🌟 Top rated: **{top_rated[h_col]}** ({top_rated['Rate']}/10).")
        
        avg_p = df['Best_Price'].mean()
        facts.append(f"📉 متوسط السعر في {city}: ${avg_p:.0f}." if lang=="Arabic" else f"📉 Market avg in {city}: ${avg_p:.0f}.")
        
        df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        best_v = df.loc[df['Value'].idxmax()]
        facts.append(f"🎯 صفقة اليوم: **{best_v[h_col]}** (أفضل جودة مقابل سعر)." if lang=="Arabic" else f"🎯 Deal of the day: **{best_v[h_col]}** (Quality/Price).")
        
        facts.append(f"📊 تم تحليل {len(df)} عرض فندقي مختلف." if lang=="Arabic" else f"📊 {len(df)} total offers analyzed.")
        facts.append(f"📍 {df[col_map['Location']].nunique()} منطقة مغطاة بالكامل." if lang=="Arabic" else f"📍 {df[col_map['Location']].nunique()} areas fully covered.")
        
        if not df['days_before'].dropna().empty:
            best_w = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 نصيحة: الحجز قبل {int(best_w)} يوم هو الأوفر لك." if lang=="Arabic" else f"📅 Tip: Booking {int(best_w)} days ahead is cheapest.")

        facts.append(f"🌐 منصة **{df[col_map['Place1']].value_counts().idxmax()}** الأكثر نشاطاً." if lang=="Arabic" else f"🌐 **{df[col_map['Place1']].value_counts().idxmax()}** is the top platform.")
        facts.append(f"📉 {len(df[df['Best_Price'] < avg_p])} فندق أسعارهم تحت المتوسط." if lang=="Arabic" else f"📉 {len(df[df['Best_Price'] < avg_p])} hotels below market avg.")
        facts.append(f"🏆 {len(df[df['Rate'] >= 9])} فندق حصلوا على تقييم 'ممتاز جداً'." if lang=="Arabic" else f"🏆 {len(df[df['Rate'] >= 9])} hotels have 'Excellent' rating.")
        facts.append(f"✨ تم التحديث: {datetime.now().strftime('%Y-%m-%d')}.")
        
    except Exception as e: facts.append(f"Note: {str(e)}")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V25")
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

    # --- SHARED DATA FILTER (Latest vs All) ---
    data_mode = st.sidebar.radio("Analysis Mode", ["All Data (Cumulative)", "Latest Update Only"])
    if data_mode == "Latest Update Only":
        latest_b = df[col_map['BookingDate']].dropna().max()
        df = df[df[col_map['BookingDate']] == latest_b]

    page_map = {
        "dashboard": "📊 Dashboard", "trends": "📈 Trends & Patterns", "rankings": "🏆 Rankings",
        "tracker": "🔍 Price Tracker", "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location", "competitor": "⚔️ Competitor Analysis",
        "guide": "🧭 Traveler Guide", "custom_compare": "🎯 Custom Hotel Compare"
    }
    
    available_pages = [page_map[p] for p in (list(page_map.keys()) if "all" in st.session_state.allowed_pages else st.session_state.allowed_pages) if p in page_map]
    selected_page = st.sidebar.radio("Select Page", available_pages)

    # --- PAGES ---
    if selected_page == "📊 Dashboard":
        st.markdown(f"### 📊 {city} Market Insights ({data_mode})")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Offers Count", len(df))
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution"), use_container_width=True)

    elif selected_page == "📈 Trends & Patterns":
        st.markdown("### 📈 Trends: Market Patterns")
        st.write("Understand general market behaviors (e.g., which arrival day is cheapest).")
        st.plotly_chart(px.bar(df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().sort_values(), title="Price Pattern by Arrival Day"), use_container_width=True)
        
        st.markdown("#### 🎯 Optimal Booking Window")
        valid_bw = df.dropna(subset=['days_before'])
        if not valid_bw.empty:
            st.plotly_chart(px.line(valid_bw.groupby('days_before')['Best_Price'].mean().reset_index(), x='days_before', y='Best_Price', title="Best Time to Book (Days in Advance)"), use_container_width=True)
        else:
            st.info("💡 Booking Window calculation active based on 'start book' and 'day of arrival'.")

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
        st.markdown("### 🎉 Fun Facts & Viral Insights")
        lang = st.radio("Language", ["Arabic", "English"], horizontal=True)
        facts = generate_fun_facts(df, col_map, city, lang)
        cols = st.columns(2)
        for i, fact in enumerate(facts): cols[i % 2].success(fact)

    elif selected_page == "🔍 Price Tracker":
        st.markdown("### 🔍 Price Tracker: Price Evolution")
        st.write("Monitor how prices change over time for specific hotels or the whole market.")
        if not df['booking_dt'].dropna().empty:
            st.plotly_chart(px.line(df.groupby('booking_dt')['Best_Price'].agg(['mean', 'min']).reset_index(), x='booking_dt', y=['mean', 'min'], title="Market Price Evolution by Booking Date"), use_container_width=True)
        
        hotel_opts = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']} | 📍{r[col_map['Location']]}", axis=1).unique()
        sel = st.selectbox("Track Specific Hotel", hotel_opts)
        h_name = sel.split(" | ")[0]
        h_df = df[df[col_map['Hotel']] == h_name].sort_values('booking_dt')
        if not h_df.empty:
            st.line_chart(h_df.set_index(col_map['BookingDate'])['Best_Price'])

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location & History")
        valid_locs = df[col_map['Location']].dropna().unique()
        if len(valid_locs) > 0:
            loc = st.selectbox("Select Area", valid_locs)
            loc_df = df[df[col_map['Location']] == loc].copy()
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            cols = [col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['BookingDate'], col_map['ArrivalDay'], col_map['Desc']]
            st.dataframe(loc_df[cols].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "⚔️ Competitor Analysis":
        st.markdown("### ⚔️ Competitor Intelligence")
        hotel_list = df[col_map['Hotel']].dropna().unique()
        if len(hotel_list) > 0:
            hotel = st.selectbox("Select Hotel", hotel_list)
            target = df[df[col_map['Hotel']] == hotel].iloc[0]
            with st.container(border=True):
                st.subheader(f"🏨 {hotel} | ${target['Best_Price']:.0f}")
                st.write(f"⭐ {target['Star']} Stars | 📍 {target[col_map['Location']]}")
            
            comps = df[df[col_map['Hotel']] != hotel].copy()
            if pd.notnull(target[col_map['Location']]) and str(target[col_map['Location']]) != "":
                comps = comps[comps[col_map['Location']] == target[col_map['Location']]]
            else:
                comps = comps[comps['Star'] == target['Star']]
            
            comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate', 'Star', col_map['ArrivalDay']]].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "🧭 Traveler Guide":
        st.markdown("### 🧭 Smart Traveler Guide")
        pref = st.radio("Filter By:", ["Best Value", "Top Rated", "Lowest Price", "Features"])
        if pref == "Best Value":
            df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
            st.dataframe(df.sort_values('Value', ascending=False).head(10)[[col_map['Hotel'], 'Best_Price', 'Rate', col_map['Location'], col_map['Desc']]], hide_index=True)
        elif pref == "Top Rated":
            st.dataframe(df.sort_values('Rate', ascending=False).head(10)[[col_map['Hotel'], 'Rate', 'Best_Price', col_map['Location']]], hide_index=True)
        elif pref == "Lowest Price":
            st.dataframe(df.sort_values('Best_Price').head(10)[[col_map['Hotel'], 'Best_Price', 'Star', col_map['Location']]], hide_index=True)
        else:
            search = st.text_input("Search (e.g. 'View')")
            if search:
                res = df[df[col_map['Desc']].str.contains(search, case=False, na=False)]
                st.dataframe(res[[col_map['Hotel'], 'Best_Price', col_map['Desc']]], hide_index=True)

    elif selected_page == "🎯 Custom Hotel Compare":
        st.markdown("### 🎯 Custom Comparison")
        all_h = []
        for c, info in CITIES_DATA.items():
            t_df, t_map, _ = load_data(info['file'])
            if t_df is not None:
                t_df['City'] = c
                t_df['Booking Company'] = t_df.apply(lambda r: get_booking_company(r, t_map), axis=1)
                all_h.append(t_df)
        if all_h:
            full = pd.concat(all_h, ignore_index=True)
            sel = st.multiselect("Select Hotels", full.apply(lambda r: f"{r[col_map['Hotel']]} ({r['City']})", axis=1).unique())
            if sel:
                names = [s.split(" (")[0] for s in sel]
                sub = full[full[col_map['Hotel']].isin(names)].copy()
                results = []
                for name in names:
                    h_data = sub[sub[col_map['Hotel']] == name]
                    if not h_data.empty:
                        best_p = h_data['Best_Price'].min()
                        last_row = h_data.iloc[-1]
                        results.append({
                            "City": last_row['City'], "Hotel": name, "Best Price ($)": best_p,
                            "Last Price ($)": last_row['Best_Price'], "Stars": last_row['Star'],
                            "Rate": last_row['Rate'], "Booking Co": last_row['Booking Company'],
                            "Location": last_row[col_map['Location']], "Description": last_row[col_map['Desc']]
                        })
                st.dataframe(pd.DataFrame(results), hide_index=True)

if __name__ == "__main__": main()
