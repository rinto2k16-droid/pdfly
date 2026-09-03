"""PDF Intelligence: AI summarizer, translation, markdown conversion.

All tools run fully offline — the 'AI' summary uses an extractive algorithm that
works on any PDF without an API key or internet connection.
"""
import os, re, json, collections

from .errors import ToolError


def _clean_text(raw):
    lines = [l.strip() for l in raw.splitlines()]
    text = " ".join(l for l in lines if l)
    text = re.sub(r"\s+", " ", text)
    return text


def read_pdf_text(path, max_chars=60000):
    from .pdf_ops import extract_text_pages
    texts, total = extract_text_pages(path, max_pages=None)
    blob = []
    used = 0
    for i, t in enumerate(texts, 1):
        if used > max_chars:
            break
        blob.append(f"[Page {i}]\n{t}")
        used += len(t)
    return "\n\n".join(blob), total


# ---------------------------------------------------------------- summarize
_STOPWORDS = set("""a an the and or but if then else for while of to in on at by with from as is are was were be been being
it its this that these those he she they them his her their we you your our i me my not no so very can will would could should
do does did done have has had having about into over under again more most other some such only own same than too s t just
don now am also there here when where why how all any both each few nor own what which who whom whose""".split())

_PRIORITY = re.compile(r"^(abstract|introduction|summary|conclusion|executive|overview|result|finding|key|highlight|recommend|method|background|purpose|objective)", re.I)


def _score_sentences(sents):
    freq = collections.Counter()
    for s in sents:
        for w in re.findall(r"[A-Za-z\u0980-\u09FF]{3,}", s.lower()):
            if w not in _STOPWORDS:
                freq[w] += 1
    ranked = []
    for idx, s in enumerate(sents):
        words = re.findall(r"[A-Za-z\u0980-\u09FF]{3,}", s.lower())
        if not words:
            continue
        score = sum(freq.get(w, 0) for w in words) / len(words)
        # boost: shorter sentences, first sentences of the doc, priority headers
        if len(s) < 140:
            score *= 1.25
        if idx == 0:
            score *= 2.0
        if _PRIORITY.search(s[:40]):
            score *= 1.3
        ranked.append((score, idx, s))
    return ranked


def summarize_pdf(paths, opts, out):
    blob, total = read_pdf_text(paths[0])
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", blob) if len(s.strip()) > 25]
    if not sents:
        raise ToolError("No text could be extracted from this PDF — it is probably a scanned "
                        "image PDF. Run OCR first, then summarize.")
    length = opts.get("length", "medium")
    n = {"short": 3, "medium": 5, "long": 8}[length]
    ranked = _score_sentences(sents)
    picked = sorted([r for r in ranked[: max(n * 3, 15)]], key=lambda r: r[1])[:n]
    picked = sorted(picked, key=lambda r: r[1])
    summary = "\n".join(f"• {s}" for _, _, s in picked)
    # key points: top-scoring remaining sentences
    kp = [s for _, _, s in sorted(ranked, reverse=True)[: n + 2] if s not in [x[2] for x in picked]]
    key_points = "\n".join(f"– {s}" for s in kp[:4])

    report = os.path.join(out, "summary.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write("AI SUMMARY\n==========\n")
        f.write(f"Source: {os.path.basename(paths[0])} — {total} pages, length: {length.upper()}\n\n")
        f.write("KEY IDEAS\n---------\n" + summary + "\n\n")
        f.write("KEY POINTS\n----------\n" + (key_points or "—") + "\n\n")
        f.write("NOTE: extractive summarizer (no external AI API). "
                "Best results on text-based PDFs.\n")
    txt_path = os.path.join(out, "summary.txt")
    return {"files": [{"name": "summary.txt", "path": txt_path}],
            "notes": [f"Summarized {total} page(s) → {n} key sentences."]}


# ---------------------------------------------------------------- assistant (summary + Q&A)
def ai_assistant(paths, opts, out):
    """Smallpdf-style AI PDF Assistant: one report with summary, key points
       and automatically generated questions with answers."""
    blob, total = read_pdf_text(paths[0])
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", blob) if len(s.strip()) > 25]
    if not sents:
        raise ToolError("No text could be extracted — this is probably a scanned PDF. Run OCR first.")

    length = opts.get("length", "medium")
    n = {"short": 3, "medium": 5, "long": 8}[length]
    ranked = _score_sentences(sents)
    picked = sorted([r for r in ranked[: max(n * 3, 15)]], key=lambda r: r[1])[:n]
    picked = sorted(picked, key=lambda r: r[1])
    summary = "\n".join(f"• {s}" for _, _, s in picked)
    kp = [s for _, _, s in sorted(ranked, reverse=True)[: n + 2] if s not in [x[2] for x in picked]]
    key_points = "\n".join(f"– {s}" for s in kp[:4])

    # auto Q&A: ask about top keywords
    qs = []
    used = set()
    for _, _, s in sorted(ranked, reverse=True):
        words = re.findall(r"[A-Za-z\u0980-\u09FF]{4,}", s.lower())
        w = next((x for x in words if x not in _STOPWORDS and x not in used), None)
        if not w:
            continue
        used.add(w)
        qs.append((f"What does this document say about '{w}'?", s))
        if len(qs) >= 5:
            break
    qa = "\n".join(f"Q{i}. {q}\nA: {a}" for i, (q, a) in enumerate(qs, 1))

    report_txt = os.path.join(out, "assistant_report.txt")
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("AI PDF ASSISTANT REPORT\n=======================\n")
        f.write(f"Source: {os.path.basename(paths[0])} — {total} page(s)\n\n")
        f.write("SUMMARY\n-------\n" + summary + "\n\n")
        f.write("KEY POINTS\n----------\n" + (key_points or "—") + "\n\n")
        f.write("AUTO Q&A\n-------\n" + (qa or "—") + "\n")
    dpath = os.path.join(out, "assistant_report.docx")
    from docx import Document
    d = Document()
    d.add_heading("AI PDF Assistant Report", 0)
    d.add_paragraph(f"Source: {os.path.basename(paths[0])} — {total} pages")
    d.add_heading("Summary", 1)
    for _, _, s in picked:
        d.add_paragraph(s, style="List Bullet")
    d.add_heading("Key points", 1)
    for s in kp[:4]:
        d.add_paragraph(s, style="List Bullet")
    d.add_heading("Auto Q & A", 1)
    for q, a in qs:
        d.add_paragraph(q, style="List Bullet")
        d.add_paragraph(a)
    d.save(dpath)
    return {"files": [{"name": "assistant_report.txt", "path": report_txt},
                      {"name": "assistant_report.docx", "path": dpath}],
            "notes": [f"Assistant report ready: {n} summary sentences, {len(qs)} Q&A pairs."]}


# ---------------------------------------------------------------- translate
def translate_pdf(paths, opts, out):
    target = opts.get("lang", "bn")
    blob, total = read_pdf_text(paths[0])
    if not blob.strip():
        raise ToolError("No text could be extracted from this PDF.")
    translated = _translate(blob, target)
    docx_path = os.path.join(out, "translated.docx")
    from docx import Document
    d = Document()
    for block in re.split(r"\n\s*\n", translated):
        for line in block.splitlines():
            if line.startswith("[Page "):
                d.add_paragraph(line)
                d.add_paragraph("")
            elif line.strip():
                d.add_paragraph(line.strip())
    d.save(docx_path)
    txt_path = os.path.join(out, "translated.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(translated)
    return {"files": [{"name": "translated.docx", "path": docx_path},
                      {"name": "translated.txt", "path": txt_path}],
            "notes": [f"Translated {total} page(s) into {target} (Google Translate, may need internet)."]}


def _translate(text, target):
    try:
        from deep_translator import GoogleTranslator
        out_parts = []
        CHUNK = 4800
        # translate page by page to preserve markers
        blocks = re.split(r"(\n\n\[Page \d+\]\n)", text)
        buf = ""
        for b in blocks:
            if b.strip().startswith("[Page "):
                if buf.strip():
                    out_parts.append(GoogleTranslator(source="auto", target=target).translate(buf[:CHUNK]) or buf)
                    buf = ""
                out_parts.append(b)
            else:
                buf += b
                if len(buf) > CHUNK:
                    out_parts.append(GoogleTranslator(source="auto", target=target).translate(buf[:CHUNK]) or buf)
                    buf = buf[CHUNK:]
        if buf.strip():
            out_parts.append(GoogleTranslator(source="auto", target=target).translate(buf) or buf)
        return " ".join(out_parts)
    except Exception as e:
        raise ToolError("Translation service unreachable (it uses Google Translate online). "
                        "Check your internet connection and try again. Details: %s" % e)


# ---------------------------------------------------------------- chat (extractive QA)
def _sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 20]


def _keywords(text):
    return {w for w in re.findall(r"[A-Za-z\u0980-\u09FF]{3,}", text.lower())
            if w not in _STOPWORDS}


def chat_pdf(paths, opts, out):
    blob, total = read_pdf_text(paths[0])
    question = str(opts.get("question") or "").strip()
    if not question:
        raise ToolError("Type your question first.")
    n_answers = max(1, min(8, int(opts.get("answers", 3))))
    qwords = _keywords(question)
    scored = []
    for i, s in enumerate(_sentences(blob)):
        overlap = qwords & _keywords(s)
        if not overlap:
            continue
        score = len(overlap) / max(1.0, len(qwords)) * 10 + len(overlap)
        if len(s.split()) < 40:
            score += 1.0
        scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    answers = [s for _, s in scored[:n_answers * 2]][:n_answers]
    if not answers:
        answers = ["I could not find a passage answering that question in this PDF. "
                   "Try rephrasing, or OCR the document first if it is scanned."]
    report = os.path.join(out, "chat_answer.txt")
    with open(report, "w", encoding="utf-8") as f:
        f.write(f"Q: {question}\n\n")
        for i, a in enumerate(answers, 1):
            f.write(f"{i}. {a}\n\n")
        f.write(f"(Answers extracted from a {total}-page PDF — offline extractive QA.)\n")
    return {"files": [{"name": "chat_answer.txt", "path": report}],
            "notes": [f"Found {len(answers)} passage(s)."]}


# ---------------------------------------------------------------- questions
def ai_questions(paths, opts, out):
    blob, total = read_pdf_text(paths[0])
    count = max(1, min(20, int(opts.get("count", 8))))
    maxlen = max(8, min(40, int(opts.get("maxlen", 22))))
    sents = [s for s in _sentences(blob) if len(s.split()) <= maxlen]
    if not sents:
        raise ToolError("No usable sentences found — this looks like a scanned PDF. Run OCR first.")
    # pick the most content-rich sentences, deduplicated
    ranked = sorted(_score_sentences(sents), key=lambda r: -r[0])
    picked, seen = [], set()
    for _, _, s in ranked:
        key = s.lower()[:60]
        if key in seen:
            continue
        seen.add(key)
        picked.append(s)
        if len(picked) >= count:
            break

    def blank_out(s):
        words = re.findall(r"[A-Za-z\u0980-\u09FF']+", s)
        freq = collections.Counter(w.lower() for w in words if w.lower() not in _STOPWORDS and len(w) > 3)
        if not freq:
            return s, None
        target = max(freq, key=freq.get)
        # blank the first occurrence
        pat = re.compile(re.escape(target), re.I)
        return pat.sub("______", s, count=1), target

    qpath = os.path.join(out, "questions.txt")
    with open(qpath, "w", encoding="utf-8") as f:
        f.write("AI-GENERATED QUESTIONS\n======================\n")
        for i, s in enumerate(picked, 1):
            q, _ = blank_out(s)
            f.write(f"{i}. {q}\n")
        f.write("\n\nANSWER KEY\n----------\n")
        for i, s in enumerate(picked, 1):
            _, ans = blank_out(s)
            f.write(f"{i}. {ans}\n")
    files = [{"name": "questions.txt", "path": qpath}]
    dpath = os.path.join(out, "questions.docx")
    from docx import Document
    d = Document()
    d.add_heading("AI-generated questions", 0)
    for i, s in enumerate(picked, 1):
        q, _ = blank_out(s)
        d.add_paragraph(f"{i}. {q}")
    d.add_paragraph("")
    d.add_heading("Answer key", 1)
    for i, s in enumerate(picked, 1):
        _, ans = blank_out(s)
        d.add_paragraph(f"{i}. {ans}")
    d.save(dpath)
    files.append({"name": "questions.docx", "path": dpath})
    return {"files": files,
            "notes": [f"Generated {len(picked)} fill-in-the-blank questions."]}


# ---------------------------------------------------------------- markdown
def pdf_to_markdown(paths, opts, out):
    from .pdf_ops import extract_text_pages
    texts, total = extract_text_pages(paths[0])
    md = [f"# Extracted from {os.path.basename(paths[0])}", ""]
    for i, t in enumerate(texts, 1):
        t = t.strip()
        if not t:
            continue
        md.append(f"## Page {i}")
        md.append("")
        # heuristics: numbered/bulleted lists -> markdown lists; headings kept as paragraphs
        lines = t.splitlines()
        in_list = None
        for line in lines:
            line = line.rstrip()
            s = line.strip()
            if not s:
                if in_list:
                    md.append("")
                    in_list = None
                continue
            m = re.match(r"^(\d+)[.)]\s+(.*)", s)
            if m:
                md.append(f"{m.group(1)}. {m.group(2)}")
                in_list = "ol"
                continue
            m = re.match(r"^[-*•·]\s+(.*)", s)
            if m:
                md.append(f"- {m.group(1)}")
                in_list = "ul"
                continue
            if in_list:
                md.append("")
                in_list = None
            md.append(s)
        md.append("")
    path = os.path.join(out, "document.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
    return {"files": [{"name": "document.md", "path": path}],
            "notes": [f"Converted {total} page(s) to Markdown."]}
