"""PDFly API client — Python.
Usage: python python_client.py a.pdf b.pdf
pip install requests
"""
import sys
import requests

BASE = "http://localhost:5000"


def upload(paths):
    files = [("files", (p.split("/")[-1], open(p, "rb"))) for p in paths]
    r = requests.post(f"{BASE}/api/upload", files=files)
    r.raise_for_status()
    return r.json()


def process(job_id, tool, options=None):
    r = requests.post(f"{BASE}/api/process",
                      json={"job_id": job_id, "tool": tool, "options": options or {}})
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    up = upload(sys.argv[1:])
    res = process(up["job_id"], "merge_pdf")
    for f in res["files"]:
        data = requests.get(BASE + f["url"]).content
        open(f["name"], "wb").write(data)
        print(f"saved: {f['name']} ({len(data)} bytes)")
