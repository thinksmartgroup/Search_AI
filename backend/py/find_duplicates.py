import os
import json
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
from urllib.parse import urlparse
import re

# Load environment variables
load_dotenv()

# Get sheet URLs from environment
SHEET_URLS = {
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}

def normalize_url(url):
    """Normalize URL for comparison"""
    if not url:
        return None
    # Remove protocol and www
    url = url.lower().replace('https://', '').replace('http://', '').replace('www.', '')
    # Remove trailing slash
    url = url.rstrip('/')
    return url

def get_sheet_data(sheet):
    """Get data from sheet with row numbers"""
    try:
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

def find_duplicates(vendors):
    """Find duplicate entries based on website"""
    # Group by normalized website
    website_groups = {}
    for vendor in vendors:
        website = normalize_url(vendor.get('website', ''))
        if website:
            if website not in website_groups:
                website_groups[website] = []
            website_groups[website].append(vendor)
    
    # Filter groups with more than one entry
    duplicates = {website: vendors for website, vendors in website_groups.items() if len(vendors) > 1}
    return duplicates

def display_vendor_info(vendor):
    """Display vendor information in a readable format"""
    print("\nVendor Details:")
    print(f"Row Number: {vendor['row_number']}")
    for key, value in vendor.items():
        if key != 'row_number':
            print(f"{key}: {value}")
    print("-" * 50)

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
                print(f"\nProcessing {industry.upper()} sheet...")
                
                # Get sheet
                sheet = client.open_by_url(url).sheet1
                
                # Get data
                vendors = get_sheet_data(sheet)
                print(f"Found {len(vendors)} vendors in sheet")
                
                # Find duplicates
                duplicates = find_duplicates(vendors)
                
                if not duplicates:
                    print("No duplicates found!")
                    continue
                    
                print(f"\nFound {len(duplicates)} groups of duplicates:")
                
                # Process each group of duplicates
                for website, duplicate_vendors in duplicates.items():
                    print(f"\n{'='*80}")
                    print(f"Duplicate Group - Website: {website}")
                    print(f"Number of duplicates: {len(duplicate_vendors)}")
                    
                    # Display all duplicates
                    for vendor in duplicate_vendors:
                        display_vendor_info(vendor)
                    
                    # Ask for deletion
                    while True:
                        response = input("\nWould you like to delete duplicates? (y/n): ").lower()
                        if response in ['y', 'n']:
                            break
                        print("Please enter 'y' or 'n'")
                    
                    if response == 'y':
                        # Keep the first entry, delete others
                        keep_vendor = duplicate_vendors[0]
                        delete_vendors = duplicate_vendors[1:]
                        
                        print("\nKeeping vendor:")
                        display_vendor_info(keep_vendor)
                        
                        print("\nDeleting vendors:")
                        for vendor in delete_vendors:
                            display_vendor_info(vendor)
                            # Delete the row
                            sheet.delete_rows(vendor['row_number'])
                            # Update row numbers for remaining entries
                            for v in vendors:
                                if v['row_number'] > vendor['row_number']:
                                    v['row_number'] -= 1
                        
                        print(f"\nDeleted {len(delete_vendors)} duplicate entries")
                    else:
                        print("Skipping deletion for this group")
                    
                    print(f"{'='*80}\n")
                
            except Exception as e:
                print(f"Error processing {industry} sheet: {str(e)}")
                
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")

if __name__ == "__main__":
    main() 