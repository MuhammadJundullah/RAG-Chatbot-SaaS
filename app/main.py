from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, chat, documents, divisions, company, permissions
from app.database.connection import db_manager

app = FastAPI(
    title="Multi-Tenant Company Chatbot API",
    description="A SaaS platform for company-specific AI chatbots using RAG and Database Integration.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with a common prefix
app.include_router(auth.router, prefix="/api/v1", tags=["Authentication & Registration"])
app.include_router(chat.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(divisions.router, prefix="/api/v1")
app.include_router(company.router, prefix="/api/v1", tags=["Company Management"])
app.include_router(permissions.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    await db_manager.connect()
    print("Database connected")

@app.on_event("shutdown")
async def shutdown_event():
    await db_manager.close()
    print("Database disconnected")

@app.get("/")
async def root():
    return {"message": "Multi-Tenant Company Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}