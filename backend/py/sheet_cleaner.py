import os
import json
import glob
import re
from datetime import datetime
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

def clean_value(value):
    """Clean a value of any code-like characters and format it properly"""
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return str(value).replace("[", "").replace("]", "").replace("{", "").replace("}", "")
    return str(value).strip()

def get_latest_logs(industry, deployment_model):
    """Get the most recent log files for an industry and deployment model"""
    # Pattern: industry_deployment_YYYYMMDD_HHMMSS.json
    pattern = f"vendor_logs/{industry}_{deployment_model}_*.json"
    log_files = glob.glob(pattern)
    
    # Sort by date in filename (newest first)
    log_files.sort(key=lambda x: x.split('_')[-1].split('.')[0], reverse=True)
    
    # Get the most recent file
    return log_files[0] if log_files else None

def get_all_headers(log_file):
    """Extract all possible headers from vendor data"""
    headers = set()
    try:
        with open(log_file, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                # New format with merged array
                for vendor_group in data:
                    if isinstance(vendor_group, dict) and "merged" in vendor_group:
                        for vendor in vendor_group["merged"]:
                            if isinstance(vendor, dict):
                                headers.update(vendor.keys())
            elif isinstance(data, dict):
                # Old format with vendors array
                for vendor in data.get("vendors", []):
                    if isinstance(vendor, dict):
                        headers.update(vendor.keys())
    except Exception as e:
        print(f"Warning: Error reading {log_file}: {e}")
    return sorted(list(headers))

def get_sheet_for_industry(industry):
    """Get the sheet for the given industry"""
    try:
        # Load credentials
        scope = ['https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
        client = gspread.authorize(creds)
        
        # Get sheet URL from environment
        sheet_url = SHEET_URLS.get(industry)
        if not sheet_url:
            print(f"Error: No sheet URL found for {industry} in environment variables")
            return None
        
        # Try to open sheet by URL
        try:
            sheet = client.open_by_url(sheet_url).sheet1
            return sheet
        except Exception as e:
            print(f"Error: Could not access sheet for {industry} at URL: {sheet_url}")
            print(f"Error details: {str(e)}")
            return None
            
    except Exception as e:
        print(f"Error accessing Google Sheets: {e}")
        return None

def clean_and_update_sheet(industry, deployment_model):
    """Clean vendor data and update the sheet"""
    # Get the most recent log file
    log_file = get_latest_logs(industry, deployment_model)
    if not log_file:
        print(f"No log file found for {industry} {deployment_model}")
        return
    
    print(f"Processing {log_file}...")
    
    # Get all possible headers
    headers = get_all_headers(log_file)
    if not headers:
        print(f"No headers found in {log_file}")
        return
    
    # Get sheet
    sheet = get_sheet_for_industry(industry)
    if not sheet:
        return
    
    # Prepare data
    all_vendors = []
    try:
        with open(log_file, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                # New format with merged array
                for vendor_group in data:
                    if isinstance(vendor_group, dict) and "merged" in vendor_group:
                        for vendor in vendor_group["merged"]:
                            if isinstance(vendor, dict):
                                all_vendors.append(vendor)
            elif isinstance(data, dict):
                # Old format with vendors array
                all_vendors.extend(data.get("vendors", []))
    except Exception as e:
        print(f"Error reading {log_file}: {e}")
        return
    
    # Clean and format data
    cleaned_data = []
    for vendor in all_vendors:
        row = []
        for header in headers:
            value = vendor.get(header, "")
            cleaned_value = clean_value(value)
            row.append(cleaned_value)
        cleaned_data.append(row)
    
    # Update sheet
    try:
        # Get existing data
        existing_data = sheet.get_all_values()
        existing_headers = existing_data[0] if existing_data else []
        
        # Combine headers
        all_headers = sorted(list(set(existing_headers + headers)))
        
        # Map new data to combined headers
        new_data = []
        for row in cleaned_data:
            new_row = []
            for header in all_headers:
                if header in headers:
                    idx = headers.index(header)
                    new_row.append(row[idx])
                else:
                    new_row.append("")
            new_data.append(new_row)
        
        # Update headers if needed
        if existing_headers != all_headers:
            sheet.update(values=[all_headers], range_name='A1')
        
        # Append new data
        if new_data:
            next_row = len(existing_data) + 1
            sheet.update(values=new_data, range_name=f'A{next_row}')
        
        print(f"Successfully added {len(new_data)} vendors to {industry} sheet")
    except Exception as e:
        print(f"Error updating sheet: {e}")

def main():
    # Process each combination
    industries = ["optometry", "chiropractic", "auto_repair"]
    deployment_models = ["cloud_based", "windows_server", "web_based"]
    
    for industry in industries:
        for deployment_model in deployment_models:
            print(f"\nProcessing {industry} {deployment_model}...")
            clean_and_update_sheet(industry, deployment_model)

if __name__ == "__main__":
    main() 