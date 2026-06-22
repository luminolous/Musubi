"use strict";

const PAIR_COLORS = {
  Chemical: "#60a5fa",
  Disease: "#f87171",
  Virus: "#a78bfa",
  Gene: "#34d399",
};
const ALL_TYPES = ["Chemical", "Disease", "Virus", "Gene"];

const state = {
  lastResponse: null,
  selectedEdgeId: null,
  network: null,
  filters: {
    pairTypes: new Set(),  // empty = show all
    minConfidence: 0.5,
    granularity: "abstract",
  },
};

// ---------- DOM helpers ----------
const $ = (id) => document.getElementById(id);

function show(el, on = true) {
  if (typeof el === "string") el = $(el);
  if (!el) return;
  el.classList.toggle("hidden", !on);
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ---------- Pair type filter UI ----------
function buildPairFilters() {
  const pairs = [];
  for (let i = 0; i < ALL_TYPES.length; i++) {
    for (let j = i; j < ALL_TYPES.length; j++) {
      pairs.push(`${ALL_TYPES[i]}-${ALL_TYPES[j]}`);
    }
  }
  const wrap = $("pairFilters");
  wrap.innerHTML = "";
  pairs.forEach((p) => {
    const id = `pf_${p}`;
    const label = document.createElement("label");
    label.className = "flex items-center gap-1 text-slate-300";
    label.innerHTML = `<input type="checkbox" id="${id}" checked class="accent-violet-500" /><span>${p}</span>`;
    wrap.appendChild(label);
    label.querySelector("input").addEventListener("change", () => {
      if (state.lastResponse) renderGraph(state.lastResponse);
    });
  });
}

function selectedPairTypes() {
  const set = new Set();
  document.querySelectorAll("#pairFilters input[type=checkbox]").forEach((cb) => {
    if (cb.checked) set.add(cb.parentNode.querySelector("span").textContent);
  });
  return set;
}

// ---------- Analyze ----------
async function analyze() {
  const text = $("txtInput").value.trim();
  if (!text) return;
  const gran = document.querySelector('input[name="gran"]:checked').value;
  state.filters.granularity = gran;
  state.filters.minConfidence = parseFloat($("sldConf").value);

  show("overlay", true);
  $("ovText").textContent = "Analyzing...";
  try {
    const res = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        text,
        granularity: gran,
        min_confidence: state.filters.minConfidence,
      }),
    });
    if (!res.ok) {
      const t = await res.text();
      alert(`Analyze failed: ${res.status} ${t}`);
      return;
    }
    const data = await res.json();
    state.lastResponse = data;
    updateStats(data.stats);
    renderGraph(data);
    show("evidencePanel", false);
  } catch (e) {
    alert(`Error: ${e}`);
  } finally {
    show("overlay", false);
  }
}

function updateStats(stats) {
  $("stAb").textContent = stats.total_abstracts;
  $("stSent").textContent = stats.total_sentences;
  $("stEnt").textContent = stats.total_entities;
  $("stEl").textContent = stats.elapsed_seconds;
  show("statsBox", true);
}

// ---------- Graph ----------
function renderGraph(resp) {
  const allowed = selectedPairTypes();
  const edges = resp.edges.filter((e) => allowed.has(e.pair_type));
  const keepKeys = new Set();
  edges.forEach((e) => { keepKeys.add(e.source); keepKeys.add(e.target); });
  const nodes = resp.nodes.filter((n) => keepKeys.has(n.id));

  const maxCount = Math.max(1, ...nodes.map((n) => n.count));
  const maxWeight = Math.max(1, ...edges.map((e) => e.weight));

  const vnNodes = nodes.map((n) => ({
    id: n.id,
    label: n.label,
    title: `${n.type} · count ${n.count}`,
    color: PAIR_COLORS[n.type],
    shape: "dot",
    size: 10 + 25 * (n.count / maxCount),
    font: { color: "#e2e8f0", size: 13 },
  }));
  const vnEdges = edges.map((e) => ({
    id: e.id,
    from: e.source,
    to: e.target,
    width: 1 + 6 * (e.weight / maxWeight),
    title: `${e.pair_type} · weight ${e.weight}`,
    color: { color: "rgba(148,163,184,0.45)", highlight: "#a78bfa" },
  }));

  show("placeholder", nodes.length === 0);

  const data = {
    nodes: new vis.DataSet(vnNodes),
    edges: new vis.DataSet(vnEdges),
  };
  const options = {
    physics: { stabilization: { iterations: 150 }, barnesHut: { gravitationalConstant: -8000 } },
    interaction: { hover: true, tooltipDelay: 150 },
    nodes: { borderWidth: 0 },
    edges: { smooth: { type: "continuous" } },
  };
  if (state.network) state.network.destroy();
  state.network = new vis.Network($("graph"), data, options);

  state.network.on("selectNode", (params) => {
    if (!params.nodes.length) return;
    const id = params.nodes[0];
    const connected = new Set(state.network.getConnectedNodes(id));
    connected.add(id);
    const updates = vnNodes.map((n) => ({
      id: n.id,
      color: connected.has(n.id) ? PAIR_COLORS[nodes.find((x) => x.id === n.id).type] : "rgba(100,116,139,0.4)",
    }));
    data.nodes.update(updates);
  });
  state.network.on("deselectNode", () => {
    const reset = vnNodes.map((n) => ({ id: n.id, color: PAIR_COLORS[nodes.find((x) => x.id === n.id).type] }));
    data.nodes.update(reset);
  });
  state.network.on("selectEdge", (params) => {
    if (!params.edges.length) return;
    renderEvidence(params.edges[0]);
  });
}

// ---------- Evidence ----------
function renderEvidence(edgeId) {
  state.selectedEdgeId = edgeId;
  const items = (state.lastResponse?.evidence || {})[edgeId] || [];
  const body = $("evidenceBody");
  body.innerHTML = "";
  if (!items.length) {
    body.innerHTML = `<div class="text-slate-500 text-xs">No evidence.</div>`;
  } else {
    items.forEach((it) => {
      const div = document.createElement("div");
      div.className = "p-2 rounded bg-slate-800/50 border border-slate-700/40";
      div.innerHTML =
        `<div class="text-[10px] text-slate-500 mb-1">context #${it.context_id}</div>` +
        `<div>${highlightSpans(it.text, it.spans)}</div>`;
      body.appendChild(div);
    });
  }
  show("evidencePanel", true);
}

function highlightSpans(text, spans) {
  if (!spans.length) return escapeHtml(text);
  const sorted = [...spans].sort((a, b) => a.start - b.start);
  let out = "";
  let cur = 0;
  for (const s of sorted) {
    if (s.start < cur) continue; // skip overlapping
    out += escapeHtml(text.slice(cur, s.start));
    out += `<span class="ent ent-${s.type}" title="${s.type} · ${s.confidence.toFixed(2)}">${escapeHtml(text.slice(s.start, s.end))}</span>`;
    cur = s.end;
  }
  out += escapeHtml(text.slice(cur));
  return out;
}

// ---------- PubMed modal ----------
function openModal() {
  $("modalErr").classList.add("hidden");
  $("modalQuery").value = "";
  show("modal", true);
  $("modalQuery").focus();
}
function closeModal() { show("modal", false); }

async function pubmedFetch() {
  const q = $("modalQuery").value.trim();
  const max = parseInt($("modalMax").value, 10) || 10;
  if (!q) return;
  $("modalErr").classList.add("hidden");
  $("modalFetch").disabled = true;
  $("modalFetch").textContent = "Fetching...";
  try {
    const res = await fetch("/pubmed-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, max_results: max }),
    });
    if (!res.ok) {
      const t = await res.text();
      const err = $("modalErr");
      err.textContent = `Error ${res.status}: ${t}`;
      err.classList.remove("hidden");
      return;
    }
    const data = await res.json();
    const joined = data.abstracts.map((a) => `${a.title}\n${a.abstract}`).join("\n\n");
    $("txtInput").value = joined;
    closeModal();
  } catch (e) {
    const err = $("modalErr");
    err.textContent = String(e);
    err.classList.remove("hidden");
  } finally {
    $("modalFetch").disabled = false;
    $("modalFetch").textContent = "Fetch";
  }
}

// ---------- Wiring ----------
function debounce(fn, ms) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

window.addEventListener("DOMContentLoaded", () => {
  buildPairFilters();

  $("btnAnalyze").addEventListener("click", analyze);

  $("sldConf").addEventListener("input", () => {
    $("lblConf").textContent = parseFloat($("sldConf").value).toFixed(2);
  });
  $("sldConf").addEventListener("change", debounce(() => {
    if (state.lastResponse) analyze();
  }, 300));

  document.querySelectorAll('input[name="gran"]').forEach((r) => {
    r.addEventListener("change", () => {
      if (state.lastResponse) analyze();
    });
  });

  $("btnPubmed").addEventListener("click", openModal);
  $("modalCancel").addEventListener("click", closeModal);
  $("modalFetch").addEventListener("click", pubmedFetch);
  $("modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });

  $("btnCloseEv").addEventListener("click", () => show("evidencePanel", false));
});
