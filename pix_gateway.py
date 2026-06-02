import os
import json
import time
import secrets
import aiohttp
from datetime import datetime, timedelta

CLIENT_ID = os.getenv("VEOPAG_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("VEOPAG_CLIENT_SECRET", "")
BASE_URL = "https://api.veopag.com/api/v1"

_token_cache = {"token": None, "expires_at": 0}


async def _get_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    async with aiohttp.ClientSession() as session:
        payload = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET}
        async with session.post(f"{BASE_URL}/auth/token", json=payload, timeout=15) as resp:
            data = await resp.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = time.time() + 3300
            return _token_cache["token"]


async def create_pix_deposit(amount: float, external_id: str) -> dict:
    token = await _get_token()
    async with aiohttp.ClientSession() as session:
        payload = {
            "amount": amount,
            "external_id": external_id,
            "description": f"Pedido ZAPTURBO #{external_id}",
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with session.post(f"{BASE_URL}/transactions/deposit", json=payload, headers=headers, timeout=15) as resp:
            data = await resp.json()
            return data


async def check_deposit_status(external_id: str) -> str:
    token = await _get_token()
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {token}"}
        async with session.get(f"{BASE_URL}/transactions/deposit?external_id={external_id}", headers=headers, timeout=15) as resp:
            data = await resp.json()
            return data.get("status", "unknown")


def generate_external_id(prefix: str = "PEDIDO") -> str:
    token_hex = secrets.token_hex(6)
    return f"{prefix}_{token_hex}"
