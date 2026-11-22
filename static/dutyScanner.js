
(() => {
    const CFG = {
        pollMs: 1500,
        idleMs: 400,
        dedupeMs: 2000,
        messageMs: 5000,
        minLen: 4,
        maxLen: 64,
    };

    const FALLBACK_PHOTO = "/static/pp/bow-kratos.gif";
    const OK_SCAN = new Set(["time_in", "time_out"]);

    const el = {
        status: document.getElementById("status"),
        date: document.getElementById("todayDate"),
        count: document.getElementById("count"),
        body: document.getElementById("dutyTableBody"),
        empty: document.getElementById("empty"),
    };

    if (!el.body || !el.status) return;

    const state = {
        buffer: "",
        bufferTimer: 0,
        lastUid: "",
        lastAt: 0,
        busy: false,
        polling: false,
        focused: document.hasFocus(),
        message: "",
        messageUntil: 0,
        audio: null,
    };

    function setMessage(text) {
        state.message = String(text || "");
        state.messageUntil = Date.now() + CFG.messageMs;
        renderStatus();
    }

    function renderStatus() {
        const idle = state.focused
            ? "Live — tap a card to record duty."
            : "Scanner paused — click the page to activate.";
        el.status.textContent =
            Date.now() < state.messageUntil ? state.message : idle;
    }

    function normalizeUid(raw) {
        const uid = String(raw || "")
            .toUpperCase()
            .replace(/[^0-9A-F]/g, "");
        return uid.length >= CFG.minLen && uid.length <= CFG.maxLen ? uid : null;
    }

    function isTypingTarget(target) {
        if (!(target instanceof Element)) return false;
        return (
            ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName) ||
            target.isContentEditable
        );
    }

    function safeImage(value) {
        if (
            typeof value !== "string" ||
            !value.startsWith("/") ||
            value.startsWith("//") ||
            value.includes("\\")
        ) {
            return FALLBACK_PHOTO;
        }
        return value;
    }

    function formatTime(value) {
        if (!value) return "—";
        const date = new Date(value);
        return Number.isNaN(date.getTime())
            ? "—"
            : date.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
              });
    }

    function formatDate(value) {
        if (!value) return "";
        const date = new Date(`${value}T00:00:00`);
        return Number.isNaN(date.getTime())
            ? value
            : date.toLocaleDateString(undefined, {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
              });
    }

    function beep(ok) {
        try {
            const Audio = window.AudioContext || window.webkitAudioContext;
            if (!Audio) return;
            const ctx = state.audio || (state.audio = new Audio());
            if (ctx.state === "suspended") ctx.resume();

            const now = ctx.currentTime;
            const oscillator = ctx.createOscillator();
            const gain = ctx.createGain();
            oscillator.type = "sine";
            oscillator.frequency.value = ok ? 880 : 240;
            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(0.15, now + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.2);
            oscillator.connect(gain).connect(ctx.destination);
            oscillator.start(now);
            oscillator.stop(now + 0.22);
        } catch (_) {
            // Audio is optional.
        }
    }

    async function postScan(uid) {
        const body = new FormData();
        body.append("rfid", uid);

        let response;
        try {
            response = await fetch("/api/duty/scan", {
                method: "POST",
                body,
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" },
            });
        } catch (_) {
            setMessage("Server unavailable.");
            beep(false);
            return;
        }

        if (response.status === 401) {
            window.location.replace("/login");
            return;
        }

        let data = {};
        try {
            data = await response.json();
        } catch (_) {
            // Use the generic failure message below.
        }

        if (!response.ok) {
            setMessage(data.detail || `Scan failed (${response.status}).`);
            beep(false);
            return;
        }

        setMessage(data.message || "Scan recorded.");
        await loadToday();
        beep(OK_SCAN.has(data.status));
    }

    async function loadToday() {
        if (state.polling) return;
        state.polling = true;
        try {
            const response = await fetch("/api/duty/today", {
                credentials: "same-origin",
                cache: "no-store",
                headers: { Accept: "application/json" },
            });
            if (response.status === 401) {
                window.location.replace("/login");
                return;
            }
            if (response.ok) applyRecords(await response.json());
        } catch (_) {
            // Keep the last good board; the next poll retries.
        } finally {
            state.polling = false;
            renderStatus();
        }
    }

    function createRow(record) {
        const person = record.person || {};
        const row = document.createElement("tr");

        const photoCell = document.createElement("td");
        const photo = document.createElement("img");
        photo.className = "duty-photo";
        photo.src = safeImage(person.logo_url);
        photo.alt = person.fullname || "Profile";
        photo.onerror = () => {
            photo.onerror = null;
            photo.src = FALLBACK_PHOTO;
        };
        photoCell.appendChild(photo);

        const nameCell = document.createElement("td");
        const name = document.createElement("strong");
        name.textContent = person.fullname || "Unknown";
        nameCell.appendChild(name);

        const timeIn = document.createElement("td");
        timeIn.textContent = formatTime(record.time_in);
        const timeOut = document.createElement("td");
        timeOut.textContent = record.time_out ? formatTime(record.time_out) : "Not yet";

        row.append(photoCell, nameCell, timeIn, timeOut);
        return row;
    }

    function applyRecords(data) {
        const records = Array.isArray(data.records) ? data.records : [];
        if (el.count) el.count.textContent = String(data.count ?? records.length);
        if (el.date) el.date.textContent = formatDate(data.date);
        if (el.empty) el.empty.hidden = records.length !== 0;

        const rows = document.createDocumentFragment();
        records.forEach((record) => rows.appendChild(createRow(record)));
        el.body.replaceChildren(rows);
    }

    function submitUid(raw) {
        const uid = normalizeUid(raw);
        if (!uid) {
            setMessage("Invalid RFID card value.");
            beep(false);
            return;
        }

        const now = Date.now();
        if (uid === state.lastUid && now - state.lastAt < CFG.dedupeMs) return;
        state.lastUid = uid;
        state.lastAt = now;

        if (state.busy) return; // A tap is still being saved; ignore extras.
        state.busy = true;
        postScan(uid).finally(() => {
            state.busy = false;
            renderStatus();
        });
    }

    function flushBuffer() {
        const raw = state.buffer;
        state.buffer = "";
        clearTimeout(state.bufferTimer);
        state.bufferTimer = 0;
        if (raw) submitUid(raw);
    }

    document.addEventListener("keydown", (event) => {
        if (event.ctrlKey || event.altKey || event.metaKey || event.isComposing) return;
        if (isTypingTarget(event.target)) return;

        if (event.key === "Enter" || event.key === "Tab") {
            if (state.buffer) {
                event.preventDefault();
                flushBuffer();
            }
            return;
        }

        if (event.key === "Escape") {
            state.buffer = "";
            clearTimeout(state.bufferTimer);
            return;
        }

        if (event.key.length !== 1) return;
        state.buffer += event.key;
        if (state.buffer.length > CFG.maxLen) {
            state.buffer = state.buffer.slice(-CFG.maxLen);
        }
        clearTimeout(state.bufferTimer);
        state.bufferTimer = window.setTimeout(flushBuffer, CFG.idleMs);
    });

    window.addEventListener("focus", () => {
        state.focused = true;
        renderStatus();
    });
    window.addEventListener("blur", () => {
        state.focused = false;
        renderStatus();
    });
    document.addEventListener("visibilitychange", () => {
        renderStatus();
        if (!document.hidden) loadToday();
    });

    renderStatus();
    loadToday();
    window.setInterval(loadToday, CFG.pollMs);
})();
