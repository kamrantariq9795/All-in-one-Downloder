// State
let currentVideoData = null;
let selectedQuality = "best";
let selectedFormat = "video"; // 'video' or 'audio'
let pollInterval = null;
let deferredInstallPrompt = null;

// DOM Elements
const urlForm = document.getElementById("urlForm");
const videoUrlInput = document.getElementById("videoUrl");
const pasteBtn = document.getElementById("pasteBtn");
const fetchBtn = document.getElementById("fetchBtn");
const statusMessage = document.getElementById("statusMessage");

// Preview Elements
const previewCard = document.getElementById("previewCard");
const videoThumbnail = document.getElementById("videoThumbnail");
const thumbnailFallback = document.getElementById("thumbnailFallback");
const platformBadge = document.getElementById("platformBadge");
const noWatermarkBadge = document.getElementById("noWatermarkBadge");
const videoDuration = document.getElementById("videoDuration");
const videoUploader = document.getElementById("videoUploader");
const videoTitle = document.getElementById("videoTitle");
const qualityOptionsList = document.getElementById("qualityOptionsList");
const qualitySelectionContainer = document.getElementById("qualitySelectionContainer");
const formatVideoBtn = document.getElementById("formatVideoBtn");
const formatAudioBtn = document.getElementById("formatAudioBtn");
const startDownloadBtn = document.getElementById("startDownloadBtn");

// Progress Elements
const progressCard = document.getElementById("progressCard");
const progressStatusText = document.getElementById("progressStatusText");
const progressSubText = document.getElementById("progressSubText");
const progressPercentText = document.getElementById("progressPercentText");
const progressBar = document.getElementById("progressBar");
const progressDownloaded = document.getElementById("progressDownloaded");
const progressSpeed = document.getElementById("progressSpeed");
const progressEta = document.getElementById("progressEta");
const completedActions = document.getElementById("completedActions");
const countdownSec = document.getElementById("countdownSec");

// Library Elements
const historyList = document.getElementById("historyList");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const historySection = document.getElementById("historySection");

// Install Elements
const navInstallBtn = document.getElementById("navInstallBtn");
const mobileNavHome = document.getElementById("mobileNavHome");
const mobileNavPaste = document.getElementById("mobileNavPaste");
const mobileNavLibrary = document.getElementById("mobileNavLibrary");
const mobileNavInstall = document.getElementById("mobileNavInstall");
const installGuideModal = document.getElementById("installGuideModal");
const closeInstallModalBtn = document.getElementById("closeInstallModalBtn");
const dismissInstallModalBtn = document.getElementById("dismissInstallModalBtn");
const nativeInstallPromptBtn = document.getElementById("nativeInstallPromptBtn");

// PWA Service Worker Registration
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

// PWA Install Prompt Listener
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
});

function handleInstallClick() {
  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.then(() => {
      deferredInstallPrompt = null;
    });
  }
  installGuideModal.classList.remove("hidden");
}

if (navInstallBtn) navInstallBtn.addEventListener("click", handleInstallClick);
if (mobileNavInstall) mobileNavInstall.addEventListener("click", handleInstallClick);
if (nativeInstallPromptBtn) nativeInstallPromptBtn.addEventListener("click", () => {
  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    deferredInstallPrompt.userChoice.then(() => {
      deferredInstallPrompt = null;
      installGuideModal.classList.add("hidden");
    });
  } else {
    showToast("Mobile Chrome ke top-right 3 dots (⋮) par tap karein aur 'Install app' dabayein.", "info");
  }
});

if (closeInstallModalBtn) closeInstallModalBtn.addEventListener("click", () => installGuideModal.classList.add("hidden"));
if (dismissInstallModalBtn) dismissInstallModalBtn.addEventListener("click", () => installGuideModal.classList.add("hidden"));
installGuideModal.addEventListener("click", (e) => {
  if (e.target === installGuideModal) installGuideModal.classList.add("hidden");
});

// Sound Chime Notification (Web Audio API)
function playCompletionTone() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.36);
  } catch (e) {}
}

// Clipboard Paste
async function handlePaste() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      videoUrlInput.value = text;
      showToast("Link paste ho gaya! Details fetch ho rahi hain...", "info");
      fetchVideoInfo(text);
    }
  } catch (err) {
    showToast("Clipboard permission nahi mili. Aap manually paste karein.", "warning");
  }
}

pasteBtn.addEventListener("click", handlePaste);

// Toast Message
function showToast(msg, type = "info") {
  statusMessage.classList.remove("hidden", "bg-red-500/20", "text-red-300", "border-red-500/40", "bg-emerald-500/20", "text-emerald-300", "border-emerald-500/40", "bg-purple-500/20", "text-purple-200", "border-purple-500/40");
  
  if (type === "error") {
    statusMessage.className = "mt-4 p-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 bg-red-500/20 text-red-300 border border-red-500/40 max-w-lg mx-auto";
    statusMessage.innerHTML = `<i class="fa-solid fa-circle-exclamation text-base"></i> <span>${msg}</span>`;
  } else if (type === "success") {
    statusMessage.className = "mt-4 p-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 max-w-lg mx-auto";
    statusMessage.innerHTML = `<i class="fa-solid fa-circle-check text-base"></i> <span>${msg}</span>`;
  } else {
    statusMessage.className = "mt-4 p-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 bg-purple-500/20 text-purple-200 border border-purple-500/40 max-w-lg mx-auto";
    statusMessage.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-base"></i> <span>${msg}</span>`;
  }
}

function formatDuration(sec) {
  if (!sec || isNaN(sec)) return "";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}

// Fetch Video Info
async function fetchVideoInfo(url) {
  if (!url) return;

  fetchBtn.disabled = true;
  fetchBtn.innerHTML = `<span>Fetching...</span>`;
  showToast("Stream extract ho rahi hai...", "info");
  previewCard.classList.add("hidden");

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url })
    });
    const data = await res.json();

    if (!data.success) {
      showToast(data.error || "Video link check karein ya dobara koshish karein.", "error");
      return;
    }

    currentVideoData = data;
    renderPreview(data);
    statusMessage.classList.add("hidden");
  } catch (err) {
    showToast("Network error: " + err.message, "error");
  } finally {
    fetchBtn.disabled = false;
    fetchBtn.innerHTML = `<span>Download</span>`;
  }
}

// Render Preview Card with Thumbnail Proxy & Fallback
function renderPreview(data) {
  thumbnailFallback.classList.add("hidden");
  videoThumbnail.classList.remove("hidden");

  if (data.thumbnail) {
    const proxyUrl = `/api/thumbnail?url=${encodeURIComponent(data.thumbnail)}`;
    videoThumbnail.src = proxyUrl;
    
    videoThumbnail.onerror = () => {
      if (videoThumbnail.src !== data.thumbnail) {
        videoThumbnail.src = data.thumbnail;
      } else {
        videoThumbnail.classList.add("hidden");
        thumbnailFallback.classList.remove("hidden");
      }
    };
  } else {
    videoThumbnail.classList.add("hidden");
    thumbnailFallback.classList.remove("hidden");
  }

  platformBadge.innerHTML = `<i class="fa-brands fa-${data.platform}"></i> ${data.platform.toUpperCase()}`;
  if (data.has_no_watermark || data.platform === "tiktok") {
    noWatermarkBadge.classList.remove("hidden");
  } else {
    noWatermarkBadge.classList.add("hidden");
  }

  videoDuration.textContent = data.duration ? formatDuration(data.duration) : "HD";
  videoUploader.innerHTML = `<i class="fa-solid fa-circle-user"></i> ${data.uploader || 'Creator'}`;
  videoTitle.textContent = data.title || "Video";

  selectedQuality = "best";
  selectedFormat = "video";
  updateFormatUI();
  renderQualityButtons(data.quality_options || []);

  previewCard.classList.remove("hidden");
  previewCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function renderQualityButtons(options) {
  qualityOptionsList.innerHTML = "";
  const videoOptions = options.filter(o => o.type === "video");
  if (videoOptions.length === 0) {
    videoOptions.push({ label: "Best Available", value: "best" });
  }

  videoOptions.forEach((opt, idx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `quality-pill ${idx === 0 ? 'active' : ''}`;
    btn.innerHTML = `<i class="fa-solid fa-video text-[10px]"></i> <span>${opt.label}</span>`;
    btn.addEventListener("click", () => {
      document.querySelectorAll(".quality-pill").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      selectedQuality = opt.value;
    });
    qualityOptionsList.appendChild(btn);
  });
}

function updateFormatUI() {
  if (selectedFormat === "video") {
    formatVideoBtn.classList.add("active");
    formatAudioBtn.classList.remove("active");
    qualitySelectionContainer.classList.remove("hidden");
    startDownloadBtn.innerHTML = `<i class="fa-solid fa-cloud-arrow-down text-base"></i> <span>Download & Auto-Save Video</span>`;
  } else {
    formatAudioBtn.classList.add("active");
    formatVideoBtn.classList.remove("active");
    qualitySelectionContainer.classList.add("hidden");
    selectedQuality = "mp3";
    startDownloadBtn.innerHTML = `<i class="fa-solid fa-music text-base"></i> <span>Download & Auto-Save MP3</span>`;
  }
}

formatVideoBtn.addEventListener("click", () => {
  selectedFormat = "video";
  selectedQuality = "best";
  updateFormatUI();
});

formatAudioBtn.addEventListener("click", () => {
  selectedFormat = "audio";
  selectedQuality = "mp3";
  updateFormatUI();
});

urlForm.addEventListener("submit", (e) => {
  e.preventDefault();
  const url = videoUrlInput.value.trim();
  if (url) fetchVideoInfo(url);
});

// Auto-Save Trigger to Device Downloads
function triggerAutoSaveToDevice(filename) {
  const fileUrl = `/api/file/${encodeURIComponent(filename)}?attachment=true`;
  const a = document.createElement("a");
  a.href = fileUrl;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  setTimeout(() => document.body.removeChild(a), 1000);

  const iframe = document.createElement("iframe");
  iframe.style.display = "none";
  iframe.src = fileUrl;
  document.body.appendChild(iframe);
  setTimeout(() => document.body.removeChild(iframe), 3000);
}

// Start Download
startDownloadBtn.addEventListener("click", async () => {
  if (!currentVideoData) return;

  startDownloadBtn.disabled = true;
  startDownloadBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin text-base"></i> <span>Starting...</span>`;

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: currentVideoData.url,
        quality: selectedQuality,
        format: selectedFormat,
        title: currentVideoData.title
      })
    });
    const data = await res.json();

    if (!data.success) {
      showToast(data.error || "Download start nahi ho saki.", "error");
      startDownloadBtn.disabled = false;
      updateFormatUI();
      return;
    }

    trackDownloadProgress(data.task_id);
  } catch (err) {
    showToast("Download error: " + err.message, "error");
    startDownloadBtn.disabled = false;
    updateFormatUI();
  }
});

// Track Progress & Auto-Refresh Page
function trackDownloadProgress(taskId) {
  progressCard.classList.remove("hidden");
  completedActions.classList.add("hidden");
  progressCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  progressBar.style.width = "5%";
  progressPercentText.textContent = "5%";
  progressStatusText.textContent = "Downloading stream...";
  progressSubText.textContent = "Server extraction active";

  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/progress/${taskId}`);
      const data = await res.json();

      if (!data.success || !data.task) return;

      const t = data.task;
      const pct = Math.max(t.progress || 0, 5);
      progressBar.style.width = `${pct}%`;
      progressPercentText.textContent = `${t.progress}%`;

      progressDownloaded.textContent = `${t.downloaded || '0 MB'} / ${t.total || '...'}`;
      progressSpeed.textContent = `${t.speed || '0 MB/s'}`;
      progressEta.textContent = `ETA: ${t.eta || '...'}`;

      if (t.status === "downloading") {
        progressStatusText.textContent = "Downloading media stream...";
        progressSubText.textContent = `Speed: ${t.speed || 'Fast'}`;
      } else if (t.status === "processing") {
        progressStatusText.textContent = "Merging Video & Audio (FFmpeg)...";
        progressSubText.textContent = "Finalizing 1080p/4K without watermark...";
        progressBar.style.width = "99%";
        progressPercentText.textContent = "99%";
      } else if (t.status === "finished") {
        clearInterval(pollInterval);
        progressBar.style.width = "100%";
        progressPercentText.textContent = "100%";
        progressStatusText.textContent = "Download Complete!";
        progressSubText.textContent = `Saved: ${t.filename || 'video'}`;

        // Trigger Auto-Save to Device
        triggerAutoSaveToDevice(t.filename);
        playCompletionTone();
        completedActions.classList.remove("hidden");

        // AUTO-REFRESH COUNTDOWN: Refresh page after 3 seconds for next video
        let secondsLeft = 3;
        countdownSec.textContent = secondsLeft;

        const countdownInterval = setInterval(() => {
          secondsLeft--;
          if (countdownSec) countdownSec.textContent = secondsLeft;
          if (secondsLeft <= 0) {
            clearInterval(countdownInterval);
            window.location.reload();
          }
        }, 1000);

      } else if (t.status === "error") {
        clearInterval(pollInterval);
        progressStatusText.textContent = "Download Failed";
        progressSubText.textContent = t.error || "Unknown error";
        progressBar.classList.add("from-red-500", "to-red-700");
        showToast(t.error || "Download error occurred.", "error");
        startDownloadBtn.disabled = false;
        updateFormatUI();
      }
    } catch (e) {
      console.error("Progress error:", e);
    }
  }, 750);
}

// Mobile Bottom Nav
if (mobileNavHome) {
  mobileNavHome.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
}

if (mobileNavPaste) {
  mobileNavPaste.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
    handlePaste();
  });
}

if (mobileNavLibrary) {
  mobileNavLibrary.addEventListener("click", () => {
    historySection.scrollIntoView({ behavior: "smooth" });
  });
}

// Load Download History
async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const data = await res.json();
    if (!data.success) return;

    const files = data.files || [];
    if (files.length === 0) {
      historyList.innerHTML = `
        <div class="text-center py-6 text-slate-500 text-xs">
          <i class="fa-solid fa-inbox text-2xl mb-1.5 block"></i>
          Abhi tak koi video download nahi hui.
        </div>
      `;
      return;
    }

    historyList.innerHTML = "";
    files.forEach(f => {
      const isAudio = f.filename.endsWith(".mp3");
      const icon = isAudio ? "fa-music text-purple-400" : "fa-film text-brand-400";

      const item = document.createElement("div");
      item.className = "flex items-center justify-between p-2.5 sm:p-3 rounded-xl bg-dark-850 border border-slate-800 hover:border-slate-700 transition";
      item.innerHTML = `
        <div class="flex items-center gap-2.5 min-w-0 pr-2">
          <div class="w-8 h-8 rounded-lg bg-dark-800 border border-slate-700 flex items-center justify-center shrink-0">
            <i class="fa-solid ${icon} text-xs"></i>
          </div>
          <div class="min-w-0">
            <h5 class="text-xs font-semibold text-white truncate max-w-[160px] sm:max-w-md" title="${f.filename}">
              ${f.filename}
            </h5>
            <div class="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono mt-0.5">
              <span>${f.size_mb} MB</span>
              <span>•</span>
              <span>${f.created_time}</span>
            </div>
          </div>
        </div>

        <div class="flex items-center gap-1.5 shrink-0">
          <a href="/api/file/${encodeURIComponent(f.filename)}?attachment=true" download class="w-7 h-7 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 flex items-center justify-center transition" title="Download">
            <i class="fa-solid fa-download text-[10px]"></i>
          </a>
        </div>
      `;
      historyList.appendChild(item);
    });
  } catch (err) {}
}

if (refreshHistoryBtn) refreshHistoryBtn.addEventListener("click", loadHistory);
loadHistory();
