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
const previewSection = document.querySelector("#previewSection");
const previewFrame = document.querySelector("#previewFrame");
const savedPath = document.querySelector("#savedPath");

let currentFile = null;
let progressTimer = null;
let currentPdfUrl = "";

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
  stopProgress();
  hideResult();
  setProgress(0, "รอไฟล์ PDF");
  setStatus("พร้อมใช้งาน");
}

function stopProgress() {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

function hideResult() {
  emptyState.classList.remove("hidden");
  resultReady.classList.add("hidden");
  previewSection.classList.add("hidden");
  previewFrame.removeAttribute("src");
  savedPath.textContent = "";
  if (currentPdfUrl) {
    URL.revokeObjectURL(currentPdfUrl);
    currentPdfUrl = "";
  }
}

function startSoftProgress() {
  let percent = 8;
  setProgress(percent, "กำลังอัปโหลดไฟล์");
  progressTimer = window.setInterval(() => {
    percent = Math.min(percent + Math.max(1, Math.round((90 - percent) * 0.12)), 90);
    const phase = percent < 35 ? "กำลังอ่านรายการสินค้า" : percent < 70 ? "กำลังเขียนโค้ดลงใบปะหน้า" : "กำลังเตรียมไฟล์ PDF";
    setProgress(percent, phase);
    if (percent >= 90) {
      stopProgress();
    }
  }, 700);
}

function filenameFromResponse(response) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/i);
  return match ? match[1] : "stampbox_output.pdf";
}

async function startJob() {
  if (!currentFile) return;

  hideResult();
  startButton.disabled = true;
  resetButton.disabled = true;
  startButton.textContent = "กำลังทำงาน";
  setStatus("กำลังทำงาน", "running");
  startSoftProgress();

  const formData = new FormData();
  formData.append("pdf", currentFile);

  try {
    const response = await fetch("/api/process", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let message = "ทำไฟล์ไม่สำเร็จ";
      try {
        const payload = await response.json();
        message = payload.error || message;
      } catch (_) {
        message = await response.text();
      }
      throw new Error(message);
    }

    const blob = await response.blob();
    const fileName = filenameFromResponse(response);
    currentPdfUrl = URL.createObjectURL(blob);

    writtenCount.textContent = response.headers.get("X-Stampbox-Written") || "0";
    totalCount.textContent = response.headers.get("X-Stampbox-Total") || "0";
    failedCount.textContent = response.headers.get("X-Stampbox-Failed") || "0";

    downloadButton.href = currentPdfUrl;
    downloadButton.download = fileName;
    previewFrame.src = currentPdfUrl;
    savedPath.textContent = fileName;

    stopProgress();
    setProgress(100, "เสร็จแล้ว");
    setStatus("เสร็จแล้ว", "done");
    emptyState.classList.add("hidden");
    resultReady.classList.remove("hidden");
    previewSection.classList.remove("hidden");
    startButton.disabled = false;
    resetButton.disabled = false;
    startButton.textContent = "ทำอีกครั้ง";
  } catch (error) {
    stopProgress();
    setProgress(100, "ทำงานไม่สำเร็จ");
    setStatus("ไม่สำเร็จ", "error");
    phaseText.textContent = error.message;
    startButton.disabled = false;
    resetButton.disabled = false;
    startButton.textContent = "ลองใหม่";
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
