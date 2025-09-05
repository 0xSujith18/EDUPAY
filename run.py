#!/usr/bin/env python3
"""
EduPay Application Startup Script
Run this file to start the EduPay Flask application
"""

import os
import sys
from app import app

def main():
    print("=" * 50)
    print("EduPay - Student Payment System")
    print("=" * 50)
    print("Starting application...")
    print("Application ready!")
    print("Please refer to documentation for login credentials.")
    print("=" * 50)
    
    # Set environment variables
    os.environ['FLASK_DEBUG'] = 'True'
    os.environ['USE_SSL'] = 'False'  # HTTP for public WiFi compatibility
    
    try:
        # Start the application
        app.run(debug=True, host='127.0.0.1', port=5000)
    except KeyboardInterrupt:
        print("\nApplication stopped by user")
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()