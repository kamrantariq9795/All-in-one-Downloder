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
const detectedIcon = document.getElementById("detectedIcon");
const statusMessage = document.getElementById("statusMessage");
const autoSaveToggle = document.getElementById("autoSaveToggle");

// Preview Elements
const previewCard = document.getElementById("previewCard");
const videoThumbnail = document.getElementById("videoThumbnail");
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
const browserDownloadBtn = document.getElementById("browserDownloadBtn");
const quickOpenFolderBtn = document.getElementById("quickOpenFolderBtn");

// Library Elements
const historyList = document.getElementById("historyList");
const historyBadge = document.getElementById("historyBadge");
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const openFolderBtn = document.getElementById("openFolderBtn");
const historyTabBtn = document.getElementById("historyTabBtn");
const historySection = document.getElementById("historySection");

// Mobile Elements
const pwaInstallBtn = document.getElementById("pwaInstallBtn");
const mobileInstallBanner = document.getElementById("mobileInstallBanner");
const mobileInstallActionBtn = document.getElementById("mobileInstallActionBtn");
const mobileNavHome = document.getElementById("mobileNavHome");
const mobileNavPaste = document.getElementById("mobileNavPaste");
const mobileNavLibrary = document.getElementById("mobileNavLibrary");
const mobileNavInstall = document.getElementById("mobileNavInstall");

// Modal Elements
const videoModal = document.getElementById("videoModal");
const modalVideoPlayer = document.getElementById("modalVideoPlayer");
const modalVideoTitle = document.getElementById("modalVideoTitle");
const closeModalBtn = document.getElementById("closeModalBtn");

// PWA Service Worker Registration
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  });
}

// PWA Install Prompt Handler
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  if (pwaInstallBtn) pwaInstallBtn.classList.remove("hidden");
  if (mobileInstallBanner) mobileInstallBanner.classList.remove("hidden");
});

async function triggerInstallPrompt() {
  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    const { outcome } = await deferredInstallPrompt.userChoice;
    if (outcome === "accepted") {
      if (pwaInstallBtn) pwaInstallBtn.classList.add("hidden");
      if (mobileInstallBanner) mobileInstallBanner.classList.add("hidden");
    }
    deferredInstallPrompt = null;
  } else {
    showToast("Mobile browser ke menu (3 dots) par click karein aur 'Install App' ya 'Add to Home Screen' select karein.", "info");
  }
}

if (pwaInstallBtn) pwaInstallBtn.addEventListener("click", triggerInstallPrompt);
if (mobileInstallActionBtn) mobileInstallActionBtn.addEventListener("click", triggerInstallPrompt);
if (mobileNavInstall) mobileNavInstall.addEventListener("click", triggerInstallPrompt);

// Sound Chime Notification (Web Audio API)
function playCompletionTone() {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, ctx.currentTime); // D5
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.12); // A5
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.36);
  } catch (e) {}
}

// Platform Detection Helper
function detectPlatformFromUrl(url) {
  const u = (url || "").toLowerCase();
  if (u.includes("tiktok.com")) return { name: "TikTok", icon: "fa-brands fa-tiktok text-pink-400", nowm: true };
  if (u.includes("youtube.com") || u.includes("youtu.be")) return { name: "YouTube", icon: "fa-brands fa-youtube text-red-500", nowm: false };
  if (u.includes("instagram.com")) return { name: "Instagram", icon: "fa-brands fa-instagram text-pink-500", nowm: true };
  if (u.includes("facebook.com") || u.includes("fb.watch") || u.includes("fb.com")) return { name: "Facebook", icon: "fa-brands fa-facebook text-blue-500", nowm: true };
  if (u.includes("twitter.com") || u.includes("x.com")) return { name: "Twitter / X", icon: "fa-brands fa-x-twitter text-slate-200", nowm: true };
  if (u.includes("pinterest.com") || u.includes("pin.it")) return { name: "Pinterest", icon: "fa-brands fa-pinterest text-red-400", nowm: true };
  if (u.includes("reddit.com") || u.includes("v.redd.it")) return { name: "Reddit", icon: "fa-brands fa-reddit text-orange-500", nowm: true };
  return { name: "Auto-Detect", icon: "fa-solid fa-link text-slate-400", nowm: false };
}

// Live URL Input Handler
videoUrlInput.addEventListener("input", (e) => {
  const detected = detectPlatformFromUrl(e.target.value);
  detectedIcon.className = `${detected.icon} transition-all text-base`;
  
  document.querySelectorAll(".platform-chip").forEach(chip => {
    const platform = chip.getAttribute("data-platform");
    if (detected.name.toLowerCase().includes(platform)) {
      chip.classList.add("active");
    } else {
      chip.classList.remove("active");
    }
  });
});

// Clipboard Paste
async function handlePaste() {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      videoUrlInput.value = text;
      videoUrlInput.dispatchEvent(new Event("input"));
      showToast("Link clipboard se paste kar diya gaya!", "info");
      fetchVideoInfo(text);
    }
  } catch (err) {
    showToast("Clipboard permission nahi mili. Aap manually Ctrl+V ya long-press kar ke paste karein.", "warning");
  }
}

pasteBtn.addEventListener("click", handlePaste);

// Toast Message
function showToast(msg, type = "info") {
  statusMessage.classList.remove("hidden", "bg-red-500/10", "border-red-500/30", "text-red-400", "bg-emerald-500/10", "border-emerald-500/30", "text-emerald-400", "bg-blue-500/10", "border-blue-500/30", "text-blue-400");
  
  if (type === "error") {
    statusMessage.className = "mt-3 p-3 rounded-xl text-xs font-medium flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-400";
    statusMessage.innerHTML = `<i class="fa-solid fa-circle-exclamation text-base"></i> <span>${msg}</span>`;
  } else if (type === "success") {
    statusMessage.className = "mt-3 p-3 rounded-xl text-xs font-medium flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400";
    statusMessage.innerHTML = `<i class="fa-solid fa-circle-check text-base"></i> <span>${msg}</span>`;
  } else {
    statusMessage.className = "mt-3 p-3 rounded-xl text-xs font-medium flex items-center gap-2 bg-blue-500/10 border border-blue-500/30 text-blue-400";
    statusMessage.innerHTML = `<i class="fa-solid fa-info-circle text-base"></i> <span>${msg}</span>`;
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
  fetchBtn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> <span>Fetching...</span>`;
  showToast("Stream info extract ki ja rahi hai...", "info");
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
    fetchBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>Fetch Video</span>`;
  }
}

// Render Preview Card
function renderPreview(data) {
  const detected = detectPlatformFromUrl(data.url);
  videoThumbnail.src = data.thumbnail || "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=600&q=80";
  
  platformBadge.innerHTML = `<i class="${detected.icon}"></i> ${detected.name}`;
  if (data.has_no_watermark || data.platform === "tiktok" || detected.nowm) {
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
    videoOptions.push({ label: "Best Available Quality", value: "best" });
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

// Trigger Device Download (Auto-Save Mechanism)
function triggerAutoSaveToDevice(filename) {
  const fileUrl = `/api/file/${encodeURIComponent(filename)}?attachment=true`;
  
  // Method 1: Invisible direct anchor trigger
  const a = document.createElement("a");
  a.href = fileUrl;
  a.download = filename;
  a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  setTimeout(() => document.body.removeChild(a), 1000);

  // Method 2: Hidden iframe fallback (guarantees trigger on Android Chrome & Safari)
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

// Track Progress
function trackDownloadProgress(taskId) {
  progressCard.classList.remove("hidden");
  completedActions.classList.add("hidden");
  progressCard.scrollIntoView({ behavior: "smooth", block: "nearest" });

  progressBar.style.width = "5%";
  progressPercentText.textContent = "5%";
  progressStatusText.textContent = "Downloading stream...";
  progressSubText.textContent = "High speed stream extraction active";

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
        progressStatusText.textContent = "Downloading media streams...";
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
        progressSubText.textContent = `File: ${t.filename || 'media'}`;

        const fileUrl = `/api/file/${encodeURIComponent(t.filename)}?attachment=true`;
        browserDownloadBtn.href = fileUrl;
        completedActions.classList.remove("hidden");

        // AUTO-SAVE TO DEVICE IF TOGGLED ON
        if (autoSaveToggle.checked) {
          triggerAutoSaveToDevice(t.filename);
          playCompletionTone();
          showToast(`"${t.filename}" aapke device (Downloads folder) mein khud-ba-khud save ho gayi hai!`, "success");
        } else {
          playCompletionTone();
        }

        startDownloadBtn.disabled = false;
        updateFormatUI();
        loadHistory();
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

// Open folder action (PC)
async function openFolder() {
  try {
    const res = await fetch("/api/open-folder", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      showToast("PC par Downloads folder open kar diya gaya!", "success");
    } else {
      showToast(data.error || "Folder open nahi ho saka", "error");
    }
  } catch (err) {
    showToast("Error opening folder: " + err.message, "error");
  }
}

if (openFolderBtn) openFolderBtn.addEventListener("click", openFolder);
if (quickOpenFolderBtn) quickOpenFolderBtn.addEventListener("click", openFolder);

if (historyTabBtn) {
  historyTabBtn.addEventListener("click", () => {
    historySection.scrollIntoView({ behavior: "smooth" });
  });
}

// Mobile Bottom Nav Event Handlers
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
    if (historyBadge) historyBadge.textContent = files.length;

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
      item.className = "flex items-center justify-between p-3 rounded-xl bg-dark-850 border border-slate-700/60 hover:border-slate-600 transition";
      item.innerHTML = `
        <div class="flex items-center gap-2.5 min-w-0 pr-2">
          <div class="w-8 h-8 rounded-lg bg-dark-700 border border-slate-700 flex items-center justify-center shrink-0">
            <i class="fa-solid ${icon} text-xs"></i>
          </div>
          <div class="min-w-0">
            <h5 class="text-xs font-semibold text-white truncate max-w-[180px] sm:max-w-md" title="${f.filename}">
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
          ${!isAudio ? `
            <button class="play-btn w-7 h-7 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 flex items-center justify-center transition" title="Preview">
              <i class="fa-solid fa-play text-[10px]"></i>
            </button>
          ` : ''}
          <a href="/api/file/${encodeURIComponent(f.filename)}?attachment=true" download class="w-7 h-7 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 flex items-center justify-center transition" title="Download">
            <i class="fa-solid fa-download text-[10px]"></i>
          </a>
          <button class="delete-btn w-7 h-7 rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 flex items-center justify-center transition" title="Delete">
            <i class="fa-regular fa-trash-can text-[10px]"></i>
          </button>
        </div>
      `;

      const playBtn = item.querySelector(".play-btn");
      if (playBtn) {
        playBtn.addEventListener("click", () => {
          modalVideoTitle.textContent = f.filename;
          modalVideoPlayer.src = `/api/file/${encodeURIComponent(f.filename)}?attachment=false`;
          videoModal.classList.remove("hidden");
          modalVideoPlayer.play();
        });
      }

      const delBtn = item.querySelector(".delete-btn");
      delBtn.addEventListener("click", async () => {
        if (confirm(`Kya aap "${f.filename}" ko delete karna chahte hain?`)) {
          const dres = await fetch("/api/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ filename: f.filename })
          });
          const ddata = await dres.json();
          if (ddata.success) {
            loadHistory();
            showToast("File delete ho gayi", "info");
          }
        }
      });

      historyList.appendChild(item);
    });
  } catch (err) {
    console.error("History fetch error:", err);
  }
}

refreshHistoryBtn.addEventListener("click", loadHistory);

// Modal Close
closeModalBtn.addEventListener("click", () => {
  modalVideoPlayer.pause();
  modalVideoPlayer.src = "";
  videoModal.classList.add("hidden");
});

videoModal.addEventListener("click", (e) => {
  if (e.target === videoModal) {
    modalVideoPlayer.pause();
    modalVideoPlayer.src = "";
    videoModal.classList.add("hidden");
  }
});

// Initial load
loadHistory();

