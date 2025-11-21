import hashlib
import hmac
import json
import time
from datetime import datetime
from fastapi import Request, HTTPException
import httpx 

from app.core.config import settings
from app.schemas.subscription_schema import Subscription
from app.models.user_model import Users

class IPaymuService:
    def __init__(self):
        self.va = settings.IPAYMU_VA
        self.api_key = settings.IPAYMU_API_KEY
        # Use non-direct endpoint; direct requires paymentMethod/paymentChannel
        self.payment_url = "https://sandbox.ipaymu.com/api/v2/payment"

    def _normalize_url(self, path: str) -> str:
        """Ensure base URL and path join cleanly (avoid double slashes)."""
        base = settings.APP_BASE_URL.rstrip('/')
        path_clean = path.lstrip('/')
        return f"{base}/{path_clean}"

    def _body_sha256(self, body: dict = None, body_bytes: bytes = None) -> str:
        if body_bytes is not None:
            return hashlib.sha256(body_bytes).hexdigest()
        elif body is not None:
            body_json = json.dumps(body, separators=(',', ':'))
            return hashlib.sha256(body_json.encode()).hexdigest()
        else:
            return hashlib.sha256("".encode()).hexdigest()

    def _sign(self, string_to_sign: str) -> str:
        return hmac.new(self.api_key.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

    def _create_signature(self, http_method: str, timestamp: str, body: dict = None, body_bytes: bytes = None) -> str:
        """
        Create signature per iPaymu spec (common pattern):
        stringToSign = "{METHOD}:{VA}:{SHA256(body)}:{API_KEY}"
        signature = HMAC_SHA256(apiKey, stringToSign)
        """
        body_sha256_hash = self._body_sha256(body=body, body_bytes=body_bytes)
        string_to_sign = f"{http_method.upper()}:{self.va}:{body_sha256_hash}:{self.api_key}"
        return self._sign(string_to_sign)

    async def create_payment_link(self, subscription: Subscription, user: Users) -> tuple[str, str]:
        """
        (Placeholder) Creates a payment link with iPaymu.
        In a real scenario, this would make an HTTP request to iPaymu's API.
        """
        # 1. Prepare payload for iPaymu
        payload = {
            "product": [subscription.plan.name],
            "qty": [1],
            "price": [subscription.plan.price],
            "returnUrl": self._normalize_url("/payment-success"),
            "notifyUrl": self._normalize_url("/api/webhooks/ipaymu-notify"),
            "referenceId": str(subscription.id),
            "buyerName": user.name,
            "buyerEmail": user.email,
            # "paymentMethod": "banktransfer",  # Uncomment and adjust per desired method
        }

        # 2. Generate timestamp (Unix epoch, required by iPaymu)
        timestamp = str(int(time.time()))

        # 3. Create signature with correct format
        signature = self._create_signature("POST", timestamp, body=payload)
        
        # Log payload, signature, and timestamp for debugging
        print(f"Payload to iPaymu: {payload}")
        print(f"Signature: {signature}")
        print(f"Timestamp: {timestamp}")

        # 4. Make actual API call to iPaymu
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.payment_url,
                    headers={
                        "signature": signature,
                        "va": self.va,
                        "apiKey": self.api_key,
                        "Content-Type": "application/json",
                        "timestamp": timestamp
                    },
                    json=payload
                )
                response.raise_for_status() 
                response_data = response.json()

                # Check if the response status is successful and data is well-formed
                if response_data.get("Status") == 200:
                    data = response_data.get("Data")
                    if data and isinstance(data, dict):
                        payment_url = data.get("Url") or data.get("url")

                        # iPaymu responses vary: prefer TransactionId/trx_id; fallback to SessionID if needed.
                        trx_id = None
                        for key in ["TransactionId", "transactionId", "trx_id", "Trx_id"]:
                            if key in data:
                                trx_id = data[key]
                                break
                        if trx_id is None and "SessionID" in data:
                            trx_id = data["SessionID"]

                        if payment_url and trx_id:
                            print(f"--- Received iPaymu payment URL: {payment_url} | trx_id: {trx_id} ---")
                            return payment_url, trx_id
                        else:
                            print(f"iPaymu API returned Status 200 but missing Url/TransactionId. Data: {data}")
                            raise HTTPException(
                                status_code=500,
                                detail=f"iPaymu API returned success but missing Url/TransactionId. Response: {response_data}"
                            )
                    else:
                        # Handle cases where Status is 200 but Data is missing or malformed
                        print(f"iPaymu API returned Status 200 but malformed Data: {response_data}")
                        raise HTTPException(
                            status_code=500,
                            detail=f"iPaymu API returned a success status but malformed data. Response: {response_data}"
                        )
                else:
                    # This block handles non-200 statuses
                    error_message = response_data.get('Message', 'Unknown iPaymu error')
                    print(f"iPaymu API Error (Status: {response_data.get('Status')}): {error_message}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to create payment link: {error_message}"
                    )
        except httpx.HTTPStatusError as e:
            print(f"HTTP error creating iPaymu payment link: {e.response.text}")
            raise HTTPException(
                status_code=500,
                detail=f"HTTP error with iPaymu API: {e.response.text}"
            )
        except httpx.RequestError as e:
            print(f"Network error creating iPaymu payment link: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Network error connecting to iPaymu API: {e}"
            )
        except Exception as e:
            print(f"Unexpected error creating iPaymu payment link: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"An unexpected error occurred: {e}"
            )


    async def verify_webhook_signature(self, request: Request) -> bool:
        """
        Verifies the incoming webhook signature from iPaymu.
        """
        # Ensure we can read the raw body for signature verification
        body_bytes = await request.body()

        # Extract headers provided by iPaymu in a case-insensitive way.
        headers_lower = {k.lower(): v for k, v in request.headers.items()}
        ipaymu_signature = headers_lower.get("signature")
        ipaymu_va = headers_lower.get("va")
        ipaymu_timestamp = headers_lower.get("timestamp")

        if not all([ipaymu_signature, ipaymu_va, ipaymu_timestamp]):
            print("Missing iPaymu webhook headers for verification.")
            return False

        if ipaymu_va != self.va:
            print(f"Webhook VA mismatch. Expected {self.va}, got {ipaymu_va}")
            return False

        # Recalculate signature using the raw body bytes with a few known patterns (timestamp/no-timestamp)
        body_hash = self._body_sha256(body_bytes=body_bytes)
        method = request.method.upper()

        candidate_strings = [
            f"{method}:{self.va}:{body_hash}:{self.api_key}",  # current outbound pattern
            f"{method}:{self.va}:{ipaymu_timestamp}:{body_hash}",  # pattern with timestamp, no apiKey at end
            f"{method}:{self.va}:{ipaymu_timestamp}:{body_hash}:{self.api_key}",  # pattern with timestamp + apiKey
        ]
        candidate_sigs = [self._sign(s) for s in candidate_strings]

        if ipaymu_signature not in candidate_sigs:
            print(f"Webhook signature mismatch! Received: {ipaymu_signature}")
            print(f"Tried signatures: {candidate_sigs}")
            return False

        # Optional: Implement timestamp verification to prevent replay attacks.
        # This requires parsing ipaymu_timestamp and comparing it with current time
        # within an acceptable tolerance (e.g., 5-10 minutes).
        # For now, we'll mark as valid if signature matches.

        print("--- Webhook signature is valid ---")
        return True

ipaymu_service = IPaymuService()
