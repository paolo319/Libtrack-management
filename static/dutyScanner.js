const POLL_MS = 1000;
const FALLBACK_PHOTO = "/static/pp/bow-kratos.gif";

const todayDate = document.getElementById("todayDate");
const count = document.getElementById("count");
const tableBody = document.getElementById("dutyTableBody");
const empty = document.getElementById("empty");
const statusText = document.getElementById("status");

const state = {
    busy: false,
    date: null,
};

// Rows are reused between polls so photos do not flicker every second.
const rows = new Map();

function setStatus(message) {
    statusText.textContent = message;
}

function formatDate(isoDate) {
    const date = isoDate ? new Date(`${isoDate}T00:00:00`) : new Date();
    return date.toLocaleDateString(undefined, {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
}

function formatTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleTimeString();
}

function setPhoto(image, url, alt) {
    image.alt = alt || "Profile photo";
    const target = url || FALLBACK_PHOTO;
    if (image.getAttribute("src") === target) return;

    image.onerror = () => {
        image.onerror = null;
        image.src = FALLBACK_PHOTO;
    };
    image.src = target;
}

function createRow() {
    const row = document.createElement("tr");

    const profileCell = document.createElement("td");
    const photo = document.createElement("img");
    photo.width = 64;
    photo.height = 64;
    photo.loading = "lazy";
    photo.decoding = "async";
    profileCell.appendChild(photo);

    const nameCell = document.createElement("td");
    const timeInCell = document.createElement("td");
    const timeOutCell = document.createElement("td");

    row.append(profileCell, nameCell, timeInCell, timeOutCell);

    row._photo = photo;
    row._name = nameCell;
    row._timeIn = timeInCell;
    row._timeOut = timeOutCell;

    return row;
}

function updateRow(row, record) {
    const person = record.person || {};

    setPhoto(row._photo, person.logo_url, person.fullname);
    row._name.textContent = person.fullname || "Unknown";
    row._timeIn.textContent = formatTime(record.time_in);
    row._timeOut.textContent = formatTime(record.time_out);
}

function renderRecords(records) {
    const seen = new Set();

    records.forEach((record, index) => {
        const id = String(record.id);
        seen.add(id);

        let row = rows.get(id);
        if (!row) {
            row = createRow();
            rows.set(id, row);
        }

        updateRow(row, record);

        const current = tableBody.children[index] || null;
        if (current !== row) {
            tableBody.insertBefore(row, current);
        }
    });

    for (const [id, row] of rows) {
        if (!seen.has(id)) {
            row.remove();
            rows.delete(id);
        }
    }
}

function resetDay() {
    rows.clear();
    tableBody.replaceChildren();
}

async function loadToday() {
    if (state.busy) return;
    state.busy = true;

    try {
        const response = await fetch("/api/duty/today", {
            cache: "no-store",
            headers: { Accept: "application/json" },
        });

        if (response.status === 401) {
            window.location.href = "/login";
            return;
        }

        if (!response.ok) {
            throw new Error(`Server returned ${response.status}.`);
        }

        const data = await response.json();
        const records = Array.isArray(data.records) ? data.records : [];

        // A new local day starts a brand-new board; yesterday is never shown.
        if (data.date !== state.date) {
            state.date = data.date;
            resetDay();
        }

        todayDate.textContent = formatDate(data.date);
        count.textContent = records.length;
        renderRecords(records);
        empty.hidden = records.length > 0;
        setStatus("Live \u2014 updating every second.");
    } catch (error) {
        setStatus(`Connection lost \u2014 retrying. ${error.message}`);
    } finally {
        state.busy = false;
        window.setTimeout(loadToday, POLL_MS);
    }
}

setStatus("Connecting\u2026");
loadToday();
