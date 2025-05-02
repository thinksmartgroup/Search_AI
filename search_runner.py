import os
import json
from serpapi import GoogleSearch
from dotenv import load_dotenv
from prompt_tracker import get_prompt_progress, update_prompt_progress, is_prompt_completed

load_dotenv()
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

def fetch_links_from_serpapi(prompt: str, industry: str, pages_per_run: int = 3) -> list:
    if not SERPAPI_KEY:
        print("❌ Missing SERPAPI_API_KEY in .env")
        return []

    if is_prompt_completed(prompt):
        print(f"✅ Prompt completed: '{prompt}'")
        return []

    progress = get_prompt_progress(prompt)
    start_page = progress["last_page"]
    end_page = min(start_page + pages_per_run, 10)  # Stop at page 10 max

    all_links = []

    for page in range(start_page, end_page):
        start = page * 10
        params = {
            "q": prompt,
            "start": start,
            "num": 10,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "hl": "en",
            "gl": "us"
        }

        try:
            search = GoogleSearch(params)
            results = search.get_dict()

            # 🔍 Debug full organic results from SerpAPI
            organic = results.get("organic_results", [])
            print(f"\n📄 Scraped page {page + 1} ({len(organic)} results)")

            if "error" in results:
                print(f"❌ SerpAPI Error: {results['error']}")
                break  # Stop this prompt to avoid wasting quota

            for result in organic:
                link = result.get("link")
                if link:
                    all_links.append({
                        "url": link,
                        "source_page": page + 1,
                        "prompt": prompt,
                        "industry": industry
                    })

        except Exception as e:
            print(f"⚠️ Exception fetching page {page + 1}: {e}")

    print(f"\n🔗 Total unique links collected: {len(all_links)}\n")
    return all_links
