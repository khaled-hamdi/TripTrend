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


def _is_pending(value) -> bool:
    """Recognize the status labels used by forms and legacy Sheets tabs."""
    normalized = str(value or '').strip().casefold()
    return normalized in {'', 'new', 'pending', 'pending review', 'submitted', 'awaiting approval', 'under review'} or 'pending' in normalized or 'review' in normalized


def _row_label(row, tab: str) -> str:
    for field in ('Title', 'Offer_Title', 'Campaign_Name', 'Subject', 'Short title', 'Question', 'Comment', 'Message', 'Partner_Name', 'Advertiser_Name', 'Contributor_Name', 'Display_Name', 'Name'):
        value = str(row.get(field, '')).strip()
        if value:
            return value[:90]
    return f'{tab} submission'


def _set_fields(tab, row_index, updates):
    rows = read_tab(tab)
    if not rows or row_index + 1 >= len(rows):
        return False
    headers = [str(x).strip() for x in rows[0]]
    body = [(list(r) + [''] * len(headers))[:len(headers)] for r in rows[1:]]
    for field, value in updates.items():
        if field in headers:
            body[row_index][headers.index(field)] = value
    replace_tab(tab, [headers] + body)
    return True


def _award_contributor_points(contributor_id, amount, reference_id, reason):
    if not str(contributor_id).strip():
        return
    contributors = _records("Contributors")
    if not contributors.empty and "Contributor_ID" in contributors.columns:
        matches = contributors[contributors["Contributor_ID"].astype(str).eq(str(contributor_id))]
        if not matches.empty:
            idx = matches.index[0]
            current = int(float(matches.iloc[0].get("Points", 0) or 0))
            total = current + int(amount)
            level = "New Contributor" if total < 10 else "Travel Contributor" if total < 50 else "Travel Insider" if total < 150 else "City Expert" if total < 500 else "Top Travel Expert"
            _set_fields("Contributors", idx, {"Points": total, "Level": level, "Last_Login": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    append_rows("Contributor_Points_Log", [[uuid.uuid4().hex, contributor_id, "Expert Answer", reference_id, amount, "Approved", reason, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), st.session_state.get("username", "admin")]], headers=NEW_TAB_HEADERS["Contributor_Points_Log"])


def render_expert_admin():
    st.subheader("🧠 Ask a Travel Expert")
    st.caption("Review visitor questions, approve contributor answers, and track requests for missing data.")
    questions = _records("Expert_Questions")
    answers = _records("Expert_Answers")
    requests = _records("Data_Requests")
    q_pending = questions[questions.get("Status", pd.Series("", index=questions.index)).map(_is_pending)] if not questions.empty else questions
    a_pending = answers[answers.get("Status", pd.Series("", index=answers.index)).map(_is_pending)] if not answers.empty else answers
    r_open = requests[~requests.get("Status", pd.Series("", index=requests.index)).astype(str).str.casefold().isin(["closed", "completed", "rejected"])] if not requests.empty else requests
    c1, c2, c3 = st.columns(3)
    c1.metric("Pending questions", len(q_pending))
    c2.metric("Pending answers", len(a_pending))
    c3.metric("Open data requests", len(r_open))

    st.markdown("#### Visitor questions")
    if questions.empty:
        st.info("No questions have been submitted yet.")
    else:
        st.dataframe(questions.tail(50), hide_index=True, use_container_width=True)
        if not q_pending.empty:
            choices = {f"{idx}: {_row_label(row, 'Expert_Questions')}"[:120]: idx for idx, row in q_pending.iterrows()}
            selected = st.selectbox("Select a question", list(choices), key="expert_admin_question")
            idx = choices[selected]
            row = q_pending.loc[idx]
            st.info(f"{row.get('Question', '')}\n\nDestination: {row.get('City', '') or 'All cities'} · Category: {row.get('Category', '')}")
            c1, c2 = st.columns(2)
            if c1.button("Mark under review", key="expert_mark_review"):
                if _set_fields("Expert_Questions", idx, {"Status": "Under Review"}): st.cache_data.clear(); st.rerun()
            if c2.button("Close question", key="expert_close_question"):
                if _set_fields("Expert_Questions", idx, {"Status": "Closed"}): st.cache_data.clear(); st.rerun()

    st.markdown("#### Contributor answers")
    if answers.empty:
        st.info("No contributor answers have been submitted yet.")
    else:
        st.dataframe(answers.tail(50), hide_index=True, use_container_width=True)
        if not a_pending.empty:
            choices = {f"{idx}: {_row_label(row, 'Contributor_Answers')}"[:120]: idx for idx, row in a_pending.iterrows()}
            selected = st.selectbox("Select an answer", list(choices), key="expert_admin_answer")
            idx = choices[selected]
            row = a_pending.loc[idx]
            st.write(str(row.get("Answer", "")))
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve and publish answer", key="expert_approve_answer"):
                if _set_fields("Expert_Answers", idx, {"Status": "Approved", "Published": "TRUE", "Approved_By": st.session_state.get("username", "admin")}):
                    _award_contributor_points(row.get("Contributor_ID", ""), 5, row.get("Answer_ID", ""), "Approved helpful expert answer")
                    qid = str(row.get("Question_ID", ""))
                    if not questions.empty and "Question_ID" in questions.columns:
                        matches = questions[questions["Question_ID"].astype(str).eq(qid)]
                        for qidx in matches.index:
                            _set_fields("Expert_Questions", qidx, {"Status": "Answered", "Answer_ID": row.get("Answer_ID", ""), "Published": "TRUE"})
                    st.cache_data.clear(); st.rerun()
            if c2.button("❌ Reject answer", key="expert_reject_answer"):
                if _set_fields("Expert_Answers", idx, {"Status": "Rejected", "Published": "FALSE", "Approved_By": st.session_state.get("username", "admin")}): st.cache_data.clear(); st.rerun()

    st.markdown("#### Requested missing data")
    if requests.empty:
        st.info("No missing-data requests have been created yet.")
    else:
        st.dataframe(requests.tail(50), hide_index=True, use_container_width=True)


def render_content_admin():
    st.subheader("🧩 Content, Events, Experiences & Partners")
    st.caption("Manage the new travel data from the Admin Panel. Google Sheets remains the backend; no manual sheet editing is required.")
    tabs = st.tabs(["Events", "Traveler Experiences", "Affiliate Widgets", "Contributors", "Moderation", "🧠 Ask Experts"])
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
        st.caption("Review visitor-submitted content here. Select a pending row, then approve or reject it. Changes are written to Google Sheets immediately.")
        moderation_tabs = [
            "Campaign_Requests", "Travel_Experiences", "Feedback_Messages",
            "Traveler_Questions", "Contributor_Answers", "Advertisements",
            "Travel_Offers", "Creator_Offers", "Affiliate_Widgets",
        ]
        pending_total = 0
        for tab in moderation_tabs:
            records = _records(tab)
            if not records.empty and 'Status' in records.columns:
                pending_total += int(records['Status'].map(_is_pending).sum())
        st.metric("Pending items awaiting review", pending_total)
        for tab in moderation_tabs:
            st.markdown(f"**{tab}**")
            records = _records(tab)
            if records.empty: st.info("No records.")
            else:
                view = records.tail(50).copy()
                st.dataframe(view, hide_index=True, use_container_width=True)
                if 'Status' in view.columns:
                    pending = view[view['Status'].map(_is_pending)]
                    if not pending.empty:
                        choices = {}
                        for idx, row in pending.iterrows():
                            choices[f"{idx}: {_row_label(row, tab)}"] = idx
                        selected = st.selectbox(f"Select pending {tab} row", list(choices), key=f"moderate_{tab}")
                        idx = choices[selected]
                        c1, c2 = st.columns(2)
                        if c1.button(f"✅ Approve {tab}", key=f"approve_{tab}"):
                            if _set_status(tab, idx, 'Approved'):
                                st.success(f'{tab} item approved.'); st.cache_data.clear(); st.rerun()
                        if c2.button(f"❌ Reject {tab}", key=f"reject_{tab}"):
                            if _set_status(tab, idx, 'Rejected'):
                                st.warning(f'{tab} item rejected.'); st.cache_data.clear(); st.rerun()
                    else:
                        st.caption("No pending items in this tab.")
    with tabs[5]:
        render_expert_admin()
