from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, chat, documents, company, divisions, chatlogs, admin
from app.database.connection import db_manager

app = FastAPI(
    title="Multi-Tenant Company Chatbot API",
    description="A SaaS platform for company-specific AI chatbots using RAG and Database Integration.",
    version="1.0.0"
)

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
app.include_router(chatlogs.router)
app.include_router(admin.router)

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
