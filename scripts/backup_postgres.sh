# !/bin/bash

# --- 1. Konfigurasi Awal & Loading ENV ---

# Tentukan jalur absolut ke file konfigurasi Anda
CONFIG_FILE="config.env"

# Muat variabel ke lingkungan shell
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "$(date +"%Y-%m-%d %H:%M:%S") - ERROR: File konfigurasi tidak ditemukan di $CONFIG_FILE" >> "$LOG_FILE"
    exit 1
fi

# --- Fungsi Logging ---
log_message() {
    echo "$(date +"%Y-%m-%d %H:%M:%S") - $1" >> "$LOG_FILE"
}

# --- Pastikan Direktori Backup Lokal Sementara Ada ---
mkdir -p "$BACKUP_DIR" || { log_message "ERROR: Gagal membuat direktori: $BACKUP_DIR"; exit 1; }

# --- Nama File Backup ---
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOCAL_BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
REMOTE_BACKUP_FILE="${R2_BACKUP_PATH}${DB_NAME}_${TIMESTAMP}.sql.gz"

# --- 2. Mulai Proses Backup Lokal (pg_dump) ---
log_message "Memulai backup database: ${DB_NAME}"

# PGDUMP_CMD menggunakan jalur absolut versi 16 untuk mencegah 'command not found'
PGDUMP_CMD="/usr/lib/postgresql/16/bin/pg_dump -Fc -h ${PG_HOST} -p ${PG_PORT} -U ${PG_USER} -d ${DB_NAME}"

if eval "$PGDUMP_CMD" | gzip > "$LOCAL_BACKUP_FILE"; then
    log_message "Backup lokal berhasil dibuat: ${LOCAL_BACKUP_FILE}"
else
    log_message "ERROR: Backup database lokal ${DB_NAME} gagal. Menghapus file parsial."
    rm -f "$LOCAL_BACKUP_FILE"
    exit 1
fi

# --- 3. Unggah ke R2 Cloud (Off-site) ---
log_message "Mengunggah ${LOCAL_BACKUP_FILE} ke R2..."

if aws --endpoint-url "${R2_ENDPOINT_URL}" \
     --region auto \
     s3 cp "${LOCAL_BACKUP_FILE}" "s3://${R2_BUCKET_NAME}/${REMOTE_BACKUP_FILE}" \
     --acl public-read; then
    
    log_message "Upload ke R2 berhasil: ${REMOTE_BACKUP_FILE}"
    log_message "Menghapus file lokal."
    rm -f "$LOCAL_BACKUP_FILE"
else
    log_message "ERROR: Upload ke R2 gagal. File lokal tetap dipertahankan."
    exit 1
fi

log_message "Proses backup dan upload selesai."
exit 0