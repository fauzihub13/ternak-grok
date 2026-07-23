# Ternak Grok

Auto register akun xAI (Grok) massal + connect ke 9router. Semua proses otomatis: generate email, OTP, verifikasi, Cloudflare Turnstile, dan koneksi ke 9router.

## Fitur

- Auto register akun xAI via API
- Support multiple email domains (acak per akun)
- Scraping OTP dari generator.email
- Solve Cloudflare Turnstile via Camoufox (headless)
- Connect akun baru ke 9router (OAuth device flow)
- Multi-threading untuk proses paralel
- Logging berwarna (hijau=sukses, merah=gagal, kuning=warning)
- Proxy optional

## File Struktur

```
ternak-grok/
├── ternakgrok.py          # Versi single domain
├── ternakgrok_multi.py    # Versi multi domain (rekomendasi)
├── base.py                # Backup/base version
├── .env                   # Config (tidak di-commit)
├── .gitignore
├── accounts.txt           # Output akun (auto-generated)
└── README.md
```

## Instalasi

### 1. Clone repo

```bash
git clone https://github.com/fauzihub13/ternak-grok.git
cd ternak-grok
```

### 2. Install dependencies

```bash
pip install python-dotenv curl-cffi requests camoufox[geoip]
```

### 3. Download browser Camoufox

```bash
python -m camoufox fetch
```

### 4. Setup environment

Copy `.env.example` atau buat file `.env`:

```env
ROUTER_AUTH_TOKEN=token_dari_9router
DEFAULT_PASSWORD=PasswordAkun123@
EMAIL_DOMAINS=domain1.com,domain2.com,domain3.com
```

#### Cara dapat `ROUTER_AUTH_TOKEN`:

1. Buka 9router di `http://localhost:20128`
2. Login ke dashboard
3. Buka DevTools > Application > Cookies
4. Copy value cookie `auth_token`

## Penggunaan

### Jalankan

```bash
# Versi multi domain (rekomendasi)
python ternakgrok_multi.py

# Versi single domain
python ternakgrok.py
```

Script akan minta input:
- **Jumlah akun** yang ingin dibuat
- **Jumlah thread** (proses paralel)
- **Proxy** (opsional, format: `http://user:pass@host:port`)

### Output

Akun tersimpan di `accounts.txt` dengan format:
```
email|password|nama|userId|router=status|timestamp
```

Contoh:
```
abc123@domain.com|Password123@|Ahmad Pratama|usr-xxx|router=connected|2025-07-23 10:30:00
```

## Konfigurasi

### Environment Variables

| Variable | Keterangan | Default |
|----------|------------|---------|
| `ROUTER_AUTH_TOKEN` | Token auth 9router | (wajib) |
| `DEFAULT_PASSWORD` | Password akun xAI | `LauSapeEmpruy88@@` |
| `EMAIL_DOMAINS` | Domain email, pisah koma | `hungtpt.site` |

### Konfigurasi di Kode

Variabel di `ternakgrok.py` / `ternakgrok_multi.py`:

| Variable | Keterangan | Default |
|----------|------------|---------|
| `ROUTER_BASE` | URL 9router | `http://localhost:20128` |
| `GENERATOR_BASE` | Email generator | `https://generator.email` |
| `TURNSTILE_SITEKEY` | Sitekey Turnstile | (xAI sitekey) |
| `TURNSTILE_SOLVER_BASE` | External solver URL | `""` (pakai Camoufox) |

## Alur Kerja

```
1. Generate random email (@domain)
   │
2. Kirim OTP ke email via xAI API
   │
3. Scraping OTP dari generator.email
   │
4. Verifikasi email dengan OTP
   │
5. Solve Cloudflare Turnstile (Camoufox)
   │
6. Buat akun xAI
   │
7. Connect ke 9router (OAuth device flow)
   │
8. Simpan ke accounts.txt
```

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ModuleNotFoundError: camoufox` | `pip install camoufox[geoip] && python -m camoufox fetch` |
| `ModuleNotFoundError: dotenv` | `pip install python-dotenv` |
| `9router tidak merespons` | Pastikan 9router jalan di `localhost:20128` |
| `auth_token expired` | Ganti `ROUTER_AUTH_TOKEN` di `.env` dengan token baru |
| `Turnstile gagal` | Pastikan Camoufox terinstall: `python -m camoufox fetch` |
| `OTP tidak diterima` | Cek domain email masih aktif di generator.email |

## Dependencies

- Python 3.10+
- `python-dotenv`
- `curl-cffi`
- `requests`
- `camoufox[geoip]`

## Disclaimer

Tool ini untuk edukasi dan penelitian. Gunakan dengan bijak dan tanggung jawab sendiri.

## DARI AI UNTUK AI
