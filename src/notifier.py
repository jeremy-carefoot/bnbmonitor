import requests
from src.database import is_already_notified, mark_as_notified

def check_and_notify(config, results):
    """
    Checks results against target price and sends a notification via ntfy.sh if matches are found.
    Does not notify if the user has already been notified for a listing with the same checkin/checkout dates.
    """
    notifications_cfg = config.get("notifications", {})
    target_price = notifications_cfg.get("target_price")
    topic_id = notifications_cfg.get("ntfy_sh_topic_id")

    if target_price is None or not topic_id:
        return

    params = config.get("search_parameters", {})
    checkin = params.get("checkin")
    checkout = params.get("checkout")

    matches = []
    notified_room_ids = []
    bnb_url = config.get("bnb_url")
    ntfy_url = config.get("ntfy_sh_url")
    
    for item in results:
        try:
            total_price = item["price"]["break_down"][-1]["amount"]
            if total_price <= target_price:
                room_id = item.get("room_id")
                if not room_id:
                    continue
                
                # Check if already notified for this listing and dates
                if is_already_notified(config, room_id, checkin, checkout):
                    continue

                name = item.get("name", "Unknown Listing")
                url = f"{bnb_url}rooms/{room_id}"
                matches.append(f"{name}: ${total_price:.2f} - {url}")
                notified_room_ids.append(room_id)
        except (KeyError, IndexError, TypeError):
            continue

    if matches:
        message = "\n".join(matches)
        title = f"Airbnb Monitor: {len(matches)} new listings found under ${target_price}!"
        
        try:
            response = requests.post(
                f"{ntfy_url}/{topic_id}",
                data=message.encode('utf-8'),
                headers={
                    "Title": title,
                    "Priority": "high",
                    "Tags": "house,moneybag"
                }
            )
            if response.status_code == 200:
                print(f"Notification sent to ntfy.sh topic: {topic_id}")
                # Mark as notified in the DB
                for rid in notified_room_ids:
                    mark_as_notified(config, rid, checkin, checkout)
            else:
                print(f"Failed to send notification. Status code: {response.status_code}")
        except Exception as e:
            print(f"Error sending notification: {e}")
