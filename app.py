# app.py
from flask import Flask, request, redirect, jsonify, render_template, session, url_for, g, flash
from models import db, User, ShortUrl, Click
from config import Config
import string
import random
import qrcode
import os
import jwt
from datetime import datetime, timedelta, timezone
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError # Import IntegrityError untuk penanganan error database

import logging
logging.basicConfig(level=logging.INFO)

# --- Inisialisasi Aplikasi Flask ---
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Pastikan direktori QR Codes ada dan dapat ditulisi
# Ini adalah tempat yang baik untuk mendefinisikan path ini
QR_CODES_FOLDER = os.path.join(app.root_path, 'static', 'qrcodes')
os.makedirs(QR_CODES_FOLDER, exist_ok=True) # Pastikan folder dibuat saat aplikasi dimulai

app.logger.setLevel(logging.INFO) # Pastikan baris ini ada setelah 'app = Flask(__name__)'

# --- PENTING: Membuat Tabel Database (Pastikan ini ada!) ---
with app.app_context():
    db.create_all()

# --- Context Processor (Pastikan ini ada!) ---
@app.context_processor
def inject_user_and_username():
    username = None
    if g.user:
        username = g.user.username
    return dict(username=username)

# --- Before Request untuk Memuat Pengguna (Pastikan ini ada!) ---
@app.before_request
def load_logged_in_user():
    token = session.get('token')
    g.user = None
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            # Menggunakan Session.get() untuk SQLAlchemy 2.0
            g.user = db.session.get(User, payload['user_id']) # Perbaikan: Gunakan db.session.get()
        except jwt.ExpiredSignatureError:
            session.pop('token', None) # Token expired, hapus dari sesi
            flash('Sesi Anda telah berakhir, silakan masuk kembali.', 'info')
        except jwt.InvalidTokenError:
            session.pop('token', None) # Token tidak valid
            flash('Token tidak valid, silakan masuk kembali.', 'error')

# --- Fungsi Pembantu (Helper Functions) ---
def generate_short_code(length=6):
    characters = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choice(characters) for i in range(length))
        if not ShortUrl.query.filter_by(short_code=code).first():
            return code

def login_required(view):
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('Anda harus masuk untuk mengakses halaman ini.', 'warning')
            return redirect(url_for('auth')) # Redirect ke halaman auth
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__ # Penting untuk Flask
    return wrapped_view

# --- Rute Aplikasi ---

@app.route('/')
def index():
    return render_template('index.html')

# --- Rute Autentikasi ---

# Ini adalah rute utama untuk menampilkan formulir login/register
# Ini yang harus memiliki endpoint 'auth'
@app.route('/auth', methods=['GET'], endpoint='auth')
def show_auth_form():
    if g.user:
        # Jika pengguna sudah login, arahkan ke dashboard
        return redirect(url_for('dashboard'))
    # Jika belum login, tampilkan halaman autentikasi
    return render_template('auth.html')

# Rute untuk proses register
@app.route('/register', methods=['POST'])
def register():
    if g.user:
        return redirect(url_for('dashboard'))

    username = request.form.get('username')
    email = request.form.get('email') # Ambil email dari form
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password') # Asumsikan Anda memiliki ini di form

    # --- Validasi Input ---
    if not username or not password or not email or not confirm_password: # Tambahkan 'email' dan 'confirm_password'
        flash('Semua kolom harus diisi.', 'error') # Pesan lebih umum
        return redirect(url_for('auth')) # Redirect kembali ke halaman auth

    if password != confirm_password: # Validasi konfirmasi password
        flash('Konfirmasi kata sandi tidak cocok.', 'error')
        return redirect(url_for('auth'))

    # --- Cek Pengguna/Email yang Sudah Ada ---
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Nama pengguna sudah terdaftar. Silakan pilih nama lain.', 'error')
        return redirect(url_for('auth'))

    existing_email = User.query.filter_by(email=email).first() # Cek apakah email sudah terdaftar
    if existing_email:
        flash('Email ini sudah terdaftar. Silakan gunakan email lain atau masuk.', 'error')
        return redirect(url_for('auth'))

    # --- Buat Pengguna Baru ---
    hashed_password = generate_password_hash(password)
    new_user = User(
        username=username,
        email=email, # Berikan nilai email ke model User
        password_hash=hashed_password
    )
    db.session.add(new_user)
    
    try:
        db.session.commit() # Coba commit perubahan
        flash('Registrasi berhasil! Silakan masuk.', 'success')
        return redirect(url_for('auth'))
    except Exception as e:
        db.session.rollback() # Jika ada error database (misal: constraint violation lainnya), batalkan transaksi
        flash(f'Terjadi kesalahan saat registrasi: {e}', 'error') # Tampilkan pesan error
        app.logger.error(f"Error during registration: {e}") # Log error untuk debugging lebih lanjut
        return redirect(url_for('auth'))

# Rute untuk proses login
@app.route('/login', methods=['POST'])
def login():
    if g.user:
        return redirect(url_for('dashboard'))

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        flash('Nama pengguna dan kata sandi harus diisi.', 'error')
        return redirect(url_for('auth'))

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        token = jwt.encode({'user_id': user.id, 'exp': datetime.now(timezone.utc) + timedelta(hours=24)},
                            app.config['SECRET_KEY'], algorithm='HS256')
        session['token'] = token
        flash('Berhasil masuk!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Kredensial tidak valid. Silakan coba lagi.', 'error')
        return redirect(url_for('auth'))

# Rute untuk logout
@app.route('/logout')
def logout():
    session.pop('token', None)
    g.user = None
    flash('Anda telah keluar.', 'info')
    return redirect(url_for('index'))

# --- Rute Dashboard ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- Rute API shorten: ---
@app.route('/api/shorten', methods=['POST'])
# @login_required # Opsional: Jika Anda ingin hanya pengguna login yang bisa memendekkan
def shorten_url_api():
    original_url = request.json.get('original_url')
    custom_alias = request.json.get('custom_alias')

    if not original_url:
        return jsonify({'error': 'URL asli diperlukan'}), 400

    if not original_url.startswith(('http://', 'https://')):
        original_url = 'http://' + original_url

    existing_short_url = None
    if g.user:
        existing_short_url = ShortUrl.query.filter_by(
            original_url=original_url,
            user_id=g.user.id
        ).first()
    else:
        existing_short_url = ShortUrl.query.filter_by(
            original_url=original_url,
            user_id=None
        ).first()

    if existing_short_url:
        short_code = existing_short_url.short_code
        # PERBAIKAN: Pastikan QR code URL menggunakan forward slashes saat diambil dari DB
        qr_code_url_from_db = None
        if existing_short_url.qr_code_path:
            # Mengganti backslash dengan forward slash jika ada
            clean_qr_path = existing_short_url.qr_code_path.replace('\\', '/')
            qr_code_url_from_db = url_for('static', filename=clean_qr_path)

        return jsonify({
            'short_url': url_for('redirect_to_original', short_code=short_code, _external=True),
            'qr_code_url': qr_code_url_from_db, # Gunakan URL yang sudah dibersihkan
            'message': 'URL ini sudah pernah dipersingkat!'
        }), 200

    if custom_alias:
        if not custom_alias.isalnum():
            return jsonify({'error': 'Alias kustom hanya boleh berisi huruf dan angka.'}), 400
        existing_alias = ShortUrl.query.filter_by(short_code=custom_alias).first()
        if existing_alias:
            return jsonify({'error': 'Alias kustom ini sudah digunakan. Silakan pilih yang lain.'}), 409
        short_code = custom_alias
    else:
        short_code = generate_short_code()

    # Generate QR Code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    full_short_url = url_for('redirect_to_original', short_code=short_code, _external=True)
    qr.add_data(full_short_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    
    # Gunakan QR_CODES_FOLDER yang didefinisikan di awal
    qr_code_filename = f'qr_{short_code}.png'
    qr_code_path_on_disk = os.path.join(QR_CODES_FOLDER, qr_code_filename)
    img.save(qr_code_path_on_disk)

    # Path relatif untuk disimpan ke DB (ini bisa tetap menggunakan os.path.join jika DB memerlukannya)
    # Karena kita sudah memastikan folder 'qrcodes' adalah bagian dari 'static',
    # path relatif dari 'static' adalah 'qrcodes/qr_filename.png'
    relative_qr_path_for_db = os.path.join('qrcodes', qr_code_filename)

    # Buat path yang ramah URL dengan forward slashes
    url_friendly_qr_path = f'qrcodes/{qr_code_filename}' # <--- Ini yang perlu digunakan untuk URL!
    
    new_short_url = ShortUrl(
        original_url=original_url,
        short_code=short_code,
        user_id=g.user.id if g.user else None,
        qr_code_path=relative_qr_path_for_db # Simpan path relatif ke DB
    )
    db.session.add(new_short_url)
    db.session.commit()

    return jsonify({
        'short_url': full_short_url,
        'qr_code_url': url_for('static', filename=url_friendly_qr_path) # <--- GANTI KE url_friendly_qr_path INI!
    }), 201

# Rute untuk redireksi (saat short URL diakses)
@app.route('/<short_code>')
def redirect_to_original(short_code):
    short_url_entry = ShortUrl.query.filter_by(short_code=short_code, is_active=True).first()
    if short_url_entry:
        # Catat klik
        user_ip = request.remote_addr
        country = 'Unknown'
        
        # --- GEOIP Logic ---
        # Pastikan Anda sudah mengunduh database GeoLite2-City.mmdb
        # dan menempatkannya di root folder project Anda (sejajar dengan app.py)
        # Atau sesuaikan path GEOIP_DB_PATH di awal app.py
        # from your code snippet, it's assumed you have geoip2.database.Reader imported
        # and 'reader' is initialized globally for efficiency.
        # If you are not using GeoIP, you can remove this try/except block.
        try:
            # Placeholder if you are not using GeoIP for now
            pass
        except Exception as e:
            app.logger.warning(f"Failed to get geoip data for {user_ip}: {e}")

        new_click = Click(short_url_id=short_url_entry.id, ip_address=user_ip, country=country)
        db.session.add(new_click)
        db.session.commit()
        
        return redirect(short_url_entry.original_url)
    else:
        flash('Tautan tidak valid atau sudah tidak aktif.', 'error')
        return redirect(url_for('index'))

# ... (Rute API untuk manajemen URL dan analitik lainnya) ...

@app.route('/api/urls', methods=['GET'])
@login_required
def get_user_urls_api():
    urls = ShortUrl.query.filter_by(user_id=g.user.id).order_by(ShortUrl.created_at.desc()).all()
    urls_data = []
    for url in urls:
        total_clicks = Click.query.filter_by(short_url_id=url.id).count()
        
        # PERBAIKAN: Pastikan QR code URL menggunakan forward slashes saat diambil dari DB
        qr_code_url_for_frontend = None
        if url.qr_code_path:
            # Mengganti backslash dengan forward slash jika ada
            clean_qr_path = url.qr_code_path.replace('\\', '/')
            qr_code_url_for_frontend = url_for('static', filename=clean_qr_path)

        urls_data.append({
            'id': url.id,
            'original_url': url.original_url,
            'short_code': url.short_code,
            'short_url': url_for('redirect_to_original', short_code=url.short_code, _external=True),
            'qr_code_url': qr_code_url_for_frontend, # Gunakan URL yang sudah dibersihkan
            'is_active': url.is_active,
            'created_at': url.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'clicks_count': total_clicks # Mengganti 'total_clicks' menjadi 'clicks_count' agar konsisten dengan JS
        })
    return jsonify({'urls': urls_data}), 200 # Mengembalikan sebagai objek dengan kunci 'urls'

@app.route('/api/urls/<int:url_id>', methods=['DELETE'])
@login_required
def delete_url_api(url_id):
    short_url = ShortUrl.query.filter_by(id=url_id, user_id=g.user.id).first()
    if not short_url:
        return jsonify({'error': 'URL tidak ditemukan atau bukan milik Anda'}), 404

    # Hapus juga file QR code dari disk jika ada
    if short_url.qr_code_path:
        full_qr_path_on_disk = os.path.join(app.root_path, 'static', short_url.qr_code_path)
        if os.path.exists(full_qr_path_on_disk):
            try:
                os.remove(full_qr_path_on_disk)
                app.logger.info(f"QR code file removed: {full_qr_path_on_disk}")
            except Exception as e:
                app.logger.error(f"Error removing QR code file {full_qr_path_on_disk}: {e}")


    Click.query.filter_by(short_url_id=url_id).delete()
    db.session.delete(short_url)
    db.session.commit()
    return jsonify({'message': 'URL berhasil dihapus'}), 200

@app.route('/api/urls/<int:url_id>/toggle-status', methods=['PUT']) # Mengubah POST menjadi PUT
@login_required
def toggle_url_active_api(url_id):
    short_url = ShortUrl.query.filter_by(id=url_id, user_id=g.user.id).first()
    if not short_url:
        return jsonify({'error': 'URL tidak ditemukan atau bukan milik Anda'}), 404

    short_url.is_active = not short_url.is_active
    db.session.commit()
    return jsonify({'message': 'Status URL berhasil diperbarui', 'is_active': short_url.is_active}), 200

@app.route('/api/urls/<int:url_id>/analytics', methods=['GET'])
@login_required
def get_url_analytics_api(url_id):
    short_url = ShortUrl.query.filter_by(id=url_id, user_id=g.user.id).first()
    if not short_url:
        return jsonify({'error': 'URL tidak ditemukan atau bukan milik Anda'}), 404

    clicks = Click.query.filter_by(short_url_id=url_id).all()

    total_clicks = len(clicks)

    country_data = {}
    for click in clicks:
        if click.country:
            country_data[click.country] = country_data.get(click.country, 0) + 1

    daily_clicks = {}
    for click in clicks:
        day_key = click.clicked_at.strftime('%Y-%m-%d') # Format tanggal
        daily_clicks[day_key] = daily_clicks.get(day_key, 0) + 1

    return jsonify({
        'short_code': short_url.short_code, # Tambahkan short_code untuk modal analitik
        'total_clicks': total_clicks,
        'country_distribution': country_data,
        'daily_clicks': daily_clicks
    }), 200

# --- Menjalankan Aplikasi ---
if __name__ == '__main__':
    app.run(debug=True, port=5000) # Pastikan Anda selalu menggunakan debug=True selama pengembangan
