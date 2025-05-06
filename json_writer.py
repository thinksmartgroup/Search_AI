import os
import json
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials

HEADERS = [
    "website", "email", "phone", "summary", "industry",
    "prompt", "source_page", "platform_type", "platform_score"
]

load_dotenv()

SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]

def get_sheet_by_industry(industry):
    industry = industry.lower().strip()
    if industry not in SHEET_URLS:
        raise ValueError(f"❌ Unsupported industry: '{industry}'")
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

def load_vendors_from_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return data.get("vendors", [])

def write_vendors_grouped_by_industry(vendors):
    industry_map = {}
    for vendor in vendors:
        industry = vendor.get("industry", "").lower().strip()
        if not industry:
            continue
        industry_map.setdefault(industry, []).append(vendor)

    for industry, group in industry_map.items():
        try:
            sheet = get_sheet_by_industry(industry)
        except ValueError as e:
            print(e)
            continue

        existing = sheet.get_all_values()
        if not existing or existing[0] != HEADERS:
            sheet.insert_row(HEADERS, index=1)

        rows = [[vendor.get(col, "") for col in HEADERS] for vendor in group]
        sheet.append_rows(rows, value_input_option="USER_ENTERED")
        print(f"✅ Added {len(rows)} rows to [{industry}]")

if __name__ == "__main__":
    import glob

    print("📁 Available JSON log files:\n")
    json_files = sorted(glob.glob("vendor_logs/*.json"))
    for i, f in enumerate(json_files, 1):
        print(f"{i}. {os.path.basename(f)}")

    selected = input("\n🔢 Enter comma-separated file numbers to upload (e.g., 1,3,5):\n> ")
    indexes = [int(i.strip()) for i in selected.split(",")]

    for i in indexes:
        json_path = json_files[i - 1]
        print(f"\n📤 Pushing vendors from '{os.path.basename(json_path)}'")
        vendors = load_vendors_from_json(json_path)
        write_vendors_grouped_by_industry(vendors)
