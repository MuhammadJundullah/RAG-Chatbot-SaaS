# Multi-Tenant Company Chatbot API Documentation

## 📋 Table of Contents
- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [General](#general)
  - [Authentication & Registration](#authentication--registration)
  - [Divisions Management](#divisions-management)
  - [Documents Management](#documents-management)
  - [Chat](#chat)
- [Response Codes](#response-codes)
- [Error Handling](#error-handling)

---

## 🔍 Overview

Multi-Tenant Company Chatbot API adalah platform SaaS yang memungkinkan perusahaan memiliki chatbot AI yang disesuaikan dengan konteks perusahaan masing-masing. Platform ini mendukung dua sumber pengetahuan utama:
1.  **Dokumen (RAG):** Admin dapat mengunggah dokumen (PDF) untuk pengetahuan umum perusahaan.
2.  **Database Eksternal (Dynamic Querying):** Admin dapat menghubungkan database read-only mereka sendiri, lalu memberikan hak akses spesifik per-divisi ke tabel dan kolom tertentu. Chatbot kemudian dapat menjawab pertanyaan yang membutuhkan data langsung dari database tersebut.

**Version:** 2.0.0

**Tech Stack:**
- FastAPI
- PostgreSQL
- ChromaDB (Vector Database)
- Google Gemini AI
- SQLAlchemy

---

## 🌐 Base URL

```
http://localhost:8000
```

**API Prefix:** `/api/v1`

---

## 🔐 Authentication

API ini menggunakan **Bearer Token Authentication** dengan JWT (JSON Web Tokens).

### Mendapatkan Token

Setelah login, Anda akan menerima access token yang harus disertakan di header setiap request:

```http
Authorization: Bearer <your_access_token>
```

### User Roles

Ada dua role pengguna:
- **COMPANY_ADMIN**: Administrator perusahaan (akses penuh)
- **EMPLOYEE**: Karyawan perusahaan (akses terbatas)

---

## 📡 Endpoints

### General

#### 1. Root Endpoint
**GET** `/`

Endpoint untuk mengecek apakah API berjalan.

**Response:**
```json
{
  "message": "Multi-Tenant Company Chatbot API is running"
}
```

#### 2. Health Check
**GET** `/health`

Endpoint untuk health check monitoring.

**Response:**
```json
{
  "status": "healthy"
}
```

---

### Authentication & Registration

#### 3. Register Company
**POST** `/api/v1/companies/register`

Mendaftarkan perusahaan baru beserta admin pertama.

**Request Body:**
```json
{
  "name": "PT Maju Jaya",
  "admin_username": "admin_majujaya",
  "admin_password": "SecurePassword123!"
}
```

**Validasi:**
- `name`: Nama perusahaan (required)
- `admin_username`: Username admin (required, unique)
- `admin_password`: Password admin (required, min 8 karakter, max 200 bytes)

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "PT Maju Jaya",
  "company_code": "ABCD1234",
  "company_secret_one_time": "xyz789abc456def"
}
```

**⚠️ Penting:** 
- `company_code` dan `company_secret_one_time` hanya ditampilkan **sekali**
- Simpan dengan aman untuk pendaftaran karyawan

**Error Responses:**
- `400 Bad Request`: Nama perusahaan atau username sudah terdaftar
- `422 Unprocessable Entity`: Validasi gagal

---

#### 4. Register Employee
**POST** `/api/v1/employees/register`

Mendaftarkan karyawan baru untuk sebuah perusahaan.

**Request Body:**
```json
{
  "username": "john_doe",
  "password": "StrongPass456!",
  "company_code": "ABCD1234",
  "company_secret": "xyz789abc456def",
  "division_id": 2
}
```

**Validasi:**
- `username`: Username karyawan (required, unique)
- `password`: Password (required, min 8 karakter, max 200 bytes)
- `company_code`: Kode perusahaan (required)
- `company_secret`: Secret perusahaan (required)
- `division_id`: ID divisi (optional)

**Response (201 Created):**
```json
{
  "id": 5,
  "username": "john_doe",
  "role": "EMPLOYEE",
  "company_id": 1,
  "division_id": 2
}
```

**Error Responses:**
- `404 Not Found`: Company code tidak valid
- `403 Forbidden`: Company secret salah
- `400 Bad Request`: Username sudah terdaftar

---

#### 5. Login (Get Access Token)
**POST** `/api/v1/token`

Login untuk mendapatkan access token.

**Request Body (Form Data):**
```json
{
  "username": "admin_majujaya",
  "password": "SecurePassword123!"
}
```

**Content-Type:** `application/x-www-form-urlencoded`

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**
- `401 Unauthorized`: Username atau password salah

**cURL Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin_majujaya&password=SecurePassword123!"
```

---

### Divisions Management

---

### Dynamic Database & Permissions

Setelah perusahaan memiliki divisi, admin dapat menghubungkan database eksternal dan mengatur hak akses untuk setiap divisi.

#### 8. Set DB Connection String
**POST** `/api/v1/company/database-connection`

Menyimpan (dengan enkripsi) URL koneksi ke database read-only eksternal milik perusahaan.

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Body:**
```json
{
  "db_url": "postgresql+asyncpg://user:password@host:port/database_name"
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Database connection string updated successfully."
}
```

---

#### 9. Add Division Permission
**POST** `/api/v1/divisions/{division_id}/permissions`

Memberikan hak akses ke sebuah tabel/kolom di database eksternal untuk sebuah divisi.

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Body:**
```json
{
  "table_name": "sales_data",
  "allowed_columns": "product_name,quantity,total_price"
}
```

**Notes:**
- Gunakan `"*"` di `allowed_columns` untuk memberikan akses ke semua kolom di tabel tersebut.

**Response (201 Created):**
```json
{
  "id": 1,
  "division_id": 2,
  "table_name": "sales_data",
  "allowed_columns": "product_name,quantity,total_price"
}
```

---

#### 10. Get Division Permissions
**GET** `/api/v1/divisions/{division_id}/permissions`

Melihat semua hak akses yang dimiliki oleh sebuah divisi.

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "division_id": 2,
    "table_name": "sales_data",
    "allowed_columns": "product_name,quantity,total_price"
  },
  {
    "id": 2,
    "division_id": 2,
    "table_name": "customers",
    "allowed_columns": "*"
  }
]
```

---

### Documents Management

#### 6. Create Division
**POST** `/api/v1/divisions`

Membuat divisi baru dalam perusahaan (hanya untuk COMPANY_ADMIN).

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Headers:**
```http
Authorization: Bearer <admin_token>
```

**Request Body:**
```json
{
  "name": "IT Department"
}
```

**Response (201 Created):**
```json
{
  "id": 3,
  "name": "IT Department",
  "company_id": 1
}
```

**Error Responses:**
- `401 Unauthorized`: Token tidak valid atau expired
- `403 Forbidden`: User bukan COMPANY_ADMIN

---

#### 7. Get Company Divisions
**GET** `/api/v1/divisions`

Mengambil daftar semua divisi dalam perusahaan (hanya untuk COMPANY_ADMIN).

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Headers:**
```http
Authorization: Bearer <admin_token>
```

**Response (200 OK):**
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
  },
  {
    "id": 3,
    "name": "IT Department",
    "company_id": 1
  }
]
```

**Error Responses:**
- `401 Unauthorized`: Token tidak valid atau expired
- `403 Forbidden`: User bukan COMPANY_ADMIN

---

### Documents Management

#### 8. Get All Documents
**GET** `/api/v1/documents`

Mengambil daftar nama file dari semua dokumen yang telah diunggah untuk perusahaan.

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Headers:**
```http
Authorization: Bearer <admin_token>
```

**Response (200 OK):**
```json
[
  "company_handbook.pdf",
  "remote_work_policy.pdf"
]
```

**Error Responses:**
- `401 Unauthorized`: Token tidak valid

---

#### 9. Upload Document
**POST** `/api/v1/documents/upload`

Upload dokumen (PDF) ke knowledge base perusahaan menggunakan RAG (hanya untuk COMPANY_ADMIN).

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Headers:**
```http
Authorization: Bearer <admin_token>
Content-Type: multipart/form-data
```

**Request Body (Form Data):**
```
file: [binary PDF file]
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Document 'company_handbook.pdf' successfully added...",
  "chunks_added": 45
}
```

---

#### 10. Delete Document
**DELETE** `/api/v1/documents/{filename}`

Menghapus sebuah dokumen dan semua datanya dari knowledge base berdasarkan nama file.

**Authentication Required:** ✅ (COMPANY_ADMIN only)

**Request Headers:**
```http
Authorization: Bearer <admin_token>
```

**Path Parameter:**
- `filename`: Nama file yang akan dihapus. Pastikan untuk melakukan URL-encode jika nama file mengandung spasi atau karakter spesial (misalnya, `My%20Document.pdf`).

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Document 'My Document.pdf' and all its associated chunks have been deleted.",
  "chunks_deleted": 50
}
```

**Error Responses:**
- `401 Unauthorized`: Token tidak valid
- `404 Not Found`: File dengan nama tersebut tidak ditemukan


---

### Chat

#### 9. Chat with AI
**POST** `/api/v1/chat`

Endpoint utama untuk berinteraksi dengan AI chatbot yang konteksnya disesuaikan dengan perusahaan.

**Authentication Required:** ✅ (All authenticated users)

**Request Headers:**
```http
Authorization: Bearer <user_token>
Content-Type: application/json
```

**Request Body:**
```json
{
  "message": "Apa saja kebijakan cuti di perusahaan?",
  "conversation_id": "uuid-optional-conversation-id"
}
```

**Fields:**
- `message`: Pertanyaan atau pesan pengguna (required)
- `conversation_id`: ID percakapan untuk melanjutkan konteks (optional, akan di-generate jika tidak ada)

**Response (200 OK):**
```json
{
  "reply": "Berdasarkan handbook perusahaan, berikut adalah kebijakan cuti:\n\n1. Cuti Tahunan: 12 hari per tahun\n2. Cuti Sakit: Maksimal 14 hari dengan surat dokter\n3. Cuti Melahirkan: 3 bulan untuk karyawan wanita\n\nUntuk pengajuan cuti, silakan mengisi form di sistem HRIS minimal 3 hari sebelumnya.",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "sources": null,
  "used_database": false
}
```

**Response Fields:**
- `reply`: Jawaban dari AI
- `conversation_id`: ID percakapan (gunakan untuk request berikutnya)
- `sources`: Sumber informasi (jika ada)
- `used_database`: Boolean, apakah menggunakan query database

**AI Capabilities:**

1. **RAG (Retrieval-Augmented Generation)**
   - Menjawab pertanyaan berdasarkan dokumen yang di-upload
   - Mengambil konteks relevan dari ChromaDB

2. **Database Query**
   - Otomatis mendeteksi pertanyaan yang memerlukan data dari database
   - Generate dan eksekusi SQL query yang aman
   - Contoh: "Berapa total penjualan bulan ini?"

3. **Context Awareness**
   - Menjaga konteks percakapan menggunakan `conversation_id`
   - Data scope berdasarkan perusahaan dan divisi user

**Example Requests:**

**General Knowledge:**
```json
{
  "message": "Bagaimana cara mengajukan reimbursement?"
}
```

**Database Query:**
```json
{
  "message": "Tampilkan 10 pelanggan dengan transaksi terbanyak"
}
```

**With Conversation Context:**
```json
{
  "message": "Bagaimana dengan kebijakan overtime?",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Responses:**
- `401 Unauthorized`: Token tidak valid
- `500 Internal Server Error`: Error processing chat

---

## 📊 Response Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Request berhasil |
| 201 | Created | Resource berhasil dibuat |
| 400 | Bad Request | Request tidak valid atau missing parameters |
| 401 | Unauthorized | Authentication gagal atau token tidak valid |
| 403 | Forbidden | User tidak memiliki permission |
| 404 | Not Found | Resource tidak ditemukan |
| 422 | Unprocessable Entity | Validasi input gagal |
| 500 | Internal Server Error | Server error |

---

## ❌ Error Handling

Semua error response mengikuti format standard:

```json
{
  "detail": "Error message description"
}
```

**Validation Error (422):**
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

---

## 🔒 Security Features

1. **Password Hashing**
   - Menggunakan bcrypt dengan SHA256 pre-hashing untuk password panjang
   - Minimum 8 karakter, maksimum 200 bytes

2. **JWT Authentication**
   - Token-based authentication
   - Token expiration
   - Role-based access control

3. **SQL Injection Prevention**
   - Query validation
   - Whitelist patterns
   - Parameterized queries

4. **Multi-Tenancy**
   - Data isolation per perusahaan
   - Company-scoped RAG collections
   - Division-level access control

---

## 🚀 Quick Start Example

### 1. Register Company
```bash
curl -X POST "http://localhost:8000/api/v1/companies/register" \
  -H "Content-Type: application/json" \
  -d 
  {
    "name": "PT Example Corp",
    "admin_username": "admin_example",
    "admin_password": "SecurePass123!"
  }
```

### 2. Login as Admin
```bash
curl -X POST "http://localhost:8000/api/v1/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin_example&password=SecurePass123!"
```

### 3. Upload Document
```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@handbook.pdf"
```

### 4. Create Division
```bash
curl -X POST "http://localhost:8000/api/v1/divisions" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Engineering"}'
```

### 5. Register Employee
```bash
curl -X POST "http://localhost:8000/api/v1/employees/register" \
  -H "Content-Type: application/json" \
  -d 
  {
    "username": "employee1",
    "password": "EmpPass123!",
    "company_code": "ABCD1234",
    "company_secret": "your_secret",
    "division_id": 1
  }
```

### 6. Chat with AI
```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d 
  {
    "message": "What are the company policies?"
  }
```

---

## 📝 Notes

- Semua timestamps dalam UTC
- Token expiration default: 30 menit (dapat dikonfigurasi)
- Maximum file upload size: 10MB (dapat dikonfigurasi)
- ChromaDB collection naming: `company_{company_id}_docs`
- Database query timeout: 30 detik

---

## 🛠️ Development

### Running the API
```bash
uvicorn app.main:app --reload
```

### Interactive API Documentation
Setelah server berjalan, akses:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 📞 Support

Untuk bantuan dan bug reports, silakan hubungi tim development atau buat issue di repository.

---

**Last Updated:** October 2025  
**API Version:** 2.0.0
