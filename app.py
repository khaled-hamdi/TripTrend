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
import random

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
                st.session_state['config_error'] = None
                return config
        except Exception as e:
            st.session_state['config_error'] = f"JSON Error: {str(e)}"
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
    "Paris": {"file": "Paris.xlsx", "emoji": "🗼", "keywords": ["paris"]},
    "Dubai": {"file": "Dubai.xlsx", "emoji": "🏙️", "keywords": ["dubai"]},
    "Istanbul": {"file": "Istanbul.xlsx", "emoji": "🕌", "keywords": ["istanbul"]},
    "Cairo": {"file": "Cairo.xlsx", "emoji": "🏛️", "keywords": ["cairo"]},
    "NewYork": {"file": "NewYork.xlsx", "emoji": "🗽", "keywords": ["newyork", "new york"]},
    "Switherland": {"file": "Switherland.xlsx", "emoji": "🏔️", "keywords": ["switherland", "swiss"]}
}

def smart_find_file(city_name):
    target = CITIES_DATA[city_name]["file"]
    keywords = CITIES_DATA[city_name]["keywords"]
    search_dirs = ["/home/ubuntu/upload/", "/home/ubuntu/", "./"]
    for d in search_dirs:
        if os.path.exists(d):
            exact_path = os.path.join(d, target)
            if os.path.exists(exact_path): return exact_path
            try:
                files = [f for f in os.listdir(d) if f.endswith('.xlsx')]
                for f in files:
                    for kw in keywords:
                        if kw.lower() in f.lower(): return os.path.join(d, f)
            except: pass
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
    if not file_path: return None, None, f"Excel file for {city_name} not found."
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

def render_affiliate_button(row, col_map, config, key_suffix=""):
    comp = get_booking_company(row, col_map)
    aff_links = config.get("_affiliate_networks", {})
    if comp in aff_links:
        btn_key = f"aff_{key_suffix}_{row.name}_{random.randint(0, 9999)}"
        st.link_button(f"🔥 Book via {comp}", aff_links[comp], type="primary", use_container_width=True, key=btn_key)
        return True
    return False

def render_ad_grid(widgets, cols=3):
    if not widgets: return
    rows = [widgets[i:i + cols] for i in range(0, len(widgets), cols)]
    for row in rows:
        st_cols = st.columns(cols)
        for idx, w in enumerate(row):
            with st_cols[idx].container(border=True):
                st.markdown(f"### {w.get('icon', '🔗')} {w['name']}")
                st.write(w.get('desc', ''))
                if w.get('type') == 'html' and 'html_code' in w:
                    components.html(w['html_code'], height=w.get('height', 200), scrolling=True)
                else:
                    st.link_button("Explore Deal", w['link'], use_container_width=True, key=f"grid_{w['name']}_{idx}_{random.randint(0, 9999)}")

def render_vip_banner(config):
    paid_ads = config.get("_paid_ads", [])
    if paid_ads:
        ad = random.choice(paid_ads)
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"### 🚀 VIP Deal: {ad['name']}")
            c1.write(ad['desc'])
            c2.link_button("Claim Now", ad['link'], type="primary", use_container_width=True, key=f"vip_{random.randint(0, 9999)}")

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
    for i in range(25): add_fact(lambda: f"💡 Market insight #{i+10} generated for {city}." if lang=="English" else f"💡 رؤية سوقية #{i+10} تم توليدها لـ {city}.")
    return facts

# ======================================================================================
# --- MAIN APP ---
# ======================================================================================
st.set_page_config(page_title="Hotel Analytics", page_icon="🏨", layout="wide")

def main():
    config = load_config()
    settings = config.get("_settings", {"public_access": False, "default_landing_page": "🌍 Country Comparison"})
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'admin_login_mode' not in st.session_state: st.session_state.admin_login_mode = False
    
    if not st.session_state.logged_in and settings.get("public_access", False) and not st.session_state.admin_login_mode:
        st.session_state.logged_in, st.session_state.username = True, "Public_Visitor"
        st.session_state.role, st.session_state.is_public = "blogger", True
        st.session_state.allowed_pages = ["comparison", "dashboard", "fun_facts", "guide", "trends", "tracker", "deals", "hot_deal", "partners", "location", "competitor", "custom_compare"]
        if 'current_page' not in st.session_state:
            st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")

    if not st.session_state.logged_in:
        st.title("🏨 Hotel Analytics Pro V45")
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
                            st.session_state.is_public, st.session_state.admin_login_mode = False, False
                            st.session_state.current_page = settings.get("default_landing_page", "🌍 Country Comparison")
                            update_last_login(u); st.rerun()
                else: st.error("❌ Invalid Credentials")
            if st.session_state.admin_login_mode:
                if st.button("Back to Public Mode"): st.session_state.admin_login_mode = False; st.rerun()
        return

    page_map = {
        "comparison": "🌍 Country Comparison", "dashboard": "📊 Dashboard",
        "hot_deal": "⭐ Hotel of the Day", "trends": "📈 Market Intelligence",
        "rankings": "🏆 Rankings", "tracker": "🔥 Deal Radar",
        "fun_facts": "🎉 Fun Facts", "location": "📍 By Location",
        "competitor": "⚔️ Competitor Analysis", "guide": "🧭 Traveler Guide & Ads",
        "deals": "🎁 Exclusive Deals", "custom_compare": "🎯 Custom Hotel Compare",
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

    st.sidebar.title(f"🚀 {st.session_state.username}")
    if st.session_state.get("is_public", False): 
        if st.sidebar.button("🔐 Admin Login"):
            st.session_state.logged_in, st.session_state.is_public, st.session_state.admin_login_mode = False, False, True
            st.rerun()
    
    # VIP Banner at the top of all pages
    render_vip_banner(config)

    city = None
    if selected_page not in ["🌍 Country Comparison", "⚙️ Admin Control Panel", "🤝 Partners Marketplace", "🎁 Exclusive Deals", "⭐ Hotel of the Day"]:
        city = st.sidebar.selectbox("Select City", list(CITIES_DATA.keys()))
        data_mode = st.sidebar.radio("Data Filter", ["All Recorded Data", "Latest Snapshot Only"])
        st.sidebar.markdown("---")
        st.sidebar.subheader("💡 Essential Services")
        widgets = config.get("_affiliate_widgets", [])
        for w in widgets[:3]:
            with st.sidebar.container(border=True):
                st.markdown(f"**{w.get('icon','🔗')} {w['name']}**")
                st.caption(w.get('desc',''))
                st.link_button("Check Deal", w['link'], use_container_width=True, key=f"side_{w['name']}")

    # --- PAGES ---
    if selected_page == "🌍 Country Comparison":
        st.title("🌍 Global Market Comparison")
        all_city_stats = []
        for c, info in CITIES_DATA.items():
            c_df, c_map, _ = load_data(c)
            if c_df is not None:
                all_city_stats.append({
                    "City": f"{info['emoji']} {c}", "Avg Price": c_df['Best_Price'].mean(),
                    "Avg Rating": c_df['Rate_Val'].mean(), "Unique Hotels": c_df[c_map['Hotel']].nunique(),
                    "Optimal Booking": round(c_df['days_before'].mean()) if not pd.isnull(c_df['days_before'].mean()) else 0
                })
        if all_city_stats:
            stats_df = pd.DataFrame(all_city_stats)
            c1, c2, c3 = st.columns(3)
            c1.metric("💰 Best Value City", stats_df.loc[stats_df['Avg Price'].idxmin(), 'City'])
            c2.metric("🌟 Quality Hub", stats_df.loc[stats_df['Avg Rating'].idxmax(), 'City'])
            c3.metric("📅 Early Booking Tip", f"{int(stats_df['Optimal Booking'].mean())} Days")
            st.markdown("---")
            st.plotly_chart(px.bar(stats_df, x='City', y='Avg Price', color='City', title="Average Market Price ($)"), use_container_width=True)
            st.subheader("💡 Traveler Essentials")
            render_ad_grid(config.get("_affiliate_widgets", []), cols=3)

    elif selected_page == "⭐ Hotel of the Day":
        st.title("⭐ Hotel of the Day")
        city_for_deal = st.selectbox("Select City for Deals", list(CITIES_DATA.keys()))
        df, col_map, err = load_data(city_for_deal)
        if df is not None:
            latest_b = df[col_map['BookingDate']].dropna().max()
            latest_df = df[df[col_map['BookingDate']] == latest_b].copy()
            best_deal = latest_df.sort_values('Value_Score', ascending=False).head(1).iloc[0]
            with st.container(border=True):
                st.markdown(f"<h1 style='text-align: center; color: #FFD700;'>🏆 Today's Top Pick in {city_for_deal}</h1>", unsafe_allow_html=True)
                st.markdown(f"<h2 style='text-align: center;'>🏨 {best_deal[col_map['Hotel']]}</h2>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns(3)
                c1.metric("Rating", f"{best_deal['Rate_Val']}/10")
                c2.metric("Stars", f"{int(best_deal['Star'])} ⭐")
                c3.metric("Current Price", f"${best_deal['Best_Price']:.0f}")
                st.markdown("---")
                st.write(f"📍 **Location:** {best_deal[col_map['Location']]}")
                st.write(f"📝 **Description:** {best_deal[col_map['Desc']]}")
                render_affiliate_button(best_deal, col_map, config, "hot_deal")

    elif selected_page == "🎁 Exclusive Deals":
        st.title("🎁 Exclusive Traveler Deals")
        st.info("🔥 Hand-picked travel essentials with exclusive discounts (Affiliates).")
        render_ad_grid(config.get("_affiliate_widgets", []), cols=3)

    elif selected_page == "🤝 Partners Marketplace":
        st.title("🤝 Partners Marketplace")
        st.info("📍 Specific sponsors and local partners in each city.")
        spons_data = config.get("_sponsors", {})
        for loc, sps in spons_data.items():
            st.subheader(f"📍 {loc}")
            cols = st.columns(3)
            for idx, sp in enumerate(sps):
                with cols[idx % 3].container(border=True):
                    st.markdown(f"### {sp['name']}")
                    st.write(sp['desc'])
                    st.link_button("Visit Partner", sp['link'], key=f"partner_{loc}_{idx}")

    elif selected_page == "⚙️ Admin Control Panel":
        st.title("⚙️ Admin Control Panel")
        tab1, tab2, tab3, tab4 = st.tabs(["👤 Users", "🔧 Settings", "📈 Usage Stats", "🔍 Diagnostics"])
        with tab1:
            user_list = {k:v for k,v in config.items() if k not in ["_settings", "_sponsors", "_stats", "_affiliate_networks", "_affiliate_widgets", "_travel_tips", "_paid_ads"]}
            st.dataframe(pd.DataFrame.from_dict(user_list, orient='index').reset_index().rename(columns={'index':'User'}), hide_index=True)
        with tab2:
            settings["public_access"] = st.toggle("🔓 Public Access", value=settings.get("public_access", False))
            settings["default_landing_page"] = st.selectbox("Landing Page", list(page_map.values()), index=list(page_map.values()).index(settings.get("default_landing_page")))
            if st.button("Save Settings"): config["_settings"] = settings; save_config(config); st.success("Updated!"); st.rerun()
        with tab3:
            stats = config.get("_stats", {"daily": {}, "total": {}})
            summary = []
            for p in page_map.values():
                summary.append({"Page": p, "Today": stats["daily"].get(datetime.now().strftime("%Y-%m-%d"), {}).get(p, 0), "Yesterday": stats["daily"].get((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), {}).get(p, 0), "Total": stats["total"].get(p, 0)})
            df_summary = pd.DataFrame(summary)
            if not df_summary.empty:
                totals = pd.DataFrame([{"Page": "🏁 TOTAL", "Today": df_summary["Today"].sum(), "Yesterday": df_summary["Yesterday"].sum(), "Total": df_summary["Total"].sum()}])
                df_summary = pd.concat([df_summary, totals], ignore_index=True)
            st.dataframe(df_summary, hide_index=True, use_container_width=True)
        with tab4:
            st.subheader("Config Diagnostics")
            if st.session_state.get('config_error'): st.error(st.session_state['config_error'])
            else: st.success("✅ config_users.json loaded successfully.")
            st.json(config.get('_affiliate_widgets', []))

    else:
        df, col_map, err = load_data(city)
        if err: st.warning(f"⚠️ {err}"); return
        if st.sidebar.radio("Snapshot", ["All Data", "Latest Only"], key="snap") == "Latest Only":
            latest_b = df[col_map['BookingDate']].dropna().max()
            df = df[df[col_map['BookingDate']] == latest_b]

        if selected_page == "📊 Dashboard":
            st.markdown(f"### 📊 {city} Market Hub")
            c1, c2, c3 = st.columns(3)
            c1.metric("Avg Price", f"${df['Best_Price'].mean():.0f}")
            c2.metric("Unique Hotels", df[col_map['Hotel']].nunique())
            c3.metric("Top Quality", f"{df['Rate_Val'].max():.1f}")
            
            # Contextual Sponsors on Dashboard
            city_sponsors = config.get("_sponsors", {}).get(city, [])
            if city_sponsors:
                st.markdown("---")
                st.subheader(f"🤝 Recommended Partners in {city}")
                render_ad_grid(city_sponsors, cols=3)
            
            st.markdown("---")
            st.subheader("🔥 Top Deals Right Now")
            top_3 = df.sort_values('Value_Score', ascending=False).head(3)
            d_cols = st.columns(3)
            for idx, (_, row) in enumerate(top_3.iterrows()):
                with d_cols[idx].container(border=True):
                    st.markdown(f"**{row[col_map['Hotel']]}**")
                    st.write(f"💰 ${row['Best_Price']:.0f} | ⭐ {row['Rate_Val']}/10")
                    render_affiliate_button(row, col_map, config, f"dash_{idx}")

        elif selected_page == "📈 Market Intelligence":
            st.markdown("### 📈 Market Trends")
            day_stats = df.groupby(col_map['ArrivalDay'])['Best_Price'].agg(['mean', 'min', 'count']).reset_index()
            day_stats.columns = ['Arrival Day', 'Avg Price ($)', 'Min Price ($)', 'Offers']
            st.dataframe(day_stats.sort_values('Avg Price ($)'), hide_index=True, use_container_width=True)

        elif selected_page == "🔥 Deal Radar":
            st.markdown("### 🔥 Price Drop Radar")
            latest_b = df[col_map['BookingDate']].dropna().max()
            latest_df = df[df[col_map['BookingDate']] == latest_b].copy()
            historical_data = df[df[col_map['BookingDate']] < latest_b]
            if not historical_data.empty:
                hist_avg = historical_data.groupby([col_map['Hotel'], col_map['ArrivalDay']])['Best_Price'].mean().reset_index()
                hist_avg.columns = [col_map['Hotel'], col_map['ArrivalDay'], 'Hist_Avg']
                latest_df = latest_df.merge(hist_avg, on=[col_map['Hotel'], col_map['ArrivalDay']], how='left')
                latest_df['Price_Drop'] = latest_df['Hist_Avg'] - latest_df['Best_Price']
                latest_df['Drop_Pct'] = (latest_df['Price_Drop'] / latest_df['Hist_Avg']) * 100
                drops = latest_df[latest_df['Price_Drop'] > 0].sort_values('Price_Drop', ascending=False).head(15)
            else:
                drops = latest_df.sort_values('Value_Score', ascending=False).head(15).copy()
                drops['Hist_Avg'] = float('nan'); drops['Price_Drop'] = 0.0; drops['Drop_Pct'] = 0.0
            
            for _, row in drops.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.markdown(f"**{row[col_map['Hotel']]}**")
                    if pd.notnull(row['Hist_Avg']): c2.markdown(f"~~${row['Hist_Avg']:.0f}~~ → **${row['Best_Price']:.0f}**")
                    else: c2.markdown(f"Price: **${row['Best_Price']:.0f}**")
                    with c3: render_affiliate_button(row, col_map, config, "radar")

        elif selected_page == "🏆 Rankings":
            st.markdown("### 🏆 Top Rated Hotels")
            df_u = df.sort_values(['Rate_Val', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=[col_map['Hotel']])
            for s in [5, 4, 3]:
                st.markdown(f"#### ⭐ {s} Star")
                stars_df = df_u[df_u['Star'] == s].head(5)
                for _, row in stars_df.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"**{row[col_map['Hotel']]}** | 🌟 {row['Rate_Val']}/10")
                        c1.write(f"💰 Best Price: ${row['Best_Price']:.0f}")
                        with c2: render_affiliate_button(row, col_map, config, "rank")

        elif selected_page == "🎉 Fun Facts":
            st.markdown("### 🎉 Fun Facts")
            lang = st.radio("Language", ["English", "Arabic"], horizontal=True)
            facts = generate_fun_facts(df, col_map, city, lang)
            cols = st.columns(2)
            for i, fact in enumerate(facts): cols[i % 2].success(fact)

        elif selected_page == "📍 By Location":
            st.markdown("### 📍 Location History")
            loc_col = col_map['Location']
            valid_locs = df[loc_col].dropna().unique()
            if len(valid_locs) > 0:
                loc = st.selectbox("Area", valid_locs)
                loc_df = df[df[loc_col] == loc].copy()
                loc_df['Booking Company'] = loc_df.apply(lambda r: get_booking_company(r, col_map), axis=1)
                st.dataframe(loc_df[[col_map['Hotel'], 'Best_Price', 'Star', 'Rate_Val', 'Booking Company', col_map['BookingDate'], col_map['ArrivalDay']]].sort_values('Best_Price'), hide_index=True)
            else: st.info("No location data found.")

        elif selected_page == "⚔️ Competitor Analysis":
            st.markdown("### ⚔️ Competitor Intelligence")
            h_col = col_map['Hotel']
            hotel_list = df[h_col].dropna().unique()
            if len(hotel_list) > 0:
                hotel = st.selectbox("Hotel", hotel_list)
                target = df[df[h_col] == hotel].iloc[0]
                with st.container(border=True):
                    st.subheader(f"🏨 {hotel} | ${target['Best_Price']:.0f}")
                    st.write(f"⭐ {target['Star']} Stars | 📍 {target[col_map['Location']]}")
                comps = df[df[h_col] != hotel].copy()
                loc_col = col_map['Location']
                if pd.notnull(target[loc_col]) and str(target[loc_col]) != "":
                    comps = comps[comps[loc_col] == target[loc_col]]
                else:
                    comps = comps[comps['Star'] == target['Star']]
                comps['Booking Company'] = comps.apply(lambda r: get_booking_company(r, col_map), axis=1)
                st.dataframe(comps[[h_col, 'Best_Price', 'Booking Company', 'Rate_Val', 'Star', col_map['ArrivalDay']]].sort_values('Best_Price'), hide_index=True)

        elif selected_page == "🧭 Traveler Guide & Ads":
            st.title("🧭 Traveler Guide")
            tab_val, tab_search = st.tabs(["💎 Best Value", "🔍 Feature Search"])
            with tab_val:
                top_val = df.sort_values('Value_Score', ascending=False).head(10)
                for _, row in top_val.iterrows():
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"**{row[col_map['Hotel']]}** | 📍 {row[col_map['Location']]}")
                        c1.write(f"💰 ${row['Best_Price']:.0f} | ⭐ {row['Rate_Val']}/10")
                        with c2: render_affiliate_button(row, col_map, config, "guide")
            with tab_search:
                search = st.text_input("Search (e.g. 'View', 'Pool')")
                if search:
                    res = df[df[col_map['Desc']].str.contains(search, case=False, na=False)]
                    for _, row in res.head(10).iterrows():
                        with st.container(border=True):
                            c1, c2 = st.columns([3, 1])
                            c1.markdown(f"**{row[col_map['Hotel']]}** | ${row['Best_Price']:.0f}")
                            with c2: render_affiliate_button(row, col_map, config, "search")
            st.markdown("---")
            st.subheader("💡 Recommended Services")
            render_ad_grid(config.get("_affiliate_widgets", []), cols=3)

        elif selected_page == "🎯 Custom Hotel Compare":
            st.markdown("### 🎯 Custom Comparison")
            selected_cities = st.multiselect("1. Select Cities", list(CITIES_DATA.keys()))
            if selected_cities:
                comparison_data = []
                for c in selected_cities:
                    c_df, c_map, _ = load_data(c)
                    if c_df is not None:
                        h_col = c_map['Hotel']
                        hotel_options = c_df[h_col].dropna().unique()
                        sel_hotels = st.multiselect(f"2. Select Hotels in {c}", hotel_options, key=f"sel_{c}")
                        if sel_hotels:
                            sub = c_df[c_df[h_col].isin(sel_hotels)].copy()
                            for name in sel_hotels:
                                h_data = sub[sub[h_col] == name]
                                if not h_data.empty:
                                    comparison_data.append({"City": c, "Hotel": name, "Best Price ($)": h_data['Best_Price'].min(), "Stars": h_data.iloc[-1]['Star'], "Rate": h_data.iloc[-1]['Rate_Val'], "Location": h_data.iloc[-1][c_map['Location']]})
                if comparison_data: st.dataframe(pd.DataFrame(comparison_data), hide_index=True, use_container_width=True)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in, st.session_state.is_public, st.session_state.admin_login_mode = False, False, False
        st.rerun()

if __name__ == "__main__": main()
