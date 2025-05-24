import os
import json
import glob
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

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
    "description",
    "products",
    "company_size",
    "founding_year",
    "pricing_model",
    "platform_type",
    "platform_score",
    "deployment_model",
    "deployment_characteristics",
    "deployment_marking",
    "hosting_type",
    "technology_stack",
    "integration_capabilities",
    "compliance_certifications",
    "industry",
    "is_primary_vendor",
    "confidence_score",
    "evidence",
    "source",
    "created_at",
    "updated_at"
]

def get_sheet_data(sheet):
    """Get and clean data from a sheet"""
    try:
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
                    # Clean the header name
                    header = headers[i].strip().lower()
                    # Clean the value
                    if isinstance(value, str):
                        value = value.strip()
                    vendor[header] = value
            sheet_data.append(vendor)
            
        return sheet_data
        
    except Exception as e:
        print(f"Error getting sheet data: {str(e)}")
        return []

def get_log_data(industry):
    """Get data from log files"""
    try:
        # Pattern: industry_*.json
        pattern = f"vendor_logs/{industry}_*.json"
        log_files = glob.glob(pattern)
        
        log_data = []
        for log_file in log_files:
            print(f"Reading log file: {log_file}")
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

def standardize_data(data, industry):
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

def main():
    try:
        # Load credentials
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Process each sheet
        for industry, url in SHEET_URLS.items():
            if not url:
                print(f"\n{industry.upper()}: No sheet URL found in environment variables")
                continue
                
            try:
                print(f"\nProcessing {industry.upper()}...")
                
                # Get sheet
                sheet = client.open_by_url(url).sheet1
                
                # Get data from sheet and logs
                sheet_data = get_sheet_data(sheet)
                log_data = get_log_data(industry)
                
                print(f"Found {len(sheet_data)} vendors in sheet")
                print(f"Found {len(log_data)} vendors in logs")
                
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
                
                print(f"Total unique vendors after deduplication: {len(all_data)}")
                
                # Standardize all data
                standardized_data = [
                    standardize_data(vendor, industry)
                    for vendor in all_data.values()
                ]
                
                # Prepare data for sheet
                sheet_data = [STANDARD_HEADERS]  # Headers
                for vendor in standardized_data:
                    row = [vendor.get(header, '') for header in STANDARD_HEADERS]
                    sheet_data.append(row)
                
                # Update sheet
                print(f"Updating sheet with {len(standardized_data)} vendors...")
                sheet.clear()
                sheet.update(values=sheet_data, range_name='A1')
                
                print(f"Successfully updated {industry} sheet with {len(standardized_data)} vendors")
                
            except Exception as e:
                print(f"Error processing {industry} sheet: {str(e)}")
                
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")

if __name__ == "__main__":
    main() 