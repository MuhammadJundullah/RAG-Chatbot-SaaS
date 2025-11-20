# app/api/v1/endpoints/payment_webhook.py
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
    # 1. Verify signature
    is_valid = await ipaymu_service.verify_webhook_signature(request)
    if not is_valid:
        # In a real scenario, we might want to log this IP for security review
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    # 2. Process the notification
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON payload")

    print(f"Received iPaymu Webhook: {payload}")

    # 3. Check status and activate
    status = payload.get('status')
    reference_id = payload.get('referenceId')

    if not status or not reference_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing status or referenceId in payload")

    if status.lower() == 'berhasil':
        try:
            subscription_id = int(reference_id)
            await subscription_service.activate_subscription(db, subscription_id=subscription_id)
        except (ValueError, TypeError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid referenceId format")
        except Exception as e:
            # Catch potential errors during activation and log them
            print(f"Error activating subscription from webhook: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to activate subscription")
    else:
        # Handle other statuses if necessary (e.g., 'pending', 'gagal')
        print(f"Received non-success status from iPaymu: {status}")

    return {"message": "Webhook received"}
