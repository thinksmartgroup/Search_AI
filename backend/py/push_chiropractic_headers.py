import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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

def push_headers_to_chiropractic():
    """Push headers to the chiropractic sheet"""
    try:
        # Load credentials
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Get chiropractic sheet URL
        sheet_url = os.getenv("CHIRO_SHEET_URL")
        if not sheet_url:
            print("Error: CHIRO_SHEET_URL not found in environment variables")
            return
            
        try:
            # Open sheet by URL
            sheet = client.open_by_url(sheet_url).sheet1
            
            # Get current data
            current_data = sheet.get_all_values()
            
            # Create new data with headers
            new_data = [CORRECT_HEADERS]  # Start with headers
            
            # Add existing data if any
            if len(current_data) > 1:  # If there's data beyond headers
                new_data.extend(current_data[1:])
            
            # Clear the sheet
            sheet.clear()
            
            # Update with new data
            sheet.update(values=new_data, range_name='A1')
            
            print("Successfully pushed headers to chiropractic sheet")
            print(f"Total headers: {len(CORRECT_HEADERS)}")
            if len(current_data) > 1:
                print(f"Preserved {len(current_data) - 1} rows of existing data")
            
        except Exception as e:
            print(f"Error accessing chiropractic sheet: {str(e)}")
            
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")

if __name__ == "__main__":
    push_headers_to_chiropractic() 