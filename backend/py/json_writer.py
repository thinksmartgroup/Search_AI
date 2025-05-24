import os
import json
import gspread
from dotenv import load_dotenv
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Define headers with all possible fields
HEADERS = [
    "website",
    "company_name",
    "description",
    "products",
    "is_primary_vendor",
    "confidence_score",
    "evidence",
    "industry",
    "source",
    "platform_type",
    "platform_score"
]

SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]

def normalize_url(url):
    """Normalize URL for comparison"""
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "").strip()

def get_sheet_by_industry(industry):
    """Get Google Sheet for specific industry"""
    industry = industry.lower().strip()
    if industry not in SHEET_URLS:
        raise ValueError(f"❌ Unsupported industry: '{industry}'")
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

def ensure_sheet_headers(sheet):
    """Ensure sheet has correct headers"""
    try:
        current_headers = sheet.row_values(1)
        if not current_headers or set(current_headers) != set(HEADERS):
            print("⚠️ Fixing sheet headers...")
            # Clear the sheet
            sheet.clear()
            # Add headers
            sheet.insert_row(HEADERS, 1)
            print("✅ Headers fixed")
            return True
        return False
    except Exception as e:
        print(f"❌ Error checking headers: {e}")
        return False

def update_google_sheet(vendors, industry):
    """Update Google Sheet with vendor data"""
    try:
        sheet = get_sheet_by_industry(industry)
        
        # Ensure headers are correct
        ensure_sheet_headers(sheet)
        
        # Get existing data
        existing_rows = sheet.get_all_records()
        
        # Get existing websites for deduplication
        existing_websites = {normalize_url(row.get("website", "")) for row in existing_rows}
        
        # Prepare new rows
        new_rows = []
        for vendor in vendors:
            # Skip if website is empty or already exists
            website = normalize_url(vendor.get("website", ""))
            if not website or website in existing_websites:
                continue
                
            # Add to existing websites set
            existing_websites.add(website)
            
            # Prepare row with all fields
            row = {
                "website": vendor.get("website", ""),
                "company_name": vendor.get("company_name", ""),
                "description": vendor.get("description", ""),
                "products": json.dumps(vendor.get("products", [])),
                "is_primary_vendor": vendor.get("is_primary_vendor", False),
                "confidence_score": vendor.get("confidence_score", 0),
                "evidence": vendor.get("evidence", ""),
                "industry": vendor.get("industry", industry),
                "source": vendor.get("source", "gemini"),
                "platform_type": vendor.get("platform_type", "Practice Management Software"),
                "platform_score": vendor.get("platform_score", 1.0)
            }
            
            # Convert row to list in header order
            row_list = [row.get(header, "") for header in HEADERS]
            new_rows.append(row_list)
        
        # Add new rows
        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
            print(f"✅ Added {len(new_rows)} new vendors to {industry} sheet")
            return len(new_rows)
        else:
            print(f"⚠️ No new vendors found for {industry} sheet")
            return 0
            
    except Exception as e:
        print(f"❌ Error updating sheet: {e}")
        print("Attempting to fix sheet...")
        try:
            # Try to fix the sheet by clearing and reinitializing
            sheet.clear()
            sheet.insert_row(HEADERS, 1)
            print("✅ Sheet reinitialized with correct headers")
            # Try the update again
            return update_google_sheet(vendors, industry)
        except Exception as e2:
            print(f"❌ Failed to fix sheet: {e2}")
            return 0

def write_vendors_grouped_by_industry(vendors):
    """Write vendors to sheets grouped by industry"""
    industry_map = {}
    for vendor in vendors:
        industry = vendor.get("industry", "").lower().strip()
        if not industry:
            continue
        industry_map.setdefault(industry, []).append(vendor)

    total_written = 0
    for industry, group in industry_map.items():
        try:
            written = update_google_sheet(group, industry)
            total_written += written
        except ValueError as e:
            print(e)
            continue
            
    return total_written

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
        total_written = write_vendors_grouped_by_industry(vendors)
        print(f"✅ Total vendors written: {total_written}")
