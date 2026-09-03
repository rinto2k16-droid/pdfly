"""Single global lock for every pypdfium2 / PDFium call.

PDFium is a native C library and is NOT thread-safe: two threads using
it at the same time corrupt the heap and kill the whole Python process
(SIGABRT → "munmap_chunk(): invalid pointer", exit code 134). That was
the exact bug behind "the server disconnects when I upload more than
2 files". EVERY pdfium usage in the app must go through this lock.
Page counts avoid pdfium entirely (they use pypdf, pure Python).
"""
import threading

PDFIUM_LOCK = threading.Lock()
