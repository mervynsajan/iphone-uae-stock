import os
import requests
from urllib.parse import quote

SKU = "MJX74AH/A"  # test iPhone

NTFY_TOPIC = "mervyn_iphone_stock" # ntfy name

LOCATIONS = [
    "Dubai",
    "Abu Dhabi",
    "Al Ain",
]

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.apple.com/ae/",
}

available = []
seen = set()

for location in LOCATIONS:
    url = (
        "https://www.apple.com/ae/shop/retail/pickup-message"
        "?pl=true"
        "&mts.0=regular"
        f"&parts.0={quote(SKU, safe='')}"
        f"&location={quote(location)}"
    )

    r = requests.get(url, headers=headers, timeout=20)

    print("LOCATION:", location)
    print("STATUS:", r.status_code)
    print("CONTENT TYPE:", r.headers.get("content-type"))

    if r.status_code != 200:
        print(r.text[:300])
        continue

    try:
        data = r.json()
    except Exception:
        print("Apple returned non-JSON")
        print(r.text[:500])
        continue

    stores = data.get("body", {}).get("stores", [])

    print("STORES FOUND:", len(stores))

    for store in stores:
        name = store.get("storeName", "Unknown Apple Store")
        store_number = store.get("storeNumber", name)

        if store_number in seen:
            continue

        seen.add(store_number)

        part = store.get("partsAvailability", {}).get(SKU, {})
        status = str(part.get("pickupDisplay", "")).lower()

        print(name, "->", status)

        if status == "available":
            available.append(name)

print("AVAILABLE:", available)

if available:
    message = (
        "🚨🚨 IPHONE AVAILABLE NOW 🚨🚨\n\n"
        "iPhone 18 Pro Max 256GB Burgundy\n\n"
        + "\n".join(f"✅ {store}" for store in available)
    )
else:
    message = (
        "❌ Still unavailable\n\n"
        "iPhone 18 Pro Max 256GB Burgundy\n"
        "Checked all 5 UAE Apple Stores."
    )

telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

resp = requests.post(
    telegram_url,
    json={
        "chat_id": CHAT_ID,
        "text": message,
        "disable_notification": False if available else True,
    },
    timeout=20,
)

print("TELEGRAM STATUS:", resp.status_code)

ntfy_url = f"https://ntfy.sh/{NTFY_TOPIC}"

ntfy_resp = requests.post(
    ntfy_url,
    data=message.encode("utf-8"),
    headers={
        "Title": "Apple UAE Stock",
        "Priority": "high" if available else "default",
        "Tags": "iphone,rotating_light" if available else "iphone",
    },
    timeout=20,
)

print("NTFY STATUS:", ntfy_resp.status_code)

