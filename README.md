# 📄 PDFly — An iLovePDF-style PDF toolkit (self-hosted)

A complete, self-hosted PDF utilities website inspired by iLovePDF.com and Smallpdf.
**52 tools**, a clean REST API, OCR, office conversions, encryption, watermarks,
redaction, PDF/A, translation and AI-style summarization — everything runs on
**your own Python server**, no documents ever leave your machine.

![tools](https://img.shields.io/badge/tools-54-green) ![engine](https://img.shields.io/badge/engine-Python%20%2B%20Flask-red) ![api](https://img.shields.io/badge/api-REST-yellow) ![deploy](https://img.shields.io/badge/deploy-Docker%20ready-blue)

> 🖥️ **Windows users:** just double-click **`start_windows.bat`** — it installs the
> dependencies, starts the server and opens your browser. Linux/macOS: `bash start_linux.sh`.

---

## ✨ Features (54 tools)

| Category | Tools |
|---|---|
| **Organize PDF** | Merge PDF · Split PDF · Delete pages · Extract pages · Reorder pages · Rotate PDF · Scan photos → PDF · **PDF Scanner (webcam)** |
| **Optimize PDF** | Compress PDF · Repair PDF · OCR PDF (English + Bengali) |
| **Convert to PDF** | JPG→PDF · Word→PDF · PowerPoint→PDF · Excel→PDF · HTML→PDF · **TXT→PDF · RTF→PDF · EPUB→PDF · ZIP→PDF · CSV→PDF · Pages→PDF · HWP/HWPX→PDF · ODT→PDF · ODS→PDF · ODP→PDF** |
| **Convert from PDF** | PDF→JPG · PDF→Word (layout-preserving) · PDF→PowerPoint · PDF→Excel · PDF→PDF/A |
| **Edit PDF** | **PDF Reader (in-browser)** · **PDF Annotator (click-to-note)** · Page numbers · Watermark · Crop · Edit/annotate · **PDF Form Filler (fills real fields)** |
| **PDF Security** | Protect (AES-256) · Unlock · Sign (image) · **Fill & Sign** · Redact (true layer destruction) · **Flatten PDF** · **Request Signatures** · Compare PDFs |
| **PDF Intelligence** | AI Summarizer · **AI PDF Assistant** · **Chat with PDF (Q&A)** · **AI Question Generator** · Translate (17 languages) · PDF→Markdown |

The **All PDF tools** menu shows every tool on one page (6 columns + AI row),
just like iLovePDF — no scrolling needed.

**Workspace UX (like iLovePDF):** after uploading, live page thumbnails appear as
draggable cards (drag to reorder — persisted via `POST /api/reorder`, no re-upload),
a sticky bottom action bar with the main button, real upload progress %, and a
download manager with per-file download + **Download all (.zip)** (`GET /api/zip/<job>`).
Uploaded and generated files are **auto-cleaned after 30 minutes**.

## 🖥️ Quick start

```bash
# 1. install Python deps
pip install -r requirements.txt

# 2. system deps (OCR + PDF/A)
#    Debian/Ubuntu:
sudo apt install -y tesseract-ocr ghostscript poppler-utils

# 3. run
python app.py            # → http://localhost:5000
# or
./run.sh
```

On Windows, run `run.bat` (installs deps automatically).

## 🎛️ REST API

```
GET  /api/tools                      → catalogue of every tool & its options
POST /api/upload                     → multipart form, field "files" (repeatable)
POST /api/process                    → {job_id, tool, options} → result files
GET  /result/<job_id>/<filename>     → download result
GET  /api/preview/<job_id>/<file>    → PNG preview of a PDF result
GET  /api/status/<job_id>            → job info
```

The web UI itself is just a client of this API, so **you can call PDFly from any
language**: see `examples/` — ready-made clients for **PHP, Ruby, Node.js,
C# (.NET), Python, curl** — and the in-app docs at `/docs`.

### Example (Python)

```python
import requests
base = "http://localhost:5000"
up = requests.post(base + "/api/upload",
                   files=[("files", open("a.pdf", "rb")), ("files", open("b.pdf", "rb"))]).json()
res = requests.post(base + "/api/process",
                    json={"job_id": up["job_id"], "tool": "merge_pdf"}).json()
open("merged.pdf", "wb").write(requests.get(base + res["files"][0]["url"]).content)
```

## 🏗️ Architecture

```
pdfly/
├── app.py                 # Flask app: pages + REST API
├── core/
│   ├── registry.py        # single source of truth: tools, options, icons
│   ├── pdf_ops.py         # merge/split/rotate/crop/watermark/numbers/compress/...
│   ├── convert.py         # Word/PPT/Excel/HTML↔PDF, PDF→JPG, OCR, PDF/A
│   ├── security.py        # protect/unlock/sign/redact/compare/forms
│   ├── intelligence.py    # summarizer, translation, markdown
│   ├── storage.py         # per-job temp sandboxes + auto-cleanup
│   └── errors.py
├── templates/             # Jinja2 (home, tool pages, API docs)
├── static/                # CSS + JS (drag&drop, options, results) + SVG icons
└── examples/              # API clients in PHP, Ruby, Node, C#, Python, bash
```

Notes:
- Uploaded files live in `/home/user/pdfly_storage/<job>/` and are auto-deleted after 2 h.
- The web UI is responsive and works on mobile.
- The "AI" summarizer is an offline extractive summarizer (no API key needed).
  Translation uses the free Google Translate endpoint (needs internet).

## 🌐 Language support

- **Frontend/engine:** Python + Flask (+ JavaScript in the browser).
- **Integration:** any language that speaks HTTP — ready examples for C#, PHP,
  Ruby, Node.js and Python are in `examples/`.

## ⚠️ Honest notes

- Uploads: up to **200 files per job** and **2 GB per request** — effectively
  unlimited for local use, and thumbnails/merges stay stable even with many
  files at once (previews are serialized through a PDFium safety lock, so the
  server can never crash from concurrent rendering).
- Free (no cloud) alternatives to `ilovepdf` differ in a few areas: interactive
  drag-and-drop page editor (thumbnails view), and digital form filling are not
  included; the relevant tools export a report instead.
- `compress_pdf` may not shrink already-optimized PDFs.
- OCR needs the `tesseract` binary. Bengali (`ben`) needs `tesseract-ocr-ben`.

## 📷 Screenshots

| Home | Tool page |
|---|---|
| Tool grid with categories like iLovePDF | Drag & drop uploader + options + live preview |

---

## 🇧🇩 বাংলায় (Bangla)

**PDFly** — iLovePDF-এর মতো একটি সম্পূর্ণ PDF টুলস ওয়েবসাইট, যা আপনার নিজের সার্ভারে চলে।
৩৩টি টুল এক জায়গায়: Merge, Split, Compress, Convert (Word/Excel/PowerPoint/JPG/HTML ↔ PDF),
OCR (ইংরেজি + বাংলা), password Protect/Unlock, Signature, Redact, Watermark, Page Number,
PDF/A, PDF তুলনা, AI সারাংশ, অনুবাদ (১৭টি ভাষা), Markdown রূপান্তর — সবকিছু ১০০% ফ্রি।

**চালানোর নিয়ম:**
```bash
pip install -r requirements.txt   # Python লাইব্রেরি
sudo apt install tesseract-ocr ghostscript   # OCR + PDF/A-র জন্য (ঐচ্ছিক)
python app.py                      # → http://localhost:5000
```

**অন্য ভাষা থেকে ব্যবহার:** এই ওয়েবসাইটটির পেছনে একটি clean REST API আছে
(`examples/` ফোল্ডার দেখুন)। PHP, Ruby, Node.js, C#, Python বা bash — যেকোনো ভাষা থেকে
আপনি একই API কল করে PDF ম্যানিপুলেট করতে পারবেন, তাই এটা যেকোনো প্রজেক্টে বসানো যায়।
ডকুমেন্টেশন: ওয়েবসাইটের **API** মেনু থেকে দেখা যাবে (`/docs`)।
