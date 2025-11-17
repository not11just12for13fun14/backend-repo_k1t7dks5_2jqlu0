import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents

app = FastAPI(title="Super App API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OTPRequest(BaseModel):
    phone: str

class OTPVerify(BaseModel):
    phone: str
    code: str


@app.get("/")
def root():
    return {"message": "Super App Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response


# --------- OTP Auth Endpoints ---------
@app.post("/auth/request-otp")
def request_otp(payload: OTPRequest):
    phone = payload.phone.strip()
    if not phone:
        raise HTTPException(status_code=400, detail="Phone is required")

    # generate 6-digit code
    code = f"{secrets.randbelow(1000000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # Save to otp collection
    create_document("otp", {
        "phone": phone,
        "code": code,
        "status": "pending",
        "expires_at": expires_at,
        "attempts": 0,
    })

    # In real life, send SMS. Here we return code for demo
    return {"success": True, "code": code, "expires_in": 300}


@app.post("/auth/verify-otp")
def verify_otp(payload: OTPVerify):
    phone = payload.phone.strip()
    code = payload.code.strip()
    now = datetime.now(timezone.utc)

    matches = get_documents("otp", {"phone": phone, "code": code}, limit=1)
    if not matches:
        raise HTTPException(status_code=400, detail="Invalid code")

    otp_doc = matches[0]
    if otp_doc.get("status") == "expired" or otp_doc.get("expires_at") < now:
        raise HTTPException(status_code=400, detail="Code expired")

    token = secrets.token_hex(16)
    expires_at = now + timedelta(days=7)
    create_document("session", {
        "user_id": phone,
        "token": token,
        "expires_at": expires_at,
    })

    # mark otp as verified (best-effort)
    try:
        db["otp"].update_many({"phone": phone, "code": code}, {"$set": {"status": "verified", "updated_at": now}})
    except Exception:
        pass

    return {"success": True, "token": token}


# --------- Activity feed (travel/payment/cab/grocery) ---------
@app.get("/activity")
def list_activity(token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    sessions = get_documents("session", {"token": token}, limit=1)
    if not sessions:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = sessions[0]["user_id"]

    items = get_documents("activity", {"user_id": user_id}, limit=50)
    # seed some demo items on first visit
    if not items:
        now = datetime.now(timezone.utc)
        demo = [
            {"user_id": user_id, "category": "travel", "title": "Flight to NYC booked", "details": "6E 101", "amount": 249.0},
            {"user_id": user_id, "category": "payment", "title": "Paid at Coffee Bar", "details": "VISA **** 4213", "amount": 4.5},
            {"user_id": user_id, "category": "cab", "title": "Cab ride completed", "details": "Downtown to Office", "amount": 12.3},
            {"user_id": user_id, "category": "grocery", "title": "Grocery order delivered", "details": "Order #GZ1021", "amount": 56.9},
        ]
        for d in demo:
            create_document("activity", d)
        items = get_documents("activity", {"user_id": user_id}, limit=50)

    return {"items": items}


# Minimal endpoints per vertical for UI demo
class RideQuoteRequest(BaseModel):
    pickup: str
    dropoff: str

@app.post("/cab/quote")
def cab_quote(req: RideQuoteRequest, token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    fare = round(2.5 + 1.2 * max(1, len(req.pickup + req.dropoff)) / 10, 2)
    return {"pickup": req.pickup, "dropoff": req.dropoff, "fare": fare}


class GroceryCart(BaseModel):
    items: int

@app.post("/grocery/checkout")
def grocery_checkout(cart: GroceryCart, token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    total = round(3.99 + cart.items * 2.5, 2)
    return {"total": total, "status": "created"}


class TravelSearch(BaseModel):
    from_city: str
    to_city: str

@app.post("/travel/search")
def travel_search(q: TravelSearch, token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    price = round(99 + (len(q.from_city) + len(q.to_city)) * 5.5, 2)
    return {"results": [{"from": q.from_city, "to": q.to_city, "airline": "IndiGo", "price": price}]}


class PaymentIntent(BaseModel):
    amount: float
    method: Optional[str] = "card"

@app.post("/pay/create-intent")
def create_payment(pi: PaymentIntent, token: Optional[str] = None):
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    ref = secrets.token_hex(8)
    create_document("payment", {"user_id": token, "amount": pi.amount, "method": pi.method, "ref": ref})
    return {"ref": ref, "status": "requires_confirmation"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
