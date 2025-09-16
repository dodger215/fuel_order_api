from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime
from dotenv import load_dotenv


load_dotenv()
import os

from app.database import get_db, init_db
from app.models import Order, FuelType, OrderStatus, PaymentStatus
from app.paystack import paystack_service

from app.schemas import OrderCreate, OrderResponse, OrderStatus, OrderWithPaymentResponse
import logging
from fastapi.responses import HTMLResponse
app = FastAPI(title="Fuelease Ghana API", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
@app.on_event("startup")
def on_startup():
    init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# @app.get("/", response_class=HTMLResponse)
# async def read_html():
#     file_path = os.path.join(BASE_DIR, "templates", "fuel.html")
#     with open(file_path, "r", encoding="utf-8") as f:
#         html_content = f.read()
#     return HTMLResponse(content=html_content)

@app.get("/fuel-prices")
async def get_fuel_prices():
    """Get current fuel prices in Ghana"""
    return {
        "regular": 12.50,
        "premium": 14.80,
        "diesel": 13.20,
        "currency": "GHS",
        "last_updated": datetime.utcnow().isoformat()
    }

@app.post("/orders", response_model=OrderWithPaymentResponse)
async def create_order(order: OrderCreate, db: Session = Depends(get_db)):
    """Create a new fuel delivery order"""
    
    # Calculate total amount
    fuel_prices = {
        FuelType.REGULAR: 12.50,
        FuelType.PREMIUM: 14.80,
        FuelType.DIESEL: 13.20
    }
    
    price_per_liter = fuel_prices[order.fuel_type]
    total_amount = price_per_liter * order.quantity
    
    # Create order in database
    db_order = Order(
        phone_number=order.phone_number,
        email=order.email,
        delivery_address=order.delivery_address,
        fuel_type=order.fuel_type,
        quantity=order.quantity,
        price_per_liter=price_per_liter,
        total_amount=total_amount,
        delivery_time=order.delivery_time
    )
    
    db.add(db_order)
    db.commit()
    db.refresh(db_order)
    

    reference = f"FUE_{db_order.id}_{uuid.uuid4().hex[:8]}"
    email = order.email or f"customer{db_order.id}@fuelease.gh"
    
    metadata = {
        "order_id": db_order.id,
        "fuel_type": order.fuel_type.value,
        "quantity": order.quantity,
        "delivery_address": order.delivery_address
    }
    
    logger.info(f"Initializing Paystack payment for order {db_order.id}")
    payment_response = await paystack_service.initialize_transaction(
        email=email,
        amount=total_amount,
        reference=reference,
        metadata=metadata
    )
    
    if not payment_response:
        # Clean up the order if payment fails
        db.delete(db_order)
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment initialization failed. Please check your Paystack API keys and try again."
        )
    
    # Update order with payment reference
    db_order.paystack_reference = reference
    db_order.paystack_access_code = payment_response["data"]["access_code"]
    db.commit()
    db.refresh(db_order)
    
    # Convert SQLAlchemy model to Pydantic model
    order_response = OrderResponse.from_orm(db_order)
    
    return {
        "order": order_response,
        "payment_url": payment_response["data"]["authorization_url"]
    }



# Test endpoint to check Paystack configuration
@app.get("/test-paystack")
async def test_paystack():
    """Test Paystack connection"""
    
    
    # Test with a small amount
    test_response = await paystack_service.initialize_transaction(
        email="test@example.com",
        amount=10.00,
        reference=f"TEST_{uuid.uuid4().hex[:8]}",
        metadata={"test": True}
    )
    
    if test_response:
        return {
            "status": "success",
            "message": "Paystack connection successful",
            "response": test_response
        }
    else:
        return {
            "status": "error",
            "message": "Paystack connection failed. Check your API keys."
        }

@app.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get order details"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order": order}

@app.get("/orders", response_model=List[OrderResponse])
async def get_orders(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all orders"""
    orders = db.query(Order).offset(skip).limit(limit).all()
    return [{"order": order} for order in orders]

@app.post("/webhook/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Paystack webhook notifications"""
    payload = await request.json()
    event = payload.get("event")
    data = payload.get("data")
    
    if event == "charge.success":
        reference = data.get("reference")
        if reference and reference.startswith("FUE_"):
            # Find the order
            order = db.query(Order).filter(Order.paystack_reference == reference).first()
            if order:
                order.payment_status = PaymentStatus.SUCCESSFUL
                order.order_status = OrderStatus.CONFIRMED
                db.commit()
    
    return JSONResponse(content={"status": "success"})

@app.get("/verify-payment/{reference}")
async def verify_payment(reference: str, db: Session = Depends(get_db)):
    """Verify payment status"""
    verification = await paystack_service.verify_transaction(reference)
    
    if verification.get("status") and verification["data"]["status"] == "success":
        # Update order status
        order = db.query(Order).filter(Order.paystack_reference == reference).first()
        if order:
            order.payment_status = PaymentStatus.SUCCESSFUL
            order.order_status = OrderStatus.CONFIRMED
            db.commit()
            return {"status": "success", "order_id": order.id}
    
    return {"status": "failed"}
