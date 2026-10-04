/**
 * Data Processing Tool - Client Application
 * Vanilla JS logic for file selection, drag-and-drop, API submission, and report rendering.
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const dropZone = document.getElementById("dropZone");
  const fileInput = document.getElementById("fileInput");
  const selectedFileInfo = document.getElementById("selectedFileInfo");
  const fileNameDisplay = document.getElementById("fileNameDisplay");
  const fileSizeDisplay = document.getElementById("fileSizeDisplay");
  const clearFileBtn = document.getElementById("clearFileBtn");
  const processBtn = document.getElementById("processBtn");
  const processBtnText = document.getElementById("processBtnText");
  const processSpinner = document.getElementById("processSpinner");
  const loadDemoBtn = document.getElementById("loadDemoBtn");

  const statusBanner = document.getElementById("statusBanner");
  const statusMessage = document.getElementById("statusMessage");
  const dismissStatusBtn = document.getElementById("dismissStatusBtn");

  const resultsSection = document.getElementById("resultsSection");
  const reportFileLabel = document.getElementById("reportFileLabel");
  const newFileBtn = document.getElementById("newFileBtn");

  const metricRowsInitial = document.getElementById("metricRowsInitial");
  const metricRowsFinal = document.getElementById("metricRowsFinal");
  const metricDuplicates = document.getElementById("metricDuplicates");
  const metricEmptyRows = document.getElementById("metricEmptyRows");
  const metricNormalized = document.getElementById("metricNormalized");
  const metricIssues = document.getElementById("metricIssues");

  const changesList = document.getElementById("changesList");
  const warningsList = document.getElementById("warningsList");

  const downloadCsvBtn = document.getElementById("downloadCsvBtn");
  const downloadXlsxBtn = document.getElementById("downloadXlsxBtn");

  const previewTableHead = document.getElementById("previewTableHead");
  const previewTableBody = document.getElementById("previewTableBody");
  const previewMeta = document.getElementById("previewMeta");

  // State
  let currentFile = null;
  const MAX_SIZE_MB = 15;
  const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
  const ALLOWED_EXTS = [".csv", ".xlsx"];

  // Helpers
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function showStatus(message, type = "error") {
    statusBanner.className = `status-banner ${type}`;
    statusMessage.textContent = message;
    statusBanner.style.display = "flex";
  }

  function hideStatus() {
    statusBanner.style.display = "none";
  }

  function validateSelectedFile(file) {
    if (!file) return false;

    const lowerName = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTS.some(ext => lowerName.endsWith(ext));
    if (!hasValidExt) {
      showStatus(`Unsupported format for '${file.name}'. Only .csv and .xlsx files are supported.`, "error");
      return false;
    }

    if (file.size === 0) {
      showStatus("Selected file is empty (0 bytes).", "error");
      return false;
    }

    if (file.size > MAX_SIZE_BYTES) {
      showStatus(`File exceeds maximum allowed size of ${MAX_SIZE_MB} MB.`, "error");
      return false;
    }

    return true;
  }

  function setFile(file) {
    if (!validateSelectedFile(file)) {
      clearFile();
      return;
    }

    currentFile = file;
    fileNameDisplay.textContent = file.name;
    fileSizeDisplay.textContent = formatBytes(file.size);
    selectedFileInfo.style.display = "flex";
    processBtn.disabled = false;
    hideStatus();
  }

  function clearFile() {
    currentFile = null;
    fileInput.value = "";
    selectedFileInfo.style.display = "none";
    processBtn.disabled = true;
  }

  // Drag and Drop Events
  ["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.add("dragover");
    }, false);
  });

  ["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropZone.classList.remove("dragover");
    }, false);
  });

  dropZone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      setFile(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      setFile(e.target.files[0]);
    }
  });

  clearFileBtn.addEventListener("click", () => {
    clearFile();
    hideStatus();
  });

  dismissStatusBtn.addEventListener("click", () => {
    hideStatus();
  });

  newFileBtn.addEventListener("click", () => {
    resultsSection.style.display = "none";
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // Process Dataset
  async function submitProcessing(fileToProcess) {
    if (!fileToProcess) return;

    // Loading state
    processBtn.disabled = true;
    processBtnText.textContent = "Processing...";
    processSpinner.style.display = "inline-block";
    hideStatus();

    const formData = new FormData();
    formData.append("file", fileToProcess);

    try {
      const response = await fetch("/api/process", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        const errorDetail = data.detail || "An unexpected error occurred during processing.";
        showStatus(errorDetail, "error");
        return;
      }

      renderResults(data);
      showStatus(`Dataset processed successfully in ${data.metrics.processing_time_ms} ms.`, "success");
    } catch (err) {
      showStatus(`Connection error: ${err.message}`, "error");
    } finally {
      processBtn.disabled = false;
      processBtnText.textContent = "Process Dataset";
      processSpinner.style.display = "none";
    }
  }

  processBtn.addEventListener("click", () => {
    if (currentFile) {
      submitProcessing(currentFile);
    }
  });

  // Load Demo Dataset Helper
  loadDemoBtn.addEventListener("click", async () => {
    try {
      loadDemoBtn.disabled = true;
      loadDemoBtn.textContent = "Loading Demo...";

      const response = await fetch("/demo-data/customers_messy.csv");
      if (!response.ok) {
        throw new Error("Could not load sample file from server.");
      }

      const blob = await response.blob();
      const demoFile = new File([blob], "customers_messy.csv", { type: "text/csv" });
      setFile(demoFile);
      showStatus("Sample business dataset loaded. Click 'Process Dataset' to clean it.", "info");
    } catch (err) {
      showStatus(`Unable to load demo dataset: ${err.message}`, "error");
    } finally {
      loadDemoBtn.disabled = false;
      loadDemoBtn.textContent = "Load Demo Dataset (customers_messy.csv)";
    }
  });

  // Render Report & Preview Table
  function renderResults(result) {
    reportFileLabel.textContent = `File: ${result.original_filename} &bull; Processed in ${result.metrics.processing_time_ms} ms`;

    // Metrics
    metricRowsInitial.textContent = result.metrics.rows_initial.toLocaleString();
    metricRowsFinal.textContent = result.metrics.rows_final.toLocaleString();
    metricDuplicates.textContent = result.metrics.duplicate_rows_removed.toLocaleString();
    metricEmptyRows.textContent = result.metrics.rows_removed_empty.toLocaleString();
    metricNormalized.textContent = result.metrics.fields_normalized.toLocaleString();
    metricIssues.textContent = result.metrics.invalid_values_detected.toLocaleString();

    // Audit Changes
    changesList.innerHTML = "";
    if (result.changes_summary && result.changes_summary.length > 0) {
      result.changes_summary.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        changesList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.className = "empty-state";
      li.textContent = "No modifications were required for this dataset.";
      changesList.appendChild(li);
    }

    // Quality Warnings
    warningsList.innerHTML = "";
    if (result.warnings && result.warnings.length > 0) {
      result.warnings.forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        warningsList.appendChild(li);
      });
    } else {
      const li = document.createElement("li");
      li.className = "empty-state";
      li.textContent = "No data-quality warnings flagged.";
      warningsList.appendChild(li);
    }

    // Downloads
    downloadCsvBtn.href = result.csv_download_url;
    downloadXlsxBtn.href = result.xlsx_download_url;

    // Table Preview
    renderTablePreview(result.columns, result.sample_preview);

    // Show Results Card & Scroll to it
    resultsSection.style.display = "block";
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function renderTablePreview(columns, rows) {
    previewTableHead.innerHTML = "";
    previewTableBody.innerHTML = "";

    if (!columns || columns.length === 0) {
      previewMeta.textContent = "No columns available";
      return;
    }

    previewMeta.textContent = `Showing first ${rows.length} records &bull; ${columns.length} columns`;

    // Header row
    const trHead = document.createElement("tr");
    columns.forEach(col => {
      const th = document.createElement("th");
      th.textContent = col;
      trHead.appendChild(th);
    });
    previewTableHead.appendChild(trHead);

    // Body rows
    rows.forEach(row => {
      const tr = document.createElement("tr");
      columns.forEach(col => {
        const td = document.createElement("td");
        const val = row[col];
        if (val === null || val === undefined || val === "") {
          td.innerHTML = '<span class="null-cell">&mdash;</span>';
        } else {
          td.textContent = String(val);
        }
        tr.appendChild(td);
      });
      previewTableBody.appendChild(tr);
    });
  }
});
