import os
import json
import requests
from serpapi import GoogleSearch
from dotenv import load_dotenv
from prompt_tracker import get_prompt_progress, update_prompt_progress, is_prompt_completed
import google.generativeai as genai
from bs4 import BeautifulSoup
import time

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")

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

def get_industry_specific_search_patterns(industry):
    """Get industry-specific search patterns to improve results"""
    patterns = {
        "chiropractic": [
            "chiropractic software developer company",
            "chiropractic practice management software developer",
            "chiropractic EHR software company",
            "chiropractic documentation software developer",
            "chiropractic billing software developer",
            "chiropractic patient management software company",
            "chiropractic treatment planning software developer",
            "chiropractic SOAP notes software company",
            "chiropractic compliance software developer",
            "chiropractic insurance processing software company"
        ],
        "optometry": [
            "optometry software developer company",
            "optometry practice management software developer",
            "optometry vision testing software company",
            "optometry patient management software developer",
            "optometry lab management software company",
            "optometry frame inventory software developer",
            "optometry contact lens software company",
            "optometry scheduling system developer",
            "optometry optical dispensing software developer",
            "optometry vision therapy software company"
        ],
        "auto_repair": [
            "auto repair software developer company",
            "auto shop management software developer",
            "auto repair parts inventory software company",
            "auto repair customer management software developer",
            "auto repair order management software company",
            "auto repair inspection software developer",
            "auto repair scheduling system company",
            "auto repair diagnostic software developer",
            "auto repair warranty management software company",
            "auto repair labor tracking software developer"
        ]
    }
    return patterns.get(industry.lower(), [])

def generate_search_queries(industry, base_prompt):
    """Generate optimized search queries for finding primary software vendors"""
    try:
        # Get industry-specific patterns
        industry_patterns = get_industry_specific_search_patterns(industry)
        
        gemini_prompt = (
            f"Generate 3 specific Google search queries to find primary software vendors for {industry}.\n"
            f"Base prompt: {base_prompt}\n\n"
            "Requirements:\n"
            "1. Focus on finding companies that develop their own software\n"
            "2. Exclude resellers, consultants, and third-party integrators\n"
            "3. Target companies with commercial products\n"
            "4. Include relevant keywords for {industry}\n\n"
            "For {industry}, consider:\n"
            f"{get_industry_specific_considerations(industry)}\n\n"
            "Use these industry-specific patterns as inspiration:\n"
            f"{json.dumps(industry_patterns, indent=2)}\n\n"
            "IMPORTANT: Make queries specific to find PRIMARY software developers, not third-party tools.\n"
            "Include terms like 'software developer', 'software company', 'technology company'.\n"
            "Exclude terms like 'integration', 'connector', 'plugin', 'add-on'.\n\n"
            "Return a JSON list of queries:\n"
            "[ \"query1\", \"query2\", \"query3\" ]"
        )

        response = model.generate_content(gemini_prompt)
        response_text = response.text.strip()
        
        # Handle potential JSON formatting issues
        if not response_text.startswith("["):
            response_text = response_text[response_text.find("["):]
        if not response_text.endswith("]"):
            response_text = response_text[:response_text.rfind("]")+1]
            
        queries = json.loads(response_text)
        
        # Validate and clean queries
        cleaned_queries = []
        for query in queries:
            # Add developer/company indicators if missing
            if not any(term in query.lower() for term in ["developer", "company", "technology", "software"]):
                query = f"{query} software developer"
            # Remove any integration-related terms
            query = query.replace(" integration", "").replace(" connector", "").replace(" plugin", "")
            cleaned_queries.append(query)
            
        return cleaned_queries
    except Exception as e:
        print(f"⚠️ Failed to generate search queries: {e}")
        # Fallback to more specific queries
        fallback_queries = [
            f"{industry} software developer company",
            f"{industry} technology company software",
            f"{industry} practice management software developer"
        ]
        return fallback_queries

def is_valid_vendor_url(url: str) -> bool:
    """Enhanced URL validation to filter out irrelevant sites and third-party integrators"""
    # Invalid patterns for all industries
    invalid_patterns = [
        # Social media and content platforms
        "youtube.com", "facebook.com", "linkedin.com", "twitter.com",
        "instagram.com", "pinterest.com", "tiktok.com", "reddit.com",
        "medium.com", "quora.com", "stackoverflow.com", "github.com",
        
        # Blog and CMS platforms
        "blogspot.com", "wordpress.com", "wix.com", "squarespace.com",
        "weebly.com", "tumblr.com", "substack.com",
        
        # Document and file sharing
        "pdf", "doc", "ppt", "xls", "txt", "zip", "rar",
        "dropbox.com", "drive.google.com", "onedrive.live.com",
        
        # Review and directory sites
        "yelp.com", "yellowpages.com", "bbb.org", "glassdoor.com",
        "indeed.com", "monster.com", "careerbuilder.com",
        
        # News and media
        "news", "article", "press-release", "media",
        "reuters.com", "bloomberg.com", "cnbc.com",
        
        # E-commerce platforms
        "amazon.com", "ebay.com", "etsy.com", "shopify.com",
        
        # Government and educational
        "gov", "edu", "org", "wikipedia.org",
        
        # Common file extensions
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".txt", ".csv", ".zip", ".rar", ".7z",
        
        # Common non-vendor paths
        "/blog/", "/news/", "/articles/", "/press/",
        "/about/", "/contact/", "/support/", "/help/",
        "/pricing/", "/features/", "/solutions/",
        
        # Known third-party integrators and non-primary vendors
        "nexhealth.com",
        "zocdoc.com",
        "patientpop.com",
        "solutionreach.com",
        "weave.com",
        "lumahealth.com",
        "phreesia.com",
        "drchrono.com",
        "athenahealth.com",
        "epic.com",
        "cerner.com",
        "allscripts.com",
        "meditech.com",
        "nextgen.com",
        "eclinicalworks.com",
        "greenwayhealth.com",
        "practicefusion.com",
        "kareo.com",
        "advancedmd.com",
        "webpt.com",
        "therabill.com",
        "clinicient.com",
        "clinicmaster.com",
        "clinicmate.com",
        "clinicware.com",
        "clinicpro.com",
        "clinicsoft.com",
        "clinicware.com",
        "clinicware.net",
        "clinicware.org",
        "clinicware.info",
        "clinicware.biz",
        "clinicware.co",
        "clinicware.io",
        "clinicware.app",
        "clinicware.software",
        "clinicware.solutions",
        "clinicware.tech",
        "clinicware.technology",
        "clinicware.systems",
        "clinicware.platform",
        "clinicware.apps",
        "clinicware.services",
        "clinicware.products",
        "clinicware.solutions",
        "clinicware.software",
        "clinicware.tech",
        "clinicware.technology",
        "clinicware.systems",
        "clinicware.platform",
        "clinicware.apps",
        "clinicware.services",
        "clinicware.products",
        
        # Common third-party integration terms
        "integration", "connector", "plugin", "add-on", "extension",
        "api", "sdk", "developer", "partner", "marketplace",
        "app store", "app marketplace", "app directory",
        "third-party", "third party", "3rd party", "3rd-party",
        
        # Common reseller terms
        "reseller", "distributor", "dealer", "partner",
        "authorized", "certified", "premium", "premier",
        
        # Common consulting terms
        "consulting", "consultant", "advisor", "advisory",
        "implementation", "deployment", "setup", "configuration",
        
        # Common marketing terms that might indicate non-vendor
        "compare", "comparison", "review", "reviews",
        "top", "best", "leading", "premium", "premier",
        "award", "awards", "certified", "certification"
    ]
    
    # Check for invalid patterns
    if any(pattern in url.lower() for pattern in invalid_patterns):
        return False
        
    # Check for common vendor indicators
    vendor_indicators = [
        "/software", "/solutions", "/products", "/platform",
        "/technology", "/systems", "/applications", "/services",
        "/company", "/about-us", "/contact-us"
    ]
    
    # If URL doesn't have any vendor indicators, it might not be a vendor site
    if not any(indicator in url.lower() for indicator in vendor_indicators):
        return False
        
    # Additional checks for primary software vendor indicators
    primary_vendor_indicators = [
        # Development and Engineering
        "develop", "development", "engineer", "engineering",
        "build", "building", "create", "creating",
        "design", "designing", "architect", "architecture",
        "code", "coding", "program", "programming",
        "developers", "engineers", "builders", "creators",
        
        # Core Technology
        "core", "platform", "framework", "foundation",
        "proprietary", "patent", "patented", "intellectual property",
        "technology", "technologies", "software", "solutions",
        "products", "applications", "systems", "platforms",
        "infrastructure", "architecture", "stack", "tech stack",
        
        # Product Development
        "product", "products", "solution", "solutions",
        "application", "applications", "system", "systems",
        "platform", "platforms", "suite", "suites",
        "module", "modules", "component", "components",
        
        # Technical Capabilities
        "api", "sdk", "library", "libraries",
        "framework", "frameworks", "engine", "engines",
        "database", "databases", "server", "servers",
        "cloud", "cloud-native", "microservices", "container",
        
        # Industry-Specific Development
        "healthcare", "medical", "clinical", "patient",
        "practice", "clinic", "hospital", "pharmacy",
        "optometry", "vision", "optical", "eye care",
        "chiropractic", "chiropractor", "spinal", "rehabilitation",
        "auto", "automotive", "repair", "maintenance",
        
        # Development Methodologies
        "agile", "scrum", "devops", "ci/cd",
        "continuous", "integration", "deployment",
        "testing", "qa", "quality", "assurance",
        
        # Technical Innovation
        "innovate", "innovation", "research", "development",
        "r&d", "rd", "labs", "laboratory",
        "prototype", "prototyping", "pilot", "beta",
        
        # Enterprise Features
        "enterprise", "business", "corporate", "commercial",
        "scalable", "scalability", "reliable", "reliability",
        "secure", "security", "compliance", "certified"
    ]
    
    # Check if the URL or domain contains primary vendor indicators
    domain = url.lower().split("//")[-1].split("/")[0]
    if not any(indicator in domain for indicator in primary_vendor_indicators):
        return False
        
    return True

def search_capterra(industry: str) -> list:
    """Search for software vendors on Capterra"""
    try:
        # Map industry to Capterra category
        category_map = {
            "chiropractic": "chiropractic-software",
            "optometry": "optometry-software",
            "auto_repair": "auto-repair-shop-software"
        }
        
        category = category_map.get(industry.lower())
        if not category:
            return []
            
        # Construct Capterra URL
        url = f"https://www.capterra.com/categories/{category}/"
        
        # Add headers to mimic browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Fetch the page
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return []
            
        # Parse the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find software listings
        listings = []
        for listing in soup.find_all('div', class_='listing-card'):
            try:
                # Extract vendor information
                vendor_name = listing.find('h3', class_='listing-name').text.strip()
                vendor_url = listing.find('a', class_='listing-link')['href']
                
                # Get vendor details
                vendor_details = get_capterra_vendor_details(vendor_url, headers)
                
                if vendor_details and is_valid_vendor_url(vendor_details['website']):
                    listings.append({
                        'name': vendor_name,
                        'url': vendor_details['website'],
                        'description': vendor_details['description'],
                        'features': vendor_details['features'],
                        'source': 'capterra',
                        'industry': industry
                    })
                    
                # Be nice to Capterra's servers
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Error processing Capterra listing: {e}")
                continue
                
        return listings
        
    except Exception as e:
        print(f"⚠️ Error searching Capterra: {e}")
        return []

def get_capterra_vendor_details(url: str, headers: dict) -> dict:
    """Get detailed information about a vendor from their Capterra page"""
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract vendor website
        website = None
        website_link = soup.find('a', class_='website-link')
        if website_link:
            website = website_link['href']
            
        # Extract description
        description = None
        desc_elem = soup.find('div', class_='description')
        if desc_elem:
            description = desc_elem.text.strip()
            
        # Extract features
        features = []
        features_elem = soup.find('div', class_='features')
        if features_elem:
            for feature in features_elem.find_all('li'):
                features.append(feature.text.strip())
                
        return {
            'website': website,
            'description': description,
            'features': features
        }
        
    except Exception as e:
        print(f"⚠️ Error getting Capterra vendor details: {e}")
        return None

def fetch_links_from_serpapi(prompt: str, industry: str, pages_per_run: int = 3) -> list:
    if not SERPAPI_KEY:
        print("❌ Missing SERPAPI_API_KEY in .env")
        return []

    if is_prompt_completed(prompt):
        print(f"✅ Prompt completed: '{prompt}'")
        return []

    # Generate optimized search queries
    search_queries = generate_search_queries(industry, prompt)
    all_links = []
    
    # Search Capterra
    print("\n🔍 Searching Capterra...")
    capterra_results = search_capterra(industry)
    all_links.extend(capterra_results)
    print(f"✅ Found {len(capterra_results)} vendors on Capterra")

    # Search Google
    for search_query in search_queries:
        print(f"\n🔍 Using search query: {search_query}")
        progress = get_prompt_progress(search_query)
        start_page = progress["last_page"]
        end_page = min(start_page + pages_per_run, 10)  # Stop at page 10 max

        for page in range(start_page, end_page):
            start = page * 10
            params = {
                "q": search_query,
                "start": start,
                "num": 10,
                "api_key": SERPAPI_KEY,
                "engine": "google",
                "hl": "en",
                "gl": "us",
                "as_sitesearch": "",
                "as_occt": "any",
                "as_dt": "i",
                "as_rights": "cc_publicdomain|cc_attribute|cc_sharealike"
            }

            try:
                search = GoogleSearch(params)
                results = search.get_dict()

                if "error" in results:
                    print(f"❌ SerpAPI Error: {results['error']}")
                    break

                organic = results.get("organic_results", [])
                print(f"\n📄 Scraped page {page + 1} ({len(organic)} results)")

                for result in organic:
                    link = result.get("link")
                    if link and is_valid_vendor_url(link):
                        all_links.append({
                            "url": link,
                            "source_page": page + 1,
                            "prompt": search_query,
                            "industry": industry,
                            "title": result.get("title", ""),
                            "snippet": result.get("snippet", ""),
                            "source": "google"
                        })

            except Exception as e:
                print(f"⚠️ Exception fetching page {page + 1}: {e}")

    print(f"\n🔗 Total unique links collected: {len(all_links)}\n")
    return all_links
