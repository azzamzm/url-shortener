# Dockerfile

# Gunakan Python 3.9 sebagai base image
FROM python:3.9-slim-buster

# Set working directory di dalam container
WORKDIR /app

# Salin file requirements.txt ke dalam container
COPY requirements.txt .

# Instal dependensi Python
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh isi proyek Anda ke dalam container
COPY . .

# Ekspos port yang digunakan aplikasi Flask (default 5000)
EXPOSE 5000

# Command default untuk menjalankan aplikasi Anda
# Ini akan ditimpa oleh 'command' di docker-compose.yml,
# tetapi baik untuk dimiliki jika menjalankan container secara mandiri.
CMD ["flask", "run", "--host=0.0.0.0"]