# Multi-Tenant Company Chatbot API

Platform SaaS untuk chatbot AI yang disesuaikan dengan konteks perusahaan menggunakan RAG (Retrieval-Augmented Generation).

[![FastAPI](https://img.shields.io/badge/FastAPI-2.0.0-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192.svg?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org)

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Menggunakan Docker (Direkomendasikan)](#menggunakan-docker-direkomendasikan)
  - [Tanpa Docker (Lingkungan Lokal)](#tanpa-docker-lingkungan-lokal)
- [Authentication and Approval Flow](#authentication-and-approval-flow)
  - [User Roles](#user-roles)
  - [Token Structure](#token-structure)
- [API Endpoints](#api-endpoints)
  - [1. Health and Status](#1-health-and-status)
  - [2. Authentication](#2-authentication)
  - [3. Super Admin](#3-super-admin)
  - [4. Companies & Company Admin](#4-companies--company-admin)
  - [5. Divisions](#5-divisions)
  - [6. Documents (RAG)](#6-documents-rag)
  - [7. AI Chat](#7-ai-chat)
  - [8. Chatlogs](#8-chatlogs)
- [Response Codes](#response-codes)
- [Security](#security)

---

## Overview

Multi-Tenant Company Chatbot API adalah sebuah platform Software-as-a-Service (SaaS) yang memungkinkan setiap perusahaan (tenant) untuk memiliki AI chatbot kustom. Chatbot ini dapat menjawab pertanyaan berdasarkan basis pengetahuan internal perusahaan yang diunggah dalam bentuk dokumen (menggunakan teknik RAG).

Fitur utama meliputi isolasi data antar perusahaan, sistem peran pengguna (admin dan employee), dan alur persetujuan untuk pengguna baru.

**Base URL**: `http://localhost:8000`  
**API Version**: `v2.0.0`

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Tenancy** | Data setiap perusahaan terisolasi sepenuhnya di level database. |
| **User Approval Flow** | Admin perusahaan dapat menyetujui atau menolak pendaftaran pengguna baru, memberikan kontrol penuh atas akses. |
| **Document RAG** | Kemampuan untuk mengunggah dokumen (PDF) yang akan menjadi basis pengetahuan untuk chatbot. |
| **Intelligent Chat** | Chatbot AI yang menggunakan konteks dari dokumen yang relevan untuk memberikan jawaban yang akurat. |
| **Secure Authentication** | Menggunakan JWT (Bearer Token) untuk otentikasi dan `bcrypt` untuk hashing password. |

---

## Tech Stack

```
Backend:      FastAPI (async)
Database:     PostgreSQL (internal)
Vector DB:    Pinecone (document embeddings)
AI Model:     Google Gemini
ORM:          SQLAlchemy (async)
Auth:         JWT (Bearer Token)
Password:     bcrypt
```

---

## Getting Started

Untuk menjalankan aplikasi ini, Anda memiliki dua opsi utama: menggunakan Docker (direkomendasikan untuk kemudahan setup) atau menjalankannya secara lokal tanpa Docker.

### Menggunakan Docker (Direkomendasikan)

Pastikan Anda telah menginstal Docker dan Docker Compose di sistem Anda.

1.  **Clone Repositori:**
    ```bash
    git clone https://github.com/your-repo/company-chatbot-v2.git
    cd company-chatbot-v2
    ```

2.  **Konfigurasi Environment:**
    Buat file `.env` di root proyek Anda berdasarkan `example.env` (jika ada) atau pastikan variabel lingkungan yang diperlukan diatur. Contoh variabel yang mungkin dibutuhkan:
    ```env
    DATABASE_URL="postgresql+asyncpg://user:password@db:5432/mydatabase"
    SECRET_KEY="your-super-secret-key"
    ALGORITHM="HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES=30
    PINECONE_API_KEY="your-pinecone-api-key"
    PINECONE_ENVIRONMENT="your-pinecone-environment"
    GEMINI_API_KEY="your-gemini-api-key"
    ```

3.  **Bangun dan Jalankan Kontainer:**
    ```bash
    docker-compose up --build -d
    ```
    Ini akan membangun image Docker, membuat kontainer untuk aplikasi dan database PostgreSQL, lalu menjalankannya di latar belakang.

4.  **Inisialisasi Database:**
    Setelah kontainer berjalan, Anda perlu menginisialisasi skema database. Anda bisa masuk ke dalam kontainer aplikasi dan menjalankan skrip inisialisasi:
    ```bash
    docker exec -it <nama_kontainer_aplikasi> bash
    # Di dalam kontainer:
    python app/database/init_db.py
    exit
    ```
    Ganti `<nama_kontainer_aplikasi>` dengan nama kontainer aplikasi Anda (misalnya, `company-chatbot-v2-app-1` atau serupa, Anda bisa melihatnya dengan `docker-compose ps`).

5.  **Akses Aplikasi:**
    Aplikasi akan tersedia di `http://localhost:8000`.
    Dokumentasi API interaktif (Swagger UI) dapat diakses di `http://localhost:8000/docs`.

### Tanpa Docker (Lingkungan Lokal)

1.  **Clone Repositori:**
    ```bash
    git clone https://github.com/your-repo/company-chatbot-v2.git
    cd company-chatbot-v2
    ```

2.  **Buat dan Aktifkan Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instal Dependensi:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Konfigurasi Environment:**
    Buat file `.env` di root proyek Anda berdasarkan `example.env` (jika ada) atau atur variabel lingkungan yang diperlukan. Pastikan `DATABASE_URL` menunjuk ke instance PostgreSQL lokal Anda (misalnya, `postgresql+asyncpg://user:password@localhost:5432/mydatabase`).

5.  **Siapkan Database PostgreSQL:**
    Pastikan Anda memiliki server PostgreSQL yang berjalan secara lokal. Buat database baru dan pengguna jika diperlukan.

6.  **Inisialisasi Database:**
    ```bash
    python -m app/database/init_db
    ```

7.  **Jalankan Aplikasi:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

8.  **Akses Aplikasi:**
    Aplikasi akan tersedia di `http://localhost:8000`.
    Dokumentasi API interaktif (Swagger UI) dapat diakses di `http://localhost:8000/docs`.



## Authentication and Approval Flow

Aplikasi ini menggunakan alur registrasi dan persetujuan multi-tingkat yang melibatkan tiga jenis pengguna: Pengguna Baru, Admin Perusahaan, dan Super Admin.

1.  **Pendaftaran (Unified Endpoint)**
    - Seorang pengguna baru dapat mendaftar dengan dua cara melalui satu endpoint `POST /auth/register`:
        - **Mendaftarkan Perusahaan Baru**: Dengan menyertakan detail perusahaan (`company_name`, `company_code`), sebuah perusahaan baru akan dibuat dengan status `pending approval`, dan pengguna akan menjadi `Company Admin` untuk perusahaan tersebut.
        - **Bergabung dengan Perusahaan**: Dengan menyertakan `company_id` dari perusahaan yang sudah ada, pengguna akan mendaftar sebagai `Employee` dengan status `pending approval`.

2.  **Persetujuan Perusahaan (Super Admin)**
    - Seorang `Super Admin` (dibuat manual atau melalui script) dapat melihat semua perusahaan yang menunggu persetujuan melalui `GET /admin/companies/pending`.
    - Super Admin kemudian dapat menyetujui perusahaan menggunakan `POST /admin/companies/{company_id}/approve`. Setelah disetujui, perusahaan dan adminnya menjadi aktif.

3.  **Persetujuan Karyawan (Company Admin)**
    - `Company Admin` dari perusahaan yang sudah disetujui dapat melihat karyawan yang menunggu persetujuan di perusahaannya melalui `GET /company/pending-employees`.
    - Company Admin dapat menyetujui karyawan menggunakan `POST /company/employees/{user_id}/approve`, yang mengaktifkan akun karyawan tersebut.

4.  **Login**
    - Setelah akun mereka aktif (baik oleh Super Admin atau Company Admin), pengguna dapat login melalui `POST /auth/token` untuk mendapatkan token akses JWT.

### User Roles

- **Super Admin**: Memiliki hak akses tertinggi untuk mengelola seluruh platform, termasuk menyetujui atau menolak pendaftaran perusahaan baru.
- **Company Admin**: Hak akses administratif untuk satu perusahaan, termasuk mengelola (menyetujui/menolak) pendaftaran karyawan baru di perusahaannya.
- **Employee**: Pengguna standar yang dapat berinteraksi dengan chatbot setelah disetujui oleh Company Admin.

### Token Structure

```json
{
  "sub": "user@example.com",
  "role": "admin",
  "company_id": 1,
  "exp": 1709556000
}
```

---

## API Endpoints

### 1. Health and Status

#### Root Endpoint
- **Endpoint**: `GET /`
- **Deskripsi**: Memeriksa apakah API berjalan.
- **Authentication**: Tidak perlu.

#### Health Check
- **Endpoint**: `GET /health`
- **Deskripsi**: Memberikan status kesehatan API.
- **Authentication**: Tidak perlu.

---

### 2. Authentication

#### 1. Unified User & Company Registration
- **Endpoint**: `POST /auth/register`
- **Deskripsi**: Titik masuk tunggal untuk registrasi. Dapat membuat perusahaan baru atau mendaftarkan karyawan ke perusahaan yang sudah ada.
- **Authentication**: Tidak perlu.
- **Request Body (Untuk Perusahaan Baru)**:
  ```json
  {
    "name": "Admin Utama",
    "email": "admin.utama@cemerlang.com",
    "password": "SuperSecretAdminPass!",
    "company_name": "PT Cemerlang Jaya",
    "company_code": "CMJ"
  }
  ```
- **Request Body (Untuk Karyawan Baru)**:
  *Catatan: Untuk mendaftar sebagai karyawan, sertakan `company_id` dan hilangkan `company_name` & `company_code`.*
  ```json
  {
    "name": "Budi Karyawan",
    "email": "budi.k@cemerlang.com",
    "password": "SecurePassword123!",
    "company_id": 1
  }
  ```
- **Response 201 (Sukses)**: Mengembalikan pesan konfirmasi.
  ```json
  // Contoh untuk perusahaan baru
  {
    "message": "Company 'PT Cemerlang Jaya' and admin user 'admin.utama@cemerlang.com' registered successfully. Pending approval from a super admin."
  }
  // Contoh untuk karyawan baru
  {
    "message": "User 'budi.k@cemerlang.com' registered for company ID 1. Pending approval from the company admin."
  }
  ```
---

#### 2. Login Pengguna Aktif
- **Endpoint**: `POST /auth/token`
- **Deskripsi**: Mendapatkan JWT. Hanya pengguna dengan akun aktif yang bisa login.
- **Authentication**: Tidak perlu.
- **Request Body** (`application/json`):
  - `email`: email pengguna
  - `password`: password pengguna

---

#### 3. Get Current User
- **Endpoint**: `GET /auth/me`
- **Deskripsi**: Mendapatkan detail pengguna yang sedang login.
- **Authentication**: **Token Diperlukan**.

---

### 3. Super Admin

Endpoint khusus untuk pengguna dengan `is_super_admin = true`.

#### List Pending Companies
- **Endpoint**: `GET /admin/companies/pending`
- **Deskripsi**: Mendapatkan daftar perusahaan yang menunggu persetujuan.
- **Authentication**: **Super Admin Token Diperlukan**.

#### Approve Company
- **Endpoint**: `POST /admin/companies/{company_id}/approve`
- **Deskripsi**: Menyetujui pendaftaran perusahaan, mengaktifkan perusahaan dan adminnya.
- **Authentication**: **Super Admin Token Diperlukan**.
- **Path Parameter**:
  - `company_id` (int): ID perusahaan yang akan disetujui.

---

### 4. Companies & Company Admin

#### List Pending Employees (Company Admin)
- **Endpoint**: `GET /companies/pending-employees`
- **Deskripsi**: Mendapatkan daftar pengguna yang menunggu persetujuan di perusahaan admin.
- **Authentication**: **Company Admin Token Diperlukan** (Header: `Authorization: Bearer <token>`).
- **Request Body**: Tidak ada (kosong).
- **Response 200 (Sukses)**: Mengembalikan array berisi objek pengguna yang berstatus `pending`.
  ```json
  [
    {
      "id": 12,
      "name": "Calon Karyawan Satu",
      "email": "calon.satu@example.com",
      "is_super_admin": false,
      "is_active_in_company": false,
      "role": "employee",
      "company_id": 1,
      "division_id": null
    },
    {
      "id": 15,
      "name": "Calon Karyawan Dua",
      "email": "calon.dua@example.com",
      "is_super_admin": false,
      "is_active_in_company": false,
      "role": "employee",
      "company_id": 1,
      "division_id": 2
    }
  ]
  ```

#### Approve Employee (Company Admin)
- **Endpoint**: `POST /companies/employees/{user_id}/approve`
- **Deskripsi**: Menyetujui pendaftaran pengguna, mengubah statusnya menjadi `active`.
- **Authentication**: **Admin Token Diperlukan**.
- **Path Parameter**:
  - `user_id` (int): ID pengguna yang akan disetujui.
- **Response 200 (Sukses)**:
  ```json
  {
    "id": 2,
    "name": "Budi Karyawan",
    "email": "budi.k@cemerlang.com",
    "status": "active",
    "role": "employee"
  }
  ```

#### Reject Employee (Company Admin)
- **Endpoint**: `POST /companies/employees/{user_id}/reject`
- **Deskripsi**: Menolak dan menghapus permintaan pendaftaran pengguna.
- **Authentication**: **Admin Token Diperlukan**.
- **Path Parameter**:
  - `user_id` (int): ID pengguna yang akan ditolak.
- **Response 200 (Sukses)**:
  ```json
  {
    "message": "User with id 2 has been rejected and deleted."
  }
  ```

#### List Companies
- **Endpoint**: `GET /companies/`
- **Deskripsi**: Mendapatkan daftar semua perusahaan. Berguna untuk halaman pendaftaran.
- **Authentication**: Tidak perlu.
- **Response 200 (Sukses)**:
  ```json
  [
    {
      "id": 1,
      "name": "PT Cemerlang Jaya",
      "code": "CMJ"
    },
    {
      "id": 2,
      "name": "PT Maju Mundur",
      "code": "MJM"
    }
  ]
  ```

#### Get Company by ID
- **Endpoint**: `GET /companies/{company_id}`
- **Deskripsi**: Mendapatkan detail perusahaan berdasarkan ID.
- **Authentication**: Tidak perlu.
- **Path Parameter**:
  - `company_id` (int): ID unik perusahaan.
- **Response 200 (Sukses)**:
  ```json
  {
    "id": 1,
    "name": "PT Cemerlang Jaya",
    "code": "CMJ"
  }
  ```

#### Get Company Users (Company Admin)
- **Endpoint**: `GET /companies/{company_id}/users/`
- **Deskripsi**: Mendapatkan daftar semua pengguna (aktif dan pending) untuk sebuah perusahaan.
- **Authentication**: **Token Diperlukan**.
- **Path Parameter**:
  - `company_id` (int): ID unik perusahaan.
- **Response 200 (Sukses)**:
  ```json
  [
    {
      "id": 1,
      "name": "Admin Utama",
      "email": "admin.utama@cemerlang.com",
      "role": "admin",
      "status": "active"
    },
    {
      "id": 2,
      "name": "Budi Karyawan",
      "email": "budi.k@cemerlang.com",
      "role": "employee",
      "status": "pending_approval"
    }
  ]
  ```

#### Create New Company Admin (Company Admin)
- **Endpoint**: `POST /admin/create-admin`
- **Deskripsi**: Membuat pengguna admin baru untuk perusahaan yang sama. Hanya admin yang bisa melakukan ini.
- **Authentication**: **Admin Token Diperlukan**.
- **Request Body**:
  ```json
  {
    "name": "Admin Baru",
    "email": "admin.baru@cemerlang.com",
    "password": "SuperSecretAdminPass!"
  }
  ```
- **Response 200 (Sukses)**:
  ```json
  {
    "id": 4,
    "name": "Admin Baru",
    "email": "admin.baru@cemerlang.com",
    "status": "active",
    "role": "admin",
    "Companyid": 1,
    "Divisionid": null
  }
  ```

---

### 4. Divisions

#### Create Division
- **Endpoint**: `POST /divisions/`
- **Deskripsi**: Membuat divisi baru dalam perusahaan admin yang sedang login. Hanya admin yang bisa membuat divisi.
- **Authentication**: **Admin Token Diperlukan**.
- **Request Body**:
  ```json
  {
    "name": "Divisi Marketing"
  }
  ```
- **Response 201 (Sukses)**:
  ```json
  {
    "id": 1,
    "name": "Divisi Marketing",
    "Companyid": 1
  }
  ```

#### List Divisions
- **Endpoint**: `GET /divisions/`
- **Deskripsi**: Mendapatkan semua divisi dalam perusahaan pengguna yang sedang login.
- **Authentication**: **Token Diperlukan**.
- **Response 200 (Sukses)**:
  ```json
  [
    {
      "id": 1,
      "name": "Divisi Marketing",
      "Companyid": 1
    },
    {
      "id": 2,
      "name": "Divisi IT",
      "Companyid": 1
    }
  ]
  ```

#### List Public Divisions by Company ID
- **Endpoint**: `GET /divisions/public/{company_id}`
- **Deskripsi**: Mendapatkan daftar divisi untuk perusahaan tertentu. Berguna untuk pendaftaran mandiri karyawan yang belum terotentikasi agar dapat memilih divisi mereka.
- **Authentication**: Tidak perlu.
- **Path Parameter**:
  - `company_id` (int): ID unik perusahaan.
- **Response 200 (Sukses)**:
  ```json
  [
    {
      "id": 1,
      "name": "Divisi Marketing",
      "Companyid": 1
    },
    {
      "id": 2,
      "name": "Divisi IT",
      "Companyid": 1
    }
  ]
  ```

---

### 5. Documents (RAG)

#### Upload Document
- **Endpoint**: `POST /documents/upload`
- **Deskripsi**: Upload dokumen (PDF) ke knowledge base perusahaan. Dokumen akan diproses dan di-embed ke vector database.
- **Authentication**: **Token Diperlukan**.
- **Request Body**: `multipart/form-data`
  - `file`: File dokumen yang akan diunggah.
- **Response 200 (Sukses)**:
  ```json
  {
    "status": "success",
    "message": "Document 'nama_file.pdf' processed and added to Pinecone for company 1.",
    "chunks_added": 10
  }
  ```

#### OCR - Extract Text from Scanned Document/Image
- **Endpoint**: `POST /documents/ocr-extract`
- **Deskripsi**: Mengunggah dokumen hasil scan (PDF) atau gambar yang berisi teks untuk diekstraksi menggunakan OCR. Teks yang diekstrak akan dikembalikan untuk pratinjau.
- **Authentication**: **Token Diperlukan**.
- **Request Body**: `multipart/form-data`
  - `file`: File gambar (JPG, PNG, TIFF, BMP, WEBP) atau PDF hasil scan.
- **Response 200 (Sukses)**:
  ```json
  {
    "extracted_text": "Teks yang berhasil diekstrak dari dokumen...",
    "temp_doc_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

#### OCR - Embed Confirmed Text to RAG
- **Endpoint**: `POST /documents/ocr-embed`
- **Deskripsi**: Mengirim teks yang telah dikonfirmasi (setelah pratinjau OCR) untuk di-embed ke dalam database vektor RAG. Ini akan membuat dokumen baru di knowledge base perusahaan.
- **Authentication**: **Token Diperlukan**.
- **Request Body**: `application/json`
  ```json
  {
    "temp_doc_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "confirmed_text": "Teks yang sudah dikonfirmasi dan siap untuk di-embedding.",
    "original_filename": "nama_file_scan.pdf"
  }
  ```
- **Response 200 (Sukses)**:
  ```json
  {
    "status": "success",
    "message": "Document 'nama_file_scan.pdf' processed and added to Pinecone for company 1.",
    "chunks_added": 15
  }
  ```

#### List Documents
- **Endpoint**: `GET /documents/`
- **Deskripsi**: Mendapatkan daftar nama file dokumen di knowledge base perusahaan.
- **Authentication**: **Token Diperlukan**.
- **Response 200 (Sukses)**:
  ```json
  {
    "documents": [
      "nama_file_1.pdf",
      "nama_file_2.pdf"
    ]
  }
  ```

#### Delete Document
- **Endpoint**: `DELETE /documents/{filename}`
- **Deskripsi**: Menghapus dokumen dari knowledge base perusahaan dan vector index-nya.
- **Authentication**: **Token Diperlukan**.
- **Path Parameter**:
  - `filename` (string): Nama file yang akan dihapus.
- **Response 200 (Sukses)**:
  ```json
  {
    "info": "File 'nama_file.pdf' and its embeddings have been deleted."
  }
  ```

---



### 6. AI Chat

#### Chat with AI
- **Endpoint**: `POST /chat`
- **Deskripsi**: Endpoint utama untuk berinteraksi dengan AI chatbot. Sistem akan mencari konteks relevan dari dokumen perusahaan sebelum menjawab.
- **Authentication**: **Token Diperlukan**.
- **Request Body**:
  ```json
  {
    "message": "Berapa total penjualan bulan ini?",
    "conversation_id": "optional-uuid-1234"
  }
  ```
- **Response 200 (Sukses)**:
  ```json
  {
    "response": "Berdasarkan laporan penjualan bulan ini, total penjualan mencapai Rp 1.2 Miliar.",
    "conversation_id": "optional-uuid-1234",
    "sources": [
      "laporan_penjualan_q3.pdf"
    ]
  }
  ```
  
---

### 7. Chatlogs

#### List Chatlogs
- **Endpoint**: `GET /chatlogs/`
- **Deskripsi**: Mendapatkan daftar riwayat percakapan untuk perusahaan. Admin dapat melihat semua log, employee hanya log miliknya.
- **Authentication**: **Token Diperlukan**.
- **Query Parameters**:
  - `user_id` (int, opsional): Filter berdasarkan ID pengguna (hanya admin).
  - `start_date` (string, YYYY-MM-DD, opsional): Filter tanggal mulai.
  - `end_date` (string, YYYY-MM-DD, opsional): Filter tanggal akhir.
  - `skip` (int, opsional, default: 0): Pagination offset.
  - `limit` (int, opsional, default: 100): Jumlah item per halaman.
- **Response 200 (Sukses)**:
  ```json
  [
    {
      "id": 1,
      "user_id": 2,
      "user_message": "Berapa total penjualan bulan ini?",
      "ai_response": "Berdasarkan laporan penjualan bulan ini, total penjualan mencapai Rp 1.2 Miliar.",
      "timestamp": "2024-10-28T10:30:00Z"
    }
  ]
  ```
---

## Response Codes

| Code | Status | Description |
|------|--------|-------------|
| **200** | OK | Request berhasil |
| **201** | Created | Resource berhasil dibuat |
| **400** | Bad Request | Request tidak valid |
| **401** | Unauthorized | Gagal otentikasi |
| **403** | Forbidden | Akses ditolak (misal: bukan admin) |
| **404** | Not Found | Resource tidak ditemukan |
| **422** | Unprocessable Entity | Error validasi |
| **500** | Internal Server Error | Terjadi error di server |
