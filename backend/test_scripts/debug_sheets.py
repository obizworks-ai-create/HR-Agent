from services.sheets import read_sheet, get_source_sheet_name
import json

print("--- DEBUGGING SHEET CONTENT ---")

# 1. Check ActiveJobSheet
print("\n[ActiveJobSheet]")
try:
    jd_rows = read_sheet("ActiveJobSheet!A:B")
    print(f"Total Rows: {len(jd_rows)}")
    if len(jd_rows) > 0:
        print(f"Header: {jd_rows[0]}")
    if len(jd_rows) > 1:
        print(f"Last Row: {jd_rows[-1]}")
        try:
            print("Parsed JSON:", json.loads(jd_rows[-1][1]).keys())
        except Exception as e:
            print(f"JSON Parse Error: {e}")
    else:
        print("WARNING: No data rows found!")
except Exception as e:
    print(f"Error reading ActiveJobSheet: {e}")

# 2. Check Source Sheet
print("\n[Source Sheet]")
try:
    source = get_source_sheet_name()
    print(f"Determined Source Name: {source}")
    rows = read_sheet(f"{source}!A:I", value_render_option='FORMULA')
    print(f"Total Rows: {len(rows)}")
    if len(rows) > 0:
        print(f"Row 0: {rows[0]}")
    if len(rows) > 1:
        print(f"Row 1: {rows[1]}")
except Exception as e:
    print(f"Error reading Source Sheet: {e}")
