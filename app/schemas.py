from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models import FuelType, OrderStatus, PaymentStatus

class OrderCreate(BaseModel):
    phone_number: str
    email: Optional[EmailStr] = None
    delivery_address: str
    fuel_type: FuelType
    quantity: int
    delivery_time: str

class OrderResponse(BaseModel):
    id: int
    phone_number: str
    email: Optional[str]
    delivery_address: str
    fuel_type: FuelType
    quantity: int
    price_per_liter: float
    total_amount: float
    delivery_time: str
    order_status: OrderStatus
    payment_status: PaymentStatus
    paystack_reference: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OrderWithPaymentResponse(BaseModel):
    order: OrderResponse
    payment_url: str
