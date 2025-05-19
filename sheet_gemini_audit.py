import os
import json
import time
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from bs4 import BeautifulSoup
import google.generativeai as genai

# Load environment variables
load_dotenv()

SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}
CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Helper: get sheet
def get_sheet_by_industry(industry):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

# Helper: extract data from website
def extract_from_website(url, driver):
    try:
        driver.get(url)
        time.sleep(3)
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        # Company name
        name = None
        if soup.title and soup.title.string:
            name = soup.title.string.strip()
        meta_site = soup.find('meta', property='og:site_name')
        if not name and meta_site and meta_site.get('content'):
            name = meta_site['content'].strip()
        h1 = soup.find('h1')
        if not name and h1 and h1.text:
            name = h1.text.strip()
        # Description
        desc = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            desc = meta_desc['content'].strip()
        # Products (try to find product names in meta tags or headings)
        products = []
        for tag in soup.find_all(['h2', 'h3', 'li']):
            text = tag.get_text(strip=True)
            if text and any(word in text.lower() for word in ['product', 'platform', 'solution', 'ehr', 'pm', 'software']):
                products.append(text)
        products = list(set(products))
        return {
            "company_name": name,
            "description": desc,
            "products": ", ".join(products) if products else None
        }
    except Exception as e:
        print(f"Failed to extract from {url}: {e}")
        return {}

# Helper: call Gemini for audit
def audit_with_gemini(sheet_row, extracted_data):
    prompt = f"""
You are an expert data auditor for a software vendor database. Here is a row from a Google Sheet and the data extracted from the vendor's website. Compare the two and:
- List what is good (correct and matching)
- List what needs to be fixed (missing, incorrect, or misaligned fields)
- List any additional information you can infer or add from the website
Return a JSON object with:
{{
  "good": ["list of good fields"],
  "needs_fix": ["list of fields needing correction or missing"],
  "gemini_data": {{...extracted/inferred fields...}},
  "sheet_data": {{...original row...}}
}}

Sheet row:
{json.dumps(sheet_row, indent=2)}

Extracted data from website:
{json.dumps(extracted_data, indent=2)}

Audit report:
"""
    try:
        model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")
        response = model.generate_content(prompt)
        text = response.text
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            report = json.loads(text[start:end])
            return report
        else:
            print("Gemini response did not contain valid JSON.")
            return None
    except Exception as e:
        print(f"Gemini error: {e}")
        return None

def main():
    print("Select industry to audit:")
    for i, ind in enumerate(SHEET_URLS.keys(), 1):
        print(f"{i}. {ind}")
    idx = input("Enter number: ").strip()
    try:
        industry = list(SHEET_URLS.keys())[int(idx)-1]
    except Exception:
        print("Invalid selection.")
        return
    sheet = get_sheet_by_industry(industry)
    current_headers = sheet.row_values(1)
    # Use expected_headers to avoid duplicate header error
    records = sheet.get_all_records(expected_headers=current_headers)
    genai.configure(api_key=GEMINI_API_KEY)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    report = []
    for idx, record in enumerate(records, start=2):
        url = record.get('website', '')
        if not url:
            continue
        print(f"Auditing row {idx} ({url})...")
        extracted = extract_from_website(url, driver)
        audit = audit_with_gemini(record, extracted)
        if audit:
            audit['row'] = idx
            report.append(audit)
    driver.quit()
    with open(f"sheet_gemini_audit_{industry}.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"Audit complete. Report saved to sheet_gemini_audit_{industry}.json.")

if __name__ == "__main__":
    main() 