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
        # Kembali ke Sandbox untuk pengujian
        self.payment_url = "https://sandbox.ipaymu.com/api/v2/payment"

    def _normalize_url(self, path: str) -> str:
        """Memastikan base URL dan path digabungkan dengan bersih."""
        base = settings.APP_BASE_URL.rstrip('/')
        path_clean = path.lstrip('/')
        return f"{base}/{path_clean}"

    def _body_sha256(self, body: dict = None, body_bytes: bytes = None) -> str:
        """Menghitung SHA256 dari body request."""
        if body_bytes is not None:
            # Gunakan body_bytes mentah untuk hashing webhook
            return hashlib.sha256(body_bytes).hexdigest()
        elif body is not None:
            # Gunakan JSON dumps tanpa whitespace untuk API request
            body_json = json.dumps(body, separators=(',', ':'))
            return hashlib.sha256(body_json.encode()).hexdigest()
        else:
            return hashlib.sha256("".encode()).hexdigest()

    def _create_api_signature(self, string_to_sign: str) -> str:
        """Menghitung HMAC-SHA256 untuk API Request (POST /payment)."""
        return hmac.new(self.api_key.encode(), string_to_sign.encode(), hashlib.sha256).hexdigest()

    def _calculate_plain_sha256(self, string_to_sign: str) -> str:
        """Menghitung SHA256 murni untuk Webhook Validation."""
        return hashlib.sha256(string_to_sign.encode()).hexdigest()

    def _get_api_signature(self, http_method: str, body: dict = None, body_bytes: bytes = None) -> str:
        """Membuat signature untuk API requests (POST /payment)."""
        body_sha256_hash = self._body_sha256(body=body, body_bytes=body_bytes)
        # Format stringToSign: {METHOD}:{VA}:{SHA256(body)}:{API_KEY}
        string_to_sign = f"{http_method.upper()}:{self.va}:{body_sha256_hash}:{self.api_key}"
        return self._create_api_signature(string_to_sign)

    async def create_payment_link(self, subscription: Subscription, user: Users) -> tuple[str, str]:
        """Membuat tautan pembayaran dengan iPaymu."""
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

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        signature = self._get_api_signature("POST", body=payload)
        
        print(f"Payload to iPaymu: {payload}")
        print(f"Signature: {signature}")
        print(f"Timestamp for header: {timestamp}")

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "signature": signature,
                    "va": self.va,
                    "Content-Type": "application/json",
                    "timestamp": timestamp 
                }
                response = await client.post(self.payment_url, headers=headers, json=payload)
                response.raise_for_status() 
                response_data = response.json()

                if response_data.get("Status") == 200:
                    # Logic untuk parsing respons yang berhasil...
                    data = response_data.get("Data")
                    payment_url = data.get("Url")
                    trx_id = data.get("TransactionId") or data.get("SessionID")
                    return payment_url, str(trx_id)
                else:
                    error_message = response_data.get('Message', 'Unknown iPaymu error')
                    raise HTTPException(status_code=500, detail=f"Failed to create payment link: {error_message}")

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"HTTP error with iPaymu API: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


    async def verify_webhook_signature(self, request: Request) -> bool:
        """
        Memverifikasi signature webhook yang masuk dari iPaymu.
        Perbaikan: Menggunakan SHA256 MURNI untuk validasi signature webhook.
        """

        body_bytes = await request.body()
        payload = {}

        # Parsing body (diasumsikan iPaymu mengirim form-urlencoded atau JSON)
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" in content_type:
            try:
                payload = json.loads(body_bytes)
            except json.JSONDecodeError:
                return False
        else:  # Form-urlencoded
            try:
                form_data = parse_qs(body_bytes.decode('utf-8'))
                payload = {k: v[0] for k, v in form_data.items() if v}
            except Exception:
                return False

        if not payload:
            print("Webhook body is empty or could not be parsed.")
            return False

        headers_lower = {k.lower(): v for k, v in request.headers.items()}
        ipaymu_signature = headers_lower.get("x-signature")

        if not ipaymu_signature:
            print("Missing iPaymu webhook signature header.")
            return False

        transaction_id = payload.get("trx_id") or payload.get("sid")
        if not transaction_id:
            print(f"Could not find 'trx_id' or 'sid' in webhook payload.")
            return False

        # 1. Hitung SHA256 dari body mentah (raw body)
        body_hash = self._body_sha256(body_bytes=body_bytes).lower()
        method = request.method.upper()
        
        # 2. Susun stringToSign untuk webhook: {METHOD}:{TRX_ID}:{HASHED_BODY}:{VA}
        string_to_sign = f"{method}:{transaction_id}:{body_hash}:{self.va}"
        
        # 3. Hitung Signature: Menggunakan SHA256 MURNI (bukan HMAC)
        calculated_signature = self._calculate_plain_sha256(string_to_sign)

        if ipaymu_signature.lower() != calculated_signature.lower():
            print(f"Webhook signature mismatch! Received: {ipaymu_signature}")
            print(f"Expected (string_to_sign='{string_to_sign}'): {calculated_signature}")
            # Log pesan error Anda di sini
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
            # return False # Jika Anda ingin menangani error di layer lain

        print("--- Webhook signature is valid ---")
        return True

ipaymu_service = IPaymuService()
