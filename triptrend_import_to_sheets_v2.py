from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
import pandas as pd

from google_sheets_adapter import append_rows, read_tab, list_tabs, replace_tab
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
    headers = [str(x).strip() for x in rows[0]]
    width = len(headers)
    # Google Sheets may omit trailing empty cells in individual rows.
    # Normalize every row to the header width before constructing the frame.
    normalized = [(list(row) + [''] * width)[:width] for row in rows[1:]]
    return pd.DataFrame(normalized, columns=headers)


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


def prepare_import_from_google_raw_tabs(import_id: str | None = None, import_date: str | None = None):
    """Build a temporary daily workbook from HOTEL_RAW__* tabs already in the master Sheet."""
    from openpyxl import Workbook
    import tempfile
    tabs = [t for t in list_tabs() if str(t).startswith('HOTEL_RAW__')]
    if not tabs:
        raise RuntimeError('No HOTEL_RAW__ tabs found in the connected Google Sheet.')
    wb = Workbook()
    wb.remove(wb.active)
    for tab in tabs:
        rows = read_tab(tab)
        if not rows:
            continue
        title = str(tab).replace('HOTEL_RAW__', '')[:31] or 'City'
        ws = wb.create_sheet(title)
        for row in rows:
            ws.append(list(row))
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
    tmp.close()
    wb.save(tmp.name)
    return prepare_import(tmp.name, import_id=import_id, import_date=import_date)


def _append_in_batches(tab_name, rows, headers=None, batch_size=200):
    rows = list(rows)
    if headers is not None:
        from google_sheets_adapter import ensure_tab
        ensure_tab(tab_name, headers)
    for start in range(0, len(rows), batch_size):
        chunk = rows[start:start + batch_size]
        last_error = None
        for attempt in range(5):
            try:
                append_rows(tab_name, chunk)
                time.sleep(0.25)
                last_error = None
                break
            except Exception as exc:
                last_error = exc
                status = getattr(getattr(exc, 'resp', None), 'status', None)
                if status not in (429, 500, 502, 503, 504):
                    raise RuntimeError(f"Google Sheets write failed for {tab_name}, rows {start + 1}-{start + len(chunk)}: {exc}") from exc
                time.sleep(2 ** attempt)
        if last_error is not None:
            raise RuntimeError(f"Google Sheets write failed after retries for {tab_name}, rows {start + 1}-{start + len(chunk)}: {last_error}") from last_error


def apply_import(prepared):
    # Keep each API request small enough for reliable Streamlit Cloud execution.
    if prepared['history_rows']:
        _append_in_batches('Price_History', prepared['history_rows'], PRICE_HEADERS)
    if prepared['master_rows']:
        _append_in_batches('Hotels_Master', prepared['master_rows'], MASTER_HEADERS)
    if prepared['alias_rows']:
        _append_in_batches('Hotel_Aliases', prepared['alias_rows'], ALIAS_HEADERS)
    if prepared['log_rows']:
        _append_in_batches('Import_Log', prepared['log_rows'], LOG_HEADERS)
    return {'history_added': len(prepared['history_rows']), 'master_added': len(prepared['master_rows']), 'aliases_added': len(prepared['alias_rows']), 'log_rows': len(prepared['log_rows'])}


def _repair_date(value):
    """Parse normal dates and Excel/Sheets serial dates without producing 1970."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return pd.NaT
    parsed = pd.to_datetime(value, errors='coerce')
    try:
        number = float(value)
        if 20000 <= number <= 80000:
            parsed = pd.Timestamp('1899-12-30') + pd.to_timedelta(number, unit='D')
    except (TypeError, ValueError, OverflowError):
        pass
    return pd.NaT if pd.isna(parsed) else pd.Timestamp(parsed).normalize()


def _repair_text(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ''
    return ' '.join(str(value).strip().lower().split())


def repair_dates_from_workbook(path: str | Path):
    """Repair blank Booking_Date/Arrival_Date rows from the original workbook.

    Matching uses city, hotel, price, and booking-company fields. Existing
    non-empty dates are preserved. Ambiguous matches are reported rather than
    guessed, so a repair cannot silently place a date on the wrong record.
    """
    source_records, _summary = load_daily_workbook(Path(path), import_id='REPAIR', import_date=datetime.now().strftime('%Y-%m-%d'))
    existing_rows = read_tab('Price_History')
    if not existing_rows or len(existing_rows) < 2:
        raise RuntimeError('Price_History is empty; there are no rows to repair.')
    headers = [str(x).strip() for x in existing_rows[0]]
    width = len(headers)
    body = [(list(row) + [''] * width)[:width] for row in existing_rows[1:]]
    frame = pd.DataFrame(body, columns=headers)
    for required in ('Booking_Date', 'Arrival_Date'):
        if required not in frame.columns:
            frame[required] = ''
            headers.append(required)
    if source_records is None or source_records.empty:
        return {'updated': 0, 'unmatched': len(frame), 'ambiguous': 0, 'total_existing': len(frame)}

    def source_key(row):
        return (
            _repair_text(row.get('City')), _repair_text(row.get('Hotel_ID')),
            _repair_text(row.get('Source_Hotel_Name')), _repair_text(row.get('Best_Price')),
            _repair_text(row.get('Best_Company')), _repair_text(row.get('Source_File')),
        )

    def existing_key(row):
        return (
            _repair_text(row.get('City')), _repair_text(row.get('Hotel_ID')),
            _repair_text(row.get('Source_Hotel_Name')), _repair_text(row.get('Best_Price')),
            _repair_text(row.get('Best_Company')), _repair_text(row.get('Source_File')),
        )

    candidates = {}
    for _, source in source_records.iterrows():
        candidates.setdefault(source_key(source), []).append(source)
    used = set()
    updated = unmatched = ambiguous = 0
    for idx, row in frame.iterrows():
        booking = _repair_date(row.get('Booking_Date'))
        arrival = _repair_date(row.get('Arrival_Date'))
        # Only rows with a missing date need repair.
        if not (pd.isna(booking) or pd.isna(arrival)):
            continue
        key = existing_key(row)
        matches = [s for s in candidates.get(key, []) if id(s) not in used]
        if not matches:
            # A fallback without Source_File handles sheets where that column
            # was renamed or truncated during the original upload.
            fallback = key[:-1]
            matches = [s for k, vals in candidates.items() if k[:-1] == fallback for s in vals if id(s) not in used]
        if not matches:
            unmatched += 1
            continue
        if len(matches) > 1:
            # Prefer a source row with both usable dates; otherwise report it.
            dated = [s for s in matches if not pd.isna(_repair_date(s.get('Booking_Date'))) and not pd.isna(_repair_date(s.get('Arrival_Date')))]
            if len(dated) == 1:
                matches = dated
            else:
                ambiguous += 1
                continue
        source = matches[0]
        used.add(id(source))
        new_booking = _repair_date(source.get('Booking_Date'))
        new_arrival = _repair_date(source.get('Arrival_Date'))
        if pd.isna(booking) and not pd.isna(new_booking):
            frame.at[idx, 'Booking_Date'] = new_booking.strftime('%Y-%m-%d')
            updated += 1
        if pd.isna(arrival) and not pd.isna(new_arrival):
            frame.at[idx, 'Arrival_Date'] = new_arrival.strftime('%Y-%m-%d')

    replace_tab('Price_History', [headers] + frame[headers].fillna('').astype(object).values.tolist())
    return {'updated': updated, 'unmatched': unmatched, 'ambiguous': ambiguous, 'total_existing': len(frame)}
