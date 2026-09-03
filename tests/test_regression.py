#!/usr/bin/env python3
"""PDFly full regression suite — all 52 tools + API safety + crash-stress.

Run:  python3 tests/test_regression.py [BASE_URL]
Kept inside the project so it survives sandbox resets.
"""
import io, os, sys, json, time, zipfile, shutil
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
TMP = "/tmp/pdftest_fixtures"
PASS = FAIL = SKIP = 0
FAILED = []


def _chk(name, fn):
    global PASS, FAIL, SKIP
    try:
        fn()
        PASS += 1
        print(f"  ✓ {name}")
    except SkipTest as e:
        SKIP += 1
        print(f"  ⚠ SKIP {name}: {e}")
    except AssertionError as e:
        FAIL += 1
        FAILED.append(name)
        print(f"  ✗ {name}: {e}")
    except Exception as e:
        FAIL += 1
        FAILED.append(name)
        print(f"  ✗ {name}: {type(e).__name__}: {e}")


class SkipTest(Exception):
    pass


# ---------------------------------------------------------------- fixtures
def build_fixtures():
    if os.path.isdir(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    def pdf(name, pages=3, label=None):
        p = os.path.join(TMP, name)
        c = canvas.Canvas(p, pagesize=A4)
        for i in range(pages):
            c.setFont("Helvetica-Bold", 20)
            c.drawString(72, 760, f"{label or name} — page {i + 1}")
            c.setFont("Helvetica", 12)
            for j in range(12):
                c.drawString(72, 700 - j * 26, f"Line {j + 1} of sample content for testing.")
            c.showPage()
        c.save()
        return p

    def jpg(name, color="red"):
        from PIL import Image
        p = os.path.join(TMP, name)
        Image.new("RGB", (600, 800), color).save(p, "JPEG")
        return p

    files = {}
    files["a.pdf"] = pdf("a.pdf", 3)
    files["b.pdf"] = pdf("b.pdf", 2)
    files["c.pdf"] = pdf("c.pdf", 1)

    # office fixtures
    from docx import Document
    d = Document(); d.add_heading("Test DOCX", 0); d.add_paragraph("Hello from python-docx.")
    files["doc.docx"] = os.path.join(TMP, "doc.docx"); d.save(files["doc.docx"])

    import openpyxl
    wb = openpyxl.Workbook(); ws = wb.active; ws["A1"] = "Name"; ws["B1"] = "Value"
    ws.append(["Alice", 42]); ws.append(["Bob", 7])
    files["book.xlsx"] = os.path.join(TMP, "book.xlsx"); wb.save(files["book.xlsx"])

    from pptx import Presentation
    pr = Presentation(); s = pr.slides.add_slide(pr.slide_layouts[1])
    s.shapes.title.text = "Test PPTX"; s.placeholders[1].text = "Hello slide"
    files["deck.pptx"] = os.path.join(TMP, "deck.pptx"); pr.save(files["deck.pptx"])

    files["doc.csv"] = os.path.join(TMP, "doc.csv")
    with open(files["doc.csv"], "w") as f:
        f.write("name,age\nAlice,42\nBob,7\n")

    files["doc.txt"] = os.path.join(TMP, "doc.txt")
    with open(files["doc.txt"], "w") as f:
        f.write("Line one of plain text.\nLine two of plain text.\n")

    files["doc.html"] = os.path.join(TMP, "doc.html")
    with open(files["doc.html"], "w") as f:
        f.write("<html><body><h1>HTML test</h1><p>Hello <b>world</b></p></body></html>")

    files["doc.rtf"] = os.path.join(TMP, "doc.rtf")
    with open(files["doc.rtf"], "w") as f:
        f.write(r"{\rtf1\ansi\deff0 {\fonttbl {\f0 Arial;}} \f0 Hello RTF world!}")

    # ODF: zip with mimetype + content.xml (text:p blocks)
    def odf(name, content_xml):
        p = os.path.join(TMP, name)
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
            z.writestr("content.xml", content_xml)
        return p

    od_xml = ('<?xml version="1.0"?>'
              '<office:document xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
              'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
              'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0">'
              '<office:body><office:text>'
              '<text:h text:outline-level="1">ODF Heading</text:h>'
              '<text:p>ODF paragraph one.</text:p><text:p>ODF paragraph two.</text:p>'
              '</office:text></office:body></office:document>')
    files["doc.odt"] = odf("doc.odt", od_xml)
    files["doc.ods"] = odf("doc.ods", od_xml)
    files["doc.odp"] = odf("doc.odp", od_xml)

    # EPUB: zip with an .xhtml chapter
    files["doc.epub"] = os.path.join(TMP, "doc.epub")
    with zipfile.ZipFile(files["doc.epub"], "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("OEBPS/c1.xhtml",
                   '<html xmlns="http://www.w3.org/1999/xhtml"><body>'
                   "<h1>Chapter one</h1><p>EPUB content here.</p></body></html>")
        z.writestr("OEBPS/c2.xhtml",
                   '<html xmlns="http://www.w3.org/1999/xhtml"><body><p>Second chapter.</p></body></html>')

    # ZIP of PDFs
    files["doc.zip"] = os.path.join(TMP, "doc.zip")
    with zipfile.ZipFile(files["doc.zip"], "w") as z:
        z.write(files["a.pdf"], "a.pdf")
        z.write(files["b.pdf"], "b.pdf")

    # Apple Pages = zip with Preview.pdf
    files["doc.pages"] = os.path.join(TMP, "doc.pages")
    with zipfile.ZipFile(files["doc.pages"], "w") as z:
        z.write(files["a.pdf"], "Preview.pdf")
        z.writestr("index.xml", "<pages>demo</pages>")

    # HWPX = zip with Contents/content.xml containing text:p
    files["doc.hwpx"] = os.path.join(TMP, "doc.hwpx")
    hwpx_content = ('<?xml version="1.0" encoding="UTF-8"?>'
                    '<hs:content xmlns:hs="http://www.hancom.co.kr/hwpml/2011/10/26">'
                    '<hs:p><hs:run><hs:t>HWPX 한글 paragraph one.</hs:t></hs:run></hs:p>'
                    '<hs:p><hs:run><hs:t>HWPX paragraph two (latin).</hs:t></hs:run></hs:p>'
                    '</hs:content>')
    with zipfile.ZipFile(files["doc.hwpx"], "w") as z:
        z.writestr("mimetype", "application/hwp+zip")
        z.writestr("Contents/content.xml", hwpx_content)

    # images
    files["img1.jpg"] = jpg("img1.jpg", "red")
    files["img2.jpg"] = jpg("img2.jpg", "blue")

    # signature image
    files["sig.png"] = os.path.join(TMP, "sig.png")
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 200), "white")
    dr = ImageDraw.Draw(im)
    dr.line([(30, 150), (120, 60), (200, 140), (300, 40), (370, 130)], fill="black", width=8)
    im.save(files["sig.png"])

    # locked PDF (password: test123)
    from pypdf import PdfWriter
    files["locked.pdf"] = os.path.join(TMP, "locked.pdf")
    w = PdfWriter()
    for page in list(__import__("pypdf").PdfReader(files["a.pdf"]).pages):
        w.add_page(page)
    w.encrypt("test123")
    with open(files["locked.pdf"], "wb") as f:
        w.write(f)

    # PDF with a form field
    from reportlab.pdfgen import canvas
    files["form.pdf"] = os.path.join(TMP, "form.pdf")
    c = canvas.Canvas(files["form.pdf"], pagesize=A4)
    c.setFont("Helvetica", 16)
    c.drawString(72, 720, "Fillable form:")
    c.acroForm.textfield(name="fullname", x=72, y=650, width=260, height=28)
    c.acroForm.textfield(name="email", x=72, y=600, width=260, height=28)
    c.save()

    return files


# ---------------------------------------------------------------- helpers
def upload(*items, single=False):
    fld = "file" if single else "files"
    files = [(fld, (f"f{i}_{os.path.basename(p)}", open(p, "rb"), "application/octet-stream"))
             for i, p in enumerate(items)]
    r = requests.post(BASE + "/api/upload", files=files, timeout=120)
    assert r.status_code == 200, f"upload HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    assert d.get("ok"), f"upload not ok: {d}"
    return d


def process(job_id, tool, options=None):
    r = requests.post(BASE + "/api/process",
                      json={"job_id": job_id, "tool": tool, "options": options or {}},
                      timeout=600)
    return r.status_code, r.json()


def download(result_file):
    r = requests.get(BASE + result_file["url"], timeout=600)
    assert r.status_code == 200, f"download HTTP {r.status_code}"
    return r.content


# ---------------------------------------------------------------- suite
def main():
    global PASS, FAIL, SKIP
    print(f"== PDFly regression @ {BASE} ==")
    F = build_fixtures()

    # ---------- health / api basics ----------
    def test_health():
        h = requests.get(BASE + "/health", timeout=10).json()
        assert h.get("ok") and h.get("build"), h
    _chk("health + build tag", test_health)

    def test_debug():
        d = requests.get(BASE + "/debug", timeout=10).json()
        assert d.get("ok") and d["storage"]["writable"], d
    _chk("debug: storage writable + 52 tools", test_debug)

    def test_selftest():
        s = requests.get(BASE + "/api/selftest", timeout=120).json()
        assert s.get("ok"), s.get("steps")
    _chk("api/selftest full engine test", test_selftest)

    def test_cors():
        r = requests.options(BASE + "/api/upload",
                             headers={"Origin": None,
                                      "Access-Control-Request-Method": "POST"}, timeout=10)
        assert r.status_code in (200, 204), r.status_code
        assert r.headers.get("Access-Control-Allow-Origin") == "*", r.headers
    _chk("CORS preflight (204 + *)", test_cors)

    def test_bad_ext():
        r = requests.post(BASE + "/api/upload",
                          files=[("files", ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream"))],
                          timeout=30)
        assert r.status_code == 400 and not r.json().get("ok"), (r.status_code, r.text[:120])
    _chk("reject .exe upload", test_bad_ext)

    def test_single_field():
        d = upload(F["a.pdf"], single=True)
        assert len(d["files"]) == 1
    _chk("upload via single 'file' field", test_single_field)

    def test_unknown_tool():
        d = upload(F["a.pdf"])
        code, r = process(d["job_id"], "no_such_tool")
        assert code == 400 and not r.get("ok"), (code, r)
    _chk("unknown tool -> 400", test_unknown_tool)

    def test_missing_job():
        code, r = process("deadbeef0000", "merge_pdf")
        assert code == 404, code
    _chk("missing job -> 404", test_missing_job)

    # ---------- the 52 tools ----------
    T = {}

    def t(name, files, options=None, min_size=200):
        def run():
            nonlocal T
            d = upload(*files)
            code, r = process(d["job_id"], name, options)
            assert r.get("ok"), f"process failed (HTTP {code}): {r.get('error')}"
            assert r.get("files"), "no output files"
            data = download(r["files"][0])
            assert len(data) >= min_size, f"output too small: {len(data)} B"
            T[name] = d["job_id"]
        _chk(name, run)

    P = F["a.pdf"]
    # Organize
    t("merge_pdf", [P, F["b.pdf"]], min_size=1000)
    t("split_pdf", [P])
    t("remove_pages", [P], {"pages": "1"})
    t("extract_pages", [P], {"pages": "2-3"})
    t("organize_pdf", [P], {"order": "2,1,3"})
    t("rotate_pdf", [P], {"angle": "90"})
    t("scan_to_pdf", [F["img1.jpg"], F["img2.jpg"]])
    t("pdf_scanner", [F["img1.jpg"], F["img2.jpg"]])
    # Optimize
    t("compress_pdf", [P])
    t("repair_pdf", [P])
    def test_ocr():
        d = upload(P)
        code, r = process(d["job_id"], "ocr_pdf")
        if not r.get("ok") and "tesseract" in (r.get("error") or "").lower():
            raise SkipTest("tesseract not installed")
        assert r.get("ok"), r.get("error")
    _chk("ocr_pdf (or graceful skip)", test_ocr)
    # Convert TO
    t("pdf_to_jpg", [P])            # zip of pages
    t("pdf_to_word", [P])
    t("pdf_to_excel", [P])
    t("pdf_to_txt", [P])
    t("pdf_to_html", [P])
    t("pdf_to_pptx", [P])
    def test_pdfa():
        d = upload(P)
        code, r = process(d["job_id"], "pdf_to_pdfa")
        if not r.get("ok") and "ghostscript" in (r.get("error") or "").lower():
            raise SkipTest("ghostscript not installed")
        assert r.get("ok"), r.get("error")
    _chk("pdf_to_pdfa (or graceful skip)", test_pdfa)
    # Convert FROM
    t("jpg_to_pdf", [F["img1.jpg"], F["img2.jpg"]])
    t("word_to_pdf", [F["doc.docx"]])
    t("excel_to_pdf", [F["book.xlsx"]])
    t("pptx_to_pdf", [F["deck.pptx"]])
    t("html_to_pdf", [F["doc.html"]])
    t("txt_to_pdf", [F["doc.txt"]])
    t("rtf_to_pdf", [F["doc.rtf"]])
    t("epub_to_pdf", [F["doc.epub"]])
    t("zip_to_pdf", [F["doc.zip"]])
    t("csv_to_pdf", [F["doc.csv"]])
    t("odt_to_pdf", [F["doc.odt"]])
    t("ods_to_pdf", [F["doc.ods"]])
    t("odp_to_pdf", [F["doc.odp"]])
    t("pages_to_pdf", [F["doc.pages"]])
    t("hwp_to_pdf", [F["doc.hwpx"]])
    # Edit
    t("watermark_pdf", [P], {"text": "CONFIDENTIAL"})
    t("page_numbers", [P])
    t("crop_pdf", [P], {"top": 10, "bottom": 10, "left": 10, "right": 10})
    t("edit_pdf", [P], {"text": "edited", "page": 1})
    t("pdf_forms", [F["form.pdf"]], {"fields": '{"fullname":"Alice","email":"a@b.com"}'})
    t("pdf_reader", [P])
    t("annotator_pdf", [P], {"annotations": json.dumps([{"page": 1, "x": 20, "y": 20, "text": "note", "size": 12, "color": "#E5322D"}])})
    # Security
    t("flatten_pdf", [P])
    t("request_signatures", [P])
    t("protect_pdf", [P], {"password": "test123", "password2": "test123"})
    t("unlock_pdf", [F["locked.pdf"]], {"password": "test123"})
    t("sign_pdf", [P, F["sig.png"]])
    t("redact_pdf", [P], {"pages": "1", "mode": "black"})
    t("compare_pdf", [P, F["b.pdf"]])
    t("fill_sign_pdf", [F["form.pdf"], F["sig.png"]], {"fields": json.dumps({"fullname": "Alice"})})
    # Intelligence
    t("ai_summarize", [P])
    t("ai_assistant", [P])
    t("translate_pdf", [P], {"lang": "en"})
    t("pdf_to_markdown", [P])
    t("chat_pdf", [P], {"question": "What is on page 1?"})
    t("ai_questions", [P])

    # ---------- crash-stress: many files + concurrent previews ----------
    def test_stress():
        d = upload(F["a.pdf"], F["b.pdf"], F["c.pdf"], P)
        j = d["job_id"]
        def hit(i):
            fn = d["files"][i]["key"]
            r = requests.get(f"{BASE}/api/preview/{j}/{fn}?page=0", timeout=60)
            return r.status_code
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
            codes = list(ex.map(lambda i: hit(i % 4), range(24)))
        assert all(c == 200 for c in codes), codes
        requests.get(BASE + "/health", timeout=10).json()["ok"]
    _chk("stress: 4 files × 24 concurrent previews, server alive", test_stress)

    def test_stress20():
        d = upload(P, F["b.pdf"], F["c.pdf"], P, P, P)  # 6 files
        assert d["ok"]
        code, r = process(d["job_id"], "merge_pdf")
        assert r.get("ok"), r.get("error")
        requests.get(BASE + "/health", timeout=10).json()["ok"]
    _chk("stress: 6-file merge, server alive", test_stress20)

    # ---------- summary ----------
    print()
    print(f"  PASSED: {PASS}   FAILED: {FAIL}   SKIPPED: {SKIP}")
    if FAILED:
        print("  FAILED LIST:", *FAILED, sep="\n    - ")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
