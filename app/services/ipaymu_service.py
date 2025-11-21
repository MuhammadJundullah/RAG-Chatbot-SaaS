import hashlib
import hmac
import json
import time
from datetime import datetime
from urllib.parse import parse_qs
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
            # For form-urlencoded data, iPaymu hashes the raw body without url-encoding the space.
            # Python's json.dumps by default adds spaces.
            # So, for hashing, we should use the raw body_bytes when available.
            return hashlib.sha256(body_bytes).hexdigest()
        elif body is not None:
            # This path is used for creating payment, which is JSON.
            body_json = json.dumps(body, separators=(',', ':'))
            return hashlib.sha256(body_json.encode()).hexdigest()
        else:
            return hashlib.sha256("".encode()).hexdigest()

    def _sign(self, string_to_sign: str) -> str:
        return hmac.new(self.api_key.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

    def _create_signature(self, http_method: str, timestamp: str, body: dict = None, body_bytes: bytes = None) -> str:
        """
        Create signature per iPaymu spec for API requests (not for webhook validation).
        stringToSign = "{METHOD}:{VA}:{SHA256(body)}:{API_KEY}"
        signature = HMAC_SHA256(apiKey, stringToSign)
        """
        body_sha256_hash = self._body_sha256(body=body, body_bytes=body_bytes)
        # This string_to_sign format is for creating payments, NOT for verifying webhooks.
        string_to_sign = f"{http_method.upper()}:{self.va}:{body_sha256_hash}:{self.api_key}"
        return self._sign(string_to_sign)

    async def create_payment_link(self, subscription: Subscription, user: Users) -> tuple[str, str]:
        """
        Creates a payment link with iPaymu.
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
        }

        # 2. Generate timestamp (Unix epoch is not what iPaymu v2 uses for payments)
        # They use a 'timestamp' header for API calls but it's not clearly defined in docs,
        # often it's the YYYYMMDDHHMMSS format for other endpoints.
        # The create payment endpoint seems to not require it in the signature string itself.
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')


        # 3. Create signature with correct format for the payment API
        signature = self._create_signature("POST", timestamp, body=payload)
        
        print(f"Payload to iPaymu: {payload}")
        print(f"Signature: {signature}")
        print(f"Timestamp for header: {timestamp}")

        # 4. Make actual API call to iPaymu
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "signature": signature,
                    "va": self.va,
                    "Content-Type": "application/json",
                    "timestamp": timestamp # This header is required by many iPaymu APIs
                }
                # The payment API v2 doesn't seem to need apiKey in header, but others do.
                # Let's add it to be safe, but it's not standard. The signature is the key.

                response = await client.post(self.payment_url, headers=headers, json=payload)
                response.raise_for_status() 
                response_data = response.json()

                if response_data.get("Status") == 200:
                    data = response_data.get("Data")
                    if data and isinstance(data, dict):
                        payment_url = data.get("Url")
                        trx_id = data.get("TransactionId") or data.get("SessionID")

                        if payment_url and trx_id:
                            print(f"--- Received iPaymu payment URL: {payment_url} | trx_id: {trx_id} ---")
                            return payment_url, str(trx_id)
                        else:
                            raise HTTPException(status_code=500, detail="iPaymu response missing Url or TransactionId.")
                    else:
                        raise HTTPException(status_code=500, detail="iPaymu response has malformed Data.")
                else:
                    error_message = response_data.get('Message', 'Unknown iPaymu error')
                    raise HTTPException(status_code=500, detail=f"Failed to create payment link: {error_message}")

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"HTTP error with iPaymu API: {e.response.text}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=500, detail=f"Network error connecting to iPaymu API: {e}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


    async def verify_webhook_signature(self, request: Request) -> bool:
        """
        Verifies the incoming webhook signature from iPaymu. It handles both JSON
        and form-urlencoded bodies.

        The correct stringToSign format for webhooks is:
        stringToSign = "{METHOD}:{TRANSACTION_ID}:{SHA256(raw_body)}:{VA}"
        The signature is then HMAC_SHA256(stringToSign, ApiKey).
        """
        body_bytes = await request.body()
        payload = {}

        # Try to parse body, first as JSON, then as form-urlencoded
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                payload = json.loads(body_bytes)
            except json.JSONDecodeError:
                print("Webhook claimed to be JSON but failed to parse.")
                return False
        else: # Assume form-urlencoded as fallback
            try:
                form_data = parse_qs(body_bytes.decode('utf-8'))
                # Convert list values from parse_qs to single values
                payload = {k: v[0] for k, v in form_data.items() if v}
            except Exception as e:
                print(f"Failed to parse webhook body as form-urlencoded: {e}")
                return False

        if not payload:
            print("Webhook body is empty or could not be parsed.")
            return False

        headers_lower = {k.lower(): v for k, v in request.headers.items()}
        ipaymu_signature = headers_lower.get("signature")

        if not ipaymu_signature:
            print("Missing iPaymu webhook signature header.")
            return False

        # iPaymu uses 'trx_id' for notifications. 'sid' is another possibility.
        transaction_id = payload.get("trx_id") or payload.get("sid")
        if not transaction_id:
            print(f"Could not find 'trx_id' or 'sid' in webhook payload. Keys: {list(payload.keys())}")
            return False

        # The hash is ALWAYS of the raw, unmodified request body bytes.
        body_hash = self._body_sha256(body_bytes=body_bytes).lower()
        method = request.method.upper()
        
        # Correct format: METHOD:TRX_ID:HASHED_BODY:VA
        string_to_sign = f"{method}:{transaction_id}:{body_hash}:{self.va}"
        calculated_signature = self._sign(string_to_sign)

        if ipaymu_signature.lower() != calculated_signature.lower():
            print(f"Webhook signature mismatch! Received: {ipaymu_signature}")
            print(f"Expected (string_to_sign='{string_to_sign}'): {calculated_signature}")
            return False

        print("--- Webhook signature is valid ---")
        return True

ipaymu_service = IPaymuService()
