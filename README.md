# Multi-Tenant Company Chatbot API

A SaaS platform for company-specific AI chatbots using RAG (Retrieval-Augmented Generation) and Database Integration.

## Base URL

All API endpoints are prefixed with `/api`

- **Local Development**: `http://localhost:8000/api`
- **Production**: `[Your Production URL]/api`

## Authentication

This API uses JWT Bearer tokens for authentication. Include the token in the `Authorization` header:

```
Authorization: Bearer <your-access-token>
```

Tokens are obtained through the `/auth/user/token` endpoint.

## API Endpoints

### 🔐 Authentication

#### POST `/auth/register`
**Deskripsi:** Register a new company (admin user only)
**Akses:** Public

**Request Body:**
```json
{
  "name": "string",
  "email": "string",
  "password": "string",
  "company_name": "string",
  "pic_phone_number": "string (optional)",
  "username": "string (optional)"
}
```

**Response:** `201 Created`
```json
{
  "message": "Company 'company_name' and admin user 'email' registered successfully. Pending approval from a super admin."
}
```

#### POST `/auth/user/token`
**Deskripsi:** Login and get access token
**Akses:** Public

**Request Body:**
```json
{
  "email": "string (optional if username provided)",
  "username": "string (optional if email provided)",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": "integer",
  "user": {
    "id": "integer",
    "email": "string",
    "username": "string",
    "name": "string",
    "role": "string",
    "company_id": "integer",
    "is_active": "boolean"
  }
}
```

#### GET `/auth/me`
**Deskripsi:** Get current logged-in user information
**Akses:** Authenticated Users

**Response:** `200 OK`
```json
{
  "id": "integer",
  "email": "string",
  "username": "string",
  "name": "string",
  "role": "string",
  "company_id": "integer",
  "is_active": "boolean"
}
```

### 🏢 Companies (Admin Only)

#### GET `/companies/me`
**Deskripsi:** Get current admin's company data
**Akses:** Company Admin

**Response:** `200 OK`
```json
{
  "id": "integer",
  "name": "string",
  "is_active": "boolean",
  "created_at": "datetime"
}
```

#### GET `/companies/users`
**Deskripsi:** Get all users in the admin's company
**Akses:** Company Admin

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "email": "string",
    "username": "string",
    "name": "string",
    "role": "string",
    "company_id": "integer",
    "division_id": "integer (nullable)",
    "is_active": "boolean"
  }
]
```

#### PUT `/companies/me`
**Deskripsi:** Update the current admin's company data, including logo upload to S3.
**Akses:** Company Admin

**Form Data:**
- `company_update`: JSON object (required) - Contains fields to update (e.g., `name`, `address`).
  ```json
  {
    "name": "string (optional)",
    "code": "string (optional)",
    "address": "string (optional)"
  }
  ```
- `logo_file`: file (optional) - The new logo file to upload.

**Response:** `200 OK`
```json
{
  "id": "integer",
  "name": "string",
  "is_active": "boolean",
  "created_at": "datetime",
  "logo_s3_path": "string (nullable)"
}
```

#### POST `/companies/employees/register`
**Deskripsi:** Register a new employee for the company
**Akses:** Company Admin

**Request Body:**
```json
{
  "name": "string",
  "email": "string",
  "password": "string",
  "username": "string (optional)",
  "division_id": "integer (optional)"
}
```

**Response:** `201 Created`
```json
{
  "id": "integer",
  "email": "string",
  "username": "string",
  "name": "string",
  "role": "employee",
  "company_id": "integer",
  "division_id": "integer (nullable)",
  "is_active": "boolean"
}
```

### 🏢 Divisions

#### POST `/divisions`
**Deskripsi:** Create a new division within the admin's company
**Akses:** Company Admin

**Request Body:**
```json
{
  "name": "string"
}
```

**Response:** `200 OK`
```json
{
  "id": "integer",
  "name": "string",
  "company_id": "integer"
}
```

#### GET `/divisions`
**Deskripsi:** Get all divisions for the current user's company
**Akses:** Authenticated Users

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "name": "string",
    "company_id": "integer"
  }
]
```

#### GET `/divisions/public/{company_id}`
**Deskripsi:** Get all divisions for a specific company (public endpoint)
**Akses:** Public

**Path Parameters:**
- `company_id`: integer

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "name": "string",
    "company_id": "integer"
  }
]
```

### 📄 Documents (Admin Only)

#### POST `/documents/upload`
**Deskripsi:** Upload a document for processing. This endpoint accepts a file, saves it temporarily, creates a DB record with 'UPLOADING' status, and triggers a background task to upload to S3.
**Akses:** Company Admin

**Form Data:**
- `file`: file (required)

**Response:** `202 Accepted`
```json
{
  "id": "integer",
  "title": "string",
  "company_id": "integer",
  "content_type": "string",
  "status": "UPLOADING",
  "s3_path": "string (nullable)",
  "temp_storage_path": "string",
  "text": "string (nullable)",
  "failed_reason": "string (nullable)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### PUT `/documents/{document_id}/retry`
**Deskripsi:** Retry a failed document upload. Allows retrying the upload process for a document that previously failed to upload.
**Akses:** Company Admin

**Path Parameters:**
- `document_id`: integer

**Response:** `200 OK`
```json
{
  "id": "integer",
  "title": "string",
  "company_id": "integer",
  "content_type": "string",
  "status": "UPLOADING",
  "s3_path": "string (nullable)",
  "temp_storage_path": "string",
  "text": "string (nullable)",
  "failed_reason": "string (nullable)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### GET `/documents`
**Deskripsi:** Get all documents for the company, regardless of status.
**Akses:** Company Admin

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "title": "string",
    "company_id": "integer",
    "content_type": "string",
    "status": "string",
    "s3_path": "string (nullable)",
    "temp_storage_path": "string (nullable)",
    "text": "string (nullable)",
    "failed_reason": "string (nullable)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

#### GET `/documents/pending-validation`
**Deskripsi:** Get documents awaiting user validation after OCR. Gets a list of documents that have been OCR'd and are awaiting user validation.
**Akses:** Company Admin

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "title": "string",
    "company_id": "integer",
    "content_type": "string",
    "status": "PENDING_VALIDATION",
    "s3_path": "string",
    "temp_storage_path": "string (nullable)",
    "text": "string (OCR extracted text)",
    "failed_reason": "string (nullable)",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

#### POST `/documents/{document_id}/confirm`
**Deskripsi:** Confirm OCR text and trigger embedding process. Receives user-confirmed text and triggers the embedding background task.
**Akses:** Company Admin

**Path Parameters:**
- `document_id`: integer

**Request Body:**
```json
{
  "confirmed_text": "string"
}
```

**Response:** `202 Accepted`
```json
{
  "id": "integer",
  "title": "string",
  "company_id": "integer",
  "content_type": "string",
  "status": "EMBEDDING",
  "s3_path": "string",
  "temp_storage_path": "string (nullable)",
  "text": "string (confirmed text)",
  "failed_reason": "string (nullable)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### GET `/documents/failed`
**Deskripsi:** Get documents that failed during processing or upload.
**Akses:** Company Admin

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "title": "string",
    "company_id": "integer",
    "content_type": "string",
    "status": "string",
    "s3_path": "string (nullable)",
    "temp_storage_path": "string (nullable)",
    "text": "string (nullable)",
    "failed_reason": "string",
    "created_at": "datetime",
    "updated_at": "datetime"
  }
]
```

#### POST `/documents/{document_id}/retry-processing`
**Deskripsi:** Retry failed document processing (OCR or Embedding). Manually triggers a retry for a document that failed during OCR or Embedding.
**Akses:** Company Admin

**Path Parameters:**
- `document_id`: integer

**Response:** `200 OK`
```json
{
  "id": "integer",
  "title": "string",
  "company_id": "integer",
  "content_type": "string",
  "status": "string",
  "s3_path": "string (nullable)",
  "temp_storage_path": "string (nullable)",
  "text": "string (nullable)",
  "failed_reason": "string (nullable)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### PUT `/documents/{document_id}/content`
**Deskripsi:** Update document content and re-generate embeddings. Updates the text content of an existing document and re-generates its embeddings.
**Akses:** Company Admin

**Path Parameters:**
- `document_id`: integer

**Request Body:**
```json
{
  "new_content": "string",
  "filename": "string"
}
```

**Response:** `200 OK`
```json
{
  "id": "integer",
  "title": "string",
  "company_id": "integer",
  "content_type": "string",
  "status": "COMPLETED",
  "s3_path": "string",
  "temp_storage_path": "string (nullable)",
  "text": "string (updated content)",
  "failed_reason": "string (nullable)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### GET `/documents/{document_id}`
**Deskripsi:** Get a single document by ID, checking for appropriate permissions.
**Akses:** Authenticated Users (Must belong to same company or be super admin)

**Path Parameters:**
- `document_id`: integer

**Response:** `200 OK`
```json
{
  "id": "integer",
  "title": "string",
  "company_id": "integer",
  "content_type": "string",
  "status": "string",
  "s3_path": "string (nullable)",
  "temp_storage_path": "string (nullable)",
  "text": "string (nullable)",
  "failed_reason": "string (nullable)",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### DELETE `/documents/{document_id}`
**Deskripsi:** Delete a document (from database, S3, and RAG service). This endpoint deletes the document from the database, S3, and the RAG service.
**Akses:** Company Admin

**Path Parameters:**
- `document_id`: integer

**Response:** `204 No Content`

### 💬 Chat

#### POST `/chat`
**Deskripsi:** Send a message to the AI chatbot. This endpoint processes the user's message, retrieves relevant context from the RAG service, generates a response using the AI model, and saves the chat to the database.
**Akses:** Authenticated Users

**Request Body:**
```json
{
  "message": "string",
  "conversation_id": "string (optional)"
}
```

**Response:** `200 OK`
```json
{
  "response": "string",
  "conversation_id": "string"
}
```

### 📝 Chatlogs

#### GET `/chatlogs`
**Deskripsi:** Get current user's chat logs. Retrieve chatlogs for the current user, filtered by their company.
**Akses:** Authenticated Users

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)
- `start_date`: date (optional)
- `end_date`: date (optional)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "question": "string",
    "answer": "string",
    "UsersId": "integer",
    "company_id": "integer",
    "conversation_id": "string",
    "created_at": "datetime"
  }
]
```

#### GET `/chatlogs/conversations`
**Deskripsi:** Get unique conversation IDs for the current user. Retrieve a list of unique conversation IDs for the current user.
**Akses:** Authenticated Users

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)

**Response:** `200 OK`
```json
["conversation_id_1", "conversation_id_2", ...]
```

#### GET `/chatlogs/{conversation_id}`
**Deskripsi:** Get chat history for a specific conversation. Retrieve chat history for a specific conversation ID for the current user.
**Akses:** Authenticated Users

**Path Parameters:**
- `conversation_id`: string

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "question": "string",
    "answer": "string",
    "UsersId": "integer",
    "company_id": "integer",
    "conversation_id": "string",
    "created_at": "datetime"
  }
]
```

### 👨‍💼 Company Admin Chatlogs

#### GET `/company/chatlogs`
**Deskripsi:** Get chat logs for the current company (admin only). Retrieve chatlogs for the current company admin, filtered by their company.
**Akses:** Company Admin

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)
- `division_id`: integer (optional)
- `user_id`: integer (optional)
- `start_date`: date (optional)
- `end_date`: date (optional)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "question": "string",
    "answer": "string",
    "UsersId": "integer",
    "company_id": "integer",
    "conversation_id": "string",
    "created_at": "datetime"
  }
]
```

### 👑 Super Admin Endpoints

#### GET `/admin/companies`
**Deskripsi:** Get all active companies
**Akses:** Super Admin

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "name": "string",
    "is_active": "boolean",
    "created_at": "datetime"
  }
]
```

#### GET `/admin/companies/pending`
**Deskripsi:** Get companies awaiting approval. Get a list of companies awaiting approval (accessible only by super admins).
**Akses:** Super Admin

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "name": "string",
    "is_active": "boolean",
    "created_at": "datetime"
  }
]
```

#### PATCH `/admin/companies/{company_id}/approve`
**Deskripsi:** Approve a pending company. Approve a company registration (accessible only by super admins).
**Akses:** Super Admin

**Path Parameters:**
- `company_id`: integer

**Response:** `200 OK`
```json
{
  "message": "Company with id {company_id} has been approved."
}
```

#### PATCH `/admin/companies/{company_id}/reject`
**Deskripsi:** Reject a pending company. Reject a company registration (accessible only by super admins).
**Akses:** Super Admin

**Path Parameters:**
- `company_id`: integer

**Response:** `200 OK`
```json
{
  "message": "Company with id {company_id} has been rejected and deleted."
}
```

#### GET `/admin/chatlogs`
**Deskripsi:** Get all chat logs (super admin only). Retrieve all chatlogs for super admin with optional filtering.
**Akses:** Super Admin

**Query Parameters:**
- `skip`: integer (default: 0)
- `limit`: integer (default: 100)
- `company_id`: integer (optional)
- `division_id`: integer (optional)
- `user_id`: integer (optional)
- `start_date`: date (optional)
- `end_date`: date (optional)

**Response:** `200 OK`
```json
[
  {
    "id": "integer",
    "question": "string",
    "answer": "string",
    "UsersId": "integer",
    "company_id": "integer",
    "conversation_id": "string",
    "created_at": "datetime"
  }
]
```

### 🏥 Health Check

#### GET `/`
**Deskripsi:** API root endpoint
**Akses:** Public

**Response:** `200 OK`
```json
{
  "message": "Multi-Tenant Company Chatbot API is running"
}
```

#### GET `/health`
**Deskripsi:** Health check endpoint
**Akses:** Public

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

## Document Status Flow

Documents go through the following status states:

1. **UPLOADING** → File is being uploaded to S3
2. **UPLOADED** → File successfully uploaded to S3
3. **PROCESSING** → OCR processing in progress
4. **PENDING_VALIDATION** → OCR complete, awaiting user confirmation
5. **EMBEDDING** → Generating embeddings for RAG
6. **COMPLETED** → Document fully processed and ready for chat
7. **UPLOAD_FAILED** → Upload to S3 failed
8. **PROCESSING_FAILED** → OCR or embedding process failed

## User Roles

- **super_admin**: Full system access, can approve/reject companies
- **admin**: Company administrator, can manage employees and documents
- **employee**: Regular user, can chat and view their own chat logs

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `202 Accepted`: Request accepted for processing
- `204 No Content`: Resource deleted successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or invalid token
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## CORS

The API allows all origins, methods, and headers for development purposes. In production, configure appropriate CORS policies.

## License

This project is proprietary and confidential.