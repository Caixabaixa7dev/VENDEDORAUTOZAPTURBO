import os
import aiohttp

BRIDGE_URL = os.getenv("BRIDGE_URL", "http://localhost:8080")


async def send_text(to: str, text: str) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{BRIDGE_URL}/send", json={"to": to, "text": text}, timeout=15) as r:
                return await r.json()
    except Exception as e:
        return {"error": str(e)}


async def check_status() -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{BRIDGE_URL}/", timeout=10) as r:
                return await r.json()
    except Exception:
        return {"status": "offline"}
