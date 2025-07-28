import os

class Config:
    # Mengambil URL database dari variabel lingkungan 'DATABASE_URL'
    # Fallback ke SQLite untuk pengembangan lokal jika variabel tidak disetel.
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or "sqlite:///site.db"

    # Mengambil kunci rahasia dari variabel lingkungan 'SECRET_KEY'.
    # Penting: Gunakan kunci yang KUAT dan UNIK di PRODUKSI!
    # Nilai default ini HANYA untuk pengembangan lokal.
    SECRET_KEY = os.getenv("SECRET_KEY") or "f79de8e5a1f702a5352efedc856acf5285961c34bd0d1a65c92419260a9254ae0e335bf46aa706e6ae5bc546e290505b47863d3d66af9c94d9e1a7cedd578ae4"

    # URL dasar aplikasi, digunakan untuk membuat tautan pendek lengkap
    BASE_URL = os.getenv("BASE_URL")

    # Direktori tempat QR Code akan disimpan.
    # Menggunakan os.getenv dengan default agar bisa di-override di lingkungan.
    QR_CODE_DIR = os.path.join(os.getcwd(), os.getenv("QR_CODE_DIR", "static/qrcodes"))

    # Pastikan direktori QR Code ada. Jika belum, buatlah.
    if not os.path.exists(QR_CODE_DIR):
        os.makedirs(QR_CODE_DIR)

    # Matikan fitur pelacakan modifikasi SQLAlchemy yang tidak perlu
    # Ini menghemat memori dan meningkatkan performa
    SQLALCHEMY_TRACK_MODIFICATIONS = False