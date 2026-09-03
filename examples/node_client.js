// PDFly API client — Node.js
// Usage: node node_client.js a.pdf b.pdf
// npm i form-data
const fs = require('fs');
const FormData = require('form-data');

const BASE = 'http://localhost:5000';

async function upload(paths) {
  const fd = new FormData();
  for (const p of paths) fd.append('files', fs.createReadStream(p), require('path').basename(p));
  const r = await fetch(`${BASE}/api/upload`, { method: 'POST', body: fd });
  return r.json();
}

async function process(jobId, tool, options = {}) {
  const r = await fetch(`${BASE}/api/process`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, tool, options }),
  });
  return r.json();
}

// ---- example: merge two PDFs ------------------------------------------
(async () => {
  const up = await upload(process.argv.slice(2));
  const res = await process(up.job_id, 'merge_pdf');
  for (const f of res.files) {
    const buf = Buffer.from(await (await fetch(BASE + f.url)).arrayBuffer());
    fs.writeFileSync(f.name, buf);
    console.log(`saved: ${f.name} (${buf.length} bytes)`);
  }
})().catch((e) => { console.error(e.message); process.exit(1); });
