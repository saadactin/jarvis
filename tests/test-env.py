#!/usr/bin/env python3
"""Test if .env file can be parsed correctly"""

from dotenv import load_dotenv
import os

try:
    load_dotenv()
    print("SUCCESS: .env file parsed successfully!")
    print(f"\nDATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:60]}...")
    print(f"PORT: {os.getenv('PORT', 'NOT SET')}")
    print(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'NOT SET')}")
    print("\nSUCCESS: No parsing errors found!")
except Exception as e:
    print(f"ERROR: Error parsing .env file: {e}")

