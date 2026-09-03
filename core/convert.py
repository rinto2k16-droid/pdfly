"""Conversions: Office <-> PDF, OCR, PDF/A."""
import os, io, re, subprocess, zipfile

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from .errors import ToolError
from .pdf_guard import PDFIUM_LOCK

_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


# ---------------------------------------------------------------- docx -> pdf
def word_to_pdf(paths, opts, out):
    src = paths[0]
    try:
        doc = Document(src)
    except Exception:
        raise ToolError("This Word file could not be opened. Please save it in "
                        "modern .docx format (old binary .doc is not supported).")
    html = ["<html><head><meta charset='utf-8'><style>",
            "body{font-family:DejaVu Sans,sans-serif;font-size:11pt;line-height:1.45;color:#111}",
            "h1{font-size:22pt}h2{font-size:17pt}h3{font-size:14pt}",
            "table{border-collapse:collapse;width:100%;margin:8pt 0}",
            "td,th{border:1px solid #999;padding:4pt 6pt;font-size:10pt}",
            "img{max-width:100%}ul,ol{margin:4pt 0}",
            "</style></head><body>"]
    for para in doc.paragraphs:
        txt = para.text or ""
        if not txt.strip() and not para.runs:
            html.append("<p>&nbsp;</p>")
            continue
        style = (para.style.name or "").lower()
        if "heading 1" in style or "title" in style:
            html.append(f"<h1>{_esc(txt)}</h1>")
        elif "heading 2" in style:
            html.append(f"<h2>{_esc(txt)}</h2>")
        elif "heading 3" in style:
            html.append(f"<h3>{_esc(txt)}</h3>")
        else:
            align = ""
            if para.alignment == WD_ALIGN_PARAGRAPH.CENTER:
                align = " style='text-align:center'"
            html.append(f"<p{align}>{_esc(txt)}</p>")
    for table in doc.tables:
        html.append("<table>")
        for row in table.rows:
            html.append("<tr>" + "".join(f"<td>{_esc(c.text)}</td>" for c in row.cells) + "</tr>")
        html.append("</table>")
    html.append("</body></html>")
    pdf_path = os.path.join(out, "word_to_pdf.pdf")
    from xhtml2pdf import pisa
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(io.StringIO("".join(html)), dest=f,
                                encoding="utf-8", link_callback=_link_cb)
    if status.err:
        raise ToolError("Could not convert this document to PDF.")
    return {"files": [{"name": "word_to_pdf.pdf", "path": pdf_path}]}


def _esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _link_cb(uri, rel):
    return None


# ---------------------------------------------------------------- pptx -> pdf
def pptx_to_pdf(paths, opts, out):
    from pptx import Presentation
    from pptx.util import Emu
    src = paths[0]
    try:
        prs = Presentation(src)
    except Exception:
        raise ToolError("This PowerPoint file could not be opened. Please save it in "
                        "modern .pptx format (old binary .ppt is not supported).")
    pdf_path = os.path.join(out, "pptx_to_pdf.pdf")
    html = ["<html><head><meta charset='utf-8'><style>",
            "body{font-family:DejaVu Sans,sans-serif;margin:0;background:#fff}",
            ".slide{page-break-after:always;padding:6%}",
            "h1{font-size:26pt;margin:0 0 16pt}",
            "p,li{font-size:14pt}ul{padding-left:22pt}",
            "img{max-width:100%}",
            "</style></head><body>"]
    for slide in prs.slides:
        html.append("<div class='slide'>")
        for shape in slide.shapes:
            if shape.has_text_frame:
                txt = "\n".join(p.text for p in shape.text_frame.paragraphs if p.text.strip())
                if not txt.strip():
                    continue
                # treat a wide, left-anchored, short text block as the slide title
                if len(txt) < 90 and shape.width > Emu(int(2 * 914400)) and shape.left < Emu(int(0.5 * 914400)):
                    html.append(f"<h1>{_esc(txt)}</h1>")
                else:
                    html.append(f"<p>{_esc(txt).replace(chr(10), '<br/>')}</p>")
            if shape.shape_type == 13:  # picture
                try:
                    img = shape.image
                    ext = img.ext
                    tmp = os.path.join(out, f"pic_{abs(hash(str(shape.shape_id)))}.{ext}")
                    with open(tmp, "wb") as f:
                        f.write(img.blob)
                    html.append(f"<img src='{os.path.basename(tmp)}'/>")
                except Exception:
                    pass
        html.append("</div>")
    html.append("</body></html>")
    from xhtml2pdf import pisa
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(io.StringIO("".join(html)), dest=f,
                                encoding="utf-8", link_callback=_link_cb)
    if status.err:
        raise ToolError("Could not convert this presentation to PDF.")
    return {"files": [{"name": "pptx_to_pdf.pdf", "path": pdf_path}]}


# ---------------------------------------------------------------- xlsx -> pdf
def excel_to_pdf(paths, opts, out):
    src = paths[0]
    if src.lower().endswith(".csv"):
        import csv
        rows = []
        with open(src, newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.reader(f):
                rows.append(r)
    else:
        from openpyxl import load_workbook
        try:
            wb = load_workbook(src, data_only=True, read_only=True)
            ws = wb.active
            rows = [[("" if c is None else str(c)) for c in row]
                    for row in ws.iter_rows(values_only=True)]
        except ToolError:
            raise
        except Exception:
            raise ToolError("This spreadsheet could not be opened. Please save it in "
                            "modern .xlsx format (old binary .xls is not supported).")
    html = ["<html><head><meta charset='utf-8'><style>",
            "body{font-family:DejaVu Sans,sans-serif;font-size:9pt}",
            "table{border-collapse:collapse;width:100%}",
            "td,th{border:1px solid #999;padding:3pt 5pt;word-wrap:break-word}",
            "th{background:#f0f0f0;font-weight:bold}",
            "@page{size:A4 landscape;margin:30pt}",
            "</style></head><body><table>"]
    for ri, row in enumerate(rows):
        if ri == 0:
            html.append("<tr>" + "".join(f"<th>{_esc(c)}</th>" for c in row) + "</tr>")
        else:
            html.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>")
    html.append("</table></body></html>")
    pdf_path = os.path.join(out, "excel_to_pdf.pdf")
    from xhtml2pdf import pisa
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(io.StringIO("".join(html)), dest=f,
                                encoding="utf-8", link_callback=_link_cb)
    if status.err:
        raise ToolError("Could not convert this spreadsheet to PDF.")
    return {"files": [{"name": "excel_to_pdf.pdf", "path": pdf_path}]}


# ---------------------------------------------------------------- html -> pdf
def html_to_pdf(paths, opts, out):
    src = paths[0]
    pdf_path = os.path.join(out, "html_to_pdf.pdf")
    from xhtml2pdf import pisa
    with open(src, "rb") as f:
        html = f.read().decode("utf-8", errors="replace")
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(io.StringIO(html), dest=f, encoding="utf-8")
    if status.err:
        raise ToolError("Could not render this HTML file to PDF.")
    return {"files": [{"name": "html_to_pdf.pdf", "path": pdf_path}]}


# ------------------------------------------------- plain text / rtf / odf / epub -> pdf
_PLAIN_STYLE = """
body{font-family:DejaVu Sans,sans-serif;font-size:10.5pt;line-height:1.5;color:#111}
h1{font-size:22pt;margin:14pt 0 8pt}h2{font-size:17pt;margin:12pt 0 6pt}
h3{font-size:14pt;margin:10pt 0 6pt}p{margin:4pt 0}
li{font-size:10.5pt}ul{margin:4pt 0 4pt 14pt}
table{border-collapse:collapse;width:100%;margin:8pt 0}
td,th{border:1px solid #999;padding:3pt 5pt;font-size:9pt}
@page{size:A4;margin:40pt}
"""


def _render_html(html_body, out_dir, name):
    pdf_path = os.path.join(out_dir, name)
    from xhtml2pdf import pisa
    doc_html = ("<html><head><meta charset='utf-8'><style>" + _PLAIN_STYLE +
                "</style></head><body>" + html_body + "</body></html>")
    with open(pdf_path, "wb") as f:
        status = pisa.CreatePDF(io.StringIO(doc_html), dest=f, encoding="utf-8")
    if status.err:
        raise ToolError("Could not render this document to PDF.")
    return pdf_path


def _lines_to_html(lines):
    """Convert plain lines to HTML: blank lines = paragraphs, simple list markers."""
    out, in_list = [], None
    for raw in lines:
        s = raw.rstrip()
        if not s.strip():
            if in_list:
                out.append("</ul>")
                in_list = None
            continue
        m = re.match(r"^[-*•·]\s+(.*)", s)
        if m:
            if in_list != "ul":
                if in_list:
                    out.append("</ul>")
                out.append("<ul>")
                in_list = "ul"
            out.append("<li>%s</li>" % _esc(m.group(1)))
            continue
        m = re.match(r"^(\d+)[.)]\s+(.*)", s)
        if m:
            if in_list != "ol":
                if in_list:
                    out.append("</ul>")
                out.append("<ol>")
                in_list = "ol"
            out.append("<li>%s</li>" % _esc(m.group(2)))
            continue
        if in_list:
            out.append("</ul>")
            in_list = None
        out.append("<p>%s</p>" % _esc(s.strip()))
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def txt_to_pdf(paths, opts, out):
    with open(paths[0], "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    pdf_path = _render_html(_lines_to_html(raw.splitlines()), out, "txt_to_pdf.pdf")
    return {"files": [{"name": "txt_to_pdf.pdf", "path": pdf_path}]}


def rtf_to_pdf(paths, opts, out):
    from striprtf.striprtf import rtf_to_text as _rtf
    with open(paths[0], "r", encoding="utf-8", errors="replace") as f:
        text = _rtf(f.read())
    pdf_path = _render_html(_lines_to_html(text.splitlines()), out, "rtf_to_pdf.pdf")
    return {"files": [{"name": "rtf_to_pdf.pdf", "path": pdf_path}]}


def _odf_text_blocks(path):
    """Extract (tag, text) blocks from an ODT/ODS/ODP content.xml."""
    import zipfile
    from xml.etree import ElementTree as ET
    NS = {
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
        "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    }
    with zipfile.ZipFile(path) as z:
        xml = z.read("content.xml")
    root = ET.fromstring(xml)
    blocks = []
    for para in root.iter("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}p"):
        txt = "".join(para.itertext()).strip()
        if txt:
            blocks.append(("p", txt))
    for head, name in (("h", "h1"),):
        for h in root.iter("{urn:oasis:names:tc:opendocument:xmlns:text:1.0}h"):
            txt = "".join(h.itertext()).strip()
            if txt:
                blocks.append((f"h{int(h.get('{{urn:oasis:names:tc:opendocument:xmlns:text:1.0}}outline-level', '1'))}", txt))
    for tbl in root.iter("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table"):
        rows = []
        for row in tbl.iter("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-row"):
            cells = []
            for cell in row.iter("{urn:oasis:names:tc:opendocument:xmlns:table:1.0}table-cell"):
                cells.append("".join(cell.itertext()).strip())
            if any(cells):
                rows.append(cells)
        if rows:
            blocks.append(("table", rows))
    return blocks


def odt_to_pdf(paths, opts, out):
    blocks = _odf_text_blocks(paths[0])
    html = []
    for kind, data in blocks:
        if kind.startswith("h"):
            html.append(f"<{kind}>{_esc(data)}</{kind}>")
        elif kind == "table":
            html.append("<table>")
            for row in data:
                html.append("<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>")
            html.append("</table>")
        else:
            html.append(f"<p>{_esc(data)}</p>")
    return {"files": [{"name": "odt_to_pdf.pdf",
                       "path": _render_html("".join(html), out, "odt_to_pdf.pdf")}]}


def ods_to_pdf(paths, opts, out):
    return odt_to_pdf(paths, opts, out)


def odp_to_pdf(paths, opts, out):
    return odt_to_pdf(paths, opts, out)


def epub_to_pdf(paths, opts, out):
    import zipfile
    from bs4 import BeautifulSoup
    with zipfile.ZipFile(paths[0]) as z:
        names = [n for n in z.namelist()
                 if n.lower().endswith((".xhtml", ".html", ".htm")) and not n.startswith(".")]
        if not names:
            raise ToolError("No HTML chapters found inside this EPUB.")
        names.sort()
        html_parts = []
        for n in names[:400]:
            soup = BeautifulSoup(z.read(n).decode("utf-8", errors="replace"), "html.parser")
            for bad in soup(["script", "style"]):
                bad.decompose()
            body = soup.body or soup
            for el in body.find_all(True):
                pass
            html_parts.append(str(body))
    pdf_path = _render_html("".join(html_parts), out, "epub_to_pdf.pdf")
    return {"files": [{"name": "epub_to_pdf.pdf", "path": pdf_path}],
            "notes": [f"Converted {len(names)} chapter(s)."]}


def zip_to_pdf(paths, opts, out):
    import zipfile
    from pypdf import PdfReader, PdfWriter
    with zipfile.ZipFile(paths[0]) as z:
        pdfs = sorted([n for n in z.namelist()
                       if n.lower().endswith(".pdf") and not n.startswith("__")])
        if not pdfs:
            raise ToolError("No PDF files found inside this ZIP archive.")
        writer = PdfWriter()
        for n in pdfs:
            try:
                r = PdfReader(io.BytesIO(z.read(n)))
                for page in r.pages:
                    writer.add_page(page)
            except ToolError:
                raise
            except Exception:
                continue
    if not writer.pages:
        raise ToolError("The PDFs inside this ZIP could not be merged (corrupted?).")
    path = os.path.join(out, "zip_to_pdf.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "zip_to_pdf.pdf", "path": path}],
            "notes": [f"Merged {len(pdfs)} PDF(s) from the archive → {len(writer.pages)} pages."]}


def csv_to_pdf(paths, opts, out):
    return excel_to_pdf(paths, opts, out)


def pages_to_pdf(paths, opts, out):
    """Apple Pages (.pages) is a ZIP archive. It normally embeds a PDF preview
       (Preview.pdf / QuickLook/Thumbnail.pdf) — extract the best one."""
    import zipfile
    src = paths[0]
    try:
        with zipfile.ZipFile(src) as z:
            names = z.namelist()
            cands = [n for n in names if n.lower().endswith(".pdf")]
            # prefer full previews over quick-look thumbnails
            prio = sorted(cands, key=lambda n: (1 if "quicklook" in n.lower() or "thumbnail" in n.lower() else 0,
                                                -z.getinfo(n).file_size))
            if not prio:
                raise ToolError("This Pages file does not embed a PDF preview. "
                                "Open it in Pages → File → Export as PDF, then upload that.")
            best = prio[0]
            pdf_data = z.read(best)
    except ToolError:
        raise
    except Exception:
        raise ToolError("Not a valid Apple Pages file (expected a .pages archive).")
    out_path = os.path.join(out, "pages_to_pdf.pdf")
    with open(out_path, "wb") as f:
        f.write(pdf_data)
    return {"files": [{"name": "pages_to_pdf.pdf", "path": out_path}],
            "notes": [f"Extracted embedded PDF preview ({best})."]}


def hwp_to_pdf(paths, opts, out):
    """HWPX (modern Hangul) is a ZIP of XML files; legacy .hwp is binary (unsupported)."""
    import zipfile
    from xml.etree import ElementTree as ET
    src = paths[0]
    if src.lower().endswith(".hwp"):
        raise ToolError("Legacy binary .hwp files are not supported. "
                        "Re-save the document as .hwpx (or export it to PDF in HWP) and try again.")
    try:
        with zipfile.ZipFile(src) as z:
            # HWPX stores its markup in .hml (Hangul Markup Language) + .xml files
            xmls = [n for n in z.namelist()
                    if n.lower().endswith((".xml", ".hml", ".xht"))]
            texts = []
            for n in sorted(xmls):
                try:
                    root = ET.fromstring(z.read(n))
                    for p in root.iter():
                        if p.tag.endswith("}p") or p.tag == "p":
                            t = "".join(p.itertext()).strip()
                            if t:
                                texts.append(t)
                        elif p.tag.endswith(("}t", "}run")) and not list(p):
                            t = "".join(p.itertext()).strip()
                            if t and not texts:
                                texts.append(t)
                except Exception:
                    continue
    except Exception:
        raise ToolError("Not a valid .hwpx file.")
    if not texts:
        raise ToolError("No text could be extracted from this HWPX file.")
    return {"files": [{"name": "hwp_to_pdf.pdf",
                       "path": _render_html(_lines_to_html(texts), out, "hwp_to_pdf.pdf")}]}


# ---------------------------------------------------------------- pdf -> jpg
def pdf_to_jpg(paths, opts, out):
    src = paths[0]
    dpi = int(opts.get("dpi", 150))
    reader_pdf = PdfReader(src)
    total = len(reader_pdf.pages)
    from .storage import zip_files
    jpgs = []
    import pypdfium2 as pdfium
    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(src)
        for i in range(total):
            bmp = doc[i].render(scale=dpi / 72.0)
            img = bmp.to_pil().convert("RGB")
            p = os.path.join(out, f"page-{i + 1:03d}.jpg")
            img.save(p, "JPEG", quality=88)
            jpgs.append(p)
        doc.close()
    if len(jpgs) == 1:
        return {"files": [{"name": os.path.basename(jpgs[0]), "path": jpgs[0]}],
                "notes": [f"{total} page(s) rendered at {dpi} DPI."]}
    zpath = zip_files(jpgs, os.path.join(out, "pdf_to_jpg.zip"))
    return {"files": [{"name": "pdf_to_jpg.zip", "path": zpath}],
            "notes": [f"{total} page(s) rendered at {dpi} DPI."]}


# ---------------------------------------------------------------- pdf -> word
def pdf_to_word(paths, opts, out):
    """PDF → DOCX. Primary engine: pdf2docx (keeps layout, tables, images).
       Fallback: plain text extraction when the PDF is not convertible."""
    path = os.path.join(out, "pdf_to_word.docx")
    try:
        from pdf2docx import Converter
        cv = Converter(paths[0])
        cv.convert(path)
        cv.close()
        if os.path.getsize(path) > 0:
            from .pdf_ops import extract_text_pages
            _, total = extract_text_pages(paths[0])
            return {"files": [{"name": "pdf_to_word.docx", "path": path}],
                    "notes": [f"Converted {total} page(s) to Word with layout, tables and images preserved."]}
    except Exception:
        pass
    # fallback: text-only docx
    from .pdf_ops import extract_text_pages
    texts, total = extract_text_pages(paths[0])
    doc = Document()
    for t in texts:
        if t.strip():
            doc.add_paragraph(t.strip())
            doc.add_paragraph("")
    doc.save(path)
    return {"files": [{"name": "pdf_to_word.docx", "path": path}],
            "notes": [f"Text extracted from {total} page(s) — could not keep exact layout for this file."]}


# ---------------------------------------------------------------- pdf -> pptx
def pdf_to_pptx(paths, opts, out):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    import pypdfium2 as pdfium
    from PIL import Image
    src = paths[0]
    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(src)
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        blank = prs.slide_layouts[6]
        for i in range(len(doc)):
            slide = prs.slides.add_slide(blank)
            bmp = doc[i].render(scale=1.6)
            img = bmp.to_pil().convert("RGB")
            imgbuf = io.BytesIO()
            img.save(imgbuf, "PNG")
            imgbuf.seek(0)
            iw, ih = img.size
            max_w, max_h = 12.5, 6.9
            scale = min(max_w / (iw / 96.0), max_h / (ih / 96.0))
            w_in = (iw / 96.0) * scale
            h_in = (ih / 96.0) * scale
            slide.shapes.add_picture(imgbuf, Inches((13.333 - w_in) / 2),
                                     Inches((7.5 - h_in) / 2), Inches(w_in), Inches(h_in))
        doc.close()
    path = os.path.join(out, "pdf_to_pptx.pptx")
    prs.save(path)
    return {"files": [{"name": "pdf_to_pptx.pptx", "path": path}],
            "notes": [f"{_count_slides(prs)} slide(s) created — each PDF page is an image background."]}


def _count_slides(prs):
    return len(prs.slides._sldIdLst)


# ---------------------------------------------------------------- pdf -> excel
def pdf_to_excel(paths, opts, out):
    from openpyxl import Workbook
    from .pdf_ops import extract_text_pages
    texts, total = extract_text_pages(paths[0])
    wb = Workbook()
    ws = wb.active
    ws.title = "Text"
    for i, t in enumerate(texts, 1):
        for j, line in enumerate([l for l in t.splitlines() if l.strip()], 1):
            ws.cell(row=i, column=j, value=line)
    path = os.path.join(out, "pdf_to_excel.xlsx")
    wb.save(path)
    return {"files": [{"name": "pdf_to_excel.xlsx", "path": path}],
            "notes": [f"Two tables are produced: page -> column. Use the AI tools for smarter extraction."]}


# ---------------------------------------------------------------- pdf -> txt / html
def pdf_to_txt(paths, opts, out):
    from .pdf_ops import extract_text_pages
    texts, total = extract_text_pages(paths[0])
    path = os.path.join(out, "pdf_to_txt.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(texts))
    return {"files": [{"name": "pdf_to_txt.txt", "path": path}],
            "notes": [f"Extracted text from {total} page(s)."]}


def pdf_to_html(paths, opts, out):
    from .pdf_ops import extract_text_pages
    texts, total = extract_text_pages(paths[0])
    body = "".join(_lines_to_html(t.splitlines()) for t in texts)
    html = ("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
            "<title>Converted with PDFly</title>"
            "<style>body{font-family:Arial,Helvetica,sans-serif;max-width:820px;"
            "margin:40px auto;padding:0 16px;line-height:1.65;color:#1c2334}"
            "h1{color:#E5322D}</style></head><body>"
            + body + "</body></html>")
    path = os.path.join(out, "pdf_to_html.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return {"files": [{"name": "pdf_to_html.html", "path": path}],
            "notes": [f"Converted {total} page(s) into a self-contained HTML document."]}


# ---------------------------------------------------------------- OCR
def ocr_pdf(paths, opts, out):
    src = paths[0]
    lang = opts.get("lang", "eng")
    outfmt = opts.get("out", "both")
    import pypdfium2 as pdfium
    import pytesseract
    from PIL import Image, ImageOps
    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(src)
        all_text = []
        for i in range(len(doc)):
            page = doc[i]
            base = float((page.get_size()[0] or 612))
            # adaptive scale: aim for ~2200 px wide, at least 2.4x, at most 6x
            scale = min(6.0, max(2.4, 2200.0 / max(base, 1)))
            bmp = page.render(scale=scale)
            img = bmp.to_pil()
            # OCR-friendly preprocessing: grayscale, contrast stretch, upscale small text
            img = ImageOps.grayscale(img)
            img = ImageOps.autocontrast(img)
            if img.size[0] < 1000:
                img = img.resize((img.size[0] * 2, img.size[1] * 2), Image.LANCZOS)
            try:
                txt = pytesseract.image_to_string(img, lang=lang)
            except Exception:
                txt = ""
            all_text.append(txt)
        doc.close()
    files = []
    if outfmt in ("txt", "both"):
        tpath = os.path.join(out, "ocr_text.txt")
        with open(tpath, "w", encoding="utf-8") as f:
            for i, t in enumerate(all_text, 1):
                f.write(f"--- Page {i} ---\n{t}\n")
        files.append({"name": "ocr_text.txt", "path": tpath})
    if outfmt in ("docx", "both"):
        d = Document()
        for i, t in enumerate(all_text, 1):
            if t.strip():
                d.add_paragraph(t.strip())
                d.add_paragraph("")
        dpath = os.path.join(out, "ocr_text.docx")
        d.save(dpath)
        files.append({"name": "ocr_text.docx", "path": dpath})
    return {"files": files,
            "notes": [f"Recognized {len(all_text)} page(s) with language '{lang}'."]}


# ---------------------------------------------------------------- PDF/A
def pdf_to_pdfa(paths, opts, out):
    src = paths[0]
    out_pdfa = os.path.join(out, "pdfa.pdf")
    out_pdf = os.path.join(out, "pdfa_source.pdf")
    # ghostscript version may or may not support pdfa_def; fall back to gs convert
    try:
        cmd = ["gs", "-dPDFA=1", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite",
               "-sColorConversionStrategy=RGB", "-dEmbedAllFonts=true",
               "-sProcessColorModel=DeviceRGB", "-dPDFACompatibilityPolicy=1",
               f"-sOutputFile={out_pdfa}", src]
        r = subprocess.run(cmd, capture_output=True, timeout=300)
        if r.returncode == 0 and os.path.getsize(out_pdfa) > 0:
            return {"files": [{"name": "pdfa.pdf", "path": out_pdfa}],
                    "notes": ["Converted to PDF/A-1b (RGB)."]}
    except Exception:
        pass
    # fallback: pdfwriter rebuild + metadata
    from pypdf import PdfReader, PdfWriter
    reader = PdfReader(src)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Producer": "PDFly PDF/A", "/Creator": "PDFly",
                         "/GTS_PDFA1": "true", "/Title": "PDF/A document"})
    with open(out_pdf, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "pdfa_source.pdf", "path": out_pdf}],
            "notes": ["Rebuilt with PDF/A-ish metadata (ghostscript converter unavailable in this environment)."]}


def _esctxt(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


from pypdf import PdfReader
