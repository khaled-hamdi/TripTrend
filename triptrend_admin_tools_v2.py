from __future__ import annotations
from datetime import datetime
import uuid
import pandas as pd
import streamlit as st
from google_sheets_adapter import append_rows, read_tab, replace_tab
from triptrend_new_features_v2 import NEW_TAB_HEADERS, _records


def _append(tab, values):
    append_rows(tab, [values], headers=NEW_TAB_HEADERS.get(tab))


def _set_status(tab, row_index, status):
    rows = read_tab(tab)
    if not rows or row_index + 1 >= len(rows):
        return False
    headers = [str(x).strip() for x in rows[0]]
    body = [(list(r) + [''] * len(headers))[:len(headers)] for r in rows[1:]]
    if 'Status' not in headers:
        return False
    body[row_index][headers.index('Status')] = status
    replace_tab(tab, [headers] + body)
    return True


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
            category = c2.selectbox("Category", ["Flights", "Hotels", "Car Rentals", "Travel SIM", "Airport Transfer", "Luggage Storage", "Tours", "Other"])
            city = c1.text_input("City (blank = all cities)")
            page_choices = ["Plan Your Trip", "Best Dates", "Hotel of the Day", "Deal Radar", "Traveler Guide", "Exclusive Deals", "Dashboard"]
            pages = ", ".join(c2.multiselect("Target pages", page_choices, default=["Plan Your Trip"]))
            placement = c1.selectbox("Placement", ["Inline", "Sidebar", "Featured"])
            widget_type = c2.selectbox("Type", ["Link", "Widget HTML", "Iframe", "Banner"])
            url = st.text_input("Affiliate URL")
            code = st.text_area("Widget/iframe HTML (optional)")
            desc = st.text_input("One-line description")
            priority = st.number_input("Priority", min_value=1, value=1, step=1)
            start_date = c2.date_input("Start date")
            end_date = c1.date_input("End date")
            ok = st.form_submit_button("Add partner/widget")
        if ok:
            if not partner.strip(): st.error("Partner name is required.")
            elif not url.strip() and not code.strip(): st.error("Provide an affiliate URL or widget code.")
            else:
                if end_date < start_date:
                    st.error("End date cannot be before start date.")
                else:
                    _append("Affiliate_Widgets", [f"WID-{uuid.uuid4().hex[:8]}", partner, category, city, pages, placement, widget_type, code, url, desc, priority, start_date.isoformat(), end_date.isoformat(), "Active"])
                    st.cache_data.clear()
                    st.success("Partner/widget added. It will appear in the selected context.")
        widgets = _records("Affiliate_Widgets")
        if not widgets.empty: st.dataframe(widgets.tail(20), hide_index=True, use_container_width=True)
    with tabs[3]:
        contributors = _records("Contributors")
        if contributors.empty: st.info("No contributors yet.")
        else: st.dataframe(contributors.sort_values("Points", ascending=False), hide_index=True, use_container_width=True)
    with tabs[4]:
        st.caption("Review visitor-submitted content here. Select a row, then approve or reject it.")
        for tab in ["Campaign_Requests", "Feedback_Messages", "Travel_Experiences"]:
            st.markdown(f"**{tab}**")
            records = _records(tab)
            if records.empty: st.info("No records.")
            else:
                view = records.tail(50).copy()
                st.dataframe(view, hide_index=True, use_container_width=True)
                if 'Status' in view.columns:
                    pending = view[view['Status'].astype(str).str.lower().isin(['new', 'pending', 'submitted', ''])]
                    if not pending.empty:
                        choices = {}
                        for idx, row in pending.iterrows():
                            label = str(row.get('Name', row.get('Offer_Title', row.get('Campaign_Name', 'Submission'))))[:80]
                            choices[f"{idx}: {label}"] = idx
                        selected = st.selectbox(f"Select pending {tab} row", list(choices), key=f"moderate_{tab}")
                        idx = choices[selected]
                        c1, c2 = st.columns(2)
                        if c1.button(f"✅ Approve {tab}", key=f"approve_{tab}"):
                            if _set_status(tab, idx, 'Approved'):
                                st.success('Approved.'); st.cache_data.clear(); st.rerun()
                        if c2.button(f"❌ Reject {tab}", key=f"reject_{tab}"):
                            if _set_status(tab, idx, 'Rejected'):
                                st.warning('Rejected.'); st.cache_data.clear(); st.rerun()
