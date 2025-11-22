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
        Memverifikasi signature webhook SESUAI DOKUMENTASI V2.
        Rumus: HMAC-SHA256(HTTPMethod:VaNumber:Lowercase(SHA-256(RequestBody)):ApiKey, ApiKey)
        """
        body_bytes = await request.body()
        
        # 1. Ambil Header Signature (Cek X-Signature atau Signature)
        headers_lower = {k.lower(): v for k, v in request.headers.items()}
        ipaymu_signature = headers_lower.get("x-signature") or headers_lower.get("signature")

        if not ipaymu_signature:
            print("Missing iPaymu webhook signature header.")
            # return False # Atau raise error tergantung kebutuhan
            raise HTTPException(status_code=400, detail="Missing webhook signature")

        # 2. Hitung Body Hash (SHA256 dari raw body, lowercase)
        # Dokumen: "Request body di enkripsi menggunakan SHA256"
        body_hash = hashlib.sha256(body_bytes).hexdigest().lower()
        
        # 3. Susun StringToSign (Sesuai Dokumen Persis)
        # Dokumen: HTTPMethod:VaNumber:Lowercase(SHA-256(RequestBody)):ApiKey
        method = "POST" # Webhook iPaymu selalu POST
        
        # Perhatikan urutannya: Method : VA : BodyHash : ApiKey
        string_to_sign = f"{method}:{self.va}:{body_hash}:{self.api_key}"
        
        # 4. Hitung Signature menggunakan HMAC-SHA256
        # Dokumen: "Signature digenerate menggunakan HMAC-256 dengan ApiKey... dan StringToSign"
        calculated_signature = hmac.new(
            self.api_key.encode(),          # Key
            string_to_sign.encode(),        # Message
            hashlib.sha256                  # Algorithm
        ).hexdigest()

        # --- Debugging Print (Bisa dihapus nanti) ---
        print(f"--- DEBUG VERIFY SIGNATURE ---")
        print(f"Body Hash:      {body_hash}")
        print(f"String to Sign: {string_to_sign}")
        print(f"Calculated:     {calculated_signature}")
        print(f"Received:       {ipaymu_signature}")
        print(f"------------------------------")

        # 5. Bandingkan
        if ipaymu_signature.lower() != calculated_signature.lower():
            print("Webhook signature mismatch!")
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        print("--- Webhook signature is valid ---")
        return True

ipaymu_service = IPaymuService()
