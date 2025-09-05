import razorpay
import stripe
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class PaymentGateway:
    def __init__(self):
        # Razorpay configuration (supports GPay, PhonePe, Paytm, etc.)
        razorpay_key_id = os.getenv('RAZORPAY_KEY_ID')
        razorpay_secret = os.getenv('RAZORPAY_KEY_SECRET')
        if razorpay_key_id and razorpay_secret:
            self.razorpay_client = razorpay.Client(auth=(razorpay_key_id, razorpay_secret))
        else:
            self.razorpay_client = None
        
        # Stripe configuration
        stripe_secret = os.getenv('STRIPE_SECRET_KEY')
        if stripe_secret:
            stripe.api_key = stripe_secret
        else:
            stripe.api_key = None
        
        # PayPal configuration
        self.paypal_client_id = os.getenv('PAYPAL_CLIENT_ID')
        self.paypal_client_secret = os.getenv('PAYPAL_CLIENT_SECRET')
        self.paypal_base_url = 'https://api.sandbox.paypal.com'  # Use live URL for production

    def create_razorpay_order(self, amount, currency='INR', receipt=None):
        """Create Razorpay order for UPI payments (GPay, PhonePe, etc.)"""
        if not self.razorpay_client:
            return {'success': False, 'error': 'Razorpay not configured'}
        
        try:
            order_data = {
                'amount': int(amount * 100),  # Amount in paise
                'currency': currency,
                'receipt': receipt or f'receipt_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'payment_capture': 1
            }
            order = self.razorpay_client.order.create(data=order_data)
            return {
                'success': True,
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key_id': os.getenv('RAZORPAY_KEY_ID')
            }
        except razorpay.errors.BadRequestError as e:
            print(f"Razorpay order creation failed: {e}")
            return {'success': False, 'error': 'Order creation failed'}
        except Exception as e:
            print(f"Razorpay order creation error: {e}")
            return {'success': False, 'error': 'Payment service unavailable'}

    def verify_razorpay_payment(self, payment_id, order_id, signature):
        """Verify Razorpay payment signature"""
        if not self.razorpay_client:
            print("Razorpay verification failed: client not configured")
            return {'success': False, 'error': 'Payment verification unavailable'}
        
        try:
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            self.razorpay_client.utility.verify_payment_signature(params_dict)
            print(f"Razorpay payment verified successfully: {payment_id}")
            return {'success': True}
        except razorpay.errors.SignatureVerificationError as e:
            print(f"Razorpay signature verification failed: {e}")
            return {'success': False, 'error': 'Payment verification failed'}
        except Exception as e:
            print(f"Razorpay verification error: {e}")
            return {'success': False, 'error': 'Payment verification failed'}

    def create_stripe_payment_intent(self, amount, currency='usd'):
        """Create Stripe payment intent"""
        if not stripe.api_key:
            return {'success': False, 'error': 'Stripe not configured'}
        
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # Amount in cents
                currency=currency,
                payment_method_types=['card'],
            )
            return {
                'success': True,
                'client_secret': intent.client_secret,
                'publishable_key': os.getenv('STRIPE_PUBLISHABLE_KEY')
            }
        except stripe.error.StripeError as e:
            print(f"Stripe payment intent creation failed: {e}")
            return {'success': False, 'error': 'Payment processing failed'}
        except Exception as e:
            print(f"Stripe payment intent error: {e}")
            return {'success': False, 'error': 'Payment service unavailable'}

    def create_paypal_order(self, amount, currency='USD'):
        """Create PayPal order"""
        if not self.paypal_client_id or not self.paypal_client_secret:
            return {'success': False, 'error': 'PayPal not configured'}
        
        try:
            # Get access token
            auth_response = requests.post(
                f'{self.paypal_base_url}/v1/oauth2/token',
                headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
                data='grant_type=client_credentials',
                auth=(self.paypal_client_id, self.paypal_client_secret),
                timeout=30
            )
            
            if auth_response.status_code != 200:
                return {'success': False, 'error': 'PayPal authentication failed'}
            
            auth_data = auth_response.json()
            access_token = auth_data.get('access_token')
            if not access_token:
                return {'success': False, 'error': 'PayPal authentication failed'}
            
            # Create order
            order_data = {
                'intent': 'CAPTURE',
                'purchase_units': [{
                    'amount': {
                        'currency_code': currency,
                        'value': str(amount)
                    }
                }]
            }
            
            order_response = requests.post(
                f'{self.paypal_base_url}/v2/checkout/orders',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {access_token}'
                },
                data=json.dumps(order_data),
                timeout=30
            )
            
            if order_response.status_code == 201:
                order = order_response.json()
                return {
                    'success': True,
                    'order_id': order['id'],
                    'client_id': self.paypal_client_id
                }
            else:
                return {'success': False, 'error': 'PayPal order creation failed'}
                
        except requests.exceptions.RequestException as e:
            print(f"PayPal request error: {e}")
            return {'success': False, 'error': 'PayPal service unavailable'}
        except Exception as e:
            print(f"PayPal order creation error: {e}")
            return {'success': False, 'error': 'Payment service unavailable'}

    def get_supported_gateways(self):
        """Get list of supported payment gateways"""
        return [
            {
                'id': 'razorpay',
                'name': 'Razorpay (UPI/GPay/PhonePe)',
                'description': 'Pay using UPI, GPay, PhonePe, Paytm, Cards',
                'currency': 'INR',
                'icon': '💳'
            },
            {
                'id': 'stripe',
                'name': 'Stripe (Cards)',
                'description': 'Pay using Credit/Debit Cards',
                'currency': 'USD',
                'icon': '💳'
            },
            {
                'id': 'paypal',
                'name': 'PayPal',
                'description': 'Pay using PayPal account',
                'currency': 'USD',
                'icon': '🅿️'
            }
        ]

# Initialize payment gateway
payment_gateway = PaymentGateway()