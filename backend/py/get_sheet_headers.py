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

def get_sheet_headers():
    """Get headers from all sheets"""
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
                # Open sheet by URL
                sheet = client.open_by_url(url).sheet1
                
                # Get headers (first row)
                headers = sheet.row_values(1)
                
                # Print results
                print(f"\n{industry.upper()} Sheet Headers:")
                print("-" * 50)
                for i, header in enumerate(headers, 1):
                    print(f"{i}. {header}")
                print(f"Total headers: {len(headers)}")
                
            except Exception as e:
                print(f"\n{industry.upper()}: Error accessing sheet - {str(e)}")
                
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")

if __name__ == "__main__":
    get_sheet_headers() 