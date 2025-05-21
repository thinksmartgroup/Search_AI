import os
import json
import re
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from collections import defaultdict
import glob
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'vendor_agent_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

class VendorAgent:
    def __init__(self):
        self.patterns = {
            'products': defaultdict(int),
            'company_sizes': defaultdict(int),
            'pricing_models': defaultdict(int),
            'common_terms': defaultdict(int)
        }
        self.learned_rules = {}
        
    def learn_from_logs(self, log_dir='logs'):
        """Learn patterns from vendor logs"""
        logging.info("Starting to learn from vendor logs...")
        
        # Get all log files
        log_files = glob.glob(os.path.join(log_dir, '*.log'))
        if not log_files:
            logging.warning(f"No log files found in {log_dir}")
            return
            
        logging.info(f"Found {len(log_files)} log files to analyze")
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    
                # Extract vendor data using regex patterns
                self._extract_patterns(content)
                
            except Exception as e:
                logging.error(f"Error processing log file {log_file}: {str(e)}")
                
        self._generate_rules()
        logging.info("Learning phase completed")
        
    def _extract_patterns(self, content):
        """Extract patterns from log content"""
        # Extract products
        product_matches = re.finditer(r'products["\']?\s*:\s*["\']([^"\']+)["\']', content)
        for match in product_matches:
            products = match.group(1).split(',')
            for product in products:
                self.patterns['products'][product.strip()] += 1
                
        # Extract company sizes
        size_matches = re.finditer(r'company_size["\']?\s*:\s*["\']([^"\']+)["\']', content)
        for match in size_matches:
            size = match.group(1).strip()
            self.patterns['company_sizes'][size] += 1
            
        # Extract pricing models
        pricing_matches = re.finditer(r'pricing_model["\']?\s*:\s*["\']([^"\']+)["\']', content)
        for match in pricing_matches:
            model = match.group(1).strip()
            self.patterns['pricing_models'][model] += 1
            
        # Extract common terms
        words = re.findall(r'\b\w+\b', content.lower())
        for word in words:
            if len(word) > 3:  # Only consider words longer than 3 characters
                self.patterns['common_terms'][word] += 1
                
    def _generate_rules(self):
        """Generate cleaning rules based on learned patterns"""
        # Generate product cleaning rules
        common_products = {k for k, v in self.patterns['products'].items() if v > 1}
        self.learned_rules['products'] = {
            'common_products': common_products,
            'min_occurrences': 2
        }
        
        # Generate company size rules
        common_sizes = {k for k, v in self.patterns['company_sizes'].items() if v > 1}
        self.learned_rules['company_sizes'] = {
            'valid_sizes': common_sizes,
            'min_occurrences': 2
        }
        
        # Generate pricing model rules
        common_models = {k for k, v in self.patterns['pricing_models'].items() if v > 1}
        self.learned_rules['pricing_models'] = {
            'valid_models': common_models,
            'min_occurrences': 2
        }
        
        # Generate common terms rules
        common_terms = {k for k, v in self.patterns['common_terms'].items() if v > 5}
        self.learned_rules['common_terms'] = {
            'valid_terms': common_terms,
            'min_occurrences': 5
        }
        
    def clean_products(self, text):
        """Clean products text using learned patterns"""
        if not text:
            return ""
            
        original = text
        
        # Keep only alphanumeric characters, spaces, hyphens, commas, and periods
        text = re.sub(r'[^a-zA-Z0-9\s,\-\.]', '', text)
        
        # Clean up multiple commas (but preserve spaces)
        text = re.sub(r',\s*,', ',', text)
        text = re.sub(r'^\s*,\s*|\s*,\s*$', '', text)
        
        # Clean up multiple hyphens
        text = re.sub(r'-+', '-', text)
        
        # Apply learned rules
        products = [p.strip() for p in text.split(',')]
        cleaned_products = []
        
        for product in products:
            # Check if product matches any common patterns
            if product.lower() in {p.lower() for p in self.learned_rules['products']['common_products']}:
                cleaned_products.append(product)
            else:
                # Try to match partial patterns
                matched = False
                for common_product in self.learned_rules['products']['common_products']:
                    if common_product.lower() in product.lower():
                        cleaned_products.append(common_product)
                        matched = True
                        break
                if not matched:
                    cleaned_products.append(product)
                    
        cleaned = ', '.join(cleaned_products)
        
        if original != cleaned:
            logging.info(f"Cleaned products: '{original}' -> '{cleaned}'")
            
        return cleaned.strip()
        
    def process_sheet(self, sheet_url):
        """Process a Google Sheet using learned patterns"""
        try:
            # Load credentials
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            client = gspread.authorize(creds)
            
            # Open sheet
            sheet = client.open_by_url(sheet_url).sheet1
            data = sheet.get_all_values()
            
            if len(data) <= 1:
                logging.warning("Sheet is empty or contains only headers")
                return
                
            headers = data[0]
            rows = data[1:]
            
            # Process each row
            for i, row in enumerate(rows, start=2):
                vendor = {}
                for j, value in enumerate(row):
                    if j < len(headers):
                        header = headers[j].strip().lower()
                        vendor[header] = value.strip()
                        
                # Clean products
                if 'products' in vendor:
                    cleaned_products = self.clean_products(vendor['products'])
                    if cleaned_products != vendor['products']:
                        # Update the sheet
                        sheet.update_cell(i, headers.index('products') + 1, cleaned_products)
                        logging.info(f"Updated products for vendor in row {i}")
                        
        except Exception as e:
            logging.error(f"Error processing sheet: {str(e)}")
            
    def run(self):
        """Run the agent on all sheets"""
        # Load environment variables
        load_dotenv()
        
        # Get sheet URLs
        sheet_urls = {
            "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
            "chiropractic": os.getenv("CHIRO_SHEET_URL"),
            "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
        }
        
        # Learn from logs
        self.learn_from_logs()
        
        # Process each sheet
        for industry, url in sheet_urls.items():
            if not url:
                logging.warning(f"No URL found for {industry} sheet")
                continue
                
            logging.info(f"Processing {industry} sheet...")
            self.process_sheet(url)
            
        logging.info("Processing completed")

if __name__ == "__main__":
    agent = VendorAgent()
    agent.run() 