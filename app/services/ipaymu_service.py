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

    async def verify_webhook_signature(self, request: Request) -> dict:
        api_key = settings.IPAYMU_API_KEY.strip()

        body_bytes = await request.body()
        raw_body = body_bytes.decode("utf-8")

        received_sig = request.headers.get("X-Signature", "").lower().strip()
        if not received_sig:
            raise HTTPException(400, "Missing X-Signature")

        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = json.loads(raw_body)
        else:
            parsed = parse_qs(raw_body, keep_blank_values=True)
            data = {}
            for k in parsed:
                values = parsed[k]
                if len(values) == 1:
                    data[k] = values[0]
                else:
                    data[k] = values

        parts = []
        for key in data:
            if key == "aSignature":
                continue
            val = data[key]

            if isinstance(val, bool):
                parts.append("true" if val else "false")
            elif isinstance(val, (int, float)):
                parts.append(str(val))
            elif isinstance(val, list):
                parts.append(json.dumps(val, separators=(",", ":")))
            elif val is None:
                parts.append("")
            else:
                parts.append(str(val))

        string_to_hash = "".join(parts) + api_key
        calculated_sig = hashlib.sha256(string_to_hash.encode("utf-8")).hexdigest()

        print(f"String length: {len(string_to_hash)}")
        print(f"Calculated: {calculated_sig}")
        print(f"Received  : {received_sig}")

        if calculated_sig != received_sig:
            print(f"STRING FULL: {string_to_hash}")
            raise HTTPException(400, "Invalid webhook signature")

        print("iPaymu WEBHOOK SIGNATURE VALID!")
        return data

    async def _verify_transaction_via_api(self, trx_id: str) -> bool:
        """
        Fungsi Helper: Mengecek status transaksi langsung ke Server iPaymu.
        Ini mengabaikan masalah format JSON webhook yang berantakan.
        """
        check_url = "https://sandbox.ipaymu.com/api/v2/transaction"
        body = {"transactionId": trx_id}

        signature = self._get_api_signature("POST", body=body)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

        headers = {
            "Content-Type": "application/json",
            "signature": signature,
            "va": self.va,
            "timestamp": timestamp,
        }

        print(f"🔍 Re-Checking Transaction {trx_id} via API...")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(check_url, headers=headers, json=body)
                data = response.json()

                if data.get("Status") == 200:
                    trans_data = data.get("Data")
                    status_code = trans_data.get("Status")

                    if str(status_code) == "1":
                        print("✅ API Verification: Transaction is CONFIRMED SUCCESS.")
                        return True
                    if str(status_code) == "0":
                        print("⚠️ API Verification: Transaction is still PENDING.")
                        return True

                    print(f"❌ API Verification: Transaction status is {status_code} (Failed/Expired).")
                    raise HTTPException(status_code=400, detail="Transaction is not success on iPaymu")

                print(f"❌ API Verification Failed: {data}")
                raise HTTPException(status_code=400, detail="Failed to verify transaction via API")

        except Exception as e:
            print(f"❌ Error checking API: {e}")
            raise HTTPException(status_code=500, detail="Internal server error verifying transaction")


ipaymu_service = IPaymuService()
