import os
import requests
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# PRODUCTS TO MONITOR
# ============================================================

PRODUCTS = {
    "iPhone 18 Pro Max 256GB Burgundy": "MJX74AH/A",
    "iPhone 18 Pro Max 256GB Glacier": "MJX84AH/A",
    "iPhone 18 Pro Max 256GB Black": "MJX54AH/A",
    

    # TEST PRODUCT
    # Uncomment this line when you want to test notifications:
    "TEST iPad": "MH5T4AB/A",
}


# ============================================================
# SETTINGS
# ============================================================

PICKUP_LOCATION = "Dubai"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

CHAT_IDS = [
    os.environ["TELEGRAM_CHAT_ID"],
    os.environ["BROTHER_TELEGRAM_CHAT_ID"],
]

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
# CHECK STOCK
# ============================================================

availability = {}

all_seen_stores = set()

print("\n==============================")
print("CHECKING APPLE UAE STOCK")
print("==============================")


for product_name, sku in PRODUCTS.items():

    print("\n------------------------------")
    print(product_name)
    print("SKU:", sku)
    print("------------------------------")

    pickup_url = (
        "https://www.apple.com/ae/shop/retail/pickup-message"
        "?pl=true"
        "&mts.0=regular"
        f"&parts.0={quote(sku, safe='')}"
        f"&location={quote(PICKUP_LOCATION)}"
    )

    available_stores = []

    try:

        response = requests.get(
            pickup_url,
            headers=HEADERS,
            timeout=20,
        )

        print("STATUS:", response.status_code)
        print(
            "CONTENT TYPE:",
            response.headers.get("content-type")
        )

        if response.status_code != 200:

            print("Apple request failed.")
            print(response.text[:300])

            availability[product_name] = []

            continue


        try:

            data = response.json()

        except Exception:

            print("Apple returned non-JSON.")
            print(response.text[:500])

            availability[product_name] = []

            continue


        stores = (
            data
            .get("body", {})
            .get("stores", [])
        )

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

                available_stores.append(
                    store_name
                )


    except Exception as e:

        print(
            f"ERROR checking {product_name}:",
            str(e)
        )


    availability[product_name] = available_stores


# ============================================================
# PRINT SUMMARY
# ============================================================

print("\n==============================")
print("AVAILABILITY SUMMARY")
print("==============================")


for product_name, stores in availability.items():

    print(
        f"{product_name}:",
        stores
    )


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
# CHECK IF ANYTHING IS AVAILABLE
# ============================================================

any_available = any(
    len(stores) > 0
    for stores in availability.values()
)


# ============================================================
# BUILD TELEGRAM MESSAGE
# ============================================================

if any_available:

    message = (
        "🚨🚨 APPLE STOCK AVAILABLE 🚨🚨\n\n"
    )


    for product_name, stores in availability.items():

        if stores:

            message += (
                f"✅ {product_name}\n"
            )

            for store in stores:

                message += (
                    f"   🏬 {store}\n"
                )

            message += "\n"

        else:

            message += (
                f"❌ {product_name}\n"
                "   Unavailable\n\n"
            )


    message += (
        f"Checked: {current_time}"
    )


    # Always send immediately if anything is available
    should_send = True


else:

    message = (
        "❌ Apple stock still unavailable\n\n"
    )


    for product_name in PRODUCTS:

        message += (
            f"❌ {product_name}\n"
        )


    message += (
        f"\nChecked {len(all_seen_stores)} "
        "UAE Apple Stores.\n\n"
        f"Checked: {current_time}"
    )


    # Send unavailable status only around
    # :00 and :30 UAE time
    should_send = (
        0 <= dubai_now.minute < 2

    )


# ============================================================
# DEBUG
# ============================================================

print("\n==============================")
print("NOTIFICATION DECISION")
print("==============================")


print("CURRENT UAE TIME:", current_time)

print(
    "ANY AVAILABLE:",
    any_available
)

print(
    "SHOULD SEND:",
    should_send
)


# ============================================================
# SEND TO BOTH TELEGRAM USERS
# ============================================================

if should_send:

    telegram_url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )


    for chat_id in CHAT_IDS:

        try:

            telegram_response = requests.post(
                telegram_url,
                json={
                    "chat_id": chat_id,
                    "text": message,

                    # Available = normal push
                    # Unavailable = silent
                    "disable_notification":
                        not any_available,
                },
                timeout=20,
            )


            print(
                f"TELEGRAM STATUS "
                f"for {chat_id}:",
                telegram_response.status_code
            )


            print(
                "TELEGRAM RESPONSE:",
                telegram_response.text
            )


        except Exception as e:

            print(
                f"TELEGRAM ERROR "
                f"for {chat_id}:",
                str(e)
            )


else:

    print(
        "Skipping unavailable "
        "message this run"
    )
