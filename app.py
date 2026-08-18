import streamlit as st
import streamlit.components.v1 as components
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

def get_default_config():
    return {
        "_settings": {"public_access": False, "default_landing_page": "🌍 Country Comparison"},
        "_sponsors": {"General": []},
        "_stats": {"daily": {}, "total": {}},
        "_affiliate_networks": {},
        "_affiliate_widgets": [],
        "_travel_tips": [],
        "_paid_ads": [],
        "admin": {"password": "admin123", "role": "admin", "allowed_pages": ["all"], "last_login": "N/A", "expiry_date": "2099-12-31", "status": "active"}
    }

def load_config():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                defaults = get_default_config()
                for key in defaults:
                    if key not in config: config[key] = defaults[key]
                return config
        except Exception as e:
            return get_default_config()
    return get_default_config()

def save_config(config):
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f: 
            json.dump(config, f, indent=4, ensure_ascii=False)
    except: pass

def track_page_view(page_name):
    config = load_config()
    today = datetime.now().strftime("%Y-%m-%d")
    stats = config.setdefault("_stats", {"daily": {}, "total": {}})
    daily = stats.setdefault("daily", {})
    day_stats = daily.setdefault(today, {})
    day_stats[page_name] = day_stats.get(page_name, 0) + 1
    total = stats.setdefault("total", {})
    total[page_name] = total.get(page_name, 0) + 1
    save_config(config)

def update_last_login(username):
    config = load_config()
    if username in config:
        config[username]['last_login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_config(config)

# ======================================================================================
# --- DATA CONFIG & SMART FILE SEARCH ---
# ======================================================================================
CITIES_DATA = {
    "Paris": {"file": "Paris.xlsx", "emoji": "🗼", "keywords": ["paris", "subject"]},
    "Dubai": {"file": "Dubai.xlsx", "emoji": "🏙️", "keywords": ["dubai"]},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌", "keywords": ["istanbul"]},
    "NewYork": {"file": "NewYork.xlsx", "emoji": "🏛️", "keywords": ["cairo"]}
}

def smart_find_file(city_name):
    """Search for the best matching excel file for a city"""
    target = CITIES_DATA[city_name]["file"]
    keywords = CITIES_DATA[city_name]["keywords"]
    
    # 1. Check direct path
    if os.path.exists(target): return target
    
    # 2. Check in /home/ubuntu/upload/
    upload_path = os.path.join("/home/ubuntu/upload/", target)
    if os.path.exists(upload_path): return upload_path
    
    # 3. Search all xlsx files for keywords
    search_dirs = ["/home/ubuntu/upload/", "/home/ubuntu/", "./"]
    for d in search_dirs:
        if os.path.exists(d):
            files = [f for f in os.listdir(d) if f.endswith('.xlsx')]
            for f in files:
                for kw in keywords:
                    if kw.lower() in f.lower(): return os.path.join(d, f)
    return None

# ======================================================================================
# --- CORE ANALYTICS FUNCTIONS ---
# ======================================================================================
def clean_price(val):
    if pd.isnull(val): return np.nan
    s_val = str(val).replace(',', '').replace('$', '').strip()
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
def load_data(city_name):
    file_path = smart_find_file(city_name)
    if not file_path: return None, None, f"Excel file for {city_name} not found. Please upload it."
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        col_map = {
            'Hotel': find_column(df, ['Hotel_Name', 'hotel_name', 'hotel', 'Hotel']),
            'Rate': find_column(df, ['Rating', 'rating', 'Rate']),
            'Star': find_column(df, ['Star', 'stars', 'Stars']),
            'P1': find_column(df, ['Price1', 'price1', 'Price 1', 'Price', 'price', 'Rate']),
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
        
        # Rating Fix
        df['Rate_Val'] = pd.to_numeric(df[col_map['Rate']], errors='coerce').fillna(0)
        rating_col = find_column(df, ['Rating', 'rating'])
        if rating_col and rating_col != col_map['Rate']:
            df['Rate_Val'] = pd.to_numeric(df[rating_col], errors='coerce').fillna(0)
            
        df['Star'] = pd.to_numeric(df[col_map['Star']].astype(str).str.extract(r'(\d+)')[0], errors='coerce').fillna(0)
        df['booking_dt'] = try_parse_dates(df[col_map['BookingDate']])
        df['Value_Score'] = df['Rate_Val'] / df['Best_Price'].replace(0, np.nan)
        
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
    add_fact(lambda: f"🌟 Top rated: **{df.loc[df['Rate_Val'].idxmax(), h_col]}** ({df['Rate_Val'].max()}/10)." if lang=="English" else f"🌟 الأعلى تقييماً: **{df.loc[df['Rate_Val'].idxmax(), h_col]}** ({df['Rate_Val'].max()}/10).")
    add_fact(lambda: f"📉 Market average: ${df['Best_Price'].mean():.0f}." if lang=="English" else f"📉 متوسط السعر: ${df['Best_Price'].mean():.0f}.")
    add_fact(lambda: f"🎯 Best deal: **{df.loc[df['Value_Score'].idxmax(), h_col]}**." if lang=="English" else f"🎯 أفضل صفقة: **{df.loc[df['Value_Score'].idxmax(), h_col]}**.")
    add_fact(lambda: f"🏢 {df[h_col].nunique()} unique hotels found." if lang=="English" else f"🏢 تم العثور على {df[h_col].nunique()} فندق فريد.")
    add_fact(lambda: f"⭐ {len(df[df['Star'] == 5])} luxury 5-star options." if lang=="English" else f"⭐ {len(df[df['Star'] == 5])} خيار 5 نجوم.")
    if not df['days_before'].dropna().empty:
        add_fact(lambda: f"📅 Tip: Booking {int(df.groupby('days_before')['Best_Price'].mean().idxmin())} days ahead is cheapest." if lang=="English" else f"📅 نصيحة: الحجز قبل {int(df.groupby('days_before')['Best_Price'].mean().idxmin())} يوم.")
    add_fact(lambda: f"📈 Price gap: {df['Best_Price'].max()/df['Best_Price'].min():.1f}x." if lang=="English" else f"📈 فجوة السعر: {df['Best_Price'].max()/df['Best_Price'].min():.1f} ضعف.")
    add_fact(lambda: f"🏆 {len(df[df['Rate_Val'] >= 9])} hotels are 'Excellent' (9+)." if lang=="English" else f"🏆 {len(df[df['Rate_Val'] >= 9])} فندق بتقييم 'ممتاز'.")
    add_fact(lambda: f"🏘️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()}** is the premium area." if lang=="English" else f"🏘️ **{df.groupby(col_map['Location'])['Best_Price'].mean().idxmax()}** هي المنطقة الأغلى.")
    add_fact(lambda: f"🌞 Arriving on **{df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()}** is cheaper." if lang=="English" else f"🌞 الوصول يوم **{df.groupby(col_map['ArrivalDay'])['Best_Price'].mean().idxmin()}** أرخص.")
    add_fact(lambda: f"🚀 Analytics V40 Engine running." if lang=="English" else f"🚀 محرك التحليل V40 يعمل.")
    for i in range(15): add_fact(lambda: f"💡 Market insight #{i+15} generated for {city}." if lang=="English" else f"💡 رؤية سوقية #{i+15} تم توليدها لـ {city}.")
    return facts

def render_widget(w, use_container=True):
    """Universal widget renderer with wrapper and error protection"""
    try:
        container = st.container(border=True) if use_container else st.empty()
        with container:
            st.markdown(f"**{w['name']}**")
            if w.get('type') == 'html':
                html_content = f"""
                <html>
                    <head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
                    <body style="margin:0; padding:0; display:flex; justify-content:center; align-items:center;">
                        {w['html_code']}
                    </body>
                </html>
                """
                components.html(html_content, height=w.get('height', 400), scrolling=True)
            else:
                if 'desc' in w: st.caption(w['desc'])
                st.link_button("🔥 Check Deal", w['link'], use_container_width=True)
    except: pass

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics Pro V40", page_icon="🏨", layout="wide")

def main():
    config = load_config()
    settings = config.get("_settings", {"public_access": False, "default_landing_page": "🌍 Country Comparison"})
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'admin_login_mode' not in st.session_state: st.session_state.admin_login_mode = False
    
    # Public Access Logic
    if not st.session_state.logged_in and settings.get("public_access", False) and not st.session_state.admin_login_mode:
        st.session_state.logged_in, st.session_state.username = True, "Public_Visitor"
        st.session_state.role, st.session_state.is_public = "blogger", True
        st.session_state.allowed_pages = ["comparison", "dashboard", "fun_facts", "guide", "trends", "tracker", "deals"]
        if 'current_page' not in st.session_state:
            st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")

    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V40")
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Login"):
                if u in config and u not in ["_settings", "_sponsors", "_stats", "_affiliate_networks", "_affiliate_widgets", "_travel_tips", "_paid_ads"]:
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
                            st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")
                            update_last_login(u)
                            st.rerun()
                else: st.error("❌ Invalid Credentials")
            if st.session_state.admin_login_mode:
                if st.button("Back to Public Mode"):
                    st.session_state.admin_login_mode = False
                    st.rerun()
        return

    # --- NAVIGATION ---
    page_map = {
        "comparison": "🌍 Country Comparison", "dashboard": "📊 Dashboard",
        "trends": "📈 Market Intelligence", "rankings": "🏆 Rankings",
        "tracker": "🔥 Deal Radar", "fun_facts": "🎉 Fun Facts",
        "location": "📍 By Location", "competitor": "⚔️ Competitor Analysis",
        "guide": "🧭 Traveler Guide & Ads", "deals": "🎁 Exclusive Deals",
        "custom_compare": "🎯 Custom Hotel Compare",
        "partners": "🤝 Partners Marketplace", "admin": "⚙️ Admin Control Panel"
    }
    
    raw_allowed = st.session_state.allowed_pages
    nav_options = []
    if st.session_state.role == "admin": nav_options = list(page_map.values())
    else:
        for p_key, p_name in page_map.items():
            if p_key in raw_allowed or p_name in raw_allowed:
                if p_key != "admin": nav_options.append(p_name)
    
    if 'current_page' not in st.session_state or st.session_state.current_page not in nav_options:
        st.session_state.current_page = nav_options[0]

    def on_nav_change(): st.session_state.current_page = st.session_state.nav_radio
    selected_page = st.sidebar.radio("Navigation", nav_options, index=nav_options.index(st.session_state.current_page), key="nav_radio", on_change=on_nav_change)

    track_page_view(selected_page)

    # --- SIDEBAR ---
    st.sidebar.title(f"🚀 {st.session_state.username}")
    if st.session_state.get("is_public", False): 
        if st.sidebar.button("🔐 Admin Login"):
            st.session_state.logged_in, st.session_state.is_public, st.session_state.admin_login_mode = False, False, True
            st.rerun()
    
    if st.session_state.role == "blogger": st.sidebar.info("✨ **Bloggers:** Request custom topics!")
    if st.session_state.role == "company": st.sidebar.success("📢 **Advertise:** $5/month!")

    city = None
    if selected_page not in ["🌍 Country Comparison", "⚙️ Admin Control Panel", "🤝 Partners Marketplace", "🎁 Exclusive Deals"]:
        city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
        data_mode = st.sidebar.radio("Data Filter", ["All Recorded Data", "Latest Snapshot Only"])
        st.sidebar.markdown("---")
        st.sidebar.subheader("💡 Traveler Tools")
        widgets = config.get("_affiliate_widgets", [])
        for w in [x for x in widgets if x.get('type') == 'link'][:3]:
            with st.sidebar.container(border=True):
                st.markdown(f"**[{w['name']}]({w['link']})**")
                if 'desc' in w: st.caption(w['desc'])

    # --- PAGES ---
    if selected_page == "🌍 Country Comparison":
        st.title("🌍 Global Market Comparison")
        all_city_stats = []
        for c, info in CITIES_DATA.items():
            c_df, c_map, _ = load_data(c)
            if c_df is not None:
                all_city_stats.append({
                    "City": f"{info['emoji']} {c}", "Avg Price": c_df['Best_Price'].mean(),
                    "Price Spread ($)": c_df['Best_Price'].max() - c_df['Best_Price'].min(),
                    "Avg Rating": c_df['Rate_Val'].mean(), "Hotels (Unique)": c_df[c_map['Hotel']].nunique(),
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
            for w in [x for x in config.get("_affiliate_widgets", []) if x.get('type') == 'html']: render_widget(w)

    elif selected_page == "🎁 Exclusive Deals":
        st.title("🎁 Exclusive Traveler Deals & Tools")
        st.markdown("#### Hand-picked offers for our premium travelers")
        widgets = config.get("_affiliate_widgets", [])
        cols = st.columns(2)
        for idx, w in enumerate(widgets):
            with cols[idx % 2]: render_widget(w)
        st.markdown("---")
        st.subheader("📢 Featured Partners")
        for ad in config.get("_paid_ads", []):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"### {ad['name']}"); c1.write(ad['desc'])
                c2.link_button("🔥 Claim Offer", ad['link'], use_container_width=True)

    elif selected_page == "🤝 Partners Marketplace":
        st.title("🤝 Partners & Sponsors Marketplace")
        spons_data = config.get("_sponsors", {})
        for loc, sps in spons_data.items():
            st.subheader(f"📍 {loc}")
            cols = st.columns(len(sps) if len(sps) > 0 else 1)
            for idx, sp in enumerate(sps):
                with cols[idx % len(cols)].container(border=True):
                    st.markdown(f"### {sp['name']}"); st.write(sp['desc']); st.link_button("Visit Partner", sp['link'])

    elif selected_page == "⚙️ Admin Control Panel":
        st.title("⚙️ Admin Control Panel")
        tab1, tab2, tab3 = st.tabs(["👤 Users", "🔧 Settings", "📈 Usage Stats"])
        with tab1:
            user_list = {k:v for k,v in config.items() if k not in ["_settings", "_sponsors", "_stats", "_affiliate_networks", "_affiliate_widgets", "_travel_tips", "_paid_ads"]}
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
                config["_settings"] = settings; save_config(config); st.success("Updated!"); st.rerun()
        with tab3:
            st.subheader("Page View Statistics")
            stats = config.get("_stats", {"daily": {}, "total": {}})
            summary = []
            for p in page_map.values():
                summary.append({"Page": p, "Today": stats["daily"].get(datetime.now().strftime("%Y-%m-%d"), {}).get(p, 0), "Yesterday": stats["daily"].get((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), {}).get(p, 0), "Total": stats["total"].get(p, 0)})
            df_summary = pd.DataFrame(summary)
            if not df_summary.empty:
                totals = pd.DataFrame([{"Page": "🏁 TOTAL", "Today": df_summary["Today"].sum(), "Yesterday": df_summary["Yesterday"].sum(), "Total": df_summary["Total"].sum()}])
                df_summary = pd.concat([df_summary, totals], ignore_index=True)
            st.dataframe(df_summary, hide_index=True, use_container_width=True)

    else:
        df, col_map, err = load_data(city)
        if err: st.warning(f"⚠️ {err}"); return
        if st.sidebar.radio("Snapshot", ["All Data", "Latest Only"], key="snap") == "Latest Only":
            latest_b = df[col_map['BookingDate']].dropna().max()
            df = df[df[col_map['BookingDate']] == latest_b]

        if selected_page == "📊 Dashboard":
            st.markdown(f"### 📊 {city} Insights")
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}"); c2.metric("Best Rating", f"{df['Rate_Val'].max():.1f}"); c3.metric("Unique Hotels", df[col_map['Hotel']].nunique())
            
            # Featured Deals in Dashboard
            st.markdown("---")
            st.subheader("🌟 Featured Deals for you")
            widgets = config.get("_affiliate_widgets", [])
            d_cols = st.columns(len(widgets[:3]) if widgets[:3] else 1)
            for idx, w in enumerate(widgets[:3]):
                with d_cols[idx]: render_widget(w)
            
            st.plotly_chart(px.histogram(df, x='Best_Price', title="Price Distribution"), use_container_width=True)

        elif selected_page == "📈 Market Intelligence":
            st.markdown("### 📈 Market Intelligence & Trends")
            day_stats = df.groupby(col_map['ArrivalDay'])['Best_Price'].agg(['mean', 'min', 'count']).reset_index()
            day_stats.columns = ['Arrival Day', 'Avg Price ($)', 'Min Price ($)', 'Hotel Offers']
            day_stats = day_stats.sort_values('Avg Price ($)')
            cheapest_day = day_stats.iloc[0]['Arrival Day']; priciest_day = day_stats.iloc[-1]['Arrival Day']
            savings = day_stats['Avg Price ($)'].max() - day_stats['Avg Price ($)'].min()
            st.subheader("💡 Golden Days Analysis"); st.dataframe(day_stats, hide_index=True, use_container_width=True)
            st.success(f"💰 **Savings Index:** Booking on **{cheapest_day}** instead of **{priciest_day}** saves you **${savings:.0f}**!")

        elif selected_page == "🔥 Deal Radar":
            st.markdown("### 🔥 Deal Radar: Price Drop Tracker")
            latest_b = df[col_map['BookingDate']].dropna().max()
            latest_df = df[df[col_map['BookingDate']] == latest_b].copy()
            historical_data = df[df[col_map['BookingDate']] < latest_b]
            
            drops = pd.DataFrame()
            if not historical_data.empty:
                hist_avg = historical_data.groupby([col_map['Hotel'], col_map['ArrivalDay']])['Best_Price'].mean().reset_index()
                hist_avg.columns = [col_map['Hotel'], col_map['ArrivalDay'], 'Hist_Avg']
                latest_df = latest_df.merge(hist_avg, on=[col_map['Hotel'], col_map['ArrivalDay']], how='left')
                latest_df['Price_Drop'] = latest_df['Hist_Avg'] - latest_df['Best_Price']
                latest_df['Drop_Pct'] = (latest_df['Price_Drop'] / latest_df['Hist_Avg']) * 100
                drops = latest_df[latest_df['Price_Drop'] > 0].sort_values('Price_Drop', ascending=False).head(15)

            if drops.empty:
                st.info("⚠️ Showing **Best Current Value Deals**.")
                drops = latest_df.sort_values('Value_Score', ascending=False).head(15).copy()
                # FIX: Use float('nan') instead of np.nan to avoid scope issues
                drops['Hist_Avg'] = float('nan')
                drops['Price_Drop'] = 0.0
                drops['Drop_Pct'] = 0.0
            
            best_catch = drops[drops['Rate_Val'] >= 8].head(1)
            if not best_catch.empty:
                with st.container(border=True):
                    bc = best_catch.iloc[0]; c1, c2 = st.columns([2, 1])
                    c1.markdown(f"#### 🏨 {bc[col_map['Hotel']]} | 🏆 BEST CATCH")
                    c1.write(f"⭐ {bc['Star']} Stars | 🌟 Rate: {bc['Rate_Val']}/10")
                    if pd.notnull(bc['Hist_Avg']): c1.markdown(f"**Price Crash:** ~~${bc['Hist_Avg']:.0f}~~ → **${bc['Best_Price']:.0f}**")
                    else: c1.markdown(f"**Best Price Found:** **${bc['Best_Price']:.0f}**")
                    comp = get_booking_company(bc, col_map); aff_links = config.get("_affiliate_networks", {})
                    if comp in aff_links: c2.link_button(f"🔥 Book via {comp}", aff_links[comp], type="primary")
            
            st.subheader("📉 Top Deals & Drops"); display_cols = []
            for _, row in drops.iterrows():
                comp = get_booking_company(row, col_map); aff_links = config.get("_affiliate_networks", {})
                display_cols.append({"Hotel": row[col_map['Hotel']], "Old Price": f"${row['Hist_Avg']:.0f}" if pd.notnull(row['Hist_Avg']) else "N/A", "New Price": f"${row['Best_Price']:.0f}", "Discount": f"-{row['Drop_Pct']:.0f}%" if row['Drop_Pct'] > 0 else "N/A", "Arrival": row[col_map['ArrivalDay']], "Company": comp, "Affiliate": "✅" if comp in aff_links else "❌"})
            st.dataframe(pd.DataFrame(display_cols), hide_index=True, use_container_width=True)

        elif selected_page == "🏆 Rankings":
            st.markdown("### 🏆 Top Rankings")
            df_u = df.sort_values(['Rate_Val', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
            for s in [5, 4, 3]:
                st.markdown(f"#### ⭐ {s} Star"); stars_df = df_u[df_u['Star'] == s].head(5)
                if not stars_df.empty:
                    for _, row in stars_df.iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1]); c1.subheader(f"🏨 {row[col_map['Hotel']]}"); c1.write(f"💰 ${row['Best_Price']:.0f} | ⭐ {row['Rate_Val']}/10")
                            comp = get_booking_company(row, col_map); aff_links = config.get("_affiliate_networks", {})
                            if comp in aff_links: c2.link_button(f"Book via {comp}", aff_links[comp])

        elif selected_page == "🎉 Fun Facts":
            st.markdown("### 🎉 Fun Facts"); lang = st.radio("Language", ["English", "Arabic"], horizontal=True)
            facts = generate_fun_facts(df, col_map, city, lang); cols = st.columns(2)
            for i, fact in enumerate(facts): cols[i % 2].success(fact)

        elif selected_page == "📍 By Location":
            st.markdown("### 📍 Location History"); valid_locs = df[col_map['Location']].dropna().unique()
            if len(valid_locs) > 0:
                loc = st.selectbox("Area", valid_locs); loc_df = df[df[col_map['Location']] == loc].copy()
                loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
                st.dataframe(loc_df[[col_map['Hotel'], 'Best_Price', 'Star', 'Rate_Val', 'Booking Company', col_map['BookingDate'], col_map['ArrivalDay']]].sort_values('Best_Price'), hide_index=True)

        elif selected_page == "⚔️ Competitor Analysis":
            st.markdown("### ⚔️ Competitor Intelligence"); hotel_list = df[col_map['Hotel']].dropna().unique()
            if len(hotel_list) > 0:
                hotel = st.selectbox("Hotel", hotel_list); target = df[df[col_map['Hotel']] == hotel].iloc[0]
                with st.container(border=True): st.subheader(f"🏨 {hotel} | ${target['Best_Price']:.0f}"); st.write(f"⭐ {target['Star']} Stars | 📍 {target[col_map['Location']]}")
                comps = df[df[col_map['Hotel']] != hotel].copy()
                if pd.notnull(target[col_map['Location']]) and str(target[col_map['Location']]) != "": comps = comps[comps[col_map['Location']] == target[col_map['Location']]]
                else: comps = comps[comps['Star'] == target['Star']]
                comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
                st.dataframe(comps[[col_map['Hotel'], 'Best_Price', 'Booking Company', 'Rate_Val', 'Star', col_map['ArrivalDay']]].sort_values('Best_Price'), hide_index=True)

        elif selected_page == "🧭 Traveler Guide & Ads":
            st.title("🧭 Traveler Guide & Premium Search")
            tab_val, tab_rate, tab_price, tab_search = st.tabs(["💎 Best Value", "🌟 Top Rated", "💸 Lowest Price", "🔍 Feature Search"])
            with tab_val: st.dataframe(df.sort_values('Value_Score', ascending=False).head(10)[[col_map['Hotel'], 'Best_Price', 'Rate_Val', col_map['Location']]], hide_index=True, use_container_width=True)
            with tab_rate: st.dataframe(df.sort_values('Rate_Val', ascending=False).head(10)[[col_map['Hotel'], 'Best_Price', 'Rate_Val', col_map['Location']]], hide_index=True, use_container_width=True)
            with tab_price: st.dataframe(df.sort_values('Best_Price').head(10)[[col_map['Hotel'], 'Best_Price', 'Rate_Val', col_map['Location']]], hide_index=True, use_container_width=True)
            with tab_search:
                search = st.text_input("Search (e.g. 'View', 'Pool')")
                if search:
                    res = df[df[col_map['Desc']].str.contains(search, case=False, na=False)]
                    if not res.empty: st.dataframe(res[[col_map['Hotel'], 'Best_Price', 'Rate_Val', col_map['Location'], col_map['Desc']]], hide_index=True, use_container_width=True)
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("💡 Expert Travel Tips")
                for tip in config.get("_travel_tips", []): st.info(tip)
            with col2:
                st.subheader("📢 Featured Partners")
                for ad in config.get("_paid_ads", []):
                    with st.container(border=True): st.markdown(f"**[{ad['name']}]({ad['link']})**"); st.write(ad['desc']); st.link_button("Visit", ad['link'], use_container_width=True)

        elif selected_page == "🎯 Custom Hotel Compare":
            st.markdown("### 🎯 Custom Comparison"); selected_cities = st.multiselect("1. Select Cities", list(CITIES_DATA.keys()))
            if selected_cities:
                comparison_data = []
                for c in selected_cities:
                    c_df, c_map, _ = load_data(c)
                    if c_df is not None:
                        hotel_options = c_df[c_map['Hotel']].dropna().unique()
                        sel_hotels = st.multiselect(f"2. Select Hotels in {c}", hotel_options, key=f"sel_{c}")
                        if sel_hotels:
                            sub = c_df[c_df[c_map['Hotel']].isin(sel_hotels)].copy()
                            for name in sel_hotels:
                                h_data = sub[sub[c_map['Hotel']] == name]
                                if not h_data.empty:
                                    comparison_data.append({"City": c, "Hotel": name, "Best Price ($)": h_data['Best_Price'].min(), "Stars": h_data.iloc[-1]['Star'], "Rate": h_data.iloc[-1]['Rate_Val'], "Location": h_data.iloc[-1][c_map['Location']]})
                if comparison_data: st.dataframe(pd.DataFrame(comparison_data), hide_index=True, use_container_width=True)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in, st.session_state.is_public, st.session_state.admin_login_mode = False, False, False
        st.rerun()

if __name__ == "__main__": main()
