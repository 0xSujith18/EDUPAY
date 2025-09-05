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

## Demo Accounts

| Username | Password | Role | Balance |
|----------|----------|------|---------|
| student1 | edu123   | Student | ₹150,000 |
| student2 | edu123   | Student | ₹200,000 |
| admin    | admin123 | Admin   | ₹500,000 |

**Default Passcode**: 1234 (for invoice payments)

## Installation

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Application**:
   ```bash
   python run.py
   ```

3. **Access Application**:
   - Open browser to `http://localhost:5000`
   - Login with demo accounts

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

### Public WiFi Compatibility
- HTTP mode enabled by default
- SSL can be enabled with `USE_SSL=True` environment variable
- Secure cookies disabled for public network compatibility

## Troubleshooting

### Common Issues

1. **Import Errors**: Run `pip install -r requirements.txt`
2. **Port Already in Use**: Change port in `app.py` or kill existing process
3. **PDF Generation Issues**: Ensure `reportlab` is installed
4. **Template Not Found**: Check templates directory structure

### Dependencies
- Flask 3.0.0
- reportlab 4.4.3 (for PDF generation)
- Werkzeug 3.0.1
- Bootstrap 5.3.0 (CDN)

## Development

### Adding New Features
1. Create new routes in `app.py`
2. Add templates in `templates/`
3. Update navigation in `layout.html`
4. Test with demo accounts

### Customization
- **Theme**: Modify CSS variables in `layout.html`
- **Payment Gateways**: Update `SimplePaymentGateway` class
- **Receipt Format**: Modify `download_receipt()` function

## License

This project is for educational purposes.

## Support

For issues or questions, check the troubleshooting section or review the code comments.