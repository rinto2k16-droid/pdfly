"""PDF security tools: protect, unlock, sign, redact, compare."""
import os, io, re

from pypdf import PdfReader, PdfWriter
from .errors import ToolError
from .pdf_guard import PDFIUM_LOCK


def protect_pdf(paths, opts, out):
    src = paths[0]
    pw = str(opts.get("password") or "")
    pw2 = str(opts.get("password2") or "")
    if len(pw) < 4:
        raise ToolError("Password must be at least 4 characters long.")
    if pw != pw2:
        raise ToolError("The passwords do not match.")
    reader = PdfReader(src)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(pw, owner_password=pw, algorithm="AES-256")
    path = os.path.join(out, "protected.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "protected.pdf", "path": path}],
            "notes": ["AES-256 encryption applied."]}


def unlock_pdf(paths, opts, out):
    src = paths[0]
    pw = str(opts.get("password") or "")
    reader = PdfReader(src)
    if reader.is_encrypted:
        if not pw:
            raise ToolError("This PDF is password protected — enter the password to unlock it.")
        try:
            ok = reader.decrypt(pw)
        except Exception:
            ok = False
        if not ok:
            raise ToolError("Wrong password — could not unlock this PDF.")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    path = os.path.join(out, "unlocked.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "unlocked.pdf", "path": path}],
            "notes": ["Password removed — the copy is now free to open and edit."]}


def sign_pdf(paths, opts, out, signature_path=None):
    """signature_path is an extra file (PNG/JPG) uploaded together with the PDF."""
    src = paths[0]
    if not signature_path or not os.path.exists(signature_path):
        raise ToolError("Please upload a signature image (PNG with transparency works best) "
                        "together with your PDF.")
    from reportlab.lib.utils import ImageReader
    from PIL import Image
    im = Image.open(signature_path)
    iw, ih = im.size
    imgbuf = io.BytesIO()
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        imgbuf_isalpha = True
    else:
        imgbuf_isalpha = False
    im.save(imgbuf, "PNG")
    imgbuf.seek(0)

    pos = opts.get("pos", "br")
    scale_pct = max(1, min(80, int(opts.get("scale", 25)))) / 100.0

    reader = PdfReader(src)
    writer = PdfWriter()
    for page in reader.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        dw = w * scale_pct
        dh = dw * ih / iw
        pad = 30
        x = {"br": w - dw - pad, "bl": pad,
             "tr": w - dw - pad, "tl": pad, "center": (w - dw) / 2}[pos]
        y = {"br": pad, "bl": pad, "tr": h - dh - pad, "tl": h - dh - pad,
             "center": (h - dh) / 2}[pos]
        from reportlab.pdfgen import canvas as rl_canvas
        cbuf = io.BytesIO()
        c = rl_canvas.Canvas(cbuf, pagesize=(w, h))
        c.drawImage(ImageReader(imgbuf), x, y, width=dw, height=dh, mask="auto")
        c.save()
        cbuf.seek(0)
        ov = PdfReader(cbuf).pages[0]
        page.merge_page(ov, over=True)
        writer.add_page(page)
    path = os.path.join(out, "signed.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "signed.pdf", "path": path}],
            "notes": [f"Signature image ({iw}x{ih} px) placed at {pos} on every page."]}


def redact_pdf(paths, opts, out):
    """Destroy the text layer of selected pages by flattening them to images.
       mode=black  -> page is replaced by a solid black rectangle.
       mode=raster -> page becomes a plain image: visible content stays,
                      but the text layer is really gone (nothing can be copied)."""
    src = paths[0]
    reader = PdfReader(src)
    total = len(reader.pages)
    pages_to_redact = set()
    spec = str(opts.get("pages") or "")
    if spec.strip():
        from .pdf_ops import parse_pages
        pages_to_redact = parse_pages(spec, total)
    if not pages_to_redact:
        pages_to_redact = set(range(total))
    mode = opts.get("mode", "black")

    import pypdfium2 as pdfium
    from PIL import Image
    from reportlab.lib.utils import ImageReader

    with PDFIUM_LOCK:
        doc = pdfium.PdfDocument(src)
        writer = PdfWriter()
        for i, page in enumerate(reader.pages):
            if i in pages_to_redact:
                w, h = float(page.mediabox.width), float(page.mediabox.height)
                if mode == "black":
                    from reportlab.pdfgen import canvas as rl_canvas
                    cbuf = io.BytesIO()
                    c = rl_canvas.Canvas(cbuf, pagesize=(w, h))
                    c.setFillColorRGB(0, 0, 0)
                    c.rect(0, 0, w, h, stroke=0, fill=1)
                    c.save()
                    cbuf.seek(0)
                    writer.add_page(PdfReader(cbuf).pages[0])
                else:
                    # flatten: rasterize the page into a lossless image -> no text layer
                    bmp = doc[i].render(scale=2.0)
                    img = bmp.to_pil().convert("RGB")
                    jbuf = io.BytesIO()
                    img.save(jbuf, "JPEG", quality=90)
                    jbuf.seek(0)
                    from reportlab.pdfgen import canvas as rl_canvas
                    cbuf = io.BytesIO()
                    c = rl_canvas.Canvas(cbuf, pagesize=(w, h))
                    c.drawImage(ImageReader(jbuf), 0, 0, width=w, height=h)
                    c.save()
                    cbuf.seek(0)
                    writer.add_page(PdfReader(cbuf).pages[0])
            else:
                writer.add_page(page)
        doc.close()
    path = os.path.join(out, "redacted.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "redacted.pdf", "path": path}],
            "notes": [f"Redacted {len(pages_to_redact)} page(s): the text layer was destroyed "
                      "and the pages were flattened — content can no longer be copied."]}


def compare_pdf(paths, opts, out):
    from .pdf_ops import extract_text_pages
    ta, na = extract_text_pages(paths[0])
    tb, nb = extract_text_pages(paths[1])
    maxpages = max(na, nb)
    changes = []
    ignore_space = bool(opts.get("ignore_space", True))

    def norm(s):
        return re.sub(r"\s+", " ", s).strip() if ignore_space else s

    for i in range(maxpages):
        a = norm(ta[i]) if i < na else "(no page)"
        b = norm(tb[i]) if i < nb else "(no page)"
        if a != b:
            changes.append(i + 1)
    report = os.path.join(out, "comparison_report.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write("PDF COMPARISON REPORT — generated by PDFly\n")
        f.write(f"File A: {os.path.basename(paths[0])} ({na} pages)\n")
        f.write(f"File B: {os.path.basename(paths[1])} ({nb} pages)\n\n")
        if changes:
            f.write(f"Changed pages: {', '.join(map(str, changes))}\n\n")
            for i in changes[:10]:
                idx = i - 1
                a = norm(ta[idx]) if idx < na else "(no page)"
                b = norm(tb[idx]) if idx < nb else "(no page)"
                f.write(f"--- Page {i} ---\nA: {a[:220]}\nB: {b[:220]}\n\n")
        else:
            f.write("No text differences found.\n")
    return {"files": [{"name": "comparison_report.txt", "path": report}],
            "notes": [f"{len(changes)} page(s) contain text differences."]}


def pdf_forms(paths, opts, out):
    """Real AcroForm filler: fills fields from a JSON dict and flattens the result."""
    import json as _json
    reader = PdfReader(paths[0])
    total = len(reader.pages)
    fields = {}
    try:
        if reader.get_fields():
            for k, v in reader.get_fields().items():
                values = v.get("/V", "") if hasattr(v, "get") else ""
                fields[k] = values
    except Exception:
        pass

    raw = str(opts.get("fields") or "").strip()
    if not raw:
        # no fill data given -> export the field list so the user knows what to fill
        report = os.path.join(out, "form_fields.txt")
        with open(report, "w", encoding="utf-8") as f:
            f.write("PDF FORM REPORT — generated by PDFly\n")
            f.write(f"Total pages: {total}\n\n")
            if fields:
                f.write("Detected fields (paste as JSON into the 'Field values' box, e.g.):\n")
                f.write('{"' + '": "...", "'.join(fields.keys()) + '": "..."}\n\n')
                for k, v in fields.items():
                    f.write(f"  {k} = {v}\n")
            else:
                f.write("No interactive form fields were detected.\n")
                f.write("This is most likely a flat PDF — you can scan it with OCR instead.\n")
        return {"files": [{"name": "form_fields.txt", "path": report}],
                "notes": [f"{len(fields)} field(s) found. Fill in the 'Field values' option as JSON "
                          "and process again to download the filled PDF."]}

    try:
        fill = _json.loads(raw)
        if not isinstance(fill, dict):
            raise ValueError
    except Exception:
        raise ToolError("The field values must be JSON like {\"name\": \"Rahim\"}.")

    from pypdf.generic import NameObject, TextStringObject, DictionaryObject, ArrayObject
    writer = PdfWriter()
    try:
        # clone preserves the interactive form (AcroForm) structure
        writer.clone_document_from_reader(reader)
    except Exception:
        for page in reader.pages:
            writer.add_page(page)

    # fill field values directly on every widget (robust across pypdf versions)
    filled, unknown = 0, []
    for page in writer.pages:
        annots = page.get(NameObject("/Annots"))
        if not annots:
            continue
        try:
            arr = annots.get_object() if hasattr(annots, "get_object") else annots
        except Exception:
            continue
        for a in arr:
            try:
                obj = a.get_object() if hasattr(a, "get_object") else a
            except Exception:
                continue
            t = obj.get(NameObject("/T"))
            if not t:
                continue
            key = str(t)
            if key in fill:
                obj[NameObject("/V")] = TextStringObject(str(fill[key]))
                obj[NameObject("/DA")] = TextStringObject("/Helv 12 Tf 0 0 0 rg")
                filled += 1
    # make viewers regenerate appearances
    try:
        root = writer._root_object
        af = root.get(NameObject("/AcroForm"))
        if af is not None:
            af_obj = af.get_object() if hasattr(af, "get_object") else af
            af_obj[NameObject("/NeedAppearances")] = bool(True)
    except Exception:
        pass
    for k in fill:
        if k not in fields:
            unknown.append(k)
    if not filled:
        raise ToolError("None of the provided field names matched — detected fields: "
                        + (", ".join(fields.keys()) if fields else "none"))

    out_pdf = os.path.join(out, "form_filled.pdf")
    with open(out_pdf, "wb") as f:
        writer.write(f)
    note = f"Filled {filled} field(s) in a form with {total} page(s). "
    if unknown:
        note += f"Unknown names ignored: {', '.join(unknown)}. "
    note += "Use 'Flatten PDF' afterwards to make the copy read-only."
    return {"files": [{"name": "form_filled.pdf", "path": out_pdf}],
            "notes": [note]}


def fill_sign_pdf(paths, opts, out):
    """Smallpdf-style 'Fill & Sign': fill form fields (JSON) AND stamp a
       signature image on every page — one click, one output file."""
    pdfs = [p for p in paths if _is_pdf(p)]
    sig = next((p for p in paths if not _is_pdf(p)), None)
    if not pdfs:
        raise ToolError("Upload one PDF (and optionally a signature image).")
    src = pdfs[0]

    # 1) fill fields if JSON was provided
    import json as _json
    reader = PdfReader(src)
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ToolError("This PDF is password-protected — unlock it first.")
    fields = {}
    try:
        if reader.get_fields():
            fields = {k: "" for k in reader.get_fields().keys()}
    except Exception:
        pass
    raw = str(opts.get("fields") or "").strip()
    fill = {}
    if raw:
        try:
            fill = _json.loads(raw)
            if not isinstance(fill, dict):
                raise ValueError
        except Exception:
            raise ToolError("Field values must be JSON like {\"name\": \"Rahim\"}.")
    writer = PdfWriter()
    try:
        writer.clone_document_from_reader(reader)
    except Exception:
        for page in reader.pages:
            writer.add_page(page)
    from pypdf.generic import NameObject, TextStringObject
    filled = 0
    for page in writer.pages:
        annots = page.get(NameObject("/Annots"))
        if not annots:
            continue
        try:
            arr = annots.get_object() if hasattr(annots, "get_object") else annots
        except Exception:
            continue
        for a in arr:
            try:
                obj = a.get_object() if hasattr(a, "get_object") else a
                t = obj.get(NameObject("/T"))
            except Exception:
                continue
            if t and str(t) in fill:
                obj[NameObject("/V")] = TextStringObject(str(fill[str(t)]))
                filled += 1
    try:
        root = writer._root_object
        af = root.get(NameObject("/AcroForm"))
        if af is not None:
            afo = af.get_object() if hasattr(af, "get_object") else af
            afo[NameObject("/NeedAppearances")] = bool(True)
    except Exception:
        pass

    # 2) stamp signature on every page
    sig_notes = []
    if sig and os.path.exists(sig):
        from reportlab.lib.utils import ImageReader
        from PIL import Image
        im = Image.open(sig)
        iw, ih = im.size
        imgbuf = io.BytesIO()
        im.save(imgbuf, "PNG")
        imgbuf.seek(0)
        pos = opts.get("pos", "br")
        scale_pct = max(1, min(80, int(opts.get("scale", 25)))) / 100.0
        for page in writer.pages:
            w, h = float(page.mediabox.width), float(page.mediabox.height)
            dw = w * scale_pct
            dh = dw * ih / iw
            pad = 30
            x = {"br": w - dw - pad, "bl": pad, "tr": w - dw - pad, "tl": pad,
                 "center": (w - dw) / 2}[pos]
            y = {"br": pad, "bl": pad, "tr": h - dh - pad, "tl": h - dh - pad,
                 "center": (h - dh) / 2}[pos]
            from reportlab.pdfgen import canvas as rl_canvas
            cbuf = io.BytesIO()
            c = rl_canvas.Canvas(cbuf, pagesize=(w, h))
            c.drawImage(ImageReader(imgbuf), x, y, width=dw, height=dh, mask="auto")
            c.save()
            cbuf.seek(0)
            ov = PdfReader(cbuf).pages[0]
            page.merge_page(ov, over=True)
        sig_notes.append(f"Signature ({iw}x{ih} px) placed at {pos} on every page.")

    path = os.path.join(out, "filled_signed.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    notes = []
    if filled:
        notes.append(f"Filled {filled} field(s).")
    elif raw:
        notes.append("No form fields matched the given JSON — check the field names.")
    notes.extend(sig_notes or ["Processing complete."])
    return {"files": [{"name": "filled_signed.pdf", "path": path}], "notes": notes}


def _is_pdf(p):
    return os.path.splitext(p)[1].lower() == ".pdf"


def flatten_pdf(paths, opts, out):
    """Remove interactive widgets/links so the PDF becomes static."""
    from pypdf.generic import NameObject, DictionaryObject, ArrayObject
    reader = PdfReader(paths[0])
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            raise ToolError("This PDF is password-protected — unlock it first, then flatten.")
    writer = PdfWriter()
    try:
        writer.clone_document_from_reader(reader)
    except Exception:
        for page in reader.pages:
            writer.add_page(page)
    removed = 0
    for page in writer.pages:
        annots = page.get(NameObject("/Annots"))
        if not annots:
            continue
        try:
            arr = annots.get_object() if hasattr(annots, "get_object") else annots
        except Exception:
            continue
        kept = ArrayObject()
        for a in arr:
            try:
                obj = a.get_object() if hasattr(a, "get_object") else a
                sub = str(obj.get(NameObject("/Subtype"), ""))
            except Exception:
                sub = ""
            if sub in ("/Widget", "/Link", "/Btn", "/Tx", "/Ch"):
                removed += 1
                continue
            kept.append(a)
        if removed or len(kept) != len(arr):
            page[NameObject("/Annots")] = kept
    # drop the interactive form dictionary so viewers can't edit fields
    try:
        root = writer._root_object
        if NameObject("/AcroForm") in root:
            del root[NameObject("/AcroForm")]
    except Exception:
        pass
    path = os.path.join(out, "flattened.pdf")
    with open(path, "wb") as f:
        writer.write(f)
    return {"files": [{"name": "flattened.pdf", "path": path}],
            "notes": [f"Removed {removed} interactive widget(s) — the PDF is now static & print-ready."]}


def request_signatures(paths, opts, out):
    """Add sign-here boxes and a signing instruction sheet (offline e-sign prep)."""
    reader = PdfReader(paths[0])
    signer = str(opts.get("signer") or "").strip()
    message = str(opts.get("message") or "Please sign this document.").strip()
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import A4

    writer = PdfWriter()
    for page in reader.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        cbuf = io.BytesIO()
        c = rl_canvas.Canvas(cbuf, pagesize=(w, h))
        c.setDash(4, 3)
        c.setStrokeColorRGB(0.9, 0.2, 0.2)
        c.setLineWidth(1.2)
        bw, bh = w * 0.42, h * 0.10
        c.rect(w - bw - 30, 30, bw, bh, stroke=1, fill=0)
        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.9, 0.2, 0.2)
        c.drawString(w - bw - 30 + 6, 30 + bh + 6, "SIGN HERE")
        c.save()
        cbuf.seek(0)
        ov = PdfReader(cbuf).pages[0]
        page.merge_page(ov, over=True)
        writer.add_page(page)

    # instruction sheet appended as first page
    sheet = io.BytesIO()
    c = rl_canvas.Canvas(sheet, pagesize=A4)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(60, 760, "Signature request")
    c.setFont("Helvetica", 12)
    y = 720
    for line in ["This document was prepared for e-signature with PDFly.",
                 f"Document: {os.path.basename(paths[0])}",
                 f"Signer: {signer or '—'}",
                 "",
                 "Instructions:",
                 "1. Open the attached document and review every page.",
                 "2. Place your handwritten or typed signature in the SIGN HERE box "
                 "on each page (bottom-right).",
                 "3. Save/download a copy as your signed record.",
                 "",
                 f"Message from the sender: {message}"]:
        c.drawString(60, y, line)
        y -= 20
    c.save()
    sheet.seek(0)
    sp = PdfReader(sheet).pages[0]
    total_pages = len(writer.pages)
    final = PdfWriter()
    final.add_page(sp)
    for page in writer.pages:
        final.add_page(page)
    path = os.path.join(out, "signature_request.pdf")
    with open(path, "wb") as f:
        final.write(f)
    return {"files": [{"name": "signature_request.pdf", "path": path}],
            "notes": [f"Prepared {total_pages} page(s) for signing. "
                      "(This server signs locally — for legally binding remote e-signatures "
                      "use a service like Sign.com; this tool prepares the documents.)"]}
