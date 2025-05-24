import os
import json
import glob
from collections import defaultdict
from urllib.parse import urlparse

# Define valid fields and their expected types
VALID_FIELDS = {
    "website": str,
    "company_name": str,
    "description": str,
    "products": list,
    "is_primary_vendor": bool,
    "confidence_score": float,
    "evidence": str,
    "industry": str,
    "source": str,
    "platform_type": str,
    "platform_score": float
}

# Define valid industries
VALID_INDUSTRIES = {"chiropractic", "optometry", "auto_repair"}

# Define valid platform types
VALID_PLATFORM_TYPES = {
    "Practice Management Software",
    "Electronic Health Records",
    "Patient Management System",
    "Appointment Scheduling Software",
    "Billing Software",
    "Inventory Management",
    "Service Management Software"
}

def normalize_url(url):
    """Normalize URL for comparison"""
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.netloc.lower().replace("www.", "").strip()

def is_valid_website(url):
    """Check if website URL is valid and relevant"""
    if not url:
        return False
        
    # Normalize URL
    url = normalize_url(url)
    
    # Invalid patterns
    invalid_patterns = {
        "facebook.com", "linkedin.com", "twitter.com", "instagram.com",
        "youtube.com", "pinterest.com", "blogspot.com", "wordpress.com",
        "medium.com", "github.com", "bitbucket.org", "gitlab.com",
        "docs.google.com", "drive.google.com", "dropbox.com",
        "capterra.com", "g2.com", "softwareadvice.com",
        "trustpilot.com", "yelp.com", "glassdoor.com",
        "amazon.com", "ebay.com", "etsy.com",
        "wikipedia.org", "wikihow.com",
        "nexhealth.com", "zocdoc.com", "patientpop.com",
        "healthgrades.com", "vitals.com", "webmd.com"
    }
    
    return not any(pattern in url for pattern in invalid_patterns)

def analyze_vendor(vendor):
    """Analyze a single vendor entry for issues"""
    issues = []
    
    # Check for missing required fields
    for field, expected_type in VALID_FIELDS.items():
        if field not in vendor:
            issues.append(f"Missing required field: {field}")
        elif not isinstance(vendor[field], expected_type):
            issues.append(f"Invalid type for {field}: expected {expected_type.__name__}, got {type(vendor[field]).__name__}")
    
    # Check website validity
    if not is_valid_website(vendor.get("website", "")):
        issues.append("Invalid or irrelevant website URL")
    
    # Check industry validity
    if vendor.get("industry") not in VALID_INDUSTRIES:
        issues.append(f"Invalid industry: {vendor.get('industry')}")
    
    # Check platform type validity
    if vendor.get("platform_type") not in VALID_PLATFORM_TYPES:
        issues.append(f"Invalid platform type: {vendor.get('platform_type')}")
    
    # Check confidence score range
    score = vendor.get("confidence_score", 0)
    if not isinstance(score, (int, float)) or score < 0 or score > 1:
        issues.append(f"Invalid confidence score: {score}")
    
    # Check for empty or invalid products
    products = vendor.get("products", [])
    if not isinstance(products, list):
        issues.append("Products must be a list")
    elif not products:
        issues.append("Empty products list")
    
    return issues

def scan_json_file(json_path):
    """Scan a single JSON file for issues"""
    try:
        print(f"\n📂 Scanning {os.path.basename(json_path)}")
        
        # Load vendors from JSON
        with open(json_path, "r") as f:
            data = json.load(f)
        vendors = data.get("vendors", [])
        
        if not vendors:
            print("⚠️ No vendors found in JSON file")
            return [], []
        
        # Analyze each vendor
        issues_by_vendor = {}
        valid_vendors = []
        
        for vendor in vendors:
            issues = analyze_vendor(vendor)
            if issues:
                issues_by_vendor[vendor.get("website", "unknown")] = issues
            else:
                valid_vendors.append(vendor)
        
        return valid_vendors, issues_by_vendor
        
    except Exception as e:
        print(f"❌ Error scanning {json_path}: {e}")
        return [], {}

def main():
    # Get all JSON files
    json_files = sorted(glob.glob("vendor_logs/*.json"))
    
    if not json_files:
        print("❌ No JSON files found in vendor_logs directory")
        return
    
    print(f"\n📁 Found {len(json_files)} JSON files")
    
    # Process each file
    all_issues = defaultdict(list)
    all_valid_vendors = []
    
    for json_file in json_files:
        valid_vendors, issues = scan_json_file(json_file)
        all_valid_vendors.extend(valid_vendors)
        
        if issues:
            for website, vendor_issues in issues.items():
                all_issues[website].extend(vendor_issues)
    
    # Print summary
    print("\n✨ Scan Summary:")
    print(f"📊 Total vendors scanned: {len(all_valid_vendors) + len(all_issues)}")
    print(f"✅ Valid vendors: {len(all_valid_vendors)}")
    print(f"❌ Vendors with issues: {len(all_issues)}")
    
    if all_issues:
        print("\n🔍 Issues found:")
        for website, issues in all_issues.items():
            print(f"\n🌐 {website}:")
            for issue in issues:
                print(f"  - {issue}")
        
        # Ask if user wants to clean up the files
        response = input("\n🧹 Would you like to clean up the JSON files? (y/n): ").lower()
        if response == 'y':
            for json_file in json_files:
                valid_vendors, _ = scan_json_file(json_file)
                if valid_vendors:
                    # Update the JSON file with only valid vendors
                    with open(json_file, "w") as f:
                        json.dump({"vendors": valid_vendors}, f, indent=2)
                    print(f"✅ Cleaned up {os.path.basename(json_file)}")
                else:
                    # Remove empty files
                    os.remove(json_file)
                    print(f"🗑️  Removed empty file {os.path.basename(json_file)}")

if __name__ == "__main__":
    main() 