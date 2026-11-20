const SYSTEM_NAMES = {
  edge_native: "edge 原生",
  qwen35_4b: "Qwen3.5-4B 级联",
  qwen35_2b: "Qwen3.5-2B 级联",
  minicpm5_2b: "MiniCPM5-2B 级联",
  qwen25_omni_3b: "Qwen2.5-Omni-3B 原生",
};
const SCEN = { home: "家居", child: "儿童" };
const STORE = "hvmt-review-v1";

let DATA = null;
let notes = {};
let selected = null;
let filtered = [];

function loadNotes() {
  try { notes = JSON.parse(localStorage.getItem(STORE) || "{}"); } catch (e) { notes = {}; }
}
function saveNotes() {
  localStorage.setItem(STORE, JSON.stringify(notes));
  renderProgress();
}
function avg(scores) {
  if (!scores) return null;
  const v = Object.values(scores).filter((x) => typeof x === "number");
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}
function audioSrc(p) {
  if (!p) return null;
  if (p.startsWith("assets/")) return "../" + p;
  if (p.startsWith("versions/v0.5/")) return "../../" + p.slice("versions/".length);
  return "../" + p;
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

function renderList() {
  const q = document.getElementById("search").value.trim().toLowerCase();
  const scen = document.getElementById("scenario").value;
  const onlyTodo = document.getElementById("onlyTodo").checked;
  filtered = DATA.cases.filter((c) => {
    if (scen && c.scenario !== scen) return false;
    if (onlyTodo && notes[c.id] && notes[c.id].heard) return false;
    if (!q) return true;
    const hay = (c.id + " " + (c.topic || "") + " " + c.turns.map((t) => t.user).join(" ")).toLowerCase();
    return hay.includes(q);
  });
  document.getElementById("list").innerHTML = filtered.map((c) => {
    const n = notes[c.id] || {};
    const cls = c.id === selected ? "item active" : "item";
    const flag = n.heard ? "✓ " : "";
    return `<div class="${cls}" data-id="${esc(c.id)}"><div class="id">${flag}${esc(c.id)}</div>
      <div class="sub">${SCEN[c.scenario] || ""} · ${esc(c.topic || "")} · ${esc(c.turn_design || "")}</div></div>`;
  }).join("");
  document.querySelectorAll(".item").forEach((el) => {
    el.onclick = () => selectCase(el.getAttribute("data-id"));
  });
  renderProgress();
}

function renderProgress() {
  const total = DATA ? DATA.cases.length : 0;
  const heard = Object.values(notes).filter((n) => n.heard).length;
  document.getElementById("progress").textContent = `已听 ${heard} / ${total}`;
}

function renderCase() {
  const c = DATA.cases.find((x) => x.id === selected);
  if (!c) return;
  const n = notes[c.id] || (notes[c.id] = { note: "", heard: false, review: false, agreeEdge: false, agreeCascade: false });
  document.getElementById("noteText").value = n.note || "";
  document.getElementById("heard").checked = !!n.heard;
  document.getElementById("review").checked = !!n.review;
  document.getElementById("agreeEdge").checked = !!n.agreeEdge;
  document.getElementById("agreeCascade").checked = !!n.agreeCascade;

  document.getElementById("meta").innerHTML = `<h2>${esc(c.id)}</h2>
    <div class="tags"><span>${SCEN[c.scenario] || c.scenario}</span><span>${esc(c.topic || "")}</span>
    <span>${esc(c.tool_mode || "")}</span>${c.age_band ? `<span>${esc(c.age_band)}</span>` : ""}
    <span>${esc(c.turn_design || "")}</span></div>`;

  document.getElementById("turns").innerHTML = c.turns.map((t) => {
    const rows = Object.keys(SYSTEM_NAMES).map((sys) => {
      const s = (t.systems && t.systems[sys]) || {};
      const a = avg(s.scores);
      const src = audioSrc(s.audio);
      const score = a == null ? '<span class="score">NA</span>' : `<span class="score">${a.toFixed(2)}</span>`;
      const audio = src ? `<audio controls preload="none" src="${esc(src)}"></audio>` : '<div class="muted">无音频</div>';
      const tool = s.tool_calls && s.tool_calls.length ? `<div class="tool">${esc(JSON.stringify(s.tool_calls).slice(0, 400))}</div>` : "";
      return `<div class="sys"><div class="sysname">${SYSTEM_NAMES[sys]} ${score}</div>
        <div class="answer">${esc(s.text || "（无回答）")}</div>${audio}${tool}</div>`;
    }).join("");
    return `<div class="turn"><div class="user">第 ${t.turn} 轮 · 用户：${esc(t.user)}</div>
      <div class="systems">${rows}</div></div>`;
  }).join("");
}

function selectCase(id) {
  selected = id;
  renderList();
  renderCase();
}

function bindNote(id, key, value) {
  if (!notes[id]) notes[id] = {};
  notes[id][key] = value;
  notes[id].updated = new Date().toISOString();
  saveNotes();
}
document.getElementById("noteText").addEventListener("input", (e) => bindNote(selected, "note", e.target.value));
["heard", "review", "agreeEdge", "agreeCascade"].forEach((k) => {
  document.getElementById(k).addEventListener("change", (e) => {
    bindNote(selected, k, e.target.checked);
    renderList();
  });
});

function download(name, text) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([text], { type: "application/octet-stream" }));
  a.download = name;
  a.click();
}
document.getElementById("exportJson").onclick = () => download("hvmt-review.json", JSON.stringify({ version: 1, notes }, null, 2));
document.getElementById("exportCsv").onclick = () => {
  const rows = [["case_id", "scenario", "topic", "note", "heard", "review", "agree_edge", "agree_cascade", "updated"]];
  for (const c of DATA.cases) {
    const n = notes[c.id] || {};
    rows.push([c.id, c.scenario, c.topic || "", n.note || "", !!n.heard, !!n.review, !!n.agreeEdge, !!n.agreeCascade, n.updated || ""]);
  }
  const csv = rows.map((r) => r.map((x) => '"' + String(x).replace(/"/g, '""') + '"').join(",")).join("\n");
  download("hvmt-review.csv", "\ufeff" + csv);
};

document.getElementById("search").addEventListener("input", renderList);
document.getElementById("scenario").addEventListener("change", renderList);
document.getElementById("onlyTodo").addEventListener("change", renderList);
document.addEventListener("keydown", (e) => {
  if (!e.altKey) return;
  const i = filtered.findIndex((c) => c.id === selected);
  if (i < 0) return;
  if (e.key === "ArrowRight" && i < filtered.length - 1) selectCase(filtered[i + 1].id);
  if (e.key === "ArrowLeft" && i > 0) selectCase(filtered[i - 1].id);
});

loadNotes();
fetch("data.json").then((r) => r.json()).then((d) => {
  DATA = d;
  renderList();
  if (filtered.length) selectCase(filtered[0].id);
});
