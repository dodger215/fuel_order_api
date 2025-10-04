from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime, timedelta
import os

from app.database import get_db, init_db
from app.models import Order, FuelType, OrderStatus, PaymentStatus, User, UserRole
from app.paystack import paystack_service

from app.schemas import (
    OrderCreate, OrderResponse, OrderStatus, OrderWithPaymentResponse,
    UserCreate, UserLogin, UserResponse, Token, UserUpdate, PasswordChange
)
from app.auth import (
    authenticate_user, create_access_token, get_current_user, get_current_active_user,
    get_password_hash, verify_password, validate_ghana_phone, validate_password_strength
)
import logging
from fastapi.responses import HTMLResponse


from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI(title="Fuelease Ghana API", version="1.0.0")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# CORS middleware
# CORS middleware - Updated configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fuelapp.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Allow-Origin",
        "Access-Control-Allow-Headers",
        "Access-Control-Allow-Methods"
    ],
    expose_headers=["Content-Length", "Content-Type"],
    max_age=3600,
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

# Authentication endpoints
@app.post("/auth/signup", response_model=UserResponse)
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account"""
    
    # Validate phone number
    if not validate_ghana_phone(user.phone_number):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Ghana phone number format"
        )
    
    # Validate password strength
    if not validate_password_strength(user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters long"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user.email) | (User.phone_number == user.phone_number)
    ).first()
    
    if existing_user:
        if existing_user.email == user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        full_name=user.full_name,
        email=user.email,
        phone_number=user.phone_number,
        hashed_password=hashed_password,
        role=user.role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@app.post("/auth/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token"""
    
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }




@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return current_user

@app.put("/auth/profile", response_model=UserResponse)
async def update_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update user profile"""
    
    # Check if phone number is being updated and validate it
    if user_update.phone_number and user_update.phone_number != current_user.phone_number:
        if not validate_ghana_phone(user_update.phone_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Ghana phone number format"
            )
        
        # Check if phone number is already taken
        existing_user = db.query(User).filter(
            User.phone_number == user_update.phone_number,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # Update user fields
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name
    if user_update.phone_number is not None:
        current_user.phone_number = user_update.phone_number
    if user_update.is_active is not None:
        current_user.is_active = user_update.is_active
    
    db.commit()
    db.refresh(current_user)
    
    return current_user

@app.post("/auth/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # Validate new password
    if not validate_password_strength(password_change.new_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters long"
        )
    
    # Update password
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}

@app.get("/auth/demo-accounts")
async def get_demo_accounts():
    """Get demo account credentials for testing"""
    return {
        "customer": {
            "email": "customer@demo.com",
            "password": "demo123",
            "role": "customer"
        },
        "driver": {
            "email": "driver@demo.com", 
            "password": "demo123",
            "role": "driver"
        },
        "admin": {
            "email": "admin@demo.com",
            "password": "demo123", 
            "role": "admin"
        }
    }

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
async def create_order(
    order: OrderCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new fuel delivery order"""
    
    # Validate Paystack keys
   
    
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
        user_id=current_user.id if current_user else None,
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

# Update your frontend JavaScript to integrate with the API