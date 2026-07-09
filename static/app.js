/* DigiTech Markdown Converter — drag & drop, upload, preview, download */

(() => {
  "use strict";

  const THEME_STORAGE_KEY = "digi-theme";
  const DEFAULT_THEME = "dark";

  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("file-input");
  const browseBtn = document.getElementById("browse-btn");
  const themeToggle = document.getElementById("theme-toggle");
  const themeIcon = themeToggle.querySelector(".theme-icon");
  const progressSection = document.getElementById("progress-section");
  const progressBar = document.getElementById("progress-bar");
  const progressLabel = document.getElementById("progress-label");
  const resultsList = document.getElementById("results-list");
  const resultsEmpty = document.getElementById("results-empty");
  const backdrop = document.getElementById("backdrop");
  const previewPanel = document.getElementById("preview-panel");
  const previewTitle = document.getElementById("preview-title");
  const previewContent = document.getElementById("preview-content");
  const previewClose = document.getElementById("preview-close");
  const previewDownload = document.getElementById("preview-download");

  let activePreviewId = null;

  /* ---------- Theme ---------- */

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    themeIcon.textContent = theme === "dark" ? "🌙" : "☀️";
  }

  function initTheme() {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    applyTheme(saved === "light" || saved === "dark" ? saved : DEFAULT_THEME);
  }

  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem(THEME_STORAGE_KEY, next);
    applyTheme(next);
  });

  /* ---------- Drag & drop / browse ---------- */

  browseBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener("click", () => fileInput.click());

  dropZone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      uploadFiles(fileInput.files);
      fileInput.value = "";
    }
  });

  ["dragenter", "dragover"].forEach((type) => {
    dropZone.addEventListener(type, (event) => {
      event.preventDefault();
      dropZone.classList.add("drag-over");
    });
  });

  ["dragleave", "drop"].forEach((type) => {
    dropZone.addEventListener(type, (event) => {
      event.preventDefault();
      dropZone.classList.remove("drag-over");
    });
  });

  dropZone.addEventListener("drop", (event) => {
    const files = event.dataTransfer ? event.dataTransfer.files : null;
    if (files && files.length > 0) {
      uploadFiles(files);
    }
  });

  /* ---------- Upload ---------- */

  function uploadFiles(fileList) {
    const formData = new FormData();
    Array.from(fileList).forEach((file) => formData.append("files", file));

    showProgress(fileList.length);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/convert");

    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setProgress(percent, percent < 100 ? `Uploading… ${percent}%` : "Converting…");
      }
    });

    xhr.addEventListener("load", () => {
      hideProgress();
      let payload = null;
      try {
        payload = JSON.parse(xhr.responseText);
      } catch {
        renderUploadError("Server returned an invalid response");
        return;
      }
      if (xhr.status !== 200) {
        renderUploadError(payload.error || `Upload failed (HTTP ${xhr.status})`);
        return;
      }
      payload.files.forEach(addResultItem);
    });

    xhr.addEventListener("error", () => {
      hideProgress();
      renderUploadError("Network error — is the server running?");
    });

    xhr.send(formData);
  }

  function showProgress(fileCount) {
    progressSection.hidden = false;
    setProgress(0, `Uploading ${fileCount} file${fileCount > 1 ? "s" : ""}…`);
  }

  function setProgress(percent, label) {
    progressBar.style.width = `${percent}%`;
    progressLabel.textContent = label;
  }

  function hideProgress() {
    progressSection.hidden = true;
    progressBar.style.width = "0%";
  }

  /* ---------- Results list ---------- */

  function updateEmptyState() {
    resultsEmpty.hidden = resultsList.children.length > 0;
  }

  function renderUploadError(message) {
    addResultItem({
      id: null,
      original_name: "Upload",
      md_name: null,
      status: "error",
      error: message,
    });
  }

  function addResultItem(file) {
    const item = document.createElement("li");
    item.className = "result-item";

    if (file.status !== "ok") {
      item.classList.add("result-error");
      item.append(
        makeSpan("result-icon", "❌"),
        makeSpan("result-name", file.original_name),
        makeSpan("result-error-message", file.error || "Conversion failed")
      );
    } else {
      const previewBtn = makeViewButton(`Preview ${file.md_name}`, () =>
        openPreview(file.id, file.md_name)
      );
      const downloadBtn = makeDownloadButton(`Download ${file.md_name}`, () =>
        downloadFile(file.id, item)
      );
      const actions = document.createElement("span");
      actions.className = "result-actions";
      actions.append(previewBtn, downloadBtn);
      item.dataset.fileId = file.id;
      item.append(
        makeSpan("result-icon", "📄"),
        makeSpan("result-name", file.md_name),
        actions
      );
    }

    resultsList.appendChild(item);
    updateEmptyState();
  }

  function makeSpan(className, text) {
    const span = document.createElement("span");
    span.className = className;
    span.textContent = text;
    return span;
  }

  function makeDownloadButton(label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn-download";
    button.setAttribute("aria-label", label);
    button.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' +
      "<span>Download</span>";
    button.addEventListener("click", onClick);
    return button;
  }

  function makeViewButton(label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn-view";
    button.setAttribute("aria-label", label);
    button.innerHTML =
      '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' +
      "<span>View</span>";
    button.addEventListener("click", onClick);
    return button;
  }

  function makeIconButton(icon, label, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn-icon";
    button.textContent = icon;
    button.setAttribute("aria-label", label);
    button.addEventListener("click", onClick);
    return button;
  }

  /* ---------- Download ---------- */

  function downloadFile(fileId, listItem) {
    const link = document.createElement("a");
    link.href = `/download/${encodeURIComponent(fileId)}`;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    link.remove();

    if (listItem) {
      listItem.remove();
      updateEmptyState();
    }
    if (activePreviewId === fileId) {
      closePreview();
    }
  }

  /* ---------- Preview panel ---------- */

  async function openPreview(fileId, mdName) {
    try {
      const response = await fetch(`/preview/${encodeURIComponent(fileId)}`);
      if (!response.ok) {
        throw new Error(`Preview unavailable (HTTP ${response.status})`);
      }
      const markdown = await response.text();
      previewTitle.textContent = mdName;
      previewContent.innerHTML = marked.parse(markdown);
      activePreviewId = fileId;
      backdrop.hidden = false;
      previewPanel.classList.add("open");
      previewPanel.setAttribute("aria-hidden", "false");
    } catch (error) {
      previewTitle.textContent = mdName;
      previewContent.textContent = error.message;
      backdrop.hidden = false;
      previewPanel.classList.add("open");
      previewPanel.setAttribute("aria-hidden", "false");
    }
  }

  function closePreview() {
    previewPanel.classList.remove("open");
    previewPanel.setAttribute("aria-hidden", "true");
    backdrop.hidden = true;
    activePreviewId = null;
  }

  previewClose.addEventListener("click", closePreview);
  backdrop.addEventListener("click", closePreview);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && activePreviewId !== null) {
      closePreview();
    }
  });

  previewDownload.addEventListener("click", () => {
    if (activePreviewId === null) return;
    const listItem = resultsList.querySelector(
      `[data-file-id="${activePreviewId}"]`
    );
    downloadFile(activePreviewId, listItem);
  });

  /* ---------- Init ---------- */

  initTheme();
  updateEmptyState();
})();
