// static/js/script.js
console.log("script.js is running!");
document.addEventListener('DOMContentLoaded', () => {
    // --- Elemen Umum UI (dari halaman utama jika ada) ---
    const shortenForm = document.getElementById('shortenForm');
    const originalUrlInput = document.getElementById('originalUrl');
    const customAliasInput = document.getElementById('customAlias');
    const resultDiv = document.getElementById('result');
    const shortUrlOutput = document.getElementById('shortUrlOutput');
    const qrCodeOutput = document.getElementById('qrCodeOutput');
    const copyButton = document.getElementById('copyButton');
    const urlsList = document.getElementById('urlsList'); // Untuk dashboard

    // --- Elemen Modal (Pop-up Pemendek URL Baru) ---
    const shortenModal = document.getElementById('shortenModal');
    const openShortenModalBtn = document.getElementById('openShortenModal');
    // closeShortenModal bisa ditangani dengan event listener umum di bawah
    const modalShortenForm = document.getElementById('modalShortenForm');
    const modalOriginalUrlInput = document.getElementById('modalOriginalUrl');
    const modalCustomAliasInput = document.getElementById('modalCustomAlias');
    const modalResultDiv = document.getElementById('modalResult');
    const modalShortUrlOutput = document.getElementById('modalShortUrlOutput');
    const modalQrCodeOutput = document.getElementById('modalQrCodeOutput');
    const modalCopyButton = document.getElementById('modalCopyButton');
    const modalErrorMessage = document.getElementById('modalErrorMessage');

    // --- Elemen Modal (Analitik URL) ---
    const analyticsModal = document.getElementById('analyticsModal');
    const analyticsShortCodeSpan = document.getElementById('analyticsShortCode');
    const totalClicksSpan = document.getElementById('totalClicks');
    const countryDistributionList = document.getElementById('countryDistribution');
    const dailyClicksList = document.getElementById('dailyClicks');


    // --- PENAMBAHAN BARU: Notifikasi Dinamis ---
    const notificationContainer = document.createElement('div');
    notificationContainer.className = 'ajax-notifications-container';
    document.body.appendChild(notificationContainer);

    function showNotification(message, type = 'info') { // type bisa 'success', 'error', 'info', 'warning'
        const notification = document.createElement('div');
        notification.className = `ajax-notification ajax-notification-${type}`;
        notification.textContent = message;
        
        notificationContainer.appendChild(notification);

        // Hapus notifikasi setelah beberapa detik
        setTimeout(() => {
            notification.classList.add('hide'); // Tambahkan kelas untuk efek fade out
            notification.addEventListener('transitionend', () => {
                notification.remove();
            });
        }, 3000); // Notifikasi akan hilang setelah 3 detik
    }


    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(message => {
        // Auto-hide setelah 5 detik
        setTimeout(() => {
            message.classList.add('hide');
            // Hapus elemen setelah transisi selesai untuk membersihkan DOM
            message.addEventListener('transitionend', () => {
                message.remove();
            });
        }, 5000); // Pesan flash akan hilang setelah 5 detik (bisa disesuaikan)

        // Penanganan tombol tutup manual
        const closeButton = message.querySelector('.close-flash-message');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                message.classList.add('hide');
                message.addEventListener('transitionend', () => {
                    message.remove();
                });
            });
        }
    });
    // --- AKHIR PENAMBAHAN BARU ---


    // --- Logika untuk Membuka/Menutup Modal Pemendek URL ---
    if (openShortenModalBtn) {
        openShortenModalBtn.addEventListener('click', () => {
            console.log("Tombol buka shortenModal diklik!");
            shortenModal.style.display = 'flex';
            if (modalShortenForm) {
                modalShortenForm.reset();
            }
            if (modalResultDiv) {
                modalResultDiv.style.display = 'none';
            }
            if (modalErrorMessage) {
                modalErrorMessage.style.display = 'none';
                modalErrorMessage.textContent = '';
            }
            if (modalQrCodeOutput) {
                modalQrCodeOutput.style.display = 'none';
                modalQrCodeOutput.src = '';
            }
        });
    }

    // Menutup modal saat mengklik tombol 'X' (close-button)
    // Logika ini akan menangani semua modal dengan kelas .close-button
    document.querySelectorAll('.modal .close-button').forEach(button => {
        button.addEventListener('click', () => {
            console.log("Tombol tutup modal umum diklik!");
            if (shortenModal) shortenModal.style.display = 'none';
            if (analyticsModal) analyticsModal.style.display = 'none';
        });
    });

    // Menutup modal saat mengklik di luar konten modal
    window.addEventListener('click', (event) => {
        if (event.target === shortenModal) {
            console.log("Shorten Modal ditutup (klik di luar window)");
            shortenModal.style.display = 'none';
        }
        if (event.target === analyticsModal) {
            console.log("Analytics Modal ditutup (klik di luar window)");
            analyticsModal.style.display = 'none';
        }
    });


    // --- Logika Pemendekan URL (di dalam modal) ---
    if (modalShortenForm) {
        modalShortenForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const originalUrl = modalOriginalUrlInput.value;
            const customAlias = modalCustomAliasInput.value;

            if (modalErrorMessage) {
                modalErrorMessage.style.display = 'none';
                modalErrorMessage.textContent = '';
            }
            if (modalResultDiv) modalResultDiv.style.display = 'none';
            if (modalQrCodeOutput) modalQrCodeOutput.style.display = 'none';


            try {
                const response = await fetch('/api/shorten', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        original_url: originalUrl,
                        custom_alias: customAlias
                    })
                });

                const data = await response.json();

                if (response.ok) { // Status 2xx (sukses)
                    modalShortUrlOutput.textContent = data.short_url;
                    modalShortUrlOutput.href = data.short_url;

                    if (data.qr_code_url && modalQrCodeOutput) {
                        modalQrCodeOutput.src = data.qr_code_url;
                        modalQrCodeOutput.style.display = 'block';
                    } else if (modalQrCodeOutput) {
                        modalQrCodeOutput.style.display = 'none';
                    }

                    modalResultDiv.style.display = 'block';

                    // Muat ulang daftar URL di dashboard untuk menampilkan URL baru
                    loadUserUrls();
                    
                    // Ganti alert() dengan notifikasi dinamis
                    if (data.message) {
                        showNotification(data.message, data.status || 'success');
                    }
                    
                } else { // Status 4xx atau 5xx (error)
                    if (modalErrorMessage) {
                        modalErrorMessage.textContent = data.error || 'Terjadi kesalahan. Silakan coba lagi.';
                        modalErrorMessage.style.display = 'block';
                    }
                    // Ganti alert() dengan notifikasi dinamis
                    if (data.error) {
                        showNotification(data.error, data.status || 'error');
                    }
                }
            } catch (error) {
                console.error('Error saat memendekkan URL:', error);
                if (modalErrorMessage) {
                    modalErrorMessage.textContent = 'Tidak dapat terhubung ke server. Periksa koneksi Anda.';
                    modalErrorMessage.style.display = 'block';
                }
                // Ganti alert() dengan notifikasi dinamis
                showNotification('Tidak dapat terhubung ke server. Periksa koneksi Anda.', 'error');
            }
        });
    }

    // --- Logika Salin URL (di dalam modal) ---
    if (modalCopyButton) {
        modalCopyButton.addEventListener('click', () => {
            const shortUrlText = modalShortUrlOutput.href;
            navigator.clipboard.writeText(shortUrlText).then(() => {
                // Ganti alert() dengan notifikasi dinamis
                showNotification('URL pendek berhasil disalin!', 'success');
            }).catch(err => {
                console.error('Gagal menyalin URL:', err);
                // Ganti alert() dengan notifikasi dinamis
                showNotification('Gagal menyalin URL. Silakan salin secara manual.', 'error');
            });
        });
    }

    // --- Logika untuk Memuat URL Pengguna (untuk dashboard) ---
    async function loadUserUrls() {
        if (!urlsList) return;

        try {
            const response = await fetch('/api/urls');
            const data = await response.json();

            if (response.ok) {
                urlsList.innerHTML = '';
                if (data.urls && data.urls.length > 0) {
                    data.urls.forEach(url => {
                        const urlItem = document.createElement('div');
                        urlItem.className = 'url-item';
                        urlItem.setAttribute('data-url-id', url.id);

                        urlItem.innerHTML = `
                            <div class="url-info">
                                <p class="original-url" title="${url.original_url}">${url.original_url}</p>
                                <a href="${url.short_url}" target="_blank" class="short-url">${url.short_code}</a>
                                
                                <p class="url-meta">Dibuat: ${new Date(url.created_at).toLocaleDateString()}</p>
                                <p class="url-meta">Klik: ${url.clicks_count}</p>
                            </div>
                            <div class="url-actions">
                                <button class="btn btn-sm btn-copy-url" data-short-url="${url.short_url}">Salin</button>
                                <button class="btn btn-sm btn-qr-code" data-qr-code-url="${url.qr_code_url}">QR Kode</button>
                                <button class="btn btn-sm btn-analytics" data-url-id="${url.id}">Analitik</button>
                                <button class="btn btn-sm btn-toggle-status" data-url-id="${url.id}" data-is-active="${url.is_active}">
                                    ${url.is_active ? 'Nonaktifkan' : 'Aktifkan'}
                                </button>
                                <button class="btn btn-sm btn-delete" data-url-id="${url.id}">Hapus</button>
                            </div>
                        `;
                        urlsList.appendChild(urlItem);
                    });
                    attachUrlEventListeners();
                } else {
                    urlsList.innerHTML = '<p>Anda belum memiliki URL pendek. Klik "Buat Tautan Baru" untuk membuat satu.</p>';
                }
            } else {
                console.error('Gagal memuat URL:', data.error || 'Kesalahan server');
                urlsList.innerHTML = `<p class="error-message">Gagal memuat URL: ${data.error || 'Kesalahan server'}</p>`;
                // Ganti alert() dengan notifikasi dinamis jika diperlukan di sini (meskipun ini ke innerHTML)
                showNotification('Gagal memuat URL: ' + (data.error || 'Kesalahan server'), data.status || 'error');
            }
        } catch (error) {
            console.error('Network error saat memuat URL:', error);
            urlsList.innerHTML = '<p class="error-message">Tidak dapat terhubung ke server untuk memuat URL.</p>';
            // Ganti alert() dengan notifikasi dinamis
            showNotification('Tidak dapat terhubung ke server untuk memuat URL.', 'error');
        }
    }

    // --- Melampirkan Event Listener ke Tombol URL Dinamis (Toggle, Analitik, Hapus) ---
    function attachUrlEventListeners() {
        // Copy URL (untuk item di daftar)
        document.querySelectorAll('.btn-copy-url').forEach(button => {
            button.onclick = (event) => {
                const shortUrl = event.target.dataset.shortUrl;
                navigator.clipboard.writeText(shortUrl).then(() => {
                    // Ganti alert() dengan notifikasi dinamis
                    showNotification('URL pendek berhasil disalin!', 'success');
                }).catch(err => {
                    console.error('Gagal menyalin URL:', err);
                    // Ganti alert() dengan notifikasi dinamis
                    showNotification('Gagal menyalin URL. Silakan salin secara manual.', 'error');
                });
            };
        });

        // QR Code (untuk item di daftar) - Akan menampilkan QR di modal atau sebagai pop-up sederhana
        document.querySelectorAll('.btn-qr-code').forEach(button => {
            button.onclick = (event) => {
                const qrCodeUrl = event.target.dataset.qrCodeUrl;
                if (qrCodeUrl) {
                    window.open(qrCodeUrl, '_blank');
                    // showNotification('QR Code berhasil dibuka.', 'info'); // Opsional notifikasi
                } else {
                    // Ganti alert() dengan notifikasi dinamis
                    showNotification('QR Code tidak tersedia untuk URL ini.', 'error');
                }
            };
        });

        // Toggle Status
        document.querySelectorAll('.btn-toggle-status').forEach(button => {
            button.onclick = async (event) => {
                const urlId = event.target.dataset.urlId;
                try {
                    const response = await fetch(`/api/urls/${urlId}/toggle-status`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    const data = await response.json();
                    if (response.ok) {
                        // Ganti alert() dengan notifikasi dinamis
                        showNotification(data.message, data.status || 'success');
                        loadUserUrls();
                    } else {
                        // Ganti alert() dengan notifikasi dinamis
                        showNotification('Gagal memperbarui status: ' + (data.error || 'Kesalahan server'), data.status || 'error');
                    }
                } catch (error) {
                    console.error('Error toggling status:', error);
                    // Ganti alert() dengan notifikasi dinamis
                    showNotification('Terjadi kesalahan saat memperbarui status.', 'error');
                }
            };
        });

        // View Analytics
        document.querySelectorAll('.btn-analytics').forEach(button => {
            button.onclick = async (event) => {
                const urlId = event.target.dataset.urlId;
                analyticsShortCodeSpan.textContent = '';
                totalClicksSpan.textContent = '0';
                countryDistributionList.innerHTML = '';
                dailyClicksList.innerHTML = '';

                try {
                    const response = await fetch(`/api/urls/${urlId}/analytics`);
                    const analyticsData = await response.json();

                    if (response.ok) {
                        analyticsShortCodeSpan.textContent = analyticsData.short_code;
                        totalClicksSpan.textContent = analyticsData.total_clicks;

                        if (Object.keys(analyticsData.country_distribution).length > 0) {
                            for (const country in analyticsData.country_distribution) {
                                const li = document.createElement('li');
                                li.innerHTML = `<strong>${country}</strong>: ${analyticsData.country_distribution[country]} klik`;
                                countryDistributionList.appendChild(li);
                            }
                        } else {
                            countryDistributionList.innerHTML = '<li>Tidak ada data negara.</li>';
                        }

                        dailyClicksList.innerHTML = '';
                        if (Object.keys(analyticsData.daily_clicks).length > 0) {
                            const sortedDates = Object.keys(analyticsData.daily_clicks).sort();
                            sortedDates.forEach(date => {
                                const li = document.createElement('li');
                                li.innerHTML = `<strong>${date}</strong>: ${analyticsData.daily_clicks[date]} klik`;
                                dailyClicksList.appendChild(li);
                            });
                        } else {
                            dailyClicksList.innerHTML = '<li>Tidak ada data klik harian.</li>';
                        }

                        analyticsModal.style.display = 'flex';
                        // Tidak perlu notifikasi sukses untuk membuka modal
                    } else {
                        // Ganti alert() dengan notifikasi dinamis
                        showNotification('Gagal memuat analitik: ' + (analyticsData.error || 'Kesalahan server'), analyticsData.status || 'error');
                    }
                } catch (error) {
                    console.error('Error loading analytics:', error);
                    // Ganti alert() dengan notifikasi dinamis
                    showNotification('Terjadi kesalahan saat memuat analitik.', 'error');
                }
            };
        });

        // Delete URL
        document.querySelectorAll('.btn-delete').forEach(button => {
            button.onclick = async (event) => {
                const urlId = event.target.dataset.urlId;
                if (confirm('Apakah Anda yakin ingin menghapus URL ini?')) {
                    try {
                        const response = await fetch(`/api/urls/${urlId}`, {
                            method: 'DELETE'
                        });
                        const data = await response.json();
                        if (response.ok) {
                            // Ganti alert() dengan notifikasi dinamis
                            showNotification(data.message, data.status || 'success');
                            loadUserUrls();
                        } else {
                            // Ganti alert() dengan notifikasi dinamis
                            showNotification('Gagal menghapus URL: ' + (data.error || 'Kesalahan server'), data.status || 'error');
                        }
                    } catch (error) {
                        console.error('Error deleting URL:', error);
                        // Ganti alert() dengan notifikasi dinamis
                        showNotification('Terjadi kesalahan saat menghapus URL.', 'error');
                    }
                }
            };
        });
    }

    // --- Panggil loadUserUrls saat halaman Dashboard dimuat ---
    if (window.location.pathname === '/dashboard') {
        loadUserUrls();
    }
});