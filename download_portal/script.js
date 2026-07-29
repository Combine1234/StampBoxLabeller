const platformLabels = {
  windows: "Windows",
  "mac-arm": "Mac Apple Silicon",
  "mac-intel": "Mac Intel",
};

const deviceHint = document.querySelector("#device-hint");
const toast = document.querySelector("#download-toast");
const year = document.querySelector("#year");

function detectPlatform() {
  const userAgent = navigator.userAgent.toLowerCase();
  const platform = (navigator.userAgentData?.platform || navigator.platform || "").toLowerCase();

  if (platform.includes("win") || userAgent.includes("windows")) {
    return "windows";
  }

  if (platform.includes("mac") || userAgent.includes("macintosh")) {
    return "mac-arm";
  }

  return null;
}

function markRecommendedPlatform() {
  const platform = detectPlatform();

  if (!platform) {
    deviceHint.textContent = "เลือกเวอร์ชันให้ตรงกับเครื่องของคุณ";
    return;
  }

  const card = document.querySelector(`[data-platform="${platform}"]`);
  if (card) {
    card.classList.add("recommended");
  }

  if (platform === "mac-arm") {
    deviceHint.textContent = "ตรวจพบ macOS — เช็กชนิดชิปก่อนดาวน์โหลด";
    return;
  }

  deviceHint.textContent = `แนะนำ: ${platformLabels[platform]}`;
}

function showDownloadToast(platform) {
  toast.querySelector("span").textContent =
    `กำลังเปิด Google Drive สำหรับ ${platformLabels[platform]}...`;
  toast.classList.add("visible");

  window.setTimeout(() => {
    toast.classList.remove("visible");
  }, 2800);
}

document.querySelectorAll("[data-download]").forEach((link) => {
  link.addEventListener("click", () => {
    showDownloadToast(link.dataset.download);
  });
});

year.textContent = new Date().getFullYear();
markRecommendedPlatform();

if (window.lucide) {
  window.lucide.createIcons();
}
