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
    "Paris": {"file": "Paris_updated.xlsx", "emoji": "🗼"},
    "Dubai": {"file": "Dubai.xlsx", "emoji": "🏙️"},
    "Istanbul": {"file": "NewYork.xlsx", "emoji": "🕌"},
#   "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️"}
}

# ======================================================================================
# --- CORE ANALYTICS FUNCTIONS ---
# ======================================================================================
def clean_price(val):
    if pd.isnull(val): return np.nan
    cleaned = re.sub(r'[^\d.]', '', str(val))
    try: 
        res = float(cleaned) if cleaned else np.nan
        return res if res > 0 else np.nan
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
        # Fact 1-5
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
        
        # Fact 6-10
        facts.append(f"📊 {len(df)} offers analyzed." if lang=="English" else f"📊 تم تحليل {len(df)} عرض فندقي.")
        facts.append(f"📍 {df[col_map['Location']].nunique()} areas covered." if lang=="English" else f"📍 {df[col_map['Location']].nunique()} منطقة مغطاة.")
        facts.append(f"🏢 {df[h_col].nunique()} unique hotels found." if lang=="English" else f"🏢 تم العثور على {df[h_col].nunique()} فندق فريد.")
        facts.append(f"⭐ {len(df[df['Star'] == 5])} five-star luxury options." if lang=="English" else f"⭐ {len(df[df['Star'] == 5])} خيار فاخر 5 نجوم.")
        facts.append(f"🏨 {len(df[df['Star'] == 3])} budget-friendly 3-star options." if lang=="English" else f"🏨 {len(df[df['Star'] == 3])} خيار اقتصادي 3 نجوم.")

        # Fact 11-15
        if not df['days_before'].dropna().empty:
            best_w = df.groupby('days_before')['Best_Price'].mean().idxmin()
            facts.append(f"📅 Tip: Booking {int(best_w)} days ahead is cheapest." if lang=="English" else f"📅 نصيحة: الحجز قبل {int(best_w)} يوم هو الأوفر.")
        facts.append(f"🌐 **{df[col_map['Place1']].value_counts().idxmax()}** dominates market listings." if lang=="English" else f"🌐 **{df[col_map['Place1']].value_counts().idxmax()}** تهيمن على قوائم السوق.")
        facts.append(f"📈 Price gap is {expensive['Best_Price']/cheapest['Best_Price'].replace(0, np.nan):.1f}x." if lang=="English" else f"📈 الفجوة السعرية هي {expensive['Best_Price']/cheapest['Best_Price'].replace(0, np.nan):.1f} ضعف.")
        facts.append(f"🏆 {len(df[df['Rate'] >= 9])} hotels are 'Excellent' (9+)." if lang=="English" else f"🏆 {len(df[df['Rate'] >= 9])} فندق بتقييم 'ممتاز'.")
        facts.append(f"📉 {len(df[df['Best_Price'] < avg_p])} hotels are below average price." if lang=="English" else f"📉 {len(df[df['Best_Price'] < avg_p])} فندق تحت متوسط السعر.")

        # Fact 16-20
        facts.append(f"🌊 {len(df[df[col_map['Desc']].str.contains('view', case=False, na=False)])} hotels mention 'View'." if lang=="English" else f"🌊 {len(df[df[col_map['Desc']].str.contains('view', case=False, na=False)])} فندق يذكر 'إطلالة'.")
        facts.append(f"🏊 {len(df[df[col_map['Desc']].str.contains('pool', case=False, na=False)])} hotels mention 'Pool'." if lang=="English" else f"🏊 {len(df[df[col_map['Desc']].str.contains('pool', case=False, na=False)])} فندق يذكر 'مسبح'.")
        facts.append(f"🍽️ {len(df[df[col_map['Desc']].str.contains('breakfast', case=False, na=False)])} mention 'Breakfast'." if lang=="English" else f"🍽️ {len(df[df[col_map['Desc']].str.contains('breakfast', case=False, na=False)])} يذكر 'إفطار'.")
        facts.append(f"✨ 5-Star average: ${df[df['Star'] == 5]['Best_Price'].mean():.0f}." if lang=="English" else f"✨ متوسط سعر الـ 5 نجوم: ${df[df['Star'] == 5]['Best_Price'].mean():.0f}.")
        facts.append(f"🔍 {len(df[df[col_map['Rate']] < 7])} hotels are below 7/10 rating." if lang=="English" else f"🔍 {len(df[df[col_map['Rate']] < 7])} فندق تقييمهم أقل من 7.")

        # Fact 21-30
        facts.append(f"🏘️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()}** is the premium area." if lang=="English" else f"🏘️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()}** هي المنطقة الأغلى.")
        facts.append(f"🏷️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmin()}** is the value area." if lang=="English" else f"🏷️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmin()}** هي المنطقة الأوفر.")
        facts.append(f"📅 Analysis covers {df[col_map['ArrivalDay']].nunique()} arrival days." if lang=="English" else f"📅 التحليل يغطي {df[col_map['ArrivalDay']].nunique()} يوم وصول.")
        facts.append(f"🌞 Arriving on **{df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()}** is cheaper." if lang=="English" else f"🌞 الوصول يوم **{df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()}** أرخص.")
        facts.append(f"🏙️ {len(df[df['Best_Price'] > 500])} luxury deals (>500)." if lang=="English" else f"🏙️ {len(df[df['Best_Price'] > 500])} صفقة فاخرة.")
        facts.append(f"💸 {len(df[df['Best_Price'] < 100])} budget deals (<100)." if lang=="English" else f"💸 {len(df[df['Best_Price'] < 100])} صفقة اقتصادية.")
        facts.append(f"✅ {len(df.dropna(subset=[col_map['Desc']]))} hotels have descriptions." if lang=="English" else f"✅ {len(df.dropna(subset=[col_map['Desc']]))} فندق لديهم وصف.")
        facts.append(f"🌟 {len(df[df['Rate'] > 8.5])} hotels are 'Top Choice'." if lang=="English" else f"🌟 {len(df[df['Rate'] > 8.5])} فندق هي 'خيار ممتاز'.")
        facts.append(f"📈 Market volatility is high this month." if lang=="English" else f"📈 تقلب الأسعار مرتفع هذا الشهر.")
        facts.append(f"🚀 Analysis V29 complete." if lang=="English" else f"🚀 اكتمل التحليل V29.")
        
        # Fact 31-35 (Extra)
        facts.append(f"🏨 {df[col_map['Place1']].nunique()} platforms integrated." if lang=="English" else f"🏨 تم دمج {df[col_map['Place1']].nunique()} منصة.")
        facts.append(f"📅 Average booking window is {df['days_before'].mean():.1f} days." if lang=="English" else f"📅 متوسط نافذة الحجز {df['days_before'].mean():.1f} يوم.")
        facts.append(f"⭐ Most hotels are in the {df['Star'].mode()[0]:.0f}-star category." if lang=="English" else f"⭐ معظم الفنادق في فئة {df['Star'].mode()[0]:.0f} نجوم.")
        facts.append(f"💎 {len(df[df['Rate'] > 9.5])} ultra-premium ratings found." if lang=="English" else f"💎 تم العثور على {len(df[df['Rate'] > 9.5])} تقييم فائق.")
        facts.append(f"💼 Business travelers prefer {df.groupby(col_map['Location'])[col_map['Hotel']].count().idxmax()}." if lang=="English" else f"💼 المسافرون لغرض العمل يفضلون {df.groupby(col_map['Location'])[col_map['Hotel']].count().idxmax()}.")

    except: facts.append("Analyzing additional insights...")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
def main():
    config = load_config()
    settings = config.get("_settings", {"public_access": False, "default_landing_page": "🌍 Country Comparison"})
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    
    # Public Access Logic
    if not st.session_state.logged_in and settings.get("public_access", False):
        test_user = config.get("test_blogger", config.get("admin"))
        st.session_state.logged_in = True
        st.session_state.username = "Public_Visitor"
        st.session_state.role = test_user.get("role", "blogger")
        st.session_state.allowed_pages = test_user.get("allowed_pages", ["all"])
        st.session_state.is_public = True
    
    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V29")
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
                            st.session_state.is_public = False
                            update_last_login(u)
                            st.rerun()
                else: st.error("❌ Invalid Credentials")
        return

    # --- SIDEBAR ---
    st.sidebar.title(f"🚀 {st.session_state.username}")
    if st.session_state.get("is_public", False): 
        st.sidebar.warning("🔓 Public Access Mode")
        if st.sidebar.button("🔐 Admin Login"):
            st.session_state.logged_in = False
            st.session_state.is_public = False
            st.rerun()
    
    # --- NAVIGATION ---
    page_map = {
        "comparison": "🌍 Country Comparison", "dashboard": "📊 Dashboard",
        "trends": "📈 Trends & Patterns", "rankings": "🏆 Rankings",
        "tracker": "🔍 Price Tracker", "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location", "competitor": "⚔️ Competitor Analysis",
        "guide": "🧭 Traveler Guide", "custom_compare": "🎯 Custom Hotel Compare",
        "admin": "⚙️ Admin Control Panel"
    }
    
    raw_allowed = st.session_state.allowed_pages
    if "all" in raw_allowed: nav_options = list(page_map.values())
    else:
        nav_options = []
        for p in raw_allowed:
            if p in page_map: nav_options.append(page_map[p])
            elif p in page_map.values(): nav_options.append(p)
        default_p = settings.get("default_landing_page", "🌍 Country Comparison")
        if default_p not in nav_options: nav_options.insert(0, default_p)
        if st.session_state.role == "admin" and page_map["admin"] not in nav_options: nav_options.append(page_map["admin"])

    # STABLE NAVIGATION LOGIC
    if 'current_page' not in st.session_state or st.session_state.current_page not in nav_options:
        st.session_state.current_page = nav_options[0]

    def on_nav_change(): st.session_state.current_page = st.session_state.nav_radio

    selected_page = st.sidebar.radio("Navigation", nav_options, index=nav_options.index(st.session_state.current_page), key="nav_radio", on_change=on_nav_change)

    # --- SHARED FILTERS ---
    data_mode = st.sidebar.radio("Data Filter", ["All Recorded Data", "Latest Snapshot Only"])
    
    # --- PAGES ---
    if selected_page == "🌍 Country Comparison":
        st.title("🌍 Global Market Comparison")
        all_city_stats = []
        for c, info in CITIES_DATA.items():
            c_df, c_map, c_err = load_data(info['file'])
            if c_df is not None:
                if data_mode == "Latest Snapshot Only":
                    latest_b = c_df[c_map['BookingDate']].dropna().max()
                    c_df = c_df[c_df[c_map['BookingDate']] == latest_b]
                all_city_stats.append({
                    "City": f"{info['emoji']} {c}", "Avg Price": c_df['Best_Price'].mean(),
                    "Min Price": c_df['Best_Price'].min(), "Max Price": c_df['Best_Price'].max(),
                    "Avg Rating": c_df['Rate'].mean(), "Hotels": c_df[c_map['Hotel']].nunique(),
                    "5-Star Avg": c_df[c_df['Star'] == 5]['Best_Price'].mean()
                })
        
        if all_city_stats:
            stats_df = pd.DataFrame(all_city_stats)
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Best Value", stats_df.loc[stats_df['Avg Price'].idxmin(), 'City'])
            c2.metric("🌟 Quality Hub", stats_df.loc[stats_df['Avg Rating'].idxmax(), 'City'])
            c3.metric("🏨 Largest Market", stats_df.loc[stats_df['Hotels'].idxmax(), 'City'])
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            col_a.plotly_chart(px.bar(stats_df, x='City', y='Avg Price', color='City', title="Average Price ($)"), use_container_width=True)
            col_b.plotly_chart(px.scatter(stats_df, x='Avg Price', y='Avg Rating', size='Hotels', color='City', title="Price vs Quality (Bubble Size = Market Size)"), use_container_width=True)
            
            st.subheader("📊 Market Benchmarking")
            st.dataframe(stats_df.sort_values('Avg Price'), hide_index=True, use_container_width=True)
            
            st.subheader("⭐ Hotel Class Share (%)")
            star_stats = []
            for c, info in CITIES_DATA.items():
                c_df, c_map, _ = load_data(info['file'])
                if c_df is not None:
                    counts = c_df['Star'].value_counts(normalize=True) * 100
                    for s in [5, 4, 3]: star_stats.append({"City": c, "Stars": f"{s} Star", "Share": counts.get(s, 0)})
            st.plotly_chart(px.bar(pd.DataFrame(star_stats), x='City', y='Share', color='Stars', barmode='stack', title="Hotel Category Mix"), use_container_width=True)

    elif selected_page == "⚙️ Admin Control Panel":
        st.title("⚙️ Admin Control Panel")
        tab1, tab2 = st.tabs(["👤 Users", "🔧 Settings"])
        with tab1:
            user_list = {k:v for k,v in config.items() if k != "_settings"}
            st.dataframe(pd.DataFrame.from_dict(user_list, orient='index').reset_index().rename(columns={'index':'User'}), hide_index=True)
            with st.expander("➕ Add User"):
                nu, np, nr = st.text_input("User"), st.text_input("Pass"), st.selectbox("Role", ["blogger","company","admin"])
                if st.button("Create"):
                    config[nu] = {"password":np, "role":nr, "status":"active", "expiry_date":(datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"), "last_login":"N/A", "allowed_pages":["all"]}
                    save_config(config); st.rerun()
        with tab2:
            pub_access = st.toggle("🔓 Public Access", value=settings.get("public_access", False))
            landing = st.selectbox("Landing Page", list(page_map.values()), index=list(page_map.values()).index(settings.get("default_landing_page")))
            if st.button("Save Settings"):
                config["_settings"] = {"public_access": pub_access, "default_landing_page": landing}
                save_config(config); st.success("Updated!"); st.rerun()

    else:
        # --- CITY PAGES ---
        city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
        df, col_map, err = load_data(CITIES_DATA[city]['file'])
        if err: st.warning(f"⚠️ {err}"); return
        
        if data_mode == "Latest Snapshot Only":
            latest_b = df[col_map['BookingDate']].dropna().max()
            df = df[df[col_map['BookingDate']] == latest_b]

        if selected_page == "📊 Dashboard":
            st.markdown(f"### 📊 {city} Insights")
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
            c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
            c3.metric("Offers", len(df))
            st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution"), use_container_width=True)

        elif selected_page == "📈 Trends & Patterns":
            st.markdown("### 📈 Trends")
            st.plotly_chart(px.bar(df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().sort_values(), title="Price by Arrival Day"), use_container_width=True)
            valid_bw = df.dropna(subset=['days_before'])
            if not valid_bw.empty:
                st.plotly_chart(px.line(valid_bw.groupby('days_before')['Best_Price'].mean().reset_index(), x='days_before', y='Best_Price', title="Optimal Booking Window"), use_container_width=True)

        elif selected_page == "🏆 Rankings":
            st.markdown("### 🏆 Top Rankings")
            df_u = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
            for s in [5, 4, 3]:
                st.markdown(f"#### ⭐ {s} Star")
                stars_df = df_u[df_u['Star'] == s].head(5)
                if not stars_df.empty:
                    for _, row in stars_df.iterrows():
                        with st.container(border=True):
                            st.subheader(f"🏨 {row[col_map['Hotel']]}")
                            st.write(f"💰 Best Price: ${row['Best_Price']:.0f} | ⭐ Rate: {row['Rate']}/10")

        elif selected_page == "🎉 Fun Facts":
            st.markdown("### 🎉 Fun Facts")
            lang = st.radio("Language", ["English", "Arabic"], horizontal=True)
            facts = generate_fun_facts(df, col_map, city, lang)
            cols = st.columns(2)
            for i, fact in enumerate(facts): cols[i % 2].success(fact)

        elif selected_page == "🔍 Price Tracker":
            st.markdown("### 🔍 Tracker")
            if not df['booking_dt'].dropna().empty:
                st.plotly_chart(px.line(df.groupby('booking_dt')['Best_Price'].agg(['mean', 'min']).reset_index(), x='booking_dt', y=['mean', 'min'], title="Market Price Trend"), use_container_width=True)
            hotel_opts = df.apply(lambda r: f"{r[col_map['Hotel']]} | ⭐{r['Star']}", axis=1).unique()
            sel = st.selectbox("Select Hotel", hotel_opts)
            h_name = sel.split(" | ")[0]
            h_df = df[df[col_map['Hotel']] == h_name].sort_values('booking_dt')
            if not h_df.empty: st.line_chart(h_df.set_index(col_map['BookingDate'])['Best_Price'])

        elif selected_page == "📍 By Location":
            st.markdown("### 📍 Location History")
            valid_locs = df[col_map['Location']].dropna().unique()
            if len(valid_locs) > 0:
                loc = st.selectbox("Area", valid_locs)
                loc_df = df[df[col_map['Location']] == loc].copy()
                loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
                st.dataframe(loc_df[[col_map['Hotel'], 'Best_Price', 'Star', 'Rate', 'Booking Company', col_map['BookingDate'], col_map['ArrivalDay'], col_map['Desc']]].sort_values('Best_Price'), hide_index=True)

        elif selected_page == "⚔️ Competitor Analysis":
            st.markdown("### ⚔️ Competitor Intelligence")
            hotel_list = df[col_map['Hotel']].dropna().unique()
            if len(hotel_list) > 0:
                hotel = st.selectbox("Hotel", hotel_list)
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
            pref = st.radio("Find:", ["Value for Money", "Top Rated", "Lowest Price", "Features"])
            res_df = None
            if pref == "Value for Money":
                df['Value'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
                res_df = df.sort_values('Value', ascending=False).head(10)
            elif pref == "Top Rated":
                res_df = df.sort_values('Rate', ascending=False).head(10)
            elif pref == "Lowest Price":
                res_df = df.sort_values('Best_Price').head(10)
            else:
                search = st.text_input("Search (e.g. 'View')")
                if search: res_df = df[df[col_map['Desc']].str.contains(search, case=False, na=False)]
            
            if res_df is not None and not res_df.empty:
                cols_to_show = [col_map['Hotel'], 'Best_Price', 'Rate', col_map['Location'], col_map['Desc']]
                st.dataframe(res_df[cols_to_show], hide_index=True)

        elif selected_page == "🎯 Custom Hotel Compare":
            st.markdown("### 🎯 Custom Comparison")
            all_h = []
            for c, info in CITIES_DATA.items():
                t_df, t_map, _ = load_data(info['file'])
                if t_df is not None:
                    t_df['City'] = c
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
                            results.append({"City": h_data.iloc[-1]['City'], "Hotel": name, "Best Price ($)": h_data['Best_Price'].min(), "Stars": h_data.iloc[-1]['Star'], "Rate": h_data.iloc[-1]['Rate'], "Location": h_data.iloc[-1][col_map['Location']]})
                    st.dataframe(pd.DataFrame(results), hide_index=True)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_public = False
        st.rerun()

if __name__ == "__main__": main()
