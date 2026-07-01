import httpx
import time
from app.core.config import settings

BASE_URL = settings.NOMBA_API_URL
_token_cache: dict = {}


async def get_access_token() -> str:
    if _token_cache.get("token") and _token_cache.get("expires_at", 0) > time.time() + 300:
        return _token_cache["token"]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/auth/token/issue",
            headers ={
                "Content-Type":"application/json",
                "accountId":settings.NOMBA_PARENT_ACCOUNT_ID
            },
            json={
                "client_id": settings.NOMBA_CLIENT_ID,
                "client_secret":settings.NOMBA_PRIVATE_KEY,
                "grant_type": "client_credentials"
            }
        )
        response.raise_for_status()
        data = response.json()["data"]
        _token_cache["token"] = data["access_token"]
        # 
        _token_cache["expires_at"] = time.time() + 1800
        return _token_cache["token"]


async def get_headers() -> dict:
    token = await get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "accountId": settings.NOMBA_PARENT_ACCOUNT_ID,
        "Content-Type": "application/json"
    }


async def create_virtual_account(account_ref: str, account_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v1/accounts/virtual",
            headers=await get_headers(),
            json={
                "accountRef": account_ref,
                "accountName": account_name,
                "currency": "NGN"
            }
        )
        response.raise_for_status()
        return response.json()["data"]


async def lookup_bank_account(account_number: str, bank_code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/v1/transfers/bank/lookup",
            headers=await get_headers(),
            params={
                "accountNumber": account_number,
                "bankCode": bank_code
            }
        )
        response.raise_for_status()
        return response.json()["data"]


async def transfer_to_bank(
    amount: float,
    account_number: str,
    account_name: str,
    bank_code: str,
    merchant_tx_ref: str,
    narration: str = ""
) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/v2/transfers/bank",
            headers=await get_headers(),
            json={
                "amount": amount,
                "accountNumber": account_number,
                "accountName": account_name,
                "bankCode": bank_code,
                "merchantTxRef": merchant_tx_ref,
                "senderName": "EscrowPay",
                "narration": narration
            }
        )
        response.raise_for_status()
        return response.json()["data"]
    

def normalize_name(name: str) -> str:
    return " ".join(name.upper().split())


async def verify_and_transfer(
    seller_name: str,
    amount: float,
    account_number: str,
    bank_code: str,
    merchant_tx_ref: str,
    narration: str = ""
) -> dict:
    # Step 1: look up the account
    bank_data = await lookup_bank_account(account_number, bank_code)
    returned_name = bank_data.get("accountName", "")

    # Step 2: compare names
    if normalize_name(returned_name) != normalize_name(seller_name):
        raise ValueError(
            f"Name mismatch: expected '{seller_name}', got '{returned_name}'"
        )

    # Step 3: transfer only if names match
    return await transfer_to_bank(
        amount=amount,
        account_number=account_number,
        account_name=returned_name,
        bank_code=bank_code,
        merchant_tx_ref=merchant_tx_ref,
        narration=narration
    )