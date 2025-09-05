# Configuration constants for EduPay application

# University Information
UNIVERSITY_NAME = "Anna University"
UNIVERSITY_SUBTITLE = "(Affiliated to Anna University)"
UNIVERSITY_ADDRESS = "Chennai - 600 025"
CONTACT_EMAIL = "accounts@annauniv.edu"
CONTACT_PHONE = "+91-44-22351723"
WEBSITE_URL = "www.annauniv.edu"

# Application Settings
DEFAULT_PASSCODE = "1234"
SESSION_TIMEOUT_MINUTES = 30
RATE_LIMIT_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 300  # 5 minutes

# Payment Settings
SUPPORTED_CURRENCIES = ["INR", "USD"]
MIN_PAYMENT_AMOUNT = 1.0
MAX_PAYMENT_AMOUNT = 1000000.0

# Security Settings
BCRYPT_LOG_ROUNDS = 12
SECRET_KEY_LENGTH = 32

# File Paths
SECRET_KEY_FILE = ".secret_key"
LOG_FILE = "edupay.log"

# Demo Mode Settings (for development only)
DEMO_MODE = True
DEMO_ACCOUNTS_ENABLED = True