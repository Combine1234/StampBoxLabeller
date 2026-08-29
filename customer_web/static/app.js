const dropzone = document.querySelector("#dropzone");
const pdfInput = document.querySelector("#pdfInput");
const selectedFile = document.querySelector("#selectedFile");
const startButton = document.querySelector("#startButton");
const resetButton = document.querySelector("#resetButton");
const systemStatus = document.querySelector("#systemStatus");
const phaseText = document.querySelector("#phaseText");
const percentText = document.querySelector("#percentText");
const progressBar = document.querySelector("#progressBar");
const emptyState = document.querySelector("#emptyState");
const resultReady = document.querySelector("#resultReady");
const writtenCount = document.querySelector("#writtenCount");
const totalCount = document.querySelector("#totalCount");
const failedCount = document.querySelector("#failedCount");
const downloadButton = document.querySelector("#downloadButton");
const reportButton = document.querySelector("#reportButton");
const previewSection = document.querySelector("#previewSection");
const previewImage = document.querySelector("#previewImage");
const savedPath = document.querySelector("#savedPath");

let currentFile = null;
let pollTimer = null;

function compactFileName(name) {
  return name
    .normalize("NFKD")
    .toLocaleLowerCase("th")
    .replace(/[^\p{L}\p{N}]+/gu, "");
}

function isProcessedFileName(name) {
  const stem = String(name || "").replace(/\.pdf$/i, "").trim().toLowerCase();
  return compactFileName(name).includes(compactFileName("พร้อมส่งลูกค้า")) || stem.endsWith("_edited");
}

function setProgress(percent, phase) {
  const safePercent = Math.max(0, Math.min(100, Math.round(percent || 0)));
  progressBar.style.width = `${safePercent}%`;
  percentText.textContent = `${safePercent}%`;
  phaseText.textContent = phase || "กำลังทำงาน";
}

function setStatus(text, state = "") {
  systemStatus.textContent = text;
  systemStatus.className = `status-pill ${state}`.trim();
}

function setFile(file) {
  if (!file) return;
  if (isProcessedFileName(file.name)) {
    currentFile = null;
    pdfInput.value = "";
    selectedFile.textContent = file.name;
    startButton.disabled = true;
    resetButton.disabled = false;
    hideResult();
    setProgress(0, "กรุณาเลือก PDF ต้นฉบับที่ยังไม่ได้เขียนโค้ด");
    setStatus("ไฟล์นี้ทำแล้ว", "error");
    return;
  }
  currentFile = file;
  selectedFile.textContent = file.name;
  startButton.disabled = false;
  resetButton.disabled = false;
  hideResult();
  setProgress(0, "พร้อมเริ่มทำไฟล์");
  setStatus("พร้อมทำไฟล์");
}

function resetAll() {
  currentFile = null;
  pdfInput.value = "";
  selectedFile.textContent = "";
  startButton.disabled = true;
  resetButton.disabled = true;
  startButton.textContent = "เริ่มทำไฟล์";
  stopPolling();
  hideResult();
  setProgress(0, "รอไฟล์ PDF");
  setStatus("พร้อมใช้งาน");
}

function hideResult() {
  emptyState.classList.remove("hidden");
  resultReady.classList.add("hidden");
  previewSection.classList.add("hidden");
  previewImage.removeAttribute("src");
  savedPath.textContent = "";
}

function showResult(job) {
  emptyState.classList.add("hidden");
  resultReady.classList.remove("hidden");
  writtenCount.textContent = job.written ?? 0;
  totalCount.textContent = job.total ?? 0;
  failedCount.textContent = job.failed ?? 0;
  downloadButton.href = job.download_url;
  downloadButton.download = job.file_name || "labels_ready.pdf";
  reportButton.href = job.report_url;
  previewImage.src = `${job.preview_url}?t=${Date.now()}`;
  savedPath.textContent = job.file_name || "";
  previewSection.classList.remove("hidden");
}

function triggerDownload(job) {
  if (!job.download_url) return;
  const link = document.createElement("a");
  link.href = job.download_url;
  link.download = job.file_name || "stampbox_ready.pdf";
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function readJsonOrThrow(response, fallbackMessage) {
  let payload = {};
  try {
    payload = await response.json();
  } catch (error) {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(payload.error || fallbackMessage);
  }
  return payload;
}

async function pollJob(jobId) {
  const response = await fetch(`/api/jobs/${jobId}`);
  const job = await readJsonOrThrow(response, "อ่านสถานะไม่สำเร็จ");
  setProgress(job.percent, job.phase);

  if (job.status === "done") {
    stopPolling();
    startButton.disabled = false;
    startButton.innerHTML = '<span class="button-icon" aria-hidden="true">↗</span>ทำอีกครั้ง';
    setStatus("เสร็จแล้ว", "done");
    showResult(job);
    triggerDownload(job);
    return;
  }

  if (job.status === "error") {
    stopPolling();
    startButton.disabled = false;
    startButton.innerHTML = '<span class="button-icon" aria-hidden="true">↗</span>ลองใหม่';
    setStatus("ไม่สำเร็จ", "error");
    phaseText.textContent = job.error || "ทำงานไม่สำเร็จ";
  }
}

async function startJob() {
  if (!currentFile) return;

  hideResult();
  startButton.disabled = true;
  resetButton.disabled = true;
  startButton.textContent = "กำลังทำงาน";
  setStatus("กำลังทำงาน", "running");
  setProgress(2, "กำลังอัปโหลด");

  const formData = new FormData();
  formData.append("pdf", currentFile);

  try {
    const response = await fetch("/api/jobs", {
      method: "POST",
      body: formData,
    });
    const payload = await readJsonOrThrow(response, "เริ่มงานไม่สำเร็จ");

    pollTimer = window.setInterval(() => {
      pollJob(payload.job_id).catch((error) => {
        stopPolling();
        setStatus("ไม่สำเร็จ", "error");
        phaseText.textContent = error.message;
        startButton.disabled = false;
        resetButton.disabled = false;
      });
    }, 700);
    await pollJob(payload.job_id);
  } catch (error) {
    setStatus("ไม่สำเร็จ", "error");
    phaseText.textContent = error.message;
    startButton.disabled = false;
    resetButton.disabled = false;
  }
}

pdfInput.addEventListener("change", () => {
  setFile(pdfInput.files?.[0]);
});

dropzone.addEventListener("dragenter", (event) => {
  event.preventDefault();
  dropzone.classList.add("dragging");
});

dropzone.addEventListener("dragover", (event) => {
  event.preventDefault();
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragging");
});

dropzone.addEventListener("drop", (event) => {
  event.preventDefault();
  dropzone.classList.remove("dragging");
  const file = event.dataTransfer.files?.[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    setStatus("เลือก PDF เท่านั้น", "error");
    return;
  }
  setFile(file);
});

startButton.addEventListener("click", startJob);
resetButton.addEventListener("click", resetAll);
