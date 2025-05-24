import os
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Get sheet URLs from environment
SHEET_URLS = {
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

def clean_products(text):
    """Clean products text by removing special characters while preserving numbers, spaces, hyphens, commas, and periods"""
    if not text:
        return ""
    
    original = text
    # Keep only alphanumeric characters, spaces, hyphens, commas, and periods
    text = re.sub(r'[^a-zA-Z0-9\s,\-\.]', '', text)
    
    # Clean up multiple commas (but preserve spaces)
    text = re.sub(r',\s*,', ',', text)     # Remove duplicate commas
    text = re.sub(r'^\s*,\s*|\s*,\s*$', '', text)  # Remove leading/trailing commas
    
    # Clean up multiple hyphens
    text = re.sub(r'-+', '-', text)        # Replace multiple hyphens with single hyphen
    
    cleaned = text.strip()
    if original != cleaned:
        print(f"Cleaning: '{original}' -> '{cleaned}'")
    return cleaned

def get_sheet_data(sheet):
    """Get data from sheet with row numbers"""
    try:
        print("Fetching data from sheet...")
        data = sheet.get_all_values()
        if len(data) <= 1:  # Only headers or empty
            return []
            
        # Get headers and data
        headers = data[0]
        rows = data[1:]
        
        # Convert to dictionary format with row numbers
        sheet_data = []
        for i, row in enumerate(rows, start=2):  # Start from 2 because row 1 is headers
            vendor = {'row_number': i}
            for j, value in enumerate(row):
                if j < len(headers):
                    header = headers[j].strip().lower()
                    vendor[header] = value.strip()
            sheet_data.append(vendor)
            
        return sheet_data
        
    except Exception as e:
        print(f"Error getting sheet data: {str(e)}")
        return []

def display_vendor_info(vendor, show_cleaned=True):
    """Display vendor information in a readable format"""
    print("\nVendor Details:")
    print(f"Row Number: {vendor['row_number']}")
    print(f"Company Name: {vendor.get('company_name', '')}")
    print(f"Original Products: {vendor.get('products', '')}")
    if show_cleaned:
        print(f"Cleaned Products: {clean_products(vendor.get('products', ''))}")
    print("-" * 50)

def main():
    try:
        print("Starting product cleaning process...")
        
        # Load credentials
        print("Loading Google Sheets credentials...")
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
                print(f"\nProcessing {industry.upper()} sheet...")
                
                # Get sheet
                print("Opening sheet...")
                sheet = client.open_by_url(url).sheet1
                
                # Get data
                vendors = get_sheet_data(sheet)
                print(f"Found {len(vendors)} vendors in sheet")
                
                # Track statistics
                total_processed = 0
                total_updated = 0
                
                # Process each vendor
                for vendor in vendors:
                    total_processed += 1
                    print(f"\rProcessing vendor {total_processed}/{len(vendors)}...", end="", flush=True)
                    
                    original_products = vendor.get('products', '')
                    cleaned_products = clean_products(original_products)
                    
                    if original_products != cleaned_products:
                        print(f"\n{'='*80}")
                        display_vendor_info(vendor)
                        
                        # Ask for update
                        while True:
                            response = input("\nWould you like to update the products? (y/n): ").lower()
                            if response in ['y', 'n']:
                                break
                            print("Please enter 'y' or 'n'")
                        
                        if response == 'y':
                            # Update the products column
                            print("Updating sheet...")
                            sheet.update_cell(vendor['row_number'], 
                                           sheet.row_values(1).index('products') + 1, 
                                           cleaned_products)
                            print("Products updated successfully!")
                            total_updated += 1
                        else:
                            print("Skipping update for this vendor")
                        
                        print(f"{'='*80}\n")
                
                # Show summary for this industry
                print(f"\nSummary for {industry.upper()}:")
                print(f"Total vendors processed: {total_processed}")
                print(f"Total vendors updated: {total_updated}")
                
            except Exception as e:
                print(f"Error processing {industry} sheet: {str(e)}")
                
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")
    
    print("\nProduct cleaning process completed!")

if __name__ == "__main__":
    main() 