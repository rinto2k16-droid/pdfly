"""PDFly — iLovePDF-style PDF toolkit. Flask backend.

API (all JSON):
  GET  /api/tools                     -> tool catalogue
  POST /api/upload                    -> multipart files -> {job_id, files}
  POST /api/process                   -> {job_id, tool, options} -> result files
  GET  /result/<job_id>/<filename>    -> download a result
  GET  /api/preview/<job_id>/<file>   -> PNG preview (first page) of a PDF result
  GET  /api/status/<job_id>           -> job info
  GET  /health                        -> liveness
"""
import os, io, sys, json, uuid, time, re, subprocess, threading, faulthandler

from flask import Flask, request, jsonify, render_template, send_file, send_from_directory, abort, Response

from core import registry
from core.errors import ToolError
from core.storage import job_dir, cleanup, zip_files
from core import pdf_ops, convert, security, intelligence

BASE = os.path.dirname(os.path.abspath(__file__))
APP_BUILD = "20"   # bump whenever JS/CSS changes -> busts the browser cache via ?v=
app = Flask(__name__, template_folder=os.path.join(BASE, "templates"),
            static_folder=os.path.join(BASE, "static"))
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024  # 2 GB — no practical upload limit
app.config["JSON_SORT_KEYS"] = False
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # no stale JS/CSS in the browser

JOBS = {}  # job_id -> {files: [...], tool, created, status}
_LOCK = threading.Lock()

# ------------------------------------------------------------------ *
#  PDFium (pypdfium2) is a NATIVE C library and is NOT thread-safe:
#  using it from several Flask worker threads at once corrupts the
#  heap and kills the whole server process (SIGABRT — "munmap_chunk():
#  invalid pointer", exit code 134). That is exactly what happened
#  when 3+ files were uploaded: the browser fired 3+ preview
#  requests at the same time. EVERY PDFium call goes through
#  PDFIUM_LOCK (core/pdf_guard.py); page counts use pypdf
#  (pure Python, thread-safe).
# ------------------------------------------------------------------ *
from core.pdf_guard import PDFIUM_LOCK
PREVIEW_CACHE = {}      # (path, page, mtime) -> JPEG bytes (small simple cache)
PREVIEW_CACHE_CAP = 300

ALLOWED_EXT = {
    "pdf": ".pdf", "doc": ".doc", "docx": ".docx", "ppt": ".ppt", "pptx": ".pptx",
    "xls": ".xls", "xlsx": ".xlsx", "xlsm": ".xlsm", "csv": ".csv",
    "html": ".html", "htm": ".htm", "md": ".md", "txt": ".txt",
    "rtf": ".rtf", "epub": ".epub", "zip": ".zip", "odt": ".odt",
    "ods": ".ods", "odp": ".odp", "pages": ".pages", "hwpx": ".hwpx",
    "hwp": ".hwp",
    "png": ".png", "jpg": ".jpg", "jpeg": ".jpeg", "webp": ".webp",
    "gif": ".gif", "bmp": ".bmp", "tiff": ".tiff", "svg": ".svg",
}


# ------------------------------------------------------------------ helpers
def _ext(name):
    return os.path.splitext(name)[1].lower()


def _norm_opts(o):
    if o is None:
        return {}
    if isinstance(o, str):
        try:
            o = json.loads(o)
        except Exception:
            return {}
    return o or {}


def _cleanup_thread():
    while True:
        time.sleep(600)
        try:
            cleanup()
        except Exception:
            pass


threading.Thread(target=_cleanup_thread, daemon=True).start()


@app.after_request
def add_cors(resp):
    """Allow the API from ANY origin — needed for the sandboxed live preview,
       mobile apps, and server-to-server clients (PHP/Node/Ruby/.NET)."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Max-Age"] = "86400"
    # Never let the browser cache JS/CSS/API — stale main.js was the
    # exact reason "choose files" did nothing after an update.
    if request.path.startswith("/static/") or request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
    elif request.path.startswith("/result/"):
        resp.headers["Cache-Control"] = "private, no-cache, must-revalidate"
    return resp


@app.route("/api", methods=["OPTIONS"])
@app.route("/api/<path:rest>", methods=["OPTIONS"])
def cors_preflight(rest=""):
    return ("", 204)


# ------------------------------------------------------------------ pages
@app.context_processor
def _inject_build():
    return {"BUILD": APP_BUILD}


def _ctx(**kw):
    base = {"groups": registry.grouped(),
            "G": registry.G,
            "tools_map": registry.T,
            "icons_json": json.dumps(registry.G),
            "BUILD": APP_BUILD}
    base.update(kw)
    return base


@app.route("/")
def home():
    return render_template("home.html", **_ctx(tools=registry.all_tools()))


@app.route("/tool/<tid>")
def tool_page(tid):
    t = registry.T.get(tid)
    if not t:
        abort(404)
    return render_template("tool.html", **_ctx(t=t))


@app.route("/docs")
def docs_page():
    return render_template("docs.html", **_ctx(tools=registry.all_tools()))


@app.route("/health")
def health():
    return jsonify(ok=True, engine="pdfly", version=APP_BUILD, build=APP_BUILD)


@app.get("/debug")
def debug():
    """One-URL diagnostics: is the storage writable? are OCR/GS installed?
       Open /debug in the browser and check the JSON — every field tells
       you whether a feature can run on this machine."""
    from core.storage import storage_info
    import shutil
    info = storage_info()
    def has(cmd):
        return shutil.which(cmd) is not None
    return jsonify(
        ok=True,
        engine="pdfly",
        python=sys.version.split()[0],
        storage=info,
        system_tools={
            "ghostscript (PDF/A)": has("gs"),
            "tesseract (OCR)": has("tesseract"),
            "pdftoppm (poppler)": has("pdftoppm"),
        },
        tools=len(registry.all_tools()),
        jobs_active=len(JOBS),
        build=APP_BUILD,
    )


@app.get("/api/selftest")
def api_selftest():
    """Real end-to-end test WITH the server's own storage + engine:
       builds a 2-page PDF, saves it through the same path /api/upload
       uses, runs merge_pdf, and verifies the merged output. The result
       tells you in one click whether the SERVER side works."""
    steps, ok_all = [], True

    def add(name, fn):
        nonlocal ok_all
        try:
            detail = fn()
            steps.append({"name": name, "ok": True, "detail": detail})
        except Exception as e:
            ok_all = False
            steps.append({"name": name, "ok": False, "detail": f"{e}"})

    def gen_pdf():
        from pypdf import PdfWriter
        from reportlab.pdfgen import canvas
        import io as _io
        buf = _io.BytesIO()
        c = canvas.Canvas(buf)
        for p in (1, 2):
            c.setFont("Helvetica-Bold", 28)
            c.drawString(72, 740, f"PDFly self-test page {p}")
            c.showPage()
        c.save()
        buf.seek(0)
        w = PdfWriter()
        w.append(buf)
        out = _io.BytesIO()
        w.write(out)
        return out.getvalue()

    def make_job():
        nonlocal job
        data = gen_pdf()
        jid = uuid.uuid4().hex[:12]
        d = job_dir(jid)
        fp = os.path.join(d, "f0.pdf")
        with open(fp, "wb") as fh:
            fh.write(data)
        with _LOCK:
            JOBS[jid] = {"files": [{"name": "selftest.pdf", "ext": ".pdf", "path": fp}],
                         "created": time.time(), "status": "uploaded", "results": []}
        job = jid
        return f"saved {len(data)} bytes -> {fp}"

    def run_merge():
        jf = JOBS[job]["files"][0]
        result = _dispatch("merge_pdf", [jf["path"]], {}, job_dir(job))
        files_out = [{"name": r["name"], "key": os.path.basename(r["path"])}
                     for r in result.get("files", [])]
        if not files_out:
            raise RuntimeError("engine returned no output files")
        with _LOCK:
            JOBS[job]["results"] = files_out
        return f"engine produced {len(files_out)} file(s): {[f['name'] for f in files_out]}"

    def verify():
        from pypdf import PdfReader
        with _LOCK:
            res = JOBS[job]["results"]
        path = os.path.join(job_dir(job), res[0]["key"])
        if not os.path.exists(path):
            raise RuntimeError("output file missing on disk")
        r = PdfReader(path)
        if len(r.pages) < 2:
            raise RuntimeError(f"merged PDF has {len(r.pages)} pages, expected >=2")
        return f"merged PDF verified: {len(r.pages)} pages, readable"

    def check_storage():
        from core.storage import storage_info as _si
        i = _si()
        if not i["writable"]:
            raise RuntimeError(f"storage NOT writable: {i['root']}")
        return (f"root={i['root']} · writable=yes · disk_free={i['disk_free_mb']} MB · "
                f"temp={i['temp_dir']} · cleanup={i['max_age_min']} min")

    def cleanup():
        JOBS.pop(job, None)
        return "test job removed"

    job = None
    add("1. storage writable", check_storage)
    add("2. create test PDF + save via storage", make_job)
    add("3. run engine (merge_pdf)", run_merge)
    add("4. verify output PDF", verify)
    add("5. cleanup test job", cleanup)
    return jsonify(ok=ok_all, build=APP_BUILD, steps=steps)


@app.get("/api/tools")
def api_tools():
    return jsonify(ok=True, tools=registry.all_tools())


# ------------------------------------------------------------------ upload
@app.post("/api/upload")
def api_upload():
    # accept "files" (primary) or "file" (single) — belt & suspenders
    files = request.files.getlist("files") or request.files.getlist("file")
    if not files:
        return jsonify(ok=False, error="No files were uploaded. Select a file and try again."), 400
    job_id = uuid.uuid4().hex[:12]
    try:
        d = job_dir(job_id)
    except Exception as e:
        app.logger.exception("storage dir failed")
        return jsonify(ok=False, error=f"Server storage is not writable: {e}"), 500
    # 1) validate ALL files before saving anything
    metas = []
    for i, f in enumerate(files):
        base_name = (f.filename or f"file{i}").replace("\\", "/").split("/")[-1]
        ext = _ext(base_name).lower()
        if ext not in ALLOWED_EXT.values():
            return jsonify(ok=False, error=f"Unsupported file type: '{ext or '?'}' "
                                           "— upload a PDF, Office document or image."), 400
        metas.append((i, base_name, ext))

    # 2) save each file, fully guarded
    files_final = []
    for i, base_name, ext in metas:
        try:
            fp = os.path.join(d, f"f{i}{ext}")
            files[i].save(fp)
            files_final.append({"name": base_name, "ext": ext, "path": fp})
            app.logger.info("uploaded %s (%s, %d bytes) -> %s", base_name, ext,
                            os.path.getsize(fp), fp)
        except Exception as e:
            app.logger.exception("saving file %s failed", base_name)
            return jsonify(ok=False,
                           error=f"Server could not save '{base_name}': {e}"), 500
    with _LOCK:
        JOBS[job_id] = {"files": files_final, "created": time.time(),
                        "status": "uploaded", "results": []}
    from core.storage import storage_info
    return jsonify(ok=True, status="success", job_id=job_id,
                   file_ids=[os.path.basename(x["path"]) for x in files_final],
                   storage=storage_info()["root"],
                   files=[{"name": x["name"], "size": os.path.getsize(x["path"]),
                           "ext": x["ext"], "key": os.path.basename(x["path"])}
                          for x in files_final])


# ------------------------------------------------------------------ process
@app.post("/api/process")
def api_process():
    data = request.get_json(silent=True) or {}
    job_id = str(data.get("job_id") or "")
    tid = str(data.get("tool") or "")
    opts = _norm_opts(data.get("options"))
    with _LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify(ok=False, error="Uploaded files not found — please upload again."), 404
    t = registry.T.get(tid)
    if not t:
        return jsonify(ok=False, error=f"Unknown tool '{tid}'."), 400

    paths = [x["path"] for x in job["files"] if os.path.exists(x["path"])]
    if not paths:
        return jsonify(ok=False, error="No files in this job."), 400

    minf = t.get("min_files", 1)
    if len(paths) < minf:
        return jsonify(ok=False, error=f"This tool needs at least {minf} file(s)."), 400
    if len(paths) > t.get("max_files", 1):
        return jsonify(ok=False, error=f"This tool accepts at most {t.get('max_files')} file(s)."), 400

    # per-tool file-type validation
    accepts = [a.strip().lower() for a in (t.get("accept") or "").split(",") if a.strip()]
    for p in paths:
        if accepts and _ext(p) not in accepts:
            return jsonify(ok=False, error=f"'{os.path.basename(p)}' is not accepted by {t['title']} "
                                           f"(expected {', '.join(accepts)})."), 400

    out = job_dir(job_id)  # results live inside the job's own sandbox folder
    try:
        result = _dispatch(tid, paths, opts, out)
    except ToolError as e:
        return jsonify(ok=False, error=str(e)), 400
    except Exception as e:
        app.logger.exception("process failed")
        return jsonify(ok=False, error=f"Processing failed: {e}"), 500

    files_out = []
    for r in result.get("files", []):
        p = r["path"]
        files_out.append({"name": r["name"],
                          "url": f"/result/{os.path.basename(os.path.dirname(p))}/{os.path.basename(p)}",
                          "size": os.path.getsize(p),
                          "key": os.path.basename(p)})
    with _LOCK:
        JOBS[job_id]["status"] = "done"
        JOBS[job_id]["results"] = result.get("files", [])
    return jsonify(ok=True, status="success", files=files_out, notes=result.get("notes", []))


def _dispatch(tid, paths, opts, out):
    P = pdf_ops
    if tid == "merge_pdf":
        return P.merge_pdf(paths, opts, out)
    if tid == "split_pdf":
        return P.split_pdf(paths, opts, out)
    if tid == "remove_pages":
        return P.remove_pages(paths, opts, out)
    if tid == "extract_pages":
        return P.extract_pages(paths, opts, out)
    if tid == "organize_pdf":
        return P.organize_pdf(paths, opts, out)
    if tid == "rotate_pdf":
        return P.rotate_pdf(paths, opts, out)
    if tid == "crop_pdf":
        return P.crop_pdf(paths, opts, out)
    if tid == "compress_pdf":
        return P.compress_pdf(paths, opts, out)
    if tid == "repair_pdf":
        return P.repair_pdf(paths, opts, out)
    if tid == "watermark_pdf":
        return P.watermark_pdf(paths, opts, out)
    if tid == "page_numbers":
        return P.page_numbers(paths, opts, out)
    if tid == "edit_pdf":
        return P.edit_pdf(paths, opts, out)
    if tid == "scan_to_pdf":
        return P.scan_to_pdf(paths, opts, out)
    if tid == "pdf_scanner":
        return P.scan_to_pdf(paths, opts, out)
    if tid == "jpg_to_pdf":
        return P.jpg_to_pdf(paths, opts, out)
    if tid == "annotator_pdf":
        return P.annotate_pdf(paths, opts, out)
    if tid == "word_to_pdf":
        return convert.word_to_pdf(paths, opts, out)
    if tid == "pptx_to_pdf":
        return convert.pptx_to_pdf(paths, opts, out)
    if tid == "excel_to_pdf":
        return convert.excel_to_pdf(paths, opts, out)
    if tid == "html_to_pdf":
        return convert.html_to_pdf(paths, opts, out)
    if tid == "txt_to_pdf":
        return convert.txt_to_pdf(paths, opts, out)
    if tid == "rtf_to_pdf":
        return convert.rtf_to_pdf(paths, opts, out)
    if tid == "epub_to_pdf":
        return convert.epub_to_pdf(paths, opts, out)
    if tid == "zip_to_pdf":
        return convert.zip_to_pdf(paths, opts, out)
    if tid == "csv_to_pdf":
        return convert.csv_to_pdf(paths, opts, out)
    if tid == "odt_to_pdf":
        return convert.odt_to_pdf(paths, opts, out)
    if tid == "ods_to_pdf":
        return convert.ods_to_pdf(paths, opts, out)
    if tid == "odp_to_pdf":
        return convert.odp_to_pdf(paths, opts, out)
    if tid == "pages_to_pdf":
        return convert.pages_to_pdf(paths, opts, out)
    if tid == "hwp_to_pdf":
        return convert.hwp_to_pdf(paths, opts, out)
    if tid == "pdf_to_jpg":
        return convert.pdf_to_jpg(paths, opts, out)
    if tid == "pdf_to_word":
        return convert.pdf_to_word(paths, opts, out)
    if tid == "pdf_to_pptx":
        return convert.pdf_to_pptx(paths, opts, out)
    if tid == "pdf_to_excel":
        return convert.pdf_to_excel(paths, opts, out)
    if tid == "pdf_to_txt":
        return convert.pdf_to_txt(paths, opts, out)
    if tid == "pdf_to_html":
        return convert.pdf_to_html(paths, opts, out)
    if tid == "ocr_pdf":
        return convert.ocr_pdf(paths, opts, out)
    if tid == "pdf_to_pdfa":
        return convert.pdf_to_pdfa(paths, opts, out)
    if tid == "protect_pdf":
        return security.protect_pdf(paths, opts, out)
    if tid == "unlock_pdf":
        return security.unlock_pdf(paths, opts, out)
    if tid == "sign_pdf":
        sig = None
        pdfs = []
        for x in paths:
            if _ext(x) in (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff"):
                sig = x
            else:
                pdfs.append(x)
        if not pdfs:
            raise ToolError("Please upload one PDF and one signature image.")
        return security.sign_pdf(pdfs, opts, out, signature_path=sig)
    if tid == "redact_pdf":
        return security.redact_pdf(paths, opts, out)
    if tid == "compare_pdf":
        return security.compare_pdf(paths, opts, out)
    if tid == "flatten_pdf":
        return security.flatten_pdf(paths, opts, out)
    if tid == "request_signatures":
        return security.request_signatures(paths, opts, out)
    if tid == "fill_sign_pdf":
        return security.fill_sign_pdf(paths, opts, out)
    if tid == "pdf_forms":
        return security.pdf_forms(paths, opts, out)
    if tid == "pdf_reader":
        return {"files": [{"name": os.path.basename(paths[0]), "path": paths[0]}],
                "notes": ["Opened in the browser reader below — or press Download."]}
    if tid == "ai_summarize":
        return intelligence.summarize_pdf(paths, opts, out)
    if tid == "ai_assistant":
        return intelligence.ai_assistant(paths, opts, out)
    if tid == "translate_pdf":
        return intelligence.translate_pdf(paths, opts, out)
    if tid == "pdf_to_markdown":
        return intelligence.pdf_to_markdown(paths, opts, out)
    if tid == "chat_pdf":
        return intelligence.chat_pdf(paths, opts, out)
    if tid == "ai_questions":
        return intelligence.ai_questions(paths, opts, out)
    raise ToolError(f"Tool '{tid}' is not implemented.")


# ------------------------------------------------------------------ results
@app.get("/result/<job_id>/<path:filename>")
def download(job_id, filename):
    # only serve files inside a job dir whose id we generated
    if not re.fullmatch(r"[0-9a-f]+", job_id) or "/" in filename or ".." in filename:
        abort(400)
    from core.storage import STORAGE_ROOT
    root = os.path.join(STORAGE_ROOT, job_id)
    full = os.path.join(root, filename)
    if not os.path.isfile(full):
        abort(404)
    resp = send_file(full, as_attachment=True, download_name=filename)
    return resp


@app.get("/api/preview/<job_id>/<path:filename>")
def preview(job_id, filename):
    if not re.fullmatch(r"[0-9a-f]+", job_id) or ".." in filename or "/" in filename:
        abort(400)
    from core.storage import STORAGE_ROOT
    full = os.path.join(STORAGE_ROOT, job_id, filename)
    if not os.path.isfile(full):
        abort(404)
    try:
        page_no = max(0, int(request.args.get("page", 0)))
    except Exception:
        page_no = 0
    try:
        mtime = os.path.getmtime(full)
    except Exception:
        mtime = 0
    ck = (full, page_no, mtime)
    hit = PREVIEW_CACHE.get(ck)
    if hit:
        return Response(hit, mimetype="image/jpeg")
    try:
        with PDFIUM_LOCK:                     # single PDFium user at a time!
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(full)
            try:
                total = len(doc)
                p = max(0, min(total - 1, page_no))
                bmp = doc[p].render(scale=1.3)
                img = bmp.to_pil().convert("RGB")
            finally:
                doc.close()
        w, h = img.size
        if h / w > 2.2:                       # normalize long pages
            img = img.crop((0, 0, w, int(w * 2.2)))
        if img.width > 1400:                  # cap memory for huge scans
            img.thumbnail((1400, 2100))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        data = buf.getvalue()
        if len(PREVIEW_CACHE) > PREVIEW_CACHE_CAP:
            PREVIEW_CACHE.clear()
        PREVIEW_CACHE[ck] = data
        return Response(data, mimetype="image/jpeg")
    except Exception:
        abort(404)


@app.get("/api/pages/<job_id>/<path:filename>")
def page_count(job_id, filename):
    if not re.fullmatch(r"[0-9a-f]+", job_id) or ".." in filename or "/" in filename:
        abort(400)
    from core.storage import STORAGE_ROOT
    full = os.path.join(STORAGE_ROOT, job_id, filename)
    if not os.path.isfile(full):
        abort(404)
    # pypdf is pure Python -> safe in threads (first choice, never crashes)
    try:
        from pypdf import PdfReader
        with open(full, "rb") as fh:
            n = len(PdfReader(fh).pages)
        return jsonify(ok=True, pages=n)
    except Exception:
        pass
    # fallback: PDFium, serialized by PDFIUM_LOCK
    try:
        with PDFIUM_LOCK:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(full)
            try:
                n = len(doc)
            finally:
                doc.close()
        return jsonify(ok=True, pages=n)
    except Exception:
        abort(404)


@app.get("/api/status/<job_id>")
def status(job_id):
    j = JOBS.get(job_id)
    if not j:
        return jsonify(ok=False, error="Job not found"), 404
    return jsonify(ok=True, status=j.get("status"))


# ------------------------------------------------------------------ reorder
@app.post("/api/reorder")
def api_reorder():
    """Persist a drag-and-drop order change on the uploaded files (no re-upload!)."""
    data = request.get_json(silent=True) or {}
    job_id = str(data.get("job_id") or "")
    order = data.get("order")
    with _LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify(ok=False, error="Job not found — please upload again."), 404
    if not isinstance(order, list) or len(order) != len(job["files"]):
        return jsonify(ok=False, error="Order must cover every file exactly once."), 400
    try:
        order = [int(i) for i in order]
    except (TypeError, ValueError):
        return jsonify(ok=False, error="Order must be a list of indices."), 400
    if sorted(order) != list(range(len(job["files"]))):
        return jsonify(ok=False, error="Order must be a permutation of the file indices."), 400
    with _LOCK:
        job["files"] = [job["files"][i] for i in order]
    return jsonify(ok=True, status="success", order=order)


# ------------------------------------------------------------------ results zip
@app.get("/api/zip/<job_id>")
def api_results_zip(job_id):
    """Download ALL result files of a job as one ZIP ('Download all' button)."""
    with _LOCK:
        job = JOBS.get(job_id)
        results = list(job["results"]) if job else []
    if not results:
        abort(404)
    finals = [r["path"] for r in results if os.path.isfile(r.get("path", ""))]
    if len(finals) == 0:
        abort(404)
    if len(finals) == 1:
        return send_file(finals[0], as_attachment=True, download_name=os.path.basename(finals[0]))
    from core.storage import zip_files
    zpath = zip_files(finals, os.path.join(os.path.dirname(finals[0]), "pdfly_results.zip"))
    return send_file(zpath, as_attachment=True, download_name="pdfly_results.zip")


# ------------------------------------------------------------------ errors
@app.errorhandler(404)
def e404(e):
    if request.path.startswith(("/api", "/result")):
        return jsonify(ok=False, error="Not found"), 404
    return render_template("error.html", **_ctx(code=404, message="Page not found")), 404


@app.errorhandler(413)
def e413(e):
    return jsonify(ok=False, error="File too large (limit 300 MB per request)."), 413


@app.errorhandler(500)
def e500(e):
    if request.path.startswith("/api"):
        return jsonify(ok=False, error="Internal server error"), 500
    return render_template("error.html", code=500, message="Something broke"), 500


if __name__ == "__main__":
    faulthandler.enable()   # if anything native ever crashes, the console shows WHERE
    port = int(os.environ.get("PORT", 5000))
    print("=" * 64)
    print(f"  PDFly build {APP_BUILD} — your PDF toolkit is starting")
    print(f"  Open in your browser:  http://localhost:{port}")
    print("  Server console shows every upload (file name + bytes).")
    print(f"  Diagnostics page:      http://localhost:{port}/debug")
    print("  Uploads: unlimited (200 files per job, up to 2 GB per upload)")
    print("=" * 64, flush=True)
    while True:
        try:
            app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
            break                                   # clean Ctrl+C exit
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:                      # unexpected crash -> auto-restart
            print(f"[PDFly] server error: {e!r} — restarting in 3 s…", flush=True)
            time.sleep(3)
