import os
import json
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import urlparse
from collections import defaultdict

# Load environment variables
load_dotenv()

SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}
CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]

# Helper to normalize URLs
def normalize_url(url):
    if not url:
        return ""
    url = url.strip().lower()
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return parsed.netloc.replace("www.", "")

# Helper to standardize company names
def normalize_company_name(name):
    if not name:
        return ""
    return name.strip().replace("Inc.", "Inc").replace("LLC", "LLC").replace("Ltd.", "Ltd").replace("  ", " ")

# Helper to merge product lists
def merge_products(prod1, prod2):
    set1 = set([p.strip() for p in prod1.split(",") if p.strip()]) if prod1 else set()
    set2 = set([p.strip() for p in prod2.split(",") if p.strip()]) if prod2 else set()
    return ", ".join(sorted(set1 | set2))

# Helper to merge descriptions
def merge_descriptions(desc1, desc2):
    if desc1 and desc2:
        if desc1 == desc2:
            return desc1
        return f"{desc1} | {desc2}"
    return desc1 or desc2 or ""

# Helper to merge evidence
def merge_evidence(ev1, ev2):
    if ev1 and ev2:
        if ev1 == ev2:
            return ev1
        return f"{ev1} | {ev2}"
    return ev1 or ev2 or ""

# Main deduplication and cleaning function
def deduplicate_and_clean(sheet):
    records = sheet.get_all_records()
    current_headers = sheet.row_values(1)
    deduped = {}
    log = []
    for record in records:
        url_key = normalize_url(record.get("website", ""))
        name_key = normalize_company_name(record.get("company_name", ""))
        key = url_key or name_key
        if not key:
            continue
        if key not in deduped:
            deduped[key] = record.copy()
        else:
            # Merge products
            deduped[key]["products"] = merge_products(deduped[key].get("products", ""), record.get("products", ""))
            # Merge descriptions
            deduped[key]["description"] = merge_descriptions(deduped[key].get("description", ""), record.get("description", ""))
            # Merge evidence
            deduped[key]["evidence"] = merge_evidence(deduped[key].get("evidence", ""), record.get("evidence", ""))
            # Prefer non-empty fields for company name, website
            if not deduped[key].get("company_name") and record.get("company_name"):
                deduped[key]["company_name"] = record.get("company_name")
            if not deduped[key].get("website") and record.get("website"):
                deduped[key]["website"] = record.get("website")
            # Log the merge
            log.append({"merged": [deduped[key], record]})
    # Standardize all fields
    cleaned = []
    for rec in deduped.values():
        rec["company_name"] = normalize_company_name(rec.get("company_name", ""))
        rec["website"] = rec.get("website", "").strip()
        rec["products"] = ", ".join(sorted(set([p.strip() for p in rec.get("products", "").split(",") if p.strip()])))
        cleaned.append([rec.get(h, "") for h in current_headers])
    return cleaned, log

def main():
    print("Select industry to deduplicate:")
    for i, ind in enumerate(SHEET_URLS.keys(), 1):
        print(f"{i}. {ind}")
    idx = input("Enter number: ").strip()
    try:
        industry = list(SHEET_URLS.keys())[int(idx)-1]
    except Exception:
        print("Invalid selection.")
        return
    sheet = get_sheet_by_industry(industry)
    print(f"Deduplicating and cleaning {industry} sheet...")
    cleaned, log = deduplicate_and_clean(sheet)
    # Clear and rewrite sheet
    sheet.clear()
    sheet.insert_row(sheet.row_values(1), 1)
    if cleaned:
        sheet.append_rows(cleaned, value_input_option="USER_ENTERED")
    with open(f"deduplication_log_{industry}.json", "w") as f:
        json.dump(log, f, indent=2)
    print(f"Deduplication complete. Log saved to deduplication_log_{industry}.json.")

def get_sheet_by_industry(industry):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

if __name__ == "__main__":
    main() 