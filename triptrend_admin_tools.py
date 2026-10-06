from __future__ import annotations
from datetime import datetime
import uuid
import pandas as pd
import streamlit as st
from google_sheets_adapter import append_rows, read_tab
from triptrend_new_features import NEW_TAB_HEADERS, _records


def _append(tab, values):
    append_rows(tab, [values], headers=NEW_TAB_HEADERS.get(tab))


def render_content_admin():
    st.subheader("🧩 Content, Events, Experiences & Partners")
    st.caption("Manage the new travel data from the Admin Panel. Google Sheets remains the backend; no manual sheet editing is required.")
    tabs = st.tabs(["Events", "Traveler Experiences", "Affiliate Widgets", "Contributors", "Moderation"])
    with tabs[0]:
        with st.form("admin_add_event"):
            c1, c2 = st.columns(2)
            city = c1.text_input("City *")
            country = c2.text_input("Country")
            name = c1.text_input("Event name *")
            kind = c2.text_input("Event type")
            start = c1.date_input("Start date")
            end = c2.date_input("End date")
            location = st.text_input("Location")
            desc = st.text_area("Description")
            link = st.text_input("Event link")
            ok = st.form_submit_button("Add event")
        if ok:
            if not city.strip() or not name.strip(): st.error("City and event name are required.")
            else:
                _append("Events", [f"EV-{uuid.uuid4().hex[:8]}", city, country, name, kind, start, end, location, desc, link, "", "Active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                st.success("Event added.")
        events = _records("Events")
        if not events.empty: st.dataframe(events.tail(20), hide_index=True, use_container_width=True)
    with tabs[1]:
        with st.form("admin_add_experience"):
            c1, c2 = st.columns(2)
            contributor = c1.text_input("Contributor name *")
            city = c2.text_input("City *")
            kind = c1.selectbox("Experience type", ["Price", "Weather", "Service", "Hotel", "Transport", "Food", "Activity", "Other"])
            date = c2.date_input("Experience date")
            title = st.text_input("Short title")
            comment = st.text_area("Traveler comment *")
            value = st.text_input("Value (optional)")
            unit = st.text_input("Unit (optional)")
            ok = st.form_submit_button("Add and approve experience")
        if ok:
            if not contributor.strip() or not city.strip() or not comment.strip(): st.error("Contributor, city, and comment are required.")
            else:
                _append("Travel_Experiences", [f"EXP-{uuid.uuid4().hex[:8]}", "", contributor, city, "", kind, title, comment, value, unit, date, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Approved", 0, st.session_state.get("username", "admin")])
                st.success("Experience added and approved.")
        exp = _records("Travel_Experiences")
        if not exp.empty: st.dataframe(exp.tail(20), hide_index=True, use_container_width=True)
    with tabs[2]:
        with st.form("admin_add_widget"):
            c1, c2 = st.columns(2)
            partner = c1.text_input("Partner name *")
            category = c2.text_input("Category", value="Flights")
            city = c1.text_input("City (blank = all cities)")
            pages = c2.text_input("Target pages", value="Plan Your Trip")
            placement = c1.selectbox("Placement", ["Inline", "Sidebar", "Featured"])
            widget_type = c2.selectbox("Type", ["Link", "Widget HTML", "Iframe", "Banner"])
            url = st.text_input("Affiliate URL")
            code = st.text_area("Widget/iframe HTML (optional)")
            desc = st.text_input("One-line description")
            priority = st.number_input("Priority", min_value=1, value=1, step=1)
            ok = st.form_submit_button("Add partner/widget")
        if ok:
            if not partner.strip(): st.error("Partner name is required.")
            elif not url.strip() and not code.strip(): st.error("Provide an affiliate URL or widget code.")
            else:
                _append("Affiliate_Widgets", [f"WID-{uuid.uuid4().hex[:8]}", partner, category, city, pages, placement, widget_type, code, url, desc, priority, "", "", "Active"])
                st.success("Partner/widget added. It will appear in the selected context.")
        widgets = _records("Affiliate_Widgets")
        if not widgets.empty: st.dataframe(widgets.tail(20), hide_index=True, use_container_width=True)
    with tabs[3]:
        contributors = _records("Contributors")
        if contributors.empty: st.info("No contributors yet.")
        else: st.dataframe(contributors.sort_values("Points", ascending=False), hide_index=True, use_container_width=True)
    with tabs[4]:
        for tab in ["Campaign_Requests", "Feedback_Messages", "Travel_Experiences"]:
            st.markdown(f"**{tab}**")
            records = _records(tab)
            if records.empty: st.info("No records.")
            else: st.dataframe(records.tail(50), hide_index=True, use_container_width=True)
