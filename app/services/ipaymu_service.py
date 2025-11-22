import hashlib
import hmac
import json
from datetime import datetime
from urllib.parse import parse_qs

import httpx
from fastapi import HTTPException, Request

from app.core.config import settings
from app.models.user_model import Users
from app.schemas.subscription_schema import Subscription


class IPaymuService:
    def __init__(self):
        self.va = settings.IPAYMU_VA
        self.api_key = settings.IPAYMU_API_KEY
        # Kembali ke Sandbox untuk pengujian
        self.payment_url = "https://sandbox.ipaymu.com/api/v2/payment"

    def _normalize_url(self, path: str) -> str:
        """Memastikan base URL dan path digabungkan dengan bersih."""
        base = settings.APP_BASE_URL.rstrip("/")
        path_clean = path.lstrip("/")
        return f"{base}/{path_clean}"

    def _body_sha256(self, body: dict = None, body_bytes: bytes = None) -> str:
        """Menghitung SHA256 dari body request."""
        if body_bytes is not None:
            return hashlib.sha256(body_bytes).hexdigest()
        if body is not None:
            body_json = json.dumps(body, separators=(",", ":"))
            return hashlib.sha256(body_json.encode()).hexdigest()
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

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        signature = self._get_api_signature("POST", body=payload)

        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "signature": signature,
                    "va": self.va,
                    "Content-Type": "application/json",
                    "timestamp": timestamp,
                }
                response = await client.post(self.payment_url, headers=headers, json=payload)
                response.raise_for_status()
                response_data = response.json()

                if response_data.get("Status") == 200:
                    data = response_data.get("Data")
                    payment_url = data.get("Url")
                    trx_id = data.get("TransactionId") or data.get("SessionID")
                    return payment_url, str(trx_id)

                error_message = response_data.get("Message", "Unknown iPaymu error")
                raise HTTPException(status_code=500, detail=f"Failed to create payment link: {error_message}")

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=500, detail=f"HTTP error with iPaymu API: {e.response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

    async def verify_webhook_signature(self, request: Request) -> bool:
        """
        Memverifikasi signature webhook dengan Multi-Check Strategy.
        Mencoba 3 variasi rumus karena dokumentasi sering ambigu.
        """
        body_bytes = await request.body()

        headers_lower = {k.lower(): v for k, v in request.headers.items()}
        ipaymu_signature = headers_lower.get("x-signature") or headers_lower.get("signature")

        if not ipaymu_signature:
            raise HTTPException(status_code=400, detail="Missing webhook signature")

        body_hash = hashlib.sha256(body_bytes).hexdigest().lower()
        method = "POST"

        # Multi-check variations
        string_v1 = f"{method}:{self.va}:{body_hash}:{self.api_key}"
        calc_v1 = hmac.new(self.api_key.encode(), string_v1.encode(), hashlib.sha256).hexdigest()

        string_v2 = f"{method}:{self.va}:{body_hash}"
        calc_v2 = hmac.new(self.api_key.encode(), string_v2.encode(), hashlib.sha256).hexdigest()

        string_v3 = f"{method}:{self.va}:{body_hash}:{self.api_key}"
        calc_v3 = hashlib.sha256(string_v3.encode()).hexdigest()

        if ipaymu_signature.lower() == calc_v1.lower():
            return True
        if ipaymu_signature.lower() == calc_v2.lower():
            return True
        if ipaymu_signature.lower() == calc_v3.lower():
            return True

        raise HTTPException(status_code=400, detail="Invalid webhook signature")


ipaymu_service = IPaymuService()
