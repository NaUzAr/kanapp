#!/bin/bash

# --- Konfigurasi Awal & Peringatan Keamanan ---
echo "Skrip ini akan mengkonfigurasi PostgreSQL untuk akses jarak jauh."
echo "PERINGATAN: Aturan firewall dan pg_hba.conf akan diatur untuk mengizinkan koneksi dari SEMUA alamat IP (0.0.0.0/0)."
echo "Untuk lingkungan produksi, sangat disarankan untuk mengganti 0.0.0.0/0 dengan alamat IP spesifik yang Anda percayai."
read -p "Tekan [Enter] untuk melanjutkan atau [Ctrl+C] untuk membatalkan..."

# --- 1. Temukan Direktori Konfigurasi PostgreSQL ---
# Menemukan versi PostgreSQL yang aktif dan path konfigurasinya
PG_VERSION=$(pg_lsclusters -h | awk 'NR==2 {print $1}')
PG_CONF_DIR="/etc/postgresql/${PG_VERSION}/main"

if [ ! -d "$PG_CONF_DIR" ]; then
    echo "Direktori konfigurasi PostgreSQL tidak ditemukan di $PG_CONF_DIR. Keluar."
    exit 1
fi

echo "Direktori Konfigurasi PostgreSQL ditemukan di: $PG_CONF_DIR"

# File konfigurasi
PG_CONF_FILE="${PG_CONF_DIR}/postgresql.conf"
PG_HBA_FILE="${PG_CONF_DIR}/pg_hba.conf"


# --- 2. Cadangkan File Konfigurasi ---
echo "Membuat cadangan file konfigurasi..."
sudo cp "${PG_CONF_FILE}" "${PG_CONF_FILE}.bak_$(date +%F)"
sudo cp "${PG_HBA_FILE}" "${PG_HBA_FILE}.bak_$(date +%F)"
echo "Cadangan berhasil dibuat dengan akhiran .bak_TANGGAL"


# --- 3. Ubah postgresql.conf ---
echo "Mengubah listen_addresses di ${PG_CONF_FILE}..."
# Mengubah atau menambahkan 'listen_addresses = '*'
if sudo grep -q "^#listen_addresses" "${PG_CONF_FILE}"; then
    # Jika barisnya dikomentari, hapus komentar dan ubah nilainya
    sudo sed -i "s/^#listen_addresses = 'localhost'/listen_addresses = '*'/" "${PG_CONF_FILE}"
elif sudo grep -q "^listen_addresses" "${PG_CONF_FILE}"; then
    # Jika barisnya sudah ada, ubah nilainya
    sudo sed -i "s/^listen_addresses = .*/listen_addresses = '*'/" "${PG_CONF_FILE}"
else
    # Jika tidak ada sama sekali, tambahkan di akhir
    echo "listen_addresses = '*'" | sudo tee -a "${PG_CONF_FILE}" > /dev/null
fi

# Verifikasi perubahan
echo "Verifikasi perubahan di postgresql.conf:"
sudo grep "^listen_addresses" "${PG_CONF_FILE}"


# --- 4. Ubah pg_hba.conf ---
echo "Menambahkan aturan koneksi jarak jauh ke ${PG_HBA_FILE}..."
# Menambahkan aturan untuk mengizinkan semua koneksi IPv4 dengan password
echo "# Aturan untuk mengizinkan koneksi jarak jauh (ditambahkan oleh skrip)" | sudo tee -a "${PG_HBA_FILE}" > /dev/null
echo "host    all             all             0.0.0.0/0               md5" | sudo tee -a "${PG_HBA_FILE}" > /dev/null

# Verifikasi perubahan
echo "Verifikasi perubahan di pg_hba.conf:"
sudo tail -n 2 "${PG_HBA_FILE}"


# --- 5. Konfigurasi Firewall (UFW) ---
if command -v ufw &> /dev/null; then
    echo "Mengkonfigurasi firewall UFW..."
    sudo ufw allow 5432/tcp
    sudo ufw reload
    echo "Status UFW:"
    sudo ufw status
else
    echo "Peringatan: Perintah 'ufw' tidak ditemukan. Lewati konfigurasi firewall."
    echo "Pastikan Anda membuka port 5432/tcp secara manual jika ada firewall lain yang aktif."
fi


# --- 6. Restart Layanan PostgreSQL ---
echo "Me-restart layanan PostgreSQL untuk menerapkan perubahan..."
sudo systemctl restart postgresql.service

# Cek status layanan setelah restart
echo "Status layanan PostgreSQL:"
sudo systemctl is-active postgresql.service


echo -e "\nKonfigurasi selesai. Server PostgreSQL Anda seharusnya sekarang dapat diakses dari luar."
echo "Gunakan alamat IP server Anda untuk terhubung."
