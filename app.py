from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import math
import uuid
from markupsafe import escape, Markup
import threading
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import io
import secrets
import time
from functools import wraps
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
# University configuration constants
UNIVERSITY_NAME = "Anna University"
UNIVERSITY_SUBTITLE = "College of Engineering"
UNIVERSITY_ADDRESS = "Chennai, Tamil Nadu - 600025"
CONTACT_EMAIL = "fees@annauniv.edu"
CONTACT_PHONE = "+91-44-2235-8000"
WEBSITE_URL = "www.annauniv.edu"

# Email configuration
EMAIL_CONFIG = {
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email': 'edupay.system@gmail.com',  # Replace with your email
    'password': 'your_app_password'      # Replace with your app password
}

def send_receipt_email(student_email, student_name, receipt_pdf, transaction_id, amount):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['email']
        msg['To'] = student_email
        msg['Subject'] = f'Payment Receipt - Transaction #{transaction_id}'
        
        body = f"""
Dear {student_name},

Thank you for your payment! Your transaction has been processed successfully.

Transaction Details:
- Transaction ID: {transaction_id}
- Amount: ₹{amount:,.2f}
- Date: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}

Please find your official receipt attached to this email.

Best regards,
Anna University Payment System
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Attach PDF receipt
        pdf_attachment = MIMEApplication(receipt_pdf, _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename=f'Receipt_{transaction_id}.pdf')
        msg.attach(pdf_attachment)
        
        # Send email
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False
from pymongo import MongoClient

app = Flask(__name__)
# Use a fixed secret key from environment or generate once and persist
SECRET_KEY_FILE = '.secret_key'
if os.path.exists(SECRET_KEY_FILE):
    with open(SECRET_KEY_FILE, 'r') as f:
        app.secret_key = f.read().strip()
else:
    secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
    with open(SECRET_KEY_FILE, 'w') as f:
        f.write(secret_key)
    app.secret_key = secret_key

# MongoDB connection
try:
    mongo_client = MongoClient('mongodb://localhost:27017/')
    db = mongo_client['edupay']
    payments_collection = db['payments']
except:
    mongo_client = None
    db = None
    payments_collection = None
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Security headers
@app.after_request
def add_security_headers(response):
    # Only add HSTS in production with valid SSL
    # response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' https://cdn.jsdelivr.net; font-src 'self' https://fonts.gstatic.com; connect-src 'self'"
    return response

# Rate limiting storage
login_attempts = {}

def rate_limit_check(key, max_attempts=5, window=300):
    now = time.time()
    if key not in login_attempts:
        login_attempts[key] = []
    login_attempts[key] = [attempt for attempt in login_attempts[key] if now - attempt < window]
    if len(login_attempts[key]) >= max_attempts:
        return False
    login_attempts[key].append(now)
    return True

def require_auth(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Persistent data storage
import json

USER_DATA_FILE = 'user_data.json'

def save_user_data():
    try:
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"Error saving user data: {e}")

def load_user_data():
    try:
        if os.path.exists(USER_DATA_FILE):
            with open(USER_DATA_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading user data: {e}")
    return {}

# In-memory data stores with thread safety
users = load_user_data()
next_user_id = 1
transactions_data = {}
invoices_data = {}
due_reminders = {}
support_messages = []
notification_templates = {
    'due_reminder': 'Dear {name}, your fee payment of ₹{amount} is due on {due_date}. Please pay at your earliest convenience.',
    'overdue_notice': 'URGENT: Dear {name}, your fee payment of ₹{amount} is overdue. Please pay immediately to avoid penalties.',
    'payment_confirmation': 'Dear {name}, your payment of ₹{amount} has been received and processed successfully.'
}
data_lock = threading.Lock()

# Fee structure storage
fee_structure_data = {
    'B.E Computer Science': {
        '1st Year': {'tuition': 150000, 'lab': 25000, 'library': 5000, 'activity': 10000},
        '2nd Year': {'tuition': 150000, 'lab': 30000, 'library': 5000, 'activity': 12000},
        '3rd Year': {'tuition': 160000, 'lab': 35000, 'library': 5000, 'activity': 15000},
        '4th Year': {'tuition': 160000, 'lab': 40000, 'library': 5000, 'activity': 18000}
    },
    'B.E Mechanical Engineering': {
        '1st Year': {'tuition': 140000, 'lab': 20000, 'library': 5000, 'activity': 10000},
        '2nd Year': {'tuition': 140000, 'lab': 25000, 'library': 5000, 'activity': 12000},
        '3rd Year': {'tuition': 150000, 'lab': 30000, 'library': 5000, 'activity': 15000},
        '4th Year': {'tuition': 150000, 'lab': 35000, 'library': 5000, 'activity': 18000}
    }
}

# Simple payment gateway mock (replaces payment_service.py)
class SimplePaymentGateway:
    def get_supported_gateways(self):
        return [
            {'id': 'razorpay', 'name': 'Razorpay (UPI/GPay)', 'description': 'Pay using UPI, GPay, PhonePe', 'currency': 'INR', 'icon': '💳'},
            {'id': 'stripe', 'name': 'Stripe (Cards)', 'description': 'Pay using Credit/Debit Cards', 'currency': 'INR', 'icon': '💳'},
            {'id': 'paypal', 'name': 'PayPal', 'description': 'Pay using PayPal account', 'currency': 'INR', 'icon': '🅿️'}
        ]
    
    def create_razorpay_order(self, amount):
        return {'success': True, 'order_id': f'order_{uuid.uuid4()}', 'amount': int(amount * 100), 'currency': 'INR', 'key_id': 'demo_key'}
    
    def create_stripe_payment_intent(self, amount):
        return {'success': True, 'client_secret': f'pi_{uuid.uuid4()}_secret', 'publishable_key': 'demo_key'}
    
    def create_paypal_order(self, amount):
        return {'success': True, 'order_id': f'paypal_{uuid.uuid4()}', 'client_id': 'demo_client'}
    
    def verify_razorpay_payment(self, payment_id, order_id, signature):
        return {'success': True}

payment_gateway = SimplePaymentGateway()

# Demo accounts
DEMO_ACCOUNTS = [
    {
        'username': 'student1',
        'password': 'edu123',
        'name': 'Student1',
        'email': 'student1@school.edu',
        'phone': '+91-9876543210',
        'parent_name': 'Parent One',
        'parent_phone': '+91-9876543211',
        'address': '123 Main Street, Chennai, Tamil Nadu - 600001',
        'grade': '10',
        'course': 'B.E Computer Science',
        'year': '2nd Year',
        'balance': 150000.00,
        'passcode_hash': generate_password_hash('1234')
    },
    {
        'username': 'student2',
        'password': 'edu123',
        'name': 'Student2',
        'email': 'student2@school.edu',
        'phone': '+91-9876543220',
        'parent_name': 'Parent Two',
        'parent_phone': '+91-9876543221',
        'address': '456 Park Avenue, Chennai, Tamil Nadu - 600002',
        'grade': '11',
        'course': 'B.E Mechanical Engineering',
        'year': '3rd Year',
        'balance': 200000.00,
        'passcode_hash': generate_password_hash('1234')
    },
    {
        'username': 'admin',
        'password': 'admin123',
        'name': 'Admin',
        'email': 'admin@school.edu',
        'phone': '+91-9876543230',
        'parent_name': 'N/A',
        'parent_phone': 'N/A',
        'address': 'University Campus, Chennai, Tamil Nadu - 600025',
        'grade': 'Staff',
        'course': 'Administration',
        'year': 'N/A',
        'balance': 500000.00,
        'is_admin': True,
        'passcode_hash': generate_password_hash('1234')
    }
]

# Parent accounts
PARENT_ACCOUNTS = [
    {
        'username': 'parent1',
        'password': 'parent123',
        'name': 'John Parent',
        'email': 'parent1@email.com',
        'phone': '+91-9876543240',
        'children': ['Student1', 'Student2'],
        'user_type': 'parent'
    }
]

# Institution accounts
INSTITUTION_ACCOUNTS = [
    {
        'username': 'institution1',
        'password': 'inst123',
        'name': 'ABC College',
        'email': 'admin@abccollege.edu',
        'phone': '+91-9876543250',
        'address': 'College Street, Chennai',
        'user_type': 'institution'
    }
]

def get_current_user():
    if 'username' in session and session['username'] in users:
        return users[session['username']]
    return None

def create_student_invoices(user_id):
    today = datetime.now().date()
    due_date_1 = today + timedelta(days=15)
    due_date_2 = today + timedelta(days=45)
    
    invoices = [
        {
            'id': str(uuid.uuid4()),
            'issue_date': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
            'due_date': due_date_1.strftime('%Y-%m-%d'),
            'description': 'Tuition Fee - Semester 1',
            'amount': 150000.00,
            'status': 'Pending',
            'paid_date': None,
            'due_soon': (due_date_1 - today).days <= 7
        },
        {
            'id': str(uuid.uuid4()),
            'issue_date': (today - timedelta(days=10)).strftime('%Y-%m-%d'),
            'due_date': due_date_2.strftime('%Y-%m-%d'),
            'description': 'Activity Fee',
            'amount': 12050.00,
            'status': 'Pending',
            'paid_date': None,
            'due_soon': (due_date_2 - today).days <= 7
        }
    ]
    invoices_data[user_id] = invoices

def initialize_demo_accounts():
    global next_user_id
    try:
        for account in DEMO_ACCOUNTS:
            if account['username'] not in users:
                users[account['username']] = {
                    'password_hash': generate_password_hash(account['password']),
                    'name': account['name'],
                    'email': account['email'],
                    'phone': account.get('phone', 'N/A'),
                    'parent_name': account.get('parent_name', 'N/A'),
                    'parent_phone': account.get('parent_phone', 'N/A'),
                    'address': account.get('address', 'N/A'),
                    'grade': account['grade'],
                    'course': account.get('course', 'N/A'),
                    'year': account.get('year', 'N/A'),
                    'balance': account['balance'],
                    'id': next_user_id,
                    'is_admin': account.get('is_admin', False),
                    'passcode_hash': account.get('passcode_hash', generate_password_hash('1234'))
                }
                transactions_data[next_user_id] = []
                create_student_invoices(next_user_id)
                next_user_id += 1
    except Exception as e:
        print(f"Error initializing demo accounts: {e}")

# Initialize data
initialize_demo_accounts()







@app.route('/')
def home():
    return render_template('home.html')






@app.route('/student-login')
def student_login():
    return redirect(url_for('login'))

@app.route('/parent-login', methods=['GET', 'POST'])
def parent_login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Add rate limiting for parent login
        if not rate_limit_check(f"parent_login_{client_ip}", max_attempts=5, window=300):
            flash('Too many login attempts. Please try again in 5 minutes.', 'danger')
            return redirect(url_for('parent_login'))
        
        parent = next((p for p in PARENT_ACCOUNTS if p['username'] == username), None)
        if parent and parent['password'] == password:
            session['username'] = username
            session['user_type'] = 'parent'
            session['user_data'] = parent
            flash('Welcome to Parent Portal!', 'success')
            return redirect(url_for('parent_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('parent_login.html')

@app.route('/institution-login', methods=['GET', 'POST'])
def institution_login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Add rate limiting for institution login
        if not rate_limit_check(f"institution_login_{client_ip}", max_attempts=5, window=300):
            flash('Too many login attempts. Please try again in 5 minutes.', 'danger')
            return redirect(url_for('institution_login'))
        
        institution = next((i for i in INSTITUTION_ACCOUNTS if i['username'] == username), None)
        if institution and institution['password'] == password:
            session['username'] = username
            session['user_type'] = 'institution'
            session['user_data'] = institution
            flash('Welcome to Institution Portal!', 'success')
            return redirect(url_for('institution_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('institution_login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        if not rate_limit_check(f"login_{client_ip}", max_attempts=5, window=300):
            flash('Too many login attempts. Please try again in 5 minutes.', 'danger')
            return redirect(url_for('login'))

        # Check student/admin accounts
        user = users.get(username)
        if user and check_password_hash(user['password_hash'], password):
            session['username'] = username
            session['login_time'] = time.time()
            session.permanent = True
            return redirect(url_for('dashboard'))
        
        # Check parent accounts
        parent = next((p for p in PARENT_ACCOUNTS if p['username'] == username), None)
        if parent and parent['password'] == password:
            session['username'] = username
            session['user_type'] = 'parent'
            session['user_data'] = parent
            flash('Welcome to Parent Portal!', 'success')
            return redirect(url_for('parent_dashboard'))
        
        # Check institution accounts
        institution = next((i for i in INSTITUTION_ACCOUNTS if i['username'] == username), None)
        if institution and institution['password'] == password:
            session['username'] = username
            session['user_type'] = 'institution'
            session['user_data'] = institution
            flash('Welcome to Institution Portal!', 'success')
            return redirect(url_for('institution_dashboard'))
        
        flash('Invalid credentials', 'danger')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
@require_auth
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    user_id = user['id']
    transactions = sorted(
        transactions_data.get(user_id, []),
        key=lambda x: x['date'],
        reverse=True
    )[:5]
    
    pending_invoices = [inv for inv in invoices_data.get(user_id, []) if inv['status'] == 'Pending']
    
    return render_template(
        'dashboard.html',
        user=user,
        transactions=transactions,
        invoices=pending_invoices
    )

@app.route('/make_payment', methods=['GET', 'POST'])
@require_auth
def make_payment():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            amount_str = request.form['amount'].strip()
            if not amount_str or 'nan' in amount_str.lower() or 'inf' in amount_str.lower():
                raise ValueError('Invalid amount format')
            amount = float(amount_str)
            if amount <= 0 or math.isnan(amount) or math.isinf(amount):
                raise ValueError('Amount must be positive')
        except (ValueError, TypeError) as e:
            flash('Invalid amount', 'danger')
            return redirect(url_for('make_payment'))

        if user['balance'] < amount:
            flash('Insufficient funds', 'danger')
            return redirect(url_for('make_payment'))

        # Record transaction with thread safety
        description = escape(request.form.get('description', 'Payment'))
        with data_lock:
            transaction = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'description': description,
                'amount': -amount,
                'balance': user['balance'] - amount
            }
            transactions_data[user['id']].append(transaction)
            user['balance'] -= amount

        flash('Payment successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('make_payment.html', user=user)

@app.route('/pay_invoice/<invoice_id>', methods=['GET', 'POST'])
def pay_invoice(invoice_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))

    user_id = user['id']
    invoice = next((inv for inv in invoices_data.get(user_id, []) if inv['id'] == invoice_id), None)
    
    if not invoice or invoice['status'] == 'Paid':
        flash('Invalid invoice', 'danger')
        return redirect(url_for('dashboard'))

    if user['balance'] < invoice['amount']:
        flash('Insufficient funds', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'GET':
        return render_template('confirm_payment.html', invoice=invoice, user=user)
    
    # POST request - verify passcode
    passcode = request.form.get('passcode', '').strip()
    
    # Check against user's stored passcode hash
    if not check_password_hash(user['passcode_hash'], passcode):
        flash('Invalid passcode. Please try again.', 'danger')
        return render_template('confirm_payment.html', invoice=invoice, user=user)
    
    # Record payment
    payment_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    transaction_id = str(uuid.uuid4())[:8].upper()
    
    transaction = {
        'date': payment_date,
        'description': f"Invoice Payment: {invoice['description']}",
        'amount': -invoice['amount'],
        'balance': user['balance'] - invoice['amount'],
        'transaction_id': transaction_id
    }
    transactions_data[user_id].append(transaction)
    user['balance'] -= invoice['amount']
    invoice['status'] = 'Paid'
    invoice['paid_date'] = datetime.now().strftime('%Y-%m-%d')

    # Store payment info for PDF generation
    session['last_payment'] = {
        'transaction_id': transaction_id,
        'invoice_id': invoice_id,
        'description': invoice['description'],
        'amount': invoice['amount'],
        'date': payment_date,
        'user_name': user['name'],
        'user_id': user['id']
    }
    
    # Generate and email receipt
    try:
        receipt_pdf = generate_receipt_pdf(session['last_payment'], user)
        email_sent = send_receipt_email(user['email'], user['name'], receipt_pdf, transaction_id, invoice['amount'])
        if email_sent:
            flash('Invoice paid successfully! Receipt has been emailed to you.', 'success')
        else:
            flash('Invoice paid successfully! Receipt email failed - you can download it from the dashboard.', 'warning')
    except Exception as e:
        print(f"Receipt generation/email error: {e}")
        flash('Invoice paid successfully! Receipt email failed - you can download it from the dashboard.', 'warning')

    return redirect(url_for('view_receipt'))

def generate_receipt_pdf(payment, user):
    """Generate PDF receipt and return as bytes"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    def draw_centered_text(canvas, text, y_pos, font_name, font_size):
        canvas.setFont(font_name, font_size)
        text_width = canvas.stringWidth(text, font_name, font_size)
        canvas.drawString((width - text_width) / 2, y_pos, text)
    
    # University Letterhead
    draw_centered_text(p, UNIVERSITY_NAME, height - 40, "Helvetica-Bold", 18)
    draw_centered_text(p, UNIVERSITY_SUBTITLE, height - 60, "Helvetica-Bold", 14)
    draw_centered_text(p, UNIVERSITY_ADDRESS, height - 80, "Helvetica", 12)
    
    # Title
    draw_centered_text(p, "FEE PAYMENT RECEIPT", height - 120, "Helvetica-Bold", 16)
    
    # Receipt Box
    p.rect(50, height - 500, width - 100, 350, stroke=1, fill=0)
    
    # Receipt Details
    p.setFont("Helvetica-Bold", 12)
    p.drawString(70, height - 160, f"Receipt No: FEE/{payment['transaction_id']}")
    p.drawRightString(width - 70, height - 160, f"Date: {payment['date'][:10]}")
    
    p.line(70, height - 175, width - 70, height - 175)
    
    # Student Details
    p.setFont("Helvetica-Bold", 11)
    p.drawString(70, height - 200, "STUDENT DETAILS:")
    p.setFont("Helvetica", 11)
    p.drawString(70, height - 220, f"Name: {payment['user_name']}")
    p.drawString(70, height - 240, f"Register No: {payment['user_id']}")
    p.drawString(70, height - 260, f"Course: {user.get('course', 'B.E / B.Tech')}")
    
    # Payment Details
    p.setFont("Helvetica-Bold", 11)
    p.drawString(70, height - 290, "PAYMENT DETAILS:")
    p.setFont("Helvetica", 11)
    p.drawString(70, height - 310, f"Fee Type: {payment['description']}")
    p.drawString(70, height - 330, f"Amount Paid: Rs. {payment['amount']:.2f}")
    p.drawString(70, height - 350, f"Payment Mode: Online")
    p.drawString(70, height - 370, f"Transaction ID: {payment['transaction_id']}")
    p.drawString(70, height - 390, f"Status: PAID")
    
    # Amount in words box
    p.rect(70, height - 440, width - 140, 40, stroke=1, fill=0)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(75, height - 420, "Amount in Words:")
    p.setFont("Helvetica", 10)
    amount_words = number_to_words(int(payment['amount']))
    p.drawString(75, height - 435, amount_words)
    
    # Signature section
    p.setFont("Helvetica", 10)
    p.drawString(70, height - 470, "Received the above amount towards fee payment.")
    p.drawRightString(width - 70, height - 520, "Authorized Signatory")
    p.drawRightString(width - 70, height - 535, "Accounts Section")
    
    # Footer
    p.line(50, 80, width - 50, 80)
    draw_centered_text(p, "This is a computer generated receipt and does not require signature.", 65, "Helvetica-Oblique", 9)
    draw_centered_text(p, f"For any queries, contact: {CONTACT_EMAIL} | Ph: {CONTACT_PHONE}", 50, "Helvetica-Oblique", 9)
    draw_centered_text(p, f"Visit: {WEBSITE_URL}", 35, "Helvetica-Oblique", 9)
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

def number_to_words(num):
    """Convert number to words for Indian currency"""
    if num == 0:
        return "Zero Rupees Only"
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def convert_hundreds(n):
        result = ""
        if n >= 100:
            result += ones[n // 100] + " Hundred "
            n %= 100
        if n >= 20:
            result += tens[n // 10] + " "
            n %= 10
        if n > 0:
            result += ones[n] + " "
        return result
    
    if num < 1000:
        return convert_hundreds(num).strip() + " Rupees Only"
    elif num < 100000:
        thousands = num // 1000
        remainder = num % 1000
        result = convert_hundreds(thousands).strip() + " Thousand "
        if remainder > 0:
            result += convert_hundreds(remainder).strip() + " "
        return result.strip() + " Rupees Only"
    else:
        return f"Rupees {num} Only"

@app.route('/view_receipt')
@require_auth
def view_receipt():
    user = get_current_user()
    if not user or 'last_payment' not in session:
        flash('No recent payment found', 'danger')
        return redirect(url_for('dashboard'))
    
    payment = session['last_payment']
    return render_template('receipt.html', payment=payment, user=user)

@app.route('/download_receipt')
@require_auth
def download_receipt():
    user = get_current_user()
    if not user or 'last_payment' not in session:
        flash('No recent payment found', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        payment = session['last_payment']
        
        # Create PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Helper function for centered text
        def draw_centered_text(canvas, text, y_pos, font_name, font_size):
            canvas.setFont(font_name, font_size)
            text_width = canvas.stringWidth(text, font_name, font_size)
            canvas.drawString((width - text_width) / 2, y_pos, text)
        
        # University Letterhead (centered)
        draw_centered_text(p, UNIVERSITY_NAME, height - 40, "Helvetica-Bold", 18)
        draw_centered_text(p, UNIVERSITY_SUBTITLE, height - 60, "Helvetica-Bold", 14)
        draw_centered_text(p, UNIVERSITY_ADDRESS, height - 80, "Helvetica", 12)
        
        # Title (centered)
        p.setFont("Helvetica-Bold", 16)
        text = "FEE PAYMENT RECEIPT"
        text_width = p.stringWidth(text, "Helvetica-Bold", 16)
        p.drawString((width - text_width) / 2, height - 120, text)
        
        # Receipt Box
        p.rect(50, height - 500, width - 100, 350, stroke=1, fill=0)
        
        # Receipt Number
        p.setFont("Helvetica-Bold", 12)
        p.drawString(70, height - 160, f"Receipt No: FEE/{payment['transaction_id']}")
        p.drawRightString(width - 70, height - 160, f"Date: {payment['date'][:10]}")
        
        # Horizontal line
        p.line(70, height - 175, width - 70, height - 175)
        
        # Student Details
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, height - 200, "STUDENT DETAILS:")
        p.setFont("Helvetica", 11)
        p.drawString(70, height - 220, f"Name: {payment['user_name']}")
        p.drawString(70, height - 240, f"Register No: {payment['user_id']}")
        p.drawString(70, height - 260, f"Course: B.E / B.Tech")
        
        # Payment Details
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, height - 290, "PAYMENT DETAILS:")
        p.setFont("Helvetica", 11)
        p.drawString(70, height - 310, f"Fee Type: {payment['description']}")
        p.drawString(70, height - 330, f"Amount Paid: Rs. {payment['amount']:.2f}")
        p.drawString(70, height - 350, f"Payment Mode: Online")
        p.drawString(70, height - 370, f"Transaction ID: {payment['transaction_id']}")
        p.drawString(70, height - 390, f"Status: PAID")
        
        # Amount in words box
        p.rect(70, height - 440, width - 140, 40, stroke=1, fill=0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(75, height - 420, "Amount in Words:")
        p.setFont("Helvetica", 10)
        amount_words = number_to_words(int(payment['amount']))
        p.drawString(75, height - 435, amount_words)
        
        # Signature section
        p.setFont("Helvetica", 10)
        p.drawString(70, height - 470, "Received the above amount towards fee payment.")
        p.drawRightString(width - 70, height - 520, "Authorized Signatory")
        p.drawRightString(width - 70, height - 535, "Accounts Section")
        
        # Footer (centered)
        p.line(50, 80, width - 50, 80)
        
        draw_centered_text(p, "This is a computer generated receipt and does not require signature.", 65, "Helvetica-Oblique", 9)
        draw_centered_text(p, f"For any queries, contact: {CONTACT_EMAIL} | Ph: {CONTACT_PHONE}", 50, "Helvetica-Oblique", 9)
        draw_centered_text(p, f"Visit: {WEBSITE_URL}", 35, "Helvetica-Oblique", 9)
        
        p.showPage()
        p.save()
        
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Fee_Receipt_{payment['transaction_id']}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        # Log error details server-side, show generic message to user
        print(f"Receipt generation error: {e}")
        flash('Error generating receipt. Please try again.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/parent-dashboard')
def parent_dashboard():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    parent = session['user_data']
    # Mock parent transactions
    transactions = [
        {'date': '2024-01-15 10:30:00', 'description': 'Student1 Tuition Fee Payment', 'amount': -15000, 'balance': 85000},
        {'date': '2024-01-10 14:20:00', 'description': 'Student2 Activity Fee Payment', 'amount': -12050, 'balance': 100000}
    ]
    return render_template('parent_dashboard.html', parent=parent, transactions=transactions)

@app.route('/parent-make-payment', methods=['GET', 'POST'])
def parent_make_payment():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    
    parent = session['user_data']
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            description = escape(request.form.get('description', 'Parent Payment'))
            
            # Store payment info for receipt
            session['last_payment'] = {
                'transaction_id': str(uuid.uuid4())[:8].upper(),
                'description': description,
                'amount': amount,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_name': parent['name'],
                'user_id': 'P001'
            }
            
            flash(Markup('Payment successful! <a href="/parent-download-receipt" class="alert-link">Download Receipt</a>'), 'success')
            return redirect(url_for('parent_dashboard'))
        except ValueError:
            flash('Invalid amount', 'danger')
    
    return render_template('parent_make_payment.html', parent=parent)

@app.route('/parent-payment-gateways')
def parent_payment_gateways():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    
    parent = session['user_data']
    return render_template('parent_payment_gateways.html', parent=parent)

@app.route('/parent-profile')
def parent_profile():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    
    parent = session['user_data']
    return render_template('parent_profile.html', parent=parent)

@app.route('/parent-pay-due/<child>/<fee_type>/<amount>')
def parent_pay_due(child, fee_type, amount):
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    
    try:
        amount_float = float(amount)
        
        # Store payment info for receipt
        session['last_payment'] = {
            'transaction_id': str(uuid.uuid4())[:8].upper(),
            'description': f'{child} - {fee_type}',
            'amount': amount_float,
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'user_name': session['user_data']['name'],
            'user_id': 'P001'
        }
        
        flash(Markup(f'Payment successful for {child} - {fee_type}! <a href="/parent-download-receipt" class="alert-link">Download Receipt</a>'), 'success')
        return redirect(url_for('parent_dashboard'))
    except ValueError:
        flash('Invalid payment amount', 'danger')
        return redirect(url_for('parent_dashboard'))

@app.route('/parent-download-receipt')
def parent_download_receipt():
    if 'user_type' not in session or session['user_type'] != 'parent':
        return redirect(url_for('parent_login'))
    
    if 'last_payment' not in session:
        flash('No recent payment found', 'danger')
        return redirect(url_for('parent_dashboard'))
    
    try:
        payment = session['last_payment']
        
        # Create PDF (same as student receipt)
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        def draw_centered_text(canvas, text, y_pos, font_name, font_size):
            canvas.setFont(font_name, font_size)
            text_width = canvas.stringWidth(text, font_name, font_size)
            canvas.drawString((width - text_width) / 2, y_pos, text)
        
        # University Letterhead
        draw_centered_text(p, UNIVERSITY_NAME, height - 40, "Helvetica-Bold", 18)
        draw_centered_text(p, UNIVERSITY_SUBTITLE, height - 60, "Helvetica-Bold", 14)
        draw_centered_text(p, UNIVERSITY_ADDRESS, height - 80, "Helvetica", 12)
        
        # Title
        draw_centered_text(p, "FEE PAYMENT RECEIPT", height - 120, "Helvetica-Bold", 16)
        
        # Receipt Box
        p.rect(50, height - 500, width - 100, 350, stroke=1, fill=0)
        
        # Receipt Details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(70, height - 160, f"Receipt No: FEE/{payment['transaction_id']}")
        p.drawRightString(width - 70, height - 160, f"Date: {payment['date'][:10]}")
        
        p.line(70, height - 175, width - 70, height - 175)
        
        # Parent Details
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, height - 200, "PARENT DETAILS:")
        p.setFont("Helvetica", 11)
        p.drawString(70, height - 220, f"Name: {payment['user_name']}")
        p.drawString(70, height - 240, f"Parent ID: {payment['user_id']}")
        p.drawString(70, height - 260, f"Payment Type: Parent Payment")
        
        # Payment Details
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, height - 290, "PAYMENT DETAILS:")
        p.setFont("Helvetica", 11)
        p.drawString(70, height - 310, f"Description: {payment['description']}")
        p.drawString(70, height - 330, f"Amount Paid: Rs. {payment['amount']:.2f}")
        p.drawString(70, height - 350, f"Payment Mode: Online")
        p.drawString(70, height - 370, f"Transaction ID: {payment['transaction_id']}")
        p.drawString(70, height - 390, f"Status: PAID")
        
        # Amount in words
        p.rect(70, height - 440, width - 140, 40, stroke=1, fill=0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(75, height - 420, "Amount in Words:")
        p.setFont("Helvetica", 10)
        amount_words = number_to_words(int(payment['amount']))
        p.drawString(75, height - 435, amount_words)
        
        # Signature section
        p.setFont("Helvetica", 10)
        p.drawString(70, height - 470, "Received the above amount towards fee payment.")
        p.drawRightString(width - 70, height - 520, "Authorized Signatory")
        p.drawRightString(width - 70, height - 535, "Accounts Section")
        
        # Footer
        p.line(50, 80, width - 50, 80)
        draw_centered_text(p, "This is a computer generated receipt and does not require signature.", 65, "Helvetica-Oblique", 9)
        draw_centered_text(p, f"For any queries, contact: {CONTACT_EMAIL} | Ph: {CONTACT_PHONE}", 50, "Helvetica-Oblique", 9)
        draw_centered_text(p, f"Visit: {WEBSITE_URL}", 35, "Helvetica-Oblique", 9)
        
        p.showPage()
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Parent_Receipt_{payment['transaction_id']}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Receipt generation error: {e}")
        flash('Error generating receipt. Please try again.', 'danger')
        return redirect(url_for('parent_dashboard'))

@app.route('/institution-dashboard')
def institution_dashboard():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    institution = session['user_data']
    
    # Generate daily collection data for last 7 days with realistic variations
    import random
    daily_collections = []
    today = datetime.now().date()
    base_amounts = [180000, 220000, 150000, 280000, 320000, 190000, 245000]  # Realistic daily collections
    
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        # Use base amount with some real transaction data if available
        real_total = sum(abs(t['amount']) for user_transactions in transactions_data.values() 
                        for t in user_transactions if t['date'].startswith(date.strftime('%Y-%m-%d')) and t['amount'] < 0)
        # Combine real data with base amount for demonstration
        total = base_amounts[6-i] + real_total
        daily_collections.append({'date': date.strftime('%m/%d'), 'amount': total})
    
    return render_template('institution_dashboard.html', institution=institution, daily_collections=daily_collections)

@app.route('/institution-make-payment', methods=['GET', 'POST'])
def institution_make_payment():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    institution = session['user_data']
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            description = escape(request.form.get('description', 'Institution Payment'))
            
            # Store payment info for receipt
            session['last_payment'] = {
                'transaction_id': str(uuid.uuid4())[:8].upper(),
                'description': description,
                'amount': amount,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_name': institution['name'],
                'user_id': 'INST001'
            }
            
            flash(Markup('Payment successful! <a href="/institution-download-receipt" class="alert-link">Download Receipt</a>'), 'success')
            return redirect(url_for('institution_dashboard'))
        except ValueError:
            flash('Invalid amount', 'danger')
    
    return render_template('institution_make_payment.html', institution=institution)

@app.route('/institution-payment-gateways')
def institution_payment_gateways():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    institution = session['user_data']
    return render_template('institution_payment_gateways.html', institution=institution)

@app.route('/institution-profile')
def institution_profile():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    institution = session['user_data']
    return render_template('institution_profile.html', institution=institution)

@app.route('/institution-download-receipt')
def institution_download_receipt():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    if 'last_payment' not in session:
        flash('No recent payment found', 'danger')
        return redirect(url_for('institution_dashboard'))
    
    try:
        payment = session['last_payment']
        
        # Create PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        def draw_centered_text(canvas, text, y_pos, font_name, font_size):
            canvas.setFont(font_name, font_size)
            text_width = canvas.stringWidth(text, font_name, font_size)
            canvas.drawString((width - text_width) / 2, y_pos, text)
        
        # University Letterhead
        draw_centered_text(p, UNIVERSITY_NAME, height - 40, "Helvetica-Bold", 18)
        draw_centered_text(p, UNIVERSITY_SUBTITLE, height - 60, "Helvetica-Bold", 14)
        draw_centered_text(p, UNIVERSITY_ADDRESS, height - 80, "Helvetica", 12)
        
        # Title
        draw_centered_text(p, "PAYMENT RECEIPT", height - 120, "Helvetica-Bold", 16)
        
        # Receipt Box
        p.rect(50, height - 500, width - 100, 350, stroke=1, fill=0)
        
        # Receipt Details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(70, height - 160, f"Receipt No: INST/{payment['transaction_id']}")
        p.drawRightString(width - 70, height - 160, f"Date: {payment['date'][:10]}")
        
        p.line(70, height - 175, width - 70, height - 175)
        
        # Institution Details
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, height - 200, "INSTITUTION DETAILS:")
        p.setFont("Helvetica", 11)
        p.drawString(70, height - 220, f"Name: {payment['user_name']}")
        p.drawString(70, height - 240, f"Institution ID: {payment['user_id']}")
        p.drawString(70, height - 260, f"Payment Type: Institution Payment")
        
        # Payment Details
        p.setFont("Helvetica-Bold", 11)
        p.drawString(70, height - 290, "PAYMENT DETAILS:")
        p.setFont("Helvetica", 11)
        p.drawString(70, height - 310, f"Description: {payment['description']}")
        p.drawString(70, height - 330, f"Amount Paid: Rs. {payment['amount']:.2f}")
        p.drawString(70, height - 350, f"Payment Mode: Online")
        p.drawString(70, height - 370, f"Transaction ID: {payment['transaction_id']}")
        p.drawString(70, height - 390, f"Status: PAID")
        
        # Amount in words
        p.rect(70, height - 440, width - 140, 40, stroke=1, fill=0)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(75, height - 420, "Amount in Words:")
        p.setFont("Helvetica", 10)
        amount_words = number_to_words(int(payment['amount']))
        p.drawString(75, height - 435, amount_words)
        
        # Signature section
        p.setFont("Helvetica", 10)
        p.drawString(70, height - 470, "Received the above amount towards payment.")
        p.drawRightString(width - 70, height - 520, "Authorized Signatory")
        p.drawRightString(width - 70, height - 535, "Accounts Section")
        
        # Footer
        p.line(50, 80, width - 50, 80)
        draw_centered_text(p, "This is a computer generated receipt and does not require signature.", 65, "Helvetica-Oblique", 9)
        draw_centered_text(p, f"For any queries, contact: {CONTACT_EMAIL} | Ph: {CONTACT_PHONE}", 50, "Helvetica-Oblique", 9)
        draw_centered_text(p, f"Visit: {WEBSITE_URL}", 35, "Helvetica-Oblique", 9)
        
        p.showPage()
        p.save()
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Institution_Receipt_{payment['transaction_id']}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"Receipt generation error: {e}")
        flash('Error generating receipt. Please try again.', 'danger')
        return redirect(url_for('institution_dashboard'))

@app.route('/admin-dashboard')
@require_auth
def admin_dashboard():
    user = get_current_user()
    if not user or not user.get('is_admin'):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', user=user)

@app.route('/profile')
@require_auth
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)

@app.route('/change-password', methods=['GET', 'POST'])
@require_auth
def change_password():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('change_password.html', user=user)
    
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    if not all([current_password, new_password, confirm_password]):
        flash('All fields are required', 'danger')
        return render_template('change_password.html', user=user)
    
    if not check_password_hash(user['password_hash'], current_password):
        flash('Current password is incorrect', 'danger')
        return render_template('change_password.html', user=user)
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'danger')
        return render_template('change_password.html', user=user)
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters long', 'danger')
        return render_template('change_password.html', user=user)
    
    with data_lock:
        user['password_hash'] = generate_password_hash(new_password)
        save_user_data()
    
    flash('Password changed successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/change-passcode', methods=['GET', 'POST'])
@require_auth
def change_passcode():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        return render_template('change_passcode.html', user=user)
    
    current_passcode = request.form.get('current_passcode', '')
    new_passcode = request.form.get('new_passcode', '')
    confirm_passcode = request.form.get('confirm_passcode', '')
    
    if not all([current_passcode, new_passcode, confirm_passcode]):
        flash('All fields are required', 'danger')
        return render_template('change_passcode.html', user=user)
    
    if not check_password_hash(user['passcode_hash'], current_passcode):
        flash('Current passcode is incorrect', 'danger')
        return render_template('change_passcode.html', user=user)
    
    if new_passcode != confirm_passcode:
        flash('New passcodes do not match', 'danger')
        return render_template('change_passcode.html', user=user)
    
    if len(new_passcode) != 4 or not new_passcode.isdigit():
        flash('Passcode must be exactly 4 digits', 'danger')
        return render_template('change_passcode.html', user=user)
    
    with data_lock:
        user['passcode_hash'] = generate_password_hash(new_passcode)
        save_user_data()
    
    flash('Passcode changed successfully', 'success')
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Payment gateway routes
@app.route('/payment_gateways')
def payment_gateways():
    if 'user_type' in session and session['user_type'] == 'parent':
        return redirect(url_for('parent_payment_gateways'))
    elif 'user_type' in session and session['user_type'] == 'institution':
        return redirect(url_for('institution_payment_gateways'))
    
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    
    gateways = payment_gateway.get_supported_gateways()
    return render_template('payment_gateways.html', user=user, gateways=gateways)

@app.route('/create_payment/<gateway_id>', methods=['POST'])
def create_payment(gateway_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        amount = float(request.json.get('amount', 0))
        if amount <= 0 or math.isnan(amount) or math.isinf(amount):
            return jsonify({'error': 'Invalid amount'}), 400
        
        if gateway_id == 'razorpay':
            result = payment_gateway.create_razorpay_order(amount)
        elif gateway_id == 'stripe':
            result = payment_gateway.create_stripe_payment_intent(amount)
        elif gateway_id == 'paypal':
            result = payment_gateway.create_paypal_order(amount)
        else:
            return jsonify({'error': 'Invalid gateway'}), 400
        
        return jsonify(result)
    except Exception as e:
        # Log error details server-side, show generic message to user
        print(f"Payment creation error: {e}")
        return jsonify({'error': 'Payment processing failed'}), 500

@app.route('/verify_payment', methods=['POST'])
def verify_payment():
    # Handle parent payments
    if 'user_type' in session and session['user_type'] == 'parent':
        try:
            data = request.json
            gateway = data.get('gateway')
            amount = float(data.get('amount', 0))
            
            if amount <= 0:
                return jsonify({'error': 'Invalid amount'}), 400
            
            # Store payment info for parent receipt
            session['last_payment'] = {
                'transaction_id': str(uuid.uuid4())[:8].upper(),
                'description': f'Online Payment via {gateway.title()}',
                'amount': amount,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_name': session['user_data']['name'],
                'user_id': 'P001'
            }
            
            return jsonify({'success': True, 'message': 'Payment successful'})
        except Exception as e:
            print(f"Parent payment verification error: {e}")
            return jsonify({'error': 'Payment verification failed'}), 500
    
    # Handle institution payments
    if 'user_type' in session and session['user_type'] == 'institution':
        try:
            data = request.json
            gateway = data.get('gateway')
            amount = float(data.get('amount', 0))
            
            if amount <= 0:
                return jsonify({'error': 'Invalid amount'}), 400
            
            # Store payment info for institution receipt
            session['last_payment'] = {
                'transaction_id': str(uuid.uuid4())[:8].upper(),
                'description': f'Online Payment via {gateway.title()}',
                'amount': amount,
                'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'user_name': session['user_data']['name'],
                'user_id': 'INST001'
            }
            
            return jsonify({'success': True, 'message': 'Payment successful'})
        except Exception as e:
            print(f"Institution payment verification error: {e}")
            return jsonify({'error': 'Payment verification failed'}), 500
    
    # Handle student payments
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.json
        gateway = data.get('gateway')
        
        if gateway == 'razorpay':
            result = payment_gateway.verify_razorpay_payment(
                data.get('payment_id'),
                data.get('order_id'),
                data.get('signature')
            )
        else:
            result = {'success': True}  # Simplified for other gateways
        
        if result['success']:
            # Record successful payment with validation
            amount = float(data.get('amount', 0))
            if amount <= 0 or math.isnan(amount) or math.isinf(amount):
                return jsonify({'error': 'Invalid amount'}), 400
                
            with data_lock:
                transaction = {
                    'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'description': f'Online Payment via {escape(gateway.title())}',
                    'amount': amount,
                    'balance': user['balance'] + amount,
                    'gateway': escape(gateway),
                    'payment_id': escape(data.get('payment_id', ''))
                }
                transactions_data[user['id']].append(transaction)
                user['balance'] += amount
            
            return jsonify({'success': True, 'message': 'Payment successful'})
        else:
            return jsonify({'success': False, 'error': 'Payment verification failed'})
    
    except Exception as e:
        # Log error details server-side, show generic message to user
        print(f"Payment verification error: {e}")
        return jsonify({'error': 'Payment verification failed'}), 500

@app.route('/send_reminder', methods=['POST'])
def send_reminder():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    student_id = data.get('student_id')
    message = escape(data.get('message', ''))
    target = data.get('target', 'student')
    
    if not all([student_id, message]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    reminder_id = str(uuid.uuid4())[:8]
    due_reminders[reminder_id] = {
        'student_id': student_id,
        'message': message,
        'target': target,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'sent'
    }
    
    return jsonify({'success': True, 'reminder_id': reminder_id})

@app.route('/send_bulk_reminder', methods=['POST'])
def send_bulk_reminder():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    target = data.get('target', 'students')
    message = escape(data.get('message', ''))
    message_type = data.get('message_type', 'reminder')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    count = 125 if target == 'students' else 125 if target == 'parents' else 250
    
    reminder_id = str(uuid.uuid4())[:8]
    due_reminders[reminder_id] = {
        'type': 'bulk',
        'target': target,
        'message': message,
        'message_type': message_type,
        'count': count,
        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'sent'
    }
    
    return jsonify({'success': True, 'count': count, 'reminder_id': reminder_id})

@app.route('/collection_data')
def collection_data():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    daily_collections = []
    today = datetime.now().date()
    for i in range(6, -1, -1):
        date = today - timedelta(days=i)
        total = sum(abs(t['amount']) for user_transactions in transactions_data.values() 
                   for t in user_transactions if t['date'].startswith(date.strftime('%Y-%m-%d')) and t['amount'] < 0)
        daily_collections.append({'date': date.strftime('%Y-%m-%d'), 'amount': total})
    
    return jsonify(daily_collections)

@app.route('/reminder_history')
def reminder_history():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    recent_reminders = []
    for reminder_id, reminder in due_reminders.items():
        if reminder.get('status') == 'sent':
            recent_reminders.append({
                'id': reminder_id,
                'target': reminder.get('target', 'student'),
                'message': reminder.get('message', ''),
                'date': reminder.get('created_date', ''),
                'type': reminder.get('type', 'individual')
            })
    
    return jsonify(recent_reminders[-10:])

@app.route('/student-management')
def student_management():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    # Get all students from demo accounts
    students = []
    for username, user in users.items():
        if not user.get('is_admin', False):
            # Calculate pending amount from invoices
            pending_amount = sum(inv['amount'] for inv in invoices_data.get(user['id'], []) if inv['status'] == 'Pending')
            
            students.append({
                'id': user['id'],
                'username': username,
                'name': user['name'],
                'email': user['email'],
                'phone': user.get('phone', 'N/A'),
                'course': user.get('course', 'N/A'),
                'year': user.get('year', 'N/A'),
                'balance': user['balance'],
                'pending_amount': pending_amount,
                'status': 'Overdue' if pending_amount > 0 else 'Paid',
                'parent_name': user.get('parent_name', 'N/A'),
                'parent_phone': user.get('parent_phone', 'N/A')
            })
    
    total_students = len(students)
    paid_students = len([s for s in students if s['status'] == 'Paid'])
    overdue_students = len([s for s in students if s['status'] == 'Overdue'])
    total_pending = sum(s['pending_amount'] for s in students)
    
    stats = {
        'total_students': total_students,
        'paid_students': paid_students,
        'overdue_students': overdue_students,
        'total_pending': total_pending
    }
    
    return render_template('student_management.html', students=students, stats=stats)

@app.route('/student-details/<int:student_id>')
def student_details(student_id):
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    # Find student by ID
    student = None
    for username, user in users.items():
        if user['id'] == student_id and not user.get('is_admin', False):
            student = user
            student['username'] = username
            break
    
    if not student:
        flash('Student not found', 'danger')
        return redirect(url_for('student_management'))
    
    # Get student transactions and invoices
    student_transactions = transactions_data.get(student_id, [])
    student_invoices = invoices_data.get(student_id, [])
    
    return render_template('student_details.html', student=student, 
                         transactions=student_transactions, invoices=student_invoices)

@app.route('/fee-structure')
def fee_structure():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    # Sample fee structure data
    fee_structure = {
        'B.E Computer Science': {
            '1st Year': {'tuition': 150000, 'lab': 25000, 'library': 5000, 'activity': 10000},
            '2nd Year': {'tuition': 150000, 'lab': 30000, 'library': 5000, 'activity': 12000},
            '3rd Year': {'tuition': 160000, 'lab': 35000, 'library': 5000, 'activity': 15000},
            '4th Year': {'tuition': 160000, 'lab': 40000, 'library': 5000, 'activity': 18000}
        },
        'B.E Mechanical Engineering': {
            '1st Year': {'tuition': 140000, 'lab': 20000, 'library': 5000, 'activity': 10000},
            '2nd Year': {'tuition': 140000, 'lab': 25000, 'library': 5000, 'activity': 12000},
            '3rd Year': {'tuition': 150000, 'lab': 30000, 'library': 5000, 'activity': 15000},
            '4th Year': {'tuition': 150000, 'lab': 35000, 'library': 5000, 'activity': 18000}
        }
    }
    
    return render_template('fee_structure.html', fee_structure=fee_structure_data)

@app.route('/update-fee-structure', methods=['POST'])
def update_fee_structure():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    course = data.get('course')
    year = data.get('year')
    fee_type = data.get('fee_type')
    amount = float(data.get('amount', 0))
    
    if not all([course, year, fee_type]) or amount <= 0:
        return jsonify({'error': 'Invalid data'}), 400
    
    # Update the fee structure data
    with data_lock:
        if course in fee_structure_data and year in fee_structure_data[course]:
            fee_structure_data[course][year][fee_type] = amount
            return jsonify({'success': True, 'message': f'Updated {fee_type.title()} Fee for {course} - {year} to ₹{amount:,.0f}'})
        else:
            return jsonify({'error': 'Course or year not found'}), 400

@app.route('/generate-invoice', methods=['POST'])
def generate_invoice():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    student_id = int(data.get('student_id', 0))
    fee_type = data.get('fee_type')
    amount = float(data.get('amount', 0))
    due_date = data.get('due_date')
    
    if not all([student_id, fee_type, amount, due_date]) or amount <= 0:
        return jsonify({'error': 'Invalid data'}), 400
    
    # Create new invoice
    new_invoice = {
        'id': str(uuid.uuid4()),
        'issue_date': datetime.now().strftime('%Y-%m-%d'),
        'due_date': due_date,
        'description': fee_type,
        'amount': amount,
        'status': 'Pending',
        'paid_date': None,
        'due_soon': False
    }
    
    if student_id not in invoices_data:
        invoices_data[student_id] = []
    
    invoices_data[student_id].append(new_invoice)
    
    return jsonify({'success': True, 'message': 'Invoice generated successfully', 'invoice_id': new_invoice['id'][:8]})

@app.route('/analytics')
def analytics():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    # Generate analytics data
    today = datetime.now().date()
    
    # Monthly collection data
    monthly_data = []
    for i in range(11, -1, -1):
        month_start = today.replace(day=1) - timedelta(days=i*30)
        month_name = month_start.strftime('%b %Y')
        amount = 2500000 + (i * 150000)  # Sample data
        monthly_data.append({'month': month_name, 'amount': amount})
    
    # Course-wise collection
    course_data = [
        {'course': 'B.E Computer Science', 'students': 65, 'collected': 1250000, 'pending': 150000},
        {'course': 'B.E Mechanical Engineering', 'students': 60, 'collected': 1100000, 'pending': 200000}
    ]
    
    # Payment method analysis
    payment_methods = [
        {'method': 'UPI/GPay', 'percentage': 45, 'amount': 1125000},
        {'method': 'Credit/Debit Card', 'percentage': 35, 'amount': 875000},
        {'method': 'Net Banking', 'percentage': 20, 'amount': 500000}
    ]
    
    return render_template('analytics.html', 
                         monthly_data=monthly_data, 
                         course_data=course_data, 
                         payment_methods=payment_methods)

@app.route('/settings')
def settings():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return redirect(url_for('institution_login'))
    
    institution = session['user_data']
    return render_template('settings.html', institution=institution)

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if 'user_type' not in session or session['user_type'] != 'institution':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    setting_type = data.get('type')
    value = data.get('value')
    
    # Update institution settings (in real app, this would update database)
    if setting_type == 'notification_email':
        session['user_data']['notification_email'] = value
    elif setting_type == 'late_fee_percentage':
        session['user_data']['late_fee_percentage'] = float(value)
    elif setting_type == 'payment_deadline_days':
        session['user_data']['payment_deadline_days'] = int(value)
    


@app.route('/send-support-message', methods=['POST'])
def send_support_message():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Please log in first'}), 401
    
    data = request.json
    message = data.get('message', '').strip()
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    with data_lock:
        support_messages.append({
            'id': len(support_messages) + 1,
            'user_id': user['id'],
            'user_name': user['name'],
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'unread'
        })
    
    return jsonify({'success': True, 'message': 'Message sent to admin successfully'})

@app.route('/admin-messages')
@require_auth
def admin_messages():
    user = get_current_user()
    if not user or not user.get('is_admin'):
        flash('Admin access required', 'danger')
        return redirect(url_for('login'))
    
    # Mark all messages as read
    with data_lock:
        for msg in support_messages:
            msg['status'] = 'read'
    
    return render_template('admin_messages.html', messages=support_messages, user=user)

if __name__ == '__main__':
    debug_mode = True  # Enable debug mode to see errors
    use_ssl = os.getenv('USE_SSL', 'False').lower() == 'true'
    host = '127.0.0.1'  # Bind to localhost for security
    
    if use_ssl:
        # HTTPS with self-signed certificate (for testing)
        app.run(debug=debug_mode, host=host, port=5000, ssl_context='adhoc')
    else:
        # HTTP for public WiFi compatibility
        app.run(debug=debug_mode, host=host, port=5000)