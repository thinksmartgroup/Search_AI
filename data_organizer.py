import os
import json
import glob
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
import time
import re

# Load environment variables
load_dotenv()

# Get sheet URLs from environment
SHEET_URLS = {
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

# Define the standard headers
STANDARD_HEADERS = [
    "company_name",
    "website",
    "products",
    "industry",
    "confidence",
    "evidence",
    "source"
]

class DataOrganizer:
    def __init__(self):
        self.setup_google_sheets()
        self.setup_playwright()
        self.organized_data = {industry: [] for industry in SHEET_URLS.keys()}
        
    def setup_google_sheets(self):
        """Initialize Google Sheets connection"""
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        self.client = gspread.authorize(creds)
        
    def setup_playwright(self):
        """Initialize Playwright browser"""
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        
    def get_sheet_data(self, industry):
        """Get data from Google Sheet"""
        try:
            sheet_url = SHEET_URLS.get(industry)
            if not sheet_url:
                print(f"No sheet URL found for {industry}")
                return []
                
            sheet = self.client.open_by_url(sheet_url).sheet1
            data = sheet.get_all_values()
            
            if len(data) <= 1:  # Only headers or empty
                return []
                
            # Get headers and data
            headers = data[0]
            rows = data[1:]
            
            # Convert to dictionary format
            sheet_data = []
            for row in rows:
                vendor = {}
                for i, value in enumerate(row):
                    if i < len(headers):
                        vendor[headers[i]] = value
                sheet_data.append(vendor)
                
            return sheet_data
            
        except Exception as e:
            print(f"Error getting sheet data for {industry}: {str(e)}")
            return []
            
    def get_log_data(self, industry):
        """Get data from log files"""
        try:
            # Pattern: industry_*.json
            pattern = f"vendor_logs/{industry}_*.json"
            log_files = glob.glob(pattern)
            
            log_data = []
            for log_file in log_files:
                with open(log_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # New format with merged array
                        for vendor_group in data:
                            if isinstance(vendor_group, dict) and "merged" in vendor_group:
                                log_data.extend(vendor_group["merged"])
                    elif isinstance(data, dict):
                        # Old format with vendors array
                        log_data.extend(data.get("vendors", []))
                        
            return log_data
            
        except Exception as e:
            print(f"Error getting log data for {industry}: {str(e)}")
            return []
            
    def scrape_website(self, url):
        """Scrape additional data from vendor website"""
        try:
            page = self.browser.new_page()
            page.goto(url, wait_until='networkidle')
            
            # Extract company information
            data = {
                'description': '',
                'products': [],
                'company_size': '',
                'technology_stack': []
            }
            
            # Get meta description
            meta_desc = page.query_selector('meta[name="description"]')
            if meta_desc:
                data['description'] = meta_desc.get_attribute('content')
                
            # Get main content
            main_content = page.query_selector('main') or page.query_selector('body')
            if main_content:
                text = main_content.inner_text()
                data['description'] = data['description'] or text[:500]  # First 500 chars if no meta
                
            # Look for product information
            product_elements = page.query_selector_all('a[href*="product"], a[href*="solution"]')
            data['products'] = [el.inner_text() for el in product_elements if el.inner_text().strip()]
            
            # Look for company size indicators
            size_indicators = ['employees', 'team', 'company size', 'about us']
            for indicator in size_indicators:
                elements = page.query_selector_all(f'text/{indicator}')
                for el in elements:
                    parent = el.evaluate('node => node.parentElement')
                    if parent:
                        data['company_size'] = parent.inner_text()
                        break
                        
            # Look for technology stack
            tech_indicators = ['technology', 'stack', 'platform', 'built with']
            for indicator in tech_indicators:
                elements = page.query_selector_all(f'text/{indicator}')
                for el in elements:
                    parent = el.evaluate('node => node.parentElement')
                    if parent:
                        data['technology_stack'] = parent.inner_text().split(',')
                        break
                        
            page.close()
            return data
            
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return {}
            
    def standardize_data(self, data, industry):
        """Standardize data to match headers"""
        standardized = {}
        
        # Map existing fields
        for header in STANDARD_HEADERS:
            value = data.get(header, '')
            if isinstance(value, (list, dict)):
                value = str(value)
            standardized[header] = value
            
        # Set industry
        standardized['industry'] = industry
        
        # Set timestamps
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if not standardized['created_at']:
            standardized['created_at'] = now
        standardized['updated_at'] = now
        
        return standardized
        
    def organize_data(self):
        """Organize all data sources"""
        for industry in SHEET_URLS.keys():
            print(f"\nProcessing {industry}...")
            
            # Get data from all sources
            sheet_data = self.get_sheet_data(industry)
            log_data = self.get_log_data(industry)
            
            # Combine and deduplicate data
            all_data = {}
            for source in [sheet_data, log_data]:
                for vendor in source:
                    company_name = vendor.get('company_name', '').lower()
                    if company_name:
                        if company_name not in all_data:
                            all_data[company_name] = vendor
                        else:
                            # Merge data, preferring non-empty values
                            for key, value in vendor.items():
                                if value and not all_data[company_name].get(key):
                                    all_data[company_name][key] = value
                                    
            # Scrape additional data for vendors with websites
            for company_name, vendor in all_data.items():
                website = vendor.get('website')
                if website and not vendor.get('description'):
                    print(f"Scraping {website}...")
                    scraped_data = self.scrape_website(website)
                    vendor.update(scraped_data)
                    
            # Standardize all data
            self.organized_data[industry] = [
                self.standardize_data(vendor, industry)
                for vendor in all_data.values()
            ]
            
    def save_to_sheets(self):
        """Save organized data back to sheets"""
        for industry, data in self.organized_data.items():
            try:
                sheet_url = SHEET_URLS.get(industry)
                if not sheet_url:
                    continue
                    
                sheet = self.client.open_by_url(sheet_url).sheet1
                
                # Prepare data for sheet
                sheet_data = [STANDARD_HEADERS]  # Headers
                for vendor in data:
                    row = [vendor.get(header, '') for header in STANDARD_HEADERS]
                    sheet_data.append(row)
                    
                # Update sheet
                sheet.clear()
                sheet.update(values=sheet_data, range_name='A1')
                
                print(f"Successfully updated {industry} sheet with {len(data)} vendors")
                
            except Exception as e:
                print(f"Error updating {industry} sheet: {str(e)}")
                
    def cleanup(self):
        """Clean up resources"""
        self.browser.close()
        self.playwright.stop()
        
    def run(self):
        """Run the full organization process"""
        try:
            print("Starting data organization...")
            self.organize_data()
            print("\nSaving to sheets...")
            self.save_to_sheets()
            print("\nDone!")
        finally:
            self.cleanup()

if __name__ == "__main__":
    organizer = DataOrganizer()
    organizer.run() 