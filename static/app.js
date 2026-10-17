/* ---------------------------------------------------------------
   app.js — Symptom Triage Helper front end.
   The expert system lives on the server (app.py); this file only asks
   the questions it returns and shows its explanation. Nothing is stored.
   --------------------------------------------------------------- */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const screens = { start: $("screen-start"), question: $("screen-question"), result: $("screen-result") };
  const OFFLINE_HELP = "Couldn't reach the checker. If it might be an emergency, call your local emergency number now.";

  /* ── Theme: follows the system until the user picks ───────────── */
  const themeToggle = $("theme-toggle");
  const systemDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  const THEME_KEY = "triage-theme";

  function savedTheme() {
    try {
      const v = localStorage.getItem(THEME_KEY);
      return v === "light" || v === "dark" ? v : "auto";
    } catch (err) { return "auto"; }
  }

  function applyTheme() {
    const mode = savedTheme();
    const dark = mode === "auto" ? !!(systemDark && systemDark.matches) : mode === "dark";
    const root = document.documentElement;
    root.setAttribute("data-theme", dark ? "dark" : "light");
    root.setAttribute("data-theme-mode", mode);
    const names = { auto: "Auto", light: "Light", dark: "Dark" };
    const next = { auto: "light", light: "dark", dark: "auto" }[mode];
    $("theme-label").textContent = names[mode];
    themeToggle.setAttribute("aria-label",
      `Theme: ${mode === "auto" ? "follows your system" : mode}. Activate to switch to ${next === "auto" ? "follow your system" : next}.`);
  }

  themeToggle.addEventListener("click", () => {
    const next = { auto: "light", light: "dark", dark: "auto" }[savedTheme()];
    try {
      if (next === "auto") localStorage.removeItem(THEME_KEY);
      else localStorage.setItem(THEME_KEY, next);
    } catch (err) { /* private mode: ignore */ }
    applyTheme();
  });
  if (systemDark) {
    const onChange = () => { if (savedTheme() === "auto") applyTheme(); };
    if (systemDark.addEventListener) systemDark.addEventListener("change", onChange);
    else if (systemDark.addListener) systemDark.addListener(onChange);
  }
  applyTheme();

  /* ── Helpers ──────────────────────────────────────────────────── */
  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([k, v]) => {
      if (k === "text") node.textContent = v;
      else if (k in node) node[k] = v;
      else node.setAttribute(k, v);
    });
    children.flat().forEach((c) => { if (c != null) node.append(c); });
    return node;
  }

  function svgIcon(name, size) {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "ic");
    svg.setAttribute("width", size);
    svg.setAttribute("height", size);
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(ns, "use");
    use.setAttribute("href", `#i-${name}`);
    svg.append(use);
    return svg;
  }

  function announce(message) {
    const status = $("status");
    status.textContent = "";
    window.setTimeout(() => { status.textContent = message; }, 40);
  }

  function show(name, focusEl) {
    Object.entries(screens).forEach(([key, node]) => { node.hidden = key !== name; });
    window.scrollTo({ top: 0, behavior: "auto" });
    if (focusEl) focusEl.focus({ preventScroll: true });
  }

  /* ── Consultation state ───────────────────────────────────────── */
  let facts = {};
  let history = [];   // question ids in the order they were answered
  let busy = false;

  async function ask() {
    const response = await fetch("/triage", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ facts }),
    });
    if (!response.ok) throw new Error("bad response");
    return response.json();
  }

  async function advance(errorTarget) {
    if (busy) return;
    busy = true;
    errorTarget.textContent = "";
    try {
      const data = await ask();
      if (data.done) renderResult(data.result);
      else renderQuestion(data.question, data.progress);
    } catch (err) {
      errorTarget.textContent = OFFLINE_HELP;
    } finally {
      busy = false;
    }
  }

  /* ── Start ────────────────────────────────────────────────────── */
  $("start-btn").addEventListener("click", async () => {
    facts = {};
    history = [];
    const btn = $("start-btn");
    const error = $("start-error");
    btn.classList.add("is-loading");
    await advance(error);
    btn.classList.remove("is-loading");
  });

  /* ── Question screen ──────────────────────────────────────────── */
  let currentQuestion = null;

  function renderQuestion(q, progress) {
    currentQuestion = q;
    $("question-text").textContent = q.text;
    $("question-hint").textContent = q.type === "multi" ? "Choose all that apply." : "Choose one.";

    const pct = Math.round((progress.answered / progress.total) * 100);
    $("progress-text").textContent = `Question ${progress.answered + 1} of about ${progress.total}`;
    $("progress-bar").style.width = `${pct}%`;
    const track = $("progress-track");
    track.setAttribute("aria-valuenow", String(pct));
    track.setAttribute("aria-valuetext", `Question ${progress.answered + 1} of about ${progress.total}`);

    $("why").open = false;
    $("why-text").textContent = q.why;
    $("why-rules").textContent = q.used_by.length
      ? `Your answer is used by ${q.used_by.length} rule${q.used_by.length === 1 ? "" : "s"} in the knowledge base (${q.used_by.join(", ")}).`
      : "";

    const options = $("options");
    const cont = $("continue-btn");
    options.replaceChildren();

    if (q.type === "single") {
      cont.hidden = true;
      q.options.forEach((o) => {
        const b = el("button", { type: "button", className: "option", text: o.label });
        b.addEventListener("click", () => answer(q.id, o.value));
        options.append(b);
      });
    } else {
      cont.hidden = false;
      cont.disabled = true;
      q.options.forEach((o) => {
        const input = el("input", { type: "checkbox", value: o.value });
        const box = el("span", { className: "box" }, svgIcon("check", 16));
        options.append(el("label", { className: "option" }, input, box, el("span", { text: o.label })));
      });
    }

    $("back-btn").hidden = false;
    show("question", $("question-text"));
    announce($("progress-text").textContent + ": " + q.text);
  }

  // "None of these" is exclusive; picking anything else clears it.
  $("options").addEventListener("change", (e) => {
    if (!currentQuestion || currentQuestion.type !== "multi" || e.target.type !== "checkbox") return;
    const boxes = Array.from($("options").querySelectorAll("input"));
    if (e.target.value === "none" && e.target.checked) boxes.forEach((b) => { if (b !== e.target) b.checked = false; });
    else if (e.target.checked) boxes.forEach((b) => { if (b.value === "none") b.checked = false; });
    $("continue-btn").disabled = !boxes.some((b) => b.checked);
  });

  $("continue-btn").addEventListener("click", () => {
    const values = Array.from($("options").querySelectorAll("input:checked")).map((b) => b.value);
    if (values.length) answer(currentQuestion.id, values);
  });

  function answer(id, value) {
    if (busy) return;
    facts[id] = value;
    history.push(id);
    advance($("error"));
  }

  $("back-btn").addEventListener("click", () => {
    if (busy) return;
    $("error").textContent = "";
    if (!history.length) {
      show("start", $("start-title"));
      return;
    }
    delete facts[history.pop()];
    advance($("error"));
  });

  /* ── Result screen ────────────────────────────────────────────── */
  const LEVEL_ICONS = { emergency: "alert", urgent: "clock", soon: "calendar", selfcare: "home" };
  let lastResult = null;

  function fillList(list, items) {
    list.replaceChildren(...items);
  }

  function ruleItem(rule, withIf) {
    const li = el("li");
    if (!withIf) {
      li.append(rule.then, el("br"), el("span", { className: "rule-tag", text: `Rule ${rule.id}` }));
      return li;
    }
    li.append(
      el("div", { className: "rule-head", text: `Rule ${rule.id} · ${rule.level_label}` }),
      el("div", { className: "conds" }, el("span", { className: "kw", text: "IF" }), rule.if.join("  AND  ")),
      el("div", null, el("span", { className: "kw", text: "THEN" }), rule.then),
    );
    return li;
  }

  function renderResult(r) {
    lastResult = r;
    const card = $("result-card");
    card.className = `result-card level-${r.key}`;
    $("result-icon").setAttribute("href", `#i-${LEVEL_ICONS[r.key]}`);
    $("result-label").textContent = r.label;
    $("result-action").textContent = r.action;

    fillList($("reasons"), r.reasons.map((x) => ruleItem(x, false)));
    $("also-wrap").hidden = r.also_noted.length === 0;
    fillList($("also"), r.also_noted.map((x) => ruleItem(x, false)));
    fillList($("advice"), r.advice.map((t) => el("li", { text: t })));
    $("watch-card").hidden = r.watch_for.length === 0;
    fillList($("watch"), r.watch_for.map((t) => el("li", { text: t })));

    $("resolution").textContent = r.resolution;
    $("answers").replaceChildren(...r.answers.flatMap((a) => [el("dt", { text: a.question }), el("dd", { text: a.answer })]));
    fillList($("trace"), r.trace.map((x) => ruleItem(x, true)));
    $("disclaimer").textContent = r.disclaimer;

    document.title = `${r.label} — Symptom Triage Helper`;
    show("result", $("result-label"));
    announce(`Result: ${r.label}. ${r.action}`);
  }

  function summaryText(r) {
    const lines = [
      `Symptom Triage Helper result: ${r.label}`,
      r.action,
      "",
      "Why:",
      ...r.reasons.map((x) => `- ${x.then} (rule ${x.id})`),
    ];
    if (r.also_noted.length) lines.push("", "Also noted:", ...r.also_noted.map((x) => `- ${x.then} (rule ${x.id})`));
    lines.push("", "What to do now:", ...r.advice.map((t) => `- ${t}`));
    if (r.watch_for.length) lines.push("", "Get care sooner if:", ...r.watch_for.map((t) => `- ${t}`));
    lines.push("", "Answers:", ...r.answers.map((a) => `- ${a.question}: ${a.answer}`), "", r.disclaimer);
    return lines.join("\n");
  }

  $("copy-btn").addEventListener("click", async () => {
    if (!lastResult) return;
    const label = $("copy-text");
    try {
      await navigator.clipboard.writeText(summaryText(lastResult));
      label.textContent = "Copied!";
    } catch (err) {
      label.textContent = "Couldn't copy";
    }
    window.setTimeout(() => { label.textContent = "Copy summary"; }, 2000);
  });

  $("print-btn").addEventListener("click", () => {
    document.querySelector(".how").open = true;
    window.print();
  });

  $("again-btn").addEventListener("click", () => {
    facts = {};
    history = [];
    lastResult = null;
    document.title = "Symptom Triage Helper — How Urgent Is It?";
    $("start-error").textContent = "";
    show("start", $("start-title"));
  });
})();
