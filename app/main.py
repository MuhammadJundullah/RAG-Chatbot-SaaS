from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.auth.api import router as auth_router
from app.modules.chat.api import router as chat_router
from app.modules.documents.api import router as documents_router
from app.modules.company.api import router as company_router
from app.modules.chatlogs.api import user_router as chatlogs_user_router, admin_router as chatlogs_admin_router, company_admin_router as chatlogs_company_admin_router
from app.modules.admin.api import router as admin_router
from app.modules.dashboard.api import router as dashboard_router
from app.modules.subscription.api import router as subscription_router
from app.modules.payment.api import router as payment_router
from app.core.database import db_manager
from app.utils.activity_logger import log_activity 
from app.core.dependencies import get_db 
from app.core.global_error_handler import register_global_exception_handlers 
from app.core.config import settings

# No complex lifespan needed with gevent and simple singleton initialization
app = FastAPI(
    title="Multi-Tenant Company Chatbot API",
    description="A SaaS platform for company-specific AI chatbots using RAG and Database Integration.",
    version="1.0.0"
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
# Register global exception handlers
register_global_exception_handlers(app) 

# The RAGService, S3Client, and DBEngine are initialized on import now.
@app.on_event("shutdown")
async def shutdown_event():
    """Close database connections on shutdown."""
    await db_manager.close()
    print("Database engine closed.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://smart-ai-frontend-wine.vercel.app", "https://145.79.15.190", "https://smart-ai.rf.gd"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(company_router, prefix="/api")
app.include_router(chatlogs_user_router, prefix="/api")
app.include_router(chatlogs_admin_router, prefix="/api")
app.include_router(chatlogs_company_admin_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(subscription_router, prefix="/api")
app.include_router(payment_router, prefix="/api")

@app.get("/api/")
async def root():
    return {"message": "Multi-Tenant Company Chatbot API is running"}

@app.get("/api/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    # For health checks, user_id and company_id might be unknown or N/A

    return {"status": "sehat bwang"}
