#!/usr/bin/env bash
# PDFly API client — bash + curl (JSON parsing via python3, optional)
# Usage: ./bash_client.sh a.pdf b.pdf
set -euo pipefail
BASE="${BASE:-http://localhost:5000}"

# 1. upload (repeat -F for every file)
ARGS=()
for f in "$@"; do ARGS+=(-F "files=@$f"); done
UPLOAD=$(curl -s -X POST "$BASE/api/upload" "${ARGS[@]}")
JOB=$(echo "$UPLOAD" | python3 -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
echo "job: $JOB"

# 2. process — change "merge_pdf" to any tool from GET /api/tools
RES=$(curl -s -X POST "$BASE/api/process" \
      -H "Content-Type: application/json" \
      -d "{\"job_id\":\"$JOB\",\"tool\":\"merge_pdf\",\"options\":{}}")
echo "$RES"

# 3. download every result file
echo "$RES" | python3 - "$BASE" <<'PY'
import sys, json, requests
base, res = sys.argv[1], json.loads(sys.stdin.read())
if not res.get("ok"):
    print("ERROR:", res.get("error")); sys.exit(1)
for f in res["files"]:
    data = requests.get(base + f["url"]).content
    open(f["name"], "wb").write(data)
    print(f"saved: {f['name']} ({len(data)} bytes)")
PY
