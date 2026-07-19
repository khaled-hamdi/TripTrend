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
    "Paris": {"file": "paris_updated.xlsx", "emoji": "🗼", "country": "France"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️", "country": "UAE"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌", "country": "Turkey"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️", "country": "Egypt"}
}

# ======================================================================================
# --- PAGE CONFIG ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V16", page_icon="🚀", layout="wide")

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
            'Place2': find_column(df, ['Place2', 'place2', 'منصة 2']),
            'Place3': find_column(df, ['place3', 'Place3', 'منصة 3']),
            'Arrival': find_column(df, ['date of arrival', 'date_of_arrival', 'تاريخ الوصول', 'arrival']),
            'Booking': find_column(df, ['day of book', 'day_of_book', 'تاريخ الحجز', 'booking']),
            'Dist': find_column(df, ['Distance From places', 'distance', 'المسافة']),
            'Desc': find_column(df, ['Desc', 'description', 'الوصف']),
            'Location': find_column(df, ['location', 'area', 'المنطقة'])
        }
        
        # Numeric Conversions
        for p in ['P1', 'P2', 'P3']:
            if col_map[p]: df[col_map[p]] = pd.to_numeric(df[col_map[p]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        
        # Flexible Date Handling
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
        # 1. Price Extremes
        cheapest = df.loc[df['Best_Price'].idxmin()]
        expensive = df.loc[df['Best_Price'].idxmax()]
        if lang == "Arabic":
            facts.append(f"💰 أرخص فندق حالياً هو **{cheapest[hotel_col]}** بسعر ${cheapest['Best_Price']:.0f}.")
            facts.append(f"💎 أغلى فندق متاح هو **{expensive[hotel_col]}** بسعر ${expensive['Best_Price']:.0f}.")
        else:
            facts.append(f"💰 Cheapest hotel: **{cheapest[hotel_col]}** at ${cheapest['Best_Price']:.0f}.")
            facts.append(f"💎 Most expensive: **{expensive[hotel_col]}** at ${expensive['Best_Price']:.0f}.")
        
        # 2. Ratings
        top_rated = df.loc[df['Rate'].idxmax()]
        if lang == "Arabic":
            facts.append(f"🌟 الفندق الأعلى تقييماً هو **{top_rated[hotel_col]}** بتقييم {top_rated['Rate']}/10.")
            facts.append(f"📈 متوسط تقييمات الفنادق في {city} هو {df['Rate'].mean():.1f}/10.")
        else:
            facts.append(f"🌟 Top rated: **{top_rated[hotel_col]}** with {top_rated['Rate']}/10.")
            facts.append(f"📈 Average rating in {city} is {df['Rate'].mean():.1f}/10.")
        
        # 3. Value for Money
        df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        if not df['Value'].dropna().empty:
            best_value = df.loc[df['Value'].idxmax()]
            if lang == "Arabic":
                facts.append(f"🎯 أفضل قيمة مقابل سعر: **{best_value[hotel_col]}** (تقييم عالٍ بسعر ممتاز).")
            else:
                facts.append(f"🎯 Best value: **{best_value[hotel_col]}** (High rating, great price).")
        
        # 4. Market Gaps
        gap = df['Best_Price'].max() - df['Best_Price'].min()
        if lang == "Arabic":
            facts.append(f"↔️ فجوة السعر في السوق تصل إلى ${gap:.0f} بين الأرخص والأغلى.")
        else:
            facts.append(f"↔️ Price gap is ${gap:.0f} between min and max.")
            
        # 5. Booking Window
        if 'days_before' in df.columns and not df['days_before'].dropna().empty:
            best_window = df.groupby('days_before')['Best_Price'].mean().idxmin()
            if lang == "Arabic":
                facts.append(f"📅 نصيحة: الحجز قبل {int(best_window)} يوم يوفر لك أكبر قدر من المال.")
            else:
                facts.append(f"📅 Tip: Booking {int(best_window)} days ahead saves the most money.")
            
        # 6. Competition Platform
        if col_map['Place1'] and not df[col_map['Place1']].dropna().empty:
            top_platform = df[col_map['Place1']].value_counts().idxmax()
            if lang == "Arabic":
                facts.append(f"🌐 منصة **{top_platform}** تقدم أكبر عدد من العروض حالياً.")
            else:
                facts.append(f"🌐 Platform **{top_platform}** has the most offers currently.")

        # More dynamic facts...
        if lang == "Arabic":
            facts.append(f"🏨 إجمالي الفنادق المحللة في {city}: {len(df)} فندق.")
            facts.append(f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} فندق أسعارهم أقل من المتوسط.")
            facts.append(f"✨ {len(df[df['Star'] == 5])} فندق من فئة 5 نجوم تتنافس في {city}.")
            facts.append(f"🔔 تم التحديث: {datetime.now().strftime('%Y-%m-%d')}.")
        else:
            facts.append(f"🏨 Total hotels analyzed in {city}: {len(df)}.")
            facts.append(f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} hotels are below average price.")
            facts.append(f"✨ {len(df[df['Star'] == 5])} five-star hotels are competing in {city}.")
            facts.append(f"🔔 Updated: {datetime.now().strftime('%Y-%m-%d')}.")
            
    except Exception as e:
        facts.append(f"Error: {str(e)}")
    
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V16")
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

    st.sidebar.title(f"🚀 {st.session_state.username}")
    city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
    df, col_map, err = load_data(CITIES_DATA[city]['file'])
    
    if err:
        st.warning(f"⚠️ {err}")
        # Allow navigation to City Compare even if current city file fails
        if st.sidebar.radio("Select Page", ["🌍 City Compare", "🎯 Custom Hotel Compare"]) == "🌍 City Compare":
            selected_page = "🌍 City Compare"
        else: return

    page_map = {
        "dashboard": "📊 Dashboard",
        "trends": "📈 Trends",
        "rankings": "🏆 Rankings",
        "tracker": "🔍 Professional Tracker",
        "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location",
        "competitor": "⚔️ Competitor Analysis",
        "compare": "🌍 City Compare",
        "custom_compare": "🎯 Custom Hotel Compare"
    }
    
    if "all" in st.session_state.allowed_pages:
        available_pages = list(page_map.values())
    else:
        allowed_p = list(st.session_state.allowed_pages)
        available_pages = [page_map[p] for p in allowed_p if p in page_map]

    selected_page = st.sidebar.radio("Select Page", available_pages)

    # --- PAGES ---
    if selected_page == "📊 Dashboard":
        st.markdown(f"### 📊 {city} Market Insights")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Price Gap", f"${df['Best_Price'].max() - df['Best_Price'].min():.0f}")
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution", color_discrete_sequence=['#667eea']), use_container_width=True)

    elif selected_page == "📈 Trends":
        st.markdown("### 📅 Best Arrival Days & Booking Analysis")
        # Handle missing data gracefully
        valid_days = df.dropna(subset=['Day']) if 'Day' in df.columns else pd.DataFrame()
        if not valid_days.empty:
            day_avg = valid_days.groupby('Day')['Best_Price'].mean().sort_values()
            st.plotly_chart(px.bar(x=day_avg.index, y=day_avg.values, title="Average Price by Day of Week"), use_container_width=True)
        
        st.markdown("#### 🎯 Optimal Booking Window")
        if 'days_before' in df.columns:
            df_valid = df.dropna(subset=['days_before'])
            if not df_valid.empty:
                window_avg = df_valid.groupby('days_before')['Best_Price'].mean().reset_index()
                st.plotly_chart(px.line(window_avg, x='days_before', y='Best_Price', title="Best Time to Book"), use_container_width=True)
            else: st.info("Not enough booking date data to show trends.")
        else: st.info("Booking dates missing in this file.")

    elif selected_page == "🎉 Fun Facts":
        st.markdown("### 🎉 Fun Facts & Viral Insights")
        lang = st.radio("Select Language | اختر اللغة", ["Arabic", "English"], horizontal=True)
        
        if col_map['Arrival'] and not df['arrival_dt'].dropna().empty:
            dates = sorted(df['arrival_dt'].dropna().unique())
            selected_date = st.select_slider("Data Snapshot", options=dates, format_func=lambda x: x.strftime('%Y-%m-%d'))
            sub_df = df[df['arrival_dt'] <= selected_date]
        else: sub_df = df

        facts = generate_fun_facts(sub_df, col_map, city, lang)
        cols = st.columns(2)
        for i, fact in enumerate(facts):
            cols[i % 2].success(fact)

    elif selected_page == "🔍 Professional Tracker":
        st.markdown("### 🔍 Professional Market Tracker")
        if col_map['Arrival'] and not df['arrival_dt'].dropna().empty:
            trend_df = df.groupby('arrival_dt')['Best_Price'].agg(['mean', 'min', 'max']).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend_df['arrival_dt'], y=trend_df['mean'], name='Average'))
            fig.add_trace(go.Scatter(x=trend_df['arrival_dt'], y=trend_df['min'], name='Min', line=dict(dash='dash')))
            st.plotly_chart(fig, use_container_width=True)
            
            hotel_options = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']} | 📍{r[col_map['Location']] if col_map['Location'] else 'N/A'}", axis=1).unique()
            selected_option = st.selectbox("Track Specific Hotel", hotel_options)
            hotel_name = selected_option.split(" | ")[0]
            h_df = df[df[col_map['Hotel']] == hotel_name].sort_values('arrival_dt')
            st.line_chart(h_df.set_index('arrival_dt')['Best_Price'])
        else: st.info("Arrival dates are required for tracking. Please check your data.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location")
        if col_map['Location'] and df[col_map['Location']].notnull().any():
            loc = st.selectbox("Select Area", df[col_map['Location']].dropna().unique())
            loc_df = df[df[col_map['Location']] == loc].copy()
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            
            cols = [col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company']
            if col_map['Arrival']: cols.append(col_map['Arrival'])
            if col_map['Desc']: cols.append(col_map['Desc'])
            st.dataframe(loc_df[cols].sort_values(['Best_Price']), hide_index=True)

    elif selected_page == "⚔️ Competitor Analysis":
        st.markdown("### ⚔️ Competitor Intelligence")
        hotel = st.selectbox("Select Your Hotel", df[col_map['Hotel']].unique())
        target_row = df[df[col_map['Hotel']] == hotel].iloc[0]
        
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            c1.metric("Price", f"${target_row['Best_Price']:.0f}")
            c1.write(f"⭐ {target_row['Star']} | 📍 {target_row[col_map['Location']]}")
            c2.info(f"**Description:** {target_row[col_map['Desc']] if col_map['Desc'] else 'N/A'}")

        comps = df[(df[col_map['Hotel']] != hotel)]
        if col_map['Location'] and target_row[col_map['Location']]:
            comps = comps[comps[col_map['Location']] == target_row[col_map['Location']]]
        
        comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
        comps['Price_Diff'] = comps['Best_Price'] - target_row['Best_Price']
        
        st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Price_Diff', 'Booking Company', 'Rate', 'Star']], hide_index=True)

    elif selected_page == "🌍 City Compare":
        st.markdown("### 🌍 City Price Comparison")
        comp_data = []
        for c_name, c_info in CITIES_DATA.items():
            t_df, _, _ = load_data(c_info['file'])
            if t_df is not None:
                comp_data.append({"City": c_name, "Avg": t_df['Best_Price'].mean(), "Min": t_df['Best_Price'].min(), "Max": t_df['Best_Price'].max()})
        if comp_data:
            c_df = pd.DataFrame(comp_data)
            st.plotly_chart(px.bar(c_df, x='City', y='Avg', color='City'), use_container_width=True)
            st.table(c_df)

    elif selected_page == "🎯 Custom Hotel Compare":
        st.markdown("### 🎯 Custom Hotel Comparison")
        st.write("Compare specific hotels across different cities and see all their features.")
        
        all_hotels = []
        for c_name, c_info in CITIES_DATA.items():
            t_df, t_map, _ = load_data(c_info['file'])
            if t_df is not None:
                t_df['City'] = c_name
                t_df['Booking Company'] = t_df.apply(lambda r: get_booking_company(r, t_map), axis=1)
                # Keep only necessary columns for the selector
                all_hotels.append(t_df)
        
        if all_hotels:
            full_df = pd.concat(all_hotels, ignore_index=True)
            hotel_selector = full_df.apply(lambda r: f"{r[col_map['Hotel']]} ({r['City']}) | ${r['Best_Price']:.0f}", axis=1).unique()
            selected_hotels = st.multiselect("Choose hotels to compare", hotel_selector)
            
            if selected_hotels:
                selected_names = [s.split(" (")[0] for s in selected_hotels]
                compare_df = full_df[full_df[col_map['Hotel']].isin(selected_names)]
                
                display_cols = ['City', col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company']
                if col_map['Location']: display_cols.append(col_map['Location'])
                if col_map['Arrival']: display_cols.append(col_map['Arrival'])
                if col_map['Desc']: display_cols.append(col_map['Desc'])
                if col_map['Dist']: display_cols.append(col_map['Dist'])
                
                st.dataframe(compare_df[display_cols], hide_index=True)
        else: st.info("No hotel data available for comparison.")

if __name__ == "__main__": main()
