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
- [Authentication Flow](#authentication-flow)
  - [User Roles](#user-roles)
  - [Token Structure](#token-structure)
- [API Endpoints](#api-endpoints)
  - [1. Health and Status](#1-health-and-status)
  - [2. Authentication](#2-authentication)
  - [3. Companies](#3-companies)
  - [4. Divisions](#4-divisions)
  - [5. Documents (RAG)](#5-documents-rag)
  - [6. AI Chat](#6-ai-chat)
  - [7. Chatlogs](#7-chatlogs)
  - [8. Admin](#8-admin)
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

## Authentication Flow

Aplikasi ini menggunakan alur registrasi yang berbeda untuk admin pertama perusahaan dan untuk karyawan berikutnya.

1.  **Pendaftaran Perusahaan & Admin Pertama**
    - Pengguna baru mendaftarkan perusahaannya dan akun adminnya sekaligus melalui `POST /auth/company-signup`.
    - Akun admin ini langsung aktif dan menerima token untuk sesi pertama.

2.  **Pendaftaran Mandiri Karyawan**
    - Calon karyawan mendaftarkan diri ke perusahaan yang sudah ada menggunakan `POST /auth/register`.
    - Akun baru ini akan dibuat dengan status `pending_approval` dan belum bisa digunakan.

3.  **Persetujuan oleh Admin**
    - Admin perusahaan akan melihat daftar pendaftar di `GET /admin/pending-users`.
    - Admin dapat menyetujui pendaftaran melalui `POST /admin/users/{user_id}/approve`.

4.  **Login Karyawan**
    - Setelah disetujui, status karyawan menjadi `active`.
    - Karyawan tersebut sekarang dapat login melalui `POST /auth/token` untuk mendapatkan token akses.

### User Roles

- **admin**: Hak akses administratif, termasuk mengelola (menyetujui/menolak) pengguna.
- **employee**: Pengguna standar yang dapat berinteraksi dengan chatbot.

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

#### 1. Registrasi Perusahaan & Admin Pertama
- **Endpoint**: `POST /auth/company-signup`
- **Deskripsi**: Titik awal untuk perusahaan baru. Membuat perusahaan dan admin pertamanya, yang langsung berstatus `active`.
- **Authentication**: Tidak perlu.
- **Request Body**:
  ```json
  {
    "company_name": "PT Cemerlang Jaya",
    "company_code": "CMJ",
    "admin_name": "Admin Utama",
    "admin_email": "admin.utama@cemerlang.com",
    "admin_password": "SuperSecretAdminPass!"
  }
  ```
- **Response 201 (Sukses)**: Mengembalikan token akses untuk admin yang baru dibuat.
  ```json
  {
    "access_token": "...",
    "token_type": "bearer"
  }
  ```

---

#### 2. Registrasi Mandiri Karyawan
- **Endpoint**: `POST /auth/register`
- **Deskripsi**: Karyawan mendaftarkan diri ke perusahaan yang sudah ada. Akun akan dibuat dengan status `pending_approval`.
- **Authentication**: Tidak perlu.
- **Request Body**:
  ```json
  {
    "name": "Budi Karyawan",
    "email": "budi.k@cemerlang.com",
    "password": "SecurePassword123!",
    "role": "employee",
    "Companyid": 1,
    "Divisionid": 1
  }
  ```
- **Response 201 (Sukses)**: Mengembalikan detail pengguna dengan status `pending_approval`.
  ```json
  {
    "id": 2,
    "name": "Budi Karyawan",
    "email": "budi.k@cemerlang.com",
    "status": "pending_approval",
    "role": "employee",
    "Companyid": 1,
    "Divisionid": 1
  }
  ```

---

#### 3. Login Pengguna Aktif
- **Endpoint**: `POST /auth/token`
- **Deskripsi**: Mendapatkan JWT. Hanya pengguna dengan status `active` yang bisa login.
- **Authentication**: Tidak perlu.
- **Form Data** (`application/x-www-form-urlencoded`):
  - `username`: email pengguna
  - `password`: password pengguna

---

#### Get Current User
- **Endpoint**: `GET /auth/me`
- **Deskripsi**: Mendapatkan detail pengguna yang sedang login.
- **Authentication**: **Token Diperlukan**.
- **Response 200 (Sukses)**:
  ```json
  {
    "id": 1,
    "name": "Admin Utama",
    "email": "admin.utama@cemerlang.com",
    "role": "admin",
    "status": "active",
    "Companyid": 1,
    "Divisionid": null
  }
  ```

---

### 3. Companies

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

#### Get Company Users
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
    "filename": "nama_file.pdf",
    "info": "File uploaded and processing started."
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

### 8. Admin

Endpoint khusus untuk pengguna dengan peran `admin`.

#### List Pending Users
- **Endpoint**: `GET /admin/pending-users`
- **Deskripsi**: Mendapatkan daftar pengguna yang menunggu persetujuan di perusahaan admin.
- **Authentication**: **Admin Token Diperlukan**.
- **Response 200 (Sukses)**:
  ```json
  [
    {
      "id": 2,
      "name": "Budi Karyawan",
      "email": "budi.k@cemerlang.com",
      "status": "pending_approval",
      "role": "employee"
    }
  ]
  ```

#### Approve User
- **Endpoint**: `POST /admin/users/{user_id}/approve`
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

#### Reject User
- **Endpoint**: `POST /admin/users/{user_id}/reject`
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
