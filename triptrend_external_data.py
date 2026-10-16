from __future__ import annotations

import re
from datetime import date
import pandas as pd
import streamlit as st
from google_sheets_adapter import list_tabs, read_tab


def _frame(tab: str) -> pd.DataFrame:
    try:
        rows = read_tab(tab)
    except Exception:
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()
    headers = [str(x).strip() if x is not None else f"Unnamed_{i}" for i, x in enumerate(rows[0])]
    width = len(headers)
    return pd.DataFrame([(list(r) + [""] * width)[:width] for r in rows[1:]], columns=headers)


def _tabs(prefixes):
    try:
        return [t for t in list_tabs() if any(t.startswith(p) for p in prefixes)]
    except Exception:
        return []


def _city_from_tab(tab: str, prefix: str):
    return tab[len(prefix):].replace("_", " ").strip()


def city_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


def _col(df, names):
    lookup = {str(c).strip().casefold(): c for c in df.columns}
    for n in names:
        if n.casefold() in lookup:
            return lookup[n.casefold()]
    return None


@st.cache_data(ttl=300, show_spinner=False)
def external_events() -> pd.DataFrame:
    frames = []
    for tab in _tabs(["EV__"]):
        df = _frame(tab)
        if df.empty:
            continue
        city = _city_from_tab(tab, "EV__")
        out = pd.DataFrame({
            "City": city,
            "Event_Name": df[_col(df, ["Event_Name", "Event Name", "Name"]) ] if _col(df, ["Event_Name", "Event Name", "Name"]) else "",
            "Date": df[_col(df, ["Date", "Event_Date"]) ] if _col(df, ["Date", "Event_Date"]) else "",
            "Time": df[_col(df, ["Time", "Event_Time"]) ] if _col(df, ["Time", "Event_Time"]) else "",
            "Cost": df[_col(df, ["Cost", "Price"]) ] if _col(df, ["Cost", "Price"]) else "",
            "City_or_Venue": df[_col(df, ["City_or_Venue", "Venue", "Location"]) ] if _col(df, ["City_or_Venue", "Venue", "Location"]) else "",
            "Source_Tab": tab,
        })
        out["Event_Date"] = out["Date"]
        frames.append(out)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["City","Event_Name","Date","Event_Date","Time","Cost","City_or_Venue","Source_Tab"])


@st.cache_data(ttl=300, show_spinner=False)
def city_prices() -> pd.DataFrame:
    frames = []
    for tab in _tabs(["PR__"]):
        df = _frame(tab)
        if df.empty:
            continue
        city = _city_from_tab(tab, "PR__")
        item = _col(df, ["Kind", "kind", "Item", "Item_Name"])
        price = _col(df, ["Prices", "prices", "Price", "Edit"])
        rng = _col(df, ["Range", "Price_Range"])
        cat = _col(df, ["category", "categor", "Category"])
        out = pd.DataFrame({
            "City": city,
            "Item_Name": df[item] if item else "",
            "Raw_Price": df[price] if price else "",
            "Raw_Range": df[rng] if rng else "",
            "Category": df[cat] if cat else "",
            "Source_Tab": tab,
        })
        out["Price_Value"] = pd.to_numeric(out["Raw_Price"].astype(str).str.replace(r"[^0-9.\-]", "", regex=True), errors="coerce")
        out["Currency"] = out["Raw_Price"].astype(str).str.extract(r"([£$€¥₹₺]|Dh|E£|Fr\\.)", expand=False).fillna("")
        frames.append(out)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["City","Item_Name","Raw_Price","Raw_Range","Category","Source_Tab","Price_Value","Currency"])


def _temperature(value):
    m = re.search(r"-?\d+(?:\.\d+)?", str(value or "").replace("٫", "."))
    return float(m.group()) if m else None


@st.cache_data(ttl=300, show_spinner=False)
def external_weather() -> pd.DataFrame:
    frames = []
    for tab in _tabs(["WEATHER__"]):
        df = _frame(tab)
        if df.empty:
            continue
        # Source format: city header, then day / max / min repeating in each city column.
        for col in df.columns:
            city = str(col).strip()
            if not city or city.startswith("Unnamed"):
                continue
            values = df[col].tolist()
            previous_day = None
            month = 9
            for i in range(0, len(values) - 2):
                raw_day = values[i]
                if not isinstance(raw_day, (int, float)):
                    continue
                day = int(raw_day)
                if day == 0:
                    iso, status = "", "Invalid day value"
                else:
                    if previous_day is not None and day < previous_day:
                        month += 1
                    try:
                        iso = date(2026, month, day).isoformat()
                        status = "Parsed"
                    except ValueError:
                        iso, status = "", "Invalid calendar date"
                    previous_day = day
                frames.append({"City": city, "Forecast_Date": iso, "Day": day, "Temperature_Max": _temperature(values[i+1]), "Temperature_Min": _temperature(values[i+2]), "Raw_Max": values[i+1], "Raw_Min": values[i+2], "Status": status, "Source_Tab": tab})
    return pd.DataFrame(frames)


@st.cache_data(ttl=300, show_spinner=False)
def external_currency() -> pd.DataFrame:
    frames = []
    for tab in _tabs(["CURRENCY__"]):
        df = _frame(tab)
        if df.empty:
            continue
        name = _col(df, ["Currency"])
        rate = _col(df, ["Dollar", "Rate", "Value"])
        out = pd.DataFrame({"Currency": df[name] if name else "", "Dollar": df[rate] if rate else "", "Source_Tab": tab})
        out["Dollar"] = pd.to_numeric(out["Dollar"], errors="coerce")
        frames.append(out)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["Currency","Dollar","Source_Tab"])


@st.cache_data(ttl=300, show_spinner=False)
def external_flights() -> pd.DataFrame:
    for tab in ["Flights", "Flight_Master"] + _tabs(["FLIGHT__"]):
        df = _frame(tab)
        if not df.empty and len(df.columns) >= 3:
            # Prefer the supplied Flight_Master names while exposing stable aliases for analytics.
            price = _col(df, ["Price (USD)", "Price", "Fare"])
            origin = _col(df, ["From city", "Origin", "From airport"])
            destination = _col(df, ["To city", "Destination", "To airport"])
            if price:
                df["Price"] = pd.to_numeric(df[price], errors="coerce")
            if origin: df["Origin"] = df[origin]
            if destination: df["Destination"] = df[destination]
            return df
    return pd.DataFrame()


def external_cities() -> list[str]:
    values = []
    for frame in [external_events(), city_prices(), external_weather()]:
        if not frame.empty and "City" in frame.columns:
            values.extend(frame["City"].dropna().astype(str).tolist())
    seen = {}
    for v in values:
        key = re.sub(r"[^a-z0-9]", "", v.casefold())
        if key and key not in seen: seen[key] = v.strip()
    return sorted(seen.values())
