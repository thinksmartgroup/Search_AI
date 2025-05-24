import os
import json
import time
import glob

print("Starting imports...")  # Debug print

print("Importing google.generativeai...")
import google.generativeai as genai
print("Importing dotenv...")
from dotenv import load_dotenv
print("Importing query_generator...")
from query_generator import generate_next_prompt_variation
print("Importing search_runner...")
from search_runner import fetch_links_from_serpapi
print("Importing summarizer...")
from summarizer import summarize_and_extract_contact
print("Importing json_writer...")
from json_writer import update_google_sheet
print("Importing prompt_tracker...")
from prompt_tracker import (
    get_used_prompts_for_intent,
    add_used_prompt,
    get_prompt_progress,
    update_prompt_progress
)
print("Importing logger...")
from logger import save_vendor_log

print("Imports successful")  # Debug print

# Load environment variables
print("Loading environment variables...")  # Debug print
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY not found in environment variables.")
    print("Please create a .env file with your GEMINI_API_KEY or set it in your environment.")
    exit(1)

print("Configuring Gemini...")  # Debug print
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")
except Exception as e:
    print(f"Error configuring Gemini API: {e}")
    print("Please check your API key and try again.")
    exit(1)

print("Gemini configured successfully")  # Debug print

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

def find_vendors_by_deployment(industry, deployment_model, retry_count=0, max_retries=5):
    """Find vendors for a specific deployment model"""
    try:
        if retry_count >= max_retries:
            print(f"\nReached maximum retry attempts ({max_retries}). Proceeding with current vendors.")
            return

        deployment_info = get_deployment_models()[deployment_model]
        
        # Load previously found vendors
        previously_found = set()
        for json_file in glob.glob(f"vendor_logs/{industry}_*.json"):
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)
                    # Handle both old and new formats
                    if isinstance(data, list):
                        # New format with merged array
                        for vendor_group in data:
                            if isinstance(vendor_group, dict) and "merged" in vendor_group:
                                for vendor in vendor_group["merged"]:
                                    if isinstance(vendor, dict):
                                        website = vendor.get("website", "").lower().strip()
                                        if website:
                                            previously_found.add(website)
                    elif isinstance(data, dict):
                        # Old format with vendors array
                        for vendor in data.get("vendors", []):
                            if isinstance(vendor, dict):
                                website = vendor.get("website", "").lower().strip()
                                if website:
                                    previously_found.add(website)
            except Exception as e:
                print(f"Warning: Error reading {json_file}: {e}")
                continue

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
                "products": "string",
                "is_primary_vendor": "True",
                "confidence_score": "0.85",
                "evidence": "string",
                "industry": "{industry}",
                "source": "gemini",
                "platform_type": "{deployment_info['name']}",
                "platform_score": {5 if deployment_model == 'cloud_based' else 1},
                "deployment_model": "{deployment_info['name']}",
                "deployment_marking": "{deployment_info['marking']}",
                "deployment_characteristics": "string",
                "company_size": "string",
                "founding_year": "string",
                "technology_stack": "string",
                "integration_capabilities": "string",
                "compliance_certifications": "string",
                "pricing_model": "string",
                "hosting_type": "string",
                "created_at": "YYYY-MM-DD HH:MM:SS",
                "updated_at": "YYYY-MM-DD HH:MM:SS"
            }}
        ]
        """

        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
        except Exception as e:
            print(f"Error generating content with Gemini: {e}")
            print("Retrying with a different prompt...")
            return find_vendors_by_deployment(industry, deployment_model, retry_count + 1, max_retries)
        
        # Handle potential JSON formatting issues
        if not response_text.startswith("["):
            response_text = response_text[response_text.find("["):]
        if not response_text.endswith("]"):
            response_text = response_text[:response_text.rfind("]")+1]
            
        try:
            vendors = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON response: {e}")
            print("Retrying with a different prompt...")
            return find_vendors_by_deployment(industry, deployment_model, retry_count + 1, max_retries)
        
        # Filter out any vendors that were previously found
        vendors = [v for v in vendors if v.get("website", "").lower().strip() not in previously_found]
        
        # More lenient validation
        valid_vendors = []
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
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
            
            # Add timestamps and ensure all fields exist with optometry-style defaults
            vendor["created_at"] = current_time
            vendor["updated_at"] = current_time
            vendor["is_primary_vendor"] = "True"
            vendor["confidence_score"] = "0.85"
            vendor["evidence"] = vendor.get("evidence", "Based on website analysis and industry knowledge")
            vendor["source"] = "gemini"
            vendor["deployment_model"] = deployment_info["name"]
            vendor["deployment_marking"] = deployment_info["marking"]
            vendor["deployment_characteristics"] = vendor.get("deployment_characteristics", "Windows Server-based deployment with local installation")
            vendor["company_size"] = vendor.get("company_size", "Small to Medium")
            vendor["founding_year"] = vendor.get("founding_year", "2000")
            vendor["technology_stack"] = vendor.get("technology_stack", "Windows Server, SQL Server")
            vendor["integration_capabilities"] = vendor.get("integration_capabilities", "Standard integration capabilities")
            vendor["compliance_certifications"] = vendor.get("compliance_certifications", "Industry standard certifications")
            vendor["pricing_model"] = vendor.get("pricing_model", "Contact for Quote")
            vendor["hosting_type"] = vendor.get("hosting_type", "On-Premise")
                
            valid_vendors.append(vendor)
        
        # Save current vendors regardless of count
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        json_filename = f"vendor_logs/{industry}_{deployment_model}_{timestamp}.json"
        os.makedirs("vendor_logs", exist_ok=True)
        
        # Format vendors in the optometry style with two entries per vendor
        formatted_vendors = []
        for vendor in valid_vendors:
            # Create two slightly different versions of the same vendor
            vendor1 = vendor.copy()
            vendor2 = vendor.copy()
            
            # Modify the second version slightly
            if "|" in vendor2["company_name"]:
                vendor2["company_name"] = vendor2["company_name"].split("|")[0].strip()
            else:
                vendor2["company_name"] = f"{vendor2['company_name']} - Contact"
            
            formatted_vendor = {
                "merged": [vendor1, vendor2]
            }
            formatted_vendors.append(formatted_vendor)
        
        with open(json_filename, "w") as f:
            json.dump(formatted_vendors, f, indent=2)
        print(f"\nSaved {len(valid_vendors)} vendors to {json_filename}")
        
        # Print current vendors
        print(f"\nCurrent vendors found ({len(valid_vendors)}):")
        for vendor_group in formatted_vendors:
            vendor = vendor_group["merged"][0]  # Use first version for display
            print(f"\n{deployment_info['marking']} {vendor['company_name']}")
            print(f"Website: {vendor['website']}")
            print(f"Description: {vendor['description']}")
            print(f"Products: {vendor['products']}")
            print(f"Primary Vendor: {vendor['is_primary_vendor']}")
            print(f"Confidence: {vendor['confidence_score']}")
            print(f"Evidence: {vendor['evidence']}")
            print(f"Deployment: {vendor['deployment_marking']} {vendor['deployment_model']}")
            print(f"Company Size: {vendor['company_size']}")
            print(f"Founded: {vendor['founding_year']}")
            print(f"Tech Stack: {vendor['technology_stack']}")
            print(f"Pricing: {vendor['pricing_model']}")
            print(f"Hosting: {vendor['hosting_type']}")
            print("-" * 80)
        
        # Ensure we have exactly 10 vendors
        if len(valid_vendors) != 10:
            print(f"Warning: Got {len(valid_vendors)} unique vendors instead of 10")
            if len(valid_vendors) > 10:
                valid_vendors = valid_vendors[:10]
                formatted_vendors = formatted_vendors[:10]
            else:
                # If we have less than 10, try one more time with a different prompt
                print(f"Retrying with a different prompt... (Attempt {retry_count + 1} of {max_retries})")
                return find_vendors_by_deployment(industry, deployment_model, retry_count + 1, max_retries)
        
        # Save to Google Sheets
        try:
            # Convert formatted vendors back to flat list for sheet writing
            sheet_vendors = []
            for vendor_group in formatted_vendors:
                # Add both entries from the merged array
                sheet_vendors.extend(vendor_group["merged"])
            written = update_google_sheet(sheet_vendors, industry)
            print(f"Written {written} vendors to Google Sheets")
        except Exception as e:
            print(f"Warning: Failed to write to Google Sheets: {e}")
            print(f"Error details: {str(e)}")
            # Try to save the vendors to a local file as backup
            try:
                backup_file = f"vendor_logs/{industry}_{deployment_model}_sheet_backup_{timestamp}.json"
                with open(backup_file, "w") as f:
                    json.dump(sheet_vendors, f, indent=2)
                print(f"Saved vendors to backup file: {backup_file}")
            except Exception as backup_error:
                print(f"Failed to save backup file: {backup_error}")
            
    except Exception as e:
        print(f"Error: {e}")
        # Try to save any vendors we found before the error
        if 'valid_vendors' in locals() and valid_vendors:
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                json_filename = f"vendor_logs/{industry}_{deployment_model}_error_{timestamp}.json"
                os.makedirs("vendor_logs", exist_ok=True)
                
                with open(json_filename, "w") as f:
                    json.dump({"vendors": valid_vendors, "error": str(e)}, f, indent=2)
                print(f"\nSaved {len(valid_vendors)} vendors to {json_filename} before error")
            except Exception as save_error:
                print(f"Failed to save vendors after error: {save_error}")
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
    print("Starting script...")  # Debug print
    
    # Define available industries
    industries = {
        "1": "chiropractic",
        "2": "optometry",
        "3": "auto_repair"
    }
    
    print("Displaying menu...")  # Debug print
    
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
    
    print(f"Selected industry: {industry}")  # Debug print
    
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
    
    print(f"Selected deployment model: {deployment_model}")  # Debug print
    
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
