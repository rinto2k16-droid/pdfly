"""Tool registry: single source of truth for the whole UI + API."""

CATEGORIES = ["All", "Organize PDF", "Optimize PDF", "Convert PDF", "Edit PDF",
              "PDF Security", "PDF Intelligence"]

# ---------------------------------------------------------------- icons (SVG)
def _svg(bg, inner):
    return ('<svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="2" y="2" width="44" height="44" rx="10" fill="{bg}"/>'
            f'{inner}</svg>')

G = {
    "merge":   _svg("#E5322D", '<path d="M14 18h10v6h8v-4l8 8-8 8v-4H14z" fill="#fff"/><rect x="6" y="12" width="6" height="6" rx="1" fill="#fff" opacity=".85"/>'),
    "split":   _svg("#E5322D", '<path d="M20 16h6l-3-4 9 8-9 8 3-4h-6v-4H8v-4h12z" fill="#fff"/><rect x="36" y="26" width="6" height="6" rx="1" fill="#fff" opacity=".85"/>'),
    "remove":  _svg("#E5322D", '<path d="M12 22h24v4H12z" fill="#fff"/><path d="M20 12h8l2 4h6v4H12v-4h6z" fill="#fff" opacity=".85"/>'),
    "extract": _svg("#E5322D", '<path d="M26 12v12H14v6h18v-6l8 8-8 8v-6H14v-4h18z" fill="#fff" opacity=".95"/><rect x="14" y="10" width="6" height="6" rx="1" fill="#fff" opacity=".8"/>'),
    "organize":_svg("#E5322D", '<path d="M14 14h12v6H14zM14 24h8v6h-8zM14 34h10v4H14z" fill="#fff"/><path d="M30 30l4-4 4 4-4-4v4z" fill="#fff" opacity=".7"/><circle cx="34" cy="36" r="3" fill="#fff"/>'),
    "scan":    _svg("#E5322D", '<rect x="12" y="14" width="24" height="20" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M18 22h12M18 27h12" stroke="#fff" stroke-width="2"/><path d="M16 10v4M24 10v4M32 10v4M16 34v4M24 34v4M32 34v4" stroke="#fff" stroke-width="2" opacity=".8"/>'),
    "compress":_svg("#57B560", '<path d="M20 14h8v8h-8z" fill="#fff"/><path d="M20 26h8v8h-8z" fill="#fff" opacity=".85"/><path d="M8 14h6v20H8zM34 14h6v20h-6z" fill="#fff" opacity=".7"/>'),
    "repair":  _svg("#57B560", '<path d="M30 12l6 6-14 14-8 4 4-8z" fill="#fff"/><path d="M12 34l6-6 2 6-4 4z" fill="#fff" opacity=".85"/>'),
    "ocr":     _svg("#57B560", '<rect x="12" y="16" width="24" height="20" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M17 28l3-4 3 4 3-6 3 6" fill="none" stroke="#fff" stroke-width="2"/><path d="M14 8h4M22 8h4M30 8h4" stroke="#fff" stroke-width="2" opacity=".8"/>'),
    "jpg":     _svg("#F5A623", '<rect x="8" y="12" width="26" height="26" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><circle cx="15" cy="19" r="3" fill="#fff"/><path d="M8 34l9-9 7 7 4-4 6 6z" fill="#fff"/><path d="M38 20v8M34 24h8" stroke="#fff" stroke-width="2"/><text x="30" y="16" font-size="10" fill="#fff" font-family="Arial" font-weight="bold">JPG</text>'),
    "word":    _svg("#437EE2", '<rect x="10" y="10" width="22" height="28" rx="2" fill="#fff"/><path d="M10 14c0-2.2 1.8-4 4-4h14c2.2 0 4 1.8 4 4v4H10z" fill="#437EE2"/><text x="13" y="34" font-size="13" fill="#437EE2" font-family="Arial" font-weight="bold">W</text><path d="M32 18l4-8 4 8" fill="none" stroke="#fff" stroke-width="2"/>'),
    "ppt":     _svg("#E8712C", '<rect x="10" y="10" width="22" height="28" rx="2" fill="#fff"/><path d="M10 14c0-2.2 1.8-4 4-4h14c2.2 0 4 1.8 4 4v4H10z" fill="#E8712C"/><text x="13" y="34" font-size="13" fill="#E8712C" font-family="Arial" font-weight="bold">P</text><rect x="32" y="22" width="6" height="6" rx="1" fill="#fff"/>'),
    "excel":   _svg("#2E9E5B", '<rect x="10" y="10" width="22" height="28" rx="2" fill="#fff"/><path d="M10 14c0-2.2 1.8-4 4-4h14c2.2 0 4 1.8 4 4v4H10z" fill="#2E9E5B"/><text x="13" y="34" font-size="13" fill="#2E9E5B" font-family="Arial" font-weight="bold">X</text><path d="M34 20l5 5-5 5" fill="none" stroke="#fff" stroke-width="2"/>'),
    "html":    _svg("#F5A623", '<path d="M14 14l-6 10 6 10M34 14l6 10-6 10M27 12l-6 24" fill="none" stroke="#fff" stroke-width="3"/>'),
    "rotate":  _svg("#E5322D", '<path d="M36 24a12 12 0 1 1-4-9" fill="none" stroke="#fff" stroke-width="3"/><path d="M36 8v8h-8" fill="none" stroke="#fff" stroke-width="3"/>'),
    "page_num":_svg("#E5322D", '<rect x="10" y="12" width="28" height="26" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="32" font-size="12" fill="#fff" font-family="Arial" text-anchor="middle">1</text><path d="M10 30h28" stroke="#fff" stroke-width="1.5" opacity=".6"/>'),
    "watermark":_svg("#E5322D", '<path d="M10 34c4-10 8-14 14-14s10 4 14 14" fill="none" stroke="#fff" stroke-width="2.5"/><circle cx="24" cy="20" r="5" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="15" font-size="8" fill="#fff" font-family="Arial" text-anchor="middle">W</text>'),
    "crop":    _svg("#E5322D", '<path d="M14 8v20a6 6 0 0 0 6 6h20" fill="none" stroke="#fff" stroke-width="3"/><path d="M8 14h20a6 6 0 0 1 6 6v20" fill="none" stroke="#fff" stroke-width="3" opacity=".55"/>'),
    "edit":    _svg("#8E44AD", '<rect x="10" y="12" width="20" height="26" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M30 18l6-6 4 4-6 6-4 1z" fill="#fff"/><path d="M15 24h8M15 29h8" stroke="#fff" stroke-width="2"/>'),
    "forms":   _svg("#8E44AD", '<rect x="10" y="10" width="28" height="30" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M15 18h18M15 24h18" stroke="#fff" stroke-width="2" opacity=".6"/><path d="M15 31h8v3h-8z" fill="#fff"/><path d="M28 29l4-4 2 2-4 4-2 0z" fill="#fff"/>'),
    "lock":    _svg("#437EE2", '<rect x="14" y="22" width="20" height="16" rx="3" fill="#fff"/><path d="M18 22v-5a6 6 0 0 1 12 0v5" fill="none" stroke="#fff" stroke-width="3"/><circle cx="24" cy="30" r="2.5" fill="#437EE2"/>'),
    "unlock":  _svg("#57B560", '<rect x="14" y="22" width="20" height="16" rx="3" fill="#fff"/><path d="M18 22v-5a6 6 0 0 1 11-4" fill="none" stroke="#fff" stroke-width="3"/><circle cx="24" cy="30" r="2.5" fill="#57B560"/>'),
    "sign":    _svg("#57B560", '<path d="M14 34c4 2 8-2 9-6l4-12 3 8c3-1 5-3 6-6" fill="none" stroke="#fff" stroke-width="3"/><path d="M14 34c8 0 12-6 14-12" fill="none" stroke="#fff" stroke-width="2" opacity=".6"/>'),
    "redact":  _svg("#E5322D", '<rect x="12" y="10" width="24" height="28" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><rect x="16" y="16" width="16" height="3.5" fill="#fff"/><rect x="16" y="23" width="16" height="3.5" fill="#fff" opacity=".6"/><rect x="16" y="30" width="10" height="3.5" fill="#fff"/>'),
    "compare": _svg("#437EE2", '<path d="M10 12h11v24H10zM27 12h11v24H27z" fill="#fff" opacity=".9"/><path d="M10 20h11M10 26h11M27 20h11M27 26h11" stroke="#437EE2" stroke-width="1.5"/><path d="M21 24h6v4h-6z" fill="#437EE2"/>'),
    "sum":     _svg("#8E44AD", '<path d="M14 16h20M14 24h20M14 32h12" stroke="#fff" stroke-width="3"/><path d="M30 30l4-4 4 4-4-4z" fill="#fff"/>'),
    "trans":   _svg("#8E44AD", '<path d="M12 22h18M22 14l8 8-8 8" fill="none" stroke="#fff" stroke-width="3"/><path d="M36 26H18M26 18l-8 8 8 8" fill="none" stroke="#fff" stroke-width="2" opacity=".5"/>'),
    "md":      _svg("#2E9E5B", '<rect x="10" y="10" width="28" height="28" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="31" font-size="11" fill="#fff" font-family="Arial" text-anchor="middle" font-weight="bold">M↓</text>'),
    "pdfa":    _svg("#437EE2", '<rect x="10" y="10" width="28" height="28" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="31" font-size="11" fill="#fff" font-family="Arial" text-anchor="middle" font-weight="bold">A</text><path d="M34 6l2 2 4-4" fill="none" stroke="#fff" stroke-width="2"/>'),
    "pages":   _svg("#F5A623", '<rect x="12" y="8" width="24" height="32" rx="3" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M12 12a4 4 0 0 1 4-4h12a4 4 0 0 1 4 4v4H12z" fill="#fff" opacity=".9"/><text x="24" y="32" font-size="13" fill="#F5A623" font-family="Arial" text-anchor="middle" font-weight="bold">Pg</text>'),
    "hwp":     _svg("#437EE2", '<rect x="10" y="10" width="28" height="28" rx="3" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="31" font-size="14" fill="#fff" font-family="Arial" text-anchor="middle" font-weight="bold">H</text><path d="M14 16h20M14 36h20" stroke="#fff" stroke-width="1.5" opacity=".6"/>'),
    "assist":  _svg("#8E44AD", '<path d="M24 8l3.2 8.6L36 20l-8.8 3.4L24 32l-3.2-8.6L12 20l8.8-3.4z" fill="#fff"/><path d="M36 30l1.6 4.4L42 36l-4.4 1.6L36 42l-1.6-4.4L30 36l4.4-1.6z" fill="#fff" opacity=".8"/>'),
    "fillsign":_svg("#57B560", '<rect x="10" y="10" width="28" height="24" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M15 20h18M15 26h10" stroke="#fff" stroke-width="2" opacity=".7"/><path d="M18 38c4 1 7-3 8-7l2-5 3 4c2-1 4-2 5-4" fill="none" stroke="#fff" stroke-width="2.2"/>'),
    "txt":     _svg("#437EE2", '<rect x="10" y="10" width="28" height="28" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="30" font-size="13" fill="#fff" font-family="Arial" text-anchor="middle" font-weight="bold">T</text><path d="M15 17h18" stroke="#fff" stroke-width="1.5" opacity=".6"/>'),
    "rtf":     _svg("#8E44AD", '<rect x="10" y="10" width="28" height="28" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><text x="24" y="30" font-size="11" fill="#fff" font-family="Arial" text-anchor="middle" font-weight="bold">R</text>'),
    "epub":    _svg("#2E9E5B", '<path d="M24 14c-4-3-9-4-13-4v26c4 0 9 1 13 4 4-3 9-4 13-4V10c-4 0-9 1-13 4z" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M24 14v26" stroke="#fff" stroke-width="1.5" opacity=".7"/>'),
    "csv":     _svg("#2E9E5B", '<path d="M14 14l20 20M34 14L14 34" stroke="#fff" stroke-width="3.5"/><rect x="9" y="9" width="30" height="30" rx="4" fill="none" stroke="#fff" stroke-width="2"/>'),
    "reader":  _svg("#8E44AD", '<path d="M12 14c4-1 8 0 11 2v20c-3-2-7-3-11-2z" fill="#fff" opacity=".9"/><path d="M36 14c-4-1-8 0-11 2v20c3-2 7-3 11-2z" fill="#fff" opacity=".6"/><circle cx="24" cy="22" r="4" fill="none" stroke="#8E44AD" stroke-width="2"/>'),
    "annotate":_svg("#E8712C", '<path d="M12 34l2-7 14-14 6 6-14 14z" fill="#fff"/><path d="M28 13l6 6 4-4-6-6z" fill="#fff" opacity=".8"/><path d="M10 38h20" stroke="#fff" stroke-width="2"/>'),
    "flatten": _svg("#E5322D", '<path d="M24 8l14 7-14 7-14-7z" fill="#fff"/><path d="M10 24l14 7 14-7" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M10 31l14 7 14-7" fill="none" stroke="#fff" stroke-width="2" opacity=".5"/>'),
    "reqsign": _svg("#57B560", '<rect x="12" y="10" width="24" height="28" rx="2" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M16 22h16M16 28h10" stroke="#fff" stroke-width="2"/><path d="M18 36c3 1 5-1 6-4l2-4 2 3c2-1 3-2 4-4" fill="none" stroke="#fff" stroke-width="2"/>'),
    "chat":    _svg("#8E44AD", '<path d="M10 12h28v20H22l-8 7v-7h-4z" fill="none" stroke="#fff" stroke-width="2.5"/><circle cx="17" cy="22" r="2" fill="#fff"/><circle cx="24" cy="22" r="2" fill="#fff"/><circle cx="31" cy="22" r="2" fill="#fff"/>'),
    "qgen":    _svg("#437EE2", '<text x="24" y="31" font-size="17" fill="#fff" font-family="Arial" text-anchor="middle" font-weight="bold">?</text><path d="M14 12h20" stroke="#fff" stroke-width="2" opacity=".6"/><path d="M14 36h20" stroke="#fff" stroke-width="2" opacity=".6"/>'),
    "share":   _svg("#57B560", '<circle cx="18" cy="24" r="5" fill="#fff"/><circle cx="32" cy="12" r="4.5" fill="#fff" opacity=".85"/><circle cx="32" cy="36" r="4.5" fill="#fff" opacity=".85"/><path d="M22 22l7-7M22 26l7 7" stroke="#fff" stroke-width="2.5"/>'),
    "zip":     _svg("#F5A623", '<rect x="8" y="10" width="32" height="28" rx="4" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M18 16h4M18 22h4" stroke="#fff" stroke-width="2"/><path d="M18 28l4.5 4.5L27 28l-4.5-2z" fill="#fff"/><rect x="16" y="30" width="16" height="4" rx="1" fill="#fff" opacity=".85"/>'),
    "scancam": _svg("#E5322D", '<rect x="6" y="12" width="36" height="26" rx="4" fill="none" stroke="#fff" stroke-width="2.5"/><circle cx="24" cy="25" r="7" fill="none" stroke="#fff" stroke-width="2.5"/><path d="M31 12l-3-4h-8l-3 4" fill="#fff"/><circle cx="24" cy="25" r="2.5" fill="#fff"/>'),
}

# ------------------------------------------------------------------- options
def radio(id_, label, choices, default=None, hint=""):
    return {"type": "radio", "id": id_, "label": label, "choices": choices,
            "default": default, "hint": hint}

def select(id_, label, choices, default=None, hint=""):
    return {"type": "select", "id": id_, "label": label, "choices": choices,
            "default": default, "hint": hint}

def text(id_, label, placeholder="", default="", hint=""):
    return {"type": "text", "id": id_, "label": label, "placeholder": placeholder,
            "default": default, "hint": hint}

def password(id_, label, placeholder="", hint=""):
    return {"type": "password", "id": id_, "label": label, "placeholder": placeholder, "hint": hint}

def pages(id_, label, placeholder="e.g. 2,4-6", hint="1-based page numbers. e.g. 2,4-6"):
    return {"type": "pages", "id": id_, "label": label, "placeholder": placeholder, "hint": hint}

def number(id_, label, minv=0, maxv=100, default=50, suffix="", hint=""):
    return {"type": "number", "id": id_, "label": label, "min": minv, "max": maxv,
            "default": default, "suffix": suffix, "hint": hint}

def check(id_, label, default=False, hint=""):
    return {"type": "check", "id": id_, "label": label, "default": default, "hint": hint}

# ------------------------------------------------------------------- tools
T = {}

def tool(tid, title, short, tagline, category, icon, accept, **kw):
    kw.setdefault("options", [])
    kw.setdefault("multiple", False)
    kw.setdefault("min_files", 1)
    kw.setdefault("max_files", 1)
    T[tid] = dict(id=tid, title=title, short=short, tagline=tagline,
                  category=category, icon=icon, accept=accept, **kw)

# ---- Organize PDF
tool("merge_pdf", "Merge PDF", "Merge PDF files",
     "Combine PDFs in the order you want with the easiest PDF merger available.",
     "Organize PDF", "merge", ".pdf", multiple=True, max_files=200,
     min_files=2, hint="Drag the files to reorder them. The pages of the top file come first.")

tool("split_pdf", "Split PDF", "Split PDF files",
     "Separate one page or a whole set into independent PDF files.",
     "Organize PDF", "split", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[
         radio("mode", "How do you want to split?", [
             ("every", "Extract every page (each page becomes a PDF)"),
             ("ranges", "Split by ranges", "e.g. 1-3, 4, 7-9"),
             ("size", "Split every X pages"),
         ], "every"),
         pages("ranges", "Pages / ranges", hint="e.g. 1-3, 4, 7-9 → each group becomes a file"),
         number("chunk", "Pages per file", 1, 200, 5, " pages"),
     ])

tool("remove_pages", "Delete PDF pages", "Delete pages from PDF",
     "Delete selected pages from your PDF and save the rest as a new file.",
     "Organize PDF", "remove", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[pages("pages", "Pages to remove", hint="These pages will be deleted. e.g. 2,4-6"),
              check("invert", "Keep only these pages (inverse selection)", False)])

tool("extract_pages", "Extract pages", "Extract pages from PDF",
     "Pull the pages you need out of a PDF and save them as a new file.",
     "Organize PDF", "extract", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[pages("pages", "Pages to extract", hint="e.g. 1,3,5-8")])

tool("organize_pdf", "Organize PDF", "Reorder pages in PDF",
     "Rearrange the page order of your PDF — or reverse it completely.",
     "Organize PDF", "organize", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[
         text("order", "New page order (1-based, comma separated)",
              "e.g. 3,1,2 or reverse", "", "Leave empty to keep the order."),
         check("reverse", "Reverse the whole document", False),
     ])

tool("rotate_pdf", "Rotate PDF", "Rotate PDF pages",
     "Rotate all pages of your PDF by 90, 180 or 270 degrees.",
     "Organize PDF", "rotate", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[radio("angle", "Rotation angle", [("90", "90° clockwise"),
                                               ("180", "180°"),
                                               ("270", "270° clockwise")], "90")])

# ---- Optimize PDF
tool("compress_pdf", "Compress PDF", "Compress PDF files",
     "Reduce file size while optimizing for maximal PDF quality.",
     "Optimize PDF", "compress", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[radio("level", "Compression level", [
         ("low", "Low compression — best quality"),
         ("medium", "Recommended compression — good quality"),
         ("high", "Extreme compression — smaller file"),
     ], "medium")])

tool("repair_pdf", "Repair PDF", "Repair damaged PDF files",
     "Fix structurally damaged or corrupted PDF files and recover content.",
     "Optimize PDF", "repair", ".pdf", multiple=False, max_files=1, min_files=1)

tool("ocr_pdf", "OCR PDF", "OCR — make scanned PDFs searchable",
     "Recognize text in scanned documents and export it as text or Word.",
     "Optimize PDF", "ocr", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[select("lang", "OCR language", [("eng", "English"), ("ben", "Bengali")], "eng"),
              select("out", "Output format", [("txt", "Plain text (.txt)"), ("docx", "Word document (.docx)"),
                                              ("both", "Both")], "both")])

# ---- Convert PDF
tool("jpg_to_pdf", "JPG to PDF", "Convert images to PDF",
     "Convert JPG, PNG & other images into PDF files instantly.",
     "Convert PDF", "jpg", ".png,.jpg,.jpeg,.webp,.bmp,.gif,.tiff", multiple=True, max_files=200, min_files=1,
     options=[radio("mode", "PDF layout", [("single", "All images in one PDF"),
                                           ("each", "One PDF per image (ZIP)")], "single"),
              select("pagesize", "Page size", [("fit", "Fit image to page size"),
                                               ("a4", "A4 portrait (auto-rotate)"),
                                               ("auto", "Same size as image")], "fit"),
              number("margin", "Page margin (mm)", 0, 40, 0, " mm")])

tool("word_to_pdf", "Word to PDF", "Convert Word to PDF",
     "Make DOC and DOCX files easy to read by converting them to PDF.",
     "Convert PDF", "word", ".docx,.doc", multiple=False, max_files=1, min_files=1)

tool("pptx_to_pdf", "PowerPoint to PDF", "Convert PowerPoint to PDF",
     "Make PPT and PPTX slideshows easy to view by converting them to PDF.",
     "Convert PDF", "ppt", ".pptx,.ppt", multiple=False, max_files=1, min_files=1)

tool("excel_to_pdf", "Excel to PDF", "Convert Excel to PDF",
     "Make EXCEL spreadsheets easy to read by converting them to PDF.",
     "Convert PDF", "excel", ".xlsx,.xlsm,.csv", multiple=False, max_files=1, min_files=1)

tool("html_to_pdf", "HTML to PDF", "Convert HTML to PDF",
     "Turn any HTML file into a printable PDF document.",
     "Convert PDF", "html", ".html,.htm", multiple=False, max_files=1, min_files=1)

tool("txt_to_pdf", "TXT to PDF", "Convert TXT to PDF",
     "Turn plain text files into a clean, readable PDF document.",
     "Convert PDF", "txt", ".txt", multiple=False, max_files=1, min_files=1)

tool("rtf_to_pdf", "RTF to PDF", "Convert RTF to PDF",
     "Convert legacy rich text documents into modern PDF files.",
     "Convert PDF", "rtf", ".rtf", multiple=False, max_files=1, min_files=1)

tool("epub_to_pdf", "EPUB to PDF", "Convert EPUB to PDF",
     "Turn any ebook into a print-ready PDF with headings and chapters.",
     "Convert PDF", "epub", ".epub", multiple=False, max_files=1, min_files=1)

tool("zip_to_pdf", "ZIP to PDF", "Convert ZIP to PDF",
     "Merge every PDF inside a ZIP archive into a single PDF file.",
     "Convert PDF", "zip", ".zip", multiple=False, max_files=1, min_files=1,
     options=[check("all", "Merge all PDFs found inside (recommended)", True)])

tool("csv_to_pdf", "CSV to PDF", "Convert CSV to PDF",
     "Convert any CSV table into a tidy, printable PDF spreadsheet.",
     "Convert PDF", "csv", ".csv", multiple=False, max_files=1, min_files=1)

tool("pages_to_pdf", "Pages to PDF", "Convert Apple Pages to PDF",
     "Turn Apple Pages documents into a printable PDF file.",
     "Convert PDF", "pages", ".pages", multiple=False, max_files=1, min_files=1,
     note="Apple Pages files normally embed a PDF preview — PDFly extracts it.")

tool("hwp_to_pdf", "HWP to PDF", "Convert HWP/HWPX to PDF",
     "Convert Korean Hangul Word Processor documents (.hwpx) into PDF.",
     "Convert PDF", "hwp", ".hwpx,.hwp", multiple=False, max_files=1, min_files=1,
     note="Modern .hwpx files are supported. For legacy .hwp files, please re-save as .hwpx.")

tool("fill_sign_pdf", "Fill & Sign PDF", "Fill & Sign PDF",
     "Fill form fields and stamp your signature image in one click.",
     "PDF Security", "fillsign", ".pdf,.png,.jpg,.jpeg,.webp", multiple=True, max_files=2, min_files=1,
     options=[text("fields", "Field values (JSON)", 'e.g. {"name": "Rahim"}', "", "Optional — paste field values as JSON."),
              select("pos", "Signature position", [("br", "Bottom right"), ("bl", "Bottom left"),
                                                   ("tr", "Top right"), ("tl", "Top left"),
                                                   ("center", "Center")], "br"),
              number("scale", "Signature width (% of page)", 5, 80, 25, " %")])

tool("odt_to_pdf", "ODT to PDF", "Convert OpenOffice text to PDF",
     "Convert OpenOffice Writer documents (.odt) into PDF.",
     "Convert PDF", "word", ".odt", multiple=False, max_files=1, min_files=1)

tool("ods_to_pdf", "ODS to PDF", "Convert OpenOffice sheets to PDF",
     "Convert OpenOffice Calc spreadsheets (.ods) into PDF.",
     "Convert PDF", "excel", ".ods", multiple=False, max_files=1, min_files=1)

tool("odp_to_pdf", "ODP to PDF", "Convert OpenOffice slides to PDF",
     "Convert OpenOffice Impress presentations (.odp) into PDF.",
     "Convert PDF", "ppt", ".odp", multiple=False, max_files=1, min_files=1)

tool("scan_to_pdf", "Scan to PDF", "Scan photos / camera to PDF",
     "Turn photos and camera captures into a searchable PDF document.",
     "Organize PDF", "scan", ".png,.jpg,.jpeg,.webp,.bmp,.gif,.tiff", multiple=True, max_files=200, min_files=1,
     options=[radio("mode", "PDF layout", [("single", "All images in one PDF"),
                                           ("each", "One PDF per image (ZIP)")], "single")])

tool("pdf_to_jpg", "PDF to JPG", "Convert PDF to images",
     "Convert each PDF page into a JPG or extract all images in seconds.",
     "Convert PDF", "jpg", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[select("dpi", "Resolution", [("72", "72 DPI (screen)"), ("150", "150 DPI (web)"),
                                           ("300", "300 DPI (print)")], "150")])

tool("pdf_to_word", "PDF to Word", "Convert PDF to Word",
     "Easily convert your PDF files into easy to edit DOC and DOCX documents.",
     "Convert PDF", "word", ".pdf", multiple=False, max_files=1, min_files=1)

tool("pdf_to_pptx", "PDF to PowerPoint", "Convert PDF to PowerPoint",
     "Turn your PDF files into easy to edit PPT and PPTX slideshows.",
     "Convert PDF", "ppt", ".pdf", multiple=False, max_files=1, min_files=1)

tool("pdf_to_excel", "PDF to Excel", "Convert PDF to Excel",
     "Pull data straight from PDFs into Excel spreadsheets in a few short seconds.",
     "Convert PDF", "excel", ".pdf", multiple=False, max_files=1, min_files=1)

tool("pdf_to_txt", "PDF to TXT", "Extract text from PDF",
     "Extract all the text from your PDF into a plain .txt file.",
     "Convert PDF", "txt", ".pdf", multiple=False, max_files=1, min_files=1)

tool("pdf_to_html", "PDF to HTML", "Convert PDF to HTML",
     "Turn your PDF into a clean, self-contained HTML page.",
     "Convert PDF", "html", ".pdf", multiple=False, max_files=1, min_files=1)

tool("pdf_to_pdfa", "PDF to PDF/A", "Convert PDF to PDF/A",
     "Convert your PDF into an archival PDF/A file for long-term storage.",
     "Convert PDF", "pdfa", ".pdf", multiple=False, max_files=1, min_files=1)

# ---- Edit PDF
tool("page_numbers", "Add page numbers", "Add page numbers to PDF",
     "Stamp automatic page numbers onto every page of your document.",
     "Edit PDF", "page_num", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[select("format", "Number format", [
                    ("n", "1, 2, 3 …"), ("pagen", "Page 1"), ("nm", "1 / 10"),
                    ("nofm", "Page 1 of 10")], "n"),
              select("pos", "Position", [("bc", "Bottom center"), ("br", "Bottom right"),
                                         ("bl", "Bottom left"), ("tc", "Top center"),
                                         ("tr", "Top right")], "bc"),
              number("size", "Font size (pt)", 6, 48, 12, " pt"),
              text("prefix", "Prefix (optional)", "e.g. CONFIDENTIAL — ", "")])

tool("watermark_pdf", "Watermark PDF", "Watermark a PDF",
     "Stamp text over every page of your PDF — perfect for drafts & DRAFT copies.",
     "Edit PDF", "watermark", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[text("text", "Watermark text", "CONFIDENTIAL", "CONFIDENTIAL"),
              number("opacity", "Opacity (%)", 5, 100, 20, " %"),
              number("size", "Font size (pt)", 10, 300, 70, " pt"),
              check("tile", "Tile the watermark across the page", True),
              check("diag", "Rotate diagonally (45°)", True)])

tool("crop_pdf", "Crop PDF", "Crop PDF pages",
     "Trim the margins of every page of your PDF by a percentage.",
     "Edit PDF", "crop", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[number("top", "Cut from top (%)", 0, 45, 0, " %"),
              number("right", "Cut from right (%)", 0, 45, 0, " %"),
              number("bottom", "Cut from bottom (%)", 0, 45, 0, " %"),
              number("left", "Cut from left (%)", 0, 45, 0, " %")])

tool("edit_pdf", "Edit PDF", "Edit PDF — add text & annotations",
     "Add text notes, titles and annotations on top of your PDF pages.",
     "Edit PDF", "edit", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[text("text", "Text to add", "Type something…", ""),
              select("pos", "Position", [("top", "Top of every page"), ("center", "Center"),
                                         ("bottom", "Bottom of every page"), ("first", "Top of first page only")], "top"),
              number("size", "Font size (pt)", 6, 100, 18, " pt"),
              select("color", "Color", [("#E5322D", "Red"), ("#000000", "Black"), ("#437EE2", "Blue"),
                                        ("#2E9E5B", "Green"), ("#8E44AD", "Purple")], "#000000")])

tool("pdf_forms", "PDF Form Filler", "Fill PDF forms",
     "Fill the fields of an interactive PDF form and download the filled copy.",
     "Edit PDF", "forms", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[text("fields", "Field values (JSON)", 'e.g. {"name": "Rahim", "email": "r@mail.com"}',
                   "", "The browser shows the detected fields after upload — paste them here as JSON, or type directly.")])

tool("pdf_reader", "PDF Reader", "Read PDF online",
     "Open, read and navigate your PDF right in the browser — no download needed.",
     "Edit PDF", "reader", ".pdf", multiple=False, max_files=1, min_files=1)

tool("annotator_pdf", "PDF Annotator", "Annotate PDF",
     "Click anywhere on a page to drop text notes, then download the annotated copy.",
     "Edit PDF", "annotate", ".pdf", multiple=False, max_files=1, min_files=1,
     note="Click on the page preview to place your note.",
     options=[text("text", "Note text", "Type a comment…", ""),
              number("size", "Font size (pt)", 8, 72, 14, " pt"),
              select("color", "Color", [("#E5322D", "Red"), ("#000000", "Black"),
                                        ("#437EE2", "Blue"), ("#2E9E5B", "Green"),
                                        ("#8E44AD", "Purple")], "#E5322D")])

tool("flatten_pdf", "Flatten PDF", "Flatten a PDF",
     "Remove interactive form fields and links so the PDF becomes a static, print-ready file.",
     "PDF Security", "flatten", ".pdf", multiple=False, max_files=1, min_files=1)

tool("request_signatures", "Request Signatures", "Request signatures",
     "Prepare your PDF for e-signing: sign-here boxes are placed on every page and a signing sheet is generated.",
     "PDF Security", "reqsign", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[text("signer", "Signer name (optional)", "e.g. Rahim Uddin", ""),
              text("message", "Message to the signer (optional)", "Please sign this document.", "Confirm that you reviewed these documents.")])

# ---- PDF Security
tool("protect_pdf", "Protect PDF", "Protect PDF with password",
     "Encrypt your PDF with a password and keep sensitive data safe.",
     "PDF Security", "lock", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[password("password", "Password", "Enter a password…"),
              password("password2", "Repeat password", "Repeat the password…")])

tool("unlock_pdf", "Unlock PDF", "Unlock PDF files",
     "Remove a known password from a PDF and get a clean, unlocked copy.",
     "PDF Security", "unlock", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[password("password", "Document password", "Enter the current password…")])

tool("sign_pdf", "Sign PDF", "Sign PDF documents",
     "Place your handwritten signature image onto any PDF page.",
     "PDF Security", "sign", ".pdf,.png,.jpg,.jpeg,.webp", multiple=True, max_files=2, min_files=1,
     options=[select("pos", "Signature position", [("br", "Bottom right"), ("bl", "Bottom left"),
                                                   ("tr", "Top right"), ("tl", "Top left"),
                                                   ("center", "Center")], "br"),
              number("scale", "Signature width (% of page)", 5, 80, 25, " %")])

tool("redact_pdf", "Redact PDF", "Redact PDF content",
     "Permanently remove content from selected pages — the text layer is destroyed.",
     "PDF Security", "redact", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[pages("pages", "Pages to redact", hint="e.g. 2,4-6"),
              radio("mode", "Redaction type", [
                  ("black", "Paint the page solid black"),
                  ("raster", "Remove the text layer only (keep the visual look)"),
              ], "black")])

tool("compare_pdf", "Compare PDF", "Compare PDF documents",
     "Compare two PDF files and see exactly what changed.",
     "PDF Security", "compare", ".pdf", multiple=True, max_files=2, min_files=2,
     options=[check("ignore_space", "Ignore whitespace differences", True)])

# ---- PDF Intelligence
tool("ai_summarize", "AI Summarizer", "Summarize PDF with AI",
     "Get a quick, readable summary and the key points of any PDF.",
     "PDF Intelligence", "sum", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[radio("length", "Summary length", [("short", "Short (3 sentences)"),
                                                 ("medium", "Medium (5 sentences)"),
                                                 ("long", "Long (8 sentences)")], "medium")])

tool("translate_pdf", "Translate PDF", "Translate PDF documents",
     "Translate the whole text of a PDF into 15+ languages with one click.",
     "PDF Intelligence", "trans", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[select("lang", "Translate to", [
                    ("en", "English"), ("bn", "Bengali (বাংলা)"), ("hi", "Hindi"),
                    ("es", "Spanish"), ("fr", "French"), ("de", "German"),
                    ("it", "Italian"), ("pt", "Portuguese"), ("ru", "Russian"),
                    ("ar", "Arabic"), ("ja", "Japanese"), ("ko", "Korean"),
                    ("zh-CN", "Chinese (Simplified)"), ("tr", "Turkish"),
                    ("id", "Indonesian"), ("vi", "Vietnamese"), ("th", "Thai")], "bn")])

tool("pdf_to_markdown", "PDF to Markdown", "Convert PDF to Markdown",
     "Turn any PDF into clean, editable Markdown text with headings & lists.",
     "PDF Intelligence", "md", ".pdf", multiple=False, max_files=1, min_files=1)

tool("ai_assistant", "AI PDF Assistant", "AI PDF Assistant",
     "Your all-in-one AI helper: summary, key points and auto-generated Q&A from any PDF.",
     "PDF Intelligence", "assist", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[radio("length", "Summary length", [("short", "Short (3 sentences)"),
                                                 ("medium", "Medium (5 sentences)"),
                                                 ("long", "Long (8 sentences)")], "medium")])

tool("chat_pdf", "Chat with PDF", "Ask questions to your PDF",
     "Type a question and get the exact sentences from your PDF that answer it.",
     "PDF Intelligence", "chat", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[text("question", "Your question", "What is the main result of the study?", ""),
              number("answers", "Number of answers", 1, 8, 3, "")])

tool("ai_questions", "AI Question Generator", "Generate questions from PDF",
     "Turn any document into a study quiz: fill-in-the-blank questions from the key content.",
     "PDF Intelligence", "qgen", ".pdf", multiple=False, max_files=1, min_files=1,
     options=[number("count", "Number of questions", 1, 20, 8, ""),
              number("maxlen", "Max sentence length (words)", 8, 40, 22, "")])

tool("pdf_scanner", "PDF Scanner", "Scan camera photos to PDF",
     "Use your phone or webcam to scan paper documents straight into PDF.",
     "Organize PDF", "scancam", ".png,.jpg,.jpeg", multiple=True, max_files=200, min_files=1,
     note="In the browser: allow camera access and press Capture. Select 'Upload' if you prefer files.")

# ------------------------------------------------------------------- order
HOME_ORDER = ["merge_pdf", "split_pdf", "compress_pdf", "pdf_to_word", "pdf_to_pptx",
              "pdf_to_excel", "pdf_to_txt", "pdf_to_html",
              "word_to_pdf", "pptx_to_pdf", "excel_to_pdf",
              "edit_pdf", "pdf_to_jpg", "jpg_to_pdf", "rotate_pdf", "page_numbers",
              "watermark_pdf", "crop_pdf", "protect_pdf", "unlock_pdf", "sign_pdf",
              "redact_pdf", "compare_pdf", "remove_pages", "extract_pages",
              "organize_pdf", "scan_to_pdf", "pdf_scanner", "repair_pdf", "ocr_pdf",
              "html_to_pdf", "txt_to_pdf", "rtf_to_pdf", "epub_to_pdf",
              "zip_to_pdf", "csv_to_pdf", "pages_to_pdf", "hwp_to_pdf",
              "odt_to_pdf", "ods_to_pdf", "odp_to_pdf", "pdf_to_pdfa",
              "pdf_forms", "pdf_reader", "annotator_pdf", "flatten_pdf",
              "request_signatures", "fill_sign_pdf",
              "translate_pdf", "ai_summarize", "ai_assistant", "chat_pdf",
              "ai_questions", "pdf_to_markdown"]

def grouped():
    by_cat = {}
    for tid in HOME_ORDER:
        t = T[tid]
        by_cat.setdefault(t["category"], []).append(t)
    return by_cat

def all_tools():
    return [T[tid] for tid in HOME_ORDER if tid in T]
