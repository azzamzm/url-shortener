from flask import Flask, request, redirect, jsonify, render_template, session, url_for, g, flash
from models import db, User, ShortUrl, Click # Asumsi models.py sudah ada dan benar
import string
import random
import qrcode
import os
import jwt
from datetime import datetime, timedelta, timezone
import requests
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

import logging
import io # Import untuk menangani gambar dalam memori
import base64 # Import untuk encoding Base64

logging.basicConfig(level=logging.INFO)

# --- Inisialisasi Aplikasi Flask ---
app = Flask(__name__)

# Mengambil konfigurasi sensitif dari variabel lingkungan
# Gunakan nilai default untuk pengembangan lokal jika variabel lingkungan tidak diatur
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'kunci_rahasia_default_untuk_pengembangan')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///site.db')

# Inisialisasi database
db.init_app(app)

app.logger.setLevel(logging.INFO)

# --- PENTING: Membuat Tabel Database (Pastikan ini ada!) ---
# Untuk aplikasi produksi, disarankan menggunakan Flask-Migrate untuk manajemen skema database.
# Namun, untuk memulai, db.create_all() akan berfungsi.
with app.app_context():
    db.create_all()

# --- Context Processor ---
@app.context_processor
def inject_user_and_username():
    username = None
    if g.user:
        username = g.user.username
    return dict(username=username)

# --- Before Request untuk Memuat Pengguna ---
@app.before_request
def load_logged_in_user():
    token = session.get('token')
    g.user = None
    if token:
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            g.user = db.session.get(User, payload['user_id'])
        except jwt.ExpiredSignatureError:
            session.pop('token', None)
            flash('Sesi Anda telah berakhir, silakan masuk kembali.', 'info')
        except jwt.InvalidTokenError:
            session.pop('token', None)
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
            return redirect(url_for('auth'))
        return view(*args, **kwargs)
    wrapped_view.__name__ = view.__name__
    return wrapped_view

# --- Rute Aplikasi ---

@app.route('/')
def index():
    return render_template('index.html')

# --- Rute Autentikasi ---

@app.route('/auth', methods=['GET'], endpoint='auth')
def show_auth_form():
    if g.user:
        return redirect(url_for('dashboard'))
    return render_template('auth.html')

@app.route('/register', methods=['POST'])
def register():
    if g.user:
        return redirect(url_for('dashboard'))

    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not username or not password or not email or not confirm_password:
        flash('Semua kolom harus diisi.', 'error')
        return redirect(url_for('auth'))

    if password != confirm_password:
        flash('Konfirmasi kata sandi tidak cocok.', 'error')
        return redirect(url_for('auth'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('Nama pengguna sudah terdaftar. Silakan pilih nama lain.', 'error')
        return redirect(url_for('auth'))

    existing_email = User.query.filter_by(email=email).first()
    if existing_email:
        flash('Email ini sudah terdaftar. Silakan gunakan email lain atau masuk.', 'error')
        return redirect(url_for('auth'))

    hashed_password = generate_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password
    )
    db.session.add(new_user)
    
    try:
        db.session.commit()
        flash('Registrasi berhasil! Silakan masuk.', 'success')
        return redirect(url_for('auth'))
    except Exception as e:
        db.session.rollback()
        flash(f'Terjadi kesalahan saat registrasi: {e}', 'error')
        app.logger.error(f"Error during registration: {e}")
        return redirect(url_for('auth'))

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
        # QR code tidak disimpan ke disk di Vercel, jadi tidak ada path langsung.
        # Frontend perlu memanggil endpoint /api/qr/<short_code> untuk mendapatkan QR.
        return jsonify({
            'short_url': url_for('redirect_to_original', short_code=short_code, _external=True),
            'qr_code_url': None, # Tidak ada URL QR code langsung dari sini lagi
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

    # --- TIDAK ADA LAGI PENYIMPANAN QR CODE KE DISK DI SINI ---
    # QR code akan dihasilkan on-demand melalui endpoint API baru.
    
    new_short_url = ShortUrl(
        original_url=original_url,
        short_code=short_code,
        user_id=g.user.id if g.user else None,
        qr_code_path=None # Tidak ada path QR code yang disimpan di DB lagi
    )
    db.session.add(new_short_url)
    db.session.commit()

    # Mengembalikan URL pendek dan instruksi untuk mendapatkan QR code
    return jsonify({
        'short_url': url_for('redirect_to_original', short_code=short_code, _external=True),
        'qr_code_url': url_for('get_qr_code_api', short_code=short_code, _external=True), # Beri tahu frontend cara mendapatkan QR
        'message': 'URL berhasil dipersingkat!'
    }), 201

# Rute untuk redireksi (saat short URL diakses)
@app.route('/<short_code>')
def redirect_to_original(short_code):
    short_url_entry = ShortUrl.query.filter_by(short_code=short_code, is_active=True).first()
    if short_url_entry:
        # Catat klik
        user_ip = request.remote_addr
        country = 'Unknown' # Default jika GeoIP tidak digunakan atau gagal

        # --- GEOIP Logic (Pastikan Anda menginstal geoip2 jika menggunakan ini) ---
        # Jika Anda menggunakan geoip2, pastikan database GeoLite2-City.mmdb
        # ada di lokasi yang dapat diakses (misalnya, di root folder proyek)
        # dan Anda memiliki kode inisialisasi reader.
        # Contoh:
        # import geoip2.database
        # GEOIP_DB_PATH = os.path.join(app.root_path, 'GeoLite2-City.mmdb')
        # try:
        #     reader = geoip2.database.Reader(GEOIP_DB_PATH)
        # except Exception as e:
        #     app.logger.error(f"Failed to load GeoIP database: {e}")
        #     reader = None
        #
        # if reader:
        #     try:
        #         response = reader.city(user_ip)
        #         country = response.country.name if response.country else 'Unknown'
        #     except Exception as e:
        #         app.logger.warning(f"Failed to get geoip data for {user_ip}: {e}")
        # else:
        #     app.logger.warning("GeoIP reader not initialized.")

        new_click = Click(short_url_id=short_url_entry.id, ip_address=user_ip, country=country)
        db.session.add(new_click)
        db.session.commit()
        
        return redirect(short_url_entry.original_url)
    else:
        flash('Tautan tidak valid atau sudah tidak aktif.', 'error')
        return redirect(url_for('index'))

# --- API Endpoint Baru untuk Mendapatkan QR Code (Base64) ---
@app.route('/api/qr/<short_code>', methods=['GET'])
def get_qr_code_api(short_code):
    """
    Menghasilkan dan mengembalikan QR code untuk short_code tertentu dalam format Base64.
    Digunakan oleh frontend untuk menampilkan QR code secara on-demand.
    """
    short_url_entry = ShortUrl.query.filter_by(short_code=short_code).first()
    if not short_url_entry:
        return jsonify({'error': 'Short URL tidak ditemukan'}), 404

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

    # Simpan gambar ke buffer memori
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return jsonify({'qr_code_data': f"data:image/png;base64,{img_str}"}), 200


# --- Rute API untuk manajemen URL dan analitik lainnya ---

@app.route('/api/urls', methods=['GET'])
@login_required
def get_user_urls_api():
    urls = ShortUrl.query.filter_by(user_id=g.user.id).order_by(ShortUrl.created_at.desc()).all()
    urls_data = []
    for url in urls:
        total_clicks = Click.query.filter_by(short_url_id=url.id).count()
        
        # QR code tidak lagi disimpan di disk. Frontend akan memanggil endpoint /api/qr/<short_code>
        # untuk mendapatkan QR code.
        qr_code_url_for_frontend = url_for('get_qr_code_api', short_code=url.short_code, _external=True)

        urls_data.append({
            'id': url.id,
            'original_url': url.original_url,
            'short_code': url.short_code,
            'short_url': url_for('redirect_to_original', short_code=url.short_code, _external=True),
            'qr_code_url': qr_code_url_for_frontend, # Sekarang mengarah ke API endpoint baru
            'is_active': url.is_active,
            'created_at': url.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'clicks_count': total_clicks
        })
    return jsonify({'urls': urls_data}), 200

@app.route('/api/urls/<int:url_id>', methods=['DELETE'])
@login_required
def delete_url_api(url_id):
    short_url = ShortUrl.query.filter_by(id=url_id, user_id=g.user.id).first()
    if not short_url:
        return jsonify({'error': 'URL tidak ditemukan atau bukan milik Anda'}), 404

    # --- TIDAK ADA LAGI PENGHAPUSAN FILE QR CODE DARI DISK ---
    # Karena QR code tidak disimpan secara permanen di serverless.

    Click.query.filter_by(short_url_id=url_id).delete()
    db.session.delete(short_url)
    db.session.commit()
    return jsonify({'message': 'URL berhasil dihapus'}), 200

@app.route('/api/urls/<int:url_id>/toggle-status', methods=['PUT'])
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
        day_key = click.clicked_at.strftime('%Y-%m-%d')
        daily_clicks[day_key] = daily_clicks.get(day_key, 0) + 1

    return jsonify({
        'short_code': short_url.short_code,
        'total_clicks': total_clicks,
        'country_distribution': country_data,
        'daily_clicks': daily_clicks
    }), 200

# --- Menjalankan Aplikasi (Hanya untuk pengembangan lokal) ---
# Blok ini tidak akan dieksekusi oleh Vercel.
# if __name__ == '__main__':
#     app.run(debug=True, port=5000)
