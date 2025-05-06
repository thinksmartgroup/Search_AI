import os
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urlparse
import json

# Load environment variables
load_dotenv()

# Load spreadsheet URLs
INDUSTRY_SHEET_MAP = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto repair": os.getenv("AUTO_REPAIR_SHEET_URL"),
}

# Load scopes
SCOPE_FEEDS = os.getenv("SCOPE_FEEDS")
SCOPE_DRIVE = os.getenv("SCOPE_DRIVE")
scope = [SCOPE_FEEDS, SCOPE_DRIVE]

# Load and validate credentials
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
if not GOOGLE_CREDENTIALS_FILE or not os.path.isfile(GOOGLE_CREDENTIALS_FILE):
    raise FileNotFoundError("❌ GOOGLE_CREDENTIALS_FILE is missing or not found on disk.")

credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
gc = gspread.authorize(credentials)

def normalize_url(url):
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "").strip()

def get_sheet_by_industry(industry):
    sheet_url = INDUSTRY_SHEET_MAP.get(industry.lower())
    if not sheet_url:
        raise ValueError(f"❌ No sheet found for industry: {industry}")
    return gc.open_by_url(sheet_url).sheet1

def update_google_sheet(vendors, industry):
    sheet = get_sheet_by_industry(industry)
    existing_rows = sheet.get_all_records()

    existing_products = set()
    for row in existing_rows:
        product_name = row.get("product", "").strip().lower()
        if product_name:
            existing_products.add(product_name)

    headers = sheet.row_values(1)
    new_rows = []

    for vendor in vendors:
        product_name = vendor.get("product", "").strip().lower()
        if not product_name or product_name in existing_products:
            continue

    # Add missing headers
    for key in vendor.keys():
        if key not in headers:
            headers.append(key)
            sheet.update_cell(1, len(headers), key)

    row = [ json.dumps(vendor[header]) if isinstance(vendor.get(header), (list, dict)) else vendor.get(header, "")
            for header in headers]
    new_rows.append(row)
    existing_products.add(product_name)


    if new_rows:
        sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
        print(f"✅ Added {len(new_rows)} new vendors to {industry} sheet")
        return len(new_rows)
    else:
        print(f"⚠️ No new vendors found for {industry} sheet")
        return 0
