from query_generator import generate_next_prompt_variation
from search_runner import fetch_links_from_serpapi
from summarizer import summarize_and_extract_contact
from sheet_writer import update_google_sheet
from prompt_tracker import (
    get_used_prompts_for_intent,
    add_used_prompt,
    is_prompt_completed,
    update_prompt_progress
)
from logger import save_vendor_log  # ✅ Add this

MAX_PROMPTS_PER_INTENT = 3

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

                    # Fallback values
                    if not vendor.get("platform_type"):
                        vendor["platform_type"] = "Unknown"
                        vendor["platform_score"] = 0
                    elif "platform_score" not in vendor:
                        vendor["platform_score"] = 1

                    parsed_vendors.append(vendor)

            # ✅ Save all vendors to JSON (even if some are duplicates)
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
    user_intent = input("🧠 What do you want to search for? (e.g., 'Find software vendors for chiropractors in California')\n> ")
    industry = input("🏷️  Enter target industry (chiropractic / optometry / auto_repair):\n> ").strip().lower()
    run_pipeline(user_intent, industry)
