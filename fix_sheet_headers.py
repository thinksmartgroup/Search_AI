import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import json
import concurrent.futures

# Load environment variables
load_dotenv()

SHEET_URLS = {
    "chiropractic": os.getenv("CHIRO_SHEET_URL"),
    "optometry": os.getenv("OPTOMETRY_SHEET_URL"),
    "auto_repair": os.getenv("AUTO_REPAIR_SHEET_URL")
}
CREDENTIALS_FILE = "credentials.json"
SCOPES = [os.getenv("SCOPE_FEEDS"), os.getenv("SCOPE_DRIVE")]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_sheet_by_industry(industry):
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_url(SHEET_URLS[industry]).sheet1


def gemini_suggest_header(sample_data, col_idx):
    prompt = f"""
You are an expert data wrangler. Here is a sample of data from a spreadsheet column:
{json.dumps(sample_data, indent=2)}
Suggest a clear, context-appropriate column header for this data. Return only the new column name as a string.
"""
    try:
        model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")
        response = model.generate_content(prompt)
        suggestion = response.text.strip().splitlines()[0].strip('"')
        return suggestion if suggestion else f"Column{col_idx+1}"
    except Exception as e:
        print(f"Gemini error: {e}")
        return f"Column{col_idx+1}"


def gemini_suggest_header_with_timeout_and_retries(sample_data, col_idx, timeout=5, retries=3):
    for attempt in range(1, retries+1):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(gemini_suggest_header, sample_data, col_idx)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                print(f"[Attempt {attempt}] Gemini timed out for column {col_idx+1} (timeout {timeout}s). Retrying...")
            except Exception as e:
                print(f"[Attempt {attempt}] Gemini error for column {col_idx+1}: {e}. Retrying...")
    print(f"Gemini failed for column {col_idx+1} after {retries} attempts. Using fallback name.")
    return f"Column{col_idx+1}"


def main():
    print("Select industry to suggest headers:")
    for i, ind in enumerate(SHEET_URLS.keys(), 1):
        print(f"{i}. {ind}")
    idx = input("Enter number: ").strip()
    try:
        industry = list(SHEET_URLS.keys())[int(idx)-1]
    except Exception:
        print("Invalid selection.")
        return
    sheet = get_sheet_by_industry(industry)
    genai.configure(api_key=GEMINI_API_KEY)
    # Assume first row is data, not headers
    data = sheet.get_all_values()
    if not data:
        print("Sheet is empty.")
        return
    num_cols = len(data[0])
    sample_rows = min(3, len(data))
    suggestions = []
    for col in range(num_cols):
        sample_data = [data[row][col] for row in range(sample_rows) if col < len(data[row])]
        print(f"Suggesting header for column {col+1}...")
        suggestions.append(gemini_suggest_header_with_timeout_and_retries(sample_data, col))
    while True:
        print("\nGemini's suggested headers:")
        for i, s in enumerate(suggestions, 1):
            print(f"{i}. {s}")
        approve = input("\nApprove these headers? (y/n): ").strip().lower()
        if approve == 'y':
            sheet.insert_row(suggestions, 1)
            print("Headers inserted.")
            break
        else:
            print("Options:")
            print("1. Regenerate a specific column header")
            print("2. Regenerate all headers")
            print("3. Manually enter a header for a column")
            print("4. Cancel")
            choice = input("Choose an option (1-4): ").strip()
            if choice == '1':
                col_num = int(input("Enter column number to regenerate: ").strip()) - 1
                sample_data = [data[row][col_num] for row in range(sample_rows) if col_num < len(data[row])]
                print(f"Regenerating header for column {col_num+1}...")
                suggestions[col_num] = gemini_suggest_header_with_timeout_and_retries(sample_data, col_num)
            elif choice == '2':
                for col in range(num_cols):
                    sample_data = [data[row][col] for row in range(sample_rows) if col < len(data[row])]
                    print(f"Regenerating header for column {col+1}...")
                    suggestions[col] = gemini_suggest_header_with_timeout_and_retries(sample_data, col)
            elif choice == '3':
                col_num = int(input("Enter column number to name: ").strip()) - 1
                manual = input("Enter your header: ").strip()
                suggestions[col_num] = manual
            elif choice == '4':
                print("Cancelled.")
                return

if __name__ == "__main__":
    main() 