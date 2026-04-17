import json
import os
import sys

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "bnb_url": "https://www.airbnb.ca/",
    "ntfy_sh_url": "https://ntfy.sh/",
    "output_file": "results",
    "database_file": "bnb_monitor.db",
    "currency": "CAD",
    "language": "en",
    "search_parameters": {
        "search_box": None,
        "checkin": None,
        "checkout": None,
        "adult_count": None,
        "price_min": 0,
        "price_max": None
    },
    "notifications": {
        "target_price": None,
        "ntfy_sh_topic_id": None
    }
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        print(f"Created {CONFIG_FILE}. Please configure search parameters and restart.")
        sys.exit(0)

    with open(CONFIG_FILE, "r") as f:
        config = json.load(f)

    params = config.get("search_parameters", {})
    required = ["search_box", "checkin", "checkout", "adult_count", "price_max"]
    missing = [field for field in required if params.get(field) is None]

    if missing:
        print(f"Error: Missing or empty search parameters in {CONFIG_FILE}: {', '.join(missing)}")
        sys.exit(1)

    return config
