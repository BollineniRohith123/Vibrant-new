#!/usr/bin/env python3
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
import uuid
from datetime import datetime

async def init_admin():
    # MongoDB connection
    mongo_url = "mongodb://localhost:27017"
    client = AsyncIOMotorClient(mongo_url)
    db = client["test_database"]
    
    # Hash password
    password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create admin user
    admin_data = {
        "id": str(uuid.uuid4()),
        "name": "Admin User",
        "email": "admin@vibrantyoga.com",
        "password_hash": password_hash,
        "role": "admin",
        "status": "active",
        "created_at": datetime.utcnow(),
        "preferences": {},
        "booking_summary": {}
    }
    
    # Delete existing admin user
    await db.users.delete_many({"email": "admin@vibrantyoga.com"})
    
    # Insert new admin user
    result = await db.users.insert_one(admin_data)
    
    print(f"Admin user created with ID: {admin_data['id']}")
    print(f"Password hash: {password_hash}")

if __name__ == "__main__":
    asyncio.run(init_admin())