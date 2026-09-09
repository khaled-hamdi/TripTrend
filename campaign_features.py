from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import html
import uuid
from typing import Any

import pandas as pd
import streamlit as st

from google_sheets_adapter import append_rows, read_tab


TAB_HEADERS = {
    "Campaign_Requests": [
        "Request_ID", "Request_Date", "Advertiser_Name", "Contact_Name", "Email",
        "Phone_or_WhatsApp", "Advertiser_Type", "Campaign_Type", "Offer_Title",
        "Country", "City", "Target_Pages", "Selected_Plan", "Amount", "Currency",
        "Trial_Request", "Start_Date", "End_Date", "Payment_Status", "Payment_Reference",
        "Status", "Admin_Notes", "Approved_By", "Approved_At",
    ],
    "Engagement_Events": [
        "Event_ID", "Event_Date", "Event_Time", "Event_Type", "Campaign_ID", "Offer_ID",
        "Creator_ID", "Page_Name", "City", "Country", "Session_ID", "Device_Type",
        "Source_Channel", "UTM_Source", "UTM_Medium", "UTM_Campaign",
    ],
    "Feedback_Messages": [
        "Message_ID", "Created_At", "Full_Name", "Email", "Phone_or_WhatsApp",
        "Preferred_Contact_Method", "Message_Type", "Subject", "Message", "Related_City",
        "Related_Campaign_ID", "Related_Offer_ID", "Source_Page", "Status", "Priority",
        "Assigned_To", "Admin_Notes", "First_Response_At", "Resolved_At", "Consent_To_Reply",
    ],
}


def _read_records(tab: str) -> pd.DataFrame:
    try:
        rows = read_tab(tab)
    except Exception:
        return pd.DataFrame()
    if not rows or len(rows) < 2:
        return pd.DataFrame()
    headers = [str(x).strip() for x in rows[0]]
    body = rows[1:]
    width = len(headers)
    normalized = [(list(row) + [""] * width)[:width] for row in body]
    return pd.DataFrame(normalized, columns=headers)


def _now() -> datetime:
    return datetime.now()


def _session_id() -> str:
    raw = f"{st.session_state.get('username','visitor')}|{st.session_state.get('session_seed','')}"
    if not st.session_state.get("session_seed"):
        st.session_state["session_seed"] = uuid.uuid4().hex
        raw = f"visitor|{st.session_state['session_seed']}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _track(event_type: str, campaign_id: str = "", offer_id: str = "", creator_id: str = "", page: str = "", city: str = "") -> None:
    try:
        now = _now()
        append_rows("Engagement_Events", [[
            uuid.uuid4().hex, now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), event_type,
            campaign_id, offer_id, creator_id, page, city, "", _session_id(), "Web", "TripTrend", "", "", "",
        ]], headers=TAB_HEADERS["Engagement_Events"])
    except Exception:
        # Analytics must never break the public page.
        pass


def _safe_date(value: Any):
    parsed = pd.to_datetime(value, errors="coerce")
    return parsed if not pd.isna(parsed) else pd.NaT


def _active_offers() -> pd.DataFrame:
    offers = _read_records("Travel_Offers")
    if offers.empty:
        return offers
    now = pd.Timestamp.now().normalize()
    for col in ("Start_Display_Date", "End_Display_Date", "Campaign_Start_Date", "Campaign_End_Date"):
        if col in offers.columns:
            offers[col] = pd.to_datetime(offers[col], errors="coerce")
    status = offers.get("Status", pd.Series("Active", index=offers.index)).astype(str).str.lower()
    active = status.isin(["active", "approved", "featured", "paid active", "active trial", ""])
    if "Start_Display_Date" in offers.columns:
        active &= offers["Start_Display_Date"].isna() | (offers["Start_Display_Date"] <= now)
    if "End_Display_Date" in offers.columns:
        active &= offers["End_Display_Date"].isna() | (offers["End_Display_Date"] >= now)
    return offers[active].copy()


def _offer_card(row: pd.Series, idx: int, page_name: str = "Monthly Travel Offers") -> None:
    offer_id = str(row.get("Offer_ID", row.get("Campaign_ID", f"offer-{idx}")))
    title = str(row.get("Offer_Title", row.get("Title", "Travel Offer")))
    advertiser = str(row.get("Advertiser_Name", "Travel Partner"))
    city = str(row.get("City", "All destinations"))
    desc = str(row.get("Short_Description", row.get("Description", "Discover this travel offer.")))
    price = str(row.get("Price_From", "Contact for price"))
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            st.markdown(f"### {html.escape(title)}")
            st.caption(f"{advertiser} · {city}")
            st.write(desc)
            st.write(f"**From:** {price} {row.get('Currency', 'USD')}")
        with c2:
            likes = int(float(row.get("Likes_Total", 0) or 0)) if str(row.get("Likes_Total", "")).strip() else 0
            if st.button(f"♥ {likes} Like", key=f"like_{offer_id}_{idx}"):
                like_key = f"liked_{offer_id}"
                if not st.session_state.get(like_key, False):
                    _track("Like", offer_id=offer_id, page=page_name, city=city)
                    st.session_state[like_key] = True
                    st.success("Liked")
            link = str(row.get("Link_URL", "")).strip()
            if link.startswith("http"):
                if st.button("View Details", key=f"details_{offer_id}_{idx}"):
                    _track("Details_View", offer_id=offer_id, page=page_name, city=city)
                    st.session_state[f"show_offer_{offer_id}"] = True
                st.link_button("Book / Contact", link, key=f"book_{offer_id}_{idx}")
        if st.session_state.get(f"show_offer_{offer_id}"):
            _track("Offer_View", offer_id=offer_id, page=page_name, city=city)
            st.info(str(row.get("Full_Description", row.get("Long_Description", desc))))
            st.caption("Campaign performance is based on aggregate TripTrend activity and is not a guaranteed booking count.")


def render_campaign_page() -> None:
    st.title("📣 Monthly Travel Offers & Campaigns")
    st.write("Discover current travel programs, services, creator campaigns, and city offers.")
    offers = _active_offers()
    if offers.empty:
        st.info("No active offers are published yet. Be the first to create a campaign.")
    else:
        c1, c2, c3 = st.columns(3)
        cities = sorted([x for x in offers.get("City", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        types = sorted([x for x in offers.get("Offer_Type", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
        city = c1.selectbox("Destination", ["All"] + cities)
        offer_type = c2.selectbox("Offer type", ["All"] + types)
        sort_by = c3.selectbox("Sort by", ["Featured", "Most liked", "Newest"])
        shown = offers.copy()
        if city != "All" and "City" in shown.columns:
            shown = shown[shown["City"].astype(str).eq(city)]
        if offer_type != "All" and "Offer_Type" in shown.columns:
            shown = shown[shown["Offer_Type"].astype(str).eq(offer_type)]
        if sort_by == "Most liked" and "Likes_Total" in shown.columns:
            shown["_likes"] = pd.to_numeric(shown["Likes_Total"], errors="coerce").fillna(0)
            shown = shown.sort_values("_likes", ascending=False)
        elif sort_by == "Featured" and "Featured" in shown.columns:
            shown = shown.sort_values("Featured", ascending=False)
        for idx, (_, row) in enumerate(shown.head(30).iterrows()):
            _offer_card(row, idx)
    st.markdown("---")
    st.subheader("Create your campaign")
    st.caption("Submit one form for a free 30-day trial, a $12 monthly campaign, or a $25 three-month campaign. Your content is reviewed before publication.")
    if st.button("Create Your Campaign", type="primary"):
        st.session_state["show_campaign_form"] = True
    if st.session_state.get("show_campaign_form"):
        _render_campaign_form()


def _render_campaign_form() -> None:
    with st.form("campaign_request_form"):
        name = st.text_input("Advertiser or creator name *")
        contact = st.text_input("Contact person *")
        email = st.text_input("Email")
        phone = st.text_input("Phone or WhatsApp")
        advertiser_type = st.selectbox("Advertiser type", ["Company", "Blogger", "Service", "Tour Guide", "Driver", "Hotel", "Other"])
        campaign_type = st.selectbox("Campaign type", ["Tour Package", "Hotel Offer", "Travel Service", "Creator Campaign", "Seasonal Campaign", "Other"])
        title = st.text_input("Offer or campaign title *")
        city = st.text_input("City or destination")
        country = st.text_input("Country")
        details = st.text_area("Description and details *")
        plan = st.selectbox("Choose your plan", ["Free Trial - 30 Days", "Monthly Campaign - $12", "Quarterly Campaign - $25"])
        start = st.date_input("Requested start date")
        link = st.text_input("Website or booking link")
        submitted = st.form_submit_button("Submit for Review", type="primary")
    if submitted:
        if not name.strip() or not title.strip() or not details.strip():
            st.error("Please complete the required fields.")
            return
        trial = plan.startswith("Free")
        amount = 0 if trial else (12 if "Monthly" in plan else 25)
        row = [
            f"REQ-{uuid.uuid4().hex[:10]}", _now().strftime("%Y-%m-%d %H:%M:%S"), name, contact, email,
            phone, advertiser_type, campaign_type, title, country, city, "Monthly Travel Offers",
            plan, amount, "USD", trial, str(start), "", "Pending Payment" if not trial else "Not Required", "",
            "Pending Review", "", "", "",
        ]
        try:
            append_rows("Campaign_Requests", [row], headers=TAB_HEADERS["Campaign_Requests"])
            st.success("Your campaign request was submitted for review.")
            if not trial:
                st.info("Payment is reviewed manually. The campaign is not published until payment is confirmed.")
        except Exception as exc:
            st.error(f"Could not submit the request: {exc}")


def render_creator_hub() -> None:
    st.title("🎥 TripTrend Creator Hub")
    st.write("Discover travel bloggers and creators across Facebook, Instagram, YouTube, TikTok, and X.")
    creators = _read_records("Creators")
    profiles = _read_records("Creator_Profiles")
    content = _read_records("Creator_Content")
    if creators.empty:
        st.info("No creator profiles are published yet.")
        return
    for idx, (_, creator) in enumerate(creators.head(50).iterrows()):
        cid = str(creator.get("Creator_ID", idx))
        with st.container(border=True):
            st.subheader(str(creator.get("Creator_Name", "Travel Creator")))
            st.write(str(creator.get("Bio", creator.get("Primary_Niche", "Travel content creator"))))
            if not profiles.empty and "Creator_ID" in profiles.columns:
                prof = profiles[profiles["Creator_ID"].astype(str) == cid]
                for _, p in prof.iterrows():
                    url = str(p.get("Profile_URL", ""))
                    if url.startswith("http"):
                        st.link_button(str(p.get("Platform", "Profile")), url)
            if not content.empty and "Creator_ID" in content.columns:
                st.markdown("**Featured topics**")
                st.dataframe(content[content["Creator_ID"].astype(str) == cid].head(5), hide_index=True, use_container_width=True)


def render_contact_page() -> None:
    st.title("✉️ Contact, Feedback & Support")
    st.write("Send a question, complaint, suggestion, campaign request, or report about an offer.")
    with st.form("feedback_form"):
        name = st.text_input("Your name *")
        email = st.text_input("Email")
        contact = st.text_input("Phone or WhatsApp")
        kind = st.selectbox("Message type", ["Question", "Complaint", "Suggestion", "Report an Offer", "Technical Issue", "Partnership", "Other"])
        subject = st.text_input("Subject")
        message = st.text_area("Message *", height=160)
        city = st.text_input("Related city, if any")
        consent = st.checkbox("I agree that TripTrend may use my contact details to reply.")
        submitted = st.form_submit_button("Send Message", type="primary")
    if submitted:
        if not name.strip() or not message.strip() or not consent:
            st.error("Please enter your name and message and allow us to reply.")
            return
        try:
            append_rows("Feedback_Messages", [[
                f"MSG-{uuid.uuid4().hex[:10]}", _now().strftime("%Y-%m-%d %H:%M:%S"), name, email, contact,
                "Email" if email else "Phone", kind, subject, message, city, "", "", st.session_state.get("current_page", "Contact"),
                "New", "Normal", "", "", "", "", True,
            ]], headers=TAB_HEADERS["Feedback_Messages"])
            st.success("Your message was sent successfully.")
        except Exception as exc:
            st.error(f"Could not send your message: {exc}")


def render_public_campaign_report(offer_id: str) -> None:
    offers = _read_records("Travel_Offers")
    if offers.empty or "Offer_ID" not in offers.columns:
        st.info("Public report is not available yet.")
        return
    row = offers[offers["Offer_ID"].astype(str) == str(offer_id)]
    if row.empty:
        st.info("Campaign not found.")
        return
    row = row.iloc[0]
    events = _read_records("Engagement_Events")
    if events.empty:
        st.info("The campaign report will appear after the first interactions.")
        return
    events = events[events.get("Offer_ID", pd.Series(dtype=str)).astype(str) == str(offer_id)]
    counts = events.get("Event_Type", pd.Series(dtype=str)).value_counts()
    st.subheader(f"Campaign Performance: {row.get('Offer_Title', 'Travel Offer')}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Views", int(counts.get("Offer_View", 0) + counts.get("Details_View", 0)))
    c2.metric("Likes", int(counts.get("Like", 0)))
    c3.metric("Clicks", int(counts.get("Booking_Click", 0) + counts.get("Ad_Click", 0)))
    c4.metric("Updated", _now().strftime("%Y-%m-%d"))
    st.caption("Aggregate TripTrend activity only; these figures are not guaranteed bookings.")
