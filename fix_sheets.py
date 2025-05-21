import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get sheet URLs from environment
SHEET_URLS = {
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "chiropractic": os.getenv("CHIROPRACTIC_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

# Define the correct headers in the right order
CORRECT_HEADERS = [
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

def fix_sheet(sheet):
    """Fix the structure of a sheet"""
    try:
        # Get all data
        all_data = sheet.get_all_values()
        
        if not all_data:
            print("Sheet is empty")
            return
            
        # Get current headers
        current_headers = all_data[0]
        
        # Create a mapping from current headers to correct headers
        header_map = {}
        for i, header in enumerate(current_headers):
            # Clean the header
            clean_header = header.strip().lower()
            if clean_header in CORRECT_HEADERS:
                header_map[i] = CORRECT_HEADERS.index(clean_header)
        
        # Create new data with correct headers
        new_data = [CORRECT_HEADERS]  # Start with correct headers
        
        # Process each row
        for row in all_data[1:]:  # Skip header row
            new_row = [""] * len(CORRECT_HEADERS)  # Initialize with empty strings
            for i, value in enumerate(row):
                if i in header_map:
                    new_row[header_map[i]] = value
            new_data.append(new_row)
        
        # Clear the sheet
        sheet.clear()
        
        # Update with new data
        sheet.update(values=new_data, range_name='A1')
        
        print(f"Successfully fixed sheet structure")
        print(f"Old headers: {len(current_headers)}")
        print(f"New headers: {len(CORRECT_HEADERS)}")
        
    except Exception as e:
        print(f"Error fixing sheet: {str(e)}")

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
                print(f"\nFixing {industry.upper()} sheet...")
                sheet = client.open_by_url(url).sheet1
                fix_sheet(sheet)
                
            except Exception as e:
                print(f"Error accessing {industry} sheet: {str(e)}")
                
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")

if __name__ == "__main__":
    main() 