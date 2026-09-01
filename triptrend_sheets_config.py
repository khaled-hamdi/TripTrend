from __future__ import annotations

from datetime import datetime
import streamlit as st
from google_sheets_adapter import read_tab


@st.cache_data(ttl=120, show_spinner=False)
def _rows(tab):
    rows = read_tab(tab)
    if not rows:
        return []
    headers = [str(x).strip() for x in rows[0]]
    return [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in rows[1:] if any(str(x).strip() for x in row)]


def _truthy(value):
    return str(value).strip().lower() in {'true', '1', 'yes', 'active', 'on'}


def load_config_from_sheets(default_config):
    config = dict(default_config)
    settings = dict(default_config.get('_settings', {}))
    for row in _rows('Settings'):
        key, value = str(row.get('Setting_Key', '')).strip(), row.get('Setting_Value', '')
        if key:
            if str(value).strip().lower() in {'true', 'false'}:
                value = _truthy(value)
            settings[key] = value
    config['_settings'] = settings

    networks = {}
    for row in _rows('Affiliate_Networks'):
        if _truthy(row.get('Active', 'TRUE')) and row.get('Match_Name') and row.get('Affiliate_URL'):
            networks[str(row['Match_Name']).strip()] = str(row['Affiliate_URL']).strip()
    config['_affiliate_networks'] = networks

    widgets = []
    sponsors = {'General': []}
    for row in _rows('Advertisements') + _rows('Travel_Offers') + _rows('Creator_Offers'):
        if not _truthy(row.get('Status', 'Active')):
            continue
        link = str(row.get('Link_URL', '')).strip()
        if not link:
            continue
        name = row.get('Advertiser_Name') or row.get('Creator_ID') or 'Partner'
        title = row.get('Title') or row.get('Offer_Title') or row.get('Offer_Type') or name
        desc = row.get('Short_Description') or row.get('Description') or ''
        city = str(row.get('City', '')).strip() or 'General'
        item = {'name': str(title), 'desc': str(desc), 'link': link, 'icon': str(row.get('Icon', '🔗') or '🔗'), 'type': 'link', 'city': city}
        widgets.append(item)
        sponsors.setdefault(city, []).append(item)
    config['_affiliate_widgets'] = widgets
    config['_sponsors'] = sponsors

    # Keep a compatible user map for the existing login UI.
    reserved = {'_settings', '_sponsors', '_stats', '_affiliate_networks', '_affiliate_widgets', '_travel_tips', '_paid_ads'}
    for row in _rows('Users'):
        username = str(row.get('Username', '')).strip()
        if not username:
            continue
        allowed = str(row.get('Allowed_Pages', 'all')).strip()
        config[username] = {
            'password': str(row.get('Password_or_Hash', '')),
            'role': str(row.get('Role', 'blogger')).strip().lower(),
            'allowed_pages': ['all'] if allowed.lower() == 'all' else [x.strip() for x in allowed.split('|') if x.strip()],
            'last_login': row.get('Last_Login', 'N/A'),
            'expiry_date': str(row.get('Expiry_Date', '2099-12-31') or '2099-12-31'),
            'status': str(row.get('Status', 'active')).strip().lower(),
        }
    return config
