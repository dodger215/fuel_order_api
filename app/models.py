from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class FuelType(str, enum.Enum):
    REGULAR = "regular"
    PREMIUM = "premium"
    DIESEL = "diesel"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    EN_ROUTE = "en_route"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    delivery_address = Column(String, nullable=False)
    fuel_type = Column(Enum(FuelType), nullable=False)
    quantity = Column(Integer, nullable=False)
    price_per_liter = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    delivery_time = Column(String, nullable=False)  # "now", "1hour", etc.
    order_status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    paystack_reference = Column(String, nullable=True)
    paystack_access_code = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)