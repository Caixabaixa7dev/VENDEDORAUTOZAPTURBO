import os
import aiohttp
from typing import Optional

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
API_VERSION = "v18.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}/{PHONE_NUMBER_ID}"


async def send_text(to: str, text: str) -> dict:
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return {"error": "WhatsApp API not configured"}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    return await _post(payload)


async def send_image(to: str, image_url: str, caption: Optional[str] = None) -> dict:
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        return {"error": "WhatsApp API not configured"}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "image",
        "image": {"link": image_url, "caption": caption or ""},
    }

    return await _post(payload)


async def _post(payload: dict) -> dict:
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f"{BASE_URL}/messages", json=payload, headers=headers, timeout=15) as resp:
                data = await resp.json()
                return data
        except Exception as e:
            return {"error": str(e)}


def verify_webhook(query) -> Optional[str]:
    mode = query.get("hub.mode")
    token = query.get("hub.verify_token")
    challenge = query.get("hub.challenge")

    expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "zapturbo123")

    if mode == "subscribe" and token == expected_token:
        return challenge
    return None


def extract_message(body: dict) -> Optional[dict]:
    try:
        entry = body.get("entry", [])[0]
        change = entry.get("changes", [])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return None

        msg = messages[0]
        phone = msg.get("from", "")
        msg_type = msg.get("type", "")

        text = ""
        if msg_type == "text":
            text = msg.get("text", {}).get("body", "")
        elif msg_type == "interactive":
            text = msg.get("interactive", {}).get("button_reply", {}).get("title", "")
        elif msg_type == "button":
            text = msg.get("button", {}).get("text", "")

        name = value.get("contacts", [{}])[0].get("profile", {}).get("name", "Cliente")

        if not text:
            return None

        return {"phone": phone, "text": text, "name": name}
    except (IndexError, KeyError, TypeError):
        return None
