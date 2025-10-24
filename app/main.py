from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import auth, chat, documents, company, divisions, chatlogs, admin
from app.core.database import db_manager

# No complex lifespan needed with gevent and simple singleton initialization
app = FastAPI(
    title="Multi-Tenant Company Chatbot API",
    description="A SaaS platform for company-specific AI chatbots using RAG and Database Integration.",
    version="1.0.0"
)

# The RAGService, S3Client, and DBEngine are initialized on import now.

@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    await db_manager.close()
    print("Database engine closed.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(company.router)
app.include_router(divisions.router)
app.include_router(chatlogs.user_router)
app.include_router(chatlogs.admin_router)
app.include_router(chatlogs.company_admin_router)
app.include_router(admin.router)

@app.get("/")
async def root():
    return {"message": "Multi-Tenant Company Chatbot API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}