import json
from fastapi import APIRouter, Request

router = APIRouter()

@router.post("/webhooks/ipaymu-notify")
async def ipaymu_notify(request: Request):
    try:
        # Baca body (buat ambil reference_id / trx_id)
        try:
            body = await request.json()
        except Exception:
            # fallback jika form-urlencoded
            form_data = await request.form()
            body = dict(form_data)
        
        reference_id = body.get("reference_id") or body.get("referenceId")
        trx_id = body.get("trx_id") or body.get("sid")
        status_val = body.get("status")
        status_code = body.get("status_code") or body.get("statusCode")

        print(f"iPaymu Notify → Ref: {reference_id}, Trx: {trx_id}, Status: {status_val} ({status_code})")

        # DI SINI ANDA PROSES UPDATE SUBSCRIPTION
        # Contoh:
        # if status_code == 1 or status == "berhasil":
        #     await activate_subscription(reference_id)

        # SELALU balikkan 200 OK biar iPaymu berhenti retry
        return {"status": "OK", "message": "Webhook received successfully"}

    except Exception as e:
        print(f"Webhook error: {e}")
        # Tetap balikkan 200 biar iPaymu tidak retry terus
        return {"status": "OK", "message": "Processed with error"}
