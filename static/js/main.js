/* ==================================================================
   PDFly — main.js  (hardened upload pipeline)
   ------------------------------------------------------------------
   * Drag & drop, file picker, clipboard paste (Ctrl+V)
   * XHR upload with live progress + 60 s timeout + fetch() fallback
   * ON-PAGE DEBUG CONSOLE (bottom-left 🛠): logs every action and the
     exact server response, so if anything fails you SEE the reason.
   * Delegated click handlers for #dropzone and #goBtn: even if an
     earlier init step fails, buttons keep working.
   * window.onerror + unhandledrejection surface everything as a toast.
   ================================================================== */
(function () {
  "use strict";

  /* ------------------------------------------------------ helpers */
  function $(sel, el) { return (el || document).querySelector(sel); }
  function $all(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }

  function toast(msg, err) {
    var t = $(".toast");
    if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); }
    t.textContent = msg;
    t.classList.toggle("err", !!err);
    t.classList.add("show");
    clearTimeout(t._h);
    t._h = setTimeout(function () { t.classList.remove("show"); }, 4500);
  }

  /* ------------------------- on-page debug console ------------------ */
  var dbgLines = [];
  function dbg(msg, isErr) {
    var line = new Date().toTimeString().slice(0, 8) + " " + msg;
    dbgLines.push(line);
    if (dbgLines.length > 60) dbgLines.shift();
    try {
      if (isErr) console.error("[PDFly] " + line);
      else console.log("[PDFly] " + line);
    } catch (e) { /* console unavailable — ignore */ }
  }
  window.PDFlyDbg = dbg;   // callable from the console (F12) too

  /* ------------------------------------------------------------- *
   *  GLOBAL PICK HOOK — the <input> calls this INLINE (onchange),
   *  so picking files works even if a later init step crashed.
   * ------------------------------------------------------------- */
  var pendingPicks = [];
  window.__pdflyPick = function (inp) {
    var fs = [];
    try { fs = Array.prototype.slice.call(inp.files || []); } catch (e) { }
    try { inp.value = ""; } catch (e) { }
    window.__pdflyPick._lastPick = Date.now();
    if (!fs.length) return;
    dbg("picker hook: " + fs.length + " file(s) from the dialog");
    if (typeof addFiles === "function" && STATE && STATE.files) addFiles(fs);
    else pendingPicks = pendingPicks.concat(fs);
  };
  /* which build of main.js is the browser ACTUALLY running? */
  var BUILD = (document.body && document.body.getAttribute("data-build")) || "?";

  /* report ANY uncaught error, never fail silently (also on-page) */
  window.addEventListener("error", function (e) {
    dbg("JS error: " + (e.message || "unknown"), true);
    toast("JS error: " + (e.message || "unknown"), true);
    var s = $("#dzStatus");
    if (s) { s.textContent = "✗ JS error: " + (e.message || "unknown") + " — refresh (Ctrl+F5)"; s.classList.add("err"); }
  });
  window.addEventListener("unhandledrejection", function (e) {
    dbg("Promise error: " + (e.reason && e.reason.message ? e.reason.message : e.reason), true);
  });

  function humanSize(b) {
    if (b > 1048576) return (b / 1048576).toFixed(1) + " MB";
    if (b > 1024) return Math.round(b / 1024) + " KB";
    return b + " B";
  }
  function postJSON(url, data) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data)
    }).then(function (r) { return r.json(); });
  }
  function readOpts(scope) {
    var opts = {};
    $all("[data-opt]", scope).forEach(function (n) {
      var id = n.getAttribute("data-opt");
      var type = n.getAttribute("data-type");
      if (type === "radio") {
        var checked = $('input[data-opt="' + id + '"]:checked', scope);
        if (checked) opts[id] = checked.value;
      } else if (type === "check") {
        opts[id] = n.checked;
      } else if (type === "number") {
        var v = parseFloat(n.value);
        opts[id] = isNaN(v) ? parseFloat(n.getAttribute("data-default") || "0") || 0 : v;
      } else {
        opts[id] = n.value;
      }
    });
    return opts;
  }

  window.PDFly = { $: $, $all: $all, toast: toast, dbg: dbg, postJSON: postJSON, readOpts: readOpts, humanSize: humanSize };

  /* -------------------------------------------------- header menus */
  $all(".dd").forEach(function (dd) {
    var btn = $(".dd-btn", dd);
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var was = dd.classList.contains("open");
      $all(".dd.open").forEach(function (d) { d.classList.remove("open"); });
      if (!was) dd.classList.add("open");
    });
  });
  document.addEventListener("click", function () {
    $all(".dd.open").forEach(function (d) { d.classList.remove("open"); });
  });

  /* ------------------------------------------------ server health */
  function checkServer() {
    fetch("/health").then(function (r) { return r.json(); }).then(function (d) {
      if (d && d.ok) dbg("server OK (" + d.engine + " v" + d.version + ")");
      else serverDown();
    }).catch(function () { serverDown(); });
  }
  function serverDown() {
    if ($("#serverAlert")) return;
    var a = document.createElement("div");
    a.id = "serverAlert";
    a.className = "server-alert";
    a.textContent = "⚠️ API server is not reachable. Run the launcher: Windows → start_windows.bat · Linux → bash start_linux.sh, then refresh this page.";
    document.body.prepend(a);
  }
  checkServer();

  /* ----------------------------------------------------- filter */
  $all(".chip").forEach(function (chip) {
    chip.addEventListener("click", function () {
      $all(".chip").forEach(function (c) { c.classList.remove("active"); });
      chip.classList.add("active");
      var cat = chip.getAttribute("data-cat");
      $all("[data-card]").forEach(function (card) {
        card.style.display = (cat === "All" || card.getAttribute("data-card") === cat) ? "" : "none";
      });
    });
  });

  /* ============================================================== *
   *   TOOL PAGE — uploader + workspace + processing
   * ============================================================== */
  /* which page are we on?  body[data-tool] OR #workbox[data-tool] with a
     NON-EMPTY tool id — if neither matches, this is the home page. */
  var page = null;
  $all("[data-tool]").forEach(function (el) {
    if (!page && el.getAttribute("data-tool")) page = el;
  });
  if (!page) return;                     // home page: nothing to wire here

  var TOOL = page.getAttribute("data-tool");
  dbg("tool page detected via [" + page.tagName.toLowerCase() + "[data-tool]] → " + TOOL);
  var STATE = {
    jobId: null,
    files: [],                            // {name, size, file, key, pages}
    uploading: false,
    processing: false,
    pagesMeta: {}
  };

  var drop = $("#dropzone"), fileInput = $("#fileInput");
  var grid = $("#fileGrid"), actionBar = $("#actionBar"), goBtn = $("#goBtn");
  var progress = $("#progress"), progressText = $("#progressText"), progressBar = $("#progressBar");
  var dzStatus = $("#dzStatus");

  var ACCEPT = (drop && drop.getAttribute("data-accept")) || ".pdf";
  var MULTIPLE = drop && drop.getAttribute("data-multiple") === "true";
  var MAXF = parseInt((drop && drop.getAttribute("data-max")) || "10", 10);
  var MINF = parseInt((drop && drop.getAttribute("data-min")) || "1", 10);

  dbg("tool=" + TOOL + " · accept=" + ACCEPT + " · multiple=" + MULTIPLE + " · max=" + MAXF);

  function setDzStatus(msg, err, html) {
    if (dzStatus) {
      if (html) dzStatus.innerHTML = msg; else dzStatus.textContent = msg;
      dzStatus.classList.toggle("err", !!err);
    }
  }

  /* boot marker — if you still see "Loading engine…" here, main.js
     never ran on this page (hard refresh with Ctrl+F5 fixes it). */
  setDzStatus("Ready ✓ — select, drop or paste files below");
  dbg("engine v" + BUILD + " ready");
  if (pendingPicks.length) {
    var pp = pendingPicks; pendingPicks = [];
    addFiles(pp);
  }

  /* ---------------------------------------------------- 1. add files */
  function acceptType(name) {
    name = (name || "").toLowerCase();
    return ACCEPT.split(",").some(function (ext) {
      var e = (ext || "").trim().toLowerCase();
      return e && name.indexOf(e) === name.length - e.length;
    });
  }

  function addFiles(fileList) {
    var files = Array.prototype.slice.call(fileList || []);
    if (!files.length) return;
    if (!MULTIPLE) { files = files.slice(0, 1); STATE.files = []; }  // single-file tools replace
    files.forEach(function (f) {
      if (!acceptType(f.name)) {
        dbg("rejected: " + f.name + " (type not allowed)", true);
        toast(f.name + " is not an accepted type", true);
        return;
      }
      if (STATE.files.length >= MAXF) { toast("Maximum " + MAXF + " files at once", true); return; }
      STATE.files.push({ name: f.name, size: f.size, file: f, key: null, pages: null });
      dbg("picked: " + f.name + " (" + humanSize(f.size) + ")");
    });
    renderCards();
    setDzStatus(STATE.files.length + " file(s) selected — uploading…");
    upload();
  }

  /* ----------------------------- 2. upload (XHR + progress + logs) */
  function upload() {
    if (STATE.uploading || !STATE.files.length) return;
    STATE.uploading = true;
    setBusy(true, "Uploading… 0%", 0);
    setDzStatus("Uploading " + STATE.files.length + " file(s)…");

    var fd = new FormData();
    STATE.files.forEach(function (r, i) { fd.append("files", r.file, "f" + i + "_" + r.file.name); });

    function onDone(res, statusText) {
      STATE.uploading = false;
      if (!res || !res.ok) {
        var msg = (res && res.error) || "Upload failed (" + (statusText || "error") + ")";
        dbg("upload FAILED: " + msg, true);
        toast(msg, true);
        setDzStatus("✗ " + msg + " — " + (STATE.triedRetry ? "press \"Choose files\" to try again" : "retrying…"), true);
        STATE.files.forEach(function (r) { r.err = true; });
        renderCards();
        setBusy(false);
        if (!STATE.triedRetry) {          // one automatic retry
          STATE.triedRetry = true;
          dbg("auto-retrying upload in 1.5 s…");
          setTimeout(function () {
            STATE.files.forEach(function (r) { r.err = false; });
            upload();
          }, 1500);
        }
        return;
      }
      STATE.files.forEach(function (r) { r.err = false; });
      STATE.triedRetry = false;
      STATE.jobId = res.job_id;
      STATE.files.forEach(function (r, i) {
        if (res.files && res.files[i]) { r.key = res.files[i].key; r.size = res.files[i].size; }
      });
      dbg("upload OK → job " + STATE.jobId + " · stored at " + (res.storage || "?"));
      setBusy(false);
      setDzStatus("✓ " + STATE.files.length + " file(s) uploaded — ready below", false);
      renderCards();
      enterWorkspace();
      onUploaded();
      toast(STATE.files.length + " file(s) uploaded ✓");
    }

    if (typeof XMLHttpRequest !== "undefined") {
      try {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload");
        xhr.timeout = 60000;
        xhr.upload.onprogress = function (e) {
          if (e.lengthComputable) {
            var pct = Math.round(e.loaded / e.total * 100);
            setBusy(true, "Uploading… " + pct + "%", pct);
          }
        };
        xhr.onload = function () {
          var res = null;
          try { res = JSON.parse(xhr.responseText); } catch (e2) { res = null; }
          onDone(res, (xhr.statusText || "HTTP " + xhr.status));
        };
        xhr.ontimeout = function () {
          dbg("upload TIMED OUT after 60s", true);
          toast("Upload timed out — try a smaller file or check the server console", true);
          setBusy(false); STATE.uploading = false;
          setDzStatus("✗ upload timed out", true);
        };
        xhr.onerror = function () {
          dbg("upload NETWORK error (server not answering?)", true);
          toast("Upload failed — the server did not answer. Is the server console showing 'Running on http://127.0.0.1:5000'?", true);
          setBusy(false); STATE.uploading = false;
          setDzStatus("✗ network error", true);
        };
        xhr.onabort = function () { STATE.uploading = false; setBusy(false); };
        xhr.send(fd);
        dbg("POST /api/upload (XHR) — sending " + STATE.files.length + " file(s)…");
        return;
      } catch (xhrErr) {
        dbg("XHR failed, falling back to fetch(): " + xhrErr.message, true);
      }
    }
    /* fallback: fetch() (no progress, still fully functional) */
    fetch("/api/upload", { method: "POST", body: fd })
      .then(function (r) { return r.json(); })
      .then(function (res) { onDone(res, "ok"); })
      .catch(function (err) { onDone(null, err.message); });
  }

  /* ------------------------------------- 3. thumbnail cards + drag */
  function renderCards() {
    if (!grid) return;
    if (!STATE.files.length) {
      grid.classList.add("hidden");
      if (drop) drop.classList.remove("hidden");
      var wh0 = $("#workspaceHead"); if (wh0) wh0.classList.add("hidden");
      if (actionBar) actionBar.classList.add("hidden");
      document.body.classList.remove("has-bar");
      return;
    }
    grid.classList.remove("hidden");
    grid.innerHTML = "";

    STATE.files.forEach(function (r, i) {
      var card = document.createElement("div");
      card.className = "file-card";
      card.setAttribute("draggable", "true");
      card.setAttribute("data-idx", i);

      var thumb = document.createElement("img");
      thumb.className = "thumb"; thumb.alt = "";
      thumb.src = "/static/img/file.svg";
      card.appendChild(thumb);
      // load previews gently, one at a time (up to 200 files) —
      // the server renders them serialized + cached, so this is safe
      if (r.key && r.key.toLowerCase().endsWith(".pdf") && STATE.jobId) {
        (function (job, key, delay) {
          setTimeout(function () {
            thumb.src = "/api/preview/" + job + "/" + key + "?page=0";
          }, delay);
        })(STATE.jobId, r.key, i * 120);
      }
      thumb.onerror = function () { if (thumb.src.indexOf("file.svg") < 0) thumb.src = "/static/img/file.svg"; };

      var badge = document.createElement("span");
      badge.className = "card-badge"; badge.textContent = (i + 1);
      card.appendChild(badge);

      var cs = document.createElement("span");
      cs.className = "cstat" + (r.key ? " ok" : (r.err ? " err" : ""));
      cs.textContent = r.key ? "✓" : (r.err ? "✗" : "↑");
      cs.title = r.key ? "uploaded" : (r.err ? "upload failed — will retry / re-pick" : "uploading…");
      card.appendChild(cs);

      var fx = document.createElement("button");
      fx.className = "fx"; fx.title = "Remove"; fx.textContent = "✕";
      fx.addEventListener("click", function (ev) {
        ev.stopPropagation();
        STATE.files.splice(i, 1);
        renderCards();
      });
      card.appendChild(fx);

      var meta = document.createElement("div");
      meta.className = "fmeta";
      var nm = document.createElement("b"); nm.textContent = r.name;
      var sz = document.createElement("span"); sz.textContent = humanSize(r.size);
      meta.appendChild(nm); meta.appendChild(sz);
      card.appendChild(meta);
      grid.appendChild(card);

      if (r.key && r.key.toLowerCase().endsWith(".pdf") && STATE.pagesMeta[r.key] === undefined) {
        (function (job, key, delay) {
          setTimeout(function () {
            fetch("/api/pages/" + job + "/" + key).then(function (resp) { return resp.json(); })
              .then(function (d) {
                if (d && d.ok) {
                  STATE.pagesMeta[key] = d.pages;
                  sz.textContent = humanSize(r.size) + " · " + d.pages + " page" + (d.pages > 1 ? "s" : "");
                }
              }).catch(function () { /* non-fatal */ });
          }, 60 + delay);
        })(STATE.jobId, r.key, i * 120);
      }
    });
    attachDrag();
  }

  function attachDrag() {
    if (!grid) return;
    var dragging = null;
    $all(".file-card", grid).forEach(function (card) {
      card.addEventListener("dragstart", function (e) {
        dragging = card; card.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragend", function () {
        card.classList.remove("dragging");
        dragging = null;
        var order = $all(".file-card", grid).map(function (c) { return parseInt(c.getAttribute("data-idx"), 10); });
        if (STATE.jobId && order.length > 1) {
          postJSON("/api/reorder", { job_id: STATE.jobId, order: order }).then(function (res) {
            if (!res.ok) dbg("reorder server error: " + (res.error || ""), true);
            else dbg("order saved: [" + order.join(",") + "]");
          });
        }
        $all(".card-badge", grid).forEach(function (b, i) { b.textContent = (i + 1); });
      });
      card.addEventListener("dragover", function (e) {
        e.preventDefault();
        var after = null;
        $all(".file-card:not(.dragging)", grid).forEach(function (c) {
          var b = c.getBoundingClientRect();
          if (e.clientY > b.top + b.height / 2) after = c;
        });
        if (after) grid.insertBefore(dragging, after.nextSibling);
        else grid.insertBefore(dragging, grid.firstChild);
      });
    });
  }

  /* ------------------------------------------------ 4. workspace UI */
  function enterWorkspace() {
    if (drop) drop.classList.add("hidden");
    var dl = $("#dropHint"); if (dl) dl.classList.add("hidden");
    var wh = $("#workspaceHead");
    if (wh) {
      wh.classList.remove("hidden");
      wh.innerHTML = "<h2>" + STATE.files.length + " file(s) uploaded — ready to work</h2>" +
        (TOOL === "merge_pdf" ? "<p>Drag the cards to set the merge order (left card = first file), then press <b>Convert / Process</b>.</p>"
                              : "<p>Set the options, then press <b>Convert / Process</b>.</p>") +
        (MULTIPLE ? '<button type="button" class="btn btn-ghost" id="addMore" style="margin-top:6px">＋ Add more files</button>' : "");
      wh.scrollIntoView({ behavior: "smooth", block: "start" });
      var am = $("#addMore");
      if (am) am.addEventListener("click", function () { if (fileInput) fileInput.click(); });
    }
    if (actionBar) {
      actionBar.classList.remove("hidden");
      document.body.classList.add("has-bar");
    }
    if (goBtn) {
      goBtn.disabled = false;
      goBtn.textContent = STATE.files.length > 1 ? "Convert " + STATE.files.length + " files" : "Convert / Process";
    }
    var meta = $("#actionMeta");
    if (meta) meta.textContent = STATE.files.length + " file(s) ready · " + TOOL;
  }

  function setBusy(on, msg, pct) {
    if (!progress) return;
    if (on) {
      progress.classList.remove("hidden");
      if (progressText) progressText.textContent = msg || "Working…";
      if (progressBar) {
        progressBar.style.width = (pct === undefined || pct === null ? 40 : pct) + "%";
        if (pct === undefined || pct === null) progressBar.classList.add("indet");
        else progressBar.classList.remove("indet");
      }
    } else {
      progress.classList.add("hidden");
      if (progressBar) progressBar.style.width = "0%";
    }
  }

  /* ------------------- drop zone: drag events (direct listeners) */
  if (drop) {
    ["dragenter", "dragover"].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("drag"); });
    });
    ["dragleave", "drop"].forEach(function (ev) {
      drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("drag"); });
    });
    drop.addEventListener("drop", function (e) { addFiles(e.dataTransfer.files); });
  }

  /* file picker → files — BELT & BRACES: the <input> also has an INLINE
     onchange="window.__pdflyPick(this)" attribute in the HTML, so a pick
     works even if this listener never got attached. The 500 ms guard
     stops the same selection from being added twice. */
  if (fileInput) {
    fileInput.addEventListener("change", function () {
      if (window.__pdflyPick && window.__pdflyPick._lastPick &&
          (Date.now() - window.__pdflyPick._lastPick) < 500) {
        return;                         // already handled by the inline hook
      }
      dbg("file dialog returned " + (fileInput.files ? fileInput.files.length : 0) + " file(s)");
      addFiles(fileInput.files);
      fileInput.value = "";           // allow re-selecting the same file
    });
  }

  /* clipboard paste anywhere */
  window.addEventListener("paste", function (e) {
    var items = (e.clipboardData || {}).items || [];
    var fs = [];
    for (var i = 0; i < items.length; i++) if (items[i].kind === "file") fs.push(items[i].getAsFile());
    if (fs.length) { dbg("pasted " + fs.length + " file(s)"); addFiles(fs); }
  });

  /* ---- DELEGATED clicks: work even if some init step failed ---- */
  document.addEventListener("click", function (e) {
    var t = e.target;
    if (!t || !t.closest) return;
    // open the file picker when the user clicks anywhere on the dropzone
    if (t.closest("#dropzone")) {
      if (fileInput) fileInput.click();
      return;
    }
    // the main action button
    if (t.closest("#goBtn")) { onGoClick(); return; }
  });

  /* ================================================================ *
   *  5. PROCESS — "Convert / Process" (used by button + keyboard)
   * ================================================================ */
  function onGoClick() {
    if (STATE.processing) return;
    if (STATE.files.length < MINF) { toast("Add at least " + MINF + " file(s) first", true); return; }
    if (!STATE.jobId) { toast("Files are still uploading — wait a second", true); return; }

    if (TOOL === "pdf_reader") { Reader.load(); return; }

    STATE.processing = true;
    if (goBtn) goBtn.disabled = true;
    setBusy(true, "Processing your file" + (STATE.files.length > 1 ? "s" : "") + "…");
    dbg("POST /api/process tool=" + TOOL);

    var options = readOpts(document);
    if (TOOL === "annotator_pdf") {
      if (!Annotator.notes.length) {
        toast("Click on the page to place a note first", true);
        setBusy(false); if (goBtn) goBtn.disabled = false; return;
      }
      options.annotations = JSON.stringify(Annotator.notes);
    }

    postJSON("/api/process", { job_id: STATE.jobId, tool: TOOL, options: options })
      .then(function (res) {
        STATE.processing = false;
        if (!res.ok) {
          dbg("process FAILED: " + (res.error || "?"), true);
          toast(res.error || "Processing failed", true);
          setBusy(false); if (goBtn) goBtn.disabled = false;
          return;
        }
        dbg("process OK → " + res.files.length + " file(s)");
        showResults(res);
      })
      .catch(function (err) {
        STATE.processing = false;
        dbg("process NETWORK error: " + (err && err.message ? err.message : "?"), true);
        setBusy(false); if (goBtn) goBtn.disabled = false;
        toast("Processing failed — check the server console", true);
      });
  }

  /* ================================================================ *
   *  6. RESULTS — download manager
   * ================================================================ */
  function showResults(res) {
    var wb = $("#workbox"); if (wb) wb.classList.add("hidden");
    if (actionBar) actionBar.classList.add("hidden");
    document.body.classList.remove("has-bar");
    var r = $("#resultbox");
    r.classList.remove("hidden");
    r.scrollIntoView({ behavior: "smooth", block: "start" });

    var filesBox = $("#resFiles");
    filesBox.innerHTML = "";
    res.files.forEach(function (f) {
      var el = document.createElement("div");
      el.className = "res-file";
      var isPdf = f.name.toLowerCase().endsWith(".pdf");
      el.innerHTML =
        (isPdf ? '<img class="res-thumb" src="' + f.url.replace("/result/", "/api/preview/") + '" alt="">'
               : '<img class="res-thumb" src="/static/img/zip.svg" alt="">') +
        '<div class="meta"><b></b><span>' + humanSize(f.size) + '</span></div>' +
        '<div class="res-actions">' +
          '<a class="btn btn-primary" download href="' + f.url + '">⬇ Download</a>' +
          '<button class="btn btn-ghost share-btn" data-url="' + f.url + '">🔗 Share</button>' +
        '</div>';
      el.querySelector("b").textContent = f.name;
      filesBox.appendChild(el);
    });

    if (res.files.length > 1 && STATE.jobId) {
      var all = document.createElement("div");
      all.className = "res-all";
      all.innerHTML = '<a class="btn btn-primary btn-lg" href="/api/zip/' + STATE.jobId + '">📦 Download all (.zip)</a>';
      filesBox.parentElement.insertBefore(all, filesBox.nextSibling);
    }

    $all(".share-btn", filesBox).forEach(function (b) {
      b.addEventListener("click", function () {
        var link = location.origin + b.getAttribute("data-url");
        (navigator.clipboard ? navigator.clipboard.writeText(link) : Promise.reject())
          .then(function () { toast("Share link copied: " + link); })
          .catch(function () { prompt("Copy this share link:", link); });
      });
    });

    var notes = $("#notes");
    notes.innerHTML = "";
    (res.notes || []).forEach(function (n) {
      var li = document.createElement("li");
      li.textContent = n;
      notes.appendChild(li);
      notes.parentElement.classList.remove("hidden");
    });
  }

  var again = $("#againBtn");
  if (again) again.addEventListener("click", function () { location.reload(); });

  /* ================================================================ *
   *  SPECIAL TOOLS: reader / annotator / form filler / scanner
   * ================================================================ */
  function onUploaded() {
    if (!STATE.jobId || !STATE.files.length) return;
    if (TOOL === "pdf_reader") Reader.load();
    if (TOOL === "annotator_pdf") Annotator.load();
    if (TOOL === "pdf_forms") FormFiller.hint();
  }
  function firstKey() {
    return STATE.files.length ? (STATE.files[0].key || null) : null;
  }

  /* ---------------- PDF Reader ------------------------------ */
  var Reader = {
    page: 0, pages: 1,
    load: function () {
      var key = firstKey(); if (!key) return;
      var box = $("#readerBox"); if (!box) return;
      box.classList.remove("hidden");
      ["#workbox .dropzone", "#workbox .options", "#actionBar"].forEach(function (s) {
        var n = $(s); if (n) n.style.display = "none";
      });
      var self = this;
      fetch("/api/pages/" + STATE.jobId + "/" + key).then(function (r) { return r.json(); })
        .then(function (d) { self.pages = Math.max(1, d.pages || 1); self.show(); })
        .catch(function () { self.pages = 1; self.show(); });
    },
    show: function () {
      var key = firstKey(); if (!key) return;
      var img = $("#readerImg");
      img.src = "/api/preview/" + STATE.jobId + "/" + key + "?page=" + this.page;
      img.onload = function () { $("#readerImgWrap").classList.remove("hidden"); };
      $("#readerNav").textContent = "Page " + (this.page + 1) + " / " + this.pages;
    },
    prev: function () { if (this.page > 0) { this.page--; this.show(); } },
    next: function () { if (this.page < this.pages - 1) { this.page++; this.show(); } },
    zoom: function (dir) {
      var img = $("#readerImg");
      var w = parseFloat(img.style.maxWidth || "100%");
      if (!w || w > 500) w = 100;
      w = Math.max(30, Math.min(300, w + dir * 30));
      img.style.maxWidth = w + "%";
    },
    download: function () { var k = firstKey(); if (k) window.location.href = "/result/" + STATE.jobId + "/" + k; }
  };
  [["#readerPrev", function () { Reader.prev(); }],
   ["#readerNext", function () { Reader.next(); }],
   ["#zoomIn", function () { Reader.zoom(30); }],
   ["#zoomOut", function () { Reader.zoom(-30); }],
   ["#readerDl", function () { Reader.download(); }]].forEach(function (pair) {
    var el = $(pair[0]); if (el) el.addEventListener("click", pair[1]);
  });
  document.addEventListener("keydown", function (e) {
    var box = $("#readerBox");
    if (TOOL === "pdf_reader" && box && !box.classList.contains("hidden")) {
      if (e.key === "ArrowRight") Reader.next();
      if (e.key === "ArrowLeft") Reader.prev();
    }
  });

  /* -------------- Annotator ---------------------------------- */
  var Annotator = {
    notes: [], page: 0, pages: 1,
    load: function () {
      var key = firstKey(); if (!key) return;
      var box = $("#annotationBox"); if (!box) return;
      box.classList.remove("hidden");
      var self = this;
      fetch("/api/pages/" + STATE.jobId + "/" + key).then(function (r) { return r.json(); })
        .then(function (d) { self.pages = Math.max(1, d.pages || 1); self.showPage(); })
        .catch(function () { self.pages = 1; self.showPage(); });
    },
    showPage: function () {
      var key = firstKey(), self = this;
      var wrap = $("#annoCanvasWrap"); if (!wrap) return;
      wrap.innerHTML = "";
      var holder = document.createElement("div");
      holder.className = "anno-holder";
      var img = new Image();
      img.onload = function () {
        var MAXW = Math.min(760, ($(".tool-page") ? $(".tool-page").clientWidth - 80 : 760));
        var scale = MAXW / img.width;
        holder.style.width = (img.width * scale) + "px";
        holder.style.position = "relative";
        img.style.width = "100%"; img.style.display = "block";
        holder.appendChild(img);
        var layer = document.createElement("div");
        layer.className = "anno-layer";
        holder.appendChild(layer);
        layer.addEventListener("click", function (e) {
          var rect = holder.getBoundingClientRect();
          var xPct = (e.clientX - rect.left) / rect.width * 100;
          var yPct = (e.clientY - rect.top) / rect.height * 100;
          self.addNote(Math.round(xPct * 10) / 10, Math.round(yPct * 10) / 10, self.page + 1);
        });
        wrap.appendChild(holder);
        self.paint();
      };
      img.src = "/api/preview/" + STATE.jobId + "/" + key + "?page=" + this.page;
      $("#annoPage").textContent = "Page " + (this.page + 1) + " / " + this.pages;
    },
    addNote: function (xPct, yPct, page) {
      var text = ($("#opt-text") ? $("#opt-text").value : "").trim() || "Note";
      var size = parseFloat($("#opt-size") ? $("#opt-size").value : 14) || 14;
      var colorSel = $('input[data-opt="color"]:checked') || $('select[data-opt="color"]');
      var color = colorSel ? colorSel.value : "#E5322D";
      this.notes.push({ page: page, x: xPct, y: 100 - yPct, text: text, size: size, color: color });
      this.paint();
      toast("Note placed on page " + page);
    },
    paint: function () {
      var holder = $(".anno-holder"); if (!holder) return;
      $all(".anno-note", holder).forEach(function (n) { n.remove(); });
      this.notes.filter(function (n) { return n.page === Annotator.page + 1; }).forEach(function (n) {
        var el = document.createElement("div");
        el.className = "anno-note";
        el.style.left = n.x + "%";
        el.style.top = (100 - n.y) + "%";
        el.style.borderColor = n.color; el.style.color = n.color;
        el.textContent = n.text + "  ✕";
        el.addEventListener("click", function () {
          Annotator.notes = Annotator.notes.filter(function (x) { return x !== n; });
          Annotator.paint();
        });
        holder.appendChild(el);
      });
    },
    prev: function () { if (this.page > 0) { this.page--; this.showPage(); } },
    next: function () { if (this.page < this.pages - 1) { this.page++; this.showPage(); } }
  };
  [["#annoPrev", function () { Annotator.prev(); }],
   ["#annoNext", function () { Annotator.next(); }]].forEach(function (pair) {
    var el = $(pair[0]); if (el) el.addEventListener("click", pair[1]);
  });

  /* -------------- Form Filler --------------------------------- */
  var FormFiller = {
    hint: function () {
      if (!STATE.jobId) return;
      postJSON("/api/process", { job_id: STATE.jobId, tool: "pdf_forms", options: { fields: "" } })
        .then(function (res) {
          if (!res.ok) return;
          var box = $("#fieldsHint"); if (!box) return;
          box.classList.remove("hidden");
          fetch(res.files[0].url).then(function (r) { return r.text(); }).then(function (t) {
            var m = t.match(/\{[^}]*\}/);
            box.innerHTML = "<b>Detected fields:</b><br><pre>" + (m ? m[0].replace(/</g, "&lt;") : "—") +
              "</pre><button type='button' class='btn btn-soft' id='useFields'>Use these fields</button>";
            var uf = $("#useFields");
            if (uf) uf.addEventListener("click", function () {
              var inp = $("#opt-fields");
              if (inp && m) { inp.value = m[0]; toast("Edit the values, then press Convert / Process"); }
            });
          });
        });
    }
  };

  /* -------------- Scanner (webcam) ----------------------------- */
  (function Scanner() {
    var box = $("#scannerBox");
    if (!box || TOOL !== "pdf_scanner") return;
    box.classList.remove("hidden");
    var video = $("#camVideo"), stream = null;
    $("#camStart").addEventListener("click", function () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        toast("Camera not available — use 'Upload images' instead", true); return;
      }
      navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } })
        .then(function (s) {
          stream = s; video.srcObject = s; video.play();
          $("#camStart").textContent = "Camera on — press Capture";
          $("#camCapture").disabled = false;
        })
        .catch(function () { toast("Camera permission denied — allow it in the browser", true); });
    });
    $("#camCapture").addEventListener("click", function () {
      if (!stream) return;
      var cv = document.createElement("canvas");
      cv.width = video.videoWidth; cv.height = video.videoHeight;
      cv.getContext("2d").drawImage(video, 0, 0);
      cv.toBlob(function (blob) {
        if (!blob) return;
        if (STATE.files.length >= MAXF) { toast("Maximum " + MAXF + " captures", true); return; }
        STATE.files.push({ name: "scan-" + Date.now() + ".jpg", size: blob.size,
                           file: new File([blob], "scan-" + Date.now() + ".jpg", { type: "image/jpeg" }),
                           key: null, pages: null });
        renderCards();
        upload();
      }, "image/jpeg", 0.92);
    });
  })();

  dbg("ready — drop or select files above");
})();
