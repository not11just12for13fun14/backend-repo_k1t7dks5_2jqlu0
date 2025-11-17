"""
Database Schemas

Define your MongoDB collection schemas here using Pydantic models.
These schemas are used for data validation in your application.

Each Pydantic model represents a collection in your database.
Model name is converted to lowercase for the collection name:
- User -> "user" collection
- Product -> "product" collection
- BlogPost -> "blogs" collection
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

# Example schemas (kept for reference)

class User(BaseModel):
    """
    Users collection schema
    Collection name: "user" (lowercase of class name)
    """
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    address: str = Field(..., description="Address")
    age: Optional[int] = Field(None, ge=0, le=120, description="Age in years")
    is_active: bool = Field(True, description="Whether user is active")

class Product(BaseModel):
    """
    Products collection schema
    Collection name: "product" (lowercase of class name)
    """
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    category: str = Field(..., description="Product category")
    in_stock: bool = Field(True, description="Whether product is in stock")

# Super app schemas

class Authuser(BaseModel):
    """Auth users by phone number (collection: authuser)"""
    phone: str = Field(..., description="E.164 phone number or local string")
    name: Optional[str] = Field(None, description="Display name")

class Otp(BaseModel):
    """OTP requests (collection: otp)"""
    phone: str
    code: str
    status: Literal["pending", "verified", "expired"] = "pending"
    expires_at: datetime
    attempts: int = 0

class Session(BaseModel):
    """Auth session tokens (collection: session)"""
    user_id: str
    token: str
    expires_at: datetime

class Activity(BaseModel):
    """User activity timeline (collection: activity)"""
    user_id: str
    category: Literal["travel", "payment", "cab", "grocery"]
    title: str
    details: Optional[str] = None
    amount: Optional[float] = None

class Ride(BaseModel):
    """Cab rides (collection: ride)"""
    user_id: str
    pickup: str
    dropoff: str
    fare: float

class Order(BaseModel):
    """Grocery orders (collection: order)"""
    user_id: str
    items: int
    total: float

class Booking(BaseModel):
    """Travel bookings (collection: booking)"""
    user_id: str
    from_city: str
    to_city: str
    price: float

class Payment(BaseModel):
    """Payments (collection: payment)"""
    user_id: str
    amount: float
    method: Literal["card", "upi", "wallet"] = "card"
