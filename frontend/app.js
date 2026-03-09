// ── State ────────────────────────────────────────────────────────────────────
let currentJobId = null;
let pollHandle = null;
let leadsOffset = 0;
const LEADS_LIMIT = 50;
let allJobs = [];

// ── API helper ────────────────────────────────────────────────────────────────
function apiBase() {
  const stored = document.getElementById("apiBase")?.value || "";
  if (stored.trim()) return stored.trim().replace(/\/$/, "");
  // Auto-detect: on production (served via nginx) use relative path
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  return isLocal ? "http://localhost:8000/api/v1" : "/api/v1";
}

async function api(path, init = {}) {
  const res = await fetch(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

// ── Tab navigation ────────────────────────────────────────────────────────────
function activateTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  const tab = document.getElementById(`tab-${name}`);
  const btn = document.querySelector(`.nav-btn[data-tab="${name}"]`);
  if (tab) tab.classList.add("active");
  if (btn) btn.classList.add("active");
  document.getElementById("topbarTitle").textContent =
    btn?.textContent.trim().replace(/^[^\w]+/, "") || name;

  if (name === "jobs") loadJobs();
  if (name === "leads") loadLeads();
  if (name === "presets") loadPresets();
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => activateTab(btn.dataset.tab));
});

// Mobile sidebar toggle
document.getElementById("menuToggle")?.addEventListener("click", () => {
  document.getElementById("sidebar").classList.toggle("open");
});

// Sync API base between sidebar input and settings input
document.getElementById("apiBase")?.addEventListener("input", e => {
  const s = document.getElementById("apiBaseSettings");
  if (s) s.value = e.target.value;
});

// ── Slide-over ────────────────────────────────────────────────────────────────
function openSlide(title, html) {
  document.getElementById("slideoverTitle").textContent = title;
  document.getElementById("slideoverBody").innerHTML = html;
  document.getElementById("slideover").classList.remove("hidden");
  document.getElementById("overlay").classList.remove("hidden");
}
function closeSlide() {
  document.getElementById("slideover").classList.add("hidden");
  document.getElementById("overlay").classList.add("hidden");
}
document.getElementById("closeSlide")?.addEventListener("click", closeSlide);
document.getElementById("overlay")?.addEventListener("click", closeSlide);

// ── Badges / pills ────────────────────────────────────────────────────────────
function statusBadge(status) {
  return `<span class="badge badge-${status}">${status}</span>`;
}
function scorePill(score) {
  const grade = score >= 80 ? "a" : score >= 60 ? "b" : score >= 40 ? "c" : "d";
  return `<span class="score-pill score-${grade}">${score}</span>`;
}
function readinessBadge(r) {
  if (!r) return `<span class="badge badge-low">—</span>`;
  return `<span class="badge badge-${r.toLowerCase()}">${r}</span>`;
}
function priorityBadge(p) {
  if (!p) return "";
  return `<span class="badge badge-${p}">${p}</span>`;
}

// ── JOBS TAB ──────────────────────────────────────────────────────────────────
async function loadJobs() {
  const el = document.getElementById("jobList");
  try {
    const jobs = await api("/jobs?limit=20");
    allJobs = jobs;
    // Populate lead tab job filter
    const sel = document.getElementById("leadJobFilter");
    if (sel) {
      const existing = [...sel.options].map(o => o.value);
      for (const j of jobs) {
        if (!existing.includes(j.id)) {
          const o = document.createElement("option");
          o.value = j.id;
          o.textContent = `${j.query} — ${j.location}`;
          sel.appendChild(o);
        }
      }
    }
    if (!jobs.length) { el.innerHTML = `<p class="muted">No jobs yet.</p>`; return; }
    el.innerHTML = jobs.map(j => `
      <div class="job-item" data-id="${j.id}">
        <div class="job-item-top">
          <span class="job-query">${esc(j.query)}</span>
          ${statusBadge(j.status)}
        </div>
        <div class="job-meta">${esc(j.location)} · ${j.total_results} leads · ${fmtDate(j.created_at)}</div>
      </div>
    `).join("");

    el.querySelectorAll(".job-item").forEach(item => {
      item.addEventListener("click", () => {
        const jid = item.dataset.id;
        el.querySelectorAll(".job-item").forEach(i => i.classList.remove("selected"));
        item.classList.add("selected");
        currentJobId = jid;
        // Switch to leads tab filtered by this job
        document.getElementById("leadJobFilter").value = jid;
        leadsOffset = 0;
        activateTab("leads");
      });
    });
  } catch (e) {
    el.innerHTML = `<p class="muted">Failed to load jobs: ${esc(e.message)}</p>`;
  }
}

const jobForm = document.getElementById("jobForm");
jobForm?.addEventListener("submit", async e => {
  e.preventDefault();
  const data = new FormData(jobForm);
  const sources = [];
  if (data.get("src_maps")) sources.push("google_maps");
  if (data.get("src_search")) sources.push("google_search");
  const body = {
    query: data.get("query"),
    location: data.get("location"),
    max_results: Number(data.get("maxResults") || 40),
    industry: data.get("industry") || undefined,
    sources_enabled: sources.length ? sources : ["google_maps"],
  };
  setStatus("jobStatus", "Creating job…");
  try {
    const job = await api("/jobs", { method: "POST", body: JSON.stringify(body) });
    currentJobId = job.id;
    setStatus("jobStatus", `✅ Job created (${job.id.slice(0,8)}…). Polling…`);
    await loadJobs();
    pollJob(job.id);
  } catch (err) {
    setStatus("jobStatus", `❌ ${err.message}`);
  }
});

document.getElementById("refreshJobs")?.addEventListener("click", loadJobs);

function pollJob(jobId) {
  if (pollHandle) clearInterval(pollHandle);
  pollHandle = setInterval(async () => {
    try {
      const job = await api(`/jobs/${jobId}`);
      const msg = job.status === "failed" && job.error_message
        ? `❌ Failed: ${job.error_message}`
        : `⏳ ${job.status} — ${job.total_results} leads`;
      setStatus("jobStatus", msg);
      if (job.status === "completed" || job.status === "failed") {
        clearInterval(pollHandle);
        pollHandle = null;
        if (job.status === "completed") setStatus("jobStatus", `✅ Done — ${job.total_results} leads found.`);
        await loadJobs();
      }
    } catch (err) {
      clearInterval(pollHandle); pollHandle = null;
      setStatus("jobStatus", `❌ Poll error: ${err.message}`);
    }
  }, 2500);
}

// ── LEADS TAB ─────────────────────────────────────────────────────────────────
async function loadLeads() {
  const rows = document.getElementById("leadRows");
  rows.innerHTML = `<tr><td colspan="6" class="muted center">Loading…</td></tr>`;

  const q = document.getElementById("leadSearch")?.value || "";
  const jobId = document.getElementById("leadJobFilter")?.value || "";
  const minScore = document.getElementById("leadScoreFilter")?.value || "";

  const params = new URLSearchParams({
    limit: LEADS_LIMIT,
    offset: leadsOffset,
    ...(q && { q }),
    ...(jobId && { job_id: jobId }),
    ...(minScore && { min_score: minScore }),
  });

  try {
    const data = await api(`/leads?${params}`);
    renderLeads(data.items || [], data.total || 0);
  } catch (err) {
    rows.innerHTML = `<tr><td colspan="6" class="muted center">Error: ${esc(err.message)}</td></tr>`;
  }
}

function renderLeads(leads, total) {
  const rows = document.getElementById("leadRows");
  if (!leads.length) {
    rows.innerHTML = `<tr><td colspan="6" class="muted center">No leads found.</td></tr>`;
    renderPagination(total);
    return;
  }
  rows.innerHTML = leads.map(l => {
    const enrichment = l.ai_enrichment || null;
    const readiness = enrichment?.ai_adoption_readiness || null;
    return `
    <tr>
      <td>
        <div style="font-weight:600;">${esc(l.business_name)}</div>
        ${l.website ? `<a href="${esc(l.website)}" target="_blank" style="font-size:11px;">${esc(l.website)}</a>` : ""}
      </td>
      <td>${esc(l.city || "—")}</td>
      <td>${l.phone ? `<a href="tel:${esc(l.phone)}">${esc(l.phone)}</a>` : "—"}</td>
      <td>${scorePill(l.lead_score)}</td>
      <td>${readinessBadge(readiness)}</td>
      <td class="actions-cell">
        <button class="btn btn-ghost btn-xs" data-action="view" data-id="${l.id}">View</button>
        <button class="btn btn-ghost btn-xs" data-action="enrich" data-id="${l.id}" data-name="${esc(l.business_name)}">Enrich</button>
        <button class="btn btn-ghost btn-xs" data-action="outreach" data-id="${l.id}">Outreach</button>
      </td>
    </tr>`;
  }).join("");

  rows.querySelectorAll("[data-action]").forEach(btn => {
    btn.addEventListener("click", () => {
      const { action, id, name } = btn.dataset;
      if (action === "view") viewLead(id);
      if (action === "enrich") enrichLead(id, name, btn);
      if (action === "outreach") goToOutreach(id);
    });
  });

  renderPagination(total);
}

function renderPagination(total) {
  const container = document.getElementById("leadPagination");
  const pages = Math.ceil(total / LEADS_LIMIT);
  const current = Math.floor(leadsOffset / LEADS_LIMIT);
  if (pages <= 1) { container.innerHTML = ""; return; }
  container.innerHTML = Array.from({ length: pages }, (_, i) =>
    `<button class="page-btn${i === current ? " active" : ""}" data-page="${i}">${i + 1}</button>`
  ).join("");
  container.querySelectorAll(".page-btn").forEach(b => {
    b.addEventListener("click", () => {
      leadsOffset = Number(b.dataset.page) * LEADS_LIMIT;
      loadLeads();
    });
  });
}

["leadSearch", "leadJobFilter", "leadScoreFilter"].forEach(id => {
  document.getElementById(id)?.addEventListener("change", () => { leadsOffset = 0; loadLeads(); });
});
document.getElementById("leadSearch")?.addEventListener("keyup", debounce(() => { leadsOffset = 0; loadLeads(); }, 400));

document.getElementById("exportCsvBtn")?.addEventListener("click", () => {
  const jobId = document.getElementById("leadJobFilter")?.value;
  const minScore = document.getElementById("leadScoreFilter")?.value;
  const params = new URLSearchParams({
    ...(jobId && { job_id: jobId }),
    ...(minScore && { min_score: minScore }),
  });
  window.open(`${apiBase()}/leads/export/csv?${params}`, "_blank");
});

// ── Lead detail slide-over ────────────────────────────────────────────────────
async function viewLead(id) {
  openSlide("Loading…", `<p class="muted">Fetching lead…</p>`);
  try {
    const l = await api(`/leads/${id}`);
    const e = l.ai_enrichment || {};
    const o = l.outreach_data || {};

    const enrichHtml = Object.keys(e).length ? `
      <div class="detail-section">
        <h4>AI Enrichment</h4>
        ${detailRow("AI Readiness", readinessBadge(e.ai_adoption_readiness))}
        ${detailRow("Urgency Score", e.urgency_score ? `${e.urgency_score}/10` : "—")}
        ${detailRow("Company Size", e.estimated_size || "—")}
        ${detailRow("Employees", e.estimated_employee_count || "—")}
        ${detailRow("Industry", e.industry_vertical || "—")}
        ${detailRow("Summary", e.company_summary || "—")}
        ${e.pain_points?.length ? `<div class="detail-row"><span class="detail-key">Pain Points</span><span class="detail-val"><div class="tag-list">${e.pain_points.map(p => `<span class="tag">${esc(p)}</span>`).join("")}</div></span></div>` : ""}
        ${e.talking_points?.length ? `<div class="detail-row"><span class="detail-key">Talking Points</span><span class="detail-val"><div class="tag-list">${e.talking_points.map(p => `<span class="tag">${esc(p)}</span>`).join("")}</div></span></div>` : ""}
        ${e.decision_maker_titles?.length ? `<div class="detail-row"><span class="detail-key">Decision Makers</span><span class="detail-val"><div class="tag-list">${e.decision_maker_titles.map(t => `<span class="tag">${esc(t)}</span>`).join("")}</div></span></div>` : ""}
        ${detailRow("Recommended Approach", e.recommended_approach || "—")}
        ${detailRow("Competitive Landscape", e.competitive_landscape || "—")}
      </div>` : `<div class="detail-section"><p class="muted">Not yet enriched. Click Enrich in the leads table.</p></div>`;

    const outreachHtml = o.subject ? `
      <div class="detail-section">
        <h4>Last Generated Outreach</h4>
        <div class="outreach-block"><div class="outreach-label">Subject</div><div class="outreach-text">${esc(o.subject)}</div></div>
        <div class="outreach-block"><div class="outreach-label">Body</div><div class="outreach-text">${esc(o.body)}</div></div>
        <div class="outreach-block"><div class="outreach-label">LinkedIn</div><div class="outreach-text">${esc(o.linkedin_message)}</div></div>
      </div>` : "";

    openSlide(l.business_name, `
      <div class="detail-section">
        <h4>Contact Info</h4>
        ${detailRow("Website", l.website ? `<a href="${esc(l.website)}" target="_blank">${esc(l.website)}</a>` : "—")}
        ${detailRow("Phone", l.phone || "—")}
        ${detailRow("Email", l.email || "—")}
        ${detailRow("Location", [l.city, l.state, l.country].filter(Boolean).join(", ") || "—")}
        ${detailRow("Lead Score", scorePill(l.lead_score))}
      </div>
      ${enrichHtml}
      ${outreachHtml}
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <button class="btn btn-primary btn-sm" id="slideEnrichBtn" data-id="${l.id}">Re-Enrich</button>
        <button class="btn btn-ghost btn-sm" id="slideOutreachBtn" data-id="${l.id}">Generate Outreach</button>
      </div>
    `);

    document.getElementById("slideEnrichBtn")?.addEventListener("click", async btn => {
      const b = btn.currentTarget;
      b.textContent = "⏳ Enriching…"; b.disabled = true;
      try {
        await api(`/leads/${b.dataset.id}/enrich`, { method: "POST" });
        viewLead(b.dataset.id);
        loadLeads();
      } catch (err) { b.textContent = `❌ ${err.message}`; }
    });

    document.getElementById("slideOutreachBtn")?.addEventListener("click", btn => {
      goToOutreach(btn.currentTarget.dataset.id);
      closeSlide();
    });

  } catch (err) {
    openSlide("Error", `<p class="muted">${esc(err.message)}</p>`);
  }
}

function detailRow(key, val) {
  return `<div class="detail-row"><span class="detail-key">${esc(key)}</span><span class="detail-val">${val}</span></div>`;
}

// ── Enrich single lead from table ─────────────────────────────────────────────
async function enrichLead(id, name, btn) {
  const orig = btn.textContent;
  btn.textContent = "⏳"; btn.disabled = true;
  try {
    await api(`/leads/${id}/enrich`, { method: "POST" });
    btn.textContent = "✅"; btn.disabled = false;
    loadLeads();
  } catch (err) {
    btn.textContent = "❌"; btn.disabled = false;
    btn.title = err.message;
  }
  setTimeout(() => { btn.textContent = orig; }, 2500);
}

// ── PRESETS TAB ───────────────────────────────────────────────────────────────
async function loadPresets() {
  const grid = document.getElementById("presetGrid");
  grid.innerHTML = `<p class="muted">Loading…</p>`;
  const industry = document.getElementById("presetIndustryFilter")?.value || "";
  try {
    const presets = await api(`/presets/india${industry ? `?industry=${industry}` : ""}`);
    if (!presets.length) { grid.innerHTML = `<p class="muted">No presets for this filter.</p>`; return; }
    grid.innerHTML = presets.map(p => `
      <div class="preset-card">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
          <span class="preset-name">${esc(p.name)}</span>
          <span class="industry-chip">${esc(p.industry || "")}</span>
        </div>
        <p class="preset-desc">${esc(p.description)}</p>
        <p class="preset-why"><strong>Why AI:</strong> ${esc(p.why_ai)}</p>
        <ul class="preset-targets">${(p.key_targets || []).map(t => `<li>${esc(t)}</li>`).join("")}</ul>
        <div class="preset-footer">
          <span class="preset-results">Max ${p.max_results} leads · ${esc(p.location)}</span>
          <button class="btn btn-primary btn-sm" data-preset="${p.id}" data-name="${esc(p.name)}">Launch Job</button>
        </div>
      </div>
    `).join("");

    grid.querySelectorAll("[data-preset]").forEach(btn => {
      btn.addEventListener("click", () => launchPresetJob(btn.dataset.preset, btn.dataset.name, btn));
    });

    // Show estimated cost for 50 leads as hint
    try {
      const cost = await api("/enrichment/cost-estimate?lead_count=50");
      const banner = document.getElementById("costEstimateBanner");
      banner.textContent = `💡 Enriching 50 leads costs approx $${cost.estimated_cost_usd} USD (₹${cost.estimated_cost_inr} INR) via Gemini.`;
      banner.classList.remove("hidden");
    } catch (_) {}
  } catch (err) {
    grid.innerHTML = `<p class="muted">Error: ${esc(err.message)}</p>`;
  }
}

async function launchPresetJob(presetId, name, btn) {
  const orig = btn.textContent;
  btn.textContent = "⏳ Launching…"; btn.disabled = true;
  try {
    const res = await api(`/jobs/preset/${presetId}`, { method: "POST" });
    btn.textContent = "✅ Job created!";
    currentJobId = res.job_id;
    setTimeout(() => {
      btn.textContent = orig; btn.disabled = false;
      activateTab("jobs");
      pollJob(res.job_id);
    }, 1500);
  } catch (err) {
    btn.textContent = `❌ ${err.message}`; btn.disabled = false;
    setTimeout(() => { btn.textContent = orig; }, 3000);
  }
}

document.getElementById("presetIndustryFilter")?.addEventListener("change", loadPresets);

// ── OUTREACH TAB ──────────────────────────────────────────────────────────────
function goToOutreach(leadId) {
  document.getElementById("outreachLeadId").value = leadId;
  activateTab("outreach");
}

const outreachForm = document.getElementById("outreachForm");
outreachForm?.addEventListener("submit", async e => {
  e.preventDefault();
  await doGenerateOutreach(false);
});

document.getElementById("regenerateBtn")?.addEventListener("click", async () => {
  await doGenerateOutreach(true);
});

async function doGenerateOutreach(regenerate) {
  const data = new FormData(outreachForm);
  const leadId = data.get("lead_id")?.trim();
  if (!leadId) { setStatus("outreachStatus", "❌ Enter a Lead ID."); return; }

  setStatus("outreachStatus", "⏳ Generating…");
  const body = {
    sender_name: data.get("sender_name"),
    sender_title: data.get("sender_title"),
    tone: data.get("tone"),
    language: data.get("language"),
  };

  const path = regenerate
    ? `/leads/${leadId}/outreach/regenerate`
    : `/leads/${leadId}/outreach`;

  try {
    const res = await api(path, { method: "POST", body: JSON.stringify(body) });
    setStatus("outreachStatus", `✅ Generated for ${esc(res.company_name || leadId)}`);
    renderOutreach(res.outreach);
  } catch (err) {
    setStatus("outreachStatus", `❌ ${err.message}`);
  }
}

function renderOutreach(o) {
  const result = document.getElementById("outreachResult");
  const content = document.getElementById("outreachContent");
  if (!o) { result.style.display = "none"; return; }

  const blocks = [
    { label: "Subject Line", text: o.subject },
    { label: "Email Body", text: o.body },
    { label: "Follow-up Subject", text: o.followup_subject },
    { label: "Follow-up Body", text: o.followup_body },
    { label: "LinkedIn Message (≤300 chars)", text: o.linkedin_message },
    { label: "Key Personalisation", text: o.key_personalization },
  ].filter(b => b.text);

  content.innerHTML = blocks.map(b => `
    <div class="outreach-block">
      <div class="outreach-label">${esc(b.label)}</div>
      <div class="outreach-text">${esc(b.text)}</div>
      <button class="btn btn-ghost btn-xs outreach-copy-btn" data-copy="${esc(b.text)}">Copy</button>
    </div>
  `).join("");

  content.querySelectorAll("[data-copy]").forEach(btn => {
    btn.addEventListener("click", () => {
      navigator.clipboard.writeText(btn.dataset.copy).then(() => {
        btn.textContent = "Copied!";
        setTimeout(() => { btn.textContent = "Copy"; }, 1500);
      });
    });
  });

  result.style.display = "flex";
}

document.getElementById("copyAllBtn")?.addEventListener("click", () => {
  const texts = [...document.querySelectorAll(".outreach-text")].map(el => el.textContent).join("\n\n---\n\n");
  navigator.clipboard.writeText(texts).then(() => {
    const btn = document.getElementById("copyAllBtn");
    btn.textContent = "Copied!";
    setTimeout(() => { btn.textContent = "Copy All"; }, 1500);
  });
});

// ── SETTINGS TAB ──────────────────────────────────────────────────────────────
document.getElementById("apiBaseSettings")?.addEventListener("input", e => {
  document.getElementById("apiBase").value = e.target.value;
});

document.getElementById("saveSettings")?.addEventListener("click", () => {
  const val = document.getElementById("apiBaseSettings").value;
  document.getElementById("apiBase").value = val;
  alert("API base URL updated.");
});

document.getElementById("calcCostBtn")?.addEventListener("click", async () => {
  const count = document.getElementById("costLeadCount")?.value || 100;
  const result = document.getElementById("costResult");
  result.classList.add("hidden");
  try {
    const data = await api(`/enrichment/cost-estimate?lead_count=${count}`);
    result.innerHTML = `
      <div class="cost-row"><span>Lead count</span><strong>${data.lead_count}</strong></div>
      <div class="cost-row"><span>Input tokens (est.)</span><strong>${data.estimated_input_tokens.toLocaleString()}</strong></div>
      <div class="cost-row"><span>Output tokens (est.)</span><strong>${data.estimated_output_tokens.toLocaleString()}</strong></div>
      <div class="cost-row"><span>Cost (USD)</span><strong>$${data.estimated_cost_usd}</strong></div>
      <div class="cost-row"><span>Cost (INR)</span><strong>₹${data.estimated_cost_inr}</strong></div>
      <div class="cost-row"><span>Model</span><strong>${data.model}</strong></div>
      <p style="margin-top:8px;font-size:11px;color:var(--muted);">${data.note}</p>
    `;
    result.classList.remove("hidden");
  } catch (err) {
    result.innerHTML = `<p class="muted">Error: ${esc(err.message)}</p>`;
    result.classList.remove("hidden");
  }
});

// ── Utils ─────────────────────────────────────────────────────────────────────
function setStatus(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
}

function esc(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  } catch { return iso; }
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// ── Init ──────────────────────────────────────────────────────────────────────
activateTab("jobs");
