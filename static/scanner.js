const video = document.getElementById("camera");
const canvas = document.getElementById("canvas");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const scanBtn = document.getElementById("scanBtn");
const manualId = document.getElementById("manualId");
const recordBtn = document.getElementById("recordBtn");
const statusText = document.getElementById("status");
const todayDate = document.getElementById("todayDate");
const count = document.getElementById("count");
const visitorList = document.getElementById("visitorList");

const ID_RE = /^\d{2}-\d{4}-\d{6}$/;
const AUTO_INTERVAL_MS = 2000;

const state = {
    stream: null,
    autoTimer: null,
    busy: false,
    displayedDate: null,
};

function setStatus(message) {
    statusText.textContent = message;
}

function showDate(isoDate) {
    const date = isoDate ? new Date(`${isoDate}T00:00:00`) : new Date();
    state.displayedDate = date.toDateString();
    todayDate.textContent = date.toLocaleDateString(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
}

// If the kiosk stays open past midnight, reload so yesterday's list clears.
setInterval(() => {
    if (state.displayedDate !== new Date().toDateString()) {
        loadToday();
    }
}, 60 * 1000);

function currentMode() {
    return document.querySelector('input[name="mode"]:checked').value;
}

async function startCamera() {
    try {
        state.stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: "environment", width: 1280, height: 720 },
        });
        video.srcObject = state.stream;
        startBtn.disabled = true;
        stopBtn.disabled = false;
        scanBtn.disabled = false;
        setStatus("Camera is on. Show your ID.");
        syncAutoMode();
    } catch (error) {
        setStatus(`Cannot open camera: ${error.message}`);
    }
}

function stopCamera() {
    stopAuto();
    if (state.stream) {
        state.stream.getTracks().forEach((track) => track.stop());
        state.stream = null;
    }
    video.srcObject = null;
    startBtn.disabled = false;
    stopBtn.disabled = true;
    scanBtn.disabled = true;
    setStatus("Camera is off.");
}

function syncAutoMode() {
    stopAuto();
    if (state.stream && currentMode() === "auto") {
        state.autoTimer = setInterval(autoScan, AUTO_INTERVAL_MS);
        setStatus("Automatic scan is running.");
    }
}

function stopAuto() {
    if (state.autoTimer) {
        clearInterval(state.autoTimer);
        state.autoTimer = null;
    }
}

function captureFrame() {
    return new Promise((resolve) => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        canvas.getContext("2d").drawImage(video, 0, 0);
        canvas.toBlob(resolve, "image/jpeg", 0.9);
    });
}

async function autoScan() {
    if (state.busy || !state.stream) return;
    state.busy = true;
    try {
        const blob = await captureFrame();
        await sendImage(blob, "auto");
    } finally {
        state.busy = false;
    }
}

async function manualCapture() {
    if (!state.stream) {
        setStatus("Start the camera first.");
        return;
    }
    const blob = await captureFrame();
    await sendImage(blob, "manual");
}

async function sendImage(blob, mode) {
    const body = new FormData();
    body.append("image", blob, "frame.jpg");
    body.append("mode", mode);

    try {
        const response = await fetch("/api/scan/image", { method: "POST", body });
        handleResponse(response);
    } catch (error) {
        setStatus(`Scan failed: ${error.message}`);
    }
}

async function recordManual() {
    const id = manualId.value.trim();
    if (!ID_RE.test(id)) {
        setStatus("Use the format 00-0000-000000.");
        return;
    }

    const body = new FormData();
    body.append("id", id);

    try {
        const response = await fetch("/api/scan/manual", { method: "POST", body });
        handleResponse(response);
    } catch (error) {
        setStatus(`Record failed: ${error.message}`);
    }
}

async function handleResponse(response) {
    if (response.status === 401) {
        window.location.href = "/login";
        return;
    }

    const data = await response.json();
    const student = data.student;

    if (data.status === "ok") {
        setStatus(`Student Entered: ${student.fullname}.`);
        manualId.value = "";
    } else if (data.status === "duplicate") {
        setStatus("Already recorded a moment ago.");
    } else if (data.status === "not_found") {
        setStatus(`ID not registered: ${data.id}`);
    } else if (data.status === "wrong_school") {
        setStatus(`This ID is not registered at this school (belongs to ${data.school}).`);
    } else if (data.status === "unrecognized") {
        setStatus("No ID found in the camera. Move closer and try again.");
    } else {
        setStatus(data.message || "Scan failed.");
    }

    if (data.visitors) {
        renderVisitors(data.visitors);
    }
}

async function loadToday() {
    try {
        const response = await fetch("/api/visitors/today");
        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }
        const data = await response.json();
        showDate(data.date);
        renderVisitors(data.visitors);
    } catch (error) {
        setStatus(`Cannot load visitors: ${error.message}`);
    }
}

function renderVisitors(visitors) {
    count.textContent = visitors.length;
    visitorList.innerHTML = "";

    for (const visitor of visitors) {
        const time = new Date(visitor.time_in).toLocaleTimeString();
        const item = document.createElement("li");
        item.textContent =
            `${visitor.fullname} — ${visitor.school_id} — ` +
            `${visitor.course} (${visitor.year_level}) — ${time}`;
        visitorList.appendChild(item);
    }
}

function formatManualInput() {
    const digits = manualId.value.replace(/\D/g, "").slice(0, 12);
    let formatted = digits;
    if (digits.length > 6) {
        formatted = `${digits.slice(0, 2)}-${digits.slice(2, 6)}-${digits.slice(6)}`;
    } else if (digits.length > 2) {
        formatted = `${digits.slice(0, 2)}-${digits.slice(2)}`;
    }
    manualId.value = formatted;
}

startBtn.addEventListener("click", startCamera);
stopBtn.addEventListener("click", stopCamera);
scanBtn.addEventListener("click", manualCapture);
recordBtn.addEventListener("click", recordManual);
manualId.addEventListener("input", formatManualInput);
manualId.addEventListener("keydown", (event) => {
    if (event.key === "Enter") recordManual();
});
document.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.addEventListener("change", syncAutoMode);
});

loadToday();
showDate();
