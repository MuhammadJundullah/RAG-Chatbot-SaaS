# app/api/v1/endpoints/payment_webhook.py
import json
from fastapi import APIRouter, Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db
from app.services.ipaymu_service import ipaymu_service
from app.services.subscription_service import subscription_service

router = APIRouter()


@router.post("/webhooks/ipaymu-notify", status_code=status.HTTP_200_OK)
async def handle_ipaymu_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handles incoming webhook notifications from iPaymu.
    """
    is_valid = await ipaymu_service.verify_webhook_signature(request)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    try:
        content_type = request.headers.get('content-type')
        if content_type == 'application/x-www-form-urlencoded':
            form_data = await request.form()
            payload = {key: value for key, value in form_data.items()}
            if 'trx_id' not in payload and 'body' in payload:
                try:
                    payload = json.loads(payload['body'])
                except json.JSONDecodeError:
                    pass
        elif content_type == 'application/json':
            payload = await request.json()
        else:
            body_bytes = await request.body()
            try:
                payload = json.loads(body_bytes.decode('utf-8'))
            except json.JSONDecodeError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported Content-Type or invalid body: {content_type}")

    except Exception as e:
        print(f"Error parsing iPaymu Webhook payload: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payload format: {e}")

    print(f"Received iPaymu Webhook: {payload}")

    status_payload = payload.get('status')
    reference_id = payload.get('referenceId')

    if not status_payload or not reference_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing status or referenceId in payload")

    if status_payload.lower() == 'berhasil':
        try:
            subscription_id = int(reference_id)
            await subscription_service.activate_subscription(db, subscription_id=subscription_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid referenceId format")
        except Exception as e:
            print(f"Error activating subscription from webhook: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to activate subscription")
    else:
        print(f"Received non-success status from iPaymu: {status_payload}")

    return {"message": "Webhook received"}
