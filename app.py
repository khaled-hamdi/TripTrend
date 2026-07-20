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
st.set_page_config(page_title="Hotel Analytics Pro V18", page_icon="🚀", layout="wide")

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
        
        # Robust Mapping with multiple fallbacks
        col_map = {
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel', 'الاسم', 'Hotel Name', 'name']),
            'Rate': find_column(df, ['Rate', 'rating', 'التقييم', 'Rating', 'score']),
            'Star': find_column(df, ['Star', 'stars', 'النجوم', 'Stars', 'star']),
            'P1': find_column(df, ['Price1', 'price1', 'سعر 1', 'Price 1', 'p1']),
            'P2': find_column(df, ['price2', 'Price2', 'سعر 2', 'Price 2', 'p2']),
            'P3': find_column(df, ['price3', 'Price3', 'سعر 3', 'Price 3', 'p3']),
            'Place1': find_column(df, ['Place1', 'place1', 'منصة 1', 'Booking 1', 'platform 1']),
            'Place2': find_column(df, ['Place2', 'place2', 'منصة 2', 'Booking 2', 'platform 2']),
            'Place3': find_column(df, ['place3', 'Place3', 'منصة 3', 'Booking 3', 'platform 3']),
            'Arrival': find_column(df, ['date of arrival', 'date_of_arrival', 'تاريخ الوصول', 'arrival', 'Arrival Date', 'checkin']),
            'Booking': find_column(df, ['day of book', 'day_of_book', 'تاريخ الحجز', 'booking', 'Booking Date', 'booked_at']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة', 'Distance', 'dist']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف', 'Description', 'features']),
            'Location': find_column(df, ['location', 'area', 'المنطقة', 'Location', 'neighborhood'])
        }
        
        # Ensure critical columns exist as dummy if missing to prevent KeyError
        for key in col_map:
            if col_map[key] is None:
                dummy_name = f"dummy_{key}"
                df[dummy_name] = np.nan
                col_map[key] = dummy_name

        # Numeric Conversions
        for p in ['P1', 'P2', 'P3']:
            df[col_map[p]] = pd.to_numeric(df[col_map[p]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        
        # Date Parsing
        df['arrival_dt'] = pd.to_datetime(df[col_map['Arrival']], errors='coerce')
        df['booking_dt'] = pd.to_datetime(df[col_map['Booking']], errors='coerce')
        
        df['Month'] = df['arrival_dt'].dt.strftime('%B')
        df['Day'] = df['arrival_dt'].dt.strftime('%A')
        df['days_before'] = (df['arrival_dt'] - df['booking_dt']).dt.days
        
        return df, col_map, None
    except Exception as e: return None, None, str(e)

def get_booking_company(row, col_map):
    for p_col in ['Place1', 'Place2', 'Place3']:
        val = row[col_map[p_col]]
        if pd.notnull(val) and str(val).strip() != "":
            return str(val)
    return "N/A"

def generate_fun_facts(df, col_map, city, lang="Arabic"):
    facts = []
    if df.empty or 'Best_Price' not in df.columns: return ["لا توجد بيانات كافية"]
    
    h_col = col_map['Hotel']
    
    try:
        # 1-5: Extremes & Averages
        cheapest = df.loc[df['Best_Price'].idxmin()]
        expensive = df.loc[df['Best_Price'].idxmax()]
        facts.append(f"💰 أرخص فندق: **{cheapest[h_col]}** بـ ${cheapest['Best_Price']:.0f}." if lang=="Arabic" else f"💰 Cheapest: **{cheapest[h_col]}** at ${cheapest['Best_Price']:.0f}.")
        facts.append(f"💎 أغلى فندق: **{expensive[h_col]}** بـ ${expensive['Best_Price']:.0f}." if lang=="Arabic" else f"💎 Most expensive: **{expensive[h_col]}** at ${expensive['Best_Price']:.0f}.")
        facts.append(f"📈 متوسط الأسعار في {city} هو ${df['Best_Price'].mean():.0f}." if lang=="Arabic" else f"📈 Avg price in {city} is ${df['Best_Price'].mean():.0f}.")
        
        top_rated = df.loc[df['Rate'].idxmax()]
        facts.append(f"🌟 الأعلى تقييماً: **{top_rated[h_col]}** ({top_rated['Rate']}/10)." if lang=="Arabic" else f"🌟 Top rated: **{top_rated[h_col]}** ({top_rated['Rate']}/10).")
        facts.append(f"↔️ فجوة السعر: ${df['Best_Price'].max() - df['Best_Price'].min():.0f}." if lang=="Arabic" else f"↔️ Price gap: ${df['Best_Price'].max() - df['Best_Price'].min():.0f}.")
        
        # 6-10: Value & Stars
        df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        if not df['Value'].dropna().empty:
            best_v = df.loc[df['Value'].idxmax()]
            facts.append(f"🎯 أفضل قيمة: **{best_v[h_col]}** (جودة عالية وسعر ذكي)." if lang=="Arabic" else f"🎯 Best value: **{best_v[h_col]}** (High quality, smart price).")
        
        for s in [5, 4, 3]:
            s_df = df[df['Star'] == s]
            if not s_df.empty:
                facts.append(f"⭐ متوسط سعر فنادق {s} نجوم: ${s_df['Best_Price'].mean():.0f}." if lang=="Arabic" else f"⭐ Avg {s}-star price: ${s_df['Best_Price'].mean():.0f}.")
        
        # 11-15: Booking & Arrival
        if not df['days_before'].dropna().empty:
            best_w = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 نصيحة: الحجز قبل {int(best_w)} يوم يوفر لك أقصى مبلغ." if lang=="Arabic" else f"📅 Tip: Booking {int(best_w)} days ahead is cheapest.")
            
        if 'Day' in df.columns and not df['Day'].dropna().empty:
            cheapest_day = df.groupby('Day')['Best_Price'].mean().idxmin()
            facts.append(f"🗓️ الوصول يوم **{cheapest_day}** هو الأرخص غالباً." if lang=="Arabic" else f"🗓️ Arriving on **{cheapest_day}** is usually cheapest.")
            
        if not df['arrival_dt'].dropna().empty:
            unique_d = df['arrival_dt'].nunique()
            facts.append(f"📆 تم تحليل {unique_d} تاريخ وصول مختلف." if lang=="Arabic" else f"📆 Analyzed {unique_d} different arrival dates.")
            
        # 16-20: Location & Competition
        if not df[col_map['Location']].dropna().empty:
            top_l = df[col_map['Location']].value_counts().idxmax()
            facts.append(f"📍 منطقة **{top_l}** هي الأكثر كثافة فندقية." if lang=="Arabic" else f"📍 **{top_l}** is the densest area for hotels.")
            
        if not df[col_map['Place1']].dropna().empty:
            top_p = df[col_map['Place1']].value_counts().idxmax()
            facts.append(f"🌐 منصة **{top_p}** تهيمن على عروض {city}." if lang=="Arabic" else f"🌐 Platform **{top_p}** dominates {city} offers.")
            
        facts.append(f"📊 إجمالي العروض المحللة: {len(df)}." if lang=="Arabic" else f"📊 Total offers analyzed: {len(df)}.")
        facts.append(f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} فندق تحت متوسط السعر." if lang=="Arabic" else f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} hotels are below average price.")
        facts.append(f"✨ {len(df[df['Star'] == 5])} فندق 5 نجوم متاح حالياً." if lang=="Arabic" else f"✨ {len(df[df['Star'] == 5])} five-star hotels available.")

    except Exception as e: facts.append(f"Note: {str(e)}")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V18")
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
        valid_days = df.dropna(subset=['Day'])
        if not valid_days.empty:
            st.plotly_chart(px.bar(valid_days.groupby('Day')['Best_Price'].mean().sort_values(), title="Price by Day"), use_container_width=True)
        
        st.markdown("#### 🎯 Optimal Booking Window")
        valid_bw = df.dropna(subset=['days_before'])
        if not valid_bw.empty:
            st.plotly_chart(px.line(valid_bw.groupby('days_before')['Best_Price'].mean().reset_index(), x='days_before', y='Best_Price', title="Best Time to Book"), use_container_width=True)
        else: st.info("Booking dates missing in this file.")

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
        
        valid_dates = df['arrival_dt'].dropna().unique()
        if len(valid_dates) > 1:
            selected_date = st.select_slider("Data Snapshot", options=sorted(valid_dates), format_func=lambda x: x.strftime('%Y-%m-%d'))
            sub_df = df[df['arrival_dt'] <= selected_date]
        else: sub_df = df

        facts = generate_fun_facts(sub_df, col_map, city, lang)
        cols = st.columns(2)
        for i, fact in enumerate(facts): cols[i % 2].success(fact)

    elif selected_page == "🔍 Professional Tracker":
        st.markdown("### 🔍 Professional Market Tracker")
        valid_arr = df.dropna(subset=['arrival_dt'])
        if not valid_arr.empty:
            st.plotly_chart(px.line(valid_arr.groupby('arrival_dt')['Best_Price'].agg(['mean', 'min']).reset_index(), x='arrival_dt', y=['mean', 'min'], title="Market Trend"), use_container_width=True)
            
            hotel_opts = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']} | 📍{r[col_map['Location']]}", axis=1).unique()
            sel = st.selectbox("Track Hotel", hotel_opts)
            h_name = sel.split(" | ")[0]
            h_df = df[df[col_map['Hotel']] == h_name].dropna(subset=['arrival_dt']).sort_values('arrival_dt')
            if not h_df.empty:
                st.line_chart(h_df.set_index('arrival_dt')['Best_Price'])
        else: st.info("Arrival dates missing for tracking.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location")
        valid_locs = df[col_map['Location']].dropna().unique()
        if len(valid_locs) > 0:
            loc = st.selectbox("Select Area", valid_locs)
            loc_df = df[df[col_map['Location']] == loc].copy()
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            
            cols = [col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['Arrival'], col_map['Desc']]
            st.dataframe(loc_df[cols].sort_values('Best_Price'), hide_index=True)
        else: st.info("Location data missing.")

    elif selected_page == "⚔️ Competitor Analysis":
        st.markdown("### ⚔️ Competitor Intelligence")
        hotel_list = df[col_map['Hotel']].dropna().unique()
        if len(hotel_list) > 0:
            hotel = st.selectbox("Select Hotel", hotel_list)
            target = df[df[col_map['Hotel']] == hotel].iloc[0]
            with st.container(border=True):
                st.subheader(f"🏨 {hotel} | ${target['Best_Price']:.0f}")
                st.write(f"⭐ {target['Star']} Stars | 📍 {target[col_map['Location']]}")
                st.info(f"**Description:** {target[col_map['Desc']]}")
            
            comps = df[df[col_map['Hotel']] != hotel].copy()
            if pd.notnull(target[col_map['Location']]):
                comps = comps[comps[col_map['Location']] == target[col_map['Location']]]
            
            comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate', 'Star', col_map['Arrival']]].sort_values('Best_Price'), hide_index=True)
        else: st.info("No hotel names found.")

    elif selected_page == "🌍 City Compare":
        st.markdown("### 🌍 City Price Comparison")
        comp_data = []
        for c, info in CITIES_DATA.items():
            t_df, _, _ = load_data(info['file'])
            if t_df is not None:
                comp_data.append({"City": c, "Avg": t_df['Best_Price'].mean(), "Min": t_df['Best_Price'].min(), "Max": t_df['Best_Price'].max()})
        if comp_data:
            c_df = pd.DataFrame(comp_data)
            st.plotly_chart(px.bar(c_df, x='City', y='Avg', color='City'), use_container_width=True)
            st.table(c_df)

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
            hotel_selector = full.apply(lambda r: f"{r[col_map['Hotel']]} ({r['City']})", axis=1).unique()
            sel = st.multiselect("Select Hotels", hotel_selector)
            if sel:
                names = [s.split(" (")[0] for s in sel]
                st.dataframe(full[full[col_map['Hotel']].isin(names)][['City', col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['Location'], col_map['Arrival'], col_map['Desc']]], hide_index=True)
        else: st.info("No data for comparison.")

if __name__ == "__main__": main()
