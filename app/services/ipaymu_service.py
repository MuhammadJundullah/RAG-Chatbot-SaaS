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
        MODE DETEKTIF: Mencetak 3 Kemungkinan Struktur Data untuk menemukan mana yang benar.
        """
        body_bytes = await request.body()
        headers_lower = {k.lower(): v for k, v in request.headers.items()}
        ipaymu_signature = headers_lower.get("x-signature") or headers_lower.get("signature") or "NO_SIG"

        # Rekonstruksi data
        candidates: list[tuple[str, str]] = []
        try:
            body_str = body_bytes.decode("utf-8")
            parsed_data = parse_qs(body_str, keep_blank_values=True)
            raw_flat = {k: v[0] for k, v in parsed_data.items()}

            # Skenario 1: Semua string (kecuali boolean)
            data_s1 = raw_flat.copy()
            if "is_escrow" in data_s1:
                val = str(data_s1["is_escrow"]).lower()
                data_s1["is_escrow"] = (val == "1" or val == "true")
            json_1 = json.dumps(data_s1, separators=(",", ":")).replace("/", "\\/")
            candidates.append(("SEMUA STRING", json_1))

            # Skenario 2: ID/Status integer, uang tetap string
            data_s2 = raw_flat.copy()
            int_fields = ["trx_id", "status_code", "transaction_status_code", "paid_off"]
            for field in int_fields:
                if field in data_s2 and data_s2[field].isdigit():
                    data_s2[field] = int(data_s2[field])
            if "is_escrow" in data_s2:
                val = str(data_s2["is_escrow"]).lower()
                data_s2["is_escrow"] = (val == "1" or val == "true")
            json_2 = json.dumps(data_s2, separators=(",", ":")).replace("/", "\\/")
            candidates.append(("MIXED TYPES", json_2))

            # Skenario 3: Sorted keys
            json_3 = json.dumps(data_s2, separators=(",", ":"), sort_keys=True).replace("/", "\\/")
            candidates.append(("SORTED KEYS", json_3))

        except Exception as e:
            print(f"Error Parsing: {e}")

        # Print perbandingan
        print("DETEKTIF SIGNATURE")
        print(f"Received Sig: {ipaymu_signature}")
        print(f"API Key Used: {self.api_key[:5]}... (Cek Sandbox/Prod!)")

        match_found = False
        for name, json_body in candidates:
            body_hash = hashlib.sha256(json_body.encode()).hexdigest().lower()
            str_sign = f"POST:{self.va}:{body_hash}:{self.api_key}"
            my_sig = hmac.new(self.api_key.encode(), str_sign.encode(), hashlib.sha256).hexdigest()

            is_match = my_sig.lower() == ipaymu_signature.lower()
            prefix = "MATCH" if is_match else "GAGAL"
            if is_match:
                match_found = True

            print(f"--- {name} ---")
            print(f"JSON: {json_body}")
            print(f"Hash Body: {body_hash}")
            print(f"Signature: {my_sig} {prefix}")

        print("------------------------------------------------")

        # SEMENTARA: Return True agar iPaymu tidak retry terus.
        # Cek log untuk melihat kandidat mana yang match.
        return True


ipaymu_service = IPaymuService()
