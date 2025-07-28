// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {
    // --- Elemen Umum UI (dari halaman utama jika ada) ---
    // Pastikan ID ini ada di HTML Anda jika Anda menggunakannya di luar modal
    const shortenForm = document.getElementById('shortenForm'); // Mungkin tidak digunakan jika semua di modal
    const originalUrlInput = document.getElementById('originalUrl'); // Mungkin tidak digunakan
    const customAliasInput = document.getElementById('customAlias'); // Mungkin tidak digunakan
    const resultDiv = document.getElementById('result'); // Mungkin tidak digunakan
    const shortUrlOutput = document.getElementById('shortUrlOutput'); // Mungkin tidak digunakan
    const qrCodeOutput = document.getElementById('qrCodeOutput'); // Mungkin tidak digunakan
    const copyButton = document.getElementById('copyButton'); // Mungkin tidak digunakan
    const urlsList = document.getElementById('urlsList'); // Untuk dashboard


    // --- Elemen Modal (Pop-up Pemendek URL Baru) ---
    const shortenModal = document.getElementById('shortenModal');
    const openShortenModalBtn = document.getElementById('openShortenModal');
    const closeShortenModal = document.getElementById('closeShortenModal'); // <-- DIPERBAIKI: Pastikan ini ada di HTML modal
    const modalShortenForm = document.getElementById('modalShortenForm'); // Form di dalam modal
    const modalOriginalUrlInput = document.getElementById('modalOriginalUrl');
    const modalCustomAliasInput = document.getElementById('modalCustomAlias');
    const modalResultDiv = document.getElementById('modalResult');
    const modalShortUrlOutput = document.getElementById('modalShortUrlOutput');
    const modalQrCodeOutput = document.getElementById('modalQrCodeOutput'); // <-- DIPERBAIKI: Typo 'document =' dihilangkan
    const modalCopyButton = document.getElementById('modalCopyButton');
    const modalErrorMessage = document.getElementById('modalErrorMessage'); // <-- DIPERBAIKI: Untuk pesan error di modal

    // --- Elemen Modal (Analitik URL) ---
    const analyticsModal = document.getElementById('analyticsModal');
    // const closeAnalyticsModal = document.getElementById('closeAnalyticsModal'); // <-- Baris ini tidak diperlukan karena tombol close analytics tidak punya ID unik
    const analyticsShortCodeSpan = document.getElementById('analyticsShortCode');
    const totalClicksSpan = document.getElementById('totalClicks');
    const countryDistributionList = document.getElementById('countryDistribution');
    const dailyClicksList = document.getElementById('dailyClicks');


    // --- Logika untuk Membuka/Menutup Modal Pemendek URL ---
    if (openShortenModalBtn) {
        openShortenModalBtn.addEventListener('click', () => {
            shortenModal.style.display = 'flex'; // Menggunakan 'flex' untuk pemusatan yang lebih baik
            // Reset form dan hasil setiap kali modal dibuka
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
            // Sembunyikan QR code saat modal dibuka kembali
            if (modalQrCodeOutput) {
                   modalQrCodeOutput.style.display = 'none';
                   modalQrCodeOutput.src = ''; // Bersihkan src
            }
        });
    }

    if (closeShortenModal) { // <-- DIPERBAIKI: Penambahan event listener untuk closeShortenModal
        closeShortenModal.addEventListener('click', () => {
            console.log("Tombol tutup shortenModal diklik!"); // Tambahkan ini
            shortenModal.style.display = 'none';
        });
    }

    // Menutup modal jika klik di luar konten modal
    if (shortenModal) {
        shortenModal.addEventListener('click', (e) => {
            if (e.target === shortenModal) {
                console.log("Shorten Modal ditutup (klik di luar)"); // Tambahkan ini
                shortenModal.style.display = 'none';
            }
        });
    }


    // --- Logika Pemendekan URL (di dalam modal) ---
    if (modalShortenForm) {
        modalShortenForm.addEventListener('submit', async (e) => { // Gunakan 'submit' untuk form
            e.preventDefault(); // Mencegah form dari pengiriman standar (page reload)

            const originalUrl = modalOriginalUrlInput.value;
            const customAlias = modalCustomAliasInput.value;

            // Bersihkan pesan error sebelumnya
            if (modalErrorMessage) {
                modalErrorMessage.style.display = 'none';
                modalErrorMessage.textContent = '';
            }

            // Sembunyikan hasil dan QR code lama saat submit baru
            if (modalResultDiv) modalResultDiv.style.display = 'none';
            if (modalQrCodeOutput) modalQrCodeOutput.style.display = 'none';


            try {
                const response = await fetch('/api/shorten', { // PASTIKAN URL INI BENAR
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

                    if (data.qr_code_url && modalQrCodeOutput) { // Pastikan URL QR ada dan elemen ditemukan
                        modalQrCodeOutput.src = data.qr_code_url;
                        modalQrCodeOutput.style.display = 'block';
                    } else if (modalQrCodeOutput) {
                           // Jika tidak ada QR code URL, pastikan QR code tersembunyi
                           modalQrCodeOutput.style.display = 'none';
                    }

                    modalResultDiv.style.display = 'block';

                    // Muat ulang daftar URL di dashboard untuk menampilkan URL baru
                    loadUserUrls();
                } else { // Status 4xx atau 5xx (error)
                    if (modalErrorMessage) {
                        modalErrorMessage.textContent = data.error || 'Terjadi kesalahan. Silakan coba lagi.';
                        modalErrorMessage.style.display = 'block';
                    }
                }
            } catch (error) {
                console.error('Error saat memendekkan URL:', error);
                if (modalErrorMessage) {
                    modalErrorMessage.textContent = 'Tidak dapat terhubung ke server. Periksa koneksi Anda.';
                    modalErrorMessage.style.display = 'block';
                }
            }
        });
    }

    // --- Logika Salin URL (di dalam modal) ---
    if (modalCopyButton) {
        modalCopyButton.addEventListener('click', () => {
            const shortUrlText = modalShortUrlOutput.href; // Ambil href untuk URL lengkap
            navigator.clipboard.writeText(shortUrlText).then(() => {
                alert('URL pendek berhasil disalin!');
            }).catch(err => {
                console.error('Gagal menyalin URL:', err);
                alert('Gagal menyalin URL. Silakan salin secara manual.');
            });
        });
    }

    // --- Logika untuk Memuat URL Pengguna (untuk dashboard) ---
    async function loadUserUrls() {
        if (!urlsList) return; // Keluar jika elemen urlsList tidak ada (bukan di dashboard)

        try {
            const response = await fetch('/api/urls');
            const data = await response.json();

            if (response.ok) {
                urlsList.innerHTML = ''; // Bersihkan daftar yang sudah ada
                if (data.urls && data.urls.length > 0) {
                    data.urls.forEach(url => {
                        const urlItem = document.createElement('div');
                        urlItem.className = 'url-item'; // Class untuk styling kartu
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
                    attachUrlEventListeners(); // Lampirkan event listener setelah URL dimuat
                } else {
                    urlsList.innerHTML = '<p>Anda belum memiliki URL pendek. Klik "Buat Tautan Baru" untuk membuat satu.</p>';
                }
            } else {
                console.error('Gagal memuat URL:', data.error || 'Kesalahan server');
                urlsList.innerHTML = `<p class="error-message">Gagal memuat URL: ${data.error || 'Kesalahan server'}</p>`;
            }
        } catch (error) {
            console.error('Network error saat memuat URL:', error);
            urlsList.innerHTML = '<p class="error-message">Tidak dapat terhubung ke server untuk memuat URL.</p>';
        }
    }

    // --- Melampirkan Event Listener ke Tombol URL Dinamis (Toggle, Analitik, Hapus) ---
    function attachUrlEventListeners() {
        // Copy URL (untuk item di daftar)
        document.querySelectorAll('.btn-copy-url').forEach(button => {
            button.onclick = (event) => {
                const shortUrl = event.target.dataset.shortUrl;
                navigator.clipboard.writeText(shortUrl).then(() => {
                    alert('URL pendek berhasil disalin!');
                }).catch(err => {
                    console.error('Gagal menyalin URL:', err);
                    alert('Gagal menyalin URL. Silakan salin secara manual.');
                });
            };
        });

        // QR Code (untuk item di daftar) - Akan menampilkan QR di modal atau sebagai pop-up sederhana
        document.querySelectorAll('.btn-qr-code').forEach(button => {
            button.onclick = (event) => {
                const qrCodeUrl = event.target.dataset.qrCodeUrl;
                if (qrCodeUrl) {
                    // Anda bisa menampilkan QR code ini di modal terpisah
                    // Untuk sementara, kita bisa membuka di tab baru atau alert sederhana
                    window.open(qrCodeUrl, '_blank'); // Membuka gambar QR di tab baru
                } else {
                    alert('QR Code tidak tersedia untuk URL ini.');
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
                        alert(data.message);
                        loadUserUrls(); // Muat ulang daftar URL
                    } else {
                        alert('Gagal memperbarui status: ' + (data.error || 'Kesalahan server'));
                    }
                } catch (error) {
                    console.error('Error toggling status:', error);
                    alert('Terjadi kesalahan saat memperbarui status.');
                }
            };
        });

        // View Analytics
        document.querySelectorAll('.btn-analytics').forEach(button => {
            button.onclick = async (event) => {
                const urlId = event.target.dataset.urlId;
                // Bersihkan tampilan analitik sebelumnya
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

                        // Tampilkan distribusi negara
                        if (Object.keys(analyticsData.country_distribution).length > 0) {
                            for (const country in analyticsData.country_distribution) {
                                const li = document.createElement('li');
                                li.innerHTML = `<strong>${country}</strong>: ${analyticsData.country_distribution[country]} klik`;
                                countryDistributionList.appendChild(li);
                            }
                        } else {
                            countryDistributionList.innerHTML = '<li>Tidak ada data negara.</li>';
                        }

                        // Tampilkan klik per hari
                        dailyClicksList.innerHTML = '';
                        if (Object.keys(analyticsData.daily_clicks).length > 0) {
                            // Urutkan berdasarkan tanggal
                            const sortedDates = Object.keys(analyticsData.daily_clicks).sort();
                            sortedDates.forEach(date => {
                                const li = document.createElement('li');
                                li.innerHTML = `<strong>${date}</strong>: ${analyticsData.daily_clicks[date]} klik`;
                                dailyClicksList.appendChild(li);
                            });
                        } else {
                            dailyClicksList.innerHTML = '<li>Tidak ada data klik harian.</li>';
                        }

                        analyticsModal.style.display = 'flex'; // Tampilkan modal analitik
                    } else {
                        alert('Gagal memuat analitik: ' + (analyticsData.error || 'Kesalahan server'));
                    }
                } catch (error) {
                    console.error('Error loading analytics:', error);
                    alert('Terjadi kesalahan saat memuat analitik.');
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
                            alert(data.message);
                            loadUserUrls(); // Muat ulang daftar URL
                        } else {
                            alert('Gagal menghapus URL: ' + (data.error || 'Kesalahan server'));
                        }
                    } catch (error) {
                        console.error('Error deleting URL:', error);
                        alert('Terjadi kesalahan saat menghapus URL.');
                    }
                }
            };
        });
    }


    // --- Panggil loadUserUrls saat halaman Dashboard dimuat ---
    // Ini memastikan data URL dimuat hanya jika pengguna ada di halaman dashboard
    if (window.location.pathname === '/dashboard') {
        loadUserUrls();
    }

    // --- Menutup modal saat mengklik tombol 'X' (close-button) ---
    // Logika ini yang akan kita modifikasi
    const closeButtons = document.querySelectorAll('.close-button');
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            // --- INI BARIS YANG PERLU ANDA TAMBAHKAN UNTUK DEBUGGING ---
            console.log("Tombol tutup modal umum diklik!");
            // --- END BARIS YANG PERLU ANDA TAMBAHKAN ---

            shortenModal.style.display = 'none';
            analyticsModal.style.display = 'none';

            // --- INI BARIS YANG PERLU ANDA TAMBAHKAN UNTUK DEBUGGING ---
            console.log("Display shortenModal setelah klik:", shortenModal.style.display);
            console.log("Display analyticsModal setelah klik:", analyticsModal.style.display);
            // --- END BARIS YANG PERLU ANDA TAMBAHKAN ---
        });
    });

    // Menutup modal saat mengklik di luar konten modal (jika belum ditangani di atas untuk shortenModal)
    // Logika ini sudah ada di atas untuk shortenModal, jadi pastikan tidak ada duplikasi yang tidak diinginkan
    // Ini adalah blok event listener untuk 'window' yang akan menangani klik di luar *semua* modal
    window.addEventListener('click', (event) => {
        if (event.target == shortenModal) {
            shortenModal.style.display = 'none';
            console.log("Shorten Modal ditutup (klik di luar window)"); // Tambahkan ini
        }
        if (event.target == analyticsModal) {
            analyticsModal.style.display = 'none';
            console.log("Analytics Modal ditutup (klik di luar window)"); // Tambahkan ini
        }
    });

});
