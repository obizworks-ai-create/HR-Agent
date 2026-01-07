from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from routers.api import router as api_router
from routers.dashboard import router as dashboard_router
from routers.interview import router as interview_router

load_dotenv()

app = FastAPI(title="HR Hiring Pipeline API")

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://candidate-intelligence-platform.vercel.app", # Vercel Placeholder
    "*", # Allow all for now to avoid CORS headaches during setup
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- AUTH MIDDLEWARE ---
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Public Routes (No Password Needed)
        # 1. Root / Health check
        # 2. Interview Routes (Candidates must access these freely)
        # 3. Docs / OpenAPI (Optional, but good for debug)
        path = request.url.path
        if (path == "/" or 
            path.startswith("/api/interview") or 
            path.startswith("/docs") or 
            path.startswith("/openapi.json") or
            request.method == "OPTIONS"): # Allow CORS preflight
            return await call_next(request)
        
        # Check for Admin Password
        admin_pass = os.getenv("ADMIN_PASSWORD")
        if not admin_pass:
            # If no password set in env, allow access (Dev mode)
            return await call_next(request)
            
        client_pass = request.headers.get("x-admin-password")
        if client_pass != admin_pass:
            return Response(content="Unauthorized: Missing or Invalid Admin Password", status_code=401)
            
        return await call_next(request)

app.add_middleware(AuthMiddleware)

app.include_router(api_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api", tags=["dashboard"])
app.include_router(interview_router, prefix="/api/interview", tags=["interview"])

@app.get("/")
def read_root():
    return {"message": "HR Pipeline API is running"}
