const $ = (id) => document.getElementById(id);
const applyTheme = (theme) => {
  document.documentElement.dataset.theme = theme;
  const light = theme === "light";
  $("themeBtn").textContent = light ? "☾" : "☼";
  $("themeBtn").title = light ? "Switch to dark theme" : "Switch to light theme";
  $("themeBtn").setAttribute("aria-label", $("themeBtn").title);
  document.querySelector('meta[name="theme-color"]').content = light ? "#edf3f5" : "#070b10";
};
const savedTheme = localStorage.getItem("asg_theme");
const initialTheme = savedTheme || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
applyTheme(initialTheme);
const store = {
  get baseUrl() { return localStorage.getItem("asg_base") || "http://127.0.0.1:8000"; },
  get token() { return localStorage.getItem("asg_token") || ""; },
  set(base, token) { localStorage.setItem("asg_base", base); localStorage.setItem("asg_token", token); }
};
const shotUrls = new Map();
let liveOn = false;
let refreshing = false;
let selectedAgent = null;
let previousAgentFocus = null;
let currentAgents = [];

async function api(path, opts = {}) {
  const response = await fetch(store.baseUrl + path, {
    ...opts,
    headers: { "X-API-Token": store.token, "Content-Type": "application/json", ...(opts.headers || {}) }
  });
  if (response.status === 401) throw new Error("Unauthorized — check the API token in settings.");
  if (response.status === 403) throw new Error("Forbidden — this screen is private to its backend PC.");
  if (!response.ok) throw new Error("Backend returned HTTP " + response.status);
  return response.json();
}

const esc = (value) => String(value ?? "").replace(/[&<>\"]/g, (char) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;"
}[char]));
const time = (timestamp) => timestamp ? new Date(timestamp * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—";
const dateTime = (timestamp) => timestamp ? new Date(timestamp * 1000).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";

function setConn(ok, message) {
  $("connDot").className = "dot " + (ok ? "ok" : "error");
  $("connText").textContent = message;
}

function renderAgentCards() {
  const query = $("agentSearch").value.trim().toLocaleLowerCase();
  const status = $("agentStatusFilter").value;
  const visible = currentAgents.filter((agent) =>
    (status === "all" || agent.status === status) &&
    (!query || `${agent.name} ${agent.last_summary || ""}`.toLocaleLowerCase().includes(query)));
  $("agentGridCount").textContent = `${visible.length} of ${currentAgents.length} shown`;
  $("agents").innerHTML = visible.length ? visible.map((agent) => `
    <article class="agent-card ${agent.status === "error" ? "error" : ""}" data-agent="${esc(agent.name)}" tabindex="0" role="button" aria-label="Open ${esc(agent.name)} details">
      <div class="agent-card-head"><span class="dot ${esc(agent.status)}"></span><span>${esc(agent.name)}</span></div>
      <p>${esc(agent.last_summary || "No status reported")}</p>
      <time>Last run ${dateTime(agent.last_run)}</time>
    </article>`).join("") : `<div class="empty-small">No agents match these filters.</div>`;
}

function renderAgents(agents) {
  currentAgents = agents;
  const working = agents.filter((agent) => agent.status === "working").length;
  const errors = agents.filter((agent) => agent.status === "error").length;
  $("agentCount").textContent = String(agents.length);
  $("workingCount").textContent = String(working);
  $("errorCount").textContent = String(errors);
  $("coreStatus").textContent = errors ? "ATTENTION REQUIRED" : working ? "SYSTEM ACTIVE" : "SYSTEM STANDBY";
  $("coreHeadline").textContent = errors ? `${errors} agent${errors === 1 ? "" : "s"} need review` : "Command workspace";
  $("agentNodes").innerHTML = agents.slice(0, 4).map((agent) => `
    <div class="agent-node"><span class="dot ${esc(agent.status)}"></span><span>${esc(agent.name)}</span></div>`).join("");
  renderAgentCards();
  if (selectedAgent) {
    selectedAgent = agents.find((agent) => agent.name === selectedAgent.name) || selectedAgent;
    updateAgentDetail(selectedAgent);
  }
}

function getAgentFromCards(name) {
  return currentAgents.find((agent) => agent.name === name) || {
    name, status: "idle", last_run: null, last_summary: "Loading agent status."
  };
}

function updateAgentDetail(agent) {
  $("agentDetailName").textContent = agent.name;
  $("agentDetailStatus").textContent = agent.status;
  $("agentDetailDot").className = "dot " + agent.status;
  $("agentDetailLastRun").textContent = `Last run ${dateTime(agent.last_run)}`;
  $("agentDetailSummary").textContent = agent.last_summary || "No status reported.";
  $("agentRunBtn").disabled = agent.status === "paused";
  $("agentRunBtn").title = agent.status === "paused" ? "Resume this agent before requesting a run" : "Request an immediate run";
  $("agentPauseBtn").textContent = agent.status === "paused" ? "Resume agent" : "Pause agent";
  $("agentPauseBtn").dataset.paused = String(agent.status === "paused");
}

function runDuration(startedAt, finishedAt) {
  if (!finishedAt) return "in progress";
  const seconds = Math.max(0, Math.round(finishedAt - startedAt));
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

async function refreshAgentRuns(agentName) {
  const runs = await api(`/api/agents/${encodeURIComponent(agentName)}/runs?limit=12`);
  if (selectedAgent?.name !== agentName) return;
  $("agentRunHistory").innerHTML = runs.length ? runs.map((run) => `
    <article class="run-line">
      <div class="run-meta"><span class="run-status ${esc(run.status)}">${esc(run.status)}</span><time>${dateTime(run.started_at)}</time><span>${runDuration(run.started_at, run.finished_at)}</span></div>
      <p>${esc(run.summary || (run.status === "working" ? "Agent is running…" : "No run summary."))}</p>
    </article>`).join("") : `<div class="empty-small">No runs recorded yet.</div>`;
}

async function openAgentDetail(agent, focusTarget = null) {
  selectedAgent = agent;
  previousAgentFocus = focusTarget;
  updateAgentDetail(agent);
  $("agentModal").classList.remove("hidden");
  $("agentModal").setAttribute("aria-hidden", "false");
  $("agentDetailActivity").innerHTML = `<div class="empty-small">Loading recent activity…</div>`;
  $("agentRunHistory").innerHTML = `<div class="empty-small">Loading run history…</div>`;
  $("agentDetailError").classList.add("hidden");
  $("agentPauseBtn").focus();
  try {
    const query = new URLSearchParams({ limit: "30", agent: agent.name });
    const [activity] = await Promise.all([
      api("/api/activity?" + query.toString()), refreshAgentRuns(agent.name)
    ]);
    if (selectedAgent?.name === agent.name) renderFeed(activity, "agentDetailActivity");
  } catch (error) {
    $("agentDetailActivity").innerHTML = `<div class="empty-small">Could not load activity.</div>`;
    showAgentDetailError(error.message);
  }
}

function closeAgentDetail() {
  $("agentModal").classList.add("hidden");
  $("agentModal").setAttribute("aria-hidden", "true");
  selectedAgent = null;
  previousAgentFocus?.focus();
}

function showAgentDetailError(message) {
  $("agentDetailError").textContent = message;
  $("agentDetailError").classList.remove("hidden");
}

async function toggleAgentPause() {
  if (!selectedAgent) return;
  const agentName = selectedAgent.name;
  const paused = $("agentPauseBtn").dataset.paused !== "true";
  const button = $("agentPauseBtn");
  button.disabled = true;
  button.textContent = paused ? "Pausing…" : "Resuming…";
  $("agentDetailError").classList.add("hidden");
  try {
    await api(`/api/agents/${encodeURIComponent(agentName)}/pause`, {
      method: "POST", body: JSON.stringify({ paused })
    });
    await tick();
    const agents = await api("/api/agents");
    const updated = agents.find((agent) => agent.name === agentName);
    if (updated) await openAgentDetail(updated, previousAgentFocus);
  } catch (error) {
    showAgentDetailError(error.message);
  } finally {
    button.disabled = false;
  }
}

async function runAgentNow() {
  if (!selectedAgent) return;
  const button = $("agentRunBtn");
  const previousText = button.textContent;
  button.disabled = true;
  button.textContent = "Requesting…";
  $("agentDetailError").classList.add("hidden");
  try {
    await api(`/api/agents/${encodeURIComponent(selectedAgent.name)}/run`, { method: "POST" });
    button.textContent = "Run queued";
    await tick();
    window.setTimeout(() => refreshAgentRuns(agentName).catch(showAgentDetailError), 1200);
  } catch (error) {
    showAgentDetailError(error.message);
    button.textContent = previousText;
  } finally {
    window.setTimeout(() => {
      if (button.isConnected && button.textContent === "Run queued") button.textContent = "Run now";
      button.disabled = !selectedAgent || selectedAgent.status === "paused";
    }, 1800);
  }
}

function renderFeed(items, targetId) {
  $(targetId).innerHTML = items.length ? items.map((item) => `
    <div class="activity-line"><time>${time(item.ts)}</time><div><b>${esc(item.agent)}</b>
      <p class="k-${esc(item.kind)}">${esc(item.message).split("\n")[0]}</p></div></div>`).join("") :
    `<div class="empty-small">No activity recorded yet.</div>`;
}

function renderHeadlines(items) {
  const important = items.filter((item) => ["approval", "warn", "error"].includes(item.kind));
  const headlines = (important.length ? important : items).slice(0, 4);
  $("headlines").innerHTML = headlines.length ? headlines.map((item) => `
    <article class="headline"><div class="headline-title">${esc(item.agent)} · ${esc(item.kind)}</div>
      <div class="headline-meta">${dateTime(item.ts)}</div><p>${esc(item.message).split("\n")[0]}</p></article>`).join("") :
    `<div class="empty-small">No activity highlights yet.</div>`;
}

async function shotUrl(name) {
  if (shotUrls.has(name)) return shotUrls.get(name);
  const response = await fetch(store.baseUrl + "/api/shots/" + encodeURIComponent(name), {
    headers: { "X-API-Token": store.token }
  });
  if (!response.ok) return null;
  const url = URL.createObjectURL(await response.blob());
  shotUrls.set(name, url);
  return url;
}

async function renderApprovals(items) {
  $("taskBadge").textContent = String(items.length);
  const wrap = $("approvals");
  wrap.innerHTML = items.length ? "" : `<div class="empty-small">The queue is clear. New proposals will appear here for your review.</div>`;
  for (const approval of items) {
    const card = document.createElement("article");
    card.className = "appr" + (approval.kind === "control" ? " ctrl" : "");
    let content = `<h3>${esc(approval.title)}</h3><div class="who">${esc(approval.agent)} · ${dateTime(approval.ts)}</div>`;
    let approveText = "Approve";
    if (approval.kind === "control") {
      try {
        const spec = JSON.parse(approval.detail);
        const params = Object.entries(spec.params || {}).map(([key, value]) => `${key}=${value}`).join(" ");
        content += `<div class="ctrlbox"><b>⌁ ${esc(spec.action)}</b> <code>${esc(params)}</code><div class="why">${esc(spec.reason || "")}</div></div>`;
        if (spec.shot) {
          const url = await shotUrl(spec.shot);
          if (url) content += `<img class="ctrlshot" src="${url}" alt="Screen at proposal time">`;
        }
        approveText = "Approve & run";
      } catch {
        content += `<pre>${esc(approval.detail)}</pre>`;
      }
    } else {
      content += `<pre>${esc(approval.detail)}</pre>`;
    }
    content += `<div class="row"><button class="yes" data-approval="${Number(approval.id)}" data-decision="approved">${approveText}</button>` +
      `<button class="no" data-approval="${Number(approval.id)}" data-decision="rejected">Reject</button></div>`;
    card.innerHTML = content;
    wrap.appendChild(card);
  }
}

async function tick() {
  if (refreshing || !store.token) {
    if (!store.token) setConn(false, "Setup needed");
    return;
  }
  refreshing = true;
  try {
    const [agents, approvals, activity] = await Promise.all([
      api("/api/agents"), api("/api/approvals?status=pending"), api("/api/activity?limit=80")
    ]);
    renderAgents(agents);
    await renderApprovals(approvals);
    renderFeed(activity, "activity");
    renderFeed(activity, "logs");
    renderHeadlines(activity);
    setConn(true, "Connected");
  } catch (error) {
    setConn(false, error.message || "Backend unreachable");
  } finally {
    refreshing = false;
  }
}

async function decide(id, decision) {
  try {
    const result = await api(`/api/approvals/${id}`, { method: "POST", body: JSON.stringify({ decision }) });
    if (result.ok) await tick();
    else addChat("assistant", "That approval could not be updated. Refresh and check its current status.");
  } catch (error) {
    addChat("assistant", error.message);
  }
}

function addChat(role, message) {
  const entry = document.createElement("article");
  entry.className = `chat-message ${role}`;
  entry.innerHTML = `${role === "assistant" ? `<span class="message-tag">AS GROUP COMMAND</span>` : ""}<p>${esc(message)}</p><time class="message-time">${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</time>`;
  $("chatMessages").appendChild(entry);
  $("chatMessages").scrollTop = $("chatMessages").scrollHeight;
}

function speak(message) {
  if (!$("ttsToggle").checked || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(message));
}

async function sendCommand(text) {
  const command = text.trim();
  if (!command) return;
  addChat("user", command);
  $("commandInput").value = "";
  try {
    const result = await api("/api/command", { method: "POST", body: JSON.stringify({ text: command }) });
    addChat("assistant", result.reply);
    speak(result.reply);
    window.setTimeout(tick, 300);
  } catch (error) {
    addChat("assistant", `Command failed: ${error.message}`);
  }
}

function startLiveScreen() {
  if (!store.token || liveOn) return;
  liveOn = true;
  const image = $("screenLive");
  $("screenState").textContent = "Connecting to this PC’s private screen feed…";
  image.src = store.baseUrl + "/api/screen/live?token=" + encodeURIComponent(store.token) + "&fps=5";
  image.onload = () => {
    image.classList.add("ready");
    $("screenState").classList.add("hidden");
    $("screenFeedState").innerHTML = `<i class="tiny-dot"></i> Live on this PC`;
    $("screenFeedState").classList.add("connected");
    $("screenBtn").textContent = "Disconnect";
  };
  image.onerror = () => {
    liveOn = false;
    image.classList.remove("ready");
    image.removeAttribute("src");
    $("screenState").classList.remove("hidden");
    $("screenState").textContent = "Feed unavailable or blocked. Screen access is local to its backend PC.";
    $("screenFeedState").innerHTML = `<i class="tiny-dot"></i> Private feed unavailable here`;
    $("screenFeedState").classList.remove("connected");
    $("screenBtn").textContent = "Retry feed";
  };
}

function stopLiveScreen() {
  const image = $("screenLive");
  image.removeAttribute("src");
  image.classList.remove("ready");
  $("screenState").classList.remove("hidden");
  $("screenState").textContent = "Screen feed disconnected.";
  $("screenFeedState").innerHTML = `<i class="tiny-dot"></i> Feed disconnected`;
  $("screenFeedState").classList.remove("connected");
  $("screenBtn").textContent = "Connect feed";
  liveOn = false;
}

$("commandForm").addEventListener("submit", (event) => {
  event.preventDefault();
  sendCommand($("commandInput").value);
});
$("approvals").addEventListener("click", (event) => {
  const button = event.target.closest("button[data-approval]");
  if (button) decide(Number(button.dataset.approval), button.dataset.decision);
});
$("agents").addEventListener("click", (event) => {
  const card = event.target.closest("[data-agent]");
  if (card) openAgentDetail(getAgentFromCards(card.dataset.agent), card);
});
$("agents").addEventListener("keydown", (event) => {
  const card = event.target.closest("[data-agent]");
  if (card && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    openAgentDetail(getAgentFromCards(card.dataset.agent), card);
  }
});
$("closeAgentDetail").addEventListener("click", closeAgentDetail);
$("agentModal").addEventListener("click", (event) => {
  if (event.target === $("agentModal")) closeAgentDetail();
});
$("agentPauseBtn").addEventListener("click", toggleAgentPause);
$("agentRunBtn").addEventListener("click", runAgentNow);
$("agentSearch").addEventListener("input", renderAgentCards);
$("agentStatusFilter").addEventListener("change", renderAgentCards);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !$("agentModal").classList.contains("hidden")) closeAgentDetail();
});
document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => {
  document.querySelectorAll(".tab").forEach((item) => {
    const active = item === tab;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-view").forEach((view) => view.classList.add("hidden"));
  $("view-" + tab.dataset.tab).classList.remove("hidden");
}));

$("refreshBtn").addEventListener("click", tick);
$("syncBtn").addEventListener("click", tick);
$("themeBtn").addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  localStorage.setItem("asg_theme", theme);
  applyTheme(theme);
});
$("screenBtn").addEventListener("click", () => liveOn ? stopLiveScreen() : startLiveScreen());
$("settingsBtn").addEventListener("click", () => $("settings").classList.toggle("hidden"));
$("closeSettings").addEventListener("click", () => $("settings").classList.add("hidden"));
$("saveSettings").addEventListener("click", () => {
  store.set($("baseUrl").value.trim().replace(/\/$/, ""), $("apiToken").value.trim());
  $("settings").classList.add("hidden");
  stopLiveScreen();
  tick();
  startLiveScreen();
});
$("saveNotes").addEventListener("click", () => {
  localStorage.setItem("asg_notes", $("notesInput").value);
  $("notesStatus").textContent = "Saved on this device";
});
$("notesInput").addEventListener("input", () => { $("notesStatus").textContent = "Unsaved changes"; });
$("micBtn").addEventListener("click", () => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) { addChat("assistant", "Voice input needs a browser with speech recognition support."); return; }
  const recognition = new Recognition();
  recognition.lang = "en-US";
  $("micBtn").classList.add("listening");
  recognition.onresult = (event) => sendCommand(event.results[0][0].transcript);
  recognition.onend = () => $("micBtn").classList.remove("listening");
  recognition.onerror = () => $("micBtn").classList.remove("listening");
  recognition.start();
});

$("baseUrl").value = store.baseUrl;
$("apiToken").value = store.token;
$("notesInput").value = localStorage.getItem("asg_notes") || "";
const updateClock = () => { $("systemClock").textContent = new Date().toLocaleString([], { weekday: "short", hour: "2-digit", minute: "2-digit" }); };
updateClock();
window.setInterval(updateClock, 30000);
tick();
window.setInterval(tick, 3000);
startLiveScreen();
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  window.addEventListener("load", () => navigator.serviceWorker.register("service-worker.js").catch(() => {}));
}
