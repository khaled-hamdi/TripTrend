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
# --- USER MANAGEMENT & STATS ---
# ======================================================================================
USERS_FILE = "config_users.json"

def load_config():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            config = json.load(f)
            if "_settings" not in config: config["_settings"] = {"public_access": False, "default_landing_page": "🌍 Country Comparison"}
            if "_sponsors" not in config: config["_sponsors"] = {"General": []}
            if "_stats" not in config: config["_stats"] = {"daily": {}, "total": {}}
            return config
    return {"_settings": {"public_access": False, "default_landing_page": "🌍 Country Comparison"}, "_stats": {"daily": {}, "total": {}}}

def save_config(config):
    with open(USERS_FILE, 'w') as f: json.dump(config, f, indent=4)

def track_page_view(page_name):
    config = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    stats = config.setdefault("_stats", {"daily": {}, "total": {}})
    
    # Daily stats
    daily = stats.setdefault("daily", {})
    day_stats = daily.setdefault(today, {})
    day_stats[page_name] = day_stats.get(page_name, 0) + 1
    
    # Total stats
    total = stats.setdefault("total", {})
    total[page_name] = total.get(page_name, 0) + 1
    
    save_config(config)

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
    "Istanbul": {"file": "istanbul.xlsx", "emoji": "🕌"},
    "NewYork": {"file": "NewYork.xlsx", "emoji": "🏛️"}
}

# ======================================================================================
# --- CORE ANALYTICS FUNCTIONS ---
# ======================================================================================
def clean_price(val):
    if pd.isnull(val): return np.nan
    s_val = str(val).replace(',', '')
    nums = re.findall(r'\d+\.?\d*', s_val)
    if not nums: return np.nan
    try:
        res = float(nums[0])
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
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel', 'Hotel']),
            'Rate': find_column(df, ['Rate', 'rating', 'Rating']),
            'Star': find_column(df, ['Star', 'stars', 'Stars']),
            'P1': find_column(df, ['Price1', 'price1', 'Price 1', 'Price', 'price']),
            'P2': find_column(df, ['price2', 'Price2', 'Price 2']),
            'P3': find_column(df, ['price3', 'Price3', 'Price 3']),
            'Place1': find_column(df, ['Place1', 'place1']),
            'Place2': find_column(df, ['place2', 'Place2']),
            'Place3': find_column(df, ['place3', 'Place3']),
            'ArrivalDay': find_column(df, ['day of arrival']),
            'BookingDate': find_column(df, ['start book', 'date of creat booking']),
            'Desc': find_column(df, ['Desc', 'description', 'Desc2']),
            'Location': find_column(df, ['location', 'area']),
            'Dist': find_column(df, ['Distance From places', 'distance'])
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
        df['Value_Score'] = df['Rate'] / df['Best_Price'].replace(0, np.nan)
        
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
    def add_fact(func):
        try:
            res = func(); 
            if res: facts.append(res)
        except: pass

    add_fact(lambda: f"💰 Cheapest: **{df.loc[df['Best_Price'].idxmin(), h_col]}** at ${df['Best_Price'].min():.0f}." if lang=="English" else f"💰 أرخص فندق: **{df.loc[df['Best_Price'].idxmin(), h_col]}** بـ ${df['Best_Price'].min():.0f}.")
    add_fact(lambda: f"💎 Most expensive: **{df.loc[df['Best_Price'].idxmax(), h_col]}** at ${df['Best_Price'].max():.0f}." if lang=="English" else f"💎 أغلى فندق: **{df.loc[df['Best_Price'].idxmax(), h_col]}** بـ ${df['Best_Price'].max():.0f}.")
    add_fact(lambda: f"🌟 Top rated: **{df.loc[df['Rate'].idxmax(), h_col]}** ({df['Rate'].max()}/10)." if lang=="English" else f"🌟 الأعلى تقييماً: **{df.loc[df['Rate'].idxmax(), h_col]}** ({df['Rate'].max()}/10).")
    add_fact(lambda: f"📉 Market average: ${df['Best_Price'].mean():.0f}." if lang=="English" else f"📉 متوسط السعر: ${df['Best_Price'].mean():.0f}.")
    add_fact(lambda: f"🎯 Best deal: **{df.loc[df['Value_Score'].idxmax(), h_col]}**." if lang=="English" else f"🎯 أفضل صفقة: **{df.loc[df['Value_Score'].idxmax(), h_col]}**.")
    add_fact(lambda: f"📊 {len(df)} offers analyzed." if lang=="English" else f"📊 تم تحليل {len(df)} عرض.")
    add_fact(lambda: f"🏢 {df[h_col].nunique()} unique hotels found." if lang=="English" else f"🏢 تم العثور على {df[h_col].nunique()} فندق فريد.")
    add_fact(lambda: f"⭐ {len(df[df['Star'] == 5])} luxury 5-star options." if lang=="English" else f"⭐ {len(df[df['Star'] == 5])} خيار 5 نجوم.")
    add_fact(lambda: f"🏨 {len(df[df['Star'] == 3])} budget 3-star options." if lang=="English" else f"🏨 {len(df[df['Star'] == 3])} خيار 3 نجوم.")
    if not df['days_before'].dropna().empty:
        add_fact(lambda: f"📅 Tip: Booking {int(df.groupby('days_before')['Best_Price'].mean().idxmin())} days ahead is cheapest." if lang=="English" else f"📅 نصيحة: الحجز قبل {int(df.groupby('days_before')['Best_Price'].mean().idxmin())} يوم.")
    add_fact(lambda: f"🌐 **{df[col_map['Place1']].value_counts().idxmax()}** dominates market listings." if lang=="English" else f"🌐 **{df[col_map['Place1']].value_counts().idxmax()}** تهيمن على قوائم السوق.")
    add_fact(lambda: f"📈 Price gap: {df['Best_Price'].max()/df['Best_Price'].min():.1f}x." if lang=="English" else f"📈 فجوة السعر: {df['Best_Price'].max()/df['Best_Price'].min():.1f} ضعف.")
    add_fact(lambda: f"🏆 {len(df[df['Rate'] >= 9])} hotels are 'Excellent' (9+)." if lang=="English" else f"🏆 {len(df[df['Rate'] >= 9])} فندق بتقييم 'ممتاز'.")
    add_fact(lambda: f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} hotels are below average price." if lang=="English" else f"📉 {len(df[df['Best_Price'] < df['Best_Price'].mean()])} فندق تحت المتوسط.")
    add_fact(lambda: f"🌊 {len(df[df[col_map['Desc']].str.contains('view', case=False, na=False)])} hotels mention 'View'." if lang=="English" else f"🌊 {len(df[df[col_map['Desc']].str.contains('view', case=False, na=False)])} يذكر 'إطلالة'.")
    add_fact(lambda: f"🏊 {len(df[df[col_map['Desc']].str.contains('pool', case=False, na=False)])} hotels mention 'Pool'." if lang=="English" else f"🏊 {len(df[df[col_map['Desc']].str.contains('pool', case=False, na=False)])} يذكر 'مسبح'.")
    add_fact(lambda: f"🍽️ {len(df[df[col_map['Desc']].str.contains('breakfast', case=False, na=False)])} mention 'Breakfast'." if lang=="English" else f"🍽️ {len(df[df[col_map['Desc']].str.contains('breakfast', case=False, na=False)])} يذكر 'إفطار'.")
    add_fact(lambda: f"✨ 5-Star average: ${df[df['Star'] == 5]['Best_Price'].mean():.0f}." if lang=="English" else f"✨ متوسط سعر الـ 5 نجوم: ${df[df['Star'] == 5]['Best_Price'].mean():.0f}.")
    add_fact(lambda: f"🔍 {len(df[df['Rate'] < 7])} hotels are below 7/10 rating." if lang=="English" else f"🔍 {len(df[df['Rate'] < 7])} فندق تقييمهم أقل من 7.")
    add_fact(lambda: f"🏘️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()}** is the premium area." if lang=="English" else f"🏘️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()}** هي المنطقة الأغلى.")
    add_fact(lambda: f"🏷️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmin()}** is the value area." if lang=="English" else f"🏷️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmin()}** هي المنطقة الأوفر.")
    add_fact(lambda: f"📅 Analysis covers {df[col_map['ArrivalDay']].nunique()} arrival days." if lang=="English" else f"📅 التحليل يغطي {df[col_map['ArrivalDay']].nunique()} يوم وصول.")
    add_fact(lambda: f"🌞 Arriving on **{df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()}** is cheaper." if lang=="English" else f"🌞 الوصول يوم **{df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()}** أرخص.")
    add_fact(lambda: f"🏙️ {city} has {len(df[df['Best_Price'] > 500])} luxury deals (>500)." if lang=="English" else f"🏙️ {city} به {len(df[df['Best_Price'] > 500])} صفقة فاخرة.")
    add_fact(lambda: f"💸 {len(df[df['Best_Price'] < 100])} budget deals (<100)." if lang=="English" else f"💸 تم العثور على {len(df[df['Best_Price'] < 100])} صفقة اقتصادية.")
    add_fact(lambda: f"✅ {len(df.dropna(subset=[col_map['Desc']]))} hotels have descriptions." if lang=="English" else f"✅ {len(df.dropna(subset=[col_map['Desc']]))} فندق لديهم وصف.")
    add_fact(lambda: f"🌟 {len(df[df['Rate'] > 8.5])} hotels are 'Top Choice'." if lang=="English" else f"🌟 {len(df[df['Rate'] > 8.5])} فندق هي 'خيار ممتاز'.")
    add_fact(lambda: f"📈 Market volatility is high this month." if lang=="English" else f"📈 تقلب الأسعار مرتفع هذا الشهر.")
    add_fact(lambda: f"🚀 Analytics V34 Engine running." if lang=="English" else f"🚀 محرك التحليل V34 يعمل.")
    add_fact(lambda: f"🏨 {df[col_map['Place1']].nunique()} platforms integrated." if lang=="English" else f"🏨 تم دمج {df[col_map['Place1']].nunique()} منصة.")
    add_fact(lambda: f"📅 Avg booking window: {df['days_before'].mean():.0f} days." if lang=="English" else f"📅 متوسط نافذة الحجز {df['days_before'].mean():.0f} يوم.")
    add_fact(lambda: f"⭐ Most common: {df['Star'].mode()[0]:.0f}-star category." if lang=="English" else f"⭐ الفئة الأكثر شيوعاً: {df['Star'].mode()[0]:.0f} نجوم.")
    add_fact(lambda: f"💎 {len(df[df['Rate'] > 9.5])} ultra-premium ratings." if lang=="English" else f"💎 تم العثور على {len(df[df['Rate'] > 9.5])} تقييم فائق.")
    add_fact(lambda: f"💼 Business district: {df.groupby(col_map['Location'])[col_map['Hotel']].count().idxmax()}." if lang=="English" else f"💼 منطقة الأعمال: {df.groupby(col_map['Location'])[col_map['Hotel']].count().idxmax()}.")
    add_fact(lambda: f"🔍 {len(df[df['Best_Price'] > df['Best_Price'].median()])} hotels above median price." if lang=="English" else f"🔍 {len(df[df['Best_Price'] > df['Best_Price'].median()])} فندق فوق وسيط السعر.")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V34", page_icon="🏨", layout="wide")

def main():
    config = load_config()
    settings = config.get("_settings", {"public_access": False, "default_landing_page": "🌍 Country Comparison"})
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'admin_login_mode' not in st.session_state: st.session_state.admin_login_mode = False
    
    # SECURITY FIX: Public Access Logic
    if not st.session_state.logged_in and settings.get("public_access", False) and not st.session_state.admin_login_mode:
        # Strictly define Public Visitor Profile
        st.session_state.logged_in = True
        st.session_state.username = "Public_Visitor"
        st.session_state.role = "blogger"
        # Never allow 'all' or 'admin' page for public visitors
        st.session_state.allowed_pages = ["dashboard", "fun_facts", "guide", "comparison","trends","rankings","tracker","custom_compare","partners","location"]
        st.session_state.is_public = True
        # Force Landing Page on first entry
        if 'first_entry' not in st.session_state:
            st.session_state.first_entry = True
            st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")

    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics")
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Login"):
                if u in config and u not in ["_settings", "_sponsors", "_stats"]:
                    user = config[u]
                    if user['password'] == p:
                        expiry = datetime.strptime(user['expiry_date'], "%Y-%m-%d")
                        if datetime.now() > expiry: st.error("❌ Expired.")
                        elif user['status'] == 'inactive': st.error("❌ Disabled.")
                        else:
                            st.session_state.logged_in, st.session_state.username = True, u
                            st.session_state.role, st.session_state.allowed_pages = user['role'], user['allowed_pages']
                            st.session_state.is_public = False
                            st.session_state.admin_login_mode = False
                            # Set default page on login
                            st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")
                            update_last_login(u)
                            st.rerun()
                else: st.error("❌ Invalid Credentials")
            if st.session_state.admin_login_mode:
                if st.button("Back to Public Mode"):
                    st.session_state.admin_login_mode = False
                    st.rerun()
        return

    # --- NAVIGATION SETUP ---
    page_map = {
        "comparison": "🌍 Country Comparison", "dashboard": "📊 Dashboard",
        "trends": "📈 Trends & Patterns", "rankings": "🏆 Rankings",
        "tracker": "🔍 Price Tracker", "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location", "competitor": "⚔️ Competitor Analysis",
        "guide": "🧭 Traveler Guide", "custom_compare": "🎯 Custom Hotel Compare",
        "partners": "🤝 Partners Marketplace", "admin": "⚙️ Admin Control Panel"
    }
    
    raw_allowed = st.session_state.allowed_pages
    nav_options = []
    
    # Filter pages based on role and allowed_pages
    if st.session_state.role == "admin":
        nav_options = list(page_map.values())
    else:
        # Public or regular users
        for p_key, p_name in page_map.items():
            if p_key in raw_allowed or p_name in raw_allowed:
                # STRICT SECURITY: Never allow Admin page for non-admins
                if p_key != "admin": nav_options.append(p_name)
    
    # Ensure default landing page is available and first if not set
    default_p = settings.get("default_landing_page", "🌍 Country Comparison")
    if default_p not in nav_options and not st.session_state.is_public:
        # Only add if it's not the admin page
        if default_p != page_map["admin"]: nav_options.insert(0, default_p)

    # Validate current_page
    if 'current_page' not in st.session_state or st.session_state.current_page not in nav_options:
        st.session_state.current_page = nav_options[0]

    # --- SIDEBAR ---
    st.sidebar.title(f"🚀 {st.session_state.username}")
    if st.session_state.get("is_public", False): 
        if st.sidebar.button("🔐Login"):
            st.session_state.logged_in = False
            st.session_state.is_public = False
            st.session_state.admin_login_mode = True
            st.rerun()
    
    # Marketing Messages
    if st.session_state.role == "blogger":
        st.sidebar.info("✨ **Bloggers:** We can create custom daily topics and exclusive stats just for you!")
    if st.session_state.role == "company":
        st.sidebar.success("📢 **Advertise Here:** Grow your business for just **$5/month**!")

    def on_nav_change(): st.session_state.current_page = st.session_state.nav_radio
    selected_page = st.sidebar.radio("Navigation", nav_options, index=nav_options.index(st.session_state.current_page), key="nav_radio", on_change=on_nav_change)

    # Track View
    track_page_view(selected_page)

    # --- SHARED FILTERS & SPONSORS ---
    city = None
    if selected_page not in ["🌍 Country Comparison", "⚙️ Admin Control Panel", "🤝 Partners Marketplace"]:
        city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
        data_mode = st.sidebar.radio("Data Filter", ["All Recorded Data", "Latest Snapshot Only"])
        
        # Sidebar Sponsor Widget
        st.sidebar.markdown("---")
        st.sidebar.subheader("🌟 Featured Partners")
        sponsors = config.get("_sponsors", {}).get(city, config.get("_sponsors", {}).get("General", []))
        for sp in sponsors[:2]:
            with st.sidebar.container(border=True):
                st.markdown(f"**[{sp['name']}]({sp['link']})**")
                st.caption(sp['desc'])

    # --- PAGES ---
    if selected_page == "🌍 Country Comparison":
        st.title("🌍 Global Market Comparison")
        all_city_stats = []
        for c, info in CITIES_DATA.items():
            c_df, c_map, _ = load_data(info['file'])
            if c_df is not None:
                all_city_stats.append({
                    "City": f"{info['emoji']} {c}", "Avg Price": c_df['Best_Price'].mean(),
                    "Price Spread ($)": c_df['Best_Price'].max() - c_df['Best_Price'].min(),
                    "Avg Rating": c_df['Rate'].mean(), "Hotels (Unique)": c_df[c_map['Hotel']].nunique(),
                    "Optimal Booking": round(c_df['days_before'].mean()) if not pd.isnull(c_df['days_before'].mean()) else 0,
                    "Luxury Share (%)": (len(c_df[c_df['Star'] == 5]) / len(c_df)) * 100 if len(c_df) > 0 else 0
                })
        
        if all_city_stats:
            stats_df = pd.DataFrame(all_city_stats)
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Best Value", stats_df.loc[stats_df['Avg Price'].idxmin(), 'City'])
            c2.metric("🌟 Quality Hub", stats_df.loc[stats_df['Avg Rating'].idxmax(), 'City'])
            c3.metric("📅 Best Prep", stats_df.loc[stats_df['Optimal Booking'].idxmin(), 'City'])
            
            st.markdown("---")
            col_a, col_b = st.columns(2)
            col_a.plotly_chart(px.bar(stats_df, x='City', y='Avg Price', color='City', title="Average Market Price ($)"), use_container_width=True)
            col_b.plotly_chart(px.scatter(stats_df, x='Avg Price', y='Avg Rating', size='Hotels (Unique)', color='City', title="Price vs Quality Index"), use_container_width=True)
            
            st.subheader("📊 Market Opportunity Gap Analysis")
            st.dataframe(stats_df[['City', 'Price Spread ($)', 'Luxury Share (%)', 'Hotels (Unique)']].sort_values('Price Spread ($)', ascending=False), hide_index=True, use_container_width=True)

    elif selected_page == "🤝 Partners Marketplace":
        st.title("🤝 Partners & Sponsors Marketplace")
        spons_data = config.get("_sponsors", {})
        for loc, sps in spons_data.items():
            st.subheader(f"📍 {loc}")
            cols = st.columns(len(sps) if len(sps) > 0 else 1)
            for idx, sp in enumerate(sps):
                with cols[idx % len(cols)].container(border=True):
                    st.markdown(f"### {sp['name']}")
                    st.write(sp['desc'])
                    st.link_button("Visit Partner", sp['link'])

    elif selected_page == "⚙️ Admin Control Panel":
        st.title("⚙️ Admin Control Panel")
        tab1, tab2, tab3 = st.tabs(["👤 Users", "🔧 Settings", "📈 Usage Stats"])
        with tab1:
            user_list = {k:v for k,v in config.items() if k not in ["_settings", "_sponsors", "_stats"]}
            st.dataframe(pd.DataFrame.from_dict(user_list, orient='index').reset_index().rename(columns={'index':'User'}), hide_index=True)
            with st.expander("➕ Add User"):
                nu, np, nr = st.text_input("User"), st.text_input("Pass"), st.selectbox("Role", ["blogger","company","admin"])
                if st.button("Create"):
                    config[nu] = {"password":np, "role":nr, "status":"active", "expiry_date":(datetime.now()+timedelta(days=30)).strftime("%Y-%m-%d"), "last_login":"N/A", "allowed_pages":["all"]}
                    save_config(config); st.rerun()
        with tab2:
            settings["public_access"] = st.toggle("🔓 Public Access", value=settings.get("public_access", False))
            settings["default_landing_page"] = st.selectbox("Landing Page", list(page_map.values()), index=list(page_map.values()).index(settings.get("default_landing_page")))
            if st.button("Save Settings"):
                config["_settings"] = settings
                save_config(config); st.success("Updated!"); st.rerun()
        with tab3:
            st.subheader("Page View Statistics")
            stats = config.get("_stats", {"daily": {}, "total": {}})
            summary = []
            for p in page_map.values():
                summary.append({
                    "Page": p,
                    "Today": stats["daily"].get(datetime.now().strftime("%Y-%m-%d"), {}).get(p, 0),
                    "Yesterday": stats["daily"].get((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), {}).get(p, 0),
                    "Total": stats["total"].get(p, 0)
                })
            # --- الكود الجديد هنا ---
df_summary = pd.DataFrame(summary)
if not df_summary.empty:
    totals = pd.DataFrame([{
        "Page": "🏁 TOTAL",
        "Today": df_summary["Today"].sum(),
        "Yesterday": df_summary["Yesterday"].sum(),
        "Total": df_summary["Total"].sum()
    }])
    df_summary = pd.concat([df_summary, totals], ignore_index=True)

# حساب الارتفاع المطلوب تلقائياً (35 بكسل لكل صف + 38 بكسل للـ Header)
calc_height = (len(df_summary) + 1) * 35 + 3

st.dataframe(
    df_summary, 
    hide_index=True, 
    use_container_width=True, 
    height=calc_height  # <--- إضافة الارتفاع المحسوب هنا
)
        else:
        # --- CITY PAGES ---
        df, col_map, err = load_data(CITIES_DATA[city]['file'])
        if err: st.warning(f"⚠️ {err}"); return
        
        if data_mode == "Latest Snapshot Only":
            latest_b = df[col_map['BookingDate']].dropna().max()
            df = df[df[col_map['BookingDate']] == latest_b]

        # Contextual Ad Banner
        sponsors = config.get("_sponsors", {}).get(city, [])
        if sponsors:
            with st.container(border=True):
                st.markdown(f"🌟 **Featured in {city}:** [{sponsors[0]['name']}]({sponsors[0]['link']}) - {sponsors[0]['desc']}")

        if selected_page == "📊 Dashboard":
            st.markdown(f"### 📊 {city} Insights")
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
            c2.metric("Best Rating", f"{df['Rate'].max():.1f}")
            c3.metric("Unique Hotels", df[col_map['Hotel']].nunique())
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
                res_df = df.sort_values('Value_Score', ascending=False).head(10)
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
            selected_cities = st.multiselect("1. Select Cities", list(CITIES_DATA.keys()))
            if selected_cities:
                comparison_data = []
                for c in selected_cities:
                    c_df, c_map, _ = load_data(CITIES_DATA[c]['file'])
                    if c_df is not None:
                        hotel_options = c_df[c_map['Hotel']].dropna().unique()
                        sel_hotels = st.multiselect(f"2. Select Hotels in {c}", hotel_options, key=f"sel_{c}")
                        if sel_hotels:
                            sub = c_df[c_df[c_map['Hotel']].isin(sel_hotels)].copy()
                            for name in sel_hotels:
                                h_data = sub[sub[c_map['Hotel']] == name]
                                if not h_data.empty:
                                    comparison_data.append({
                                        "City": c, "Hotel": name, "Best Price ($)": h_data['Best_Price'].min(),
                                        "Stars": h_data.iloc[-1]['Star'], "Rate": h_data.iloc[-1]['Rate'], 
                                        "Location": h_data.iloc[-1][c_map['Location']]
                                    })
                if comparison_data:
                    st.dataframe(pd.DataFrame(comparison_data), hide_index=True, use_container_width=True)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.is_public = False
        st.session_state.admin_login_mode = False
        st.rerun()

if __name__ == "__main__": main()
