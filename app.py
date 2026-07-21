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
    "Paris": {"file": "Paris_updated.xlsx", "emoji": "🗼"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️"}
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V21", page_icon="🏨", layout="wide")

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
        
        # EXACT MAPPING based on user's specific Excel headers
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
            'Arrival': find_column(df, ['day of arrival', 'date of arrival']),
            'Booking': find_column(df, ['day of book', 'start book', 'date of creat booking']),
            'Dist': find_column(df, ['Distance From places', 'distance']),
            'Desc': find_column(df, ['Desc', 'description']),
            'Desc2': find_column(df, ['Desc2']),
            'Location': find_column(df, ['location', 'area'])
        }
        
        # Fallback for missing columns to avoid KeyError
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
        
        # Robust Date Parsing for User's specific format (e.g., '6-Jun', 'Friday')
        df['arrival_dt'] = pd.to_datetime(df[col_map['Arrival']], errors='coerce')
        df['booking_dt'] = pd.to_datetime(df[col_map['Booking']], errors='coerce')
        
        # If standard parsing fails, we use the raw values for labels
        df['arrival_label'] = df[col_map['Arrival']].astype(str)
        df['booking_label'] = df[col_map['Booking']].astype(str)
        
        # Days Before calculation (only works if dates are valid)
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
        # 1-20 Dynamic Facts Engine
        cheapest = df.loc[df['Best_Price'].idxmin()]
        expensive = df.loc[df['Best_Price'].idxmax()]
        facts.append(f"💰 أرخص فندق: **{cheapest[h_col]}** بـ ${cheapest['Best_Price']:.0f}." if lang=="Arabic" else f"💰 Cheapest: **{cheapest[h_col]}** at ${cheapest['Best_Price']:.0f}.")
        facts.append(f"💎 أغلى فندق: **{expensive[h_col]}** بـ ${expensive['Best_Price']:.0f}." if lang=="Arabic" else f"💎 Most expensive: **{expensive[h_col]}** at ${expensive['Best_Price']:.0f}.")
        
        top_rated = df.loc[df['Rate'].idxmax()]
        facts.append(f"🌟 الأعلى تقييماً: **{top_rated[h_col]}** ({top_rated['Rate']}/10)." if lang=="Arabic" else f"🌟 Top rated: **{top_rated[h_col]}** ({top_rated['Rate']}/10).")
        
        df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        if not df['Value'].dropna().empty:
            best_v = df.loc[df['Value'].idxmax()]
            facts.append(f"🎯 أفضل قيمة: **{best_v[h_col]}** (جودة ممتازة وسعر ذكي)." if lang=="Arabic" else f"🎯 Best value: **{best_v[h_col]}** (High quality, smart price).")
        
        facts.append(f"📈 متوسط الأسعار في {city} هو ${df['Best_Price'].mean():.0f}." if lang=="Arabic" else f"📈 Avg price in {city} is ${df['Best_Price'].mean():.0f}.")
        facts.append(f"↔️ فجوة السعر في السوق: ${df['Best_Price'].max() - df['Best_Price'].min():.0f}." if lang=="Arabic" else f"↔️ Price gap: ${df['Best_Price'].max() - df['Best_Price'].min():.0f}.")
        
        for s in [5, 4, 3]:
            s_df = df[df['Star'] == s]
            if not s_df.empty:
                facts.append(f"⭐ متوسط سعر فنادق {s} نجوم: ${s_df['Best_Price'].mean():.0f}." if lang=="Arabic" else f"⭐ Avg {s}-star price: ${s_df['Best_Price'].mean():.0f}.")
        
        if not df['days_before'].dropna().empty:
            best_w = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 نصيحة: الحجز قبل {int(best_w)} يوم يوفر لك أقصى مبلغ." if lang=="Arabic" else f"📅 Tip: Booking {int(best_w)} days ahead is cheapest.")
            
        if not df[col_map['Location']].dropna().empty:
            top_l = df[col_map['Location']].value_counts().idxmax()
            facts.append(f"📍 منطقة **{top_l}** هي الأكثر طلباً." if lang=="Arabic" else f"📍 **{top_l}** is the most popular area.")
            
        if not df[col_map['Place1']].dropna().empty:
            top_p = df[col_map['Place1']].value_counts().idxmax()
            facts.append(f"🌐 منصة **{top_p}** تهيمن على العروض حالياً." if lang=="Arabic" else f"🌐 Platform **{top_p}** dominates offers.")
            
        facts.append(f"📊 إجمالي العروض المحللة: {len(df)} عرض." if lang=="Arabic" else f"📊 Total offers analyzed: {len(df)}.")
        facts.append(f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} فندق أسعارهم تحت المتوسط." if lang=="Arabic" else f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} hotels are below average price.")
        facts.append(f"🏆 {len(df[df['Rate'] > 9])} فندق حصلوا على تقييم أسطوري." if lang=="Arabic" else f"🏆 {len(df[df['Rate'] > 9])} hotels have legendary ratings.")
        facts.append(f"✨ تم تحديث البيانات: {datetime.now().strftime('%Y-%m-%d')}.")
        
        if not df[col_map['Dist']].dropna().empty:
            facts.append(f"🚶 تم تحليل المسافات لـ {len(df[df[col_map['Dist']].notnull()])} فندق." if lang=="Arabic" else f"🚶 Distances analyzed for {len(df[df[col_map['Dist']].notnull()])} hotels.")

    except Exception as e: facts.append(f"Note: {str(e)}")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V21")
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
        "guide": "🧭 Traveler Guide", "custom_compare": "🎯 Custom Hotel Compare"
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
        # Try to use Day column or extract from arrival_dt
        if not df['arrival_dt'].dropna().empty:
            df['Day_Name'] = df['arrival_dt'].dt.day_name()
            st.plotly_chart(px.bar(df.groupby('Day_Name')['Best_Price'].mean().sort_values(), title="Price by Day of Arrival"), use_container_width=True)
        
        st.markdown("#### 🎯 Optimal Booking Window")
        valid_bw = df.dropna(subset=['days_before'])
        if not valid_bw.empty:
            st.plotly_chart(px.line(valid_bw.groupby('days_before')['Best_Price'].mean().reset_index(), x='days_before', y='Best_Price', title="Best Time to Book (Days in Advance)"), use_container_width=True)
        else: st.info("⚠️ Booking dates (day of book) missing or not in standard format. Ensure columns 'day of book' and 'day of arrival' are dates.")

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
        
        # Booking Date Filter (توقيت الإحصائيات)
        booking_col = col_map['Booking']
        if not df[booking_col].dropna().empty:
            b_dates = sorted(df[booking_col].dropna().unique())
            sel_b_date = st.select_slider("Select Statistics Timestamp (توقيت الإحصائيات)", options=b_dates)
            sub_df = df[df[booking_col] <= sel_b_date]
        else: sub_df = df

        facts = generate_fun_facts(sub_df, col_map, city, lang)
        cols = st.columns(2)
        for i, fact in enumerate(facts): cols[i % 2].success(fact)

    elif selected_page == "🔍 Professional Tracker":
        st.markdown("### 🔍 Professional Market Tracker")
        if not df['arrival_dt'].dropna().empty:
            st.plotly_chart(px.line(df.groupby('arrival_dt')['Best_Price'].agg(['mean', 'min']).reset_index(), x='arrival_dt', y=['mean', 'min'], title="Market Trend Over Time"), use_container_width=True)
            hotel_opts = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']} | 📍{r[col_map['Location']]}", axis=1).unique()
            sel = st.selectbox("Track Specific Hotel", hotel_opts)
            h_name = sel.split(" | ")[0]
            h_df = df[df[col_map['Hotel']] == h_name].dropna(subset=['arrival_dt']).sort_values('arrival_dt')
            if not h_df.empty: st.line_chart(h_df.set_index('arrival_dt')['Best_Price'])
        else: st.info("⚠️ Arrival dates (day of arrival) missing or not in date format.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location & History")
        valid_locs = df[col_map['Location']].dropna().unique()
        if len(valid_locs) > 0:
            loc = st.selectbox("Select Area", valid_locs)
            loc_df = df[df[col_map['Location']] == loc].copy()
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            loc_df = loc_df.rename(columns={'Best_Price': 'Best Price (Recorded)'})
            
            cols = [col_map['Hotel'], 'Best Price (Recorded)', 'Star', 'Rate', 'Booking Company', col_map['Booking'], col_map['Arrival'], col_map['Desc']]
            st.dataframe(loc_df[cols].sort_values('Best Price (Recorded)'), hide_index=True)
        else: st.info("Location data missing.")

    elif selected_page == "⚔️ Competitor Analysis":
        st.markdown("### ⚔️ Competitor Intelligence")
        hotel_list = df[col_map['Hotel']].dropna().unique()
        if len(hotel_list) > 0:
            hotel = st.selectbox("Select Your Hotel", hotel_list)
            target = df[df[col_map['Hotel']] == hotel].iloc[0]
            
            with st.container(border=True):
                st.subheader(f"🏨 {hotel} | ${target['Best_Price']:.0f}")
                st.write(f"⭐ {target['Star']} Stars | 📍 {target[col_map['Location']]}")
            
            # Filter competitors by same location OR same stars
            comps = df[df[col_map['Hotel']] != hotel].copy()
            if pd.notnull(target[col_map['Location']]) and str(target[col_map['Location']]) != "":
                comps = comps[comps[col_map['Location']] == target[col_map['Location']]]
                st.write(f"Showing competitors in **{target[col_map['Location']]}**:")
            else:
                comps = comps[comps['Star'] == target['Star']]
                st.write(f"Showing competitors with **{target['Star']} Stars**:")
            
            comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate', 'Star', col_map['Arrival']]].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "🧭 Traveler Guide":
        st.markdown("### 🧭 Smart Traveler Guide")
        st.write("Find the best deals based on your preferences.")
        
        pref = st.radio("What are you looking for?", ["Best Value (Rating/Price)", "Top Rated Only", "Cheapest Deals", "Best Views/Description"])
        
        if pref == "Best Value (Rating/Price)":
            df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
            st.dataframe(df.sort_values('Value', ascending=False).head(10)[[col_map['Hotel'], 'Best_Price', 'Rate', col_map['Location'], col_map['Desc']]], hide_index=True)
        elif pref == "Top Rated Only":
            st.dataframe(df.sort_values('Rate', ascending=False).head(10)[[col_map['Hotel'], 'Rate', 'Best_Price', col_map['Location']]], hide_index=True)
        elif pref == "Cheapest Deals":
            st.dataframe(df.sort_values('Best_Price').head(10)[[col_map['Hotel'], 'Best_Price', 'Star', col_map['Location']]], hide_index=True)
        else:
            search = st.text_input("Search in features (e.g., View, Family, Pool)")
            if search:
                res = df[df[col_map['Desc']].str.contains(search, case=False, na=False)]
                st.dataframe(res[[col_map['Hotel'], 'Best_Price', col_map['Desc'], col_map['Location']]], hide_index=True)

    elif selected_page == "🎯 Custom Hotel Compare":
        st.markdown("### 🎯 Custom Comparison (Deduplicated)")
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
