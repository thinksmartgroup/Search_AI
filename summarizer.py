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

def summarize_and_extract_contact(url, prompt="", industry="", source_page=0):
    print(f"🔍 Processing: {url}")
    text = fetch_text_from_url(url)
    if not text:
        return []

    contact_info = extract_contact_info(text)

    try:
        gemini_prompt = (
            f"Based on this webpage content:\n\n{text[:5000]}\n\n"
            "Identify all software vendors or companies relevant to chiropractic practice management, EHR, or billing. "
            "For each vendor, extract:\n"
            "- product: name of the product or software\n"
            "- platform: one of 'Windows Server', 'Cloud-based', 'Web-based', or best technical guess\n"
            "- If multiple vendors exist, return all.\n"
            "Respond only as a JSON list:\n"
            "[ {\"product\": \"ProductName\", \"platform\": \"Windows Server\"}, ... ]"
        )

        response = model.generate_content(
            gemini_prompt,
            request_options={"timeout": 600}
        )
        full_output = response.text.strip()
        products = extract_json_block(full_output)

    except Exception as e:
        print(f"⚠️ Gemini processing failed for {url}: {e}")
        return []

    vendor_entries = []
    for product_info in products:
        product = product_info.get("product", "").strip()
        platform = product_info.get("platform", "").strip()
        score = score_platform(platform)

        if not product:
            continue

        vendor_entries.append({
            "website": url,
            "email": contact_info["email"],
            "phone": contact_info["phone"],
            "summary": f"{product} - likely on {platform}",
            "industry": industry,
            "prompt": prompt,
            "source_page": source_page,
            "product": product,
            "platform_type": platform,
            "platform_score": score,
            "products": [product_info]  # keep raw data flattened in writer
        })

    return vendor_entries
