import os
import requests
from urllib.parse import quote
from datetime import datetime
from zoneinfo import ZoneInfo


# ============================================================
# SETTINGS
# ============================================================

SKU = "MJX74AH/A"

PRODUCT_NAME = "iPhone 18 Pro Max 256GB Burgundy"

# Pickup will be searched from these locations.
# Combined results cover the UAE Apple Stores.
PICKUP_LOCATIONS = [
    "Dubai",
    "Abu Dhabi",
    "Al Ain",
]

# Delivery location
DELIVERY_CITY = "Dubai"

# We want the delivery window to END on or before this date.
TARGET_DELIVERY_DATE = datetime(2026, 9, 29)

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

available_stores = []
seen_stores = set()

print("\n==============================")
print("CHECKING UAE PICKUP")
print("==============================")


for location in PICKUP_LOCATIONS:

    pickup_url = (
        "https://www.apple.com/ae/shop/retail/pickup-message"
        "?pl=true"
        "&mts.0=regular"
        f"&parts.0={quote(SKU, safe='')}"
        f"&location={quote(location)}"
    )

    try:
        response = requests.get(
            pickup_url,
            headers=HEADERS,
            timeout=20,
        )

        print(f"\nLOCATION: {location}")
        print("STATUS:", response.status_code)

        if response.status_code != 200:
            print("Pickup request failed.")
            print(response.text[:300])
            continue

        try:
            data = response.json()
        except Exception:
            print("Apple returned non-JSON pickup response.")
            print(response.text[:500])
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

            if store_number in seen_stores:
                continue

            seen_stores.add(store_number)

            part = (
                store
                .get("partsAvailability", {})
                .get(SKU, {})
            )

            pickup_status = str(
                part.get("pickupDisplay", "")
            ).lower()

            print(
                f"{store_name} -> {pickup_status}"
            )

            if pickup_status == "available":
                available_stores.append(store_name)

    except Exception as e:
        print(
            f"ERROR checking pickup for {location}:",
            str(e)
        )


print("\nPICKUP AVAILABLE:", available_stores)


# ============================================================
# DELIVERY CHECK
# ============================================================

print("\n==============================")
print("CHECKING DELIVERY")
print("==============================")


delivery_text = "Unknown"
delivery_upper_date = None
delivery_ok = False


delivery_url = (
    "https://www.apple.com/ae/shop/fulfillment-messages"
    "?fae=true"
    "&geoLocated=false"
    f"&city={quote(DELIVERY_CITY)}"
    f"&parts.0={quote(SKU, safe='')}"
    "&mts.0=expanded"
)


try:
    delivery_response = requests.get(
        delivery_url,
        headers=HEADERS,
        timeout=20,
    )

    print("DELIVERY HTTP STATUS:", delivery_response.status_code)

    if delivery_response.status_code == 200:

        try:
            delivery_data = delivery_response.json()

            expanded = (
                delivery_data
                .get("body", {})
                .get("content", {})
                .get("deliveryMessage", {})
                .get(SKU, {})
                .get("expanded", {})
            )

            delivery_options = expanded.get(
                "deliveryOptionMessages",
                []
            )

            if delivery_options:

                option = delivery_options[0]

                delivery_text = option.get(
                    "displayName",
                    "Unknown"
                )

                encoded_upper = option.get(
                    "encodedUpperDateString"
                )

                if encoded_upper:

                    try:
                        delivery_upper_date = datetime.strptime(
                            encoded_upper,
                            "%Y%m%d"
                        )

                        # We use the END of Apple's delivery window.
                        # That way the phone is guaranteed by our
                        # target date, not merely possibly arriving earlier.
                        delivery_ok = (
                            delivery_upper_date
                            <= TARGET_DELIVERY_DATE
                        )

                    except Exception as e:
                        print(
                            "Could not parse delivery date:",
                            e
                        )

        except Exception:
            print(
                "Apple returned non-JSON delivery response."
            )
            print(delivery_response.text[:500])

    else:
        print(
            "Delivery endpoint unavailable. "
            "Pickup check will continue normally."
        )
        print(delivery_response.text[:300])

except Exception as e:
    print(
        "DELIVERY CHECK ERROR:",
        str(e)
    )


print("DELIVERY WINDOW:", delivery_text)

if delivery_upper_date:
    print(
        "DELIVERY UPPER DATE:",
        delivery_upper_date.strftime("%d %b %Y")
    )

print(
    "DELIVERY BY 29 SEP:",
    delivery_ok
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
# DECIDE WHETHER THIS IS AN URGENT ALERT
# ============================================================

pickup_ok = len(available_stores) > 0

urgent = pickup_ok or delivery_ok


# ============================================================
# BUILD MESSAGE
# ============================================================

if urgent:

    message = (
        "🚨🚨 IPHONE OPTION AVAILABLE 🚨🚨\n\n"
        f"{PRODUCT_NAME}\n"
        f"SKU: {SKU}\n\n"
    )

    if pickup_ok:

        message += (
            "🏬 PICKUP AVAILABLE:\n"
            + "\n".join(
                f"✅ {store}"
                for store in available_stores
            )
            + "\n\n"
        )

    else:

        message += (
            "🏬 Pickup: ❌ Still unavailable\n\n"
        )


    if delivery_ok:

        message += (
            "🚚 DELIVERY AVAILABLE:\n"
            f"✅ {delivery_text}\n"
            "✅ Guaranteed delivery window ends "
            "on/before 29 September\n\n"
        )

    else:

        message += (
            f"🚚 Delivery: {delivery_text}\n"
            "❌ Not before 29 September\n\n"
        )


    message += (
        f"Checked: {current_time}"
    )

    # Urgent alerts ALWAYS send.
    should_send = True


else:

    message = (
        "❌ iPhone still unavailable\n\n"
        f"{PRODUCT_NAME}\n"
        f"SKU: {SKU}\n\n"
        f"🏬 Pickup: unavailable at "
        f"{len(seen_stores)} UAE Apple Stores\n\n"
        f"🚚 Delivery to {DELIVERY_CITY}:\n"
        f"{delivery_text}\n\n"
        "Target: on/before 29 September\n\n"
        f"Checked: {current_time}"
    )

    # Unavailable status only around :00 and :30.
    #
    # Example if cron runs every 5 minutes:
    # 8:02 -> send
    # 8:07 -> skip
    # 8:12 -> skip
    # 8:32 -> send
    # 8:37 -> skip
    #
    should_send = (
        0 <= dubai_now.minute < 5
        or
        30 <= dubai_now.minute < 35
    )


print("\n==============================")
print("NOTIFICATION DECISION")
print("==============================")

print("CURRENT UAE TIME:", current_time)
print("PICKUP OK:", pickup_ok)
print("DELIVERY OK:", delivery_ok)
print("URGENT:", urgent)
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

                # Available = normal notification.
                # Unavailable 30-minute status = silent.
                "disable_notification": not urgent,
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
        "Skipping Telegram message this run."
    )
