import os
import re
import json
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
PHONE_REGEX = r"\(?\b[0-9]{3}[-.)\s]?[0-9]{3}[-.\s]?[0-9]{4}\b"

def fetch_text_from_url(url):
    try:
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        return soup.get_text(separator=" ", strip=True)[:20000]
    except Exception as e:
        print(f"⚠️ Failed to fetch {url}: {e}")
        return None

def extract_contact_info(text):
    emails = re.findall(EMAIL_REGEX, text)
    phones = re.findall(PHONE_REGEX, text)
    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None
    }

def extract_json_block(text):
    try:
        json_start = text.find("[")
        json_end = text.rfind("]") + 1
        return json.loads(text[json_start:json_end])
    except Exception as e:
        print("⚠️ JSON extraction failed:", e)
        return []

def score_platform(platform):
    platform = platform.lower()
    if "windows server" in platform:
        return 10
    elif "cloud" in platform:
        return 5
    elif "web" in platform:
        return 3
    return 1

def find_official_website(vendor_name):
    """Find the official website for a vendor using Gemini"""
    try:
        prompt = (
            f"Find the official website URL for the software company: {vendor_name}\n"
            "Return ONLY the URL as a JSON object:\n"
            "{\"official_website\": \"https://example.com\"}"
        )
        
        response = model.generate_content(prompt)
        result = json.loads(response.text.strip())
        return result.get("official_website")
    except Exception as e:
        print(f"⚠️ Failed to find official website for {vendor_name}: {e}")
        return None

def extract_products_from_official_site(url, vendor_name):
    """Extract products from the vendor's official website"""
    text = fetch_text_from_url(url)
    if not text:
        return []

    try:
        prompt = (
            f"Based on this webpage content:\n\n{text[:5000]}\n\n"
            f"Company: {vendor_name}\n\n"
            "List ONLY the software products or services that this company develops and sells themselves. "
            "For each product, extract:\n"
            "- product: name of the product or software\n"
            "- platform: one of 'Windows Server', 'Cloud-based', 'Web-based', or best technical guess\n"
            "Respond as a JSON list:\n"
            "[ {\"product\": \"ProductName\", \"platform\": \"Windows Server\"}, ... ]"
        )

        response = model.generate_content(prompt)
        return extract_json_block(response.text)
    except Exception as e:
        print(f"⚠️ Failed to extract products from {url}: {e}")
        return []

def validate_vendor(text, industry, prompt):
    """Validate if the company is a primary software vendor"""
    try:
        gemini_prompt = (
            f"Based on this webpage content:\n\n{text[:5000]}\n\n"
            f"Industry: {industry}\n"
            f"Search Context: {prompt}\n\n"
            "Determine if this company is a primary software vendor. They must meet ALL these criteria:\n"
            "1. They are a PRIMARY software developer (not a reseller, consultant, or third-party)\n"
            "2. They develop/sell software specifically for {industry}\n"
            "3. Their software is directly relevant to the search prompt\n"
            "4. They have an active, commercial software product\n\n"
            "Look for signs of third-party integrations:\n"
            "- Check for 'powered by', 'integrated with', or 'using [other company]'s software'\n"
            "- Look for partner logos or integration sections\n"
            "- Check if they're primarily a reseller or consultant\n"
            "- Verify if their 'products' are actually just integrations\n\n"
            "Return a JSON object with:\n"
            "{\n"
            "  \"is_primary_vendor\": true/false,\n"
            "  \"company_name\": \"Official company name\",\n"
            "  \"confidence_score\": 0-10,\n"
            "  \"is_third_party_integration\": true/false,\n"
            "  \"rejection_reason\": \"If not a primary vendor, explain why\",\n"
            "  \"evidence\": \"Specific evidence from the content\"\n"
            "}"
        )

        response = model.generate_content(gemini_prompt)
        validation = json.loads(response.text.strip())
        
        if not validation.get("is_primary_vendor", False) or validation.get("is_third_party_integration", False):
            print(f"❌ Not a primary vendor: {validation.get('rejection_reason', 'No explanation provided')}")
            return None
            
        print(f"✅ Found primary vendor: {validation.get('company_name')} (Confidence: {validation.get('confidence_score')})")
        return validation
    except Exception as e:
        print(f"⚠️ Failed to validate vendor: {e}")
        return None

def analyze_products(text, company_name, industry):
    """Analyze products to ensure they are primary developments"""
    try:
        gemini_prompt = (
            f"Analyze these products from {company_name}'s website:\n\n{text[:5000]}\n\n"
            f"Industry: {industry}\n\n"
            "For each product, determine:\n"
            "1. Is this their own software or a third-party integration?\n"
            "2. What evidence suggests it's their own product?\n"
            "3. Are there any mentions of integration with other platforms?\n\n"
            "Look for red flags:\n"
            "- 'Powered by [other company]'\n"
            "- 'Integrated with [other company]'\n"
            "- 'Built on [other company]'s platform'\n"
            "- 'Using [other company]'s technology'\n"
            "- Partner/integration sections\n"
            "- Reseller certifications\n\n"
            "Return a JSON list:\n"
            "[ {\n"
            "    \"product_name\": \"string\",\n"
            "    \"is_own_product\": true/false,\n"
            "    \"platform\": \"string\",\n"
            "    \"confidence_score\": 0-10,\n"
            "    \"evidence\": \"string\",\n"
            "    \"third_party_integrations\": [\"list of integrations if any\"]\n"
            "  }\n"
            "]"
        )

        response = model.generate_content(gemini_prompt)
        return extract_json_block(response.text)
    except Exception as e:
        print(f"⚠️ Failed to analyze products: {e}")
        return []

def summarize_and_extract_contact(url, prompt="", industry="", source_page=0):
    print(f"🔍 Processing: {url}")
    text = fetch_text_from_url(url)
    if not text:
        return []

    # First validate if this is a primary vendor
    vendor_validation = validate_vendor(text, industry, prompt)
    if not vendor_validation:
        return []

    # If we have a primary vendor, create a basic entry
    vendor_entry = {
        "website": url,
        "company_name": vendor_validation["company_name"],
        "confidence_score": vendor_validation.get("confidence_score", 0),
        "industry": industry,
        "prompt": prompt,
        "source_page": source_page,
        "is_primary_vendor": True,
        "evidence": vendor_validation.get("evidence", "")
    }

    # Only proceed with product analysis if confidence is high enough
    if vendor_validation.get("confidence_score", 0) >= 7:
        contact_info = extract_contact_info(text)
        vendor_entry.update({
            "email": contact_info["email"],
            "phone": contact_info["phone"]
        })

        # Analyze products to ensure they are primary developments
        products = analyze_products(text, vendor_validation["company_name"], industry)
        
        # Filter out products that are just integrations
        primary_products = [
            p for p in products 
            if p.get("is_own_product", False) and p.get("confidence_score", 0) >= 7
        ]

        if primary_products:
            vendor_entry["products"] = primary_products
            vendor_entry["has_primary_products"] = True
            vendor_entry["product_count"] = len(primary_products)
        else:
            vendor_entry["has_primary_products"] = False
            vendor_entry["product_count"] = 0

    return [vendor_entry]  # Return as a list to maintain compatibility
