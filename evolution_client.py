import os
import aiohttp
from typing import Optional

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE_NAME = os.getenv("EVOLUTION_INSTANCE_NAME", "zapturbo")


async def send_text(to: str, text: str) -> dict:
    payload = {
        "number": to,
        "text": text,
        "delay": 1200,
    }
    return await _post("/message/sendText", payload)


async def send_image(to: str, image_url: str, caption: Optional[str] = None) -> dict:
    payload = {
        "number": to,
        "media": image_url,
        "caption": caption or "",
        "delay": 1200,
    }
    return await _post("/message/sendMedia", payload)


async def send_buttons(to: str, text: str, buttons: list[list[str]]) -> dict:
    payload = {
        "number": to,
        "title": text,
        "description": "",
        "footer": "ZAPTURBO",
        "buttons": buttons,
        "delay": 1200,
    }
    return await _post("/message/sendButtons", payload)


async def send_list(to: str, title: str, description: str, sections: list[dict]) -> dict:
    payload = {
        "number": to,
        "title": title,
        "description": description,
        "footerText": "ZAPTURBO",
        "sections": sections,
    }
    return await _post("/message/sendList", payload)


async def _post(endpoint: str, payload: dict) -> dict:
    url = f"{EVOLUTION_API_URL}/{EVOLUTION_INSTANCE_NAME}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
            data = await resp.json()
            return data


async def check_connection() -> bool:
    url = f"{EVOLUTION_API_URL}/{EVOLUTION_INSTANCE_NAME}/connectionState"
    headers = {"apikey": EVOLUTION_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("state", "") == "open"
                return False
    except Exception:
        return False


async def get_qrcode() -> Optional[str]:
    url = f"{EVOLUTION_API_URL}/{EVOLUTION_INSTANCE_NAME}/qrcode"
    headers = {"apikey": EVOLUTION_API_KEY}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("qrcode", {}).get("code")
                return None
    except Exception:
        return None
