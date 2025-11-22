import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.subscription_model import Subscription
from app.services.subscription_service import subscription_service

router = APIRouter()

def _is_success(status_val: str | None, status_code: str | None) -> bool:
    """Return True when the webhook indicates payment success."""
    if status_val:
        lowered = status_val.lower()
        if lowered in {"berhasil", "success", "paid", "selesai", "completed"}:
            return True
    if status_code:
        if str(status_code) in {"1", "200"}:
            return True
    return False


async def _parse_payload(request: Request) -> dict:
    """Best-effort payload parsing for JSON or form-urlencoded."""
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            return await request.json()
        form_data = await request.form()
        return {key: value for key, value in form_data.items()}
    except Exception:
        body_bytes = await request.body()
        try:
            return json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return {}


@router.post("/webhooks/ipaymu-notify")
async def ipaymu_notify(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await _parse_payload(request)
        reference_id = body.get("reference_id") or body.get("referenceId")
        trx_id = body.get("trx_id") or body.get("sid")
        status_val = body.get("status")
        status_code = body.get("status_code") or body.get("statusCode")

        print(f"iPaymu Notify → Ref: {reference_id}, Trx: {trx_id}, Status: {status_val} ({status_code})")

        # Update subscription/payment status in DB when possible
        try:
            if reference_id:
                sub_id = int(reference_id)
                subscription = await db.get(Subscription, sub_id)
                if subscription:
                    if trx_id:
                        subscription.payment_gateway_reference = trx_id
                        await db.commit()
                    if _is_success(status_val, status_code):
                        await subscription_service.activate_subscription(db, subscription_id=sub_id)
        except Exception as e:
            print(f"Failed to update subscription from webhook: {e}")

        return {"status": "OK", "message": "Webhook received successfully"}

    except Exception as e:
        print(f"Webhook error: {e}")
        return {"status": "OK", "message": "Processed with error"}
