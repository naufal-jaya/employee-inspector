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
    });
  });

  initImageTab();
  initVideoTab();
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
}

function handleImageSelect(file) {
  if (!file || !file.type.startsWith("image/")) {
    showStatus("imageStatusMsg", "Please select a valid image file.", true);
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

  setButtonLoading(analyzeBtn, true, "Analyzing...");
  showStatus("imageStatusMsg", "Running inference & safety rules...");
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
    showStatus("imageStatusMsg", `Analysis failed: ${err.message}`, true);
  } finally {
    setButtonLoading(analyzeBtn, false, '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg> Analyze Image');
  }
}

function renderImageResults(data) {
  const resultPanel = document.getElementById("imageResultPanel");
  if (resultPanel) resultPanel.hidden = false;

  const annotatedImage = document.getElementById("annotatedImage");
  if (annotatedImage && data.annotated_image) annotatedImage.src = data.annotated_image;

  const s = data.summary || {};
  setText("imgMetricScore", `${s.safety_score ?? 0}%`);
  setText("imgMetricObjects", s.total_objects ?? 0);
  setText("imgMetricPersons", s.person_count ?? 0);
  setText("imgMetricViolations", s.violations_count ?? 0);

  const econ = data.economics || {};
  setText("imgMetricRisk", `${s.risk_score ?? econ.risk_score ?? 0} / 100`);
  setText("imgMetricLoss", formatIDR(econ.estimated_loss_per_incident));
  setText("imgMetricSavings", formatIDR(econ.potential_savings));

  const allObjects = data.all_objects || [];
  setText("imgObjectCount", `${allObjects.length} item${allObjects.length !== 1 ? "s" : ""}`);
  const objectsGrid = document.getElementById("imgObjectsGrid");
  if (objectsGrid) {
    objectsGrid.innerHTML = allObjects.length
      ? allObjects.map((obj) => `
        <div class="object-chip object-chip--${getCategoryClass(obj.category)}">
          <div class="object-chip__header">
            <span class="object-chip__name">${escapeHtml(obj.class_name)}</span>
            <span class="object-chip__conf">${obj.confidence_percent || `${(obj.confidence * 100).toFixed(1)}%`}</span>
          </div>
          <div class="object-chip__meta">${obj.category}</div>
        </div>`).join("")
      : `<p class="empty-text">No objects detected.</p>`;
  }

  const resultList = document.getElementById("imgResultList");
  if (resultList) {
    const results = data.results || [];
    resultList.innerHTML = results.length
      ? results.map((p) => buildPersonCard(p)).join("")
      : `<p class="empty-text">No persons detected.</p>`;
  }
}

function buildPersonCard(person) {
  const isCompliant = person.compliance_status === "Compliant";
  const missingHtml = person.missing_ppe?.length
    ? person.missing_ppe.map((i) => `<span class="badge badge--bad">${escapeHtml(i)}</span>`).join(" ")
    : `<span class="badge badge--ok">None</span>`;
  const presentHtml = person.detected_ppe?.length
    ? person.detected_ppe.map((i) => `<span class="badge badge--ok">${escapeHtml(i)}</span>`).join(" ")
    : `<span class="badge badge--muted">None detected</span>`;
  return `
    <div class="result-card ${isCompliant ? "compliant" : "non-compliant"}">
      <div class="result-card__title">
        <span>Worker #${person.person_id}</span>
        <span class="badge ${isCompliant ? "badge--ok" : "badge--bad"}">${isCompliant ? "COMPLIANT" : "VIOLATION"}</span>
      </div>
      <div class="result-card__meta">
        <span>✔ Present: ${presentHtml}</span>
        <span>✘ Missing: ${missingHtml}</span>
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
    showStatus("videoStatusMsg", "Please select a valid video file (MP4, WebM, AVI, MOV).", true);
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

  setButtonLoading(analyzeBtn, true, "Processing — this may take a while...");
  showStatus("videoStatusMsg", "⏳ Sending video to server for full frame-by-frame analysis...");
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
    showStatus("videoStatusMsg", `Video analysis failed: ${err.message}`, true);
  } finally {
    setButtonLoading(analyzeBtn, false, '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg> Process Video');
  }
}

function renderVideoResults(data) {
  const resultPanel = document.getElementById("videoResultPanel");
  if (resultPanel) resultPanel.hidden = false;

  // Video player
  const videoEl = document.getElementById("annotatedVideo");
  if (videoEl && data.video_url) {
    videoEl.src = `${API_BASE}${data.video_url}`;
    videoEl.load();
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
      : `<p class="empty-text">No persons tracked in this video.</p>`;
  }
}

function buildTemporalCard(worker) {
  const compliantPct = worker.compliance_rate ?? 0;
  const violationPct = Math.max(0, 100 - compliantPct).toFixed(1);
  const isFullyCompliant = worker.violation_seconds === 0;

  const primaryViolationHtml = worker.primary_violation
    ? `<span>Primary violation: <span class="badge badge--bad">${escapeHtml(worker.primary_violation)}</span></span>`
    : `<span class="badge badge--ok">No violations detected</span>`;

  return `
    <div class="result-card ${isFullyCompliant ? "compliant" : "non-compliant"}">
      <div class="result-card__title">
        <span>Worker #${worker.track_id}</span>
        <span class="badge ${isFullyCompliant ? "badge--ok" : "badge--bad"}">${compliantPct.toFixed(1)}% Compliant</span>
      </div>
      <div class="time-bar-wrap">
        <div class="time-bar">
          <div class="time-bar__fill time-bar__fill--ok" style="width:${compliantPct}%" title="Compliant: ${worker.compliant_seconds}s"></div>
          <div class="time-bar__fill time-bar__fill--bad" style="width:${violationPct}%" title="Violation: ${worker.violation_seconds}s"></div>
        </div>
        <div class="time-bar__labels">
          <span>✔ ${worker.compliant_seconds}s compliant</span>
          <span>✘ ${worker.violation_seconds}s violation</span>
        </div>
      </div>
      <div class="result-card__meta">${primaryViolationHtml}</div>
    </div>`;
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

function formatIDR(value) {
  const n = Number(value) || 0;
  if (n === 0) return "Rp 0";
  return "Rp " + n.toLocaleString("id-ID");
}
