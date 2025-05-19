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

def extract_from_website(url):
    """Visit the website and extract company name, products, and description."""
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
        # Remove duplicates
        products = list(set(products))
        return {
            "company_name": name,
            "description": desc,
            "products": ", ".join(products) if products else None
        }
    except Exception as e:
        print(f"Failed to extract from {url}: {e}")
        return {}

def call_gemini(original_row, extracted_data):
    """Use Gemini to intelligently correct the row."""
    prompt = f"""
You are an expert data cleaner for a software vendor database. Here is a row from a Google Sheet and the data extracted from the vendor's website. Identify and correct any mistakes, such as swapped company names and products, missing or misaligned fields, or other inconsistencies. Return the corrected row as a JSON object with the same fields as the original row. If the original row is correct, return it unchanged.

Original row:
{json.dumps(original_row, indent=2)}

Extracted data from website:
{json.dumps(extracted_data, indent=2)}

Corrected row:
"""
    try:
        model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")
        response = model.generate_content(prompt)
        # Try to extract JSON from the response
        if hasattr(response, 'text') and response.text:
            text = response.text
        else:
            # Fallback for other response structures
            text = response.candidates[0].content.parts[0].text
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != -1:
            corrected = json.loads(text[start:end])
            return corrected
        else:
            print("Gemini response did not contain valid JSON.")
            return original_row
    except Exception as e:
        print(f"Gemini error: {e}")
        return original_row

def main():
    print("Starting intelligent browser-based cleaning of vendor sheets...")
    genai.configure(api_key=GEMINI_API_KEY)
    global driver
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=chrome_options)
    log = []
    for industry in SHEET_URLS.keys():
        print(f"\nProcessing {industry} sheet...")
        sheet = get_sheet_by_industry(industry)
        records = sheet.get_all_records()
        current_headers = sheet.row_values(1)
        updated_rows = []
        for idx, record in enumerate(records, start=2):
            url = record.get('website', '')
            if not url:
                continue
            extracted = extract_from_website(url)
            corrected = call_gemini(record, extracted)
            # Only update if corrected row is different
            if corrected and corrected != record:
                row = [corrected.get(header, "") for header in current_headers]
                range_end = chr(ord('A') + len(current_headers) - 1)
                sheet.update(range_name=f"A{idx}:{range_end}{idx}", values=[row])
                updated_rows.append(idx)
                log.append({"row": idx, "before": record, "after": corrected})
                print(f"Row {idx} updated.")
        print(f"Updated {len(updated_rows)} rows in {industry} sheet.")
    driver.quit()
    # Save log
    with open("intelligent_cleaner_log.json", "w") as f:
        json.dump(log, f, indent=2)
    print("Intelligent cleaning complete. Log saved to intelligent_cleaner_log.json.")

if __name__ == "__main__":
    main() 