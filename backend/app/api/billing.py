from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx
import uuid
import time
from app.core.dependencies import get_current_user
from app.db.supabase_client import supabase
from app.core.config import settings

router = APIRouter()

class OrderRequest(BaseModel):
    amount: float
    customer_phone: str = "9999999999"
    return_url: str = None

class VerifyRequest(BaseModel):
    order_id: str

@router.post("/create-order")
async def create_order(req: OrderRequest, user = Depends(get_current_user)):
    url = "https://api.cashfree.com/pg/orders"
    order_id = f"order_{int(time.time())}_{str(uuid.uuid4())[:8]}"
    
    # Validate return_url to prevent open redirect attacks
    ALLOWED_DOMAINS = [
        "https://learnbygenie.online",
        "https://www.learnbygenie.online",
        "https://teachgenie.online",
        "https://www.teachgenie.online",
        "http://localhost"
    ]
    if req.return_url and not any(req.return_url.startswith(domain) for domain in ALLOWED_DOMAINS):
        raise HTTPException(status_code=400, detail="Invalid return URL")
    
    payload = {
        "order_amount": req.amount,
        "order_currency": "INR",
        "order_id": order_id,
        "customer_details": {
            "customer_id": str(user.id),
            "customer_email": user.email or "student@learnbygenie.online",
            "customer_phone": req.customer_phone
        },
        "order_meta": {
            "return_url": req.return_url if req.return_url else f"https://learnbygenie.online/pricing?order_id={order_id}"
        }
    }
    
    headers = {
        "accept": "application/json",
        "x-api-version": "2023-08-01",
        "content-type": "application/json",
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=f"Cashfree error: {response.text}")
            
        data = response.json()
        return {
            "payment_session_id": data.get("payment_session_id"),
            "order_id": order_id
        }

@router.post("/verify-payment")
async def verify_payment(req: VerifyRequest, user = Depends(get_current_user)):
    url = f"https://api.cashfree.com/pg/orders/{req.order_id}"
    
    headers = {
        "accept": "application/json",
        "x-api-version": "2023-08-01",
        "x-client-id": settings.CASHFREE_APP_ID,
        "x-client-secret": settings.CASHFREE_SECRET_KEY
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to verify order")
            
        data = response.json()
        if data.get("order_status") == "PAID":
            supabase.table("profiles").update({
                "plan": "pro",
                "subscription_status": "active"
            }).eq("id", user.id).execute()
            return {"status": "success", "message": "Upgraded"}
        else:
            return {"status": "pending"}

@router.post("/upgrade-confirm")
async def confirm_upgrade(user = Depends(get_current_user)):
    return {"status": "deprecated"}
