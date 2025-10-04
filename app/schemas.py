from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models import FuelType, OrderStatus, PaymentStatus, UserRole

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

# User Authentication Schemas
class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    password: str
    role: UserRole = UserRole.CUSTOMER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None

class PasswordChange(BaseModel):
    current_password: str
    new_password: str
