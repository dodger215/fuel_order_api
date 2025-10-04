import sys
import os
sys.path.append(os.path.dirname(os.path.abspath('create_demo_accounts.py')))

from app.database import get_db, init_db
from app.models import User, UserRole
from app.auth import get_password_hash
from sqlalchemy.orm import Session

def create_demo_accounts():
   
    init_db()
    
    # Get database session
    db = next(get_db())
    
    # Demo accounts data
    demo_accounts = [
        {
            "full_name": "John Doe",
            "email": "customer@demo.com",
            "phone_number": "+233241234567",
            "password": "demo123",
            "role": UserRole.CUSTOMER
        },
        {
            "full_name": "Kwame Mensah",
            "email": "driver@demo.com",
            "phone_number": "+233245678901",
            "password": "demo123",
            "role": UserRole.DRIVER
        },
        {
            "full_name": "Admin User",
            "email": "admin@demo.com",
            "phone_number": "+233249990000",
            "password": "demo123",
            "role": UserRole.ADMIN
        }
    ]
    
    try:
        for account_data in demo_accounts:
            # Check if user already exists
            existing_user = db.query(User).filter(
                (User.email == account_data["email"]) | 
                (User.phone_number == account_data["phone_number"])
            ).first()
            
            if existing_user:
                print(f"Demo account {account_data['email']} already exists, skipping...")
                continue
            
            # Create new user
            hashed_password = get_password_hash(account_data["password"])
            user = User(
                full_name=account_data["full_name"],
                email=account_data["email"],
                phone_number=account_data["phone_number"],
                hashed_password=hashed_password,
                role=account_data["role"],
                is_active=True,
                is_verified=True
            )
            
            db.add(user)
            print(f"Created demo account: {account_data['email']} ({account_data['role'].value})")
        
        db.commit()
        print("\nDemo accounts created successfully!")
        print("\nDemo Account Credentials:")
        print("=" * 50)
        for account in demo_accounts:
            print(f"Email: {account['email']}")
            print(f"Password: {account['password']}")
            print(f"Role: {account['role'].value}")
            print("-" * 30)
            
    except Exception as e:
        db.rollback()
        print(f"Error creating demo accounts: {e}")
        return False
    finally:
        db.close()
    
    return True

if __name__ == "__main__":
    print("Creating demo accounts for FuelDrop Ghana...")
    success = create_demo_accounts()
    
    if success:
        print("\nSetup complete! You can now test the authentication system.")
        print("\nTo start the FastAPI server, run:")
        print("uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("\nSetup failed. Please check the error messages above.")
        sys.exit(1)
