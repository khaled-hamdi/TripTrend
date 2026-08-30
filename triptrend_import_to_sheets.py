from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pandas as pd

from google_sheets_adapter import append_rows, read_tab
from triptrend_data_engine import load_daily_workbook

PRICE_HEADERS = ['Import_ID','Import_Date','Booking_Date','Arrival_Date','City','Hotel_ID','Source_Hotel_Name','Best_Price','Best_Company','Price1','Company1','Price2','Company2','Price3','Company3','Rate','Rating_Label','Stars','Location','Description','Source_File','Record_Hash']
MASTER_HEADERS = ['Hotel_ID','City','Country','Canonical_Name','Stars','Rate','Rating_Label','Location','Description','Distance_From_Places','Active','Created_At','Updated_At']
ALIAS_HEADERS = ['Alias_ID','City','Alias_Name','Normalized_Alias','Hotel_ID','Match_Status','Approved_By','Approved_At','Notes']
LOG_HEADERS = ['Import_ID','Import_Date','City','Source_File','Rows_Read','Rows_Added','Rows_Duplicated','Rows_Uncertain','Rows_Rejected','Imported_By','Status','Notes']
COUNTRIES = {'Paris':'France','London':'United Kingdom','NewYork':'United States','Dubai':'UAE','Istanbul':'Turkey','Cairo':'Egypt','Switzerland':'Switzerland'}


def _text(value):
    if pd.isna(value):
        return ''
    return str(value)


def _date(value):
    if pd.isna(value):
        return ''
    return pd.Timestamp(value).strftime('%Y-%m-%d')


def _existing(tab):
    rows = read_tab(tab)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows[1:], columns=rows[0])


def prepare_import(path: str | Path, import_id: str | None = None, import_date: str | None = None):
    path = Path(path)
    import_id = import_id or f'IMP-{datetime.now():%Y%m%d-%H%M%S}'
    import_date = import_date or f'{datetime.now():%Y-%m-%d}'
    records, summary = load_daily_workbook(path, import_id=import_id, import_date=import_date)
    existing_history = _existing('Price_History')
    existing_hashes = set(existing_history.get('Record_Hash', pd.Series(dtype=str)).astype(str))
    records = records[~records['Record_Hash'].astype(str).isin(existing_hashes)].copy()
    history_rows = []
    for _, r in records.iterrows():
        history_rows.append([_date(r.get(h, '')) if h in ('Import_Date','Booking_Date','Arrival_Date') else _text(r.get(h, '')) for h in PRICE_HEADERS])
    existing_master = _existing('Hotels_Master')
    existing_ids = set(existing_master.get('Hotel_ID', pd.Series(dtype=str)).astype(str))
    latest = records.sort_values(['City','Source_Hotel_Name']).drop_duplicates(['City','Hotel_ID'])
    master_rows = []
    for _, r in latest.iterrows():
        if _text(r.get('Hotel_ID')) in existing_ids:
            continue
        master_rows.append([_text(r.get('Hotel_ID')), _text(r.get('City')), COUNTRIES.get(_text(r.get('City')), ''), _text(r.get('Source_Hotel_Name')), _text(r.get('Stars')), _text(r.get('Rate')), _text(r.get('Rating_Label')), _text(r.get('Location')), _text(r.get('Description')), '', 'TRUE', import_date, import_date])
    existing_aliases = _existing('Hotel_Aliases')
    existing_alias_keys = set(zip(existing_aliases.get('City', pd.Series(dtype=str)).astype(str), existing_aliases.get('Alias_Name', pd.Series(dtype=str)).astype(str)))
    alias_rows = []
    for i, r in records[['City','Source_Hotel_Name','Hotel_ID']].drop_duplicates().iterrows():
        key = (_text(r['City']), _text(r['Source_Hotel_Name']))
        if key in existing_alias_keys:
            continue
        alias_rows.append([f'ALIAS-{import_id}-{len(alias_rows)+1:05d}', _text(r['City']), _text(r['Source_Hotel_Name']), _text(r['Source_Hotel_Name']).lower(), _text(r['Hotel_ID']), 'Matched', 'system', import_date, ''])
    log_rows = []
    for _, s in summary.iterrows():
        log_rows.append([import_id, import_date, _text(s.get('city')), path.name, int(s.get('rows_read', 0)), int(len(records[records['City'] == s.get('city')])), int(s.get('rows_read', 0) - s.get('rows_eligible', 0)), 0, 0, 'system', 'Prepared', 'Dry-run prepared; review before apply'])
    return {'records': records, 'summary': summary, 'history_rows': history_rows, 'master_rows': master_rows, 'alias_rows': alias_rows, 'log_rows': log_rows}


def apply_import(prepared):
    if prepared['history_rows']:
        append_rows('Price_History', prepared['history_rows'])
    if prepared['master_rows']:
        append_rows('Hotels_Master', prepared['master_rows'])
    if prepared['alias_rows']:
        append_rows('Hotel_Aliases', prepared['alias_rows'])
    if prepared['log_rows']:
        append_rows('Import_Log', prepared['log_rows'])
    return {'history_added': len(prepared['history_rows']), 'master_added': len(prepared['master_rows']), 'aliases_added': len(prepared['alias_rows']), 'log_rows': len(prepared['log_rows'])}
