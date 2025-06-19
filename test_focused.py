#!/usr/bin/env python3
import requests
import json
import base64
from datetime import datetime
import time
from io import BytesIO
from PIL import Image

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://c8da5de4-4960-4f68-9c58-a71486a51e17.preview.emergentagent.com/api"

def create_test_image(size=(200, 200), color=(0, 0, 0)):
    """Create a test image for QR code and payment proof uploads"""
    image = Image.new('RGB', size, color=color)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

def test_admin_dashboard():
    """Test admin dashboard endpoint"""
    print("\n=== Testing Admin Dashboard ===")
    
    # Initialize admin user
    print("Initializing admin user...")
    response = requests.post(f"{BACKEND_URL}/admin/init")
    print(f"Admin initialization: {response.json()}")
    
    # Login as admin
    print("\nLogging in as admin...")
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": "admin@vibrantyoga.com", "password": "admin123"}
    )
    
    if response.status_code != 200:
        print(f"Admin login failed: {response.status_code} - {response.text}")
        return
    
    admin_data = response.json()
    admin_token = admin_data["access_token"]
    print(f"Admin login successful - Token: {admin_token[:10]}...")
    
    # Test admin dashboard
    print("\nTesting admin dashboard...")
    response = requests.get(
        f"{BACKEND_URL}/admin/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error response: {response.text}")
        return
    
    dashboard_data = response.json()
    print("Admin dashboard data:")
    print(f"- Total users: {dashboard_data['total_users']}")
    print(f"- Total events: {dashboard_data['total_events']}")
    print(f"- Total bookings: {dashboard_data['total_bookings']}")
    print(f"- Pending bookings: {dashboard_data['pending_bookings']}")
    print(f"- Approved bookings: {dashboard_data['approved_bookings']}")
    print(f"- Total revenue: ₹{dashboard_data['total_revenue']}")
    print(f"- Recent bookings: {len(dashboard_data['recent_bookings'])}")
    
    print("\n✅ Admin dashboard test passed!")

def test_smtp_settings():
    """Test SMTP settings endpoints"""
    print("\n=== Testing SMTP Settings ===")
    
    # Login as admin
    print("Logging in as admin...")
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": "admin@vibrantyoga.com", "password": "admin123"}
    )
    
    if response.status_code != 200:
        print(f"Admin login failed: {response.status_code} - {response.text}")
        return
    
    admin_data = response.json()
    admin_token = admin_data["access_token"]
    print(f"Admin login successful - Token: {admin_token[:10]}...")
    
    # Test get SMTP settings
    print("\nTesting get SMTP settings...")
    response = requests.get(
        f"{BACKEND_URL}/admin/smtp-settings",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error response: {response.text}")
        return
    
    smtp_data = response.json()
    print("SMTP settings data:")
    print(f"- Host: {smtp_data['host']}")
    print(f"- Port: {smtp_data['port']}")
    print(f"- Username: {smtp_data['username']}")
    print(f"- Email: {smtp_data['email']}")
    
    # Test update SMTP settings
    print("\nTesting update SMTP settings...")
    new_smtp_data = {
        "id": smtp_data.get("id", "new_settings_id"),
        "mailer_name": "Vibrant Yoga Test",
        "host": "smtp.example.com",
        "port": 587,
        "username": "test@example.com",
        "email": "test@example.com",
        "encryption": "TLS",
        "password": "test_password"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/admin/smtp-settings",
        json=new_smtp_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error response: {response.text}")
        return
    
    print("\n✅ SMTP settings test passed!")

def test_pricing_system():
    """Test the pricing system with daily/weekly/monthly options"""
    print("\n=== Testing Pricing System ===")
    
    # Login as admin
    print("Logging in as admin...")
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"email": "admin@vibrantyoga.com", "password": "admin123"}
    )
    
    if response.status_code != 200:
        print(f"Admin login failed: {response.status_code} - {response.text}")
        return
    
    admin_data = response.json()
    admin_token = admin_data["access_token"]
    print(f"Admin login successful - Token: {admin_token[:10]}...")
    
    # Register a test user
    print("\nRegistering test user...")
    user_email = f"testuser_{int(time.time())}@example.com"
    user_password = "Password123!"
    
    response = requests.post(
        f"{BACKEND_URL}/auth/register",
        json={
            "name": "Test User",
            "email": user_email,
            "password": user_password
        }
    )
    
    if response.status_code != 200:
        print(f"User registration failed: {response.status_code} - {response.text}")
        return
    
    user_data = response.json()
    user_token = user_data["access_token"]
    print(f"User registration successful - Token: {user_token[:10]}...")
    
    # Create an event with pricing tiers
    print("\nCreating event with pricing tiers...")
    event_data = {
        "title": "Morning Hatha Yoga",
        "description": "Relaxing yoga session for beginners",
        "date": "2025-06-25",
        "time": "08:00",
        "daily_price": 500,
        "weekly_price": 2000,
        "monthly_price": 6000,
        "delivery_mode": "online",
        "capacity": 25,
        "session_link": "https://zoom.us/j/123456789"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/events",
        json=event_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code != 200:
        print(f"Event creation failed: {response.status_code} - {response.text}")
        return
    
    event_data = response.json()
    event_id = event_data["id"]
    print(f"Event created successfully - ID: {event_id}")
    print(f"Pricing tiers: Daily: ₹{event_data['pricing']['daily']}, Weekly: ₹{event_data['pricing']['weekly']}, Monthly: ₹{event_data['pricing']['monthly']}")
    
    # Create daily booking
    print("\nCreating daily booking...")
    booking_data = {
        "event_id": event_id,
        "booking_type": "daily"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/bookings",
        json=booking_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code != 200:
        print(f"Daily booking creation failed: {response.status_code} - {response.text}")
        return
    
    daily_booking = response.json()
    print(f"Daily booking created successfully - ID: {daily_booking['id']}")
    print(f"Amount: ₹{daily_booking['amount']}")
    
    # Create weekly booking
    print("\nCreating weekly booking...")
    booking_data = {
        "event_id": event_id,
        "booking_type": "weekly"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/bookings",
        json=booking_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code != 200:
        print(f"Weekly booking creation failed: {response.status_code} - {response.text}")
        return
    
    weekly_booking = response.json()
    print(f"Weekly booking created successfully - ID: {weekly_booking['id']}")
    print(f"Amount: ₹{weekly_booking['amount']}")
    
    # Create monthly booking
    print("\nCreating monthly booking...")
    booking_data = {
        "event_id": event_id,
        "booking_type": "monthly"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/bookings",
        json=booking_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code != 200:
        print(f"Monthly booking creation failed: {response.status_code} - {response.text}")
        return
    
    monthly_booking = response.json()
    print(f"Monthly booking created successfully - ID: {monthly_booking['id']}")
    print(f"Amount: ₹{monthly_booking['amount']}")
    
    # Verify pricing is correct
    assert daily_booking['amount'] == event_data['pricing']['daily'], "Daily pricing mismatch"
    assert weekly_booking['amount'] == event_data['pricing']['weekly'], "Weekly pricing mismatch"
    assert monthly_booking['amount'] == event_data['pricing']['monthly'], "Monthly pricing mismatch"
    
    print("\n✅ Pricing system test passed!")

if __name__ == "__main__":
    print("=== Starting Vibrant Yoga Backend API Tests ===")
    
    # Test admin dashboard
    test_admin_dashboard()
    
    # Test SMTP settings
    test_smtp_settings()
    
    # Test pricing system
    test_pricing_system()
    
    print("\n=== All tests completed ===")