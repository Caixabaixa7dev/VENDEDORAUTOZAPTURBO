import os
import aiohttp
from typing import Optional

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:8080")
BOT_PORT = os.getenv("PORT", "10000")
BOT_PUBLIC_URL = os.getenv("BOT_PUBLIC_URL", f"http://localhost:{BOT_PORT}")


async def send_text(to: str, text: str) -> dict:
    payload = {"to": to, "text": text}
    return await _post("/send", payload)


async def send_image(to: str, image_url: str, caption: Optional[str] = None) -> dict:
    payload = {"to": to, "imageUrl": image_url, "caption": caption or ""}
    return await _post("/send-image", payload)


async def _post(endpoint: str, payload: dict) -> dict:
    url = f"{BRIDGE_URL}{endpoint}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, timeout=15) as resp:
                data = await resp.json()
                return data
        except Exception as e:
            return {"error": str(e)}


async def check_connection() -> bool:
    url = f"{BRIDGE_URL}/"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("status") == "connected"
                return False
    except Exception:
        return False


async def get_qr_code() -> Optional[str]:
    url = f"{BRIDGE_URL}/qr"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("qr")
                return None
    except Exception:
        return None
