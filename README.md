# RAG Chatbot SaaS - Dokumentasi API Lengkap

## Alur Bisnis Utama

### 1. Pendaftaran & Persetujuan Perusahaan
- **Perusahaan baru** mendaftar melalui `/auth/register` dengan data perusahaan dan admin
- **Super Admin** meninjau permohonan di `/admin/companies/pending` dan dapat menyetujui/menolak
- Setelah **disetujui**, status perusahaan menjadi aktif dan Admin Perusahaan dapat login

### 2. Pengelolaan Internal Perusahaan
- **Admin Perusahaan** dapat:
  - Membuat divisi melalui `/divisions`
  - Mendaftarkan karyawan melalui `/companies/employees/register`
  - Mengunggah dokumen melalui `/documents/upload`
- **Dokumen** diproses secara asinkron melalui pipeline: Upload → OCR → Validasi → Embedding → Siap digunakan
- **Karyawan** dapat berinteraksi dengan chatbot menggunakan dokumen perusahaan melalui `/chat`

### 3. Interaksi Chat & Pelacakan
- Pengguna mengirim pesan ke `/chat` dan menerima respons dari sistem RAG
- Semua interaksi disimpan dalam **Chatlog** dengan `conversation_id` untuk melacak percakapan
- **Admin Perusahaan** dapat melihat riwayat chat pengguna di perusahaannya
- **Super Admin** dapat melihat semua riwayat chat dengan berbagai filter

---

## Dokumentasi Endpoint API

### 🔐 Autentikasi (`/api/v1/auth`)

#### POST `/auth/register` - Daftar Perusahaan Baru
**Deskripsi**: Mendaftarkan perusahaan baru beserta admin pertama. Perusahaan akan menunggu persetujuan Super Admin.

**Request Body**:
```json
{
  "name": "Admin Perusahaan",
  "email": "admin@perusahaan.com",
  "username": "adminperusahaan",
  "password": "password123",
  "company_name": "PT Perusahaan Baru"
}
```

**Response Sukses (201 Created)**:
```json
{
  "message": "Company 'PT Perusahaan Baru' and admin user 'admin@perusahaan.com' registered successfully. Pending approval from a super admin."
}
```

**Response Error**:
- `400 Bad Request`: Data tidak valid atau perusahaan sudah ada
- `409 Conflict`: Email/username sudah digunakan

---

#### POST `/auth/user/token` - Login & Dapatkan Token
**Deskripsi**: Mendapatkan token akses untuk autentikasi. Bisa login dengan email atau username.

**Request Body**:
```json
{
  "email": "admin@perusahaan.com",
  "password": "password123"
}
```
*ATAU*
```json
{
  "username": "adminperusahaan", 
  "password": "password123"
}
```

**Response Sukses (200 OK)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "name": "Admin Perusahaan",
    "username": "adminperusahaan",
    "email": "admin@perusahaan.com",
    "role": "admin",
    "company_id": 1,
    "division_id": null,
    "is_active": true,
    "company_pic_phone_number": "+628123456789"
  }
}
```

**Response Error**:
- `401 Unauthorized`: Kredensial salah atau user tidak aktif

---

#### GET `/auth/me` - Dapatkan Data Pengguna Saat Ini
**Deskripsi**: Mengembalikan data pengguna yang sedang login termasuk informasi perusahaan.

**Response Sukses (200 OK)**:
```json
{
  "id": 1,
  "name": "Admin Perusahaan",
  "username": "adminperusahaan",
  "email": "admin@perusahaan.com",
  "role": "admin",
  "company_id": 1,
  "division_id": null,
  "is_active": true,
  "company_pic_phone_number": "+628123456789"
}
```

---

### 👑 Super Admin (`/api/v1/admin`)

#### GET `/admin/companies/pending` - Lihat Perusahaan Menunggu Persetujuan
**Deskripsi**: Mendapatkan daftar perusahaan yang menunggu persetujuan Super Admin.

**Response Sukses (200 OK)**:
```json
[
  {
    "id": 1,
    "name": "PT Perusahaan Baru",
    "code": "PTPB",
    "logo_s3_path": null,
    "address": null,
    "is_active": false,
    "pic_phone_number": null
  }
]
```

---

#### PATCH `/admin/companies/{company_id}/approve` - Setujui Perusahaan
**Deskripsi**: Menyetujui pendaftaran perusahaan dan mengaktifkannya.

**Path Parameters**:
- `company_id`: ID perusahaan yang akan disetujui

**Response Sukses (200 OK)**:
```json
{
  "message": "Company PT Perusahaan Baru has been approved and is now active."
}
```

---

### 🏢 Perusahaan (`/api/v1/companies`)

#### POST `/companies/employees/register` - Daftar Karyawan Baru
**Deskripsi**: Admin perusahaan mendaftarkan karyawan baru.

**Request Body**:
```json
{
  "name": "Karyawan Baru",
  "email": "karyawan@perusahaan.com",
  "username": "karyawanbaru",
  "password": "password123",
  "division_id": 1
}
```

**Response Sukses (201 Created)**:
```json
{
  "id": 2,
  "name": "Karyawan Baru",
  "username": "karyawanbaru",
  "email": "karyawan@perusahaan.com",
  "role": "user",
  "company_id": 1,
  "division_id": 1,
  "is_active": true,
  "company_pic_phone_number": "+628123456789"
}
```

---

### 📁 Dokumen (`/api/v1/documents`)

#### POST `/documents/upload` - Upload Dokumen Baru
**Deskripsi**: Mengupload dokumen baru untuk diproses oleh sistem RAG. Dokumen akan melalui pipeline OCR → Validasi → Embedding.

**Form Data**:
- `file`: File dokumen (PDF, DOC, TXT, dll)
- `name`: Nama dokumen
- `tags`: Tag dokumen (opsional, dipisahkan koma)

**Response Sukses (202 Accepted)**:
```json
{
  "id": 1,
  "title": "Dokumen Perusahaan",
  "company_id": 1,
  "s3_path": null,
  "content_type": "application/pdf",
  "status": "UPLOADING",
  "tags": ["kebijakan", "internal"],
  "uploaded_at": "2025-11-02T10:30:00",
  "extracted_text": null
}
```

**Status Dokumen**:
- `UPLOADING`: Sedang diupload ke S3
- `UPLOADED`: Berhasil diupload, siap untuk OCR
- `OCR_PROCESSING`: Sedang diproses OCR
- `PENDING_VALIDATION`: Menunggu validasi teks oleh admin
- `EMBEDDING`: Sedang membuat embedding
- `COMPLETED`: Siap digunakan oleh chatbot
- `UPLOAD_FAILED`/`PROCESSING_FAILED`: Gagal, bisa di-retry

---

#### POST `/documents/{document_id}/confirm` - Konfirmasi Teks OCR
**Deskripsi**: Admin mengkonfirmasi teks hasil OCR dan memicu proses embedding.

**Path Parameters**:
- `document_id`: ID dokumen yang akan dikonfirmasi

**Request Body**:
```json
{
  "confirmed_text": "Ini adalah teks yang sudah dikoreksi oleh admin..."
}
```

**Response Sukses (202 Accepted)**:
```json
{
  "id": 1,
  "title": "Dokumen Perusahaan",
  "company_id": 1,
  "s3_path": "s3://bucket/documents/1.pdf",
  "content_type": "application/pdf",
  "status": "EMBEDDING",
  "tags": ["kebijakan", "internal"],
  "uploaded_at": "2025-11-02T10:30:00",
  "extracted_text": "Ini adalah teks yang sudah dikoreksi oleh admin..."
}
```

---

### 💬 Chat (`/api/v1/chat`)

#### POST `/chat` - Kirim Pesan ke Chatbot
**Deskripsi**: Mengirim pesan ke chatbot RAG dan mendapatkan respons berdasarkan dokumen perusahaan.

**Request Body**:
```json
{
  "message": "Apa kebijakan cuti perusahaan?",
  "conversation_id": "conv-12345" // Opsional, untuk melanjutkan percakapan
}
```

**Response Sukses (200 OK)**:
```json
{
  "reply": "Berdasarkan dokumen kebijakan perusahaan, karyawan berhak mendapatkan cuti tahunan sebanyak 12 hari kerja...",
  "conversation_id": "conv-12345"
}
```

---

### 📝 Chatlog (`/api/v1/chatlogs`)

#### GET `/chatlogs` - Lihat Riwayat Chat Sendiri
**Deskripsi**: Mendapatkan riwayat percakapan pengguna saat ini.

**Query Parameters**:
- `skip`: Jumlah data yang dilewati (default: 0)
- `limit`: Jumlah data yang dikembalikan (default: 100)
- `start_date`: Tanggal mulai filter (format: YYYY-MM-DD)
- `end_date`: Tanggal akhir filter (format: YYYY-MM-DD)

**Response Sukses (200 OK)**:
```json
[
  {
    "id": 1,
    "question": "Apa kebijakan cuti perusahaan?",
    "answer": "Berdasarkan dokumen kebijakan perusahaan, karyawan berhak mendapatkan cuti tahunan sebanyak 12 hari kerja...",
    "UsersId": 2,
    "company_id": 1,
    "conversation_id": "conv-12345"
  }
]
```

---

#### GET `/chatlogs/conversations` - Lihat Daftar ID Percakapan
**Deskripsi**: Mendapatkan daftar unique conversation ID untuk pengguna saat ini.

**Response Sukses (200 OK)**:
```json
[
  "conv-12345",
  "conv-67890"
]
```

---

### 🏢 Chatlog Admin Perusahaan (`/api/v1/company/chatlogs`)

#### GET `/company/chatlogs` - Lihat Riwayat Chat Perusahaan
**Deskripsi**: Admin perusahaan melihat riwayat chat semua pengguna di perusahaannya.

**Query Parameters**:
- `page`, `limit`: Pagination
- `division_id`: Filter berdasarkan divisi
- `user_id`: Filter berdasarkan user spesifik
- `start_date`, `end_date`: Filter berdasarkan tanggal
- `search`: Cari teks di pertanyaan, jawaban, username, atau conversation ID (min 2, max 100 karakter)

**Response**: Sama seperti endpoint chatlog user biasa, tapi mencakup semua pengguna di perusahaan.

---

### 👑 Chatlog Super Admin (`/api/v1/admin/chatlogs`)

#### GET `/admin/chatlogs` - Lihat Semua Riwayat Chat
**Deskripsi**: Super Admin melihat semua riwayat chat di seluruh sistem.

**Query Parameters**:
- `skip`, `limit`: Pagination
- `company_id`: Filter berdasarkan perusahaan
- `division_id`: Filter berdasarkan divisi  
- `user_id`: Filter berdasarkan user spesifik
- `start_date`, `end_date`: Filter berdasarkan tanggal

**Response**: Sama seperti endpoint chatlog lainnya, tapi mencakup seluruh sistem.
