/* ---------------------------------------------------------------
   app.js — Study Buddy front end.
   Pure helpers (scheduling, sharing, stats) live in logic.js.
   --------------------------------------------------------------- */
(function () {
  "use strict";

  const L = window.StudyLogic;
  const $ = (id) => document.getElementById(id);

  /* ── Elements ─────────────────────────────────────────────────── */
  const els = {
    themeToggle: $("theme-toggle"), themeLabel: $("theme-label"),
    stepper: $("stepper"),
    subjectGrid: $("subject-grid"), customWrap: $("custom-subject-wrap"), customSubject: $("custom-subject"),
    levelGroup: $("level-group"), struggle: $("struggle"),
    timeGrid: $("time-grid"), customMinutes: $("custom-minutes"),
    examName: $("exam-name"), examDate: $("exam-date"), daysNote: $("days-left-note"),
    recommend: $("recommend"), error: $("error"), status: $("status"),
    result: $("result"), resultMeta: $("result-meta"), fitLabel: $("fit-label"), fitBasis: $("fit-basis"),
    methodName: $("method-name"), sharedBanner: $("shared-banner"),
    countdownCard: $("countdown-card"), countdownBadge: $("countdown-badge"),
    countdownHeadline: $("countdown-headline"), countdownTips: $("countdown-tips"),
    whyText: $("why-text"), methodReason: $("method-reason"),
    stepsList: $("steps-list"), stepsProgress: $("steps-progress"), stepsRestore: $("steps-restore"),
    breakdown: $("time-breakdown-list"),
    timerBox: $("timer-box"), timerDisplay: $("timer-display"), timerStatus: $("timer-status"),
    timerStep: $("timer-step"), timerBar: $("timer-bar"), timerToggle: $("timer-toggle"),
    timerToggleIcon: $("timer-toggle-icon"), timerBtnText: $("timer-btn-text"),
    timerNext: $("timer-next"), timerReset: $("timer-reset"),
    timerSound: $("timer-sound"), timerSoundIcon: $("timer-sound-icon"), timerAnnounce: $("timer-announce"),
    timeNote: $("time-note"), timeNoteBox: document.querySelector(".time-note-box"),
    alternativesCard: document.querySelector(".alternatives-card"), alternativesList: $("alternatives-list"),
    ruleTrace: $("rule-trace"),
    copyBtn: $("copy-btn"), copyText: $("copy-text"), shareBtn: $("share-btn"), shareText: $("share-text"),
    pdfBtn: $("pdf-btn"), again: $("again"), actionStatus: $("action-status"),
    markDone: $("mark-done"), sessionSummary: $("session-summary"),
    ratingPanel: $("rating-panel"), ratingGroup: $("rating-group"), ratingResult: $("rating-result"),
    reminderPanel: $("reminder-panel"), reminderHint: $("reminder-hint"), reminderOptions: $("reminder-options"),
    reminderSet: $("reminder-set"), reminderIcs: $("reminder-ics"), reminderStatus: $("reminder-status"),
    duePanel: $("due-panel"), dueList: $("due-list"),
    statSessions: $("stat-sessions"), statTime: $("stat-time"), statStreak: $("stat-streak"), statRating: $("stat-rating"),
    weekChart: $("week-chart"), weekSummary: $("week-summary"),
    methodsList: $("methods-list"), reviewsList: $("reviews-list"), resetData: $("reset-data"),
    confetti: $("confetti"),
    installBtn: $("install-btn"), tabbar: $("tabbar"),
    todayStreak: $("today-streak"), todayMinutes: $("today-minutes"), todayReviews: $("today-reviews"),
  };

  const BASE_TITLE = document.title;
  const KEYS = {
    theme: "study-buddy-theme",
    sessions: "study-buddy-sessions",
    reviews: "study-buddy-reviews",
    sound: "study-buddy-sound",
    legacyProgress: "study-buddy-progress",
    legacyFeedback: "study-buddy-rule-feedback",
  };
  const LEVEL_LABELS = { beginner: "Beginner", intermediate: "Intermediate", advanced: "Advanced" };
  const reducedMotion = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── Helpers ──────────────────────────────────────────────────── */
  const store = {
    get(key, fallback) {
      try {
        const raw = localStorage.getItem(key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch (err) { return fallback; }
    },
    set(key, value) {
      try { localStorage.setItem(key, JSON.stringify(value)); return true; } catch (err) { return false; }
    },
    getRaw(key) {
      try { return localStorage.getItem(key); } catch (err) { return null; }
    },
    setRaw(key, value) {
      try { localStorage.setItem(key, value); } catch (err) { /* private mode: ignore */ }
    },
    remove(key) {
      try { localStorage.removeItem(key); } catch (err) { /* ignore */ }
    },
  };

  function el(tag, props, ...children) {
    const node = document.createElement(tag);
    Object.entries(props || {}).forEach(([key, value]) => {
      if (key === "dataset") Object.assign(node.dataset, value);
      else if (key === "text") node.textContent = value;
      else if (key in node && key !== "role") node[key] = value;
      else node.setAttribute(key, value);
    });
    children.flat().forEach((child) => {
      if (child != null) node.append(child);
    });
    return node;
  }

  function icon(name, size) {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "ic");
    svg.setAttribute("width", size || 18);
    svg.setAttribute("height", size || 18);
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", `#i-${name}`);
    svg.append(use);
    return svg;
  }

  let uid = 0;
  const nextId = (prefix) => `${prefix}${Date.now().toString(36)}${(uid++).toString(36)}`;

  function announce(message) {
    els.status.textContent = "";
    window.setTimeout(() => { els.status.textContent = message; }, 40);
  }

  function setActionStatus(message) {
    els.actionStatus.textContent = message;
  }

  const todayKey = () => L.dayKey(new Date());

  function describeDays(days) {
    if (days === 0) return "today";
    if (days === 1) return "tomorrow";
    return `in ${days} days`;
  }

  function prettyDate(key) {
    const date = L.parseDayKey(key);
    if (!date) return key;
    return date.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric", timeZone: "UTC" });
  }

  /* ── Theme: follows the system until the user picks ───────────── */
  const systemDark = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function themeMode() {
    const saved = store.getRaw(KEYS.theme);
    return saved === "light" || saved === "dark" ? saved : "auto";
  }

  function applyTheme() {
    const mode = themeMode();
    const resolved = mode === "auto" ? (systemDark && systemDark.matches ? "dark" : "light") : mode;
    const root = document.documentElement;
    root.setAttribute("data-theme", resolved);
    root.setAttribute("data-theme-mode", mode);
    const next = { auto: "light", light: "dark", dark: "auto" }[mode];
    const names = { auto: "Auto", light: "Light", dark: "Dark" };
    els.themeLabel.textContent = names[mode];
    els.themeToggle.setAttribute(
      "aria-label",
      `Theme: ${mode === "auto" ? "follows your system" : names[mode].toLowerCase()}. Activate to switch to ${next === "auto" ? "follow your system" : next}.`,
    );
  }

  els.themeToggle.addEventListener("click", () => {
    const next = { auto: "light", light: "dark", dark: "auto" }[themeMode()];
    if (next === "auto") store.remove(KEYS.theme);
    else store.setRaw(KEYS.theme, next);
    applyTheme();
  });
  if (systemDark) {
    const onChange = () => { if (themeMode() === "auto") applyTheme(); };
    if (systemDark.addEventListener) systemDark.addEventListener("change", onChange);
    else if (systemDark.addListener) systemDark.addListener(onChange);
  }
  applyTheme();

  /* ── Form state ───────────────────────────────────────────────── */
  const form = { subject: "", level: "intermediate", preset: "medium" };

  function customMinutesValue() {
    const raw = els.customMinutes.value.trim();
    if (raw === "") return { empty: true };
    const n = Number(raw);
    if (!Number.isInteger(n) || n < L.MIN_MINUTES || n > L.MAX_MINUTES) return { empty: false, valid: false };
    return { empty: false, valid: true, minutes: n };
  }

  /** Minutes the user asked for, or null when the custom entry is invalid. */
  function currentMinutes() {
    const custom = customMinutesValue();
    if (custom.empty) return L.PRESET_MINUTES[form.preset];
    return custom.valid ? custom.minutes : null;
  }

  function examDaysLeft() {
    const date = els.examDate.value;
    if (!date) return null;
    return L.daysBetween(todayKey(), date);
  }

  function updateStepper() {
    const subjectDone = !!form.subject && (form.subject !== "Other" || els.customSubject.value.trim().length > 0);
    const challengeDone = !!els.struggle.value;
    const current = !subjectDone ? 1 : !challengeDone ? 2 : 3;
    els.stepper.querySelectorAll("li").forEach((li) => {
      const n = Number(li.dataset.step);
      const done = n < current;
      li.classList.toggle("done", done);
      li.classList.toggle("current", n === current);
      if (n === current) li.setAttribute("aria-current", "step");
      else li.removeAttribute("aria-current");
      const dot = li.querySelector(".stepper-dot");
      dot.textContent = done ? "✓" : String(n);
      let state = li.querySelector(".sr-only");
      if (!state) {
        state = el("span", { className: "sr-only" });
        li.append(state);
      }
      state.textContent = done ? " (completed)" : n === current ? " (current step)" : "";
    });
  }

  /* ── Step 1: subject ──────────────────────────────────────────── */
  els.subjectGrid.addEventListener("click", (e) => {
    const btn = e.target.closest(".subject");
    if (!btn) return;
    els.subjectGrid.querySelectorAll(".subject").forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-pressed", "false");
    });
    btn.classList.add("active");
    btn.setAttribute("aria-pressed", "true");
    form.subject = btn.dataset.value;
    els.error.textContent = "";

    const isOther = form.subject === "Other";
    els.customWrap.hidden = !isOther;
    if (isOther) els.customSubject.focus();
    loadStruggles();
  });

  let customTimer = null;
  els.customSubject.addEventListener("input", () => {
    els.error.textContent = "";
    els.customSubject.removeAttribute("aria-invalid");
    window.clearTimeout(customTimer);
    customTimer = window.setTimeout(loadStruggles, 450);
    updateStepper();
  });

  /* ── Step 2: level and challenge ──────────────────────────────── */
  els.levelGroup.addEventListener("change", (e) => {
    if (e.target.name !== "level") return;
    form.level = e.target.value;
    if (form.subject) loadStruggles();
  });

  els.struggle.addEventListener("change", () => {
    els.error.textContent = "";
    updateStepper();
  });

  let struggleRequest = 0;
  async function loadStruggles() {
    if (!form.subject) return;
    const token = ++struggleRequest;
    const previous = els.struggle.value;
    els.struggle.disabled = true;
    els.struggle.replaceChildren(new Option("Loading challenges…", "", true, true));
    els.struggle.options[0].disabled = true;
    updateStepper();

    try {
      const res = await fetch("/struggles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: form.subject,
          custom_subject: form.subject === "Other" ? els.customSubject.value : "",
          level: form.level,
        }),
      });
      if (!res.ok) throw new Error("bad response");
      const data = await res.json();
      if (token !== struggleRequest) return;

      const placeholder = new Option("Pick what’s tripping you up…", "", true, true);
      placeholder.disabled = true;
      els.struggle.replaceChildren(placeholder);
      data.struggles.forEach((s) => els.struggle.append(new Option(s, s)));
      if (previous && data.struggles.includes(previous)) els.struggle.value = previous;
      els.struggle.disabled = false;
    } catch (err) {
      if (token !== struggleRequest) return;
      const failed = new Option("Couldn’t load options — pick a subject again", "", true, true);
      failed.disabled = true;
      els.struggle.replaceChildren(failed);
    }
    updateStepper();
  }

  /* ── Step 3: time and deadline ────────────────────────────────── */
  function setPresetActive(active) {
    els.timeGrid.querySelectorAll(".time-btn").forEach((b) => {
      const on = active && b.dataset.value === form.preset;
      b.classList.toggle("active", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }

  els.timeGrid.addEventListener("click", (e) => {
    const btn = e.target.closest(".time-btn");
    if (!btn) return;
    form.preset = btn.dataset.value;
    els.customMinutes.value = "";
    els.customMinutes.removeAttribute("aria-invalid");
    setPresetActive(true);
    els.error.textContent = "";
  });

  els.customMinutes.addEventListener("input", () => {
    const custom = customMinutesValue();
    els.error.textContent = "";
    els.customMinutes.removeAttribute("aria-invalid");
    setPresetActive(custom.empty);
  });

  function updateDaysNote() {
    const days = examDaysLeft();
    els.examDate.removeAttribute("aria-invalid");
    if (days === null) els.daysNote.textContent = "";
    else if (days < 0) {
      els.daysNote.textContent = "That date has already passed.";
      els.examDate.setAttribute("aria-invalid", "true");
    } else {
      els.daysNote.textContent = days === 0 ? "That's today." : `${days} ${days === 1 ? "day" : "days"} left. We'll adjust the plan to fit.`;
    }
  }
  els.examDate.addEventListener("change", () => { els.error.textContent = ""; updateDaysNote(); });
  els.examDate.min = todayKey();

  /* ── Plan state ───────────────────────────────────────────────── */
  let plan = null;
  const planKey = (p) => `${p.subject.toLowerCase()}|${p.struggle.toLowerCase()}`;

  function normalizeRecommendation(data) {
    const fit = data.fit && typeof data.fit === "object" ? data.fit : {};
    data.fit = {
      label: String(fit.label || "Good match"),
      basis: String(fit.basis || "Fit details are unavailable for this recommendation."),
    };
    data.steps = (Array.isArray(data.steps) ? data.steps : []).map(String).filter(Boolean);
    data.alternatives = (Array.isArray(data.alternatives) ? data.alternatives : []).map((a) => ({
      method: String(a.method || ""),
      description: String(a.description || ""),
      why: String(a.why || ""),
      steps: Array.isArray(a.steps) ? a.steps.map(String) : [],
    })).filter((a) => a.method);
    data.why = String(data.why || "");
    data.reason = String(data.reason || "");
    return data;
  }

  /** If earlier ratings for this challenge were poor, lead with a better-rated backup. */
  function applyPriorFeedback(data) {
    const key = `${data.subject.toLowerCase()}|${data.struggle.toLowerCase()}`;
    const legacy = store.get(KEYS.legacyFeedback, {})[key];
    const stats = L.methodStats(store.get(KEYS.sessions, []), key, legacy);
    const choice = L.chooseNextMethod(stats, data.method, data.alternatives);
    if (choice.action !== "switch" || !choice.alternative.steps.length) return false;

    const preferred = choice.alternative;
    const previous = { method: data.method, description: "Your previous recommendation", why: data.why, steps: data.steps };
    data.alternatives = data.alternatives.filter((a) => a !== preferred);
    data.alternatives.unshift(previous);
    data.method = preferred.method;
    data.reason = `Your earlier ratings for this challenge were low, so this plan tries ${preferred.method}. ${preferred.description}`;
    data.why = preferred.why || data.why;
    data.steps = preferred.steps.slice(0, Math.max(1, Math.min(preferred.steps.length, L.stepCap(data.minutes))));
    data.fit = { label: "Feedback-guided", basis: "A backup method was promoted because of your earlier ratings for this challenge." };
    data.rule_used = "feedback";
    return true;
  }

  function makePlan(data, extra) {
    const steps = data.steps.map((text) => ({ id: nextId("s"), text, done: false, skipped: false, editing: false }));
    return {
      subject: data.subject,
      struggle: data.struggle,
      level: data.level || "intermediate",
      minutes: data.minutes,
      exam: extra.exam || "",
      examDate: extra.examDate || "",
      method: data.method,
      reason: data.reason,
      why: data.why,
      alternatives: data.alternatives,
      countdown: data.countdown || null,
      timeNote: data.time_note || "",
      fit: data.fit,
      rule: data.rule_used || "",
      steps,
      original: data.steps.slice(),
      shared: !!extra.shared,
      celebrated: false,
      sessionId: null,
    };
  }

  /* ── Request a plan ───────────────────────────────────────────── */
  function fail(message, field) {
    els.error.textContent = message;
    if (field) {
      field.focus();
      if (field.setAttribute) field.setAttribute("aria-invalid", "true");
    }
  }

  els.recommend.addEventListener("click", async () => {
    els.error.textContent = "";
    if (!form.subject) return fail("Please pick a subject first.", els.subjectGrid.querySelector(".subject"));
    const customSubject = els.customSubject.value.trim();
    if (form.subject === "Other" && !customSubject) return fail("Type the subject you're studying.", els.customSubject);
    if (!els.struggle.value) return fail("Please select what’s tripping you up.", els.struggle);
    const minutes = currentMinutes();
    if (minutes === null) return fail(`Enter between ${L.MIN_MINUTES} and ${L.MAX_MINUTES} whole minutes.`, els.customMinutes);
    const days = examDaysLeft();
    if (days !== null && days < 0) return fail("That deadline has already passed. Pick a date from today onwards.", els.examDate);

    const examName = L.sanitizeText(els.examName.value, 80);
    const examDate = days !== null ? els.examDate.value : "";

    els.recommend.disabled = true;
    els.recommend.classList.add("is-loading");
    els.recommend.setAttribute("aria-busy", "true");
    els.recommend.querySelector(".submit-text").textContent = "Matching your best method…";

    try {
      const response = await fetch("/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject: form.subject,
          custom_subject: form.subject === "Other" ? customSubject : "",
          struggle: els.struggle.value,
          level: form.level,
          minutes,
          exam: examName,
          days_left: days,
        }),
      });
      if (!response.ok) throw new Error("Couldn't get a plan right now. Please try again.");
      const data = normalizeRecommendation(await response.json());
      if (!data.steps.length) throw new Error("The plan came back empty. Please try again.");
      applyPriorFeedback(data);
      showPlan(makePlan(data, { exam: examName, examDate }));
    } catch (err) {
      fail(err instanceof TypeError
        ? (navigator.onLine === false
          ? "You're offline. Your saved progress and shared plans still work; connect to build a new plan."
          : "Couldn't reach the server. Check your connection and try again.")
        : err.message);
    } finally {
      els.recommend.disabled = false;
      els.recommend.classList.remove("is-loading");
      els.recommend.setAttribute("aria-busy", "false");
      els.recommend.querySelector(".submit-text").textContent = "Find my study method";
    }
  });

  /* ── Render the plan ──────────────────────────────────────────── */
  function showPlan(next, options) {
    plan = next;
    resetTimer();
    renderPlan();
    resetSessionPanels();

    els.result.hidden = false;
    if (!reducedMotion()) {
      els.result.classList.remove("is-entering");
      void els.result.offsetWidth; // restart the entrance animation
      els.result.classList.add("is-entering");
      els.result.addEventListener("animationend", function done(e) {
        if (e.target !== els.result) return;
        els.result.classList.remove("is-entering");
        els.result.removeEventListener("animationend", done);
      });
    }
    if (!options || options.focus !== false) {
      els.methodName.focus({ preventScroll: true });
      els.result.scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "start" });
    }
    announce(`Your plan is ready: ${plan.method}.`);
  }

  function renderPlan() {
    els.methodName.textContent = plan.method;
    els.resultMeta.textContent = [plan.subject, plan.struggle, LEVEL_LABELS[plan.level], L.formatMinutes(plan.minutes)].join(" · ");
    els.fitLabel.textContent = `${plan.fit.label} · rule fit, not a probability`;
    els.fitBasis.textContent = plan.fit.basis;
    // First sentence only: it names the method, the subject and the challenge.
    els.whyText.textContent = (plan.why.split(/(?<=\.)\s/)[0]) || plan.reason;
    els.methodReason.textContent = plan.why ? plan.reason : "";
    els.methodReason.hidden = !plan.why || !plan.reason;
    els.sharedBanner.hidden = !plan.shared;

    els.timeNote.textContent = plan.timeNote;
    els.timeNoteBox.hidden = !plan.timeNote;
    els.ruleTrace.textContent = plan.shared
      ? `Shared plan for ${plan.subject.toLowerCase()}: ${plan.struggle.toLowerCase()}.`
      : `Matched to your ${plan.subject.toLowerCase()} challenge: ${plan.struggle.toLowerCase()} (${LEVEL_LABELS[plan.level].toLowerCase()}).`;

    renderCountdown();
    renderAlternatives();
    renderSteps();
    rebuildTimeline();
  }

  function renderCountdown() {
    const days = plan.examDate ? L.daysBetween(todayKey(), plan.examDate) : null;
    const usable = days !== null && days >= 0;
    const hasContent = plan.countdown && (!plan.shared || plan.countdown.daysAtShare === days);
    els.countdownCard.hidden = !(plan.examDate || plan.countdown);
    if (els.countdownCard.hidden) return;

    const label = plan.exam || "your deadline";
    els.countdownBadge.textContent = days === null ? "" : days < 0 ? "Passed" : days === 0 ? "Today" : `${days} ${days === 1 ? "day" : "days"} left`;
    els.countdownBadge.hidden = days === null;

    let headline = "";
    let tips = [];
    if (hasContent && usable) {
      headline = plan.countdown.headline;
      tips = plan.countdown.tips;
    } else if (days !== null && days < 0) {
      headline = `The date for ${label} has passed.`;
    } else if (usable) {
      headline = `${label} is ${describeDays(days)}. This plan was made on a different day, so check its steps against the time you have left.`;
    }
    els.countdownHeadline.textContent = headline;
    els.countdownTips.replaceChildren(...tips.map((t) => el("li", { text: t })));
  }

  function renderAlternatives() {
    els.alternativesList.replaceChildren();
    els.alternativesCard.hidden = plan.alternatives.length === 0;
    plan.alternatives.forEach((alt) => {
      const item = el("li", null, el("strong", { text: alt.method }), ` — ${alt.description}`);
      if (alt.why) item.append(el("span", { className: "alt-why", text: alt.why }));
      els.alternativesList.append(item);
    });
  }

  /* ── Steps: tick, reorder, edit, skip ─────────────────────────── */
  function stepsChanged() {
    const texts = plan.steps.map((s) => s.text);
    return texts.length !== plan.original.length || texts.some((t, i) => t !== plan.original[i]) || plan.steps.some((s) => s.skipped);
  }

  function activeStepId() {
    if (!timer.blocks.length || timer.finished) return null;
    if (!timer.running && timer.baseElapsed === 0) return null;
    const block = timer.blocks[L.activeBlockIndex(timer.blocks, elapsedSec())];
    return block && block.stepId;
  }

  function buildStepItem(step, index, total, activeId) {
    const n = index + 1;
    const li = el("li", { className: "step-item", dataset: { id: step.id } });

    if (step.editing) {
      const area = el("textarea", { id: `edit-${step.id}`, maxLength: 300, value: step.text });
      area.setAttribute("data-edit", step.id);
      li.append(el("div", { className: "step-edit" },
        el("label", { className: "sr-only", htmlFor: area.id, text: `Edit step ${n}` }),
        area,
        el("div", { className: "edit-actions" },
          el("button", { type: "button", className: "action-btn primary", dataset: { act: "save" }, text: "Save step" }),
          el("button", { type: "button", className: "action-btn", dataset: { act: "cancel" }, text: "Cancel" }),
        ),
      ));
      return li;
    }

    const isActive = activeId === step.id;
    li.classList.toggle("is-done", step.done);
    li.classList.toggle("is-skipped", step.skipped);
    li.classList.toggle("is-active", isActive);

    const main = el("button", { type: "button", className: "step-main", dataset: { act: "toggle" } });
    main.setAttribute("role", "checkbox");
    main.setAttribute("aria-checked", step.done ? "true" : "false");
    if (step.skipped) main.disabled = true;
    if (isActive) main.setAttribute("aria-current", "step");

    const badge = el("span", { className: "step-badge", "aria-hidden": "true" }, el("span", { className: "num", text: String(n) }), icon("check", 14));
    const text = el("span", { className: "step-text" });
    if (isActive) text.append(el("span", { className: "now-tag", text: "NOW" }));
    text.append(step.text);
    if (step.skipped) text.append(el("span", { className: "skip-tag", text: "(skipped)" }));
    main.append(badge, text);

    const tool = (act, label, name, disabled) => {
      const b = el("button", { type: "button", className: "icon-btn", dataset: { act }, title: label });
      b.setAttribute("aria-label", label);
      b.disabled = !!disabled;
      b.append(icon(name, 18));
      return b;
    };
    const tools = el("div", { className: "step-tools", role: "group" },
      tool("up", `Move step ${n} up`, "up", index === 0),
      tool("down", `Move step ${n} down`, "down", index === total - 1),
      tool("edit", `Edit step ${n}`, "edit", step.skipped),
      step.skipped ? tool("restore", `Restore step ${n}`, "restore") : tool("skip", `Skip step ${n}`, "skip"),
    );
    tools.setAttribute("role", "group");
    tools.setAttribute("aria-label", `Step ${n} actions`);

    li.append(main, tools);
    return li;
  }

  function renderSteps() {
    const focused = document.activeElement;
    const focusId = focused && focused.closest && focused.closest(".step-item") ? focused.closest(".step-item").dataset.id : null;
    const focusAct = focused && focused.dataset ? focused.dataset.act : null;

    const activeId = activeStepId();
    els.stepsList.replaceChildren(...plan.steps.map((s, i) => buildStepItem(s, i, plan.steps.length, activeId)));
    els.stepsRestore.hidden = !stepsChanged();
    updateProgress(false);

    if (focusId && focusAct) {
      const item = els.stepsList.querySelector(`[data-id="${focusId}"]`);
      if (item) {
        const target = item.querySelector(`[data-act="${focusAct}"]:not(:disabled)`)
          || item.querySelector(".icon-btn:not(:disabled)") || item.querySelector("button");
        if (target) target.focus();
      }
    }
  }

  function updateProgress(allowCelebrate) {
    const active = plan.steps.filter((s) => !s.skipped);
    const done = active.filter((s) => s.done).length;
    const complete = active.length > 0 && done === active.length;
    els.stepsProgress.textContent = complete ? "All steps complete!" : `${done}/${active.length} done`;
    if (!complete) plan.celebrated = false;
    if (complete && allowCelebrate !== false && !plan.celebrated) {
      plan.celebrated = true;
      celebrate();
    }
  }

  function celebrate() {
    announce("All steps complete. Nice work! Mark the session done to log it.");
    setActionStatus("Every step is done — nice work. Mark the session done to log it.");
    els.stepsProgress.classList.remove("celebrate-pill");
    void els.stepsProgress.offsetWidth;
    els.stepsProgress.classList.add("celebrate-pill");
    if (reducedMotion()) return;
    const colors = ["#48bb78", "#f6ad55", "#6ee7a8", "#63b3ed", "#fc8181", "#b794f4"];
    const pieces = [];
    for (let i = 0; i < 44; i++) {
      const piece = document.createElement("i");
      piece.style.setProperty("--x", `${Math.round(Math.random() * 100)}%`);
      piece.style.setProperty("--dx", `${Math.round((Math.random() - 0.5) * 240)}px`);
      piece.style.setProperty("--r", `${Math.round(360 + Math.random() * 540)}deg`);
      piece.style.setProperty("--d", `${(Math.random() * 0.5).toFixed(2)}s`);
      piece.style.setProperty("--t", `${(2 + Math.random() * 1.6).toFixed(2)}s`);
      piece.style.setProperty("--c", colors[i % colors.length]);
      pieces.push(piece);
    }
    els.confetti.replaceChildren(...pieces);
    window.setTimeout(() => els.confetti.replaceChildren(), 4600);
  }

  function findStep(id) {
    return plan.steps.find((s) => s.id === id);
  }

  function onStepsChanged() {
    renderSteps();
    rebuildTimeline();
  }

  els.stepsList.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-act]");
    const item = e.target.closest(".step-item");
    if (!btn || !item || !plan) return;
    const step = findStep(item.dataset.id);
    if (!step) return;
    const index = plan.steps.indexOf(step);
    const act = btn.dataset.act;

    if (act === "toggle") {
      step.done = !step.done;
      renderSteps();
      updateProgress(true);
    } else if (act === "up" || act === "down") {
      const target = act === "up" ? index - 1 : index + 1;
      if (target < 0 || target >= plan.steps.length) return;
      plan.steps.splice(index, 1);
      plan.steps.splice(target, 0, step);
      onStepsChanged();
      announce(`Step moved to position ${target + 1} of ${plan.steps.length}.`);
    } else if (act === "edit") {
      step.editing = true;
      renderSteps();
      const area = els.stepsList.querySelector(`[data-edit="${step.id}"]`);
      if (area) { area.focus(); area.setSelectionRange(area.value.length, area.value.length); }
    } else if (act === "save" || act === "cancel") {
      commitEdit(step, act === "save");
    } else if (act === "skip" || act === "restore") {
      step.skipped = act === "skip";
      if (step.skipped) step.done = false;
      onStepsChanged();
      announce(step.skipped ? `Step ${index + 1} skipped. Time was redistributed.` : `Step ${index + 1} restored.`);
    }
  });

  function commitEdit(step, save) {
    if (save) {
      const area = els.stepsList.querySelector(`[data-edit="${step.id}"]`);
      const text = L.sanitizeText(area ? area.value : "", 300);
      if (text) step.text = text;
    }
    step.editing = false;
    onStepsChanged();
    const edit = els.stepsList.querySelector(`[data-id="${step.id}"] [data-act="edit"]`);
    if (edit) edit.focus();
  }

  els.stepsList.addEventListener("keydown", (e) => {
    const area = e.target.closest("textarea[data-edit]");
    if (!area) return;
    const step = findStep(area.dataset.edit);
    if (!step) return;
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); commitEdit(step, true); }
    else if (e.key === "Escape") { e.preventDefault(); commitEdit(step, false); }
  });

  els.stepsRestore.addEventListener("click", () => {
    plan.steps = plan.original.map((text) => ({ id: nextId("s"), text, done: false, skipped: false, editing: false }));
    plan.celebrated = false;
    onStepsChanged();
    announce("Original steps restored.");
  });

  /* ── Timeline and timer ───────────────────────────────────────── */
  const timer = {
    blocks: [], totalSec: 0,
    baseElapsed: 0, startedAt: 0,
    running: false, finished: false,
    lastIndex: -1,
    worker: null, interval: null,
  };
  let soundOn = store.getRaw(KEYS.sound) !== "0";
  let audioCtx = null;

  function elapsedSec() {
    return timer.running ? timer.baseElapsed + (Date.now() - timer.startedAt) / 1000 : timer.baseElapsed;
  }

  function rebuildTimeline() {
    const active = plan.steps.filter((s) => !s.skipped).map((s) => ({ id: s.id, text: s.text }));
    const schedule = L.buildSchedule(active, plan.minutes);
    timer.blocks = schedule.blocks;
    timer.totalSec = schedule.totalMinutes * 60;
    if (timer.lastIndex !== -1 && !timer.finished) {
      // Steps were edited mid-session: keep the elapsed time and re-find the current block.
      timer.lastIndex = Math.max(0, L.activeBlockIndex(timer.blocks, Math.min(elapsedSec(), timer.totalSec - 1)));
    }
    renderBreakdown();
    renderTimerView();
  }

  function blockStepNumber(block) {
    const ids = timer.blocks.filter((b) => b.kind === "step").map((b) => b.stepId);
    return { n: ids.indexOf(block.stepId) + 1, of: ids.length };
  }

  function renderBreakdown() {
    const started = timer.running || timer.baseElapsed > 0 || timer.finished;
    const current = started && !timer.finished ? L.activeBlockIndex(timer.blocks, elapsedSec()) : -1;
    const items = timer.blocks.map((block, i) => {
      const li = el("li", null,
        el("span", { className: "tb-range", text: `${block.startMin}–${block.endMin} min` }),
        el("span", { text: block.label }),
      );
      if (i === current) { li.classList.add("is-active"); li.setAttribute("aria-current", "step"); }
      else if (started && (timer.finished || i < current)) li.classList.add("is-past");
      return li;
    });
    els.breakdown.replaceChildren(...items);
  }

  let lastViewKey = "";
  function renderTimerView() {
    const e = Math.min(elapsedSec(), timer.totalSec);
    const remaining = Math.max(0, timer.totalSec - e);
    const clock = L.formatClock(remaining);
    els.timerDisplay.textContent = clock;
    els.timerBar.style.width = `${timer.totalSec ? (e / timer.totalSec) * 100 : 0}%`;

    const idx = timer.finished ? -1 : L.activeBlockIndex(timer.blocks, e);
    const block = idx >= 0 ? timer.blocks[idx] : null;
    let heading = "";
    let detail = "";
    let title = BASE_TITLE;

    if (timer.finished) {
      heading = "Session complete.";
      detail = " Nice work — mark the session done to log it.";
      title = `Done · ${BASE_TITLE}`;
    } else if (!timer.running && timer.baseElapsed === 0) {
      heading = "Ready when you are.";
      detail = ` ${timer.blocks.filter((b) => b.kind === "step").length} steps over ${L.formatMinutes(Math.round(timer.totalSec / 60))}. Press start to begin the plan.`;
    } else if (block) {
      const left = L.formatClock(block.endMin * 60 - e);
      let short;
      if (block.kind === "step") {
        const { n, of } = blockStepNumber(block);
        heading = `Step ${n} of ${of}`;
        short = `Step ${n}/${of}`;
      } else if (block.kind === "setup") {
        heading = "Get ready";
        short = "Get ready";
      } else {
        heading = "Final review";
        short = "Review";
      }
      detail = ` · ${left} left in this block — ${block.label}`;
      title = `${clock} · ${short}${timer.running ? "" : " (paused)"} — Study Buddy`;
    }

    const viewKey = `${heading}|${detail}`;
    if (viewKey !== lastViewKey) {
      lastViewKey = viewKey;
      els.timerStep.replaceChildren(el("strong", { text: heading }), detail);
    }
    if (timer.running || timer.finished || timer.baseElapsed > 0) document.title = title;
    else document.title = BASE_TITLE;
  }

  function setTimerChrome() {
    const state = timer.finished ? "Complete" : timer.running ? "Focusing" : timer.baseElapsed > 0 ? "Paused" : "Ready";
    els.timerStatus.textContent = state;
    els.timerBox.classList.toggle("running", timer.running);
    els.timerToggleIcon.setAttribute("href", timer.running ? "#i-pause" : "#i-play");
    els.timerBtnText.textContent = timer.running ? "Pause timer" : timer.finished ? "Restart" : timer.baseElapsed > 0 ? "Resume timer" : "Start timer";
  }

  function ensureAudio() {
    if (!soundOn) return;
    try {
      if (!audioCtx) {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (Ctx) audioCtx = new Ctx();
      }
      if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
    } catch (err) { audioCtx = null; }
  }

  function chime(kind) {
    if (!soundOn || !audioCtx) return;
    try {
      if (audioCtx.state === "suspended") audioCtx.resume();
      const notes = kind === "done" ? [523.25, 659.25, 783.99, 1046.5] : [659.25, 880];
      const t0 = audioCtx.currentTime + 0.02;
      notes.forEach((freq, i) => {
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        const start = t0 + i * 0.17;
        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, start);
        gain.gain.exponentialRampToValueAtTime(0.1, start + 0.03);
        gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.55);
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.start(start);
        osc.stop(start + 0.6);
      });
    } catch (err) { /* sound is a nicety; ignore */ }
  }

  /** Tick from a Worker so it keeps its pace in background tabs. */
  function startTicker() {
    stopTicker();
    try {
      const url = URL.createObjectURL(new Blob(["setInterval(function(){postMessage(0)},250)"], { type: "text/javascript" }));
      timer.worker = new Worker(url);
      URL.revokeObjectURL(url);
      timer.worker.onmessage = tick;
    } catch (err) {
      timer.worker = null;
      timer.interval = window.setInterval(tick, 250);
    }
  }

  function stopTicker() {
    if (timer.worker) { timer.worker.terminate(); timer.worker = null; }
    if (timer.interval) { window.clearInterval(timer.interval); timer.interval = null; }
  }

  function markBlocksDone(from, to) {
    let changed = false;
    for (let i = Math.max(from, 0); i < to && i < timer.blocks.length; i++) {
      const block = timer.blocks[i];
      const step = block.kind === "step" ? findStep(block.stepId) : null;
      if (step && !step.done && !step.skipped) { step.done = true; changed = true; }
    }
    return changed;
  }

  function describeBlock(block) {
    if (block.kind === "step") {
      const { n, of } = blockStepNumber(block);
      return `Step ${n} of ${of}: ${block.label}`;
    }
    return block.kind === "setup" ? `Get ready: ${block.label}` : `Final review: ${block.label}`;
  }

  /** Move to whatever block the elapsed time falls in; mark finished steps done. */
  function syncBlock(audible) {
    const e = elapsedSec();
    if (e >= timer.totalSec) { finishTimer(); return; }
    const idx = L.activeBlockIndex(timer.blocks, e);
    if (idx === timer.lastIndex) return;
    const previous = timer.lastIndex;
    const changed = previous >= 0 && markBlocksDone(previous, idx);
    timer.lastIndex = idx;
    if (previous >= 0 && audible) chime("step");
    els.timerAnnounce.textContent = describeBlock(timer.blocks[idx]);
    renderSteps();
    renderBreakdown();
    if (changed) updateProgress(true);
  }

  function tick() {
    if (!timer.running) return;
    syncBlock(true);
    if (timer.running) renderTimerView();
  }

  function startTimer() {
    ensureAudio();
    if (timer.finished) resetTimer();
    const idx = L.activeBlockIndex(timer.blocks, timer.baseElapsed);
    timer.running = true;
    timer.startedAt = Date.now();
    if (timer.lastIndex === -1) {
      timer.lastIndex = idx;
      els.timerAnnounce.textContent = describeBlock(timer.blocks[idx]);
    }
    startTicker();
    setTimerChrome();
    renderSteps();
    renderBreakdown();
    renderTimerView();
  }

  function pauseTimer() {
    if (!timer.running) return;
    timer.baseElapsed = elapsedSec();
    timer.running = false;
    stopTicker();
    setTimerChrome();
    renderTimerView();
  }

  function finishTimer() {
    stopTicker();
    const from = timer.lastIndex;
    timer.running = false;
    timer.finished = true;
    timer.baseElapsed = timer.totalSec;
    markBlocksDone(from, timer.blocks.length);
    timer.lastIndex = timer.blocks.length - 1;
    chime("done");
    els.timerAnnounce.textContent = "Session complete. Mark the session done to log it.";
    setTimerChrome();
    renderSteps();
    renderBreakdown();
    renderTimerView();
    updateProgress(true);
  }

  function resetTimer() {
    stopTicker();
    timer.running = false;
    timer.finished = false;
    timer.baseElapsed = 0;
    timer.startedAt = 0;
    timer.lastIndex = -1;
    lastViewKey = "";
    document.title = BASE_TITLE;
    if (plan) {
      setTimerChrome();
      renderSteps();
      renderBreakdown();
      renderTimerView();
    }
  }

  function skipBlock() {
    const idx = L.activeBlockIndex(timer.blocks, elapsedSec());
    if (idx < 0) return;
    ensureAudio();
    if (timer.lastIndex === -1) timer.lastIndex = idx;
    timer.baseElapsed = timer.blocks[idx].endMin * 60;
    timer.startedAt = Date.now();
    syncBlock(false);
    setTimerChrome();
    renderTimerView();
  }

  els.timerToggle.addEventListener("click", () => (timer.running ? pauseTimer() : startTimer()));
  els.timerReset.addEventListener("click", () => { resetTimer(); announce("Timer reset."); });
  els.timerNext.addEventListener("click", skipBlock);
  els.timerSound.addEventListener("click", () => {
    soundOn = !soundOn;
    store.setRaw(KEYS.sound, soundOn ? "1" : "0");
    els.timerSound.setAttribute("aria-pressed", String(soundOn));
    els.timerSound.setAttribute("aria-label", `Sound between steps: ${soundOn ? "on" : "off"}`);
    els.timerSoundIcon.setAttribute("href", soundOn ? "#i-volume" : "#i-mute");
    if (soundOn) { ensureAudio(); chime("step"); }
  });
  els.timerSound.setAttribute("aria-pressed", String(soundOn));
  els.timerSound.setAttribute("aria-label", `Sound between steps: ${soundOn ? "on" : "off"}`);
  els.timerSoundIcon.setAttribute("href", soundOn ? "#i-volume" : "#i-mute");

  // Timestamps, not tick counts, drive the clock — catch up immediately on return.
  document.addEventListener("visibilitychange", () => {
    if (timer.running) { tick(); }
  });

  /* ── Copy, share, export ──────────────────────────────────────── */
  function activeSteps() {
    return plan.steps.filter((s) => !s.skipped);
  }

  function planAsText() {
    const lines = [
      `Study Plan: ${plan.method}`,
      `Subject: ${plan.subject} (${plan.struggle})`,
      `Level: ${LEVEL_LABELS[plan.level]}`,
      `Duration: ${L.formatMinutes(plan.minutes)}`,
    ];
    const days = plan.examDate ? L.daysBetween(todayKey(), plan.examDate) : null;
    if (plan.examDate) lines.push(`Deadline: ${plan.exam || "Deadline"} on ${plan.examDate}${days !== null && days >= 0 ? ` (${days} days left)` : ""}`);
    lines.push("", "Why this method works for you:", plan.why || plan.reason);
    if (plan.why && plan.reason) lines.push(plan.reason);
    lines.push("", "Steps:");
    activeSteps().forEach((s, i) => lines.push(`${i + 1}. ${s.text}`));
    lines.push("", "Time breakdown:");
    timer.blocks.forEach((b, i) => lines.push(`${i + 1}. ${b.startMin}–${b.endMin} min: ${b.label}`));
    if (plan.timeNote) lines.push("", `Time tip: ${plan.timeNote}`);
    if (plan.alternatives.length) {
      lines.push("", "Other methods to try:");
      plan.alternatives.forEach((a) => lines.push(`- ${a.method}: ${a.description}`));
    }
    return lines.join("\n");
  }

  function flashButton(btn, labelEl, done, original) {
    btn.classList.add("is-done");
    labelEl.textContent = done;
    window.setTimeout(() => {
      btn.classList.remove("is-done");
      labelEl.textContent = original;
    }, 2200);
  }

  els.copyBtn.addEventListener("click", async () => {
    if (!plan) return;
    try {
      await navigator.clipboard.writeText(planAsText());
      flashButton(els.copyBtn, els.copyText, "Copied!", "Copy plan");
      setActionStatus("Plan copied to the clipboard.");
    } catch (err) {
      setActionStatus("Couldn't copy automatically. Select the plan text and copy it manually.");
    }
  });

  function shareUrl() {
    const payload = {
      v: 1,
      s: plan.subject, f: plan.struggle, l: plan.level, m: plan.minutes,
      e: plan.exam, d: plan.examDate,
      n: plan.method, r: plan.reason, w: plan.why,
      st: activeSteps().map((s) => s.text),
      a: plan.alternatives.map((a) => ({ method: a.method, description: a.description })),
      tn: plan.timeNote,
    };
    if (plan.countdown && plan.examDate) {
      payload.cd = { dl: plan.countdown.days_left != null ? plan.countdown.days_left : plan.countdown.daysAtShare, h: plan.countdown.headline, t: plan.countdown.tips };
    }
    return `${location.origin}${location.pathname}#plan=${L.encodePlan(payload)}`;
  }

  els.shareBtn.addEventListener("click", async () => {
    if (!plan) return;
    const url = shareUrl();
    try {
      await navigator.clipboard.writeText(url);
      flashButton(els.shareBtn, els.shareText, "Link copied!", "Share link");
      setActionStatus("Link copied. Anyone who opens it sees this plan; nothing is stored on a server.");
    } catch (err) {
      const input = el("input", { type: "text", value: url, readOnly: true });
      input.setAttribute("aria-label", "Share link");
      els.actionStatus.replaceChildren("Copy this link to share the plan:", input);
      input.focus();
      input.select();
    }
  });

  els.pdfBtn.addEventListener("click", () => {
    if (!plan) return;
    const previous = document.title;
    document.title = `Study plan — ${plan.method}`;
    const restore = () => { document.title = previous; window.removeEventListener("afterprint", restore); };
    window.addEventListener("afterprint", restore);
    setActionStatus("In the print dialog, choose “Save as PDF” as the destination.");
    window.print();
  });

  /* ── Sessions, ratings, reminders ─────────────────────────────── */
  function currentSession() {
    return plan && plan.sessionId ? store.get(KEYS.sessions, []).find((s) => s.id === plan.sessionId) : null;
  }

  function resetSessionPanels() {
    els.markDone.disabled = false;
    els.markDone.textContent = "Mark session done";
    els.sessionSummary.textContent = "";
    els.ratingPanel.hidden = true;
    els.reminderPanel.hidden = true;
    els.ratingResult.replaceChildren();
    els.reminderStatus.textContent = "";
    els.ratingGroup.querySelectorAll(".rating-btn").forEach((b) => b.setAttribute("aria-pressed", "false"));
    setActionStatus("");
  }

  els.markDone.addEventListener("click", () => {
    if (!plan || plan.sessionId) return;
    pauseTimer();
    const studiedSec = elapsedSec();
    const fromTimer = studiedSec >= 60;
    const minutes = fromTimer ? Math.max(1, Math.round(studiedSec / 60)) : plan.minutes;
    const now = new Date();
    const session = {
      id: nextId("ss"),
      at: now.toISOString(),
      day: L.dayKey(now),
      key: planKey(plan),
      subject: plan.subject,
      struggle: plan.struggle,
      method: plan.method,
      level: plan.level,
      minutes,
      stepsDone: activeSteps().filter((s) => s.done).length,
      stepsTotal: activeSteps().length,
      rating: null,
    };
    const sessions = store.get(KEYS.sessions, []);
    sessions.push(session);
    const saved = store.set(KEYS.sessions, sessions);
    plan.sessionId = session.id;

    els.markDone.disabled = true;
    els.markDone.textContent = "Session logged";
    els.sessionSummary.textContent = `Logged ${L.formatMinutes(minutes)} (${fromTimer ? "from the timer" : "your planned time"}), ${session.stepsDone}/${session.stepsTotal} steps done.` +
      (saved ? "" : " Your browser blocked saving, so progress won't be kept.");
    els.ratingPanel.hidden = false;
    renderReminderOptions();
    els.reminderPanel.hidden = false;
    renderProgress();
    announce("Session logged. Please rate how it went.");
    els.ratingGroup.querySelector(".rating-btn").focus();
  });

  els.ratingGroup.addEventListener("click", (e) => {
    const btn = e.target.closest(".rating-btn");
    if (!btn || !plan || !plan.sessionId) return;
    const rating = Number(btn.dataset.rating);
    const sessions = store.get(KEYS.sessions, []);
    const session = sessions.find((s) => s.id === plan.sessionId);
    if (!session) return;
    session.rating = rating;
    store.set(KEYS.sessions, sessions);
    els.ratingGroup.querySelectorAll(".rating-btn").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    renderSuggestion(rating, sessions);
    renderProgress();
  });

  function renderSuggestion(rating, sessions) {
    const legacy = store.get(KEYS.legacyFeedback, {})[planKey(plan)];
    const stats = L.methodStats(sessions, planKey(plan), legacy);
    const choice = L.chooseNextMethod(stats, plan.method, plan.alternatives);
    const out = els.ratingResult;
    out.replaceChildren();
    const seen = choice.count > 1 ? ` (average ${choice.avg.toFixed(1)}/5 over ${choice.count} ratings)` : "";

    if (choice.action === "keep") {
      out.append(`Rated ${rating}/5. ${plan.method} is working for ${plan.struggle.toLowerCase()}${seen}. Keep using it, and try a harder example next time.`);
    } else if (choice.action === "switch") {
      const alt = choice.alternative;
      out.append(
        `Rated ${rating}/5. Next time, try `, el("strong", { text: alt.method }),
        ` — ${alt.description} We'll lead with it the next time you plan this challenge.`,
      );
      if (alt.steps && alt.steps.length) {
        const use = el("button", { type: "button", className: "action-btn", text: `Use ${alt.method} now`, style: "margin-top:10px" });
        use.addEventListener("click", () => swapToAlternative(alt));
        out.append(el("br"), use);
      }
    } else {
      out.append(`Rated ${rating}/5. That's middling${seen}. Try ${plan.method} once more with a smaller, more specific goal; if it stays at 3 or below, we'll suggest a different method.`);
    }
  }

  function swapToAlternative(alt) {
    const previous = { method: plan.method, description: "The method you just used", why: plan.why, steps: plan.steps.map((s) => s.text) };
    const steps = alt.steps.slice(0, Math.max(1, L.stepCap(plan.minutes)));
    const next = {
      ...plan,
      method: alt.method,
      reason: alt.description,
      why: alt.why || plan.why,
      alternatives: [previous, ...plan.alternatives.filter((a) => a.method !== alt.method)],
      steps: steps.map((text) => ({ id: nextId("s"), text, done: false, skipped: false, editing: false })),
      original: steps.slice(),
      fit: { label: "Your pick", basis: "You switched to a backup method after rating the last session." },
      celebrated: false,
      sessionId: null,
    };
    showPlan(next);
    announce(`Switched to ${alt.method}.`);
  }

  /* Reminders (spaced repetition) */
  const OFFSET_LABELS = { 1: "Tomorrow", 3: "In 3 days", 7: "In 7 days" };

  function renderReminderOptions() {
    const days = plan.examDate ? L.daysBetween(todayKey(), plan.examDate) : null;
    const allowed = new Set(L.reviewOffsets(days !== null && days >= 0 ? days : null));
    els.reminderOptions.replaceChildren();
    els.reminderStatus.textContent = "";

    if (days !== null && days >= 0 && allowed.size === 0) {
      els.reminderHint.textContent = "Your deadline is too close for spaced reviews. Do a short closed-notes recall check shortly before it instead.";
      els.reminderOptions.hidden = true;
      els.reminderSet.parentElement.hidden = true;
      return;
    }
    els.reminderHint.textContent = "Reviewing after a delay is what makes it stick. Pick when to review this topic:";
    els.reminderOptions.hidden = false;
    els.reminderSet.parentElement.hidden = false;

    [1, 3, 7].forEach((offset) => {
      const ok = allowed.has(offset);
      const due = L.addDays(todayKey(), offset);
      const input = el("input", { type: "checkbox", value: String(offset), checked: ok, disabled: !ok });
      const label = el("label", { className: `reminder-option${ok ? "" : " is-disabled"}` },
        input,
        el("span", { text: OFFSET_LABELS[offset] }),
        el("span", { className: "date", text: ok ? prettyDate(due) : "after your deadline" }),
      );
      els.reminderOptions.append(label);
    });
  }

  function selectedReminders() {
    return Array.from(els.reminderOptions.querySelectorAll("input:checked")).map((i) => Number(i.value));
  }

  function reminderRecords(offsets) {
    return offsets.map((offset) => ({
      id: nextId("rv"),
      due: L.addDays(todayKey(), offset),
      offset,
      subject: plan.subject,
      struggle: plan.struggle,
      method: plan.method,
      done: false,
    }));
  }

  els.reminderSet.addEventListener("click", () => {
    const offsets = selectedReminders();
    if (!offsets.length) { els.reminderStatus.textContent = "Select at least one reminder."; return; }
    const reviews = store.get(KEYS.reviews, []);
    let added = 0;
    reminderRecords(offsets).forEach((r) => {
      const dup = reviews.some((x) => x.due === r.due && x.subject === r.subject && x.struggle === r.struggle && x.method === r.method && !x.done);
      if (!dup) { reviews.push(r); added++; }
    });
    store.set(KEYS.reviews, reviews);
    els.reminderStatus.textContent = added
      ? `Saved ${added} ${added === 1 ? "reminder" : "reminders"}. They appear at the top of this page when due. Use “Add to calendar” to be reminded outside the app.`
      : "Those reminders are already saved.";
    renderDue();
    renderProgress();
  });

  els.reminderIcs.addEventListener("click", () => {
    const offsets = selectedReminders();
    if (!offsets.length) { els.reminderStatus.textContent = "Select at least one reminder."; return; }
    const events = reminderRecords(offsets).map((r) => ({
      id: r.id,
      due: r.due,
      summary: `Study review: ${r.method} (${r.subject})`,
      description: `Review ${r.struggle.toLowerCase()} in ${r.subject} using ${r.method}. Close your notes and recall first, then check.`,
    }));
    const blob = new Blob([L.buildICS(events)], { type: "text/calendar;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = el("a", { href: url, download: "study-buddy-reviews.ics" });
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    els.reminderStatus.textContent = "Calendar file downloaded. Open it to add the reviews to your calendar.";
  });

  /* Due reviews */
  function renderDue() {
    const today = todayKey();
    const due = store.get(KEYS.reviews, []).filter((r) => !r.done && r.due <= today).sort((a, b) => a.due.localeCompare(b.due));
    els.duePanel.hidden = due.length === 0;
    els.dueList.replaceChildren(...due.map((r) => {
      const late = L.daysBetween(r.due, today);
      const done = el("button", { type: "button", className: "action-btn", text: "Mark reviewed" });
      done.setAttribute("aria-label", `Mark review of ${r.method} for ${r.subject} as done`);
      done.addEventListener("click", () => {
        const all = store.get(KEYS.reviews, []);
        const found = all.find((x) => x.id === r.id);
        if (found) found.done = true;
        store.set(KEYS.reviews, all);
        renderDue();
        renderProgress();
        announce("Review marked as done.");
      });
      return el("li", null,
        el("span", null,
          `Review ${r.method} — ${r.subject}`,
          el("span", { className: "due-when", text: `${r.struggle} · ${late > 0 ? `overdue by ${late} ${late === 1 ? "day" : "days"}` : "due today"}` }),
        ),
        done,
      );
    }));
  }

  /* ── Progress view ────────────────────────────────────────────── */
  function renderProgress() {
    const sessions = store.get(KEYS.sessions, []);
    const legacy = store.get(KEYS.legacyProgress, {});
    const legacyCount = Number(legacy.sessions) || 0;
    const today = todayKey();

    const legacyDays = [];
    if (L.parseDayKey(legacy.lastCompleted)) {
      for (let i = 0; i < Math.min(Number(legacy.streak) || 0, 365); i++) legacyDays.push(L.addDays(legacy.lastCompleted, -i));
    }
    const streak = L.computeStreak(sessions.map((s) => s.day).concat(legacyDays), today);
    const totalMinutes = sessions.reduce((sum, s) => sum + (Number(s.minutes) || 0), 0);
    const rated = sessions.filter((s) => Number.isInteger(s.rating));
    const avg = rated.length ? rated.reduce((sum, s) => sum + s.rating, 0) / rated.length : null;

    els.statSessions.textContent = String(sessions.length + legacyCount);
    els.statTime.textContent = L.formatMinutes(totalMinutes);
    els.statStreak.textContent = `${streak} ${streak === 1 ? "day" : "days"}`;
    els.statRating.textContent = avg === null ? "–" : `${avg.toFixed(1)}/5`;
    els.todayStreak.textContent = String(streak);
    els.todayMinutes.textContent = String(sessions.filter((s) => s.day === today).reduce((sum, s) => sum + (Number(s.minutes) || 0), 0));
    els.todayReviews.textContent = String(store.get(KEYS.reviews, []).filter((r) => !r.done && r.due <= today).length);

    const week = L.weekSummary(sessions, today);
    const peak = Math.max(30, ...week.days.map((d) => d.minutes));
    els.weekChart.replaceChildren(...week.days.map((d) => {
      const bar = el("div", { className: "bar" });
      bar.style.height = `${Math.round((d.minutes / peak) * 100)}%`;
      const li = el("li", { className: d.isToday ? "is-today" : "" },
        el("span", { className: "bar-day" }, d.label, d.isToday ? el("span", { className: "sr-only", text: " (today)" }) : null),
        el("span", { className: "bar-min" }, String(d.minutes), el("span", { className: "sr-only", text: " minutes" })),
        el("div", { className: "bar-wrap", "aria-hidden": "true" }, bar),
      );
      li.style.order = "0";
      return li;
    }));
    // Visual order: minutes, bar, day (DOM order keeps the label first for screen readers).
    els.weekChart.querySelectorAll("li").forEach((li) => {
      li.querySelector(".bar-min").style.order = "1";
      li.querySelector(".bar-wrap").style.order = "2";
      li.querySelector(".bar-day").style.order = "3";
    });
    els.weekSummary.textContent = week.totalSessions
      ? `This week: ${L.formatMinutes(week.totalMinutes)} across ${week.totalSessions} ${week.totalSessions === 1 ? "session" : "sessions"} on ${week.activeDays} of 7 days.`
      : "No sessions in the last 7 days yet. Finish a plan and mark it done to start your week.";

    // What's working: average rating per method across all challenges.
    const byMethod = {};
    rated.forEach((s) => {
      const m = byMethod[s.method] || (byMethod[s.method] = { sum: 0, count: 0 });
      m.sum += s.rating;
      m.count++;
    });
    const ranked = Object.entries(byMethod)
      .map(([method, m]) => ({ method, avg: m.sum / m.count, count: m.count }))
      .sort((a, b) => b.avg - a.avg || b.count - a.count)
      .slice(0, 3);
    els.methodsList.replaceChildren(...(ranked.length
      ? ranked.map((m) => el("li", null, m.method, el("span", { className: "sub", text: `${m.avg.toFixed(1)}/5 · ${m.count} ${m.count === 1 ? "rating" : "ratings"}` })))
      : [el("li", { className: "muted", text: "Rate a session to see which methods work best for you." })]));

    const upcoming = store.get(KEYS.reviews, []).filter((r) => !r.done).sort((a, b) => a.due.localeCompare(b.due)).slice(0, 5);
    els.reviewsList.replaceChildren(...(upcoming.length
      ? upcoming.map((r) => {
        const days = L.daysBetween(today, r.due);
        const when = days <= 0 ? "Due now" : days === 1 ? "Tomorrow" : prettyDate(r.due);
        return el("li", null, `${r.method} — ${r.subject}`, el("span", { className: "sub", text: when }));
      })
      : [el("li", { className: "muted", text: "No reviews scheduled." })]));
  }

  els.resetData.addEventListener("click", () => {
    if (!window.confirm("Clear all saved sessions, ratings and review reminders from this browser?")) return;
    [KEYS.sessions, KEYS.reviews, KEYS.legacyProgress, KEYS.legacyFeedback].forEach((k) => store.remove(k));
    renderProgress();
    renderDue();
    announce("Saved progress cleared.");
  });

  /* ── Start over ───────────────────────────────────────────────── */
  els.again.addEventListener("click", () => {
    resetTimer();
    plan = null;
    els.result.hidden = true;

    els.subjectGrid.querySelectorAll(".subject").forEach((b) => {
      b.classList.remove("active");
      b.setAttribute("aria-pressed", "false");
    });
    form.subject = "";
    els.customWrap.hidden = true;
    els.customSubject.value = "";
    struggleRequest++;
    els.struggle.replaceChildren(new Option("Choose a subject first…", "", true, true));
    els.struggle.options[0].disabled = true;
    els.struggle.disabled = true;

    form.level = "intermediate";
    els.levelGroup.querySelector('input[value="intermediate"]').checked = true;
    form.preset = "medium";
    els.customMinutes.value = "";
    setPresetActive(true);
    els.examName.value = "";
    els.examDate.value = "";
    updateDaysNote();
    els.error.textContent = "";
    setActionStatus("");
    updateStepper();

    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
    document.getElementById("main").focus({ preventScroll: true });
  });

  /* ── Open a shared plan ───────────────────────────────────────── */
  function openSharedPlan() {
    if (!location.hash.startsWith("#plan=")) return;
    const shared = L.decodePlan(location.hash.slice(6));
    if (!shared) {
      els.error.textContent = "That share link couldn't be opened. Ask for a fresh link, or build your own plan below.";
      return;
    }
    const countdown = shared.countdown
      ? { days_left: shared.countdown.daysAtShare, daysAtShare: shared.countdown.daysAtShare, headline: shared.countdown.headline, tips: shared.countdown.tips }
      : null;
    const data = {
      subject: shared.subject, struggle: shared.struggle, level: shared.level, minutes: shared.minutes,
      method: shared.method, reason: shared.reason, why: shared.why, steps: shared.steps,
      alternatives: shared.alternatives.map((a) => ({ ...a, why: "", steps: [] })),
      countdown, time_note: shared.timeNote,
      fit: { label: "Shared plan", basis: "Opened from a share link" },
    };
    showView("plan", { scroll: false });
    showPlan(makePlan(data, { exam: shared.exam, examDate: shared.examDate, shared: true }), { focus: true });
  }

  /* ── App shell: tabs and install ──────────────────────────────── */
  function showView(name, options) {
    document.querySelectorAll("[data-view]").forEach((v) => { v.hidden = v.dataset.view !== name; });
    els.tabbar.querySelectorAll(".tab").forEach((t) => {
      if (t.dataset.tab === name) t.setAttribute("aria-current", "page");
      else t.removeAttribute("aria-current");
    });
    if (!options || options.scroll !== false) window.scrollTo({ top: 0, behavior: reducedMotion() ? "auto" : "smooth" });
  }
  els.tabbar.addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (tab) showView(tab.dataset.tab);
  });

  let installPrompt = null;
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    installPrompt = e;
    els.installBtn.hidden = false;
  });
  els.installBtn.addEventListener("click", async () => {
    if (!installPrompt) return;
    installPrompt.prompt();
    await installPrompt.userChoice.catch(() => null);
    installPrompt = null;
    els.installBtn.hidden = true;
  });
  window.addEventListener("appinstalled", () => { els.installBtn.hidden = true; });

  /* ── Init ─────────────────────────────────────────────────────── */
  updateStepper();
  renderProgress();
  renderDue();
  openSharedPlan();
})();
