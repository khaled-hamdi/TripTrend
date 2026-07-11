# ======================================================================================
# --- CONFIGURATION FILE FOR HOTEL ANALYTICS APP ---
# --- يمكنك تعديل هذا الملف لإضافة مستخدمين جدد أو مدن جديدة ---
# ======================================================================================

# ==================== USERS CONFIGURATION ====================
# Format: "username": "password"
# يمكنك إضافة أي عدد من المستخدمين بأسماء متغيرة

USERS = {
    "test1": "password123",           # Demo user
    "admin": "admin123",              # Admin user
    "company_a": "company@123",       # Company A
    "company_b": "company@456",       # Company B
    "blogger_pro": "blogger2024",     # Blogger
    "travel_agency": "travel@2024",   # Travel Agency
    "hotel_manager": "hotel@2024",    # Hotel Manager
    "investor": "investor@2024"       # Investor
}

# ==================== CITIES CONFIGURATION ====================
# Format: "City_Name": {
#     "file": "paris 10-7.xlsx",
#     "emoji": "🏙️",
#     "country": "Country Name"
# }

CITIES = {
    "Paris": {
        "file": "paris 10-7.xlsx",
        "emoji": "🗼",
        "country": "France",
        "description": "The City of Light - Luxury Hotels & Budget Options"
    },
    "Dubai": {
        "file": "paris 10-7.xlsx",
        "emoji": "🏙️",
        "country": "UAE",
        "description": "Luxury Desert Destination - Premium Hotels"
    },
    "Istanbul": {
        "file": "paris 10-7.xlsx",
        "emoji": "🕌",
        "country": "Turkey",
        "description": "Bridge Between Continents - Historic & Modern Hotels"
    },
    "Cairo": {
        "file": "paris 10-7.xlsx",
        "emoji": "🏛️",
        "country": "Egypt",
        "description": "Ancient Wonders - Cultural Hub Hotels"
    },
    "New York": {
        "file": "paris 10-7.xlsx",
        "emoji": "🗽",
        "country": "USA",
        "description": "The City That Never Sleeps - Diverse Hotel Options"
    },
    "Tokyo": {
        "file": "paris 10-7.xlsx",
        "emoji": "🗾",
        "country": "Japan",
        "description": "Modern Metropolis - High-Tech Hotels"
    },
    "London": {
        "file": "paris 10-7.xlsx",
        "emoji": "🎡",
        "country": "UK",
        "description": "Historic Capital - Elegant Hotels"
    },
    "Barcelona": {
        "file": "paris 10-7.xlsx",
        "emoji": "🏖️",
        "country": "Spain",
        "description": "Mediterranean Beauty - Beach & City Hotels"
    }
}

# ==================== APP SETTINGS ====================
APP_NAME = "Hotel Analytics Pro"
APP_DESCRIPTION = "Professional Hotel Data Intelligence Platform"
APP_VERSION = "1.0.0"

# Theme Colors
COLORS = {
    "primary": "#667eea",
    "secondary": "#764ba2",
    "success": "#27ae60",
    "danger": "#e74c3c",
    "warning": "#f39c12",
    "info": "#3498db"
}

# ==================== HOW TO ADD NEW USERS ====================
# 1. Open this file (config.py)
# 2. Add a new line in the USERS dictionary:
#    "new_username": "new_password"
# 3. Save the file
# 4. Restart the Streamlit app
# Example:
#    "company_c": "company@789"

# ==================== HOW TO ADD NEW CITIES ====================
# 1. Prepare your Excel file with hotel data (same structure as Paris data)
# 2. Place it in the same directory as the app
# 3. Add a new entry in the CITIES dictionary:
#    "City_Name": {
#        "file": "city_hotels.xlsx",
#        "emoji": "🏙️",
#        "country": "Country Name",
#        "description": "City Description"
#    }
# 4. Save this file
# 5. Restart the Streamlit app

# ==================== DATA STRUCTURE REQUIREMENTS ====================
# Your Excel file should have these columns:
# - Hotel_Name: Name of the hotel
# - Price1, price2, price3: Prices from different sources
# - Rate: Hotel rating (1-10)
# - Star: Star category (1-5)
# - date of creat booking: Date when booking was made
# - date of arrival: Expected arrival date
# - Desc, Desc2, Note 1, Note 2, Note 3: Hotel descriptions/amenities
# - day of arrival: Day of the week for arrival
# - day of book: Day of the week for booking
# - Place1, place3: Hotel location information
# - Distance From places: Distance from landmarks
