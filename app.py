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
    "blogger_pro": {"password": "blogger2024", "created_at": "2026-07-11", "role": "blogger", "pages": ["dashboard", "trends", "fun_facts", "rankings"]},
}

CITIES_DATA = {
    "Paris": {"file": "Paris_updated", "emoji": "🗼"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️"}
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V19", page_icon="🚀", layout="wide")

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
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel', 'الاسم', 'Hotel Name', 'name']),
            'Rate': find_column(df, ['Rate', 'rating', 'التقييم', 'Rating', 'score']),
            'Star': find_column(df, ['Star', 'stars', 'النجوم', 'Stars', 'star']),
            'P1': find_column(df, ['Price1', 'price1', 'سعر 1', 'Price 1', 'p1']),
            'P2': find_column(df, ['price2', 'Price2', 'سعر 2', 'Price 2', 'p2']),
            'P3': find_column(df, ['price3', 'Price3', 'سعر 3', 'Price 3', 'p3']),
            'Place1': find_column(df, ['Place1', 'place1', 'منصة 1', 'Booking 1', 'platform 1']),
            'Place2': find_column(df, ['Place2', 'place2', 'منصة 2', 'Booking 2', 'platform 2']),
            'Place3': find_column(df, ['place3', 'Place3', 'منصة 3', 'Booking 3', 'platform 3']),
            'Arrival': find_column(df, ['date of arrival', 'date_of_arrival', 'تاريخ الوصول', 'arrival', 'Arrival Date', 'checkin', 'arrival_date']),
            'Booking': find_column(df, ['day of book', 'day_of_book', 'تاريخ الحجز', 'booking', 'Booking Date', 'booked_at', 'booking_date']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة', 'Distance', 'dist']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف', 'Description', 'features']),
            'Location': find_column(df, ['location', 'area', 'المنطقة', 'Location', 'neighborhood'])
        }
        
        # Diagnostics: Show user what columns are missing
        missing = [k for k, v in col_map.items() if v is None]
        if missing:
            with st.expander("🔍 Column Diagnostics (Important for Excel Formatting)"):
                st.write("The app couldn't find these columns. Please name them correctly in Excel:")
                st.write(f"Missing: {missing}")
                st.write(f"Available in your file: {list(df.columns)}")

        # Ensure critical columns exist to prevent crash
        for key in col_map:
            if col_map[key] is None:
                dummy = f"dummy_{key}"
                df[dummy] = np.nan
                col_map[key] = dummy

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
        if pd.notnull(val) and str(val).strip() != "": return str(val)
    return "N/A"

def generate_fun_facts(df, col_map, city, lang="Arabic"):
    facts = []
    if df.empty: return ["No data"]
    h_col = col_map['Hotel']
    try:
        cheapest = df.loc[df['Best_Price'].idxmin()]
        expensive = df.loc[df['Best_Price'].idxmax()]
        facts.append(f"💰 الأرخص: **{cheapest[h_col]}** بـ ${cheapest['Best_Price']:.0f}." if lang=="Arabic" else f"💰 Cheapest: **{cheapest[h_col]}** at ${cheapest['Best_Price']:.0f}.")
        facts.append(f"💎 الأغلى: **{expensive[h_col]}** بـ ${expensive['Best_Price']:.0f}." if lang=="Arabic" else f"💎 Most expensive: **{expensive[h_col]}** at ${expensive['Best_Price']:.0f}.")
        
        top_rated = df.loc[df['Rate'].idxmax()]
        facts.append(f"🌟 الأعلى تقييماً: **{top_rated[h_col]}** ({top_rated['Rate']}/10)." if lang=="Arabic" else f"🌟 Top rated: **{top_rated[h_col]}** ({top_rated['Rate']}/10).")
        
        if not df['days_before'].dropna().empty:
            best_w = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 نصيحة: الحجز قبل {int(best_w)} يوم هو الأفضل سعراً." if lang=="Arabic" else f"📅 Tip: Booking {int(best_w)} days ahead is cheapest.")
        
        facts.append(f"📊 تم تحليل {len(df)} عرض في {city}." if lang=="Arabic" else f"📊 {len(df)} offers analyzed in {city}.")
        facts.append(f"📉 متوسط سعر السوق: ${df['Best_Price'].mean():.0f}." if lang=="Arabic" else f"📉 Market avg: ${df['Best_Price'].mean():.0f}.")
        
        # Platform info
        if col_map['Place1']:
            top_p = df[col_map['Place1']].value_counts().idxmax()
            facts.append(f"🌐 منصة **{top_p}** الأكثر عرضاً حالياً." if lang=="Arabic" else f"🌐 Platform **{top_p}** has most offers.")

        # 10 more dynamic facts...
        facts.append(f"🏆 {len(df[df['Star'] == 5])} فندق 5 نجوم تتنافس." if lang=="Arabic" else f"🏆 {len(df[df['Star'] == 5])} 5-star hotels competing.")
        facts.append(f"📍 {df[col_map['Location']].nunique()} منطقة مختلفة مغطاة." if lang=="Arabic" else f"📍 {df[col_map['Location']].nunique()} areas covered.")
        facts.append(f"✨ تم تحديث البيانات: {datetime.now().strftime('%Y-%m-%d')}.")
    except Exception as e: facts.append(f"Note: {str(e)}")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V19")
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
        else:
            st.info("⚠️ Booking dates missing. Ensure you have a 'Booking Date' column in Excel.")

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
        
        # Add Booking Date Filter
        if not df['booking_dt'].dropna().empty:
            b_dates = sorted(df['booking_dt'].dropna().unique())
            sel_b_date = st.select_slider("Select Booking Snapshot (Filter by Time of Data Collection)", options=b_dates, format_func=lambda x: x.strftime('%Y-%m-%d'))
            sub_df = df[df['booking_dt'] <= sel_b_date]
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
            if not h_df.empty: st.line_chart(h_df.set_index('arrival_dt')['Best_Price'])
        else: st.info("⚠️ Arrival dates missing. Ensure you have an 'Arrival Date' column in Excel.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location")
        valid_locs = df[col_map['Location']].dropna().unique()
        if len(valid_locs) > 0:
            loc = st.selectbox("Select Area", valid_locs)
            loc_df = df[df[col_map['Location']] == loc].copy()
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(loc_df[[col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['Arrival'], col_map['Desc']]].sort_values('Best_Price'), hide_index=True)

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
            if pd.notnull(target[col_map['Location']]): comps = comps[comps[col_map['Location']] == target[col_map['Location']]]
            comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate', 'Star', col_map['Arrival']]].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "🎯 Custom Hotel Compare":
        st.markdown("### 🎯 Custom Comparison (Deduplicated)")
        st.write("Each hotel appears once with its Best Price (all time) and Last Price (most recent booking).")
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
                sub = full[full[col_map['Hotel']].isin(names)].copy()
                
                # Logic to get Best vs Last Price
                results = []
                for name in names:
                    h_data = sub[sub[col_map['Hotel']] == name]
                    if not h_data.empty:
                        best_p = h_data['Best_Price'].min()
                        # Get last price based on booking date
                        if not h_data['booking_dt'].dropna().empty:
                            last_row = h_data.sort_values('booking_dt', ascending=False).iloc[0]
                        else:
                            last_row = h_data.iloc[-1]
                        
                        results.append({
                            "City": last_row['City'],
                            "Hotel": name,
                            "Best Price ($)": best_p,
                            "Last Price ($)": last_row['Best_Price'],
                            "Last Booking Date": last_row['booking_dt'].strftime('%Y-%m-%d') if pd.notnull(last_row['booking_dt']) else "N/A",
                            "Stars": last_row['Star'],
                            "Rate": last_row['Rate'],
                            "Booking Co": last_row['Booking Company'],
                            "Location": last_row[col_map['Location']],
                            "Description": last_row[col_map['Desc']]
                        })
                
                st.dataframe(pd.DataFrame(results), hide_index=True)

if __name__ == "__main__": main()
