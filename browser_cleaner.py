import os
import json
import time
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}
CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]

HEADERS = [
    "company_name",
    "website",
    "description",
    "products",
    "is_primary_vendor",
    "confidence_score",
    "evidence",
    "industry",
    "source",
    "platform_type",
    "platform_score",
    "deployment_model",
    "deployment_marking",
    "deployment_characteristics",
    "company_size",
    "founding_year",
    "technology_stack",
    "integration_capabilities",
    "compliance_certifications",
    "pricing_model",
    "hosting_type",
    "created_at",
    "updated_at"
]

def get_sheet_by_industry(industry):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

def extract_company_name_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Try title
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    # Try meta og:site_name
    meta_site = soup.find('meta', property='og:site_name')
    if meta_site and meta_site.get('content'):
        return meta_site['content'].strip()
    # Try h1
    h1 = soup.find('h1')
    if h1 and h1.text:
        return h1.text.strip()
    # Try meta name="application-name"
    meta_app = soup.find('meta', attrs={'name': 'application-name'})
    if meta_app and meta_app.get('content'):
        return meta_app['content'].strip()
    return None

def clean_products_field(products):
    if not products:
        return ""
    # If it's a JSON string, try to parse and format
    try:
        parsed = json.loads(products)
        if isinstance(parsed, list):
            return ", ".join(
                p.get('Product') or p.get('product') or str(p) for p in parsed
            )
        elif isinstance(parsed, dict):
            return ", ".join(f"{k}: {v}" for k, v in parsed.items())
        else:
            return str(parsed)
    except Exception:
        # If not JSON, just return as is
        return products

def main():
    print("Starting browser-based cleaning of vendor sheets...")
    
    # Set up Selenium Chrome driver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    
    for industry in SHEET_URLS.keys():
        print(f"\nProcessing {industry} sheet...")
        sheet = get_sheet_by_industry(industry)
        records = sheet.get_all_records()
        # Dynamically fetch current headers
        current_headers = sheet.row_values(1)
        updated_rows = []
        for idx, record in enumerate(records, start=2):  # start=2 to skip header
            changed = False
            # Fix company_name if missing
            if not record.get('company_name') and record.get('website'):
                url = record['website']
                print(f"Visiting {url} to extract company name...")
                try:
                    driver.get(url)
                    time.sleep(3)  # Wait for page to load
                    html = driver.page_source
                    name = extract_company_name_from_html(html)
                    if name:
                        print(f"Extracted company name: {name}")
                        record['company_name'] = name
                        changed = True
                except WebDriverException as e:
                    print(f"Failed to load {url}: {e}")
            # Clean products field
            products = record.get('products', '')
            cleaned_products = clean_products_field(products)
            if cleaned_products != products:
                print(f"Cleaned products for row {idx}: {cleaned_products}")
                record['products'] = cleaned_products
                changed = True
            # If any changes, update the row
            if changed:
                # Only update columns that exist in the sheet
                row = [record.get(header, "") for header in current_headers]
                range_end = chr(ord('A') + len(current_headers) - 1)
                sheet.update(range_name=f"A{idx}:{range_end}{idx}", values=[row])
                updated_rows.append(idx)
        print(f"Updated {len(updated_rows)} rows in {industry} sheet.")
    driver.quit()
    print("Cleaning complete.")

if __name__ == "__main__":
    main() 