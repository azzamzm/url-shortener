# models.py
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Inisialisasi objek SQLAlchemy. Kita akan mengikatnya ke aplikasi Flask di app.py
db = SQLAlchemy()

# Model untuk tabel 'users'
class User(db.Model):
    __tablename__ = 'users' # Nama tabel di database

    id = db.Column(db.Integer, primary_key=True) # Kunci utama, otomatis bertambah
    username = db.Column(db.String(80), unique=True, nullable=False) # Harus unik, tidak boleh kosong
    email = db.Column(db.String(120), unique=True, nullable=False) # Harus unik, tidak boleh kosong
    password_hash = db.Column(db.String(100000), nullable=False) # Hash kata sandi, tidak boleh kosong
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Waktu pembuatan akun, default UTC

    # Menentukan hubungan: satu User bisa memiliki banyak ShortUrl
    short_urls = db.relationship('ShortUrl', backref='creator', lazy=True)

    # Metode untuk mengatur (hash) kata sandi
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    # Metode untuk memeriksa kata sandi
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Model untuk tabel 'short_urls'
class ShortUrl(db.Model):
    __tablename__ = 'short_urls' # Nama tabel di database

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True) # Kunci asing ke User, bisa kosong (tamu)
    original_url = db.Column(db.Text, nullable=False) # URL asli yang panjang, tidak boleh kosong
    short_code = db.Column(db.String(10), unique=True, nullable=False, index=True) # Kode pendek unik, tidak boleh kosong, diindeks untuk pencarian cepat
    custom_alias = db.Column(db.String(50), unique=True, nullable=True) # Alias kustom, bisa kosong, harus unik
    qr_code_path = db.Column(db.String(255), nullable=True) # Path ke gambar QR Code, bisa kosong
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # Waktu pembuatan, default UTC
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Waktu update terakhir
    is_active = db.Column(db.Boolean, default=True) # Status tautan (aktif/nonaktif)

    # Menentukan hubungan: satu ShortUrl bisa memiliki banyak Click
    clicks = db.relationship('Click', backref='short_link', lazy=True)

    def __repr__(self):
        return f'<ShortUrl {self.short_code} -> {self.original_url}>'

# Model untuk tabel 'clicks' (untuk analitik)
class Click(db.Model):
    __tablename__ = 'clicks' # Nama tabel di database

    id = db.Column(db.Integer, primary_key=True)
    short_url_id = db.Column(db.Integer, db.ForeignKey('short_urls.id'), nullable=False) # Kunci asing ke ShortUrl
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow) # Waktu klik, default UTC
    ip_address = db.Column(db.String(45), nullable=True) # Alamat IP, bisa kosong (pertimbangan privasi)
    referrer = db.Column(db.String(255), nullable=True) # Dari mana klik berasal, bisa kosong
    user_agent = db.Column(db.Text, nullable=True) # Informasi browser/OS, bisa kosong
    country = db.Column(db.String(50), nullable=True) # Negara asal klik, bisa kosong

    def __repr__(self):
        return f'<Click on {self.short_url_id} at {self.clicked_at}>'
    