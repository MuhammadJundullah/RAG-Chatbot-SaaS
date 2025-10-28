# RAG Chatbot SaaS - Multi-Tenant AI Platform

A SaaS platform for company-specific AI chatbots using RAG (Retrieval-Augmented Generation) with document processing and multi-tenant architecture.

## 🚀 Features

- **Multi-Tenant Architecture**: Isolated data per company
- **RAG-Powered Chat**: AI responses based on company documents
- **OCR Processing**: Automatic text extraction from documents
- **Role-Based Access**: Super Admin, Company Admin, and User roles
- **Document Management**: Upload, validate, and manage documents
- **Conversation History**: Track and retrieve chat logs

## 📋 Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy
- **Vector Store**: Pinecone
- **Storage**: AWS S3
- **Task Queue**: Celery with Redis
- **AI**: Google Gemini

## 🔧 Installation

```bash
# Clone repository
git clone <repository-url>
cd RAG-Chatbot-SaaS

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your credentials

# Run migrations
alembic upgrade head

# Start application
uvicorn app.main:app --reload

# Start Celery worker (separate terminal)
celery -A app.core.celery_app worker --loglevel=info
```

## 📚 API Documentation

### Authentication

#### Register Company
```http
POST /api/auth/register
Content-Type: application/json

{
  "name": "John Doe",
  "email": "admin@company.com",
  "password": "secure123",
  "company_name": "Tech Corp",
  "username": "johndoe",
  "pic_phone_number": "+1234567890"
}

Response: 201 Created
{
  "message": "Company 'Tech Corp' and admin user 'admin@company.com' registered successfully. Pending approval from a super admin."
}
```

#### Login
```http
POST /api/auth/user/token
Content-Type: application/json

{
  "email": "admin@company.com",
  "username": "johndoe",
  "password": "secure123"
}

Response: 200 OK
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "email": "admin@company.com",
    "role": "admin",
    "company_id": 1
  }
}
```

#### Get Current User
```http
GET /api/auth/me
Authorization: Bearer <token>

Response: 200 OK
{
  "id": 1,
  "email": "admin@company.com",
  "name": "John Doe",
  "role": "admin",
  "company_id": 1
}
```

---

### Super Admin

#### List Pending Companies
```http
GET /api/admin/companies/pending?skip=0&limit=100
Authorization: Bearer <super_admin_token>

Response: 200 OK
[
  {
    "id": 1,
    "name": "Tech Corp",
    "is_active": false,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Approve Company
```http
PATCH /api/admin/companies/{company_id}/approve
Authorization: Bearer <super_admin_token>

Response: 200 OK
{
  "message": "Company with id 1 has been approved."
}
```

#### Reject Company
```http
PATCH /api/admin/companies/{company_id}/reject
Authorization: Bearer <super_admin_token>

Response: 200 OK
{
  "message": "Company with id 1 has been rejected and deleted."
}
```

---

### Company Management

#### List Company Users
```http
GET /api/companies/users
Authorization: Bearer <admin_token>

Response: 200 OK
[
  {
    "id": 1,
    "email": "user@company.com",
    "name": "Jane Smith",
    "role": "user",
    "division_id": 1
  }
]
```

#### Get My Company
```http
GET /api/companies/me
Authorization: Bearer <admin_token>

Response: 200 OK
{
  "id": 1,
  "name": "Tech Corp",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00"
}
```

#### Register Employee
```http
POST /api/companies/employees/register
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Jane Smith",
  "email": "jane@company.com",
  "password": "secure123",
  "username": "janesmith",
  "division_id": 1
}

Response: 201 Created
{
  "id": 2,
  "email": "jane@company.com",
  "name": "Jane Smith",
  "role": "user",
  "company_id": 1
}
```

---

### Divisions

#### Create Division
```http
POST /api/divisions
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Engineering"
}

Response: 200 OK
{
  "id": 1,
  "name": "Engineering",
  "company_id": 1
}
```

#### List Divisions
```http
GET /api/divisions
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "id": 1,
    "name": "Engineering",
    "company_id": 1
  }
]
```

---

### Documents

#### Upload Document
```http
POST /api/documents/upload
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data

file: <binary>

Response: 202 Accepted
{
  "id": 1,
  "title": "company_policy.pdf",
  "status": "UPLOADED",
  "company_id": 1,
  "storage_path": "smartai/uploads/1/uuid-company_policy.pdf"
}
```

#### List Documents
```http
GET /api/documents?skip=0&limit=100
Authorization: Bearer <admin_token>

Response: 200 OK
[
  {
    "id": 1,
    "title": "company_policy.pdf",
    "status": "COMPLETED",
    "extracted_text": "Policy content...",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Pending Validation Documents
```http
GET /api/documents/pending-validation
Authorization: Bearer <admin_token>

Response: 200 OK
[
  {
    "id": 1,
    "title": "document.pdf",
    "status": "PENDING_VALIDATION",
    "extracted_text": "OCR extracted text..."
  }
]
```

#### Confirm Document (Trigger Embedding)
```http
POST /api/documents/{document_id}/confirm
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "confirmed_text": "Corrected and validated text content"
}

Response: 202 Accepted
{
  "id": 1,
  "status": "EMBEDDING",
  "extracted_text": "Corrected and validated text content"
}
```

#### Update Document Content
```http
PUT /api/documents/{document_id}/content
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "new_content": "Updated document content",
  "filename": "updated_doc.pdf"
}

Response: 200 OK
{
  "id": 1,
  "status": "COMPLETED",
  "extracted_text": "Updated document content"
}
```

#### Delete Document
```http
DELETE /api/documents/{document_id}
Authorization: Bearer <admin_token>

Response: 204 No Content
```

#### Retry Failed Document
```http
POST /api/documents/{document_id}/retry
Authorization: Bearer <admin_token>

Response: 200 OK
{
  "id": 1,
  "status": "UPLOADED",
  "message": "Document re-queued for processing"
}
```

---

### Chat

#### Send Message
```http
POST /api/chat
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "What is our company policy on remote work?",
  "conversation_id": "uuid-string" // optional
}

Response: 200 OK
{
  "response": "According to company policy document, remote work is allowed 3 days per week...",
  "conversation_id": "uuid-string"
}
```

---

### Chat Logs

#### Get User Conversations
```http
GET /api/chatlogs/conversations?skip=0&limit=100
Authorization: Bearer <token>

Response: 200 OK
[
  "conversation-uuid-1",
  "conversation-uuid-2"
]
```

#### Get Conversation History
```http
GET /api/chatlogs/{conversation_id}?skip=0&limit=100
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "id": 1,
    "question": "What is our policy?",
    "answer": "Our policy states...",
    "created_at": "2024-01-01T10:00:00",
    "conversation_id": "uuid"
  }
]
```

#### Get User Chat Logs
```http
GET /api/chatlogs?skip=0&limit=100&start_date=2024-01-01&end_date=2024-12-31
Authorization: Bearer <token>

Response: 200 OK
[
  {
    "id": 1,
    "question": "Question text",
    "answer": "Answer text",
    "created_at": "2024-01-01T00:00:00"
  }
]
```

#### Get Company Chat Logs (Admin)
```http
GET /api/company/chatlogs?division_id=1&user_id=2&skip=0&limit=100
Authorization: Bearer <admin_token>

Response: 200 OK
[
  {
    "id": 1,
    "question": "Question",
    "answer": "Answer",
    "user_id": 2,
    "division_id": 1
  }
]
```

#### Get All Chat Logs (Super Admin)
```http
GET /api/admin/chatlogs?company_id=1&division_id=1&user_id=2
Authorization: Bearer <super_admin_token>

Response: 200 OK
[
  {
    "id": 1,
    "question": "Question",
    "answer": "Answer",
    "company_id": 1,
    "user_id": 2
  }
]
```

---

## 🔐 Authentication

All endpoints (except `/auth/register` and `/auth/user/token`) require Bearer token:

```http
Authorization: Bearer <your_access_token>
```

## 👥 User Roles

- **Super Admin**: Full system access, approve/reject companies
- **Company Admin**: Manage company users, documents, divisions
- **User**: Chat with AI, view own chat history

## 📊 Document Processing Flow

1. **Upload** → Document uploaded to S3, status: `UPLOADED`
2. **OCR Processing** → Background task extracts text, status: `PENDING_VALIDATION`
3. **Validation** → Admin confirms/corrects text, status: `EMBEDDING`
4. **Embedding** → Background task creates vector embeddings, status: `COMPLETED`
5. **Available for RAG** → Document used in AI responses

## ⚡ Background Tasks

- **OCR Processing**: Extracts text from uploaded documents
- **Embedding Generation**: Creates vector embeddings for RAG
- Processed asynchronously using Celery

## 🛠️ Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# JWT
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# AWS S3
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
S3_BUCKET_NAME=your-bucket
AWS_REGION=us-east-1

# Pinecone
PINECONE_API_KEY=your-key
PINECONE_INDEX_NAME=your-index

# Google Gemini
GOOGLE_API_KEY=your-key

# Redis (Celery)
REDIS_URL=redis://localhost:6379/0
```

## 📝 Error Responses

All errors follow this format:

```json
{
  "detail": "Error message description"
}
```

Common status codes:
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## 📄 License

MIT License

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

**Built with ❤️ using FastAPI, Pinecone, and Google Gemini**
