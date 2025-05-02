import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

INDUSTRIES = ["chiropractic", "optometry", "auto_repair"]
HEADERS = ["website", "email", "phone", "summary", "industry", "prompt", "source_page", "platform_type", "platform_score"]
SHARE_WITH_EMAIL = "indraneel@thinksmartinc.com"

def deploy_vendor_sheets():
    scope = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(creds)

    sheet_links = {}

    for industry in INDUSTRIES:
        try:
            sheet_name = f"{industry.title()} Vendor Database"
            sheet = client.create(sheet_name)

            # Add headers
            worksheet = sheet.get_worksheet(0)
            worksheet.update_title("Vendors")
            worksheet.insert_row(HEADERS, 1)

            # Share with user
            sheet.share(SHARE_WITH_EMAIL, perm_type="user", role="writer")

            # Get shareable URL
            url = os.getenv("DEFAULT_SHEET_URL")
            sheet_links[industry] = url

            print(f"✅ Created & shared sheet for {industry}: {url}")
        except Exception as e:
            print(f"❌ Failed for {industry}: {e}")

    print("\n📋 Add these to your .env:\n")
    for industry, url in sheet_links.items():
        env_var = f"{industry.upper().replace('-', '_')}_SHEET_URL"
        print(f"{env_var}={url}")

if __name__ == "__main__":
    deploy_vendor_sheets()
