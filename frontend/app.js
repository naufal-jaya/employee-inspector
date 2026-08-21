const API_BASE = window.location.hostname === "localhost"
  ? "http://localhost:8000"
  : `http://${window.location.hostname}:8000`;

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────
let selectedImageFile = null;
let selectedVideoFile = null;

// ─────────────────────────────────────────────
// Tab Switching
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const tabs = document.querySelectorAll(".tab-btn");
  const panels = document.querySelectorAll(".tab-panel");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      tabs.forEach((t) => {
        t.classList.remove("tab-btn--active");
        t.setAttribute("aria-selected", "false");
      });
      panels.forEach((p) => {
        p.classList.remove("tab-panel--active");
        p.hidden = true;
      });

      tab.classList.add("tab-btn--active");
      tab.setAttribute("aria-selected", "true");
      const panel = document.getElementById(`${target}Panel`);
      if (panel) {
        panel.classList.add("tab-panel--active");
        panel.hidden = false;
      }

      if (target === "live") {
        startLiveLoop();
      } else {
        stopLiveLoop();
      }
    });
  });

  initImageTab();
  initVideoTab();
  initLiveTab();
});

// ─────────────────────────────────────────────
// IMAGE TAB
// ─────────────────────────────────────────────
function initImageTab() {
  const fileInput = document.getElementById("imageFileInput");
  const dropzone = document.getElementById("imageDropzone");
  const analyzeBtn = document.getElementById("analyzeImageBtn");

  setupDropzone(dropzone, fileInput, "image/*", (file) => handleImageSelect(file));

  if (analyzeBtn) analyzeBtn.addEventListener("click", analyzeImage);
  
  const demoBtn = document.getElementById("demoImageBtn");
  if (demoBtn) demoBtn.addEventListener("click", loadDemoImage);
}

async function loadDemoImage() {
  try {
    const res = await fetch("assets/demo-image.png");
    const blob = await res.blob();
    const file = new File([blob], "demo-image.png", { type: "image/png" });
    handleImageSelect(file);
    setTimeout(() => {
      document.getElementById("analyzeImageBtn").click();
    }, 300);
  } catch (err) {
    showStatus("imageStatusMsg", "Gagal memuat gambar demo.", true);
  }
}

function handleImageSelect(file) {
  if (!file || !file.type.startsWith("image/")) {
    showStatus("imageStatusMsg", "Pilih berkas gambar yang valid.", true);
    return;
  }
  selectedImageFile = file;
  document.getElementById("analyzeImageBtn").disabled = false;
  showStatus("imageStatusMsg", "");

  const reader = new FileReader();
  reader.onload = (e) => {
    const dropzone = document.getElementById("imageDropzone");
    const label = document.getElementById("imageDropzoneLabel");
    if (label) label.style.display = "none";
    removeOldPreview(dropzone, "upload-preview");

    const img = document.createElement("img");
    img.src = e.target.result;
    img.className = "upload-preview";
    dropzone.appendChild(img);
  };
  reader.readAsDataURL(file);
}

async function analyzeImage() {
  if (!selectedImageFile) return;
  const analyzeBtn = document.getElementById("analyzeImageBtn");
  const resultPanel = document.getElementById("imageResultPanel");

  setButtonLoading(analyzeBtn, true, "Menganalisis...");
  showStatus("imageStatusMsg", "Menganalisis gambar & aturan keselamatan...");
  showLoading(true);
  if (resultPanel) resultPanel.hidden = true;

  try {
    const formData = new FormData();
    formData.append("image", selectedImageFile);

    const res = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }
    const data = await res.json();
    renderImageResults(data);
    showStatus("imageStatusMsg", "");
  } catch (err) {
    showStatus("imageStatusMsg", `Analisis gagal: ${err.message}`, true);
  } finally {
    setButtonLoading(analyzeBtn, false, '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg> Analisis Gambar');
    showLoading(false);
  }
}

function renderImageResults(data) {
  const resultPanel = document.getElementById("imageResultPanel");
  if (resultPanel) resultPanel.hidden = false;

  const annotatedImage = document.getElementById("annotatedImage");
  if (annotatedImage && data.annotated_image) annotatedImage.src = data.annotated_image;

  const s = data.summary || {};
  updateGaugeChart("imgMetricScore", s.safety_score ?? 0);
  setText("imgMetricObjects", s.total_objects ?? 0);
  setText("imgMetricPersons", s.person_count ?? 0);
  setText("imgMetricViolations", s.violations_count ?? 0);
  setText("imgMetricRisk", `${s.risk_score ?? 0} / 100`);

  const allObjects = data.all_objects || [];
  setText("imgObjectCount", `${allObjects.length} objek`);
  const objectsGrid = document.getElementById("imgObjectsGrid");
  if (objectsGrid) {
    let personCounter = 0;
    objectsGrid.innerHTML = allObjects.length
      ? allObjects.map((obj) => {
          let displayName = obj.class_name;
          if (displayName === "Person") {
            personCounter++;
            displayName = `Person ${personCounter}`;
          }
          return `
        <div class="object-chip object-chip--${getCategoryClass(obj.category)}">
          <div class="object-chip__header">
            <span class="object-chip__name">${escapeHtml(displayName)}</span>
            <span class="object-chip__conf">${obj.confidence_percent || `${(obj.confidence * 100).toFixed(1)}%`}</span>
          </div>
          <div class="object-chip__meta">${obj.category}</div>
        </div>`;
        }).join("")
      : `<p class="empty-text">Tidak ada objek terdeteksi.</p>`;
  }

  const resultList = document.getElementById("imgResultList");
  if (resultList) {
    const results = data.results || [];
    resultList.innerHTML = results.length
      ? results.map((p, index) => buildPersonCard(p, index)).join("")
      : `<p class="empty-text">Tidak ada orang terdeteksi.</p>`;
  }
}

function buildPersonCard(person, index) {
  const isCompliant = person.compliance_status === "Compliant";
  const missingHtml = person.missing_ppe?.length
    ? person.missing_ppe.map((i) => `<span class="badge badge--bad">${escapeHtml(i)}</span>`).join(" ")
    : `<span class="badge badge--ok">Tidak ada</span>`;
  const presentHtml = person.detected_ppe?.length
    ? person.detected_ppe.map((i) => `<span class="badge badge--ok">${escapeHtml(i)}</span>`).join(" ")
    : `<span class="badge badge--muted">Tidak ada</span>`;
  const carriedHtml = person.carried_ppe?.length
    ? person.carried_ppe.map((i) => `<span class="badge badge--warn">${escapeHtml(i)}</span>`).join(" ")
    : "";
  const carriedLine = carriedHtml
    ? `<span>Dibawa (tidak dipakai): ${carriedHtml}</span>`
    : "";
  
  // Use array index (1-based) if provided, otherwise fallback to person_id
  const workerNumber = index !== undefined ? index + 1 : person.person_id;
  
  return `
    <div class="result-card ${isCompliant ? "compliant" : "non-compliant"}">
      <div class="result-card__title">
        <span>Pekerja #${workerNumber}</span>
        <span class="badge ${isCompliant ? "badge--ok" : "badge--bad"}">${isCompliant ? "PATUH" : "PELANGGARAN"}</span>
      </div>
      <div class="result-card__meta">
        <span>Terdeteksi: ${presentHtml}</span>
        <span>Kurang: ${missingHtml}</span>
        ${carriedLine}
      </div>
      <div class="result-card__reco">${escapeHtml(person.recommendation)}</div>
    </div>`;
}

// ─────────────────────────────────────────────
// VIDEO TAB
// ─────────────────────────────────────────────
function initVideoTab() {
  const fileInput = document.getElementById("videoFileInput");
  const dropzone = document.getElementById("videoDropzone");
  const analyzeBtn = document.getElementById("analyzeVideoBtn");

  setupDropzone(dropzone, fileInput, "video/*", (file) => handleVideoSelect(file));

  if (analyzeBtn) analyzeBtn.addEventListener("click", analyzeVideo);
}

function handleVideoSelect(file) {
  if (!file || !file.type.startsWith("video/")) {
    showStatus("videoStatusMsg", "Pilih berkas video yang valid (MP4, WebM, AVI, MOV).", true);
    return;
  }
  selectedVideoFile = file;
  document.getElementById("analyzeVideoBtn").disabled = false;
  showStatus("videoStatusMsg", "");

  const dropzone = document.getElementById("videoDropzone");
  const label = document.getElementById("videoDropzoneLabel");
  if (label) label.style.display = "none";
  removeOldPreview(dropzone, "video-preview");

  const videoEl = document.createElement("video");
  videoEl.src = URL.createObjectURL(file);
  videoEl.className = "video-preview";
  videoEl.controls = true;
  videoEl.muted = true;
  dropzone.appendChild(videoEl);
}

async function analyzeVideo() {
  if (!selectedVideoFile) return;
  const analyzeBtn = document.getElementById("analyzeVideoBtn");
  const resultPanel = document.getElementById("videoResultPanel");

  setButtonLoading(analyzeBtn, true, "Memproses... bisa memakan waktu beberapa saat");
  showStatus("videoStatusMsg", "Mengirim video ke server untuk analisis per-frame...");
  showLoading(true);
  if (resultPanel) resultPanel.hidden = true;

  try {
    const formData = new FormData();
    formData.append("video", selectedVideoFile);

    const res = await fetch(`${API_BASE}/api/analyze-video`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }
    const data = await res.json();
    renderVideoResults(data);
    showStatus("videoStatusMsg", "");
  } catch (err) {
    showStatus("videoStatusMsg", `Analisis video gagal: ${err.message}`, true);
  } finally {
    setButtonLoading(analyzeBtn, false, '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg> Proses Video');
    showLoading(false);
  }
}

function renderVideoResults(data) {
  const resultPanel = document.getElementById("videoResultPanel");
  if (resultPanel) resultPanel.hidden = false;

  // Video players (dual confidence)
  const videoHighEl = document.getElementById("annotatedVideoHigh");
  if (videoHighEl && data.video_url_high_conf) {
    videoHighEl.src = `${API_BASE}${data.video_url_high_conf}`;
    videoHighEl.load();
  }

  const videoLowEl = document.getElementById("annotatedVideoLow");
  if (videoLowEl && data.video_url_low_conf) {
    videoLowEl.src = `${API_BASE}${data.video_url_low_conf}`;
    videoLowEl.load();
  }

  const summary = data.temporal_summary || [];
  const fps = data.fps || 0;
  const totalWorkers = summary.length;
  const fullyCompliant = summary.filter((w) => w.violation_seconds === 0).length;
  const hadViolations = summary.filter((w) => w.violation_seconds > 0).length;

  setText("vidMetricFps", `${fps}`);
  setText("vidMetricPersons", totalWorkers);
  setText("vidMetricCompliant", fullyCompliant);
  setText("vidMetricViolators", hadViolations);

  const list = document.getElementById("vidTemporalList");
  if (list) {
    list.innerHTML = summary.length
      ? summary.map((w) => buildTemporalCard(w)).join("")
      : `<p class="empty-text">Tidak ada orang terlacak di video ini.</p>`;
  }
}

function buildTemporalCard(worker) {
  const compliantPct = worker.compliance_rate ?? 0;
  const violationPct = Math.max(0, 100 - compliantPct).toFixed(1);
  const isFullyCompliant = worker.violation_seconds === 0;

  const primaryViolationHtml = worker.primary_violation
    ? `<span>Pelanggaran utama: <span class="badge badge--bad">${escapeHtml(worker.primary_violation)}</span></span>`
    : `<span class="badge badge--ok">Tidak ada pelanggaran</span>`;

  return `
    <div class="result-card ${isFullyCompliant ? "compliant" : "non-compliant"}">
      <div class="result-card__title">
        <span>Pekerja #${worker.track_id}</span>
        <span class="badge ${isFullyCompliant ? "badge--ok" : "badge--bad"}">${compliantPct.toFixed(1)}% Patuh</span>
      </div>
      <div class="time-bar-wrap">
        <div class="time-bar">
          <div class="time-bar__fill time-bar__fill--ok" style="width:${compliantPct}%" title="Patuh: ${worker.compliant_seconds} dt"></div>
          <div class="time-bar__fill time-bar__fill--bad" style="width:${violationPct}%" title="Pelanggaran: ${worker.violation_seconds} dt"></div>
        </div>
        <div class="time-bar__labels">
          <span>Patuh ${worker.compliant_seconds} dt</span>
          <span>Pelanggaran ${worker.violation_seconds} dt</span>
        </div>
      </div>
      <div class="result-card__meta">${primaryViolationHtml}</div>
    </div>`;
}

// ─────────────────────────────────────────────
// LIVE CAMERA TAB
// ─────────────────────────────────────────────
const LIVE_ANALYZE_INTERVAL_MS = 1000;
const LIVE_MAX_WIDTH = 640;
let liveStream = null;
let liveAnalyzeTimer = null;
let liveBusy = false;
let liveOverlayScale = 1;

function initLiveTab() {
  const startBtn = document.getElementById("startLiveBtn");
  const stopBtn = document.getElementById("stopLiveBtn");

  if (startBtn) startBtn.addEventListener("click", startLiveCamera);
  if (stopBtn) stopBtn.addEventListener("click", stopLiveCamera);
}

async function startLiveCamera() {
  const startBtn = document.getElementById("startLiveBtn");
  const stopBtn = document.getElementById("stopLiveBtn");
  const video = document.getElementById("liveVideo");
  const placeholder = document.getElementById("livePlaceholder");

  if (!navigator.mediaDevices?.getUserMedia) {
    showStatus("liveStatusMsg", "API kamera tidak didukung di browser ini.", true);
    return;
  }
  try {
    liveStream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } } });
    video.srcObject = liveStream;
    await video.play().catch(() => {});
    if (placeholder) placeholder.style.display = "none";
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setupLiveOverlaySize();
    showLivePanel(true);
    showStatus("liveStatusMsg", "Kamera aktif. Menganalisis otomatis...");
    startLiveLoop();
  } catch (err) {
    showStatus("liveStatusMsg", `Error kamera: ${err.message}`, true);
  }
}

function setupLiveOverlaySize() {
  const video = document.getElementById("liveVideo");
  const overlay = document.getElementById("liveOverlay");
  if (!overlay || !video || !video.videoWidth) return;
  overlay.width = video.videoWidth;
  overlay.height = video.videoHeight;
}

function startLiveLoop() {
  if (liveAnalyzeTimer || !liveStream) return;
  liveAnalyzeLoop();
  liveAnalyzeTimer = setInterval(liveAnalyzeLoop, LIVE_ANALYZE_INTERVAL_MS);
}

function stopLiveLoop() {
  if (liveAnalyzeTimer) {
    clearInterval(liveAnalyzeTimer);
    liveAnalyzeTimer = null;
  }
}

async function liveAnalyzeLoop() {
  if (liveBusy) return;
  const video = document.getElementById("liveVideo");
  if (!video || !video.videoWidth) return;

  const vw = video.videoWidth;
  const vh = video.videoHeight;
  const scale = Math.min(1, LIVE_MAX_WIDTH / vw);
  const cw = Math.round(vw * scale);
  const ch = Math.round(vh * scale);

  const canvas = document.createElement("canvas");
  canvas.width = cw;
  canvas.height = ch;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, cw, ch);

  const overlay = document.getElementById("liveOverlay");
  liveOverlayScale = overlay && cw ? overlay.width / cw : 1;

  liveBusy = true;
  try {
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/jpeg", 0.85));
    const formData = new FormData();
    formData.append("image", blob, "live-frame.jpg");

    const res = await fetch(`${API_BASE}/api/analyze?light=true`, { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server error ${res.status}`);
    }
    const data = await res.json();
    renderLiveResults(data);
  } catch (err) {
    showStatus("liveStatusMsg", `Analisis langsung gagal: ${err.message}`, true);
  } finally {
    liveBusy = false;
  }
}

function renderLiveResults(data) {
  showLivePanel(true);

  const overlay = document.getElementById("liveOverlay");
  if (overlay) {
    const ctx = overlay.getContext("2d");
    ctx.clearRect(0, 0, overlay.width, overlay.height);
    drawLiveAnnotations(ctx, data, liveOverlayScale);
  }

  const s = data.summary || {};
  setText("liveMetricRisk", `${s.risk_score ?? 0} / 100`);
  setText("liveMetricPersons", s.person_count ?? 0);
  setText("liveMetricViolations", s.violations_count ?? 0);
  setText("liveMetricHazards", s.hazard_count ?? 0);

  const list = document.getElementById("liveResultList");
  if (list) {
    const results = data.results || [];
    list.innerHTML = results.length
      ? results.map((p) => buildPersonCard(p)).join("")
      : `<p class="empty-text">Tidak ada orang terdeteksi.</p>`;
  }
}

function showLivePanel(visible) {
  const panel = document.getElementById("liveResultPanel");
  if (panel) panel.hidden = !visible;
}

function stopLiveCamera() {
  stopLiveLoop();
  if (liveStream) {
    liveStream.getTracks().forEach((t) => t.stop());
    liveStream = null;
  }
  const video = document.getElementById("liveVideo");
  if (video) {
    video.pause();
    video.srcObject = null;
    video.removeAttribute("src");
    video.load();
  }
  const placeholder = document.getElementById("livePlaceholder");
  if (placeholder) placeholder.style.display = "";
  const overlay = document.getElementById("liveOverlay");
  if (overlay) {
    const ctx = overlay.getContext("2d");
    ctx.clearRect(0, 0, overlay.width, overlay.height);
  }
  showLivePanel(false);
  document.getElementById("startLiveBtn").disabled = false;
  document.getElementById("stopLiveBtn").disabled = true;
  showStatus("liveStatusMsg", "Kamera dihentikan.");
}

function drawLiveAnnotations(ctx, data, scale) {
  ctx.lineWidth = 2;
  ctx.font = "12px sans-serif";
  for (const obj of data.all_objects || []) {
    const [x1, y1, x2, y2] = obj.bbox;
    const color = liveCategoryColor(obj.category);
    ctx.strokeStyle = color;
    ctx.strokeRect(x1 * scale, y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale);
    ctx.fillStyle = color;
    const label = `${obj.class_name} ${obj.confidence_percent || ""}`.trim();
    ctx.fillText(label, x1 * scale, Math.max(y1 * scale - 4, 12));
  }
  for (const r of data.results || []) {
    const [x1, y1, x2, y2] = r.person_bbox;
    const color = r.compliance_status === "Compliant" ? "#10b981" : "#f43f5e";
    ctx.strokeStyle = color;
    ctx.lineWidth = 3;
    ctx.strokeRect(x1 * scale, y1 * scale, (x2 - x1) * scale, (y2 - y1) * scale);
  }
}

function liveCategoryColor(category) {
  switch (category) {
    case "hazard": return "#f43f5e";
    case "compliant_ppe": return "#10b981";
    case "person": return "#3b82f6";
    default: return "#f59e0b";
  }
}

// ─────────────────────────────────────────────
// Shared Helpers
// ─────────────────────────────────────────────
function setupDropzone(dropzone, fileInput, accept, onFile) {
  if (!dropzone || !fileInput) return;
  fileInput.accept = accept;

  dropzone.addEventListener("click", () => fileInput.click());
  dropzone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") fileInput.click(); });
  dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.classList.add("dragover"); });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files?.[0]) onFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => { if (fileInput.files[0]) onFile(fileInput.files[0]); });
}

function removeOldPreview(container, className) {
  const old = container?.querySelector(`.${className}`);
  if (old) old.remove();
}

function setButtonLoading(btn, loading, label) {
  if (!btn) return;
  btn.disabled = loading;
  btn.innerHTML = label;
}

function showStatus(id, msg, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.className = "status-msg" + (isError ? " status-msg--error" : "");
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function getCategoryClass(category) {
  switch (category) {
    case "compliant_ppe": return "compliant_ppe";
    case "hazard": return "hazard";
    case "person": return "person";
    default: return "equipment";
  }
}

function escapeHtml(str) {
  if (str == null) return "";
  const div = document.createElement("div");
  div.textContent = String(str);
  return div.innerHTML;
}

function showLoading(show) {
  const overlay = document.getElementById("loadingOverlay");
  if (overlay) overlay.hidden = !show;
}

function updateGaugeChart(id, score) {
  setText(id, `${score}%`);
  const fill = document.getElementById(id.replace("MetricScore", "GaugeFill"));
  if (fill) {
    // Semi-circle with r=40 -> PI * r = 125.66
    const maxDash = 125.66;
    const dash = maxDash - (score / 100) * maxDash;
    fill.style.strokeDashoffset = dash;
    
    if (score >= 80) fill.style.stroke = "var(--ok)";
    else if (score >= 50) fill.style.stroke = "var(--warn)";
    else fill.style.stroke = "var(--bad)";
  }
}
