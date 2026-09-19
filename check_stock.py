import os
import requests
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# SETTINGS
# ============================================================

PRODUCTS = {
    "Burgundy": "MJX74AH/A",
    "Glacier": "MJX84AH/A",
    "iPad Test": "MH5T4AB/A",
}

PRODUCT_NAME = "iPhone 18 Pro Max 256GB"

# One Dubai query already returns all 5 UAE Apple Stores
PICKUP_LOCATION = "Dubai"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": "https://www.apple.com/ae/",
}


# ============================================================
# PICKUP CHECK
# ============================================================

availability_by_color = {}
all_seen_stores = set()

print("\n==============================")
print("CHECKING UAE PICKUP")
print("==============================")


for color, sku in PRODUCTS.items():

    print(f"\n--- {color} ---")

    pickup_url = (
        "https://www.apple.com/ae/shop/retail/pickup-message"
        "?pl=true"
        "&mts.0=regular"
        f"&parts.0={quote(sku, safe='')}"
        f"&location={quote(PICKUP_LOCATION)}"
    )

    color_available_stores = []

    try:
        response = requests.get(
            pickup_url,
            headers=HEADERS,
            timeout=20,
        )

        print("STATUS:", response.status_code)
        print("CONTENT TYPE:", response.headers.get("content-type"))

        if response.status_code != 200:
            print(f"{color} request failed.")
            print(response.text[:300])
            availability_by_color[color] = []
            continue

        try:
            data = response.json()
        except Exception:
            print(f"Apple returned non-JSON for {color}.")
            print(response.text[:500])
            availability_by_color[color] = []
            continue

        stores = data.get("body", {}).get("stores", [])

        print("STORES FOUND:", len(stores))

        for store in stores:
            store_name = store.get(
                "storeName",
                "Unknown Apple Store"
            )

            store_number = store.get(
                "storeNumber",
                store_name
            )

            all_seen_stores.add(store_number)

            part = (
                store
                .get("partsAvailability", {})
                .get(sku, {})
            )

            pickup_status = str(
                part.get("pickupDisplay", "")
            ).lower()

            print(
                f"{store_name} -> {pickup_status}"
            )

            if pickup_status == "available":
                color_available_stores.append(store_name)

    except Exception as e:
        print(
            f"ERROR checking {color}:",
            str(e)
        )

    availability_by_color[color] = color_available_stores


# ============================================================
# SUMMARY
# ============================================================

print("\n==============================")
print("AVAILABILITY SUMMARY")
print("==============================")

for color, stores in availability_by_color.items():
    print(f"{color}: {stores}")


# ============================================================
# CURRENT UAE TIME
# ============================================================

dubai_now = datetime.now(
    ZoneInfo("Asia/Dubai")
)

current_time = dubai_now.strftime(
    "%d %b %Y %I:%M %p"
)


# ============================================================
# CHECK IF ANY COLOR IS AVAILABLE
# ============================================================

any_available = any(
    len(stores) > 0
    for stores in availability_by_color.values()
)


# ============================================================
# BUILD TELEGRAM MESSAGE
# ============================================================

if any_available:

    message = (
        "🚨🚨 IPHONE AVAILABLE NOW 🚨🚨\n\n"
        f"{PRODUCT_NAME}\n\n"
    )

    for color, stores in availability_by_color.items():

        if stores:
            message += (
                f"✅ {color}\n"
                + "\n".join(
                    f"   🏬 {store}"
                    for store in stores
                )
                + "\n\n"
            )
        else:
            message += (
                f"❌ {color}: unavailable\n\n"
            )

    message += (
        f"Checked: {current_time}"
    )

    # If ANY color is available, send immediately
    should_send = True

else:

    message = (
        "❌ iPhone still unavailable\n\n"
        f"{PRODUCT_NAME}\n\n"
        "Burgundy: ❌ Unavailable\n"
        "Glacier: ❌ Unavailable\n\n"
        f"Checked {len(all_seen_stores)} UAE Apple Stores.\n\n"
        f"Checked: {current_time}"
    )

    # Only send unavailable status around :00 and :30
    should_send = (
        0 <= dubai_now.minute < 2
       # or
       # 30 <= dubai_now.minute < 33
    )


# ============================================================
# DEBUG OUTPUT
# ============================================================

print("\n==============================")
print("NOTIFICATION DECISION")
print("==============================")

print("CURRENT UAE TIME:", current_time)
print("ANY AVAILABLE:", any_available)
print("SHOULD SEND:", should_send)


# ============================================================
# SEND TELEGRAM MESSAGE
# ============================================================

if should_send:

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    try:
        telegram_response = requests.post(
            telegram_url,
            json={
                "chat_id": CHAT_ID,
                "text": message,

                # Available alert = normal notification
                # Unavailable status = silent
                "disable_notification": not any_available,
            },
            timeout=20,
        )

        print(
            "TELEGRAM STATUS:",
            telegram_response.status_code
        )

        print(
            "TELEGRAM RESPONSE:",
            telegram_response.text
        )

    except Exception as e:
        print(
            "TELEGRAM ERROR:",
            str(e)
        )

else:
    print(
        "Skipping unavailable message this run"
    )
