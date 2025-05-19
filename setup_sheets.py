import os
import json
import glob
from datetime import datetime
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()

# Google Sheets configuration
SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]

# Define headers for the sheets
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
    """Get Google Sheet for specific industry"""
    if industry not in SHEET_URLS:
        raise ValueError(f"Unsupported industry: '{industry}'")
        
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

def ensure_sheet_headers(sheet):
    """Ensure sheet has correct headers"""
    try:
        current_headers = sheet.row_values(1)
        if not current_headers or set(current_headers) != set(HEADERS):
            print("Fixing sheet headers...")
            # Clear the sheet
            sheet.clear()
            # Add headers
            sheet.insert_row(HEADERS, 1)
            print("Headers fixed")
            return True
        return False
    except Exception as e:
        print(f"Error checking headers: {e}")
        return False

def load_vendor_data(industry):
    """Load vendor data from JSON files"""
    vendors = []
    pattern = f"vendor_logs/{industry}_*.json"
    
    for json_file in glob.glob(pattern):
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'vendors' in data:
                    vendors.extend(data['vendors'])
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    
    return vendors

def update_google_sheet(vendors, industry):
    """Update Google Sheet with vendor data"""
    try:
        sheet = get_sheet_by_industry(industry)
        
        # Ensure headers are correct
        ensure_sheet_headers(sheet)
        
        # Get existing data
        existing_rows = sheet.get_all_records()
        
        # Get existing websites for deduplication
        existing_websites = {row.get("website", "").lower().strip() for row in existing_rows}
        
        # Prepare new rows
        new_rows = []
        for vendor in vendors:
            # Skip if website is empty or already exists
            website = vendor.get("website", "").lower().strip()
            if not website or website in existing_websites:
                continue
                
            # Add to existing websites set
            existing_websites.add(website)
            
            # Convert lists to JSON strings
            for field in ['products', 'deployment_characteristics', 'technology_stack', 
                         'integration_capabilities', 'compliance_certifications']:
                if field in vendor and isinstance(vendor[field], list):
                    vendor[field] = json.dumps(vendor[field])
            
            # Add timestamps
            vendor['created_at'] = datetime.now().isoformat()
            vendor['updated_at'] = datetime.now().isoformat()
            
            # Prepare row with all fields
            row = [vendor.get(header, "") for header in HEADERS]
            new_rows.append(row)
        
        # Add new rows
        if new_rows:
            sheet.append_rows(new_rows, value_input_option="USER_ENTERED")
            print(f"Added {len(new_rows)} new vendors to {industry} sheet")
            return len(new_rows)
        else:
            print(f"No new vendors found for {industry} sheet")
            return 0
            
    except Exception as e:
        print(f"Error updating sheet: {e}")
        print("Attempting to fix sheet...")
        try:
            # Try to fix the sheet by clearing and reinitializing
            sheet.clear()
            sheet.insert_row(HEADERS, 1)
            print("Sheet reinitialized with correct headers")
            # Try the update again
            return update_google_sheet(vendors, industry)
        except Exception as e2:
            print(f"Failed to fix sheet: {e2}")
            return 0

def process_industry(industry):
    """Process all vendor data for an industry"""
    print(f"\nProcessing {industry} industry...")
    
    # Load vendor data
    vendors = load_vendor_data(industry)
    print(f"Found {len(vendors)} vendors in JSON files")
    
    # Update Google Sheet
    written = update_google_sheet(vendors, industry)
    print(f"Total vendors written to sheet: {written}")

def main():
    """Main function to process all industries"""
    print("Starting Google Sheets setup and data migration...")
    
    # Process each industry
    for industry in SHEET_URLS.keys():
        process_industry(industry)
    
    print("\nGoogle Sheets setup and data migration completed!")

if __name__ == "__main__":
    main() 