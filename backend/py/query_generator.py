import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-pro-preview-03-25")

# 🔍 Extract structured parameters from a freeform user intent
def generate_search_queries(prompt: str) -> dict:
    system_prompt = (
        "You are a backend JSON extractor for a vendor search system.\n"
        "Extract:\n"
        "- domain: type of vendors or businesses\n"
        "- location: city/state/country\n"
        "- quantity: number of vendors requested (default 3)\n"
        "Return ONLY a JSON object:\n"
        "{ \"domain\": \"...\", \"location\": \"...\", \"quantity\": 3 }"
    )

    try:
        response = model.generate_content([system_prompt, prompt])
        print("🧠 Gemini output:", response.text)
        json_data = json.loads(response.text.strip())

        return {
            "domain": json_data.get("domain", "software vendors"),
            "location": json_data.get("location", "California"),
            "quantity": int(json_data.get("quantity", 3))
        }

    except Exception as e:
        print("⚠️ Failed to parse Gemini output:", e)
        return {
            "domain": "software vendors",
            "location": "California",
            "quantity": 3
        }

def generate_next_prompt_variation(intent_prompt: str, used_prompts: list[str]) -> str:
    try:
        system_prompt = (
            "You are an intelligent assistant that generates creative Google search queries "
            "to help find software vendors for a specific business need.\n\n"
            f"Original intent:\n\"{intent_prompt}\"\n\n"
            f"Already used prompts:\n{used_prompts}\n\n"
            "Your task is to generate **one new and distinct** Google search prompt that still aligns with the original intent "
            "but explores a different angle (e.g., billing, cloud-based, practice management, portals, etc).\n"
            "Return a clean, single-line search prompt without bullets or formatting."
        )

        response = model.generate_content(system_prompt)
        prompt = response.text.strip()
        prompt = prompt.strip("-•1234567890. ").strip()

        print("🧠 New prompt from Gemini:", prompt)
        return prompt

    except Exception as e:
        print("❌ Error generating prompt variation:", e)
        return ""
