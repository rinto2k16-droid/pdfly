# PDFly — production image
# Build:  docker build -t pdfly .
# Run:    docker run -p 5000:5000 -v pdfly_data:/app/pdfly_storage pdfly
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PDFLY_STORAGE=/app/pdfly_storage

# system libs: fontconfig (fonts), tesseract (OCR), ghostscript (PDF/A)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core tesseract-ocr ghostscript poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN mkdir -p /app/pdfly_storage

EXPOSE 5000
# production WSGI server (Flask's dev server is not for production)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "2", "-t", "300", "app:app"]
