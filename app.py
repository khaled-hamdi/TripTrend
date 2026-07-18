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
st.set_page_config(page_title="Hotel Analytics Pro V15", page_icon="🚀", layout="wide")

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
        
        for p in ['P1', 'P2', 'P3']:
            if col_map[p]: df[col_map[p]] = pd.to_numeric(df[col_map[p]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        
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

def generate_fun_facts(df, col_map, city):
    facts = []
    if df.empty: return ["لا توجد بيانات كافية حالياً."]
    
    hotel_col = col_map['Hotel']
    
    try:
        # 1. Price Extremes
        if not df['Best_Price'].empty:
            cheapest = df.loc[df['Best_Price'].idxmin()]
            expensive = df.loc[df['Best_Price'].idxmax()]
            facts.append(f"💰 أرخص فندق حالياً هو **{cheapest[hotel_col]}** بسعر ${cheapest['Best_Price']:.0f}.")
            facts.append(f"💎 أغلى فندق متاح هو **{expensive[hotel_col]}** بسعر ${expensive['Best_Price']:.0f}.")
        
        # 2. Ratings
        if not df['Rate'].empty:
            top_rated = df.loc[df['Rate'].idxmax()]
            facts.append(f"🌟 الفندق الأعلى تقييماً هو **{top_rated[hotel_col]}** بتقييم {top_rated['Rate']}/10.")
            facts.append(f"📈 متوسط تقييمات الفنادق في {city} هو {df['Rate'].mean():.1f}/10.")
        
        # 3. Value for Money
        df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        if not df['Value'].dropna().empty:
            best_value = df.loc[df['Value'].idxmax()]
            facts.append(f"🎯 أفضل قيمة مقابل سعر: **{best_value[hotel_col]}** (تقييم عالٍ بسعر ممتاز).")
        
        # 4. Market Gaps
        if len(df['Best_Price']) > 1:
            gap = df['Best_Price'].max() - df['Best_Price'].min()
            facts.append(f"↔️ فجوة السعر في السوق تصل إلى ${gap:.0f} بين الأرخص والأغلى.")
        
        # 5. Star Analysis
        for s in [5, 4, 3]:
            star_df = df[df['Star'] == s]
            if not star_df.empty:
                facts.append(f"⭐ متوسط سعر فنادق {s} نجوم هو ${star_df['Best_Price'].mean():.0f}.")
                
        # 6. Booking Window
        if 'days_before' in df.columns and not df['days_before'].dropna().empty:
            best_window = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 نصيحة: الحجز قبل {int(best_window)} يوم يوفر لك أكبر قدر من المال.")
            
        # 7. Location Density
        if col_map['Location'] and not df[col_map['Location']].dropna().empty:
            top_loc = df[col_map['Location']].value_counts().idxmax()
            facts.append(f"📍 منطقة **{top_loc}** هي الأكثر كثافة فندقية في {city}.")
            
        # 8. Competition
        if col_map['Place1'] and not df[col_map['Place1']].dropna().empty:
            top_platform = df[col_map['Place1']].value_counts().idxmax()
            facts.append(f"🌐 منصة **{top_platform}** تقدم أكبر عدد من العروض حالياً.")
            
        # 9. Arrival Days
        if 'Day' in df.columns and not df['Day'].dropna().empty:
            cheapest_day = df.groupby('Day')['Best_Price'].mean().idxmin()
            facts.append(f"🗓️ الوصول يوم **{cheapest_day}** غالباً ما يكون الأرخص سعراً.")
            
        # 10. Discount Potential
        price_cols = [col_map['P1'], col_map['P2'], col_map['P3']]
        valid_p_cols = [c for c in price_cols if c and c in df.columns]
        if valid_p_cols:
            df['Price_Range'] = df[valid_p_cols].max(axis=1) - df['Best_Price']
            if not df['Price_Range'].empty:
                max_diff = df.loc[df['Price_Range'].idxmax()]
                facts.append(f"💸 فندق **{max_diff[hotel_col]}** لديه أكبر تفاوت في الأسعار بين المنصات (${df['Price_Range'].max():.0f}).")

        # 11-20: Dynamic stats
        facts.append(f"🏨 إجمالي الفنادق المحللة في {city}: {len(df)} فندق.")
        facts.append(f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} فندق أسعارهم أقل من المتوسط.")
        facts.append(f"🏆 {len(df[df['Rate'] > 8])} فندق حصلوا على تقييم 'ممتاز' (أعلى من 8).")
        
        if col_map['Dist']:
            df['dist_num'] = pd.to_numeric(df[col_map['Dist']].astype(str).str.extract(r'(\d+)')[0], errors='coerce')
            if not df['dist_num'].dropna().empty:
                closest = df.loc[df['dist_num'].idxmin()]
                facts.append(f"🚶 **{closest[hotel_col]}** هو الأقرب للمعالم السياحية ({closest[col_map['Dist']]}).")
            
        if df['Best_Price'].mean() > 0:
            facts.append(f"📊 {city} تمتلك تنوعاً سعرياً بنسبة { (df['Best_Price'].std() / df['Best_Price'].mean() * 100):.1f}%.")
        facts.append(f"✨ {len(df[df['Star'] == 5])} فندق من فئة 5 نجوم تتنافس على جذب السياح.")
        facts.append(f"🔔 تم تحديث هذه الإحصائيات بتاريخ {datetime.now().strftime('%Y-%m-%d')}.")
    except Exception as e:
        facts.append(f"⚠️ خطأ في معالجة بعض الإحصائيات: {str(e)}")
    
    return facts

def get_booking_company(row, col_map):
    for p_col in ['Place1', 'Place2', 'Place3']:
        if col_map.get(p_col) and pd.notnull(row[col_map[p_col]]):
            return row[col_map[p_col]]
    return "N/A"

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V15")
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
        return

    page_map = {
        "dashboard": "📊 Dashboard",
        "trends": "📈 Trends",
        "rankings": "🏆 Rankings",
        "tracker": "🔍 Professional Tracker",
        "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location",
        "competitor": "⚔️ Competitor Analysis",
        "compare": "📊 Price Compare"
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
        if 'Day' in df.columns and df['Day'].notnull().any():
            day_avg = df.groupby('Day')['Best_Price'].mean().sort_values()
            st.plotly_chart(px.bar(x=day_avg.index, y=day_avg.values, title="Average Price by Day of Week", labels={'x':'Day', 'y':'Price'}), use_container_width=True)
        
        st.markdown("#### 🎯 Optimal Booking Window")
        if 'days_before' in df.columns:
            df_valid = df[df['days_before'].notnull()]
            if not df_valid.empty:
                window_avg = df_valid.groupby('days_before')['Best_Price'].mean().reset_index()
                st.plotly_chart(px.line(window_avg, x='days_before', y='Best_Price', title="Best Time to Book (Days in Advance)"), use_container_width=True)
                st.info("💡 Tip: Lower points on the graph indicate the best time to book!")
            else: st.info("No data available for booking window analysis yet.")
        else: st.info("Booking date data missing in this file.")

    elif selected_page == "🏆 Rankings":
        st.markdown("### 🏆 Top Rankings by Stars")
        df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
        for s in [5, 4, 3]:
            st.markdown(f"#### ⭐ {s} Star Excellence")
            stars_df = df_u[df_u['Star'] == s].head(3)
            if not stars_df.empty:
                for _, row in stars_df.iterrows():
                    with st.container(border=True):
                        st.subheader(f"🏨 {row[col_map['Hotel']]}")
                        st.write(f"💰 Price: ${row['Best_Price']:.0f} | ⭐ Rate: {row['Rate']}/10")
            else: st.write("No data for this category.")

    elif selected_page == "🎉 Fun Facts":
        st.markdown("### 🎉 Fun Facts & Viral Insights")
        st.write("إحصائيات ذكية مخصصة للبلوجرز والمؤثرين في مجال السياحة:")
        
        if col_map['Arrival']:
            dates = sorted(df['arrival_dt'].dropna().unique())
            if len(dates) > 1:
                selected_date = st.select_slider("Select Data Snapshot", options=dates, format_func=lambda x: x.strftime('%Y-%m-%d'))
                sub_df = df[df['arrival_dt'] <= selected_date]
            else: sub_df = df
        else: sub_df = df

        facts = generate_fun_facts(sub_df, col_map, city)
        cols = st.columns(2)
        for i, fact in enumerate(facts):
            cols[i % 2].success(fact)

    elif selected_page == "🔍 Professional Tracker":
        st.markdown("### 🔍 Professional Market Tracker")
        st.write("تتبع تغيرات السوق والترتيب التنافسي للفنادق:")
        
        if col_map['Arrival']:
            trend_df = df.groupby('arrival_dt')['Best_Price'].agg(['mean', 'min', 'max']).reset_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=trend_df['arrival_dt'], y=trend_df['mean'], name='Average Price'))
            fig.add_trace(go.Scatter(x=trend_df['arrival_dt'], y=trend_df['min'], name='Min Price', line=dict(dash='dash')))
            fig.update_layout(title="Market Price Trend Over Time")
            st.plotly_chart(fig, use_container_width=True)
            
            # Enhanced Tracking
            hotel_options = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']} | 📍{r[col_map['Location']] if col_map['Location'] else 'N/A'}", axis=1).unique()
            selected_option = st.selectbox("Track Specific Hotel (Name | Stars | Location)", hotel_options)
            hotel_name = selected_option.split(" | ")[0]
            h_df = df[df[col_map['Hotel']] == hotel_name].sort_values('arrival_dt')
            st.line_chart(h_df.set_index('arrival_dt')['Best_Price'])
        else:
            st.info("Need arrival dates to enable tracking features.")

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location & Features")
        if col_map['Location'] and df[col_map['Location']].notnull().any():
            locations = df[col_map['Location']].dropna().unique()
            selected_loc = st.selectbox("Select Area", locations)
            loc_df = df[df[col_map['Location']] == selected_loc].copy()
            
            # Add Booking Company and Keep Arrival Dates
            loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
            
            cols = [col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company']
            if col_map['Arrival']: cols.append(col_map['Arrival'])
            if col_map['Desc']: cols.append(col_map['Desc'])
            
            st.dataframe(loc_df[cols].sort_values(['Best_Price', col_map['Arrival'] if col_map['Arrival'] else col_map['Hotel']]))
        else: st.info("Location data not available.")

    elif selected_page == "⚔️ Competitor Analysis":
        st.markdown("### ⚔️ Competitor Intelligence")
        hotel_list = df[col_map['Hotel']].unique()
        target_hotel = st.selectbox("Select Your Hotel", hotel_list)
        
        target_row = df[df[col_map['Hotel']] == target_hotel].iloc[0]
        target_price = target_row['Best_Price']
        target_loc = target_row[col_map['Location']] if col_map['Location'] else None
        
        # Hotel Detail Box
        with st.container(border=True):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader(f"💰 ${target_price:.0f}")
                st.write(f"⭐ {target_row['Star']} Stars")
                st.write(f"📍 {target_loc}")
            with c2:
                st.info(f"**Description:** {target_row[col_map['Desc']] if col_map['Desc'] else 'No description available.'}")

        st.markdown("---")
        if target_loc:
            comps = df[(df[col_map['Location']] == target_loc) & (df[col_map['Hotel']] != target_hotel)]
            st.write(f"Competitors in **{target_loc}**:")
        else:
            comps = df[(df['Star'] == target_row['Star']) & (df[col_map['Hotel']] != target_hotel)]
            st.write(f"Competitors with same **{target_row['Star']} Star** rating:")
            
        comps['Price_Diff'] = comps['Best_Price'] - target_price
        
        m1, m2 = st.columns(2)
        m1.metric("Your Price", f"${target_price:.0f}")
        m2.metric("Market Avg", f"${comps['Best_Price'].mean():.0f}", delta=f"{target_price - comps['Best_Price'].mean():.0f}")
        
        st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Price_Diff', 'Rate', 'Star']].sort_values('Best_Price'))

    elif selected_page == "📊 Price Compare":
        st.markdown("### 📊 Cross-City Price Comparison")
        comp_data = []
        for c_name, c_info in CITIES_DATA.items():
            t_df, _, _ = load_data(c_info['file'])
            if t_df is not None:
                comp_data.append({"City": c_name, "Avg": t_df['Best_Price'].mean(), "Min": t_df['Best_Price'].min(), "Max": t_df['Best_Price'].max()})
        
        if comp_data:
            c_df = pd.DataFrame(comp_data)
            st.plotly_chart(px.bar(c_df, x='City', y='Avg', color='City', title="Average Price Comparison"), use_container_width=True)
            st.table(c_df)

if __name__ == "__main__": main()
