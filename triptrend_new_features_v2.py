from __future__ import annotations

from datetime import datetime
import hashlib
import uuid
import html
import pandas as pd
import streamlit as st

from google_sheets_adapter import read_tab, append_rows, ensure_tab
from triptrend_external_data import external_events, city_prices, external_weather, external_currency, external_flights, city_key

# These tabs are created automatically if the connected native Google Sheet is missing them.
NEW_TAB_HEADERS = {
    "Events": ["Event_ID", "City", "Country", "Event_Name", "Event_Type", "Start_Date", "End_Date", "Location", "Description", "Link_URL", "Image_URL", "Status", "Updated_At"],
    "Travel_Experiences": ["Experience_ID", "Contributor_ID", "Contributor_Name", "City", "Country", "Experience_Type", "Title", "Comment", "Value", "Unit", "Experience_Date", "Submitted_At", "Status", "Likes", "Approved_By"],
    "Traveler_Questions": ["Question_ID", "Contributor_ID", "Name", "City", "Question", "Created_At", "Status", "Likes"],
    "Contributor_Answers": ["Answer_ID", "Question_ID", "Contributor_ID", "Contributor_Name", "Answer", "Created_At", "Status", "Likes", "Helpful_Count"],
    "Contributors": ["Contributor_ID", "Username", "Password_or_Hash", "Display_Name", "Email", "Country", "City", "Contributor_Type", "Bio", "Points", "Level", "Status", "Created_At", "Last_Login", "Recovery_Code"],
    "Contributor_Points_Log": ["Point_ID", "Contributor_ID", "Activity_Type", "Reference_ID", "Points", "Status", "Reason", "Created_At", "Approved_By"],
    "Reward_Tiers": ["Tier_ID", "Tier_Name", "Min_Points", "Reward_Type", "Reward_Description", "Active", "Requires_Approval"],
    "Affiliate_Widgets": ["Widget_ID", "Partner_Name", "Category", "City", "Target_Pages", "Placement", "Widget_Type", "Widget_Code", "Affiliate_URL", "Description", "Priority", "Start_Date", "End_Date", "Status"],
}


def ensure_new_tabs():
    for tab, headers in NEW_TAB_HEADERS.items():
        try:
            ensure_tab(tab, headers)
        except Exception:
            # Public pages must still load if an admin has not yet created the tab.
            pass


def _records(tab: str) -> pd.DataFrame:
    try:
        rows = read_tab(tab)
    except Exception:
        return pd.DataFrame()
    if not rows or len(rows) < 2:
        return pd.DataFrame(columns=NEW_TAB_HEADERS.get(tab, rows[0] if rows else []))
    headers = [str(x).strip() for x in rows[0]]
    width = len(headers)
    return pd.DataFrame([(list(r) + [""] * width)[:width] for r in rows[1:]], columns=headers)


def _truthy(value):
    return str(value).strip().lower() in {"true", "1", "yes", "active", "on", "approved", "featured"}


def _date(value):
    parsed = pd.to_datetime(value, errors="coerce")
    return "" if pd.isna(parsed) else parsed.strftime("%Y-%m-%d")


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _event_rows(city: str) -> pd.DataFrame:
    events = external_events()
    if events.empty:
        events = _records("Events")
    if events.empty:
        return events
    if "Status" in events.columns:
        events = events[events["Status"].astype(str).str.lower().isin(["active", "approved", "featured", ""])].copy()
    if city and "City" in events.columns:
        events = events[events["City"].map(city_key) == city_key(city)]
    return events


def _render_widget(row, key):
    code = str(row.get("Widget_Code", "") or "").strip()
    url = str(row.get("Affiliate_URL", "") or "").strip()
    name = str(row.get("Partner_Name", "Travel Partner"))
    desc = str(row.get("Description", "Useful travel service for your trip."))
    with st.container(border=True):
        st.markdown(f"**{name}**")
        st.caption(desc)
        if code:
            # Streamlit components support HTML/iframe snippets supplied by a trusted admin.
            import streamlit.components.v1 as components
            components.html(code, height=220, scrolling=True)
        elif url.startswith("http"):
            st.link_button("Explore service", url, key=key)


def render_trip_planner(city: str, data_loader, data_mode: str, config: dict):
    st.title(f"🧳 Plan Your Trip: {city}")
    st.caption("A compact city snapshot combining hotel intelligence, events, travel costs, and verified traveler experiences.")
    visit_date = st.date_input("📅 Visit / arrival date", value=datetime.now().date(), key=f"visit_date_{city}")
    df, cmap, err = data_loader(city, data_mode)
    hotel_available = not (err or df is None or df.empty)
    if not hotel_available:
        st.info(err or "Hotel data is not available yet. Showing the available city data below.")
        df = pd.DataFrame()

    prices = pd.to_numeric(df.get("Best_Price", pd.Series(dtype=float)), errors="coerce").dropna()
    hotels_from = prices.min() if not prices.empty else None
    hotel_avg = prices.mean() if not prices.empty else None
    events = _event_rows(city)
    weather = external_weather()
    currency = external_currency()
    city_costs = city_prices()
    food = _records("Food_Prices")
    transport = _records("Transport_Prices")
    flights = external_flights()
    activities = _records("Activities")

    cards = st.columns(4)
    cards[0].metric("🏨 Hotels from", f"${hotels_from:,.0f}" if hotels_from is not None else "N/A")
    cards[1].metric("📊 Typical hotel", f"${hotel_avg:,.0f}" if hotel_avg is not None else "N/A")
    cards[2].metric("📅 Events", int(len(events)))
    cards[3].metric("🧾 Hotel records", int(len(df)) if hotel_available else "N/A")

    st.subheader("Quick Snapshot")
    snapshot = []
    if not flights.empty:
        vals = pd.to_numeric(flights.get("Price", flights.get("Price_From", pd.Series(dtype=float))), errors="coerce").dropna()
        snapshot.append({"Item": "Flights", "Summary": f"From ${vals.min():,.0f}" if not vals.empty else "Data available"})
    if not weather.empty:
        w = weather[weather.get("City", pd.Series(dtype=str)).map(city_key).eq(city_key(city))] if "City" in weather.columns else weather
        if "Forecast_Date" in w.columns:
            chosen = w[w["Forecast_Date"].astype(str).eq(str(visit_date))]
            if not chosen.empty: w = chosen
        if not w.empty:
            r = w.iloc[-1]
            snapshot.append({"Item": "Weather", "Summary": f"High {r.get('Temperature_Max', '—')}° / Low {r.get('Temperature_Min', '—')}°"})
    if not currency.empty:
        valid_currency = currency.dropna(subset=["Dollar"]) if "Dollar" in currency.columns else currency
        snapshot.append({"Item": "Currency", "Summary": f"{len(valid_currency)} currency rates vs USD"})
    if not city_costs.empty:
        city_cost_snapshot = city_costs[city_costs["City"].astype(str).str.casefold().eq(city.casefold())]
        for name, category in [("Food", "restaurant|food"), ("Transport", "transport")]:
            part = city_cost_snapshot[city_cost_snapshot["Category"].astype(str).str.casefold().str.contains(category, na=False)]
            if not part.empty:
                vals = pd.to_numeric(part["Price_Value"], errors="coerce").dropna()
                snapshot.append({"Item": name, "Summary": f"{vals.min():,.2f}–{vals.max():,.2f}" if not vals.empty else "Data available"})
    for name, table, value_col in [("Activities", activities, "Price")]:
        if not table.empty:
            vals = pd.to_numeric(table.get(value_col, table.get("Price_From", pd.Series(dtype=float))), errors="coerce").dropna()
            snapshot.append({"Item": name, "Summary": f"${vals.min():,.0f}–${vals.max():,.0f}" if not vals.empty else "Data available"})
    if snapshot:
        st.dataframe(pd.DataFrame(snapshot), hide_index=True, use_container_width=True)
    else:
        st.info("Additional city information is being collected. You can help by sharing your travel experience.")

    st.subheader("📅 Events in this destination")
    if events.empty:
        st.info("No active events have been added for this city yet.")
    else:
        cols = [c for c in ["Event_Name", "Date", "Event_Date", "Time", "Cost", "City_or_Venue"] if c in events.columns]
        st.dataframe(events[cols].head(20), hide_index=True, use_container_width=True)

    st.subheader("🧾 City price snapshot")
    selected_costs = city_costs[city_costs["City"].map(city_key).eq(city_key(city))] if not city_costs.empty else pd.DataFrame()
    if selected_costs.empty:
        st.info("No city-cost records were found for this destination.")
    else:
        price_cols = [c for c in ["Item_Name", "Raw_Price", "Raw_Range", "Category", "Currency"] if c in selected_costs.columns]
        st.dataframe(selected_costs[price_cols].head(30), hide_index=True, use_container_width=True)

    st.subheader("💰 Trip Cost Calculator — estimated range")
    c1, c2, c3 = st.columns(3)
    nights = c1.slider("Nights", 1, 30, 5)
    travelers = c2.slider("Travelers", 1, 10, 2)
    style = c3.selectbox("Travel style", ["Budget", "Comfort", "Premium"])
    multipliers = {"Budget": (0.75, 1.0), "Comfort": (1.0, 1.45), "Premium": (1.45, 2.25)}
    low_mult, high_mult = multipliers[style]
    base_hotel = (hotel_avg or hotels_from or 100) * nights * max(1, travelers / 2)
    known_ranges = {"Hotels": (base_hotel * low_mult, base_hotel * high_mult)}
    if not city_costs.empty:
        selected_costs = city_costs[city_costs["City"].astype(str).str.casefold().eq(city.casefold())]
        if not selected_costs.empty:
            food = selected_costs[selected_costs["Category"].astype(str).str.casefold().str.contains("restaurant|food", na=False)]
            transport = selected_costs[selected_costs["Category"].astype(str).str.casefold().str.contains("transport", na=False)]
    for key, table in [("Flights", flights), ("Food", food), ("Transport", transport), ("Activities", activities)]:
        vals = pd.to_numeric(table.get("Price", table.get("Price_From", pd.Series(dtype=float))), errors="coerce").dropna() if not table.empty else pd.Series(dtype=float)
        if not vals.empty:
            factor = travelers if key in {"Flights", "Activities"} else nights * travelers
            known_ranges[key] = (vals.min() * factor, vals.max() * factor)
    total_low = sum(x[0] for x in known_ranges.values())
    total_high = sum(x[1] for x in known_ranges.values())
    st.metric("Estimated trip cost", f"${total_low:,.0f} – ${total_high:,.0f}")
    st.caption("This is a range based on available hotel, service, and traveler-contributed data—not a fixed quote.")
    st.dataframe(pd.DataFrame([{"Item": k, "Low": round(v[0]), "High": round(v[1])} for k, v in known_ranges.items()]), hide_index=True, use_container_width=True)

    exp = _records("Travel_Experiences")
    if not exp.empty and "City" in exp.columns:
        exp = exp[exp["City"].astype(str).str.casefold().eq(city.casefold())]
    st.subheader("👥 Traveler Experiences")
    if exp.empty:
        st.info("No approved traveler experiences are available yet.")
    else:
        exp = exp[exp.get("Status", pd.Series("Approved", index=exp.index)).astype(str).str.lower().isin(["approved", "active", "featured"])]
        for i, (_, row) in enumerate(exp.head(10).iterrows()):
            with st.container(border=True):
                st.markdown(f"**{row.get('Contributor_Name', 'Traveler')}** · {row.get('Experience_Date', row.get('Submitted_At', ''))}")
                st.write(str(row.get("Comment", row.get("Title", ""))))
                st.caption(f"{row.get('Experience_Type', 'Travel experience')} · {row.get('City', city)} · ♥ {row.get('Likes', 0)}")

    widgets = _records("Affiliate_Widgets")
    if not widgets.empty:
        widgets = widgets[widgets.get("Status", pd.Series("Active", index=widgets.index)).astype(str).str.lower().isin(["active", "featured", "approved"])]
        widgets = widgets[(widgets.get("City", pd.Series("", index=widgets.index)).astype(str).isin(["", city]))]
        if not widgets.empty:
            st.subheader("Useful for this trip")
            for i, (_, row) in enumerate(widgets.sort_values("Priority", ascending=True).head(3).iterrows()):
                _render_widget(row, f"planner_widget_{i}")


def render_best_dates(city: str, data_loader, data_mode: str):
    st.title(f"📅 Best Dates & Booking Advice — {city}")
    visit_date = st.date_input("📅 Planned arrival date", value=datetime.now().date(), key=f"best_dates_visit_{city}")
    df, cmap, err = data_loader(city, data_mode)
    if err or df is None or df.empty:
        st.warning(err or "Historical hotel data is not available.")
        return
    p = pd.to_numeric(df.get("Best_Price"), errors="coerce")
    valid = df.assign(_price=p).dropna(subset=["_price"])
    if valid.empty:
        st.info("More valid prices are needed for a recommendation.")
        return
    if "arrival_dt" in valid.columns:
        valid["Arrival Day"] = pd.to_datetime(valid["arrival_dt"], errors="coerce").dt.day_name()
    else:
        valid["Arrival Day"] = valid.get(cmap.get("ArrivalDay"), "Unknown")
    by_day = valid.groupby("Arrival Day")['_price'].agg(['mean', 'count']).dropna().sort_values("mean")
    st.subheader("Best Arrival Days")
    if len(by_day) >= 2:
        cheap, expensive = by_day.index[0], by_day.index[-1]
        saving = by_day.iloc[-1]['mean'] - by_day.iloc[0]['mean']
        pct = saving / by_day.iloc[-1]['mean'] * 100 if by_day.iloc[-1]['mean'] else 0
        st.success(f"Historically, **{cheap}** was about ${saving:,.0f} ({pct:.0f}%) cheaper than **{expensive}** in the selected records.")
        st.dataframe(by_day.reset_index().rename(columns={"mean": "Average Price", "count": "Records"}).round(0), hide_index=True, use_container_width=True)
    else:
        st.info(f"More arrival-day history is needed to compare days fairly. Current selection: {visit_date.strftime(chr(37)+chr(65))}.")
    if "days_before" in valid.columns:
        valid["Booking Window"] = pd.cut(pd.to_numeric(valid["days_before"], errors="coerce"), [-1, 1, 3, 7, 14, 30, 9999], labels=["0–1", "2–3", "4–7", "8–14", "15–30", "31+"])
        window = valid.groupby("Booking Window", observed=False)['_price'].agg(['mean', 'count']).dropna()
        st.subheader("Booking Window")
        if not window.empty:
            best = window['mean'].idxmin()
            low = valid[valid["Booking Window"] == best]["_price"].min()
            high = valid[valid["Booking Window"] == best]["_price"].max()
            st.info(f"Best observed booking window: **{best} days before arrival**. Historical expected range for this window: **${low:,.0f}–${high:,.0f}**. This is not a guaranteed future price.")
            st.dataframe(window.reset_index().rename(columns={"mean": "Average Price", "count": "Records"}).round(0), hide_index=True, use_container_width=True)
    st.subheader("Golden Window & Move Your Trip")
    if len(by_day) >= 3:
        st.write(f"**Golden Window:** Prefer the lowest-priced arrival-day pattern, currently **{by_day.index[0]}**.")
        st.write(f"**Move Your Trip:** Moving from {by_day.index[-1]} to {by_day.index[0]} could save about **${(by_day.iloc[-1]['mean'] - by_day.iloc[0]['mean']):,.0f}** on average.")
    else:
        st.info(f"A Golden Window needs more distinct historical arrival dates for {visit_date.strftime(chr(37)+chr(65))}.")


def render_advertiser_account_gate():
    if st.session_state.get("role") in {"admin", "advertiser", "contributor"}:
        return True
    st.info("To create or manage an advertising campaign, create an advertiser account or log in. Guests can still browse all public content.")
    with st.form("advertiser_signup"):
        username = st.text_input("Choose username")
        password = st.text_input("Choose password", type="password")
        email = st.text_input("Recovery email (recommended)")
        submitted = st.form_submit_button("Create advertiser account")
    if submitted:
        if not username.strip() or not password.strip():
            st.error("Username and password are required.")
        else:
            try:
                append_rows("Users", [[f"USR-{uuid.uuid4().hex[:8]}", username.strip(), password, "advertiser", "deals|campaigns|contact", "", "2099-12-31", "active", email]], headers=["User_ID", "Username", "Password_or_Hash", "Role", "Allowed_Pages", "Last_Login", "Expiry_Date", "Status", "Notes"])
                st.success("Account created. You can now log in from the main screen.")
            except Exception as exc:
                st.error(f"Could not create account: {exc}")
    return False


def render_advertiser_notice():
    st.info("Campaign pricing: **$12 for one month** or **$20 for three months**. Every approved new campaign receives a **30-day free trial**. Payment is sent through PayPal to **marketandsellbuy@gmail.com**. The campaign may be published before payment confirmation, subject to admin review.")
