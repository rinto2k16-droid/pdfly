"""Core PDF manipulation tools (organize / optimize / edit)."""
import os, re, io, math
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .errors import ToolError
from .pdf_guard import PDFIUM_LOCK

# unicode-capable fonts if available
_FONT = "Helvetica"
try:
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    _FONT = "DejaVu"
except Exception:
    pass

_ACCENTS = {"DejaVu": "DejaVu-Bold", "Helvetica": "Helvetica-Bold"}


def _page_size(page):
    mb = page.mediabox
    return float(mb.width), float(mb.height)


def _overlay_page(w, h, draw):
    """Build a one-page PDF (canvas) and return its PageObject."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(w, h))
    draw(c)
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def _writer_out(writer, out_dir, name):
    path = os.path.join(out_dir, name)
    with open(path, "wb") as f:
        writer.write(f)
    return path


def parse_pages(spec, total):
    """'2,4-6,9' -> set of 0-based indexes."""
    out = set()
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a
            for n in range(a, b + 1):
                if 1 <= n <= total:
                    out.add(n - 1)
        else:
            n = int(part)
            if 1 <= n <= total:
                out.add(n - 1)
    return out


# ---------------------------------------------------------------- merge / split
def merge_pdf(paths, opts, out):
    writer = PdfWriter()
    for p in paths:
        reader = PdfReader(p)
        for page in reader.pages:
            writer.add_page(page)
    writer.add_metadata({"/Producer": "PDFly", "/Creator": "PDFly"})
    return {"files": [{"name": "merged.pdf", "path": _writer_out(writer, out, "merged.pdf")}],
            "notes": [f"{len(writer.pages)} pages merged from {len(paths)} files."]}


def split_pdf(paths, opts, out):
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    mode = opts.get("mode", "every")
    produced = []
    if mode == "every":
        for i in range(total):
            w = PdfWriter()
            w.add_page(reader.pages[i])
            produced.append(_writer_out(w, out, f"page-{i + 1:03d}.pdf"))
    elif mode == "ranges":
        groups = parse_groups(opts.get("ranges", ""), total)
        if not groups:
            raise ToolError("No valid ranges given. Example: 1-3, 4, 7-9")
        for gi, g in enumerate(groups, 1):
            w = PdfWriter()
            for i in g:
                w.add_page(reader.pages[i])
            produced.append(_writer_out(w, out, f"part-{gi:02d}.pdf"))
    else:  # size
        chunk = max(1, int(opts.get("chunk", 5)))
        for gi, start in enumerate(range(0, total, chunk), 1):
            w = PdfWriter()
            for i in range(start, min(start + chunk, total)):
                w.add_page(reader.pages[i])
            produced.append(_writer_out(w, out, f"part-{gi:02d}.pdf"))
    if len(produced) > 1:
        from .storage import zip_files
        zpath = zip_files(produced, os.path.join(out, "split_result.zip"))
        return {"files": [{"name": "split_result.zip", "path": zpath}],
                "notes": [f"{total} pages -> {len(produced)} PDF file(s)."]}
    return {"files": [{"name": os.path.basename(produced[0]), "path": produced[0]}]}


def parse_groups(spec, total):
    """'1-3,4,7-9' -> [[0,1,2],[3],[6,7,8]] (0-based)."""
    groups = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a
            groups.append(list(range(max(1, a) - 1, min(total, b))))
        else:
            n = int(part)
            if 1 <= n <= total:
                groups.append([n - 1])
    return groups


def remove_pages(paths, opts, out):
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    rm = parse_pages(opts.get("pages", ""), total)
    keep = total - len(rm)
    if keep < 1:
        raise ToolError("You removed every page — nothing left to save.")
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if (i in rm) != bool(opts.get("invert", False)):
            continue
        writer.add_page(page)
    return {"files": [{"name": "pages_removed.pdf", "path": _writer_out(writer, out, "pages_removed.pdf")}],
            "notes": [f"Removed {len(rm)} page(s); {keep} page(s) kept."]}


def extract_pages(paths, opts, out):
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    sel = parse_pages(opts.get("pages", ""), total)
    if not sel:
        raise ToolError("No valid pages selected.")
    writer = PdfWriter()
    for i in sorted(sel):
        writer.add_page(reader.pages[i])
    return {"files": [{"name": "extracted_pages.pdf", "path": _writer_out(writer, out, "extracted_pages.pdf")}],
            "notes": [f"Extracted {len(sel)} page(s) into a new PDF."]}


def organize_pdf(paths, opts, out):
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    writer = PdfWriter()
    if opts.get("reverse"):
        order = list(range(total - 1, -1, -1))
    elif str(opts.get("order", "")).strip():
        order = []
        for tok in str(opts["order"]).split(","):
            tok = tok.strip()
            if not tok:
                continue
            n = int(tok)
            if not (1 <= n <= total):
                raise ToolError(f"Page {n} out of range (document has {total} pages).")
            order.append(n - 1)
        if len(set(order)) != total:
            raise ToolError("Your order must include every page exactly once.")
    else:
        order = list(range(total))
    for i in order:
        writer.add_page(reader.pages[i])
    return {"files": [{"name": "organized.pdf", "path": _writer_out(writer, out, "organized.pdf")}]}


def rotate_pdf(paths, opts, out):
    reader = PdfReader(paths[0])
    angle = int(opts.get("angle", 90))
    if angle not in (90, 180, 270):
        raise ToolError("Angle must be 90, 180 or 270.")
    writer = PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    return {"files": [{"name": f"rotated_{angle}.pdf", "path": _writer_out(writer, out, f"rotated_{angle}.pdf")}]}


def crop_pdf(paths, opts, out):
    reader = PdfReader(paths[0])
    writer = PdfWriter()
    for page in reader.pages:
        w, h = _page_size(page)
        t = float(opts.get("top", 0)) / 100.0
        r = float(opts.get("right", 0)) / 100.0
        b = float(opts.get("bottom", 0)) / 100.0
        l = float(opts.get("left", 0)) / 100.0
        if t + b >= 1 or l + r >= 1:
            raise ToolError("Margins are too large — the page would disappear.")
        x0, y0 = float(page.mediabox.left), float(page.mediabox.bottom)
        page.mediabox.left = x0 + w * l
        page.mediabox.right = x0 + w * (1 - r)
        page.mediabox.bottom = y0 + h * b
        page.mediabox.top = y0 + h * (1 - t)
        writer.add_page(page)
    return {"files": [{"name": "cropped.pdf", "path": _writer_out(writer, out, "cropped.pdf")}]}


# ---------------------------------------------------------------- optimize
def repair_pdf(paths, opts, out):
    reader = PdfReader(paths[0])
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata({"/Producer": "PDFly (repaired)", "/Creator": "PDFly"})
    return {"files": [{"name": "repaired.pdf", "path": _writer_out(writer, out, "repaired.pdf")}],
            "notes": ["The file was re-parsed and rebuilt; damaged objects were dropped."]}


def compress_pdf(paths, opts, out):
    src = paths[0]
    orig_size = os.path.getsize(src)
    level = opts.get("level", "medium")
    scale, quality = {"low": (2.0, 80), "medium": (1.5, 62), "high": (1.1, 45)}[level]

    # method A: structural rewrite
    a_path = None
    try:
        reader = PdfReader(src)
        writer = PdfWriter()
        for page in reader.pages:
            if hasattr(page, "compress_content"):
                try:
                    page.compress_content()
                except Exception:
                    pass
            writer.add_page(page)
        writer.add_metadata({"/Producer": "PDFly compressed"})
        a_path = _writer_out(writer, out, "compress_a.pdf")
    except Exception:
        a_path = None

    # method B: rasterize pages to JPEG
    b_path = None
    try:
        import pypdfium2 as pdfium
        from PIL import Image
        from reportlab.lib.utils import ImageReader
        with PDFIUM_LOCK:
            doc = pdfium.PdfDocument(src)
            writer = PdfWriter()
            for i in range(len(doc)):
                bmp = doc[i].render(scale=scale)
                img = bmp.to_pil().convert("RGB")
                jbuf = io.BytesIO()
                img.save(jbuf, "JPEG", quality=quality, optimize=True)
                jbuf.seek(0)
                iw, ih = img.size
                cbuf = io.BytesIO()
                c = rl_canvas.Canvas(cbuf, pagesize=(iw, ih))
                c.drawImage(ImageReader(jbuf), 0, 0, width=iw, height=ih)
                c.save()
                cbuf.seek(0)
                reader = PdfReader(cbuf)
                writer.add_page(reader.pages[0])
            doc.close()
        b_path = _writer_out(writer, out, "compress_b.pdf")
    except Exception:
        b_path = None

    cands = [p for p in (a_path, b_path) if p and os.path.getsize(p) < orig_size]
    if not cands:
        raise ToolError("Sorry — this file could not be compressed further, and rewriting it "
                        "would not make it smaller. It is likely already highly optimized.")
    best = min(cands, key=os.path.getsize)
    final = os.path.join(out, "compressed.pdf")
    if os.path.abspath(best) != os.path.abspath(final):
        os.replace(best, final)
    saved = 100 * (1 - os.path.getsize(final) / orig_size)
    note = "Rasterized pages (images) were used to reach this size." if os.path.basename(best).startswith("compress_b") else "Content streams were rewritten and optimised."
    return {"files": [{"name": "compressed.pdf", "path": final}],
            "notes": [f"File size reduced by {saved:.1f}% ({orig_size / 1024:.0f} KB → {os.path.getsize(final) / 1024:.0f} KB). {note}"]}


# ---------------------------------------------------------------- edit
def watermark_pdf(paths, opts, out):
    reader = PdfReader(paths[0])
    text = str(opts.get("text", "")) or "CONFIDENTIAL"
    opacity = max(0.03, min(1.0, float(opts.get("opacity", 20)) / 100.0))
    size = float(opts.get("size", 70))
    tile = bool(opts.get("tile", True))
    diag = bool(opts.get("diag", True))
    font = str(opts.get("font", _FONT))
    writer = PdfWriter()
    cache = {}
    for page in reader.pages:
        w, h = _page_size(page)
        if (w, h) not in cache:
            def draw(c, w=w, h=h):
                c.setFont(font, size)
                c.setFillAlpha(opacity)
                c.setFillColorRGB(0.55, 0.55, 0.55)
                if tile:
                    step = max(size * 2.6, 190)
                    for x in range(-int(h), int(w) + int(h), int(step)):
                        for y in range(-int(w), int(h) + int(w), int(step)):
                            c.saveState()
                            c.translate(x, y)
                            if diag:
                                c.rotate(45)
                            c.drawCentredString(0, 0, text)
                            c.restoreState()
                else:
                    c.saveState()
                    c.translate(w / 2, h / 2)
                    if diag:
                        c.rotate(45)
                    c.drawCentredString(0, 0, text)
                    c.restoreState()
            cache[(w, h)] = _overlay_page(w, h, draw)
        page.merge_page(cache[(w, h)], over=True)
        writer.add_page(page)
    return {"files": [{"name": "watermarked.pdf", "path": _writer_out(writer, out, "watermarked.pdf")}]}


def page_numbers(paths, opts, out):
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    fmt = opts.get("format", "n")
    pos = opts.get("pos", "bc")
    size = float(opts.get("size", 12))
    prefix = str(opts.get("prefix", ""))
    def make_overlay(w, h, disp):
        def draw(c):
            c.setFont(_FONT, size)
            c.setFillColorRGB(0.25, 0.25, 0.25)
            dx = {"bc": (w / 2, 20), "br": (w - 25, 20), "bl": (25, 20),
                  "tc": (w / 2, h - 25), "tr": (w - 25, h - 25)}[pos]
            if pos.endswith("r"):
                c.drawRightString(dx[0], dx[1], disp)
            elif pos.endswith("l"):
                c.drawString(dx[0] - 20, dx[1], disp)
            else:
                c.drawCentredString(dx[0], dx[1], disp)
        return _overlay_page(w, h, draw)

    writer = PdfWriter()
    cache = {}  # (w,h) -> overlay page
    for i, page in enumerate(reader.pages, 1):
        w, h = _page_size(page)
        if fmt == "n":
            disp = f"{prefix}{i}"
        elif fmt == "pagen":
            disp = f"{prefix}Page {i}"
        elif fmt == "nm":
            disp = f"{prefix}{i} / {total}"
        else:
            disp = f"{prefix}Page {i} of {total}"
        key = (round(w), round(h))
        if key not in cache:
            cache[key] = make_overlay(w, h, disp)
        page.merge_page(cache[key], over=True)
        writer.add_page(page)
    return {"files": [{"name": "numbered.pdf", "path": _writer_out(writer, out, "numbered.pdf")}]}


def edit_pdf(paths, opts, out):
    """Add text annotations over pages (simplified 'Edit PDF')."""
    reader = PdfReader(paths[0])
    text = str(opts.get("text", "")).strip()
    if not text:
        raise ToolError("Please type some text to add.")
    pos = opts.get("pos", "top")
    size = float(opts.get("size", 18))
    color = str(opts.get("color", "#000000"))
    r = int(color[1:3], 16) / 255.0
    g = int(color[3:5], 16) / 255.0
    b = int(color[5:7], 16) / 255.0
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        apply_page = pos != "first" or i == 0
        if apply_page:
            w, h = _page_size(page)
            def draw(c, w=w, h=h, r=r, g=g, b=b, size=size, text=text):
                c.setFont(_FONT, size)
                c.setFillColorRGB(r, g, b)
                tw = c.stringWidth(text, _FONT, size)
                c.drawString(25, h - 25 - size, text)
                c.setStrokeColorRGB(r, g, b)
                c.setLineWidth(1)
                c.line(25, h - 30 - size, 25 + tw, h - 30 - size)
            ov = _overlay_page(w, h, draw)
            page.merge_page(ov, over=True)
        writer.add_page(page)
    return {"files": [{"name": "annotated.pdf", "path": _writer_out(writer, out, "annotated.pdf")}],
            "notes": ["Text annotations were added. (Full drag-and-drop editing is not available offline.)"]}


def scan_to_pdf(paths, opts, out):
    return _images_to_pdf(paths, opts, out)


def jpg_to_pdf(paths, opts, out):
    return _images_to_pdf(paths, opts, out)


def _images_to_pdf(paths, opts, out):
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    mode = opts.get("mode", "single")
    pagesize = opts.get("pagesize", "fit")
    margin = float(opts.get("margin", 0)) * 72 / 25.4  # mm -> pt
    ocr = bool(opts.get("ocr", False))
    ocr_lang = opts.get("lang", "eng")
    images = []
    for p in paths:
        im = Image.open(p)
        im.load()
        if im.mode in ("RGBA", "P", "LA"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")
        images.append(im)

    def build(ims):
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf)
        for im in ims:
            iw, ih = im.size
            if pagesize == "auto":
                pw, ph = iw, ih
            elif pagesize == "a4":
                pw, ph = A4
                if iw > ih:
                    pw, ph = ph, pw
            else:
                pw, ph = A4
            c.setPageSize((pw, ph))
            avail_w, avail_h = pw - 2 * margin, ph - 2 * margin
            scale = min(avail_w / iw, avail_h / ih)
            dw, dh = iw * scale, ih * scale
            c.drawImage(ImageReader(_pil_to_bytes(im)),
                        (pw - dw) / 2, (ph - dh) / 2, width=dw, height=dh)
            c.showPage()
        c.save()
        buf.seek(0)
        return buf

    def _pil_to_bytes(im):
        b = io.BytesIO()
        im.save(b, "PNG")
        b.seek(0)
        return b

    buf = build(images)
    files = []
    if mode == "each":
        from .storage import zip_files
        parts = []
        for i, im in enumerate(images, 1):
            b = build([im])
            with open(os.path.join(out, f"image-{i:02d}.pdf"), "wb") as f:
                f.write(b.getvalue())
            parts.append(os.path.join(out, f"image-{i:02d}.pdf"))
        zpath = zip_files(parts, os.path.join(out, "images_to_pdf.zip"))
        files = [{"name": "images_to_pdf.zip", "path": zpath}]
    else:
        pdf_path = os.path.join(out, "images.pdf")
        with open(pdf_path, "wb") as f:
            f.write(buf.getvalue())
        files = [{"name": "images.pdf", "path": pdf_path}]
    notes = [f"{len(images)} image(s) converted to PDF."]
    if ocr:
        notes.append("OCR layer skipped for plain images — use OCR PDF for scanned documents, "
                     "or run the Convert PDF → JPG then OCR flow.")
    return {"files": files, "notes": notes}


def annotate_pdf(paths, opts, out):
    """Stamp text notes at percentage coordinates chosen in the browser annotator."""
    import json as _json
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    raw = str(opts.get("annotations") or "[]")
    try:
        notes = _json.loads(raw)
    except Exception:
        notes = []
    if not notes:
        raise ToolError("Click on the page preview to place at least one note, "
                        "then press 'Convert / Process'.")
    # group notes by 0-based page index
    by_page = {}
    for n in notes:
        pg = int(n.get("page", 1)) - 1
        if 0 <= pg < total:
            by_page.setdefault(pg, []).append(n)

    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        mine = by_page.get(i)
        if mine:
            w, h = _page_size(page)
            page_notes = list(mine)
            def draw(c, w=w, h=h, page_notes=page_notes):
                for n in page_notes:
                    x = float(n.get("x", 50)) / 100.0 * w
                    y = float(n.get("y", 50)) / 100.0 * h
                    size = float(n.get("size", 14))
                    color = str(n.get("color", "#E5322D"))
                    r = int(color[1:3], 16) / 255.0
                    g = int(color[3:5], 16) / 255.0
                    b = int(color[5:7], 16) / 255.0
                    text = str(n.get("text", "")).strip()
                    if not text:
                        continue
                    c.setFont(_FONT, size)
                    c.setFillColorRGB(r, g, b)
                    c.setStrokeColorRGB(r, g, b)
                    c.setLineWidth(0.8)
                    c.rect(x - 4, y - size * 0.35, c.stringWidth(text, _FONT, size) + 8,
                           size * 1.3, stroke=1, fill=0)
                    c.drawString(x, y - size * 0.25, text)
            page.merge_page(_overlay_page(w, h, draw), over=True)
        writer.add_page(page)
    return {"files": [{"name": "annotated.pdf", "path": _writer_out(writer, out, "annotated.pdf")}],
            "notes": [f"Stamped {len(notes)} note(s)."]}


# ---------------------------------------------------------------- reusable
def extract_text_pages(path, max_pages=None):
    reader = PdfReader(path)
    texts = []
    for i, page in enumerate(reader.pages):
        if max_pages and i >= max_pages:
            break
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            texts.append("")
    return texts, len(reader.pages)
