const form = document.getElementById("jobForm");
const statusBox = document.getElementById("status");
const rows = document.getElementById("leadRows");
const exportBtn = document.getElementById("exportBtn");
const apiBaseInput = document.getElementById("apiBase");

let currentJobId = null;
let pollHandle = null;

function apiBase() {
  return apiBaseInput.value.trim().replace(/\/$/, "");
}

function setStatus(message) {
  statusBox.textContent = message;
}

function renderLeads(items) {
  rows.innerHTML = "";

  if (!items.length) {
    rows.innerHTML = `<tr><td colspan="5">No leads yet.</td></tr>`;
    return;
  }

  for (const lead of items) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${lead.business_name}</td>
      <td>${lead.phone || "-"}</td>
      <td>${lead.website ? `<a href="${lead.website}" target="_blank" rel="noreferrer">${lead.website}</a>` : "-"}</td>
      <td>${[lead.city, lead.state, lead.country].filter(Boolean).join(", ") || "-"}</td>
      <td>${lead.lead_score}</td>
    `;
    rows.appendChild(tr);
  }
}

async function request(path, init = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response.text();
}

async function loadLeads(jobId) {
  const data = await request(`/jobs/${jobId}/leads`);
  renderLeads(data.items || []);
}

async function pollJob(jobId) {
  if (pollHandle) {
    clearInterval(pollHandle);
  }

  pollHandle = setInterval(async () => {
    try {
      const job = await request(`/jobs/${jobId}`);
      const statusMsg = job.status === "failed" && job.error_message
        ? `Job failed: ${job.error_message}`
        : `Job ${job.status} | ${job.total_results} leads`;
      setStatus(statusMsg);

      if (job.status === "completed" || job.status === "failed") {
        clearInterval(pollHandle);
        pollHandle = null;
        await loadLeads(jobId);
      }
    } catch (error) {
      clearInterval(pollHandle);
      pollHandle = null;
      setStatus(`Polling error: ${error.message}`);
    }
  }, 2500);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);

  const body = {
    query: data.get("query"),
    location: data.get("location"),
    max_results: Number(data.get("maxResults") || 40),
  };

  setStatus("Creating job...");
  rows.innerHTML = "";

  try {
    const job = await request("/jobs", {
      method: "POST",
      body: JSON.stringify(body),
    });

    currentJobId = job.id;
    setStatus(`Job created: ${job.id}. Starting...`);
    await pollJob(job.id);
  } catch (error) {
    setStatus(`Error: ${error.message}`);
  }
});

exportBtn.addEventListener("click", () => {
  const params = new URLSearchParams();
  if (currentJobId) {
    params.set("job_id", currentJobId);
  }

  const url = `${apiBase()}/leads/export/csv${params.toString() ? `?${params.toString()}` : ""}`;
  window.open(url, "_blank");
});
