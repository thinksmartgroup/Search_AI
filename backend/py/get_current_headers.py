import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

def get_sheet_headers():
    """Fetch headers from all Google Sheets"""
    try:
        # Load environment variables
        load_dotenv()
        
        # Get sheet URLs
        sheet_urls = {
            "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
            "chiropractic": os.getenv("CHIRO_SHEET_URL"),
            "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
        }
        
        # Load credentials
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Process each sheet
        for industry, url in sheet_urls.items():
            if not url:
                print(f"\nNo URL found for {industry} sheet")
                continue
                
            try:
                # Open sheet
                sheet = client.open_by_url(url).sheet1
                
                # Get headers
                headers = sheet.row_values(1)
                
                # Display headers
                print(f"\n{'='*80}")
                print(f"Headers for {industry.upper()} sheet:")
                print(f"Total columns: {len(headers)}")
                print("-" * 40)
                
                # Display each header with its position
                for i, header in enumerate(headers, 1):
                    print(f"{i}. {header}")
                    
            except Exception as e:
                print(f"Error processing {industry} sheet: {str(e)}")
                
    except Exception as e:
        print(f"Error accessing Google Sheets: {str(e)}")

if __name__ == "__main__":
    get_sheet_headers() 