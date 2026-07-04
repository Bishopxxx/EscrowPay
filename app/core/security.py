import hmac
import hashlib
import base64
from app.core.config import settings

KEY = settings.NOMBA_WEBHOOK_SECRET.encode()

def verify_signature(payload: dict, headers: dict) -> bool:
    try:
        data = payload.get("data", {})
        merchant = data.get("merchant", {})
        transaction = data.get("transaction", {})

        s = ":".join([
            payload.get("event_type", ""),
            payload.get("requestId", ""),
            merchant.get("userId", ""),
            merchant.get("walletId", ""),
            transaction.get("transactionId", ""),
            transaction.get("type", ""),
            transaction.get("time", ""),
            transaction.get("responseCode", ""),
            headers.get("nomba-timestamp", "")
        ])

        expected = base64.b64encode(
            hmac.new(KEY, s.encode(), hashlib.sha256).digest()
        ).decode()

        return hmac.compare_digest(expected, headers.get("nomba-signature", ""))
    except Exception:
        return False
    



# def verify_signature(payload: bytes, signature:str) -> bool:
#     expected = hmac.new(
#         settings.NOMBA_WEBHOOK_SECRET.encode(),
#         payload,
#         hashlib.sha256
#     ).hexdigest()
#     return hmac.compare_digest(expected, signature)