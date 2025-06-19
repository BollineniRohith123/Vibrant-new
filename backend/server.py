from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.encoders import jsonable_encoder
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, auth
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from io import BytesIO
from PIL import Image
from bson import ObjectId

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Firebase Admin SDK setup
firebase_config = {
    "type": "service_account",
    "project_id": "guruze-46446",
    "private_key_id": "dummy_key_id",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC1234567890\n-----END PRIVATE KEY-----\n",
    "client_email": "firebase-adminsdk-dummy@guruze-46446.iam.gserviceaccount.com",
    "client_id": "dummy_client_id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-dummy%40guruze-46446.iam.gserviceaccount.com"
}

# For development, we'll use a mock approach for Firebase
# In production, you'd use the actual service account key
firebase_initialized = False
try:
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred)
    firebase_initialized = True
except Exception as e:
    print(f"Firebase initialization failed: {e}")
    firebase_initialized = False

# Custom JSON Encoder for ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    
    # Convert ObjectId to string
    if '_id' in doc:
        doc['id'] = str(doc['_id'])
        del doc['_id']
    
    # Convert any other ObjectId fields
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            doc[key] = str(value)
        elif isinstance(value, list):
            doc[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
    
    return doc

# Create the main app
app = FastAPI(title="Vibrant Yoga API", version="1.0.0")
api_router = APIRouter(prefix="/api")

# Set custom JSON encoder
app.json_encoder = JSONEncoder

# Security
security = HTTPBearer()

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    firebase_id: Optional[str] = None
    name: str
    email: EmailStr
    role: str = "user"  # user or admin
    status: str = "active"  # active or suspended
    created_at: datetime = Field(default_factory=datetime.utcnow)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    booking_summary: Dict[str, Any] = Field(default_factory=dict)

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    date: str  # YYYY-MM-DD format
    time: str  # HH:MM format
    price: float
    qr_code_base64: Optional[str] = None
    upi_id: Optional[str] = None
    is_online: bool = True
    session_link: Optional[str] = None
    capacity: int = 50
    waitlist_enabled: bool = True
    delivery_mode: str = "online"  # online, offline, hybrid
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str  # admin user id

class Booking(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    event_id: str
    booking_type: str = "single"  # single, weekly, monthly
    payment_proof_base64: Optional[str] = None
    utr_number: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    admin_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None

class SMTPSettings(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    mailer_name: str = "Vibrant Yoga"
    host: str = "sveats.cyberdetox.in"
    port: int = 465
    username: str = "info@sveats.cyberdetox.in"
    email: str = "info@sveats.cyberdetox.in"
    encryption: str = "SSL"
    password: str = "Neelarani@10"

# Request/Response Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    firebase_id: Optional[str] = None

class EventCreate(BaseModel):
    title: str
    description: str
    date: str
    time: str
    price: float
    upi_id: Optional[str] = None
    is_online: bool = True
    session_link: Optional[str] = None
    capacity: int = 50
    delivery_mode: str = "online"

class BookingCreate(BaseModel):
    event_id: str
    booking_type: str = "single"
    utr_number: Optional[str] = None

class BookingUpdate(BaseModel):
    status: str
    admin_notes: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

# Utility Functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current user from JWT token"""
    try:
        token = credentials.credentials
        # For development, we'll use a simple token validation
        # In production, validate Firebase JWT token
        if token == "mock_token":
            # Return mock admin user for development
            return {
                "id": "admin_user_id",
                "email": "admin@vibrantyoga.com",
                "role": "admin",
                "name": "Admin User"
            }
        
        # Try to find user by token in database
        user = await db.users.find_one({"firebase_id": token})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    """Ensure current user is admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

async def send_email(to_email: str, subject: str, body: str):
    """Send email using SMTP settings"""
    try:
        smtp_settings = await db.smtp_settings.find_one({})
        if not smtp_settings:
            # Use default settings
            smtp_settings = SMTPSettings().dict()
        
        msg = MIMEMultipart()
        msg['From'] = smtp_settings['email']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP_SSL(smtp_settings['host'], smtp_settings['port'])
        server.login(smtp_settings['username'], smtp_settings['password'])
        server.send_message(msg)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def convert_image_to_base64(image_data: bytes) -> str:
    """Convert image bytes to base64 string"""
    try:
        image = Image.open(BytesIO(image_data))
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Image conversion failed: {e}")
        return ""

# Authentication Routes
@api_router.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Login user with email/password"""
    # For development, use mock authentication
    if request.email == "admin@vibrantyoga.com" and request.password == "admin123":
        # Create or get admin user
        admin_user = await db.users.find_one({"email": request.email})
        if not admin_user:
            admin_data = User(
                name="Admin User",
                email=request.email,
                role="admin",
                firebase_id="admin_firebase_id"
            )
            await db.users.insert_one(admin_data.dict())
            admin_user = admin_data.dict()
        
        return TokenResponse(
            access_token="mock_token",
            token_type="bearer",
            user=User(**admin_user)
        )
    
    # Check if user exists
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return TokenResponse(
        access_token="mock_token",
        token_type="bearer",
        user=User(**user)
    )

@api_router.post("/auth/google")
async def google_auth(token: str):
    """Authenticate with Google OAuth token"""
    try:
        # In production, verify Firebase token
        # For development, use mock data
        if token == "mock_google_token":
            user_data = {
                "name": "Test User",
                "email": "user@example.com",
                "firebase_id": "test_firebase_id"
            }
            
            # Check if user exists
            existing_user = await db.users.find_one({"email": user_data["email"]})
            if not existing_user:
                new_user = User(**user_data)
                await db.users.insert_one(new_user.dict())
                existing_user = new_user.dict()
            
            return TokenResponse(
                access_token="mock_token",
                token_type="bearer",
                user=User(**existing_user)
            )
        
        raise HTTPException(status_code=401, detail="Invalid Google token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

# User Routes
@api_router.get("/users/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    return User(**current_user)

@api_router.get("/users", response_model=List[User])
async def get_users(current_user: dict = Depends(get_admin_user)):
    """Get all users (admin only)"""
    users = await db.users.find().to_list(1000)
    return [User(**user) for user in users]

@api_router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str, 
    role: str,
    current_user: dict = Depends(get_admin_user)
):
    """Update user role (admin only)"""
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "User role updated successfully"}

# Event Routes
@api_router.get("/events", response_model=List[Event])
async def get_events():
    """Get all upcoming events"""
    events = await db.events.find().to_list(1000)
    return [Event(**event) for event in events]

@api_router.post("/events", response_model=Event)
async def create_event(
    event: EventCreate,
    current_user: dict = Depends(get_admin_user)
):
    """Create new event (admin only)"""
    event_data = Event(**event.dict(), created_by=current_user["id"])
    await db.events.insert_one(event_data.dict())
    return event_data

@api_router.post("/events/{event_id}/qr-code")
async def upload_qr_code(
    event_id: str,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_admin_user)
):
    """Upload QR code for event (admin only)"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Convert to base64
        qr_code_base64 = convert_image_to_base64(file_content)
        
        # Update event
        result = await db.events.update_one(
            {"id": event_id},
            {"$set": {"qr_code_base64": qr_code_base64}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Event not found")
        
        return {"message": "QR code uploaded successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File upload failed: {str(e)}")

@api_router.get("/events/{event_id}", response_model=Event)
async def get_event(event_id: str):
    """Get event by ID"""
    event = await db.events.find_one({"id": event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return Event(**event)

# Booking Routes
@api_router.post("/bookings", response_model=Booking)
async def create_booking(
    booking: BookingCreate,
    current_user: dict = Depends(get_current_user)
):
    """Create new booking"""
    # Check if event exists
    event = await db.events.find_one({"id": booking.event_id})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    booking_data = Booking(**booking.dict(), user_id=current_user["id"])
    await db.bookings.insert_one(booking_data.dict())
    
    # Send confirmation email
    await send_email(
        to_email=current_user["email"],
        subject="Booking Confirmation - Vibrant Yoga",
        body=f"""
        <h2>Booking Submitted Successfully!</h2>
        <p>Dear {current_user['name']},</p>
        <p>Your booking for "{event['title']}" has been submitted and is pending approval.</p>
        <p><strong>Event Details:</strong></p>
        <ul>
            <li>Date: {event['date']}</li>
            <li>Time: {event['time']}</li>
            <li>Price: ₹{event['price']}</li>
        </ul>
        <p>You will receive another email once your booking is approved.</p>
        <p>Thank you for choosing Vibrant Yoga!</p>
        """
    )
    
    return booking_data

@api_router.post("/bookings/{booking_id}/payment-proof")
async def upload_payment_proof(
    booking_id: str,
    file: UploadFile = File(...),
    utr_number: str = Form(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload payment proof for booking"""
    try:
        # Read file content
        file_content = await file.read()
        
        # Convert to base64
        payment_proof_base64 = convert_image_to_base64(file_content)
        
        # Update booking
        result = await db.bookings.update_one(
            {"id": booking_id, "user_id": current_user["id"]},
            {"$set": {
                "payment_proof_base64": payment_proof_base64,
                "utr_number": utr_number
            }}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Booking not found")
        
        return {"message": "Payment proof uploaded successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File upload failed: {str(e)}")

@api_router.get("/bookings", response_model=List[Booking])
async def get_bookings(current_user: dict = Depends(get_current_user)):
    """Get user's bookings"""
    if current_user["role"] == "admin":
        bookings = await db.bookings.find().to_list(1000)
    else:
        bookings = await db.bookings.find({"user_id": current_user["id"]}).to_list(1000)
    
    return [Booking(**booking) for booking in bookings]

@api_router.put("/bookings/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    update: BookingUpdate,
    current_user: dict = Depends(get_admin_user)
):
    """Update booking status (admin only)"""
    if update.status not in ["pending", "approved", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    # Get booking details
    booking = await db.bookings.find_one({"id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    # Update booking
    update_data = {"status": update.status}
    if update.admin_notes:
        update_data["admin_notes"] = update.admin_notes
    if update.status == "approved":
        update_data["approved_at"] = datetime.utcnow()
    
    await db.bookings.update_one(
        {"id": booking_id},
        {"$set": update_data}
    )
    
    # Get user and event details for email
    user = await db.users.find_one({"id": booking["user_id"]})
    event = await db.events.find_one({"id": booking["event_id"]})
    
    if user and event:
        if update.status == "approved":
            subject = "Booking Approved - Vibrant Yoga"
            body = f"""
            <h2>Booking Approved!</h2>
            <p>Dear {user['name']},</p>
            <p>Your booking for "{event['title']}" has been approved.</p>
            <p><strong>Event Details:</strong></p>
            <ul>
                <li>Date: {event['date']}</li>
                <li>Time: {event['time']}</li>
                <li>Price: ₹{event['price']}</li>
            </ul>
            """
            if event.get('is_online') and event.get('session_link'):
                body += f"<p><strong>Join Link:</strong> <a href='{event['session_link']}'>{event['session_link']}</a></p>"
            
            body += "<p>See you in class!</p>"
            
        else:  # rejected
            subject = "Booking Update - Vibrant Yoga"
            body = f"""
            <h2>Booking Update</h2>
            <p>Dear {user['name']},</p>
            <p>Your booking for "{event['title']}" requires attention.</p>
            """
            if update.admin_notes:
                body += f"<p><strong>Note:</strong> {update.admin_notes}</p>"
            
            body += "<p>Please contact us if you have any questions.</p>"
        
        await send_email(user['email'], subject, body)
    
    return {"message": "Booking status updated successfully"}

# Admin Dashboard Routes
@api_router.get("/admin/dashboard")
async def get_admin_dashboard(current_user: dict = Depends(get_admin_user)):
    """Get admin dashboard data"""
    total_users = await db.users.count_documents({})
    total_events = await db.events.count_documents({})
    total_bookings = await db.bookings.count_documents({})
    pending_bookings = await db.bookings.count_documents({"status": "pending"})
    approved_bookings = await db.bookings.count_documents({"status": "approved"})
    
    # Get recent bookings
    recent_bookings_cursor = db.bookings.find().sort("created_at", -1).limit(10)
    recent_bookings_raw = await recent_bookings_cursor.to_list(10)
    recent_bookings = [serialize_doc(booking) for booking in recent_bookings_raw]
    
    return {
        "total_users": total_users,
        "total_events": total_events,
        "total_bookings": total_bookings,
        "pending_bookings": pending_bookings,
        "approved_bookings": approved_bookings,
        "recent_bookings": recent_bookings
    }

# SMTP Settings Routes
@api_router.get("/admin/smtp-settings")
async def get_smtp_settings(current_user: dict = Depends(get_admin_user)):
    """Get SMTP settings (admin only)"""
    settings_raw = await db.smtp_settings.find_one({})
    if not settings_raw:
        # Return default settings
        return SMTPSettings().dict()
    
    settings = serialize_doc(settings_raw)
    return settings

@api_router.post("/admin/smtp-settings")
async def update_smtp_settings(
    settings: SMTPSettings,
    current_user: dict = Depends(get_admin_user)
):
    """Update SMTP settings (admin only)"""
    await db.smtp_settings.delete_many({})  # Remove old settings
    await db.smtp_settings.insert_one(settings.dict())
    return {"message": "SMTP settings updated successfully"}

# Health check
@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()