from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

DAILY_HEADERS = [
    'Hotel_Name', 'Rate', 'Rating', 'rates_no', 'location', 'Desc', 'Desc2',
    'Place1', 'Price1', 'price2', 'place2', 'price3', 'place3',
    'Note 1', 'Distance From places', 'Note 2', 'Note 3', 'Star',
    'start book', 'date of creat booking', 'day of book', 'day of arrival'
]

HEADER_ALIASES = {
    'Hotel_Name': ['Hotel_Name', 'hotel_name', 'hotel', 'Hotel'],
    'Rate': ['Rate', 'rate'],
    'Rating': ['Rating', 'rating'],
    'rates_no': ['rates_no', 'ratings_no'],
    'location': ['location', 'area'],
    'Desc': ['Desc', 'description'],
    'Desc2': ['Desc2', 'desc2'],
    'Place1': ['Place1', 'place1'],
    'Price1': ['Price1', 'price1', 'Price 1', 'Price', 'price'],
    'price2': ['price2', 'Price2', 'Price 2'],
    'place2': ['place2', 'Place2'],
    'price3': ['price3', 'Price3', 'Price 3', 'price3dup'],
    'place3': ['place3', 'Place3'],
    'Note 1': ['Note 1', 'Note1'],
    'Distance From places': ['Distance From places', 'Distance', 'distance'],
    'Note 2': ['Note 2', 'Note2'],
    'Note 3': ['Note 3', 'Note3'],
    'Star': ['Star', 'stars', 'Stars'],
    'start book': ['start book', 'Start book'],
    'date of creat booking': ['date of creat booking', 'Booking Date', 'booking_date'],
    'day of book': ['day of book', 'Booking Day'],
    'day of arrival': ['day of arrival', 'Arrival Day'],
}


def clean_text(value) -> str:
    if pd.isna(value):
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


def normalize_name(value) -> str:
    text = clean_text(value).lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace('&', ' and ')
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def clean_price(value):
    if pd.isna(value):
        return np.nan
    matches = re.findall(r'\d+(?:[.,]\d+)?', str(value).replace(',', ''))
    if not matches:
        return np.nan
    try:
        result = float(matches[0])
        return result if result > 0 else np.nan
    except ValueError:
        return np.nan


def parse_date(value, reference_year: int | None = None):
    if pd.isna(value) or clean_text(value) == '':
        return pd.NaT
    if isinstance(value, (datetime, pd.Timestamp)):
        return pd.Timestamp(value).normalize()
    text = clean_text(value)
    parsed = pd.to_datetime(text, errors='coerce', dayfirst=False)
    if not pd.isna(parsed):
        return pd.Timestamp(parsed).normalize()
    year = reference_year or datetime.now().year
    for fmt in ('%d-%b', '%d-%B', '%m-%d-%y', '%m/%d/%y', '%d/%m/%y'):
        parsed = pd.to_datetime(f'{text}-{year}' if fmt in ('%d-%b', '%d-%B') else text, format=fmt, errors='coerce')
        if not pd.isna(parsed):
            return pd.Timestamp(parsed).normalize()
    return pd.NaT


def find_column(columns: Iterable[str], aliases: Iterable[str]):
    normalized = {str(c).strip().lower(): c for c in columns}
    for alias in aliases:
        if alias.lower() in normalized:
            return normalized[alias.lower()]
    return None


def normalize_city(sheet_name: str) -> str:
    key = normalize_name(sheet_name).replace(' ', '')
    mapping = {
        'paris': 'Paris', 'london': 'London', 'newyork': 'NewYork',
        'dubai': 'Dubai', 'istanbul': 'Istanbul', 'cairo': 'Cairo',
        'switzerland': 'Switzerland', 'switherland': 'Switzerland',
    }
    return mapping.get(key, clean_text(sheet_name))


def hotel_id(city: str, normalized: str) -> str:
    prefix = re.sub(r'[^A-Z]', '', city.upper())[:3] or 'HOT'
    digest = hashlib.sha1(f'{city}|{normalized}'.encode('utf-8')).hexdigest()[:8].upper()
    return f'{prefix}-{digest}'


def infer_arrival_date(booking_date, arrival_value):
    booking_date = parse_date(booking_date)
    if pd.isna(booking_date) or pd.isna(arrival_value):
        return pd.NaT
    text = clean_text(arrival_value)
    direct = parse_date(arrival_value)
    # A parsed full date is preferred. If the source contains only a weekday,
    # infer the next occurrence after the booking date.
    if not pd.isna(direct) and not re.fullmatch(r'[A-Za-zÀ-ÿ]+', text):
        return direct
    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
    }
    target = days.get(text.lower())
    if target is None:
        return pd.NaT
    delta = (target - booking_date.weekday()) % 7
    if delta == 0:
        delta = 7
    return booking_date + pd.Timedelta(days=delta)


def record_hash(row: pd.Series) -> str:
    values = '|'.join(clean_text(row.get(k, '')) for k in (
        'City', 'Hotel_ID', 'Booking_Date', 'Arrival_Date', 'Best_Price', 'Best_Company',
        'Price1', 'Company1', 'Price2', 'Company2', 'Price3', 'Company3'))
    return hashlib.sha256(values.encode('utf-8')).hexdigest()


def read_city_sheet(ws: pd.DataFrame, city: str, source_file: str, import_id: str, import_date: str) -> Tuple[pd.DataFrame, dict]:
    df = ws.copy()
    df.columns = [str(c).strip() for c in df.columns]
    mapped = {}
    for canonical, aliases in HEADER_ALIASES.items():
        source = find_column(df.columns, aliases)
        if source is None:
            df[canonical] = np.nan
        else:
            mapped[canonical] = source
            if source != canonical:
                df[canonical] = df[source]
    df['City'] = normalize_city(city)
    df['Source_File'] = source_file
    df['Import_ID'] = import_id
    df['Import_Date'] = import_date
    df['Source_Hotel_Name'] = df['Hotel_Name'].map(clean_text)
    df['Normalized_Name'] = df['Hotel_Name'].map(normalize_name)
    df['Hotel_ID'] = [hotel_id(c, n) if n else '' for c, n in zip(df['City'], df['Normalized_Name'])]
    for col in ('Price1', 'price2', 'price3'):
        df[col] = df[col].map(clean_price)
    df['Best_Price'] = df[['Price1', 'price2', 'price3']].min(axis=1, skipna=True)
    df['Best_Company'] = ''
    for idx, row in df.iterrows():
        for price_col, company_col in (('Price1', 'Place1'), ('price2', 'place2'), ('price3', 'place3')):
            if pd.notna(row[price_col]) and clean_text(row[company_col]):
                df.at[idx, 'Best_Company'] = clean_text(row[company_col])
                break
    df['Booking_Date'] = df['date of creat booking'].map(parse_date)
    if df['Booking_Date'].isna().all():
        df['Booking_Date'] = df['start book'].map(parse_date)
    # Full dates are preferred; day names are retained as labels for later inference.
    df['Arrival_Date'] = [infer_arrival_date(b, a) for b, a in zip(df['Booking_Date'], df['day of arrival'])]
    df['Rate'] = pd.to_numeric(df['Rate'], errors='coerce')
    df['Stars'] = pd.to_numeric(df['Star'].astype(str).str.extract(r'(\d+(?:\.\d+)?)')[0], errors='coerce')
    df['Rating_Label'] = df['Rating'].map(clean_text)
    df['Location'] = df['location'].map(clean_text)
    df['Description'] = df['Desc'].map(clean_text)
    df['Record_Hash'] = df.apply(record_hash, axis=1)
    # Only non-empty hotel records are eligible for import.
    df = df[df['Normalized_Name'] != ''].copy()
    price_history_cols = [
        'Import_ID', 'Import_Date', 'Booking_Date', 'Arrival_Date', 'City', 'Hotel_ID',
        'Source_Hotel_Name', 'Best_Price', 'Best_Company', 'Price1', 'Place1',
        'price2', 'place2', 'price3', 'place3', 'Rate', 'Rating_Label', 'Stars',
        'Location', 'Description', 'Source_File', 'Record_Hash'
    ]
    out = df[price_history_cols].rename(columns={
        'Place1': 'Company1', 'price2': 'Price2', 'place2': 'Company2',
        'price3': 'Price3', 'place3': 'Company3'
    })
    summary = {
        'city': normalize_city(city), 'rows_read': len(ws), 'rows_eligible': len(out),
        'rows_with_price': int(out['Best_Price'].notna().sum()),
        'rows_missing_booking_date': int(out['Booking_Date'].isna().sum()),
        'rows_missing_arrival_date': int(out['Arrival_Date'].isna().sum()),
        'unique_hotels': int(out['Hotel_ID'].nunique()),
        'missing_headers': [k for k in HEADER_ALIASES if k not in mapped],
    }
    return out, summary


def load_daily_workbook(path: str | Path, import_id: str | None = None, import_date: str | None = None):
    path = Path(path)
    import_id = import_id or f'IMP-{datetime.now():%Y%m%d-%H%M%S}'
    import_date = import_date or f'{datetime.now():%Y-%m-%d}'
    sheets = pd.read_excel(path, sheet_name=None)
    records, summaries = [], []
    for sheet_name, frame in sheets.items():
        prepared, summary = read_city_sheet(frame, sheet_name, path.name, import_id, import_date)
        records.append(prepared)
        summaries.append(summary)
    combined = pd.concat(records, ignore_index=True) if records else pd.DataFrame()
    if not combined.empty:
        combined = combined.drop_duplicates(subset=['Record_Hash']).reset_index(drop=True)
    return combined, pd.DataFrame(summaries)
