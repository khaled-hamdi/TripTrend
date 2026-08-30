from __future__ import annotations

import json
import os
from typing import Iterable, Sequence

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


def _credentials():
    """Load service-account credentials from Streamlit Secrets or environment variables."""
    from google.oauth2.service_account import Credentials
    try:
        import streamlit as st
        secret_info = st.secrets.get('gcp_service_account')
        if secret_info:
            return Credentials.from_service_account_info(dict(secret_info), scopes=SCOPES)
    except Exception:
        pass
    raw = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '').strip()
    if not raw:
        raise RuntimeError('gcp_service_account or GOOGLE_SERVICE_ACCOUNT_JSON is not configured')
    info = json.loads(raw)
    return Credentials.from_service_account_info(info, scopes=SCOPES)


def _service():
    from googleapiclient.discovery import build
    return build('sheets', 'v4', credentials=_credentials(), cache_discovery=False)


def spreadsheet_id() -> str:
    value = os.getenv('TRIPTREND_SPREADSHEET_ID', '').strip()
    if not value:
        try:
            import streamlit as st
            value = str(st.secrets.get('TRIPTREND_SPREADSHEET_ID', '')).strip()
        except Exception:
            value = ''
    if not value:
        raise RuntimeError('TRIPTREND_SPREADSHEET_ID is not configured')
    return value


def get_metadata():
    return _service().spreadsheets().get(
        spreadsheetId=spreadsheet_id(), includeGridData=False
    ).execute()


def list_tabs() -> list[str]:
    metadata = get_metadata()
    return [s['properties']['title'] for s in metadata.get('sheets', [])]


def read_tab(tab_name: str, range_end: str = 'ZZ') -> list[list]:
    result = _service().spreadsheets().values().get(
        spreadsheetId=spreadsheet_id(),
        range=f"'{tab_name}'!A1:{range_end}",
        majorDimension='ROWS',
        valueRenderOption='UNFORMATTED_VALUE',
    ).execute()
    return result.get('values', [])


def append_rows(tab_name: str, rows: Iterable[Sequence]):
    values = [list(row) for row in rows]
    if not values:
        return None
    return _service().spreadsheets().values().append(
        spreadsheetId=spreadsheet_id(),
        range=f"'{tab_name}'!A1",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body={'values': values},
    ).execute()


def replace_tab(tab_name: str, rows: Iterable[Sequence]):
    values = [list(row) for row in rows]
    return _service().spreadsheets().values().update(
        spreadsheetId=spreadsheet_id(),
        range=f"'{tab_name}'!A1",
        valueInputOption='USER_ENTERED',
        body={'values': values},
    ).execute()
