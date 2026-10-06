from __future__ import annotations

from pathlib import Path
from datetime import date
import re
import sys
from openpyxl import load_workbook, Workbook


def temperature(value):
    if value is None or str(value).strip() == "":
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", str(value).replace("٫", "."))
    return float(m.group()) if m else None


def normalize(input_path: str, output_path: str, start_year: int = 2026, start_month: int = 9):
    src = load_workbook(input_path, read_only=True, data_only=True)
    ws = src.active
    cities = [ws.cell(1, c).value for c in range(2, ws.max_column + 1)]
    records = []
    raw_rows = []
    current_month = start_month
    previous_day = None
    for r in range(2, ws.max_row + 1):
        for c, city in enumerate(cities, start=2):
            if not city:
                continue
            raw_day = ws.cell(r, c).value
            high = ws.cell(r + 1, c).value if r + 1 <= ws.max_row else None
            low = ws.cell(r + 2, c).value if r + 2 <= ws.max_row else None
            # A valid day starts a 3-row block; rows containing temperatures are skipped.
            if not isinstance(raw_day, (int, float)):
                continue
            day = int(raw_day)
            if day == 0:
                status = "Invalid day value"
                iso = ""
            else:
                if previous_day is not None and day < previous_day:
                    current_month += 1
                try:
                    iso = date(start_year, current_month, day).isoformat()
                    status = "Parsed"
                except ValueError:
                    iso = ""
                    status = "Invalid calendar date"
            raw_rows.append([city, raw_day, high, low, r, status])
            records.append([
                f"WX-{len(records)+1:05d}", str(city).strip(), "", iso, day,
                temperature(high), temperature(low), str(high or ""), str(low or ""),
                "Celsius assumed from source symbol", input_path, ws.title, r, status
            ])
        if isinstance(ws.cell(r, 2).value, (int, float)) and int(ws.cell(r, 2).value) != 0:
            previous_day = int(ws.cell(r, 2).value)

    out = Workbook()
    normalized = out.active
    normalized.title = "Weather_Normalized"
    normalized.append(["Weather_ID", "City", "Country", "Forecast_Date", "Day", "Temperature_Max", "Temperature_Min", "Raw_Max", "Raw_Min", "Unit_Note", "Source_File", "Source_Sheet", "Source_Row", "Status"])
    for row in records:
        normalized.append(row)
    raw = out.create_sheet("Weather_Raw")
    raw.append(["City", "Raw_Day", "Raw_Max", "Raw_Min", "Source_Row", "Status"])
    for row in raw_rows:
        raw.append(row)
    out.save(output_path)
    print(f"created {output_path}: {len(records)} records")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("Usage: python normalize_weather.py Weather.xlsx Weather_Normalized.xlsx")
    normalize(sys.argv[1], sys.argv[2])
