import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import re
import json

# ======================================================================================
# --- USER MANAGEMENT & PERSISTENCE ---
# ======================================================================================
USERS_FILE = "config_users.json"

def load_config():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            config = json.load(f)
            if "_settings" not in config:
                config["_settings"] = {"public_access": False, "default_landing_page": "🌍 Country Comparison"}
            return config
    return {
        "_settings": {"public_access": False, "default_landing_page": "🌍 Country Comparison"},
        "admin": {"password": "admin123", "role": "admin", "allowed_pages": ["all"], "last_login": "N/A", "expiry_date": "2099-12-31", "status": "active"}
    }

def save_config(config):
    with open(USERS_FILE, 'w') as f: json.dump(config, f, indent=4)

def update_last_login(username):
    config = load_config()
    if username in config:
        config[username]['last_login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_config(config)

# ======================================================================================
# --- DATA CONFIG ---
# ======================================================================================
CITIES_DATA = {
    "Paris": {"file": "subjectsanalysis.xlsx", "emoji": "🗼"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️"}
}

# ======================================================================================
# --- CORE ANALYTICS FUNCTIONS ---
# ======================================================================================
def clean_price(val):
    if pd.isnull(val): return np.nan
    cleaned = re.sub(r'[^\d.]', '', str(val))
    try: return float(cleaned) if cleaned else np.nan
    except: return np.nan

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
            'Desc': find_column(df, ['Desc', 'description']),
            'Location': find_column(df, ['location', 'area'])
        }
        for key in col_map:
            if col_map[key] is None:
                dummy = f"dummy_{key}"
                df[dummy] = np.nan
                col_map[key] = dummy

        for p in ['P1', 'P2', 'P3']: df[col_map[p]] = df[col_map[p]].apply(clean_price)
        df['Best_Price'] = df[[col_map['P1'], col_map['P2'], col_map['P3']]].min(axis=1)
        df['Best_Price'] = df['Best_Price'].fillna(df[col_map['P1']])
        df['Rate'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        df['booking_dt'] = try_parse_dates(df[col_map['BookingDate']])
        
        days_map = {'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6}
        def infer_arrival(row):
            if pd.isnull(row['booking_dt']) or pd.isnull(row[col_map['ArrivalDay']]): return np.nan
            b_dt, arr_day_name = row['booking_dt'], str(row[col_map['ArrivalDay']]).strip().capitalize()
            if arr_day_name not in days_map: return b_dt
            days_diff = (days_map[arr_day_name] - b_dt.weekday()) % 7
            if days_diff == 0: days_diff = 7
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

def generate_fun_facts(df, col_map, city, lang="English"):
    facts = []
    if df.empty: return ["No data available"]
    h_col = col_map['Hotel']
    try:
        # Fact 1-5: Basic Prices & Ratings
        cheapest = df.loc[df['Best_Price'].idxmin()]
        facts.append(f"💰 Cheapest: **{cheapest[h_col]}** at ${cheapest['Best_Price']:.0f}." if lang=="English" else f"💰 أرخص فندق: **{cheapest[h_col]}** بـ ${cheapest['Best_Price']:.0f}.")
        expensive = df.loc[df['Best_Price'].idxmax()]
        facts.append(f"💎 Most expensive: **{expensive[h_col]}** at ${expensive['Best_Price']:.0f}." if lang=="English" else f"💎 أغلى فندق: **{expensive[h_col]}** بـ ${expensive['Best_Price']:.0f}.")
        top_rated = df.loc[df['Rate'].idxmax()]
        facts.append(f"🌟 Top rated: **{top_rated[h_col]}** ({top_rated['Rate']}/10)." if lang=="English" else f"🌟 الأعلى تقييماً: **{top_rated[h_col]}** ({top_rated['Rate']}/10).")
        avg_p = df['Best_Price'].mean()
        facts.append(f"📉 Market avg in {city}: ${avg_p:.0f}." if lang=="English" else f"📉 متوسط السعر في {city}: ${avg_p:.0f}.")
        df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        best_v = df.loc[df['Value'].idxmax()]
        facts.append(f"🎯 Best deal: **{best_v[h_col]}** (Quality/Price)." if lang=="English" else f"🎯 أفضل صفقة: **{best_v[h_col]}** (جودة مقابل سعر).")
        
        # Fact 6-10: Market Volume & Diversity
        facts.append(f"📊 {len(df)} offers analyzed." if lang=="English" else f"📊 تم تحليل {len(df)} عرض فندقي.")
        facts.append(f"📍 {df[col_map['Location']].nunique()} areas covered." if lang=="English" else f"📍 {df[col_map['Location']].nunique()} منطقة مغطاة.")
        facts.append(f"🏢 {df[h_col].nunique()} unique hotels found." if lang=="English" else f"🏢 تم العثور على {df[h_col].nunique()} فندق فريد.")
        facts.append(f"⭐ {len(df[df['Star'] == 5])} five-star luxury options." if lang=="English" else f"⭐ {len(df[df['Star'] == 5])} خيار فاخر 5 نجوم.")
        facts.append(f"🏨 {len(df[df['Star'] == 3])} budget-friendly 3-star options." if lang=="English" else f"🏨 {len(df[df['Star'] == 3])} خيار اقتصادي 3 نجوم.")

        # Fact 11-15: Booking Insights
        if not df['days_before'].dropna().empty:
            best_w = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 Tip: Booking {int(best_w)} days ahead is cheapest." if lang=="English" else f"📅 نصيحة: الحجز قبل {int(best_w)} يوم هو الأوفر.")
        
        top_platform = df[col_map['Place1']].value_counts().idxmax()
        facts.append(f"🌐 **{top_platform}** dominates the market listings." if lang=="English" else f"🌐 **{top_platform}** تهيمن على قوائم السوق.")
        
        price_gap = expensive['Best_Price'] / cheapest['Best_Price'].replace(0, np.nan)
        facts.append(f"📈 The gap between highest and lowest price is {price_gap:.1f}x." if lang=="English" else f"📈 الفجوة بين أعلى وأقل سعر هي {price_gap:.1f} ضعف.")
        
        facts.append(f"🏆 {len(df[df['Rate'] >= 9])} hotels are 'Excellent' (9+)." if lang=="English" else f"🏆 {len(df[df['Rate'] >= 9])} فندق بتقييم 'ممتاز'.")
        facts.append(f"📉 {len(df[df['Best_Price'] < avg_p])} hotels are below average price." if lang=="English" else f"📉 {len(df[df['Best_Price'] < avg_p])} فندق تحت متوسط السعر.")

        # Fact 16-20: Specifics
        facts.append(f"🌊 {len(df[df[col_map['Desc']].str.contains('view', case=False, na=False)])} hotels mention 'View'." if lang=="English" else f"🌊 {len(df[df[col_map['Desc']].str.contains('view', case=False, na=False)])} فندق يذكر 'إطلالة'.")
        facts.append(f"🏊 {len(df[df[col_map['Desc']].str.contains('pool', case=False, na=False)])} hotels mention 'Pool'." if lang=="English" else f"🏊 {len(df[df[col_map['Desc']].str.contains('pool', case=False, na=False)])} فندق يذكر 'مسبح'.")
        facts.append(f"🍽️ {len(df[df[col_map['Desc']].str.contains('breakfast', case=False, na=False)])} mention 'Breakfast'." if lang=="English" else f"🍽️ {len(df[df[col_map['Desc']].str.contains('breakfast', case=False, na=False)])} يذكر 'إفطار'.")
        
        avg_5s = df[df['Star'] == 5]['Best_Price'].mean()
        if not np.isnan(avg_5s):
            facts.append(f"✨ 5-Star average: ${avg_5s:.0f} per night." if lang=="English" else f"✨ متوسط سعر الـ 5 نجوم: ${avg_5s:.0f}.")
        
        facts.append(f"🔍 {len(df[df[col_map['Rate']] < 7])} hotels are below 7/10 rating." if lang=="English" else f"🔍 {len(df[df[col_map['Rate']] < 7])} فندق تقييمهم أقل من 7.")

        # Fact 21-30: Advanced Analytics
        most_expensive_area = df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()
        facts.append(f"🏘️ **{most_expensive_area}** is the premium district." if lang=="English" else f"🏘️ **{most_expensive_area}** هي المنطقة الأغلى.")
        
        cheapest_area = df.groupby(col_map['Location'])['Best_Price'].mean().idxmin()
        facts.append(f"🏷️ **{cheapest_area}** offers the best value area." if lang=="English" else f"🏷️ **{cheapest_area}** هي المنطقة الأوفر.")
        
        facts.append(f"📅 Analysis covers {df[col_map['ArrivalDay']].nunique()} arrival days." if lang=="English" else f"📅 التحليل يغطي {df[col_map['ArrivalDay']].nunique()} يوم وصول.")
        
        best_day = df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()
        facts.append(f"🌞 Arriving on **{best_day}** is generally cheaper." if lang=="English" else f"🌞 الوصول يوم **{best_day}** أرخص غالباً.")
        
        facts.append(f"🏙️ {city} market has {len(df[df['Best_Price'] > 500])} luxury deals (>500)." if lang=="English" else f"🏙️ سوق {city} به {len(df[df['Best_Price'] > 500])} صفقة فاخرة.")
        facts.append(f"💸 {len(df[df['Best_Price'] < 100])} budget deals (<100) found." if lang=="English" else f"💸 تم العثور على {len(df[df['Best_Price'] < 100])} صفقة اقتصادية.")
        
        facts.append(f"✅ {len(df.dropna(subset=[col_map['Desc']]))} hotels have detailed descriptions." if lang=="English" else f"✅ {len(df.dropna(subset=[col_map['Desc']]))} فندق لديهم وصف مفصل.")
        facts.append(f"🌟 {len(df[df['Rate'] > 8.5])} hotels are 'Top Choice'." if lang=="English" else f"🌟 {len(df[df['Rate'] > 8.5])} فندق هي 'خيار ممتاز'.")
        
        facts.append(f"🕒 Latest market snapshot: {datetime.now().strftime('%H:%M')} today." if lang=="English" else f"🕒 أحدث لقطة للسوق: {datetime.now().strftime('%H:%M')} اليوم.")
        facts.append(f"🚀 Powered by Hotel Analytics Engine V27." if lang=="English" else f"🚀 مدعوم بمحرك تحليل الفنادق V27.")

    except: facts.append("Exploring more insights...")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    config = load_config()
    settings = config.get("_settings", {"public_access": False, "default_landing_page": "🌍 Country Comparison"})
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    # Bypass Login if Public Access is enabled
    if not st.session_state.logged_in and settings.get("public_access", False):
        test_user = config.get("test_blogger", config.get("admin"))
        st.session_state.logged_in = True
        st.session_state.username = "Public_Visitor"
        st.session_state.role = test_user.get("role", "blogger")
        st.session_state.allowed_pages = test_user.get("allowed_pages", ["all"])
        st.session_state.is_public = True
    else:
        st.session_state.is_public = False

    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V27")
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Login"):
                if u in config and u != "_settings":
                    user = config[u]
                    if user['password'] == p:
                        expiry = datetime.strptime(user['expiry_date'], "%Y-%m-%d")
                        if datetime.now() > expiry: st.error("❌ Subscription Expired.")
                        elif user['status'] == 'inactive': st.error("❌ Account Disabled.")
                        else:
                            st.session_state.logged_in, st.session_state.username = True, u
                            st.session_state.role, st.session_state.allowed_pages = user['role'], user['allowed_pages']
                            update_last_login(u)
                            st.rerun()
                else: st.error("❌ Invalid Credentials")
        return

    # --- SIDEBAR ---
    st.sidebar.title(f"🚀 {st.session_state.username}")
    if st.session_state.is_public: st.sidebar.warning("🔓 Public Access Mode")
    
    # --- NAVIGATION MAP ---
    page_map = {
        "comparison": "🌍 Country Comparison",
        "dashboard": "📊 Dashboard",
        "trends": "📈 Trends & Patterns",
        "rankings": "🏆 Rankings",
        "tracker": "🔍 Price Tracker",
        "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location",
        "competitor": "⚔️ Competitor Analysis",
        "guide": "🧭 Traveler Guide",
        "custom_compare": "🎯 Custom Hotel Compare",
        "admin": "⚙️ Admin Control Panel"
    }
    
    # Normalize allowed pages from JSON
    raw_allowed = st.session_state.allowed_pages
    if "all" in raw_allowed:
        nav_options = list(page_map.values())
    else:
        # Match keys or values from JSON
        nav_options = []
        for p in raw_allowed:
            # Check if p is a key
            if p in page_map: nav_options.append(page_map[p])
            # Check if p is a value
            elif p in page_map.values(): nav_options.append(p)
        
        # Ensure Landing Page is included if it's the default
        default_p = settings.get("default_landing_page", "🌍 Country Comparison")
        if default_p not in nav_options: nav_options.insert(0, default_p)
        
        if st.session_state.role == "admin" and page_map["admin"] not in nav_options:
            nav_options.append(page_map["admin"])

    # Default Page Logic
    if 'current_page' not in st.session_state:
        st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")
    
    # Sidebar Navigation
    selected_page = st.sidebar.radio("Navigation", nav_options, index=nav_options.index(st.session_state.current_page) if st.session_state.current_page in nav_options else 0)
    st.session_state.current_page = selected_page

    # --- SHARED DATA FILTER (Only for city pages) ---
    if selected_page != "🌍 Country Comparison" and selected_page != "⚙️ Admin Control Panel":
        city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
        df, col_map, err = load_data(CITIES_DATA[city]['file'])
        if err: st.warning(f"⚠️ {err}"); return
        
        data_mode = st.sidebar.radio("Analysis Mode", ["All Data (Cumulative)", "Latest Update Only"])
        if data_mode == "Latest Update Only":
            latest_b = df[col_map['BookingDate']].dropna().max()
            df = df[df[col_map['BookingDate']] == latest_b]
    else:
        df, col_map = None, None

    # --- PAGES ---
    if selected_page == "🌍 Country Comparison":
        st.title("🌍 Global Market Comparison")
        st.markdown("#### *The ultimate dashboard for travel bloggers and investors*")
        
        all_city_stats = []
        for c, info in CITIES_DATA.items():
            c_df, c_map, c_err = load_data(info['file'])
            if c_df is not None:
                all_city_stats.append({
                    "City": f"{info['emoji']} {c}",
                    "Avg Price": c_df['Best_Price'].mean(),
                    "Min Price": c_df['Best_Price'].min(),
                    "Max Price": c_df['Best_Price'].max(),
                    "Avg Rating": c_df['Rate'].mean(),
                    "Hotels": c_df[c_map['Hotel']].nunique(),
                    "5-Star Avg": c_df[c_df['Star'] == 5]['Best_Price'].mean()
                })
        
        if all_city_stats:
            stats_df = pd.DataFrame(all_city_stats)
            
            c1, c2, c3 = st.columns(3)
            best_val_city = stats_df.loc[stats_df['Avg Price'].idxmin(), 'City']
            top_rated_city = stats_df.loc[stats_df['Avg Rating'].idxmax(), 'City']
            luxury_hub = stats_df.loc[stats_df['5-Star Avg'].idxmin(), 'City']
            
            c1.metric("💰 Best Value City", best_val_city)
            c2.metric("🌟 Quality Hub", top_rated_city)
            c3.metric("💎 Luxury for Less", luxury_hub)
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            with col_a:
                fig1 = px.bar(stats_df, x='City', y='Avg Price', color='City', title="Average Price per Night ($)")
                st.plotly_chart(fig1, use_container_width=True)
            with col_b:
                fig2 = px.bar(stats_df, x='City', y='Avg Rating', color='City', title="Average Traveler Rating (1-10)")
                st.plotly_chart(fig2, use_container_width=True)
            
            st.subheader("📊 Comparative Data Table")
            st.dataframe(stats_df.sort_values('Avg Price'), hide_index=True, use_container_width=True)
            
            st.info("💡 **Blogger Tip:** Use this data to recommend the best 'Luxury for Less' destinations this month!")

    elif selected_page == "⚙️ Admin Control Panel":
        st.title("⚙️ Admin Control Panel")
        tab1, tab2, tab3 = st.tabs(["👤 Users", "🔧 Settings", "📈 System"])
        
        with tab1:
            user_list = {k:v for k,v in config.items() if k != "_settings"}
            user_df = pd.DataFrame.from_dict(user_list, orient='index').reset_index()
            st.dataframe(user_df.rename(columns={'index':'User'})[['User','role','last_login','expiry_date','status']], hide_index=True)
            
            with st.expander("➕ Add User"):
                nu, np, nr = st.text_input("Username"), st.text_input("Password"), st.selectbox("Role", ["blogger","company","admin"])
                ne = st.date_input("Expiry", datetime.now()+timedelta(days=30))
                if st.button("Create"):
                    config[nu] = {"password":np, "role":nr, "status":"active", "expiry_date":ne.strftime("%Y-%m-%d"), "last_login":"N/A", "allowed_pages":["dashboard","fun_facts","guide"]}
                    save_config(config); st.rerun()

        with tab2:
            st.subheader("Global App Settings")
            pub_access = st.toggle("🔓 Public Access (Bypass Login)", value=settings.get("public_access", False))
            landing = st.selectbox("Default Landing Page", list(page_map.values()), index=list(page_map.values()).index(settings.get("default_landing_page", "🌍 Country Comparison")))
            
            if st.button("Save Settings"):
                config["_settings"] = {"public_access": pub_access, "default_landing_page": landing}
                save_config(config); st.success("Settings Updated!"); st.rerun()

        with tab3:
            st.write(f"Total Users: {len(user_list)}")
            st.write(f"Active Files: {len([c for c,i in CITIES_DATA.items() if os.path.exists(i['file'])])}")

    elif selected_page == "📊 Dashboard":
        st.markdown(f"### 📊 {city} Market Insights")
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
        c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
        c3.metric("Offers Count", len(df))
        st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution"), use_container_width=True)

    elif selected_page == "📈 Trends & Patterns":
        st.markdown("### 📈 Trends: Market Patterns")
        st.plotly_chart(px.bar(df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().sort_values(), title="Price Pattern by Arrival Day"), use_container_width=True)
        valid_bw = df.dropna(subset=['days_before'])
        if not valid_bw.empty:
            st.plotly_chart(px.line(valid_bw.groupby('days_before')['Best_Price'].mean().reset_index(), x='days_before', y='Best_Price', title="Best Time to Book"), use_container_width=True)
        else: st.info("💡 Booking Window calculation active based on 'start book' and 'day of arrival'.")

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

    elif selected_page == "🎉 Fun Facts":
        st.markdown("### 🎉 Fun Facts & Viral Insights")
        lang = st.radio("Language", ["English", "Arabic"], horizontal=True)
        facts = generate_fun_facts(df, col_map, city, lang)
        cols = st.columns(2)
        for i, fact in enumerate(facts): cols[i % 2].success(fact)

    elif selected_page == "🔍 Price Tracker":
        st.markdown("### 🔍 Price Tracker")
        if not df['booking_dt'].dropna().empty:
            st.plotly_chart(px.line(df.groupby('booking_dt')['Best_Price'].agg(['mean', 'min']).reset_index(), x='booking_dt', y=['mean', 'min'], title="Market Price Evolution"), use_container_width=True)
        hotel_opts = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']}", axis=1).unique()
        sel = st.selectbox("Track Specific Hotel", hotel_opts)
        h_name = sel.split(" | ")[0]
        h_df = df[df[col_map['Hotel']] == h_name].sort_values('booking_dt')
        if not h_df.empty: st.line_chart(h_df.set_index(col_map['BookingDate'])['Best_Price'])

    elif selected_page == "📍 By Location":
        st.markdown("### 📍 Hotels by Location")
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
            else: comps = comps[comps['Star'] == target['Star']]
            comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
            st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate', 'Star', col_map['ArrivalDay']]].sort_values('Best_Price'), hide_index=True)

    elif selected_page == "🧭 Traveler Guide":
        st.markdown("### 🧭 Traveler Guide")
        pref = st.radio("Find:", ["Best Value", "Top Rated", "Lowest Price", "Features"])
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
                        results.append({
                            "City": h_data.iloc[-1]['City'], "Hotel": name, "Best Price ($)": h_data['Best_Price'].min(),
                            "Last Price ($)": h_data.iloc[-1]['Best_Price'], "Stars": h_data.iloc[-1]['Star'],
                            "Rate": h_data.iloc[-1]['Rate'], "Location": h_data.iloc[-1][col_map['Location']]
                        })
                st.dataframe(pd.DataFrame(results), hide_index=True)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_public = False
        st.rerun()

if __name__ == "__main__": main()
