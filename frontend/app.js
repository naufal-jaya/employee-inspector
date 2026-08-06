const API_BASE = window.location.hostname === "localhost"
  ? "http://localhost:8000"
  : `http://${window.location.hostname}:8000`;

let selectedFile = null;

document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("fileInput");
  const dropzone = document.getElementById("dropzone");
  const dropzoneLabel = document.getElementById("dropzoneLabel");
  const analyzeBtn = document.getElementById("analyzeBtn");

  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer.files && e.dataTransfer.files.length) {
        handleFileSelect(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files.length) {
        handleFileSelect(fileInput.files[0]);
      }
    });
  }

  if (analyzeBtn) {
    analyzeBtn.addEventListener("click", analyzeImage);
  }
});

function handleFileSelect(file) {
  const dropzone = document.getElementById("dropzone");
  const dropzoneLabel = document.getElementById("dropzoneLabel");
  const analyzeBtn = document.getElementById("analyzeBtn");

  if (!file || !file.type.startsWith("image/")) {
    showStatus("Please select a valid image file.", true);
    return;
  }
  selectedFile = file;
  if (analyzeBtn) analyzeBtn.disabled = false;
  showStatus("");

  const reader = new FileReader();
  reader.onload = (e) => {
    if (dropzoneLabel) dropzoneLabel.style.display = "none";
    if (dropzone) {
      const oldPreview = dropzone.querySelector(".upload-preview");
      if (oldPreview) oldPreview.remove();

      const preview = document.createElement("img");
      preview.src = e.target.result;
      preview.className = "upload-preview";
      dropzone.appendChild(preview);
    }
  };
  reader.readAsDataURL(file);
}

async function analyzeImage() {
  const analyzeBtn = document.getElementById("analyzeBtn");
  const resultPanel = document.getElementById("resultPanel");

  if (!selectedFile) return;

  if (analyzeBtn) {
    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
  }
  showStatus("Processing inference & safety rules...");
  if (resultPanel) resultPanel.hidden = true;

  try {
    const formData = new FormData();
    formData.append("image", selectedFile);

    const res = await fetch(`${API_BASE}/api/analyze`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server returned status ${res.status}`);
    }

    const data = await res.json();
    renderResults(data);
    showStatus("");
  } catch (err) {
    showStatus(`Analysis failed: ${err.message}`, true);
  } finally {
    if (analyzeBtn) {
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = "Analyze Image";
    }
  }
}

function showStatus(msg, isError = false) {
  const statusMsg = document.getElementById("statusMsg");
  if (statusMsg) {
    statusMsg.textContent = msg;
    statusMsg.className = "status-msg" + (isError ? " status-msg--error" : "");
  }
}

function renderResults(data) {
  const resultPanel = document.getElementById("resultPanel");
  const annotatedImage = document.getElementById("annotatedImage");
  const metricScore = document.getElementById("metricScore");
  const metricObjects = document.getElementById("metricObjects");
  const metricPersons = document.getElementById("metricPersons");
  const metricViolations = document.getElementById("metricViolations");
  const objectsGrid = document.getElementById("objectsGrid");
  const resultList = document.getElementById("resultList");

  if (resultPanel) resultPanel.hidden = false;
  if (annotatedImage && data.annotated_image) {
    annotatedImage.src = data.annotated_image;
  }

  // Summary Metrics
  const summary = data.summary || {};
  if (metricScore) {
    metricScore.textContent = (summary.person_count ?? 0) > 0 ? `${summary.safety_score ?? 0}%` : "—";
  }
  if (metricObjects) metricObjects.textContent = summary.total_objects ?? 0;
  if (metricPersons) metricPersons.textContent = summary.person_count ?? 0;
  if (metricViolations) metricViolations.textContent = summary.violations_count ?? 0;


  // All Detected Objects Chips
  if (objectsGrid) {
    objectsGrid.innerHTML = "";
    const allObjects = data.all_objects || [];
    if (allObjects.length === 0) {
      objectsGrid.innerHTML = '<span class="empty-msg">No objects detected.</span>';
    } else {
      allObjects.forEach((obj) => {
        const chip = document.createElement("div");
        chip.className = `object-chip object-chip--${getCategoryClass(obj.category)}`;
        chip.innerHTML = `
          <span class="chip-name">${escapeHtml(obj.class_name)}</span>
          <span class="chip-conf">${obj.confidence_percent || `${(obj.confidence * 100).toFixed(1)}%`}</span>
        `;
        objectsGrid.appendChild(chip);
      });
    }
  }

  // Worker Compliance Breakdown
  if (resultList) {
    resultList.innerHTML = "";
    const results = data.results || [];
    if (results.length === 0) {
      resultList.innerHTML = '<p class="empty-msg">No persons detected in this image.</p>';
      return;
    }

    results.forEach((person) => {
      const card = document.createElement("div");
      const isCompliant = person.compliance_status === "Compliant";
      card.className = `person-card ${isCompliant ? "person-card--compliant" : "person-card--violation"}`;

      const missingPpeHtml = person.missing_ppe.length
        ? person.missing_ppe.map((item) => `<span class="badge badge--bad">${escapeHtml(item)}</span>`).join(" ")
        : '<span class="badge badge--ok">None</span>';

      const presentPpeHtml = person.detected_ppe.length
        ? person.detected_ppe.map((item) => `<span class="badge badge--ok">${escapeHtml(item)}</span>`).join(" ")
        : '<span class="badge badge--muted">None</span>';

      const advisory = isCompliant
        ? "Worker fully complies with safety SOP."
        : `Action required: Missing ${person.missing_ppe.join(", ")}.`;

      card.innerHTML = `
        <div class="person-card__header">
          <strong class="person-title">Person #${person.person_id}</strong>
          <span class="badge ${isCompliant ? "badge--ok" : "badge--bad"}">
            ${isCompliant ? "COMPLIANT" : "NON-COMPLIANT"}
          </span>
        </div>
        <div class="person-card__details">
          <p><strong>Detected PPE:</strong> ${presentPpeHtml}</p>
          <p><strong>Missing PPE:</strong> ${missingPpeHtml}</p>
          <p class="advisory-text"><strong>Advisory:</strong> ${advisory}</p>
        </div>
      `;
      resultList.appendChild(card);
    });
  }
}

function getCategoryClass(category) {
  switch (category) {
    case "compliant_ppe": return "ok";
    case "hazard": return "bad";
    case "person": return "person";
    default: return "equipment";
  }
}

function escapeHtml(str) {
  if (str === undefined || str === null) return "";
  const div = document.createElement("div");
  div.textContent = String(str);
  return div.innerHTML;
}
