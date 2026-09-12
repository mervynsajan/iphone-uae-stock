import os
import requests

SKU = "MH5T4AB/A"  # test iPad SKU

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
        "https://www.apple.com/ae/shop/fulfillment-messages"
        f"?fae=true&pl=true&mts.0=regular&mts.1=compact"
        f"&parts.0={SKU}"
        f"&location={location}"
    )

    r = requests.get(url, headers=headers, timeout=20)

    print("LOCATION:", location)
    print("STATUS:", r.status_code)
    print("CONTENT TYPE:", r.headers.get("content-type"))

    if r.status_code != 200:
        continue

    try:
        data = r.json()
    except Exception:
        print("Apple returned non-JSON")
        print(r.text[:500])
        continue

    stores = (
        data.get("body", {})
            .get("content", {})
            .get("pickupMessage", {})
            .get("stores", [])
    )

    for store in stores:
        name = store.get("storeName", "Unknown Apple Store")

        if name in seen:
            continue

        seen.add(name)

        part = store.get("partsAvailability", {}).get(SKU, {})

        status = (
            part.get("pickupDisplay")
            or part.get("pickupSearchQuote")
            or ""
        )

        if "available" in str(status).lower() and "unavailable" not in str(status).lower():
            available.append(f"{name} — {status}")

print("AVAILABLE:", available)

if available:
    message = (
        "🚨 APPLE UAE PICKUP AVAILABLE\n\n"
        "TEST: iPad Air\n"
        f"SKU: {SKU}\n\n"
        + "\n".join(f"✅ {x}" for x in available)
    )

    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        telegram_url,
        json={
            "chat_id": CHAT_ID,
            "text": message,
        },
        timeout=20,
    )
