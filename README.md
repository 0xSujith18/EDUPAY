# EduPay - Student Payment System

A modern Flask-based student payment management system with SpaceX-inspired design.

## Features

- **Student Authentication**: Secure login system with rate limiting
- **Payment Management**: Make payments, view transaction history
- **Invoice System**: Pay pending invoices with passcode verification
- **PDF Receipts**: Generate formal Anna University-style receipts
- **Multiple Payment Gateways**: Support for Razorpay, Stripe, PayPal
- **Security**: Rate limiting, secure sessions, input validation
- **Modern UI**: SpaceX-inspired dark theme with responsive design

## Quick Start

### Option 1: Windows Batch File
```bash
start.bat
```

### Option 2: Python Script
```bash
python run.py
```

### Option 3: Direct Flask
```bash
python app.py
```

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Application**:
   ```bash
   python run.py
   ```

## Project Structure

```
edu pay/
├── app.py                 # Main Flask application
├── run.py                 # Startup script
├── start.bat             # Windows batch file
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── templates/            # HTML templates
│   ├── layout.html       # Base template with SpaceX theme
│   ├── login.html        # Login page
│   ├── dashboard.html    # Student dashboard
│   ├── make_payment.html # Payment form
│   ├── confirm_payment.html # Payment confirmation
│   └── payment_gateways.html # Payment methods
└── static/              # Static files
    ├── css/
    │   └── style.css    # Additional styles
    └── js/
        └── script.js    # JavaScript functionality
```

## Security Features

- **Rate Limiting**: 5 login attempts per 5 minutes
- **Passcode Protection**: 4-digit passcode for invoice payments
- **Session Security**: Secure session management
- **Input Validation**: XSS and injection protection
- **Security Headers**: CSP, XSS protection, etc.

## Payment Features

- **Invoice Management**: View and pay pending invoices
- **Transaction History**: Complete payment history
- **PDF Receipts**: Professional university-style receipts
- **Multiple Gateways**: Razorpay (UPI/GPay), Stripe, PayPal
- **Balance Management**: Real-time balance updates

## Configuration

### Environment Variables (.env)
```
FLASK_SECRET_KEY=your_secret_key
FLASK_DEBUG=False
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
STRIPE_PUBLISHABLE_KEY=your_stripe_key
STRIPE_SECRET_KEY=your_stripe_secret
```
