import os
from pathlib import Path

from dotenv import load_dotenv
import razorpay

# Load environment variables from .env (fallback to .env.example for placeholders)
env_path = Path('.env')
if not env_path.is_file():
    example_path = Path('.env.example')
    if example_path.is_file():
        print('Loading example env file. Please create a .env with real credentials.')
        load_dotenv(example_path)
    else:
        print('No .env or .env.example found. Exiting.')
        exit(1)
else:
    load_dotenv(env_path)

# Retrieve credentials
key_id = os.getenv('RAZORPAY_KEY_ID')
key_secret = os.getenv('RAZORPAY_KEY_SECRET')

if not key_id or not key_secret:
    print('Error: Razorpay credentials are missing. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env')
    exit(1)

client = razorpay.Client(auth=(key_id, key_secret))

# Create a test payment link for ₹500 (50000 paise)
payload = {
    "amount": 50000,
    "currency": "INR",
    "description": "Test payment link for Razorpay sandbox"
}

try:
    response = client.payment_link.create(payload)
    print('Payment link created successfully')
    print('Short URL:', response.get('short_url'))
    print('Link ID:', response.get('id'))
except razorpay.errors.BadRequestError as e:
    print('Bad request error:', e)
except razorpay.errors.ServerError as e:
    print('Server error:', e)
except Exception as e:
    print('Unexpected error:', e)
