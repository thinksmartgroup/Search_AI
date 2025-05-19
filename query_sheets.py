import os
import json
from datetime import datetime
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from tabulate import tabulate
from collections import Counter

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

def get_sheet_by_industry(industry):
    """Get Google Sheet for specific industry"""
    if industry not in SHEET_URLS:
        raise ValueError(f"Unsupported industry: '{industry}'")
        
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1

def get_vendor_stats(sheet):
    """Get statistics about vendors in the sheet"""
    # Get all records
    records = sheet.get_all_records()
    
    # Total vendors
    total_vendors = len(records)
    
    # Vendors by deployment model
    deployment_counter = Counter(record.get('deployment_model', 'Unknown') for record in records)
    deployment_stats = [(model, count) for model, count in deployment_counter.most_common()]
    
    # Vendors by platform type
    platform_counter = Counter(record.get('platform_type', 'Unknown') for record in records)
    platform_stats = [(platform, count) for platform, count in platform_counter.most_common()]
    
    return {
        "total_vendors": total_vendors,
        "deployment_stats": deployment_stats,
        "platform_stats": platform_stats
    }

def get_top_vendors(sheet, limit=5):
    """Get top vendors by confidence score"""
    records = sheet.get_all_records()
    
    # Sort by confidence score, handling empty values
    sorted_records = sorted(
        records,
        key=lambda x: float(x.get('confidence_score', 0) or 0),  # Convert empty string to 0
        reverse=True
    )
    
    # Get top N records
    top_records = sorted_records[:limit]
    
    # Format for display
    return [(
        record.get('company_name', ''),
        record.get('website', ''),
        record.get('confidence_score', '0') or '0',  # Show 0 for empty values
        record.get('deployment_model', ''),
        record.get('platform_type', '')
    ) for record in top_records]

def search_vendors(sheet, query):
    """Search vendors by name or description"""
    records = sheet.get_all_records()
    
    # Search in company name and description
    results = []
    for record in records:
        if (query.lower() in record.get('company_name', '').lower() or
            query.lower() in record.get('description', '').lower()):
            results.append((
                record.get('company_name', ''),
                record.get('website', ''),
                record.get('description', ''),
                record.get('deployment_model', ''),
                record.get('platform_type', '')
            ))
            if len(results) >= 10:  # Limit to 10 results
                break
    
    return results

def main():
    """Main function to query and analyze vendor data"""
    print("Vendor Sheet Analysis")
    print("=" * 50)
    
    for industry in SHEET_URLS.keys():
        print(f"\nAnalyzing {industry.upper()} industry:")
        print("-" * 50)
        
        try:
            sheet = get_sheet_by_industry(industry)
            
            # Get statistics
            stats = get_vendor_stats(sheet)
            
            print(f"\nTotal Vendors: {stats['total_vendors']}")
            
            print("\nDeployment Model Distribution:")
            print(tabulate(stats['deployment_stats'], 
                          headers=['Deployment Model', 'Count'],
                          tablefmt='grid'))
            
            print("\nPlatform Type Distribution:")
            print(tabulate(stats['platform_stats'],
                          headers=['Platform Type', 'Count'],
                          tablefmt='grid'))
            
            print("\nTop 5 Vendors by Confidence Score:")
            top_vendors = get_top_vendors(sheet)
            print(tabulate(top_vendors,
                          headers=['Company', 'Website', 'Confidence', 'Deployment', 'Platform'],
                          tablefmt='grid'))
            
            # Interactive search
            while True:
                query = input("\nEnter search term (or 'q' to quit): ").strip()
                if query.lower() == 'q':
                    break
                    
                results = search_vendors(sheet, query)
                if results:
                    print("\nSearch Results:")
                    print(tabulate(results,
                                 headers=['Company', 'Website', 'Description', 'Deployment', 'Platform'],
                                 tablefmt='grid'))
                else:
                    print("No results found.")
                    
        except Exception as e:
            print(f"Error processing {industry} sheet: {e}")
            continue

if __name__ == "__main__":
    main() 