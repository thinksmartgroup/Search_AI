import json
import os
from datetime import datetime

LOG_DIR = "vendor_logs"
os.makedirs(LOG_DIR, exist_ok=True)

def save_vendor_log(vendors, industry, prompt_used):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_industry = industry.lower().replace(" ", "_")
    filename = f"{LOG_DIR}/{safe_industry}_{timestamp}.json"

    log_data = {
        "industry": industry,
        "timestamp": timestamp,
        "prompt_used": prompt_used,
        "vendors": vendors
    }

    with open(filename, "w") as f:
        json.dump(log_data, f, indent=2)

    print(f"📝 Logged {len(vendors)} vendors to {filename}")
