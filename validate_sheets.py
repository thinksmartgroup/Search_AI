#!/usr/bin/env python3

import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import google.generativeai as genai
import logging
from datetime import datetime
import time
from tqdm import tqdm

# Set up logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    handlers=[
        logging.FileHandler(f'validate_sheets_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

# Create logger
logger = logging.getLogger('SheetValidator')

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')

# Define headers for the sheets
HEADERS = [
    "company_name",
    "website",
    "products",
    "industry",
    "confidence",
    "evidence",
    "source"
]

def fetch_sheet_data(client, url):
    """Fetch all data from a Google Sheet."""
    try:
        logger.info(f"Fetching data from sheet: {url}")
        sheet = client.open_by_url(url).sheet1
        data = sheet.get_all_values()
        if len(data) <= 1:
            logger.warning(f"No data found in sheet: {url}")
            return None
        
        # Convert to list of dictionaries
        headers = data[0]
        rows = []
        for row in data[1:]:
            row_dict = dict(zip(headers, row))
            rows.append(row_dict)
        
        logger.info(f"Successfully fetched {len(rows)} rows from sheet: {url}")
        return rows
    except Exception as e:
        logger.error(f"Error fetching sheet data from {url}: {str(e)}")
        return None

def validate_with_gemini(row):
    """Validate a row using Gemini AI."""
    company_name = row['company_name']
    logger.info(f"Validating company: {company_name}")
    
    prompt = f"""
    You are a data validation expert. Your task is to validate vendor data and determine their deployment type.

    Input data to validate:
    {{
        "company_name": "{row['company_name']}",
        "website": "{row['website']}",
        "products": "{row['products']}",
        "industry": "{row['industry']}",
        "confidence": "{row['confidence']}",
        "evidence": "{row['evidence']}",
        "source": "{row['source']}"
    }}

    Based on your knowledge of the vendor and their products, determine the deployment type and provide a confidence score between 0.00 and 1.00:
    - Closer to 1.00 indicates more Windows Server based characteristics
    - Closer to 0.00 indicates more web-based characteristics
    - Values around 0.50 indicate cloud-based characteristics

    Look for indicators like:
    - Windows Server, on-premise, local installation (higher scores)
    - Cloud, SaaS, hosted, AWS, Azure, GCP (middle scores)
    - Web-based, browser-based, no installation (lower scores)

    IMPORTANT: Respond with ONLY a JSON object in this exact format, nothing else:
    {{
        "valid": true/false,
        "confidence": number between 0.00 and 1.00,
        "reason": "brief explanation of deployment type and validation",
        "summary": "one-line summary of why this score was chosen"
    }}
    """
    try:
        logger.debug(f"Sending prompt to Gemini for {company_name}")
        response = model.generate_content(prompt)
        
        # Clean the response text to ensure it's valid JSON
        response_text = response.text.strip()
        logger.debug(f"Received response from Gemini for {company_name}")
        
        # Extract JSON from response
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON object found in response")
        
        json_str = response_text[start_idx:end_idx]
        result = json.loads(json_str)
        
        # Validate result structure
        required_keys = ['valid', 'confidence', 'reason', 'summary']
        if not all(key in result for key in required_keys):
            raise ValueError("Missing required keys in response")
        
        # Ensure confidence is between 0.00 and 1.00
        confidence = float(result['confidence'])
        result['confidence'] = max(0.00, min(1.00, confidence))
        
        logger.info(f"Validation complete for {company_name}: confidence={result['confidence']}, valid={result['valid']}")
        logger.info(f"Summary: {result['summary']}")
        return result
    except Exception as e:
        logger.error(f"Error validating {company_name} with Gemini: {str(e)}")
        return {"valid": False, "confidence": 0.00, "reason": f"Error in validation: {str(e)}", "summary": "Error occurred during validation"}

def update_sheet(client, url, row_index, new_confidence, new_evidence):
    """Update the confidence and evidence in the sheet."""
    try:
        logger.info(f"Updating sheet {url} at row {row_index + 2}")
        sheet = client.open_by_url(url).sheet1
        sheet.update_cell(row_index + 2, 5, new_confidence)  # confidence column
        sheet.update_cell(row_index + 2, 6, new_evidence)    # evidence column
        logger.info(f"Successfully updated sheet {url} at row {row_index + 2}")
    except Exception as e:
        logger.error(f"Error updating sheet {url} at row {row_index + 2}: {str(e)}")

def process_sheet(client, industry, url):
    """Process a single sheet."""
    logger.info(f"\n{'='*80}\nStarting to process {industry} sheet: {url}\n{'='*80}")
    
    if not url:
        logger.warning(f"No URL provided for {industry} sheet")
        return

    rows = fetch_sheet_data(client, url)
    if rows is None:
        logger.warning(f"No data found in {industry} sheet")
        return

    logger.info(f"Processing {len(rows)} rows in {industry} sheet")
    
    # Create progress bar for this sheet
    pbar = tqdm(total=len(rows), desc=f"Processing {industry} vendors")
    
    for index, row in enumerate(rows):
        company_name = row['company_name']
        logger.info(f"\nProcessing row {index + 2} for company: {company_name}")
        
        # Validate with Gemini
        validation = validate_with_gemini(row)
        if not validation["valid"]:
            logger.warning(f"Invalid data for {company_name}: {validation['reason']}")

        # Update confidence if needed
        current_confidence = float(row['confidence']) if row['confidence'] else 0.0
        if validation["confidence"] != current_confidence:
            logger.info(f"Updating confidence for {company_name} from {current_confidence} to {validation['confidence']}")
            update_sheet(client, url, index, validation["confidence"], validation["reason"])
        else:
            logger.info(f"No confidence update needed for {company_name}")

        # Update progress bar
        pbar.update(1)
        
        # Add a small delay to avoid rate limits
        time.sleep(1)

    pbar.close()
    logger.info(f"\n{'='*80}\nCompleted processing {industry} sheet\n{'='*80}\n")

def main():
    logger.info("Starting sheet validation process")
    
    # Load credentials
    logger.info("Loading Google credentials")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    logger.info("Successfully authenticated with Google")

    # Get sheet URLs
    sheet_urls = {
        "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
        "chiropractic": os.getenv("CHIRO_SHEET_URL"),
        "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
    }
    logger.info(f"Found {len(sheet_urls)} sheets to process")

    # Process sheets sequentially
    for industry, url in sheet_urls.items():
        process_sheet(client, industry, url)

    logger.info("Sheet validation process completed")

if __name__ == "__main__":
    main() 