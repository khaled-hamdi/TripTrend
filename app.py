import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import hashlib

# ======================================================================================
# --- PAGE CONFIG & THEME ---
# ======================================================================================
st.set_page_config(
    page_title="Hotel Analytics Pro | تحليلات الفنادق الاحترافية",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 30px;
    }
    h2 {
        color: #34495e;
        border-bottom: 3px solid #667eea;
        padding-bottom: 10px;
    }
    .booking-platform {
        background: #f8f9fa;
        padding: 10px;
        border-left: 4px solid #667eea;
        margin: 5px 0;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# ======================================================================================
# --- USER CREDENTIALS (قاعدة بيانات المستخدمين) ---
# ======================================================================================
USERS_DB = {
    "test1": "password123",
    "admin": "admin123",
    "company_a": "company@123",
    "blogger_pro": "blogger2024",
    "travel_agency": "travel@2024"
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_login(username, password):
    if username in USERS_DB:
        return USERS_DB[username] == password
    return False

# ======================================================================================
# --- CITIES DATA MAPPING (ربط المدن بالبيانات) ---
# ======================================================================================
CITIES_DATA = {
    "Paris": {"file": "subjectsanalysis.xlsx", "emoji": "🗼", "country": "France"},
    "Dubai": {"file": "dubai_hotels.xlsx", "emoji": "🏙️", "country": "UAE"},
    "Istanbul": {"file": "istanbul_hotels.xlsx", "emoji": "🕌", "country": "Turkey"},
    "Cairo": {"file": "cairo_hotels.xlsx", "emoji": "🏛️", "country": "Egypt"},
    "New York": {"file": "newyork_hotels.xlsx", "emoji": "🗽", "country": "USA"}
}

# ======================================================================================
# --- DATA LOADING & PROCESSING ---
# ======================================================================================
@st.cache_data
def load_and_process_data(file_path):
    try:
        df = pd.read_excel(file_path)
        
        # Clean Prices
        for col in ['Price1', 'price2', 'price3']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce')
        
        df['Best_Price'] = df[['Price1', 'price2', 'price3']].min(axis=1)
        df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce')
        df['Star'] = pd.to_numeric(df['Star'], errors='coerce')
        
        # Handle Dates
        df['booking_date_dt'] = pd.to_datetime(df['date of creat booking'], errors='coerce')
        df['arrival_date_dt'] = pd.to_datetime(df['date of arrival'], errors='coerce')
        df['Arrival_Month'] = df['arrival_date_dt'].dt.strftime('%B')
        df['Arrival_Day_Name'] = df['arrival_date_dt'].dt.strftime('%A')
        
        # Extract Amenities
        df['All_Text'] = (df['Desc'].fillna('') + " " + df['Desc2'].fillna('') + " " + 
                          df['Note 1'].fillna('') + " " + df['Note 2'].fillna('') + " " + df['Note 3'].fillna('')).str.lower()
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None

# ======================================================================================
# --- LOGIN PAGE ---
# ======================================================================================
def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("---")
        st.markdown("<h1>🏨 Hotel Analytics Pro</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #667eea;'>تحليلات الفنادق الاحترافية</h3>", unsafe_allow_html=True)
        st.markdown("---")
        
        st.markdown("<h4 style='text-align: center;'>Professional Hotel Data Intelligence</h4>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #7f8c8d;'>Unlock hotel market insights | اكتشف أسرار سوق الفنادق</p>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        username = st.text_input("👤 Username", placeholder="Enter your username")
        password = st.text_input("🔐 Password", type="password", placeholder="Enter your password")
        
        if st.button("🚀 Login", use_container_width=True):
            if verify_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success(f"✅ Welcome {username}!")
                st.rerun()
            else:
                st.error("❌ Invalid username or password!")
        
        st.markdown("---")
        st.markdown("<p style='text-align: center; font-size: 12px; color: #95a5a6;'>Demo Credentials:<br>test1/password123 | admin/admin123</p>", unsafe_allow_html=True)

# ======================================================================================
# --- MAIN DASHBOARD ---
# ======================================================================================
def show_dashboard():
    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.markdown(f"### 👤 Welcome, **{st.session_state.username}**")
    with col3:
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.rerun()
    
    st.markdown("---")
    
    # City Selection
    st.markdown("### 🌍 Select Your City | اختر المدينة")
    selected_city = st.selectbox(
        "Choose a city to analyze:",
        list(CITIES_DATA.keys()),
        format_func=lambda x: f"{CITIES_DATA[x]['emoji']} {x} - {CITIES_DATA[x]['country']}"
    )
    
    # Load data
    file_path = CITIES_DATA[selected_city]['file']
    df = load_and_process_data(file_path)
    
    if df is None:
        st.warning(f"⚠️ Data file for {selected_city} not found. Using sample data.")
        return
    
    st.success(f"✅ Loaded {len(df)} records for {selected_city}")
    st.markdown("---")
    
    # ==================== TABS ====================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Dashboard",
        "💎 Market Extremes",
        "📈 Trends & Seasonality",
        "🏆 Top Rankings",
        "🔍 Hotel Tracker"
    ])
    
    # ==================== TAB 1: DASHBOARD ====================
    with tab1:
        st.markdown("### 📊 Market Overview | نظرة عامة على السوق")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📍 Total Hotels", len(df['Hotel_Name'].unique()), delta="Hotels in database")
        with col2:
            st.metric("💰 Avg Price", f"${df['Best_Price'].mean():.0f}", delta=f"${df['Best_Price'].std():.0f} std dev")
        with col3:
            st.metric("⭐ Avg Rating", f"{df['Rate'].mean():.1f}", delta="out of 10")
        with col4:
            st.metric("🌟 Avg Stars", f"{df['Star'].mean():.1f}", delta="stars")
        
        st.markdown("---")
        
        # Price Distribution Chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 💵 Price Distribution")
            fig_price = px.histogram(df, x='Best_Price', nbins=30, title="Price Distribution",
                                     labels={'Best_Price': 'Price ($)', 'count': 'Number of Hotels'},
                                     color_discrete_sequence=['#667eea'])
            fig_price.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_price, use_container_width=True)
        
        with col2:
            st.markdown("### ⭐ Rating Distribution")
            fig_rating = px.histogram(df, x='Rate', nbins=20, title="Rating Distribution",
                                      labels={'Rate': 'Rating', 'count': 'Number of Hotels'},
                                      color_discrete_sequence=['#764ba2'])
            fig_rating.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig_rating, use_container_width=True)
        
        # Star Category Breakdown
        st.markdown("### 🏨 Hotels by Star Category")
        star_counts = df['Star'].value_counts().sort_index(ascending=False)
        fig_stars = px.bar(x=star_counts.index, y=star_counts.values, 
                          labels={'x': 'Star Rating', 'y': 'Number of Hotels'},
                          title="Hotel Distribution by Stars",
                          color_discrete_sequence=['#667eea'])
        fig_stars.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_stars, use_container_width=True)
    
    # ==================== TAB 2: MARKET EXTREMES (WITH BOOKING PLATFORMS) ====================
    with tab2:
        st.markdown("### 💎 Market Extremes | أبطال السوق")
        
        abs_cheapest = df.loc[df['Best_Price'].idxmin()]
        abs_expensive = df.loc[df['Best_Price'].idxmax()]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🟢 Cheapest Deal Ever | أرخص صفقة")
            st.info(f"""
            **Hotel:** {abs_cheapest['Hotel_Name']}
            **Price:** ${abs_cheapest['Best_Price']:.0f}
            **Rating:** {abs_cheapest['Rate']} ⭐
            **Stars:** {abs_cheapest['Star']} 🌟
            **Arrival:** {abs_cheapest['arrival_date_dt'].strftime('%d %B %Y') if pd.notnull(abs_cheapest['arrival_date_dt']) else 'N/A'}
            **Day:** {abs_cheapest['Arrival_Day_Name']}
            """)
            
            # Booking Platforms for Cheapest
            st.markdown("#### 🔗 Booking Platforms | منصات الحجز:")
            if pd.notnull(abs_cheapest['Place1']):
                st.markdown(f"""<div class='booking-platform'>
                <strong>Primary Platform:</strong> {abs_cheapest['Place1']}
                </div>""", unsafe_allow_html=True)
            if pd.notnull(abs_cheapest['place3']):
                st.markdown(f"""<div class='booking-platform'>
                <strong>Alternative Platform:</strong> {abs_cheapest['place3']}
                </div>""", unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 🔴 Most Expensive Record | أغلى سعر")
            st.warning(f"""
            **Hotel:** {abs_expensive['Hotel_Name']}
            **Price:** ${abs_expensive['Best_Price']:.0f}
            **Rating:** {abs_expensive['Rate']} ⭐
            **Stars:** {abs_expensive['Star']} 🌟
            **Arrival:** {abs_expensive['arrival_date_dt'].strftime('%d %B %Y') if pd.notnull(abs_expensive['arrival_date_dt']) else 'N/A'}
            **Day:** {abs_expensive['Arrival_Day_Name']}
            """)
            
            # Booking Platforms for Most Expensive
            st.markdown("#### 🔗 Booking Platforms | منصات الحجز:")
            if pd.notnull(abs_expensive['Place1']):
                st.markdown(f"""<div class='booking-platform'>
                <strong>Primary Platform:</strong> {abs_expensive['Place1']}
                </div>""", unsafe_allow_html=True)
            if pd.notnull(abs_expensive['place3']):
                st.markdown(f"""<div class='booking-platform'>
                <strong>Alternative Platform:</strong> {abs_expensive['place3']}
                </div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Price Range Analysis
        st.markdown("### 📊 Price Range Comparison")
        price_stats = {
            'Metric': ['Minimum', 'Maximum', 'Average', 'Median', 'Std Dev'],
            'Price ($)': [
                f"${df['Best_Price'].min():.0f}",
                f"${df['Best_Price'].max():.0f}",
                f"${df['Best_Price'].mean():.0f}",
                f"${df['Best_Price'].median():.0f}",
                f"${df['Best_Price'].std():.0f}"
            ]
        }
        st.dataframe(pd.DataFrame(price_stats), use_container_width=True)
    
    # ==================== TAB 3: TRENDS & SEASONALITY ====================
    with tab3:
        st.markdown("### 📈 Market Trends & Seasonality | الاتجاهات والمواسم")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📅 Monthly Trends")
            monthly_avg = df.groupby('Arrival_Month')['Best_Price'].mean().sort_values()
            fig_monthly = px.bar(x=monthly_avg.index, y=monthly_avg.values,
                                labels={'x': 'Month', 'y': 'Average Price ($)'},
                                title="Average Price by Month",
                                color_discrete_sequence=['#667eea'])
            fig_monthly.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_monthly, use_container_width=True)
        
        with col2:
            st.markdown("### 📆 Day of Week Trends")
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            daily_avg = df.groupby('Arrival_Day_Name')['Best_Price'].mean().reindex(day_order)
            fig_daily = px.bar(x=daily_avg.index, y=daily_avg.values,
                              labels={'x': 'Day', 'y': 'Average Price ($)'},
                              title="Average Price by Day of Week",
                              color_discrete_sequence=['#764ba2'])
            fig_daily.update_layout(height=400, xaxis_tickangle=-45)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        st.markdown("---")
        
        # Insights
        col1, col2 = st.columns(2)
        with col1:
            best_month = monthly_avg.idxmin()
            worst_month = monthly_avg.idxmax()
            st.success(f"✅ **Cheapest Month:** {best_month} (${monthly_avg.min():.0f})")
            st.error(f"❌ **Most Expensive Month:** {worst_month} (${monthly_avg.max():.0f})")
        
        with col2:
            best_day = daily_avg.idxmin()
            worst_day = daily_avg.idxmax()
            st.success(f"✅ **Cheapest Day:** {best_day} (${daily_avg.min():.0f})")
            st.error(f"❌ **Most Expensive Day:** {worst_day} (${daily_avg.max():.0f})")
    
    # ==================== TAB 4: TOP RANKINGS ====================
    with tab4:
        st.markdown("### 🏆 Top Rankings | أفضل الفنادق")
        
        df_unique = df.sort_values(['Rate', 'Best_Price'], ascending=[False, True]).drop_duplicates(subset=['Hotel_Name'])
        
        for star in [5, 4, 3]:
            st.markdown(f"### ⭐ Top 5 Hotels - {star} Stars")
            top_hotels = df_unique[df_unique['Star'] == star].head(5)
            
            if not top_hotels.empty:
                for i, (idx, row) in enumerate(top_hotels.iterrows(), 1):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric(f"#{i}", row['Hotel_Name'][:20], f"${row['Best_Price']:.0f}")
                    with col2:
                        st.metric("Rating", f"{row['Rate']}", "⭐")
                    with col3:
                        st.metric("Stars", f"{row['Star']}", "🌟")
                    with col4:
                        st.metric("Price", f"${row['Best_Price']:.0f}", "USD")
            else:
                st.info(f"No {star}-star hotels available")
            st.markdown("---")
    
    # ==================== TAB 5: HOTEL TRACKER (WITH BOOKING PLATFORMS) ====================
    with tab5:
        st.markdown("### 🔍 Track Specific Hotel | تتبع فندق محدد")
        
        hotel_names = sorted(df['Hotel_Name'].unique())
        selected_hotel = st.selectbox("Select a hotel to track:", hotel_names)
        
        hotel_data = df[df['Hotel_Name'] == selected_hotel]
        
        if not hotel_data.empty:
            cheapest = hotel_data.loc[hotel_data['Best_Price'].idxmin()]
            expensive = hotel_data.loc[hotel_data['Best_Price'].idxmax()]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🟢 Cheapest Record")
                st.info(f"""
                **Price:** ${cheapest['Best_Price']:.0f}
                **Date:** {cheapest['arrival_date_dt'].strftime('%d %B %Y') if pd.notnull(cheapest['arrival_date_dt']) else 'N/A'}
                **Day:** {cheapest['Arrival_Day_Name']}
                **Rating:** {cheapest['Rate']} ⭐
                """)
                
                # Booking Platforms
                st.markdown("#### 🔗 Booking Platforms:")
                if pd.notnull(cheapest['Place1']):
                    st.markdown(f"""<div class='booking-platform'>
                    <strong>Primary:</strong> {cheapest['Place1']}
                    </div>""", unsafe_allow_html=True)
                if pd.notnull(cheapest['place3']):
                    st.markdown(f"""<div class='booking-platform'>
                    <strong>Alternative:</strong> {cheapest['place3']}
                    </div>""", unsafe_allow_html=True)
            
            with col2:
                st.markdown("### 🔴 Most Expensive Record")
                st.warning(f"""
                **Price:** ${expensive['Best_Price']:.0f}
                **Date:** {expensive['arrival_date_dt'].strftime('%d %B %Y') if pd.notnull(expensive['arrival_date_dt']) else 'N/A'}
                **Day:** {expensive['Arrival_Day_Name']}
                **Rating:** {expensive['Rate']} ⭐
                """)
                
                # Booking Platforms
                st.markdown("#### 🔗 Booking Platforms:")
                if pd.notnull(expensive['Place1']):
                    st.markdown(f"""<div class='booking-platform'>
                    <strong>Primary:</strong> {expensive['Place1']}
                    </div>""", unsafe_allow_html=True)
                if pd.notnull(expensive['place3']):
                    st.markdown(f"""<div class='booking-platform'>
                    <strong>Alternative:</strong> {expensive['place3']}
                    </div>""", unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Price History Chart
            st.markdown("### 📊 Price History")
            hotel_data_sorted = hotel_data.sort_values('arrival_date_dt')
            fig_history = px.line(hotel_data_sorted, x='arrival_date_dt', y='Best_Price',
                                 title=f"Price History - {selected_hotel}",
                                 labels={'arrival_date_dt': 'Date', 'Best_Price': 'Price ($)'},
                                 markers=True)
            fig_history.update_layout(height=400)
            st.plotly_chart(fig_history, use_container_width=True)
        else:
            st.warning("Hotel not found in database")

# ======================================================================================
# --- MAIN APP LOGIC ---
# ======================================================================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = None
    
    if not st.session_state.logged_in:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
