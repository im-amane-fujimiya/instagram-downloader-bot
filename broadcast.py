import os
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TABLE = "broadcast_chats"


def _headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def register_chat(chat):
    if not SUPABASE_URL or not SUPABASE_KEY or not chat:
        return False

    if chat.get("type") not in ("group", "supergroup", "channel"):
        return False

    row = {
        "chat_id": str(chat["id"]),
        "chat_type": chat["type"],
        "title": chat.get("title") or "",
        "active": True,
    }

    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers={
                **_headers(),
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            json=row,
            timeout=15,
        )
        print("BROADCAST REGISTER:", r.status_code, r.text[:500])
        return r.ok
    except Exception as e:
        print("BROADCAST REGISTER ERROR:", repr(e))
        return False


def unregister_chat(chat_id):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return False

    try:
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers=_headers(),
            params={"chat_id": f"eq.{chat_id}"},
            json={"active": False},
            timeout=15,
        )
        return r.ok
    except Exception as e:
        print("BROADCAST UNREGISTER ERROR:", repr(e))
        return False


def get_broadcast_chats():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{TABLE}",
            headers=_headers(),
            params={
                "active": "eq.true",
                "select": "chat_id,chat_type,title",
                "order": "id.asc",
            },
            timeout=15,
        )
        if not r.ok:
            print("BROADCAST LIST ERROR:", r.status_code, r.text[:500])
            return []
        return r.json() or []
    except Exception as e:
        print("BROADCAST LIST ERROR:", repr(e))
        return []


def broadcast_copy_message(telegram_api, from_chat_id, message_id, telegram_helper):
    targets = get_broadcast_chats()
    success = 0
    failed = 0

    for target in targets:
        target_id = target.get("chat_id")
        if not target_id:
            continue

        try:
            telegram_helper(
                "copyMessage",
                payload={
                    "chat_id": target_id,
                    "from_chat_id": from_chat_id,
                    "message_id": message_id,
                },
                timeout=30,
            )
            success += 1
        except Exception as e:
            failed += 1
            print("BROADCAST SEND FAILED:", target_id, repr(e))

            error = str(e).lower()
            if (
                "chat not found" in error
                or "bot was kicked" in error
                or "forbidden" in error
                or "not enough rights" in error
            ):
                unregister_chat(target_id)

    return success, failed, len(targets)
            
