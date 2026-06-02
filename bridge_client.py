import os
import time
import threading

_outbox = []
_outbox_lock = threading.Lock()
_id_counter = 0


async def send_text(to: str, text: str) -> dict:
    global _id_counter

    with _outbox_lock:
        _id_counter += 1
        _outbox.append({
            "id": _id_counter,
            "to": to,
            "text": text,
            "created_at": time.time(),
        })

    return {"ok": True, "id": _id_counter}


def get_outbox_messages() -> list[dict]:
    with _outbox_lock:
        return list(_outbox)


def mark_message_sent(msg_id: int):
    with _outbox_lock:
        for i, msg in enumerate(_outbox):
            if msg["id"] == msg_id:
                _outbox.pop(i)
                return True
    return False


async def check_status() -> dict:
    return {"status": "ok", "queue_size": len(_outbox)}
