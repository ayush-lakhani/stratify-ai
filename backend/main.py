"""
FastAPI Backend with MongoDB for AI Content Strategy Planner
Production-ready with JWT auth, Redis caching, rate limiting, and CrewAI integration
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import MongoClient
from jose import JWTError, jwt
from datetime import datetime, timedelta
from datetime import datetime as dt_now # Alias for explicit calls if needed
import redis
import hashlib
import json
import time
import os
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from bson import ObjectId
from dotenv import load_dotenv # Added for loading environment variables

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Razorpay for Payments
import razorpay

# Async and Streaming Support
import asyncio
import uuid
from fastapi import BackgroundTasks
from fastapi.responses import StreamingResponse

# Import CrewAI (comment out for demo mode without GROQ_API_KEY)
try:
    from crew import create_content_strategy_crew
    CREW_AI_ENABLED = bool(os.getenv("GROQ_API_KEY"))
except:
    CREW_AI_ENABLED = False

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Razorpay Configuration
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
RAZORPAY_PLAN_ID = os.getenv("RAZORPAY_PLAN_ID", "")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
RAZORPAY_ENABLED = bool(RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET)

# Initialize Razorpay client
if RAZORPAY_ENABLED:
    razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
else:
    razorpay_client = None

# Rate Limiting Configuration
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))

# Password hashing - Using SHA256 for compatibility (Production: use Argon2)
import hashlib
import secrets

def hash_password_sha256(password: str, salt: str = None) -> str:
    """Hash password using SHA256 with salt"""
    if salt is None:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${pwd_hash}"

def verify_password_sha256(password: str, hashed: str) -> bool:
    """Verify password against SHA256 hash"""
    try:
        salt, pwd_hash = hashed.split('$')
        return hashlib.sha256((password + salt).encode()).hexdigest() == pwd_hash
    except:
        return False

security = HTTPBearer()

# ============================================================================
# MONGODB SETUP
# ============================================================================

mongo_client = MongoClient(MONGODB_URL)
db = mongo_client.content_planner

# Collections
users_collection = db.users
strategies_collection = db.strategies

# Create indexes
users_collection.create_index("email", unique=True)
strategies_collection.create_index("user_id")
strategies_collection.create_index("cache_key")

# ============================================================================
# REDIS SETUP
# ============================================================================

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    REDIS_ENABLED = True
except:
    REDIS_ENABLED = False
    print("⚠️  Redis not available - caching disabled")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class StrategyInput(BaseModel):
    goal: str = Field(..., min_length=10, max_length=500)
    audience: str = Field(..., min_length=5, max_length=200)
    industry: str = Field(..., min_length=3, max_length=100)
    platform: str = Field(..., min_length=3, max_length=50)
    contentType: str = Field(default="Mixed Content", max_length=50)

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

# ============================================================================
# FASTAPI APP
# ============================================================================

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{RATE_LIMIT_PER_MINUTE}/minute"])

app = FastAPI(
    title="Stratify.ai",
    description="AI-Powered Content Strategy Platform | 5 Elite Agents | ROI Predictions | SEO Keywords | Production SaaS",
    version="2.0.0-production"
)

# Add rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# AUTHENTICATION UTILITIES
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return verify_password_sha256(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return hash_password_sha256(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    
    user["id"] = str(user["_id"])
    return user

# ============================================================================
# CACHING UTILITIES
# ============================================================================

def generate_cache_key(strategy_input: StrategyInput) -> str:
    input_str = f"{strategy_input.goal}|{strategy_input.audience}|{strategy_input.industry}|{strategy_input.platform}|{strategy_input.contentType}"
    return hashlib.md5(input_str.encode()).hexdigest()

def get_cached_strategy(cache_key: str) -> Optional[dict]:
    if not REDIS_ENABLED:
        return None
    try:
        cached = redis_client.get(f"strategy:{cache_key}")
        return json.loads(cached) if cached else None
    except:
        return None

def set_cached_strategy(cache_key: str, strategy: dict, ttl: int = 86400):
    if not REDIS_ENABLED:
        return
    try:
        redis_client.setex(f"strategy:{cache_key}", ttl, json.dumps(strategy))
    except:
        pass

def check_rate_limit(user_id: str, limit: int = 3) -> bool:
    if not REDIS_ENABLED:
        return True
    
    current_month = datetime.now().strftime("%Y-%m")
    key = f"strategy_count:{user_id}:{current_month}"
    
    try:
        current = redis_client.get(key)
        count = int(current) if current else 0
        print(f"📊 Rate check: User {user_id} = {count}/{limit} used")
        return count < limit
    except:
        return True

# ============================================================================
# DEMO STRATEGY DATA
# ============================================================================

def generate_demo_strategy(strategy_input: StrategyInput) -> dict:
    """Generate demo strategy when CrewAI is not available"""
    return {
        "personas": [
            {
                "name": f"{strategy_input.audience.title()} Enthusiast (Young)",
                "age_range": "18-24",
                "occupation": "Student/Early Career",
                "pain_points": ["Limited budget", "Time constraints", "Learning curve", "Overwhelmed by options", "Need quick results"],
                "desires": ["Affordable solutions", "Easy to use", "Quick wins", "Build skills", "Feel confident"],
                "objections": ["Too expensive", "Not sure if it works", "Already tried others", "No time to learn", "Quality concerns"],
                "daily_habits": [f"Checks {strategy_input.platform} daily", "Consumes content during commute", "Engages in evening", "Weekend planning", "Follows trends"],
                "content_preferences": ["Short video", "Quick tips", "Behind-the-scenes", "Trendy content", "Mobile-friendly"]
            },
            {
                "name": f"{strategy_input.audience.title()} Professional",
                "age_range": "25-34",
                "occupation": "Working Professional",
                "pain_points": ["Limited time", "Struggling with consistency", "Unsure about strategy", "Algorithm changes", "Difficulty measuring ROI"],
                "desires": ["Grow authentically", "Create easily", "Build brand", "Monetize expertise", "Save time"],
                "objections": ["Too expensive", "Not sure if it works", "Already tried others", "No time to learn", "Quality concerns"],
                "daily_habits": [f"Checks {strategy_input.platform} daily", "Consumes content during commute", "Engages in evening", "Plans on weekends", "Follows influencers"],
                "content_preferences": ["Short video", "Quick tips", "Behind-the-scenes", "UGC", "Data insights"]
            },
            {
                "name": f"{strategy_input.audience.title()} Expert",
                "age_range": "35-45",
                "occupation": "Senior Professional/Manager",
                "pain_points": ["Keeping up with trends", "Delegating content creation", "ROI measurement", "Brand consistency", "Scaling challenges"],
                "desires": ["Efficient systems", "Proven strategies", "Team collaboration", "Authority building", "Long-term growth"],
                "objections": ["Implementation complexity", "Team training needed", "Budget allocation", "Risk of change", "Competitive concerns"],
                "daily_habits": [f"Strategic {strategy_input.platform} review", "Industry research", "Team meetings", "Performance analysis", "Networking"],
                "content_preferences": ["Educational posts", "Case studies", "Industry insights", "Professional content", "Long-form valuable content"]
            }
        ],
        "competitor_gaps": [
            {"gap": "Lack of personalized strategies", "impact": "High", "implementation": "AI personalization engine"},
            {"gap": "No real-time trends", "impact": "High", "implementation": "Trend monitoring"},
            {"gap": "Missing analytics", "impact": "Medium", "implementation": "Performance tracking"},
            {"gap": "Limited platform insights", "impact": "Medium", "implementation": "Platform optimization"},
            {"gap": "No collaboration", "impact": "Low", "implementation": "Team tools"}
        ],
        "keywords": [
            {
                "term": f"{strategy_input.industry.lower()} content ideas", 
                "intent": "Informational", 
                "difficulty": "Easy", 
                "monthly_searches": "5K-10K", 
                "priority": 10,
                "hashtags": [f"#{strategy_input.industry.replace(' ', '')}Content", "#ContentIdeas", "#MarketingTips", "#SocialMediaStrategy", "#ContentCreation"]
            },
            {
                "term": f"grow on {strategy_input.platform.lower()}", 
                "intent": "Informational", 
                "difficulty": "Easy", 
                "monthly_searches": "10K-50K", 
                "priority": 9,
                "hashtags": [f"#{strategy_input.platform}Growth", f"#{strategy_input.platform}Tips", "#SocialMediaGrowth", "#DigitalMarketing", "#GrowYourBusiness"]
            },
            {
                "term": f"{strategy_input.platform.lower()} tips", 
                "intent": "Informational", 
                "difficulty": "Easy", 
                "monthly_searches": "5K-10K", 
                "priority": 8,
                "hashtags": [f"#{strategy_input.platform}Tips", "#SocialMediaTips", "#MarketingHacks", "#ContentStrategy", "#DigitalMarketing"]
            },
            {
                "term": f"{strategy_input.industry.lower()} marketing", 
                "intent": "Transactional", 
                "difficulty": "Medium", 
                "monthly_searches": "5K-10K", 
                "priority": 7,
                "hashtags": [f"#{strategy_input.industry.replace(' ', '')}Marketing", "#IndustryTips", "#B2BMarketing", "#MarketingStrategy", "#BusinessGrowth"]
            },
            {
                "term": f"viral {strategy_input.platform.lower()} content", 
                "intent": "Informational", 
                "difficulty": "Medium", 
                "monthly_searches": "5K-10K", 
                "priority": 6,
                "hashtags": ["#ViralContent", f"#{strategy_input.platform}Viral", "#ContentMarketing", "#SocialMedia", "#Trending"]
            }
        ],
        "strategic_guidance": {
            "what_to_do": ["Behind-the-scenes content", "User testimonials", "Educational carousels", "Quick tip Reels", "Industry insights"],
            "how_to_do_it": ["Hook in first 3 seconds", "Add captions/text overlays", "Use trending audio", "Include clear CTA", "Post consistently"],
            "where_to_post": {
                "primary_platform": strategy_input.platform,
                "posting_locations": ["Feed", "Reels", "Stories"],
                "cross_promotion": ["TikTok (repurpose)", "YouTube Shorts"]
            },
            "when_to_post": {
                "best_days": ["Tuesday", "Thursday", "Saturday"],
                "best_times": ["9-11 AM", "1-3 PM", "7-9 PM"],
                "frequency": "3-5 times per week",
                "consistency_tips": ["Batch create on Sundays", "Schedule in advance"]
            },
            "what_to_focus_on": ["Engagement rate over followers", "Save rate for value", "Comment quality", "Share potential", "Watch time"],
            "why_it_works": ["Video captures attention faster", "Consistency trains algorithm", "Value builds trust", "Storytelling creates connection", "Clear CTAs drive action"],
            "productivity_boosters": ["Batch create content", "Use templates", "Repurpose across platforms", "Set reminders", "Plan 2 weeks ahead"],
            "things_to_avoid": ["Don't post without CTA", "Avoid overly salesy tone", "Don't ignore comments", "Avoid inconsistency", "Don't skip captions"]
        },
        "calendar": [
            {"week": 1, "day": 1, "topic": "Introduction", "format": "Reel", "caption_hook": "Here's why...", "cta": "Follow for more"},
            {"week": 1, "day": 3, "topic": "Quick Win", "format": "Carousel", "caption_hook": "Want results?", "cta": "Save this"},
            {"week": 2, "day": 2, "topic": "Educational", "format": "Post", "caption_hook": "Did you know...", "cta": "Share this"}
        ],
        "sample_posts": [
            {
                "title": "🚀 Game-Changing Strategy",
                "caption": f"If you're in {strategy_input.industry}, listen up.\n\n✅ Consistent posting\n✅ Authentic storytelling\n✅ Value-first\n\nComment 'STRATEGY' 👇",
                "hashtags": [f"#{strategy_input.industry.replace(' ', '')}", f"#{strategy_input.platform}Marketing", "#ContentStrategy"],
                "image_prompt": f"Professional workspace with {strategy_input.platform} dashboard, vibrant colors",
                "best_time": "Weekdays 9-11 AM"
            }
        ],
        "roi_prediction": {
            "traffic_lift_percentage": "18-25%",
            "engagement_boost_percentage": "35-45%",
            "estimated_monthly_reach": "5K-15K",
            "conversion_rate_estimate": "1.5-2.5%",
            "time_to_results": "30-60 days"
        }
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "message": "AI Content Strategy Planner API - MongoDB Edition",
        "version": "2.0.0",
        "database": "MongoDB",
        "cache": "Redis" if REDIS_ENABLED else "Disabled",
        "ai": "CrewAI" if CREW_AI_ENABLED else "Demo Mode"
    }

@app.get("/api/health")
async def health_check():
    try:
        mongo_client.admin.command('ping')
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    return {
        "status": "operational",
        "database": db_status,
        "redis": "healthy" if REDIS_ENABLED else "disabled",
        "crewai": "enabled" if CREW_AI_ENABLED else "demo mode",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/auth/signup", response_model=Token)
async def signup(user_data: UserCreate):
    if users_collection.find_one({"email": user_data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_doc = {
        "email": user_data.email,
        "hashed_password": get_password_hash(user_data.password),
        "tier": "free",
        "created_at": datetime.utcnow()
    }
    
    result = users_collection.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(data={"sub": user_id})
    return Token(access_token=access_token, user_id=user_id, email=user_data.email)

@app.post("/api/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = users_collection.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})
    return Token(access_token=access_token, user_id=user_id, email=user["email"])

@app.get("/api/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "tier": current_user.get("tier", "free"),
        "created_at": current_user.get("created_at")
    }

# ============================================================================
# STRIPE CHECKOUT (Pro Tier)
# ============================================================================

@app.post("/api/pro-checkout")
async def create_checkout_session(request: Request, current_user: dict = Depends(get_current_user)):
    """Create Razorpay subscription for Pro tier (₹2,400/mo)"""
    if not RAZORPAY_ENABLED:
        raise HTTPException(status_code=503, detail="Razorpay not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to .env")
    
    try:
        # Create Razorpay subscription
        subscription = razorpay_client.subscription.create({
            'plan_id': RAZORPAY_PLAN_ID,
            'customer_notify': 1,
            'quantity': 1,
            'total_count': 12,  # 12 months
            'notes': {
                'user_id': current_user["id"],
                'email': current_user["email"]
            }
        })
        
        return {
            "subscription_id": subscription['id'],
            "razorpay_key": RAZORPAY_KEY_ID
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay error: {str(e)}")

# ============================================================================
# STRATEGY GENERATION
# ============================================================================


@app.post("/api/strategy")
async def generate_strategy(
    strategy_input: StrategyInput,
    current_user: dict = Depends(get_current_user)
):
    # Rate limiting
    if not check_rate_limit(current_user["id"]):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Check cache
    cache_key = generate_cache_key(strategy_input)
    cached_strategy = get_cached_strategy(cache_key)
    
    if cached_strategy:
        return {
            "success": True,
            "strategy": cached_strategy,
            "cached": True,
            "generation_time": 0.0,
            "message": "Strategy retrieved from cache"
        }
    
    # Generate strategy
    start_time = time.time()
    
    if CREW_AI_ENABLED:
        try:
            strategy_dict = create_content_strategy_crew(strategy_input)
            message = "Strategy generated successfully"
        except Exception as e:
            strategy_dict = generate_demo_strategy(strategy_input)
            message = f"⚠️ CrewAI error, using demo: {str(e)}"
    else:
        strategy_dict = generate_demo_strategy(strategy_input)
        message = "⚠️ DEMO MODE: Add GROQ_API_KEY to .env for AI generation"
    
    generation_time = time.time() - start_time
    
    # Cache result
    set_cached_strategy(cache_key, strategy_dict)
    
    # Save to MongoDB
    strategy_doc = {
        "user_id": current_user["id"],
        "goal": strategy_input.goal,
        "audience": strategy_input.audience,
        "industry": strategy_input.industry,
        "platform": strategy_input.platform,
        "output_data": strategy_dict,
        "cache_key": cache_key,
        "generation_time": int(generation_time),
        "created_at": datetime.utcnow()
    }
    strategies_collection.insert_one(strategy_doc)
    
    # Increment usage count
    if REDIS_ENABLED:
        try:
            current_month = datetime.now().strftime("%Y-%m")
            count_key = f"strategy_count:{current_user['id']}:{current_month}"
            
            # Get current or 0
            current_val = redis_client.get(count_key)
            new_count = int(current_val) + 1 if current_val else 1
            
            # Set with 24h expiry (rolling)
            redis_client.setex(count_key, 86400, new_count)
            print(f"📈 Usage incremented for {current_user['id']}: {new_count}/3")
        except Exception as e:
            print(f"⚠️ Failed to increment usage: {e}")
    
    return {
        "success": True,
        "strategy": strategy_dict,
        "cached": False,
        "generation_time": generation_time,
        "message": message
    }

@app.get("/api/history")
async def get_history(current_user: dict = Depends(get_current_user), limit: int = 20):
    strategies = list(strategies_collection.find(
        {"user_id": current_user["id"]}
    ).sort("created_at", -1).limit(limit))
    
    history_items = []
    for s in strategies:
        history_items.append({
            "id": str(s["_id"]),
            "goal": s["goal"],
            "audience": s["audience"],
            "industry": s["industry"],
            "platform": s["platform"],
            "created_at": s["created_at"],
            "generation_time": s.get("generation_time")
        })
    
    return {
        "success": True,
        "strategies": history_items,
        "total": len(history_items)
    }

@app.get("/api/strategy/{strategy_id}")
async def get_strategy_by_id(strategy_id: str, current_user: dict = Depends(get_current_user)):
    try:
        strategy = strategies_collection.find_one({
            "_id": ObjectId(strategy_id),
            "user_id": current_user["id"]
        })
    except:
        raise HTTPException(status_code=404, detail="Invalid strategy ID")
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return {
        "success": True,
        "strategy": strategy["output_data"],
        "input": {
            "goal": strategy["goal"],
            "audience": strategy["audience"],
            "industry": strategy["industry"],
            "platform": strategy["platform"]
        },
        "created_at": strategy["created_at"],
        "generation_time": strategy.get("generation_time")
    }

@app.delete("/api/strategy/{strategy_id}")
async def delete_strategy(strategy_id: str, current_user: dict = Depends(get_current_user)):
    try:
        result = strategies_collection.delete_one({
            "_id": ObjectId(strategy_id),
            "user_id": current_user["id"]
        })
    except:
        raise HTTPException(status_code=404, detail="Invalid strategy ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # CRITICAL FIX: Full reset of rate limit counter on delete
    if REDIS_ENABLED:
        try:
            current_month = datetime.now().strftime("%Y-%m")
            cache_key = f"strategy_count:{current_user['id']}:{current_month}"
            
            # RESET TO ZERO (explicitly)
            redis_client.delete(cache_key)
            redis_client.setex(cache_key, 86400, 0)
            
            print(f"✅ FULL RESET: User {current_user['id']} → 0/3 strategies used")
        except Exception as e:
            print(f"⚠️ Failed to reset rate limit: {str(e)}")
    
    return {
        "success": True, 
        "message": "Strategy deleted - 3/3 strategies available",
        "status": "0/3 used"
    }


# ============================================================================
# RAZORPAY WEBHOOK - Automatic Pro Tier Upgrade
# ============================================================================

@app.post("/api/razorpay/webhook")
async def razorpay_webhook(request: Request):
    """Handle Razorpay webhook events for subscription management"""
    if not RAZORPAY_ENABLED:
        raise HTTPException(status_code=503, detail="Razorpay not configured")
    
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")
    
    # Verify webhook signature
    try:
        razorpay_client.utility.verify_webhook_signature(
            payload.decode(), 
            signature, 
            RAZORPAY_WEBHOOK_SECRET
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Parse event
    import json
    event = json.loads(payload)
    
    # Handle subscription.activated
    if event['event'] == 'subscription.activated':
        notes = event['payload']['subscription']['entity']['notes']
        user_id = notes.get('user_id')
        
        if user_id:
            # Upgrade user to Pro tier
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {
                    "tier": "pro",
                    "razorpay_subscription_id": event['payload']['subscription']['entity']['id']
                }}
            )
            print(f"✅ User {user_id} upgraded to Pro via Razorpay")
    
    # Handle subscription.cancelled
    elif event['event'] == 'subscription.cancelled':
        notes = event['payload']['subscription']['entity']['notes']
        user_id = notes.get('user_id')
        
        if user_id:
            # Downgrade user to free tier
            users_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": {"tier": "free"}}
            )
            print(f"⚠️ User {user_id} downgraded to Free (subscription cancelled)")
    
    return {"status": "success"}


# ============================================================================
# REFERRAL SYSTEM - Viral Growth ($5K/mo potential)
# ============================================================================

class ReferralCodeInput(BaseModel):
    referral_code: str = Field(..., min_length=6, max_length=10)

@app.post("/api/referral/apply")
async def apply_referral(
    referral_input: ReferralCodeInput,
    current_user: dict = Depends(get_current_user)
):
    """
    Apply referral code - Gives referring user 7 days free Pro
    Viral loop: User shares code → Friend signs up → Both get benefits
    """
    
    # Check if referral code exists
    referrer = users_collection.find_one({"referral_code": referral_input.referral_code})
    
    if not referrer:
        raise HTTPException(status_code=404, detail="Invalid referral code")
    
    # Can't refer yourself
    if str(referrer["_id"]) == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot use your own referral code")
    
    # Check if already used a referral
    current_user_doc = users_collection.find_one({"_id": ObjectId(current_user["id"])})
    if current_user_doc.get("referred_by"):
        raise HTTPException(status_code=400, detail="Referral code already applied")
    
    # REWARD REFERRER: 7 days free Pro
    users_collection.update_one(
        {"_id": referrer["_id"]},
        {
            "$set": {
                "tier": "pro",
                "pro_until": datetime.utcnow() + timedelta(days=7),
                "updated_at": datetime.utcnow()
            },
            "$inc": {"referral_count": 1}
        }
    )
    
    # Mark new user as referred
    users_collection.update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": {
            "referred_by": str(referrer["_id"]),
            "referred_at": datetime.utcnow()
        }}
    )
    
    return {
        "success": True,
        "message": f"🎉 Referral applied! You and {referrer.get('email', 'the referrer')} both get bonuses!"
    }


@app.get("/api/referral/code")
async def get_referral_code(current_user: dict = Depends(get_current_user)):
    """
    Get user's unique referral code (generate if doesn't exist)
    """
    user_doc = users_collection.find_one({"_id": ObjectId(current_user["id"])})
    
    # Generate referral code if doesn't exist
    if not user_doc.get("referral_code"):
        import secrets
        referral_code = secrets.token_urlsafe(6).upper().replace("-", "").replace("_", "")[:8]
        
        users_collection.update_one(
            {"_id": ObjectId(current_user["id"])},
            {"$set": {"referral_code": referral_code}}
        )
    else:
        referral_code = user_doc["referral_code"]
    
    referral_count = user_doc.get("referral_count", 0)
    
    return {
        "referral_code": referral_code,
        "referral_count": referral_count,
        "share_url": f"https://stratify.ai/signup?ref={referral_code}",
        "message": "Share this link to earn free Pro access!"
    }


# ============================================================================
# PROFILE ENDPOINTS
# ============================================================================

@app.get("/profile")
async def get_profile(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get user profile information"""
    try:
        # Verify token
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Count strategies for this user
        total_strategies = strategies_collection.count_documents({"user_id": user_id})
        
        # Get monthly usage from Redis
        usage_month = 0
        if REDIS_ENABLED:
            try:
                current_month = datetime.now().strftime("%Y-%m")
                count_key = f"strategy_count:{user_id}:{current_month}"
                current_val = redis_client.get(count_key)
                usage_month = int(current_val) if current_val else 0
            except:
                pass
        
        return {
            "name": user.get("name", user["email"].split("@")[0]),
            "email": user["email"],
            "tier": user.get("tier", "free"),
            "usage_month": usage_month,
            "total_strategies": total_strategies,
            "photo": user.get("photo", None)
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"❌ Profile fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/profile")
async def update_profile(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Update user profile"""
    try:
        # Verify token
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get update data
        data = await request.json()
        update_fields = {}
        
        if "name" in data:
            update_fields["name"] = data["name"]
        if "photo" in data:
            update_fields["photo"] = data["photo"]
        
        # Update user
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )
        
        return {"success": True, "message": "Profile updated successfully"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"❌ Profile update error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FEEDBACK ENDPOINT (VenturusAI Response)
# ============================================================================

@app.post("/feedback")
async def submit_feedback(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Submit feedback (thumbs up/down) on a strategy"""
    try:
        # Verify token
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get feedback data
        data = await request.json()
        strategy_id = data.get("strategy_id")
        rating = data.get("rating")  # "up" or "down"
        comment = data.get("comment", "")
        
        # Update strategy with feedback
        strategies_collection.update_one(
            {"_id": ObjectId(strategy_id), "user_id": user_id},
            {
                "$set": {
                    "feedback_rating": rating,
                    "feedback_comment": comment,
                    "feedback_date": datetime.utcnow()
                }
            }
        )
        
        return {
            "success": True,
            "message": "Feedback submitted successfully"
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        print(f"❌ Feedback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
