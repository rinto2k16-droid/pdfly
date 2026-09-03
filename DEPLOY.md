# 🚀 PDFly কে অনলাইনে পাবলিশ করা (ডোমেইন + হোস্টিং)

PDFly একটি **self-hosted** ওয়েবসাইট — আপনার যেকোনো Linux VPS, Shared Hosting (Python
সাপোর্টসহ), বা PaaS-এ চালাতে পারবেন। নিচে সব জনপ্রিয় পদ্ধতি দেওয়া হলো।

> **লোকালি চালাতে (Windows):** `start_windows.bat` ডাবল-ক্লিক করুন।
> **লোকালি চালাতে (Linux/macOS):** `bash start_linux.sh` চালান।

---

## পদ্ধতি ১: Docker দিয়ে (সবচেয়ে সহজ — যেকোনো VPS)

```bash
# 1. আপনার VPS-এ (Ubuntu/Debian) Docker ইনস্টল করুন:
curl -fsSL https://get.docker.com | sh

# 2. প্রজেক্ট ফোল্ডারে যান (যেখানে Dockerfile আছে) এবং বিল্ড করুন:
docker build -t pdfly .

# 3. চালান:
docker run -d --name pdfly -p 5000:5000 -v pdfly_data:/app/pdfly_storage \
  --restart unless-stopped pdfly

# 4. এখন http://YOUR_SERVER_IP:5000 এ সাইট চলছে ✓
```

## পদ্ধতি ২: Docker + Nginx + ডোমেইন (SSL সহ)

```
server {
    listen 80;
    server_name yourdomain.com;
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        client_max_body_size 300M;   # বড় ফাইল আপলোডের জন্য জরুরি
    }
}
```
তারপর `certbot --nginx -d yourdomain.com` দিয়ে **HTTPS** ফ্রি SSL দিন।

## পদ্ধতি ৩: সরাসরি Python (VPS এ)

```bash
sudo apt update && sudo apt install -y python3-pip python3-venv \
    tesseract-ocr ghostscript poppler-utils fonts-dejavu-core
cd pdfly
pip3 install -r requirements.txt gunicorn
gunicorn -b 0.0.0.0:5000 -w 2 -t 300 app:app
```
**(শেয়ার্ড হোস্টিং-এ)** cPanel/হোস্টিং প্যানেলের Python App / Passenger সেটআপে
`app.py`-কে WSGI entry হিসেবে দিন, `requirements.txt` ইনস্টল করান।

## পদ্ধতি ৪: PaaS (Railway / Render / Fly.io — ফ্রি টায়ার)

- **Railway:** New Project → Deploy from GitHub → Build command: `pip install -r requirements.txt`, Start command: `gunicorn -b 0.0.0.0:$PORT -w 2 -t 300 app:app`
- **Render (Web Service):**
  - Build: `pip install -r requirements.txt`
  - Start: `gunicorn -b 0.0.0.0:$PORT -w 2 -t 300 app:app`
  - Volume মাউন্ট করুন: `/app/pdfly_storage` (ফাইল ২ ঘণ্টা রাখার জন্য)

## ⚠️ Production-এ খেয়াল রাখবেন

| বিষয় | কী করবেন |
|---|---|
| Upload limit | Nginx/Proxy-তে `client_max_body_size 300M` দিন |
| ফাইল পরিষ্কার | ফাইল ২ ঘণ্টা পর অটো-ডিলিট হয় (built-in) |
| Workers | gunicorn `-w 2` যথেষ্ট; বেশি হলে 4 |
| টাইমআউট | বড় PDF-এর জন্য proxy timeout ≥ 300s |
| OCR | `tesseract-ocr` + বাংলা দরকার হলে `tesseract-ocr-ben` |
| SSL | সবসময় HTTPS (certbot বিনামূল্যে) |

## 🇧🇩 সংক্ষেপে

1. যেকোনো VPS নিন (Hostinger / DigitalOcean / Contabo — $5/মাস)
2. উপরের Docker কমান্ড চালান
3. ডোমেইন (DNS A record) → VPS IP-তে পয়েন্ট করুন
4. Nginx + certbot দিয়ে SSL বসান — **ব্যস!** এখন আপনার নিজের iLovePDF চলছে।
