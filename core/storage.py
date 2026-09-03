"""Temporary job-file storage helpers.

Robust across OS / permissions:
 1. Uses $PDFLY_STORAGE if set.
 2. Else the project folder's pdfly_storage/ (works on Windows & Linux).
 3. If that is NOT writable (read-only drive, Program Files, etc.),
    automatically falls back to the system temp dir — uploads can then
    never fail because of permissions.
"""
import os, sys, time, uuid, shutil, tempfile, zipfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _writable(path):
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".write_test")
        with open(probe, "w") as f:
            f.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def _pick_root():
    env = os.environ.get("PDFLY_STORAGE")
    if env and _writable(env):
        return env
    proj = os.path.join(PROJECT_ROOT, "pdfly_storage")
    if _writable(proj):
        return proj
    # last resort: OS temp dir (always writable)
    tmp = os.path.join(tempfile.gettempdir(), "pdfly_storage")
    _writable(tmp)
    return tmp


STORAGE_ROOT = _pick_root()
MAX_AGE = 30 * 60  # seconds — files older than 30 minutes are auto-cleaned


def storage_info():
    """Human-readable info used by /debug and the startup banner."""
    try:
        free = shutil.disk_usage(STORAGE_ROOT).free
    except Exception:
        free = -1
    return {
        "root": STORAGE_ROOT,
        "writable": _writable(STORAGE_ROOT),
        "disk_free_mb": round(free / 1048576) if free >= 0 else None,
        "temp_dir": tempfile.gettempdir(),
        "max_age_min": MAX_AGE // 60,
    }


def job_dir(job_id=None):
    job_id = job_id or uuid.uuid4().hex[:12]
    d = os.path.join(STORAGE_ROOT, job_id)
    os.makedirs(d, exist_ok=True)
    return d


def cleanup():
    try:
        now = time.time()
        for name in os.listdir(STORAGE_ROOT):
            p = os.path.join(STORAGE_ROOT, name)
            if os.path.isdir(p) and now - os.path.getmtime(p) > MAX_AGE:
                shutil.rmtree(p, ignore_errors=True)
    except Exception:
        pass


def zip_files(paths, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    return zip_path


# startup banner: tell the operator exactly where files are kept
_info = storage_info()
print(f"[PDFly] Storage: {_info['root']}  (writable={_info['writable']}, "
      f"free disk={_info['disk_free_mb']} MB)", file=sys.stderr)
