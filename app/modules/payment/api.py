import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from datetime import datetime

from app.models.subscription_model import Subscription
from app.models.transaction_model import Transaction
from app.modules.subscription.service import subscription_service

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


def _is_expired(status_val: str | None, status_code: str | None) -> bool:
    """Return True when the webhook indicates payment expired/cancelled."""
    if status_val and status_val.lower() in {"expired", "cancelled", "canceled"}:
        return True
    if status_code and str(status_code) in {"-2"}:
        return True
    return False


async def _parse_payload(request: Request) -> dict:
    """Best-effort payload parsing for JSON or form-urlencoded."""
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            raw = await request.json()
            return {str(k).lower(): v for k, v in raw.items()}
        form_data = await request.form()
        return {str(key).lower(): value for key, value in form_data.items()}
    except Exception:
        body_bytes = await request.body()
        try:
            raw = json.loads(body_bytes.decode("utf-8"))
            return {str(k).lower(): v for k, v in raw.items()}
        except Exception:
            return {}


@router.post("/webhooks/ipaymu-notify")
async def ipaymu_notify(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        body = await _parse_payload(request)
        reference_id = body.get("reference_id") or body.get("referenceid")
        trx_id = body.get("trx_id") or body.get("trxid") or body.get("sid")
        status_val = body.get("status")
        status_code = body.get("status_code") or body.get("statuscode")

        print(f"iPaymu Notify → Ref: {reference_id}, Trx: {trx_id}, Status: {status_val} ({status_code})")

        handled = False

        # Try transaction-first flow
        if reference_id:
            try:
                tx_id = int(reference_id)
                transaction = await db.get(Transaction, tx_id)
                if transaction:
                    handled = True
                    if trx_id:
                        transaction.payment_reference = trx_id
                    if _is_success(status_val, status_code):
                        if transaction.status != "paid":
                            transaction.status = "paid"
                            transaction.paid_at = datetime.now()

                            if transaction.type == "topup":
                                subscription = await subscription_service.get_subscription_by_company(
                                    db, company_id=transaction.company_id
                                )
                                subscription.top_up_quota += transaction.questions_delta or 0
                            elif transaction.type == "subscription":
                                await subscription_service.apply_subscription_payment(db, transaction)
                            await db.commit()
                    elif _is_expired(status_val, status_code):
                        transaction.status = "expired"
                        if transaction.type == "subscription":
                            subscription = await subscription_service.get_subscription_by_company_optional(
                                db, company_id=transaction.company_id
                            )
                            if subscription:
                                subscription.status = "expired"
                    else:
                        # Pending/unknown status: mark pending explicitly
                        transaction.status = "pending_payment"
                    await db.commit()
            except Exception as e:
                await db.rollback()
                print(f"Failed to process transaction webhook: {e}")

        # Legacy: fall back to subscription reference if no transaction handled
        if not handled and reference_id:
            try:
                sub_id = int(reference_id)
                subscription = await db.get(Subscription, sub_id)
                if subscription:
                    if trx_id:
                        subscription.payment_gateway_reference = trx_id
                        await db.commit()
                    if _is_success(status_val, status_code):
                        await subscription_service.activate_subscription(db, subscription_id=sub_id)
                    elif _is_expired(status_val, status_code):
                        subscription.status = "expired"
                        await db.commit()
                        await db.refresh(subscription)
            except Exception as e:
                await db.rollback()
                print(f"Failed to update subscription from webhook: {e}")

        return {"status": "OK", "message": "Webhook received successfully"}

    except Exception as e:
        await db.rollback()
        print(f"Webhook error: {e}")
        return {"status": "OK", "message": "Processed with error"}
