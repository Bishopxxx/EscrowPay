from app.core.config import settings
import hmac
import hashlib

def verify_signature(payload: bytes, signature:str) -> bool:
    expected = hmac.new(
        settings.NOMBA_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
