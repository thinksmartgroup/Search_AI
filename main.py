import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from query_generator import generate_next_prompt_variation
from search_runner import fetch_links_from_serpapi
from summarizer import summarize_and_extract_contact
from json_writer import update_google_sheet
from prompt_tracker import (
    get_used_prompts_for_intent,
    add_used_prompt,
    is_prompt_completed,
    update_prompt_progress
)
from logger import save_vendor_log  
import time

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")

MAX_PROMPTS_PER_INTENT = 3

def get_industry_specific_considerations(industry):
    """Get industry-specific search considerations"""
    considerations = {
        "chiropractic": """
        - Practice management software
        - EHR (Electronic Health Records)
        - Billing and insurance management
        - Patient management systems
        - Treatment plan software
        - SOAP notes software
        - Chiropractic documentation
        - Insurance claim processing
        - Patient scheduling systems
        - Compliance management
        - HIPAA compliant software
        - Treatment tracking
        - Outcome assessment tools
        """,
        "optometry": """
        - Practice management software
        - Vision testing software
        - Patient records management
        - Optical lab management
        - Frame inventory management
        - Contact lens management
        - Vision insurance processing
        - Appointment scheduling
        - Optical dispensing software
        - Vision therapy tracking
        - Eye exam documentation
        - Prescription management
        - Inventory tracking
        """,
        "auto_repair": """
        - Shop management software
        - Parts inventory management
        - Customer management systems
        - Repair order management
        - Vehicle inspection software
        - Service scheduling systems
        - Parts ordering integration
        - Customer communication tools
        - Repair tracking systems
        - Diagnostic tool integration
        - Warranty management
        - Labor time tracking
        - Customer portal systems
        """
    }
    return considerations.get(industry.lower(), "")

def find_vendors(industry):
    """Use Gemini to find vendors for the selected industry"""
    try:
        prompt = f"""
        Find EXACTLY 10 primary software vendors for {industry} practices. 
        Focus on companies that develop their own software, not third-party integrators.
        
        For {industry}, consider these types of software:
        {get_industry_specific_considerations(industry)}
        
        Requirements:
        1. Return EXACTLY 10 vendors, no more, no less
        2. Only include companies that develop their own software
        3. Exclude resellers, consultants, and third-party integrators
        4. Focus on commercial software products
        5. Each vendor must be distinct and unique
        6. Include complete details for each vendor
        
        Return a JSON array of EXACTLY 10 vendors with this structure:
        [
            {{
                "company_name": "string",
                "website": "string",
                "description": "string",
                "products": ["string"],
                "is_primary_vendor": true/false,
                "confidence_score": 0-1,
                "evidence": "string",
                "industry": "{industry}",
                "source": "gemini",
                "platform_type": "Practice Management Software",
                "platform_score": 1.0
            }}
        ]
        """

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        # Handle potential JSON formatting issues
        if not response_text.startswith("["):
            response_text = response_text[response_text.find("["):]
        if not response_text.endswith("]"):
            response_text = response_text[:response_text.rfind("]")+1]
            
        vendors = json.loads(response_text)
        
        # Ensure we have exactly 10 vendors
        if len(vendors) != 10:
            print(f"⚠️ Warning: Got {len(vendors)} vendors instead of 10")
            if len(vendors) > 10:
                vendors = vendors[:10]
            else:
                # If we have less than 10, try again
                return find_vendors(industry)
        
        # Print results
        print(f"\n✅ Found {len(vendors)} vendors for {industry}:")
        for vendor in vendors:
            print(f"\n📋 {vendor['company_name']}")
            print(f"🌐 {vendor['website']}")
            print(f"📝 {vendor['description']}")
            print(f"🛠️  Products: {', '.join(vendor['products'])}")
            print(f"🎯 Primary Vendor: {vendor['is_primary_vendor']}")
            print(f"📊 Confidence: {vendor['confidence_score']}")
            print(f"🔍 Evidence: {vendor['evidence']}")
            print("-" * 80)
            
        # Save to JSON
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_filename = f"vendor_logs/{industry}_{timestamp}.json"
        os.makedirs("vendor_logs", exist_ok=True)
        
        with open(json_filename, "w") as f:
            json.dump({"vendors": vendors}, f, indent=2)
        print(f"\n💾 Saved results to {json_filename}")
        
        # Save to Google Sheets
        written = update_google_sheet(vendors, industry)
        print(f"📊 Written {written} vendors to Google Sheets")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def run_pipeline(user_intent, industry):
    print(f"🔍 Starting vendor search for: '{user_intent}' in {industry}\n")

    used_prompts = get_used_prompts_for_intent(user_intent)

    while len(used_prompts) < MAX_PROMPTS_PER_INTENT:
        prompt = generate_next_prompt_variation(user_intent, used_prompts)
        if not prompt:
            print("⚠️ Gemini could not generate a new prompt.")
            break

        print(f"🧠 New prompt from Gemini: {prompt}")

        while not is_prompt_completed(prompt):
            print(f"🚀 Working on prompt: {prompt}")

            link_objs = fetch_links_from_serpapi(prompt, industry)
            if not link_objs:
                print(f"⚠️ No links found for prompt: {prompt}")
                update_prompt_progress(prompt, new_entries=0)
                break

            parsed_vendors = []
            for link_obj in link_objs:
                vendor_results = summarize_and_extract_contact(
                    link_obj["url"],
                    prompt=prompt,
                    industry=industry,
                    source_page=link_obj["source_page"]
                )

                for vendor in vendor_results:
                    if not vendor.get("website"):
                        continue

                    # Add source information
                    vendor["source"] = link_obj.get("source", "google")
                    vendor["title"] = link_obj.get("title", "")
                    vendor["snippet"] = link_obj.get("snippet", "")

                    # Fallback values
                    if not vendor.get("platform_type"):
                        vendor["platform_type"] = "Unknown"
                        vendor["platform_score"] = 0
                    elif "platform_score" not in vendor:
                        vendor["platform_score"] = 1

                    parsed_vendors.append(vendor)

            # Save all vendors to JSON (even if some are duplicates)
            save_vendor_log(parsed_vendors, industry, prompt)

            if parsed_vendors:
                print(f"📥 Attempting to write {len(parsed_vendors)} vendors to sheet...")
                unique_written = update_google_sheet(parsed_vendors, industry)
                update_prompt_progress(prompt, new_entries=unique_written)
            else:
                update_prompt_progress(prompt, new_entries=0)

            print("-" * 60)

        add_used_prompt(user_intent, prompt)
        used_prompts.append(prompt)

    print("🏁 Finished processing all prompts for this intent.\n")


if __name__ == "__main__":
    # Define available industries
    industries = {
        "1": "chiropractic",
        "2": "optometry",
        "3": "auto_repair"
    }
    
    # Display industry menu
    print("\n🏷️  Select target industry:")
    print("1. Chiropractic")
    print("2. Optometry")
    print("3. Auto Repair")
    
    # Get industry selection
    while True:
        selection = input("\n🔢 Enter industry number (1-3): ").strip()
        if selection in industries:
            industry = industries[selection]
            break
        print("❌ Invalid selection. Please enter 1, 2, or 3.")
    
    # Generate appropriate search intent based on industry
    search_intents = {
        "chiropractic": "Find primary software vendors for chiropractic practices",
        "optometry": "Find primary software vendors for optometry practices",
        "auto_repair": "Find primary software vendors for auto repair shops"
    }
    
    user_intent = search_intents[industry]
    print(f"\n🔍 Searching for: {user_intent}")
    
    # Let Gemini take over
    print(f"\n🤖 Gemini is searching for {industry} software vendors...")
    find_vendors(industry)
