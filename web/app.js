"use strict";

// Statuses that mean "still working", so the page keeps polling.
const POLL_STATUSES = new Set(["running", "publishing"]);
const POLL_MS = 2000;

const state = { runId: null, timer: null };
const $ = (selector) => document.querySelector(selector);

// Build DOM nodes safely. User text is always set with textContent, never innerHTML.
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node[key] = value;
  }
  node.append(...children.filter((c) => c !== null && c !== undefined));
  return node;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return body;
}

function toast(message) {
  const t = $("#toast");
  t.textContent = message;
  t.hidden = false;
  clearTimeout(toast.handle);
  toast.handle = setTimeout(() => (t.hidden = true), 4000);
}

// ---- Header and run list ----------------------------------------------------

async function loadHealth() {
  try {
    const h = await api("/api/health");
    $("#health").textContent = h.openai_key_set
      ? "OpenAI key set"
      : "OpenAI key missing: set OPENAI_API_KEY in .env";
  } catch {
    $("#health").textContent = "server unreachable";
  }
}

async function refreshRuns() {
  const runs = await api("/api/runs");
  const list = $("#runs");
  if (!runs.length) {
    list.replaceChildren(el("li", { class: "muted", textContent: "No runs yet" }));
    return;
  }
  list.replaceChildren(
    ...runs.map((r) =>
      el(
        "li",
        { class: r.id === state.runId ? "active" : "" },
        el("button", { type: "button", class: "link", textContent: r.niche, onclick: () => openRun(r.id) }),
        el("span", { class: `badge ${r.status}`, textContent: r.status }),
      ),
    ),
  );
}

// ---- Run detail -------------------------------------------------------------

function openRun(runId) {
  state.runId = runId;
  clearInterval(state.timer);
  loadRun(runId).then((run) => {
    if (run && POLL_STATUSES.has(run.status)) {
      state.timer = setInterval(() => loadRun(runId), POLL_MS);
    }
  });
}

async function loadRun(runId) {
  try {
    const run = await api(`/api/runs/${runId}`);
    if (runId !== state.runId) return null; // the user switched runs while this request was in flight
    render(run);
    refreshRuns().catch(() => {});
    if (!POLL_STATUSES.has(run.status)) clearInterval(state.timer);
    return run;
  } catch (err) {
    clearInterval(state.timer);
    toast(err.message);
    return null;
  }
}

function render(run) {
  const detail = $("#detail");
  // Keep the review form alive between polls so the reviewer's edits are not wiped.
  let editor = detail.querySelector("#editor");
  if (run.status !== "awaiting_approval") editor = null;
  else if (!editor || editor.dataset.run !== run.id) editor = buildEditor(run);

  detail.replaceChildren(
    ...[
      header(run),
      run.error ? el("pre", { class: "error", textContent: run.error }) : null,
      editor,
      results(run),
      ...artifacts(run),
    ].filter(Boolean),
  );
}

function header(run) {
  const when = new Date(run.created_at * 1000).toLocaleString();
  const mode = run.live ? "Live" : "Dry run";
  const video = run.video ? " · video attached" : "";
  return el(
    "div",
    {},
    el(
      "div",
      { class: "row" },
      el("h2", { textContent: run.niche }),
      el("span", { class: `badge ${run.status}`, textContent: run.status }),
    ),
    el("p", { class: "muted", textContent: `${mode} · ${when}${video}` }),
  );
}

function buildEditor(run) {
  const p = run.posts || {};
  const yt = p.youtube || {};
  const tweets = Array.isArray(p.x) ? p.x.join("\n---\n") : p.x || "";
  const area = (id, label, value, rows) =>
    el("label", {}, label, el("textarea", { id, rows, value }));

  const form = el(
    "form",
    { id: "editor", class: "editor" },
    el("h3", { textContent: "Review and edit before publishing" }),
    area("ed-x", "X thread (separate tweets with a line containing ---)", tweets, 6),
    area("ed-linkedin", "LinkedIn", p.linkedin || "", 6),
    area("ed-facebook", "Facebook", p.facebook || "", 4),
    area("ed-instagram", "Instagram caption", p.instagram || "", 4),
    area("ed-tiktok", "TikTok caption", p.tiktok || "", 2),
    el("label", {}, "YouTube title", el("input", { id: "ed-yt-title", value: yt.title || "" })),
    area("ed-yt-desc", "YouTube description", yt.description || "", 4),
    el(
      "div",
      { class: "actions" },
      el("button", {
        type: "button",
        class: "primary",
        textContent: run.live ? "Approve and publish" : "Approve (dry run)",
        onclick: () => decide(run.id, true),
      }),
      el("button", { type: "button", class: "danger", textContent: "Reject", onclick: () => decide(run.id, false) }),
    ),
  );
  form.dataset.run = run.id;
  return form;
}

function readEditor() {
  const value = (id) => document.getElementById(id).value.trim();
  return {
    x: value("ed-x").split(/\n-{3,}\n/).map((s) => s.trim()).filter(Boolean),
    linkedin: value("ed-linkedin"),
    facebook: value("ed-facebook"),
    instagram: value("ed-instagram"),
    tiktok: value("ed-tiktok"),
    youtube: { title: value("ed-yt-title"), description: value("ed-yt-desc") },
  };
}

async function decide(runId, approve) {
  const body = approve ? { approve: true, posts: readEditor() } : { approve: false };
  try {
    await api(`/api/runs/${runId}/approve`, { method: "POST", body: JSON.stringify(body) });
    toast(approve ? "Approved" : "Rejected");
    openRun(runId); // resume polling until the run finishes
  } catch (err) {
    toast(err.message);
  }
}

function results(run) {
  if (!run.results || !run.results.length) return null;
  return el(
    "section",
    { class: "section" },
    el("h3", { textContent: "Publishing results" }),
    el(
      "table",
      {},
      el(
        "tbody",
        {},
        ...run.results.map((r) =>
          el("tr", {}, el("td", { textContent: r.platform }), el("td", { textContent: r.status })),
        ),
      ),
    ),
  );
}

function artifacts(run) {
  const parts = [];
  if (run.has_image) {
    parts.push(
      el(
        "section",
        { class: "section" },
        el("h3", { textContent: "Image" }),
        el("img", { src: `/api/runs/${run.id}/image`, alt: "Generated image", class: "preview" }),
      ),
    );
  }
  if (run.blog) parts.push(textSection("Blog post", run.blog));
  if (run.video_script) parts.push(textSection("Video script", run.video_script));
  return parts;
}

function textSection(title, text) {
  return el("section", { class: "section" }, el("h3", { textContent: title }), el("pre", { textContent: text }));
}

// ---- New run ----------------------------------------------------------------

async function uploadVideo(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/uploads", { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || "Upload failed");
  return body.video_id;
}

$("#new-run").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const file = $("#video").files[0];
    const videoId = file ? await uploadVideo(file) : null;
    const run = await api("/api/runs", {
      method: "POST",
      body: JSON.stringify({
        niche: $("#niche").value.trim(),
        live: $("#live").checked,
        video_id: videoId,
      }),
    });
    form.reset();
    $("#mode-hint").textContent = "Dry run: drafts only. Nothing is posted.";
    openRun(run.id);
    refreshRuns().catch(() => {});
  } catch (err) {
    toast(err.message);
  }
});

$("#live").addEventListener("change", (event) => {
  $("#mode-hint").textContent = event.target.checked
    ? "Live: approved posts go to every platform that has credentials set."
    : "Dry run: drafts only. Nothing is posted.";
});

// ---- Start ------------------------------------------------------------------

loadHealth();
refreshRuns().catch((err) => toast(err.message));
setInterval(() => refreshRuns().catch(() => {}), 10000);
