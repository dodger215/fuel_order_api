import httpx

import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class PaystackService:
    def __init__(self):
        # REPLACE THESE HARDCODED KEYS WITH ENVIRONMENT VARIABLES
        self.secret_key = os.environ.get("PAYSTACK_SECRET_KEY")
        self.public_key = os.environ.get("PAYSTACK_PUBLIC_KEY")
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json"
        }
    async def initialize_transaction(self, email, amount, reference, metadata=None):
        url = f"{self.base_url}/transaction/initialize"
        payload = {
            "email": email,
            "amount": int(amount * 100),  # Convert to kobo
            "reference": reference,
            "metadata": metadata or {},
            "currency": "GHS"  # Ghana Cedis
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                response_data = response.json()
                
                logger.info(f"Paystack response: {response_data}")
                
                if response.status_code == 200 and response_data.get("status"):
                    return response_data
                else:
                    logger.error(f"Paystack API error: {response_data}")
                    return None
                    
        except httpx.RequestError as e:
            logger.error(f"Paystack request error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return None

    async def verify_transaction(self, reference):
        url = f"{self.base_url}/transaction/verify/{reference}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response_data = response.json()
                
                if response.status_code == 200 and response_data.get("status"):
                    return response_data
                else:
                    logger.error(f"Paystack verification error: {response_data}")
                    return None
                    
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return None

    async def create_transfer_recipient(self, name, account_number, bank_code, currency="GHS"):
        url = f"{self.base_url}/transferrecipient"
        payload = {
            "type": "mobile_money",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self.headers)
                return response.json()
        except Exception as e:
            logger.error(f"Transfer recipient error: {str(e)}")
            return None

paystack_service = PaystackService()