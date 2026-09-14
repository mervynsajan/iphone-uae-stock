import os
import requests
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo

SKU = "MJX74AH/A" #iphone sku
#SKU = "MH5T4AB/A" #ipad sku


PRODUCT_NAME = "iPhone 18 Pro Max 256GB Burgundy"

LOCATIONS = [
    "Dubai",
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

    try:
        r = requests.get(
            url,
            headers=headers,
            timeout=20
        )

        print("LOCATION:", location)
        print("STATUS:", r.status_code)
        print("CONTENT TYPE:", r.headers.get("content-type"))

        if r.status_code != 200:
            print("Apple request failed")
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
            name = store.get(
                "storeName",
                "Unknown Apple Store"
            )

            store_number = store.get(
                "storeNumber",
                name
            )

            if store_number in seen:
                continue

            seen.add(store_number)

            part = (
                store
                .get("partsAvailability", {})
                .get(SKU, {})
            )

            status = str(
                part.get("pickupDisplay", "")
            ).lower()

            print(name, "->", status)

            if status == "available":
                available.append(name)

    except Exception as e:
        print(
            f"ERROR checking {location}:",
            str(e)
        )


print("AVAILABLE:", available)

dubai_now = datetime.now(
    ZoneInfo("Asia/Dubai")
)

current_time = dubai_now.strftime(
    "%d %b %Y %I:%M %p"
)

if available:
    message = (
        "🚨🚨 IPHONE AVAILABLE NOW 🚨🚨\n\n"
        f"{PRODUCT_NAME}\n"
        f"SKU: {SKU}\n\n"
        + "\n".join(
            f"✅ {store}"
            for store in available
        )
        + f"\n\nChecked: {current_time}"
    )

    should_send = True

else:
    message = (
        "❌ iPhone still unavailable\n\n"
        f"{PRODUCT_NAME}\n"
        f"SKU: {SKU}\n\n"
        f"Checked {len(seen)} UAE Apple Stores.\n\n"
        f"Checked: {current_time}"
    )

    # Only send unavailable status twice per hour:
    # around :00 and :30
    should_send = (
        dubai_now.minute < 5
        or
        30 <= dubai_now.minute < 35
    )


if should_send:
    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    try:
        resp = requests.post(
            telegram_url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "disable_notification": False,
            },
            timeout=20,
        )

        print(
            "TELEGRAM STATUS:",
            resp.status_code
        )

        print(
            "TELEGRAM RESPONSE:",
            resp.text
        )

    except Exception as e:
        print(
            "TELEGRAM ERROR:",
            str(e)
        )

else:
    print(
        "Skipping unavailable message "
        "this run"
    )
