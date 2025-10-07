# Multi-Tenant Company Chatbot API

Platform SaaS untuk chatbot AI yang disesuaikan dengan konteks perusahaan menggunakan RAG (Retrieval-Augmented Generation) dan Dynamic Database Integration.

[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
  - [1. Health & Status](#1-health--status)
  - [2. Authentication & Registration](#2-authentication--registration)
  - [3. Company Management](#3-company-management)
  - [4. Division Management](#4-division-management)
  - [5. Document Management](#5-document-management)
  - [6. AI Chat](#6-ai-chat)
- [Response Codes](#response-codes)
- [Security](#security)

---

## Overview

Multi-Tenant Company Chatbot API memungkinkan setiap perusahaan memiliki AI chatbot yang disesuaikan dengan:
- **Knowledge Base (RAG)**: Dokumen internal perusahaan
- **Database Integration**: Koneksi ke database eksternal dengan kontrol akses granular
- **Multi-Tenancy**: Isolasi data penuh antar perusahaan
- **Role-Based Access**: Kontrol akses berbasis role dan divisi

**Base URL**: `http://localhost:8000`  
**API Version**: `v2.0.0`  
**API Prefix**: `/api/v1`

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Tenancy** | Setiap perusahaan memiliki space data terisolasi |
| **User Roles** | COMPANY_ADMIN (full access) & EMPLOYEE (restricted) |
| **Document RAG** | Upload & manage PDF documents untuk knowledge base |
| **Dynamic DB** | Connect external databases |
| **Intelligent Chat** | AI yang combine RAG + Database + Context awareness |
| **Security** | JWT auth, bcrypt passwords, SQL injection prevention |

---

## Tech Stack

```
Backend:      FastAPI (async)
Database:     PostgreSQL (internal)
Vector DB:    ChromaDB (document embeddings)
AI Model:     Google Gemini
ORM:          SQLAlchemy (async)
Auth:         JWT (Bearer Token)
Password:     bcrypt + SHA256
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- pip or conda

### Installation

```bash
# Clone repository
git clone <repository-url>
cd company_chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chatbot_db

# Security
SECRET_KEY=your-super-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI
GEMINI_API_KEY=your-gemini-api-key

# ChromaDB
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

### Run Server

```bash
uvicorn app.main:app --reload --port 8000
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Authentication

### How It Works

1. Login via `/api/v1/token` to receive JWT token
2. Include token in header: `Authorization: Bearer <token>`
3. Token expires after 30 minutes (configurable)

### User Roles

| Role | Description | Capabilities |
|------|-------------|--------------|
| **COMPANY_ADMIN** | Administrator perusahaan | Manage divisions, upload/delete documents, set DB connection, full chat access |
| **EMPLOYEE** | Karyawan perusahaan | Chat with AI |

### Token Structure

```json
{
  "sub": "username",
  "role": "COMPANY_ADMIN",
  "company_id": 1,
  "division_id": null,
  "exp": 1709556000
}
```

---

## API Endpoints

### 1. Health & Status

#### Root Endpoint

Check if API is running.

```http
GET /
```

**Authentication**: Not required

**Response 200**:
```json
{
  "message": "Multi-Tenant Company Chatbot API is running"
}
```

---

#### Health Check

```http
GET /health
```

**Authentication**: Not required

**Response 200**:
```json
{
  "status": "healthy"
}
```

---

### 2. Authentication & Registration

#### Register Company

Daftarkan perusahaan baru beserta admin pertama.

```http
POST /api/v1/companies/register
```

**Authentication**: Not required

**Request Body**:
```json
{
  "name": "PT Maju Jaya",
  "admin_username": "admin_majujaya",
  "admin_password": "SecurePassword123!"
}
```

**Validation Rules**:
- `name`: Required, unique, max 255 chars
- `admin_username`: Required, unique, alphanumeric + underscore
- `admin_password`: Required, 8-200 bytes

**Response 201**:
```json
{
  "id": 1,
  "name": "PT Maju Jaya",
  "company_code": "ABCD1234",
  "company_secret_one_time": "xyz789abc456def123"
}
```

**Important**: `company_code` dan `company_secret_one_time` hanya ditampilkan sekali. Simpan dengan aman untuk registrasi employee.

**Error Responses**:
- `400`: Company name atau username sudah ada
- `422`: Validation error

---

#### Register Employee

Daftarkan karyawan baru untuk perusahaan.

```http
POST /api/v1/employees/register
```

**Authentication**: Not required

**Request Body**:
```json
{
  "username": "john_doe",
  "password": "StrongPass456!",
  "company_code": "ABCD1234",
  "company_secret": "xyz789abc456def123",
  "division_id": 2
}
```

**Validation Rules**:
- `username`: Required, unique
- `password`: Required, 8-200 bytes
- `company_code`: Required, 8 chars
- `company_secret`: Required
- `division_id`: Optional

**Response 201**:
```json
{
  "id": 5,
  "username": "john_doe",
  "role": "EMPLOYEE",
  "company_id": 1,
  "division_id": 2
}
```

**Error Responses**:
- `404`: Company code tidak valid
- `403`: Company secret salah
- `400`: Username sudah terdaftar atau division_id invalid

---

#### Login

Login untuk mendapatkan JWT access token.

```http
POST /api/v1/token
```

**Authentication**: Not required

**Content-Type**: `application/x-www-form-urlencoded`

**Form Data**:
```
username=admin_majujaya
password=SecurePassword123!
```

**Response 200**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401`: Username atau password salah

---

### 3. Company Management

#### Set Database Connection

Simpan connection string ke database eksternal perusahaan.

```http
POST /api/v1/company/database-connection
```

**Authentication**: COMPANY_ADMIN only

**Request Body**:
```json
{
  "db_url": "postgresql+asyncpg://user:password@host:5432/database_name"
}
```

**Supported Database Types**:

| Database | Connection String Format |
|----------|-------------------------|
| PostgreSQL | `postgresql+asyncpg://user:pass@host:port/db` |
| MySQL | `mysql+aiomysql://user:pass@host:port/db` |

**Response 200**:
```json
{
  "status": "success",
  "message": "Database connection string updated successfully."
}
```

**Security Notes**:
- Connection string di-encrypt sebelum disimpan
- Database harus read-only untuk keamanan
- Dapat di-update kapan saja

---

#### Get Database Connection Status

Cek status koneksi database eksternal.

```http
GET /api/v1/company/database-connection
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
{
  "is_configured": true,
  "db_host": "your-db-host.com"
}
```

---

#### Delete Database Connection

Hapus connection string database eksternal.

```http
DELETE /api/v1/company/database-connection
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
{
  "status": "success",
  "message": "Database connection string deleted successfully."
}
```

---

#### Get External Database Schema

Introspeksi dan dapatkan skema (tabel dan kolom) dari database eksternal.

```http
GET /api/v1/company/database-schema
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
{
  "schema": {
    "users": [
      "id",
      "name",
      "email"
    ],
    "products": [
      "id",
      "product_name",
      "price"
    ]
  }
}
```

---

#### List Company Employees

Dapatkan daftar semua karyawan di perusahaan.

```http
GET /api/v1/company/employees
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
[
  {
    "id": 5,
    "username": "john_doe",
    "role": "EMPLOYEE",
    "company_id": 1,
    "division_id": 2,
    "is_active": true
  }
]
```

---

#### List Pending Employees

Dapatkan daftar karyawan yang registrasinya masih pending (belum aktif).

```http
GET /api/v1/company/employees/pending
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
[
  {
    "id": 6,
    "username": "jane_doe",
    "role": "EMPLOYEE",
    "company_id": 1,
    "division_id": 1,
    "is_active": false
  }
]
```

---

#### Activate Employee

Aktifkan seorang karyawan yang statusnya masih pending.

```http
PUT /api/v1/company/employees/{employee_id}/activate
```

**Authentication**: COMPANY_ADMIN only

**Path Parameters**:
- `employee_id` (integer, required)

**Response 200**:
```json
{
  "status": "success",
  "message": "Employee jane_doe has been activated."
}
```

**Error Responses**:
- `404`: Employee tidak ditemukan
- `400`: Employee sudah aktif

---

### 4. Division Management

#### Create Division

Buat divisi baru dalam perusahaan.

```http
POST /api/v1/divisions
```

**Authentication**: COMPANY_ADMIN only

**Request Body**:
```json
{
  "name": "IT Department"
}
```

**Response 201**:
```json
{
  "id": 3,
  "name": "IT Department",
  "company_id": 1
}
```

---

#### List All Divisions

Dapatkan semua divisi dalam perusahaan.

```http
GET /api/v1/divisions
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
[
  {
    "id": 1,
    "name": "Sales Department",
    "company_id": 1
  },
  {
    "id": 2,
    "name": "Marketing Department",
    "company_id": 1
  }
]
```

---

#### Get Single Division

Dapatkan detail satu divisi.

```http
GET /api/v1/divisions/{division_id}
```

**Authentication**: COMPANY_ADMIN only

**Path Parameters**:
- `division_id` (integer, required)

**Response 200**:
```json
{
  "id": 3,
  "name": "IT Department",
  "company_id": 1
}
```

**Error Responses**:
- `404`: Division tidak ditemukan

---

#### Update Division

Update nama divisi.

```http
PUT /api/v1/divisions/{division_id}
```

**Authentication**: COMPANY_ADMIN only

**Path Parameters**:
- `division_id` (integer, required)

**Request Body**:
```json
{
  "name": "Information Technology Department"
}
```

**Response 200**:
```json
{
  "id": 3,
  "name": "Information Technology Department",
  "company_id": 1
}
```

---

#### Delete Division

Hapus divisi.

```http
DELETE /api/v1/divisions/{division_id}
```

**Authentication**: COMPANY_ADMIN only

**Path Parameters**:
- `division_id` (integer, required)

**Response 204**: No Content

**Error Responses**:
- `404`: Division tidak ditemukan

---

### 5. Document Management

#### Upload Document

Upload dokumen PDF ke knowledge base perusahaan.

```http
POST /api/v1/documents/upload
```

**Authentication**: COMPANY_ADMIN only

**Content-Type**: `multipart/form-data`

**Form Data**:
- `file`: PDF file (binary)

**Constraints**:
- Format: PDF only
- Max size: 10MB
- Processing: Automatic text extraction, chunking, embedding

**Response 200**:
```json
{
  "status": "success",
  "message": "Document 'company_handbook.pdf' successfully added to company knowledge base",
  "chunks_added": 45
}
```

**Processing Pipeline**:
1. Extract text dari PDF
2. Split menjadi chunks (dengan overlap untuk context)
3. Generate embeddings
4. Store di ChromaDB dengan metadata (company_id, filename, chunk_index)

**Error Responses**:
- `400`: Invalid file atau processing failed
- `500`: Server error

---

#### List Documents

Dapatkan daftar semua dokumen yang telah di-upload.

```http
GET /api/v1/documents
```

**Authentication**: COMPANY_ADMIN only

**Response 200**:
```json
[
  "company_handbook.pdf",
  "employee_benefits_2024.pdf",
  "remote_work_policy.pdf"
]
```

---

#### Delete Document

Hapus dokumen dan semua chunks terkait.

```http
DELETE /api/v1/documents/{filename}
```

**Authentication**: COMPANY_ADMIN only

**Path Parameters**:
- `filename` (string, required): Nama file (URL-encoded jika ada spasi/special chars)

**Response 200**:
```json
{
  "status": "success",
  "message": "Document 'company_handbook.pdf' and all its associated chunks have been deleted.",
  "chunks_deleted": 45
}
```

**URL Encoding Guide**:

| Original | Encoded |
|----------|---------|
| `My Document.pdf` | `My%20Document.pdf` |
| `Report (2024).pdf` | `Report%20%282024%29.pdf` |

---

### 6. AI Chat

#### Chat with AI

Endpoint utama untuk berinteraksi dengan AI chatbot.

```http
POST /api/v1/chat
```

**Authentication**: All authenticated users

**Request Body**:
```json
{
  "message": "Apa saja kebijakan cuti di perusahaan?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Request Fields**:
- `message` (string, required): Pertanyaan atau pesan user
- `conversation_id` (string, optional): UUID untuk conversation continuity

**Response 200**:
```json
{
  "reply": "Berdasarkan company handbook, berikut kebijakan cuti:\n\n1. Cuti Tahunan: 12 hari per tahun\n2. Cuti Sakit: Maksimal 14 hari dengan surat dokter\n3. Cuti Melahirkan: 3 bulan untuk karyawan wanita",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "sources": null,
  "used_database": false
}
```

**Response Fields**:
- `reply`: Jawaban dari AI
- `conversation_id`: UUID untuk conversation tracking
- `sources`: Daftar sumber informasi (jika ada)
- `used_database`: True jika database di-query

---

#### AI Capabilities

**RAG (Retrieval-Augmented Generation)**
- Semantic search di ChromaDB
- Context dari uploaded PDF documents
- Company-scoped results only
- Relevance-based ranking

**Database Queries**
- Auto-detect pertanyaan yang memerlukan data
- Generate safe SQL queries (validated)

- Keywords trigger: berapa, jumlah, total, rata-rata, pelanggan, tampilkan, data

**Context Management**
- Multi-turn conversations
- Follow-up question understanding
- Conversation history tracking
- Context-aware responses

**Multi-Tenancy & Security**
- Data isolation per company

- Safe SQL query validation
- No cross-company data leakage

---

#### Example Use Cases

**General Knowledge (RAG-based)**

Request:
```json
{
  "message": "Bagaimana cara mengajukan reimbursement?"
}
```

Response:
```json
{
  "reply": "Berdasarkan company handbook:\n\n1. Isi form reimbursement di HRIS\n2. Attach bukti pembelian\n3. Submit ke supervisor\n4. Finance akan proses dalam 5-7 hari kerja",
  "used_database": false
}
```

---

**Database Query**

Request:
```json
{
  "message": "Berapa total penjualan bulan ini?"
}
```

Response:
```json
{
  "reply": "Total Penjualan: Rp 450.500.000\nJumlah Transaksi: 1.234\nRata-rata: Rp 365.050\n\nPeningkatan 15% dari bulan lalu.",
  "used_database": true
}
```

---

**Follow-up Question**

Initial request:
```json
{
  "message": "Siapa top 5 sales person bulan ini?"
}
```

Follow-up:
```json
{
  "message": "Bagaimana performanya dibanding bulan lalu?",
  "conversation_id": "abc123-def456"
}
```

Response:
```json
{
  "reply": "Perbandingan performa top 5 sales:\n\n1. John Doe: +20%\n2. Jane Smith: +15%\n3. Bob Wilson: +10%\n\nRata-rata peningkatan 14%",
  "used_database": true
}
```

---

## Response Codes

| Code | Status | Description |
|------|--------|-------------|
| **200** | OK | Request berhasil |
| **201** | Created | Resource berhasil dibuat |
| **204** | No Content | Request berhasil, no response body |
| **400** | Bad Request | Request invalid |
| **401** | Unauthorized | Authentication gagal |
| **404** | Not Found | Resource tidak ditemukan |
| **422** | Unprocessable Entity | Validation error |
| **500** | Internal Server Error | Server error |

---

## Error Handling

### Standard Error Format

```json
{
  "detail": "Error message description"
}
```

### Validation Error (422)

```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password is too long (max 200 bytes)",
      "type": "value_error"
    }
  ]
}
```

### Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| Invalid token | Token expired atau tidak valid | Login ulang |
| Incorrect username or password | Kredensial salah | Periksa username dan password |
| Invalid company code | Company code tidak ditemukan | Verify company code |
| Invalid company secret credential | Company secret salah | Gunakan secret yang benar |
| Division not found in your company | Division ID tidak valid | Pastikan division ID milik company Anda |
| Password is too long (max 200 bytes) | Password melebihi batas | Gunakan password lebih pendek |

---

## Security

### Password Security

**Hashing Algorithm**:
- Primary: bcrypt (rounds: 12)
- Pre-hash: SHA256 (untuk password > 72 bytes)
- Salt: Unique per password

**Requirements**:
- Minimum: 8 characters
- Maximum: 200 bytes (UTF-8 encoded)

### JWT Token Security

**Configuration**:
- Algorithm: HS256
- Expiration: 30 minutes (configurable)
- Secret key: Min 32 characters (from .env)

**Token Contains**:
- User ID (sub)
- Role (COMPANY_ADMIN/EMPLOYEE)
- Company ID
- Division ID (for employees)
- Expiration timestamp

### Database Security

**External Database Connection**:
- Connection strings encrypted at rest
- Read-only access recommended
- SQL injection prevention via parameterized queries
- Query validation before execution

### Multi-Tenancy Security

**Data Isolation**:
- Company ID enforced at database level
- ChromaDB filtered by company_id
- No cross-tenant data access
- Automatic scoping in all queries

---

## License

This project is proprietary software. All rights reserved.

---

## Support

For issues or questions:
- Create an issue in the repository
- Contact: support@yourcompany.com

---

**Last Updated**: October 2025  
**API Version**: v2.0.0
