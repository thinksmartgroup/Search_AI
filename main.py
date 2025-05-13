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
    get_prompt_progress,
    update_prompt_progress
)
from logger import save_vendor_log  
import time
import glob

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

def get_deployment_models():
    """Get deployment model categories and their characteristics"""
    return {
        "cloud_based": {
            "name": "Cloud-Based",
            "marking": "CLOUD",
            "characteristics": [
                "SaaS (Software as a Service)",
                "Cloud-hosted",
                "Browser-based access",
                "No local installation",
                "Automatic updates",
                "Subscription model",
                "Multi-tenant architecture"
            ],
            "documentation_types": [
                "Online documentation",
                "Knowledge base",
                "Video tutorials",
                "API documentation",
                "User guides"
            ]
        },
        "windows_server": {
            "name": "Windows Server-Based",
            "marking": "WINDOWS",
            "characteristics": [
                "On-premises installation",
                "Windows Server requirements",
                "Local database",
                "Client-server architecture",
                "Manual updates",
                "Perpetual license",
                "Single-tenant"
            ],
            "system_requirements": {
                "server": [
                    "Windows Server 2016/2019/2022",
                    "SQL Server 2016 or later",
                    "Minimum 16GB RAM",
                    "Quad-core processor",
                    "100GB+ storage",
                    "RAID configuration recommended",
                    "Regular backup system"
                ],
                "client": [
                    "Windows 10/11 Professional",
                    "4GB RAM minimum",
                    "Dual-core processor",
                    "1GB free disk space",
                    "Network connectivity",
                    "Latest .NET Framework",
                    "Compatible web browser"
                ],
                "network": [
                    "Gigabit network recommended",
                    "Static IP for server",
                    "Firewall configuration",
                    "VPN support if needed",
                    "Domain controller integration",
                    "Active Directory support",
                    "Network monitoring tools"
                ],
                "security": [
                    "SSL/TLS encryption",
                    "User authentication",
                    "Role-based access control",
                    "Audit logging",
                    "Data encryption at rest",
                    "Regular security updates",
                    "Compliance certifications"
                ]
            },
            "documentation_types": [
                "Installation guide (PDF)",
                "System requirements (PDF)",
                "User manual (PDF)",
                "Administration guide (PDF)",
                "Network setup guide (PDF)",
                "Security configuration guide (PDF)",
                "Troubleshooting guide (PDF)",
                "API documentation",
                "Video tutorials",
                "Knowledge base"
            ]
        },
        "web_based": {
            "name": "Web-Based",
            "marking": "WEB",
            "characteristics": [
                "Browser-based interface",
                "Hosted solution",
                "Internet access required",
                "No local installation",
                "Centralized updates",
                "Subscription or license model",
                "Multi-tenant or single-tenant"
            ],
            "documentation_types": [
                "Online documentation",
                "User guides (PDF)",
                "API documentation",
                "Video tutorials",
                "Knowledge base"
            ]
        }
    }

def find_vendors_by_deployment(industry, deployment_model):
    """Find vendors for a specific deployment model"""
    try:
        deployment_info = get_deployment_models()[deployment_model]
        
        # Load previously found vendors
        previously_found = set()
        for json_file in glob.glob(f"vendor_logs/{industry}_*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    for vendor in data.get("vendors", []):
                        website = vendor.get("website", "").lower().strip()
                        if website:
                            previously_found.add(website)
            except Exception as e:
                print(f"Warning: Error reading {json_file}: {e}")

        # Generate a simpler prompt
        prompt = f"""
        Find 10 software vendors for {industry} practices in the United States.
        Focus on {deployment_info['name']} solutions.
        
        For {industry}, consider these types of software:
        {get_industry_specific_considerations(industry)}
        
        Return a JSON array of 10 vendors with this structure:
        [
            {{
                "company_name": "string",
                "website": "string",
                "description": "string",
                "products": ["string"],
                "is_primary_vendor": true,
                "confidence_score": 0.8,
                "evidence": "string",
                "industry": "{industry}",
                "source": "gemini",
                "platform_type": "Practice Management Software",
                "platform_score": 1.0,
                "deployment_model": "{deployment_info['name']}",
                "deployment_marking": "{deployment_info['marking']}",
                "deployment_characteristics": ["string"],
                "company_size": "string",
                "founding_year": "number",
                "technology_stack": ["string"],
                "integration_capabilities": ["string"],
                "compliance_certifications": ["string"],
                "pricing_model": "string",
                "hosting_type": "string"
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
        
        # Filter out any vendors that were previously found
        vendors = [v for v in vendors if v.get("website", "").lower().strip() not in previously_found]
        
        # More lenient validation
        valid_vendors = []
        for vendor in vendors:
            website = vendor.get("website", "").lower().strip()
            if not website:
                continue
                
            # Skip only the most obvious invalid domains
            if any(pattern in website for pattern in [
                "facebook.com", "linkedin.com", "twitter.com",
                "youtube.com", "wikipedia.org", "gov", "edu"
            ]):
                continue
                
            valid_vendors.append(vendor)
        
        # Ensure we have exactly 10 vendors
        if len(valid_vendors) != 10:
            print(f"Warning: Got {len(valid_vendors)} unique vendors instead of 10")
            if len(valid_vendors) > 10:
                valid_vendors = valid_vendors[:10]
            else:
                # If we have less than 10, try one more time with a different prompt
                print("Retrying with a different prompt...")
                return find_vendors_by_deployment(industry, deployment_model)
        
        # Print results
        print(f"\nFound {len(valid_vendors)} {deployment_info['marking']} {deployment_info['name']} vendors for {industry}:")
        for vendor in valid_vendors:
            print(f"\n{deployment_info['marking']} {vendor['company_name']}")
            print(f"Website: {vendor['website']}")
            print(f"Description: {vendor['description']}")
            print(f"Products: {', '.join(vendor['products'])}")
            print(f"Primary Vendor: {vendor['is_primary_vendor']}")
            print(f"Confidence: {vendor['confidence_score']}")
            print(f"Evidence: {vendor['evidence']}")
            print(f"Deployment: {deployment_info['marking']} {vendor['deployment_model']}")
            
            if vendor.get('company_size'):
                print(f"Company Size: {vendor['company_size']}")
            if vendor.get('founding_year'):
                print(f"Founded: {vendor['founding_year']}")
            if vendor.get('technology_stack'):
                print(f"Tech Stack: {', '.join(vendor['technology_stack'])}")
            if vendor.get('pricing_model'):
                print(f"Pricing: {vendor['pricing_model']}")
            if vendor.get('hosting_type'):
                print(f"Hosting: {vendor['hosting_type']}")
            print("-" * 80)
            
        # Save to JSON
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_filename = f"vendor_logs/{industry}_{deployment_model}_{timestamp}.json"
        os.makedirs("vendor_logs", exist_ok=True)
        
        with open(json_filename, "w") as f:
            json.dump({"vendors": valid_vendors}, f, indent=2)
        print(f"\nSaved results to {json_filename}")
        
        # Save to Google Sheets
        written = update_google_sheet(valid_vendors, industry)
        print(f"Written {written} vendors to Google Sheets")
            
    except Exception as e:
        print(f"Error: {e}")
        return []

def run_pipeline(user_intent, industry):
    print(f"Starting vendor search for: '{user_intent}' in {industry}\n")

    # Get used prompts for this intent
    used_prompts = get_used_prompts_for_intent(user_intent)
    if len(used_prompts) >= MAX_PROMPTS_PER_INTENT:
        print(f"Maximum prompts ({MAX_PROMPTS_PER_INTENT}) reached for this intent")
        return

    # Generate next prompt variation
    next_prompt = generate_next_prompt_variation(user_intent, used_prompts)
    if not next_prompt:
        print("No new prompt variations available")
        return

    # Add to used prompts
    add_used_prompt(user_intent, next_prompt)
    print(f"Using prompt: {next_prompt}")

    # Fetch links from SerpAPI
    links = fetch_links_from_serpapi(next_prompt)
    if not links:
        print("No links found")
        return

    # Process each link
    for link_obj in links:
        try:
            # Summarize and extract contact info
            summary = summarize_and_extract_contact(link_obj["link"])
            if not summary:
                continue

            # Extract vendor information
            vendors = summary.get("vendors", [])
            for vendor in vendors:
                if not vendor.get("website"):
                    continue

                # Add source information
                vendor["source"] = link_obj.get("source", "google")
                vendor["title"] = link_obj.get("title", "")
                vendor["snippet"] = link_obj.get("snippet", "")

                # Fallback values
                if not vendor.get("platform_type"):
                    vendor["platform_type"] = "Unknown"
                if not vendor.get("platform_score"):
                    vendor["platform_score"] = 1.0

                # Save to log
                save_vendor_log(vendor)

                # Update Google Sheet
                update_google_sheet([vendor], industry)

        except Exception as e:
            print(f"Error processing {link_obj['link']}: {e}")
            continue

    # Update prompt progress
    update_prompt_progress(user_intent, next_prompt, len(links))


if __name__ == "__main__":
    # Define available industries
    industries = {
        "1": "chiropractic",
        "2": "optometry",
        "3": "auto_repair"
    }
    
    # Display industry menu
    print("\nSelect target industry:")
    print("1. Chiropractic")
    print("2. Optometry")
    print("3. Auto Repair")
    
    # Get industry selection
    while True:
        selection = input("\nEnter industry number (1-3): ").strip()
        if selection in industries:
            industry = industries[selection]
            break
        print("Invalid selection. Please enter 1, 2, or 3.")
    
    # Get deployment model
    deployment_models = {
        "1": "cloud_based",
        "2": "windows_server",
        "3": "web_based"
    }
    
    print("\nSelect deployment model:")
    print("1. Cloud-Based (SaaS)")
    print("2. Windows Server-Based")
    print("3. Web-Based")
    
    while True:
        model_selection = input("\nEnter deployment model number (1-3): ").strip()
        if model_selection in deployment_models:
            deployment_model = deployment_models[model_selection]
            break
        print("Invalid selection. Please enter 1, 2, or 3.")
    
    # Generate appropriate search intent
    search_intents = {
        "chiropractic": "Find primary software vendors for chiropractic practices",
        "optometry": "Find primary software vendors for optometry practices",
        "auto_repair": "Find primary software vendors for auto repair shops"
    }
    
    user_intent = search_intents[industry]
    deployment_info = get_deployment_models()[deployment_model]
    print(f"\nSearching for: {user_intent} with {deployment_info['name']} deployment")
    
    # Let Gemini take over
    print(f"\nGemini is searching for {industry} software vendors...")
    find_vendors_by_deployment(industry, deployment_model)
