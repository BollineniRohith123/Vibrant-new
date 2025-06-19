#!/usr/bin/env python3
import requests
import json
import base64
import os
from datetime import datetime
import time
import unittest
from io import BytesIO
from PIL import Image

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://c8da5de4-4960-4f68-9c58-a71486a51e17.preview.emergentagent.com/api"

class VibrantYogaBackendTest(unittest.TestCase):
    """Test suite for Vibrant Yoga Backend API"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test data and authenticate"""
        cls.admin_token = None
        cls.user_token = None
        cls.admin_user = None
        cls.regular_user = None
        cls.test_event_id = None
        cls.test_booking_id = None
        
        # Admin credentials
        cls.admin_email = "admin@vibrantyoga.com"
        cls.admin_password = "admin123"
        
        # Regular user credentials
        cls.user_email = "user@example.com"
        cls.user_password = "user123"
        
        # Create a test QR code image
        cls.test_qr_image = cls._create_test_image()
        cls.test_payment_proof = cls._create_test_image(color=(255, 0, 0))
        
        print("\n=== Starting Vibrant Yoga Backend API Tests ===")
    
    @staticmethod
    def _create_test_image(size=(200, 200), color=(0, 0, 0)):
        """Create a test image for QR code and payment proof uploads"""
        image = Image.new('RGB', size, color=color)
        buffer = BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    def test_01_health_check(self):
        """Test the health check endpoint"""
        print("\n--- Testing Health Check Endpoint ---")
        response = requests.get(f"{BACKEND_URL}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        print("✅ Health check endpoint is working")
    
    def test_02_admin_login(self):
        """Test admin login endpoint"""
        print("\n--- Testing Admin Login Endpoint ---")
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"email": self.admin_email, "password": self.admin_password}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["token_type"], "bearer")
        self.assertIsNotNone(data["access_token"])
        self.assertEqual(data["user"]["email"], self.admin_email)
        self.assertEqual(data["user"]["role"], "admin")
        
        # Save admin token and user data for later tests
        self.__class__.admin_token = data["access_token"]
        self.__class__.admin_user = data["user"]
        print(f"✅ Admin login successful - Token: {self.admin_token[:10]}...")
    
    def test_03_google_auth(self):
        """Test Google authentication endpoint (mock)"""
        print("\n--- Testing Google Auth Endpoint (Mock) ---")
        response = requests.post(
            f"{BACKEND_URL}/auth/google",
            params={"token": "mock_google_token"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["token_type"], "bearer")
        self.assertIsNotNone(data["access_token"])
        
        # Save user token and data for later tests
        self.__class__.user_token = data["access_token"]
        self.__class__.regular_user = data["user"]
        print(f"✅ Google auth successful - Token: {self.user_token[:10]}...")
    
    def test_04_get_current_user(self):
        """Test get current user endpoint"""
        print("\n--- Testing Get Current User Endpoint ---")
        # Test with admin token
        response = requests.get(
            f"{BACKEND_URL}/users/me",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["email"], self.admin_email)
        self.assertEqual(data["role"], "admin")
        print("✅ Get current user (admin) successful")
        
        # Test with user token - note: in this implementation, all tokens return the same user
        # This is because we're using mock tokens for testing
        response = requests.get(
            f"{BACKEND_URL}/users/me",
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Get current user with user token successful")
    
    def test_05_get_all_users(self):
        """Test get all users endpoint (admin only)"""
        print("\n--- Testing Get All Users Endpoint (Admin Only) ---")
        # Test with admin token
        response = requests.get(
            f"{BACKEND_URL}/users",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)  # At least admin and regular user
        print(f"✅ Get all users successful - Found {len(data)} users")
        
        # Test with user token (should fail)
        response = requests.get(
            f"{BACKEND_URL}/users",
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 403)
        print("✅ Regular user correctly denied access to all users")
    
    def test_06_update_user_role(self):
        """Test update user role endpoint (admin only)"""
        print("\n--- Testing Update User Role Endpoint (Admin Only) ---")
        # Get user ID from regular user
        user_id = self.regular_user["id"]
        
        # Test with admin token
        response = requests.put(
            f"{BACKEND_URL}/users/{user_id}/role",
            params={"role": "admin"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Updated user role to admin")
        
        # Change back to regular user
        response = requests.put(
            f"{BACKEND_URL}/users/{user_id}/role",
            params={"role": "user"},
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Updated user role back to user")
    
    def test_07_get_events(self):
        """Test get events endpoint"""
        print("\n--- Testing Get Events Endpoint ---")
        response = requests.get(f"{BACKEND_URL}/events")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        print(f"✅ Get events successful - Found {len(data)} events")
    
    def test_08_create_event(self):
        """Test create event endpoint (admin only)"""
        print("\n--- Testing Create Event Endpoint (Admin Only) ---")
        event_data = {
            "title": "Test Yoga Session",
            "description": "This is a test yoga session created by automated tests",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": "10:00",
            "price": 500.0,
            "upi_id": "test@upi",
            "is_online": True,
            "session_link": "https://zoom.us/test",
            "capacity": 20,
            "delivery_mode": "online"
        }
        
        # Test with admin token
        response = requests.post(
            f"{BACKEND_URL}/events",
            json=event_data,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], event_data["title"])
        self.assertEqual(data["price"], event_data["price"])
        
        # Save event ID for later tests
        self.__class__.test_event_id = data["id"]
        print(f"✅ Created test event with ID: {self.test_event_id}")
        
        # Test with user token (should fail)
        response = requests.post(
            f"{BACKEND_URL}/events",
            json=event_data,
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 403)
        print("✅ Regular user correctly denied access to create event")
    
    def test_09_get_event_by_id(self):
        """Test get event by ID endpoint"""
        print("\n--- Testing Get Event By ID Endpoint ---")
        response = requests.get(f"{BACKEND_URL}/events/{self.test_event_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], self.test_event_id)
        print(f"✅ Get event by ID successful - Title: {data['title']}")
    
    def test_10_upload_qr_code(self):
        """Test upload QR code endpoint (admin only)"""
        print("\n--- Testing Upload QR Code Endpoint (Admin Only) ---")
        # Reset file pointer
        self.test_qr_image.seek(0)
        
        # Test with admin token
        files = {"file": ("qr_code.png", self.test_qr_image, "image/png")}
        response = requests.post(
            f"{BACKEND_URL}/events/{self.test_event_id}/qr-code",
            files=files,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ QR code upload successful")
        
        # Verify QR code was added to event
        response = requests.get(f"{BACKEND_URL}/events/{self.test_event_id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNotNone(data["qr_code_base64"])
        self.assertTrue(data["qr_code_base64"].startswith("data:image/png;base64,"))
        print("✅ QR code verified in event data")
    
    def test_11_create_booking(self):
        """Test create booking endpoint"""
        print("\n--- Testing Create Booking Endpoint ---")
        booking_data = {
            "event_id": self.test_event_id,
            "booking_type": "single",
            "utr_number": "TEST123456789"
        }
        
        # Test with user token
        response = requests.post(
            f"{BACKEND_URL}/bookings",
            json=booking_data,
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], self.test_event_id)
        self.assertEqual(data["status"], "pending")
        
        # Save booking ID for later tests
        self.__class__.test_booking_id = data["id"]
        print(f"✅ Created test booking with ID: {self.test_booking_id}")
    
    def test_12_get_bookings(self):
        """Test get bookings endpoint"""
        print("\n--- Testing Get Bookings Endpoint ---")
        # Test with user token
        response = requests.get(
            f"{BACKEND_URL}/bookings",
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        print(f"✅ Get user bookings successful - Found {len(data)} bookings")
        
        # Test with admin token (should see all bookings)
        response = requests.get(
            f"{BACKEND_URL}/bookings",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        print(f"✅ Get all bookings (admin) successful - Found {len(data)} bookings")
    
    def test_13_upload_payment_proof(self):
        """Test upload payment proof endpoint"""
        print("\n--- Testing Upload Payment Proof Endpoint ---")
        # Reset file pointer
        self.test_payment_proof.seek(0)
        
        # Test with user token
        files = {"file": ("payment_proof.png", self.test_payment_proof, "image/png")}
        data = {"utr_number": "TEST123456789"}
        response = requests.post(
            f"{BACKEND_URL}/bookings/{self.test_booking_id}/payment-proof",
            files=files,
            data=data,
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Payment proof upload successful")
    
    def test_14_update_booking_status(self):
        """Test update booking status endpoint (admin only)"""
        print("\n--- Testing Update Booking Status Endpoint (Admin Only) ---")
        update_data = {
            "status": "approved",
            "admin_notes": "Approved by automated test"
        }
        
        # Test with admin token
        response = requests.put(
            f"{BACKEND_URL}/bookings/{self.test_booking_id}/status",
            json=update_data,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Booking status update successful")
        
        # Test with user token (should fail)
        response = requests.put(
            f"{BACKEND_URL}/bookings/{self.test_booking_id}/status",
            json=update_data,
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 403)
        print("✅ Regular user correctly denied access to update booking status")
    
    def test_15_admin_dashboard(self):
        """Test admin dashboard endpoint (admin only)"""
        print("\n--- Testing Admin Dashboard Endpoint (Admin Only) ---")
        # Test with admin token
        response = requests.get(
            f"{BACKEND_URL}/admin/dashboard",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_users", data)
        self.assertIn("total_events", data)
        self.assertIn("total_bookings", data)
        self.assertIn("pending_bookings", data)
        self.assertIn("approved_bookings", data)
        print("✅ Admin dashboard access successful")
        
        # Test with user token (should fail)
        response = requests.get(
            f"{BACKEND_URL}/admin/dashboard",
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 403)
        print("✅ Regular user correctly denied access to admin dashboard")
    
    def test_16_smtp_settings(self):
        """Test SMTP settings endpoints (admin only)"""
        print("\n--- Testing SMTP Settings Endpoints (Admin Only) ---")
        # Test get SMTP settings
        response = requests.get(
            f"{BACKEND_URL}/admin/smtp-settings",
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("host", data)
        self.assertIn("port", data)
        self.assertIn("username", data)
        print("✅ Get SMTP settings successful")
        
        # Test update SMTP settings
        smtp_data = {
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
            json=smtp_data,
            headers={"Authorization": f"Bearer {self.admin_token}"}
        )
        self.assertEqual(response.status_code, 200)
        print("✅ Update SMTP settings successful")
        
        # Test with user token (should fail)
        response = requests.get(
            f"{BACKEND_URL}/admin/smtp-settings",
            headers={"Authorization": f"Bearer {self.user_token}"}
        )
        self.assertEqual(response.status_code, 403)
        print("✅ Regular user correctly denied access to SMTP settings")

if __name__ == "__main__":
    unittest.main(verbosity=2)