/* ---------------------------------------------------------------
   logic.js — pure helpers for Study Buddy (no DOM access).
   Loaded in the browser as window.StudyLogic and in Node for tests.
   --------------------------------------------------------------- */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.StudyLogic = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const MIN_MINUTES = 5;
  const MAX_MINUTES = 480;
  const PRESET_MINUTES = { short: 15, medium: 30, long: 60 };
  const LEVELS = ["beginner", "intermediate", "advanced"];
  const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  const pad2 = (n) => String(n).padStart(2, "0");
  const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));

  /* ── Dates (day keys are local calendar days, "YYYY-MM-DD") ───── */
  function dayKey(date) {
    return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
  }

  function parseDayKey(key) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(key));
    if (!m) return null;
    const date = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    const valid = date.getUTCFullYear() === +m[1] && date.getUTCMonth() === +m[2] - 1 && date.getUTCDate() === +m[3];
    return valid ? date : null;
  }

  function keyFromUTC(date) {
    return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
  }

  function addDays(key, n) {
    const date = parseDayKey(key);
    if (!date) return null;
    date.setUTCDate(date.getUTCDate() + n);
    return keyFromUTC(date);
  }

  function daysBetween(fromKey, toKey) {
    const a = parseDayKey(fromKey);
    const b = parseDayKey(toKey);
    if (!a || !b) return null;
    return Math.round((b - a) / 86400000);
  }

  /* ── Time ──────────────────────────────────────────────────────── */
  function formatClock(totalSeconds) {
    const s = Math.max(0, Math.ceil(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return h > 0 ? `${h}:${pad2(m)}:${pad2(sec)}` : `${pad2(m)}:${pad2(sec)}`;
  }

  function formatMinutes(minutes) {
    if (minutes < 60) return `${minutes} min`;
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return m ? `${h} h ${m} min` : `${h} h`;
  }

  /** How many steps fit in a session. Mirrors max_steps_for() in app.py. */
  function stepCap(minutes) {
    if (minutes < 10) return 1;
    if (minutes < 20) return 2;
    if (minutes < 30) return 3;
    if (minutes < 45) return 4;
    return 5;
  }

  /**
   * Lay out a session: setup, one block per step, then a review block.
   * `steps` is an array of { id, text }. Every step gets at least a minute.
   */
  function buildSchedule(steps, totalMinutes) {
    const n = steps.length;
    const total = clamp(Math.round(Number(totalMinutes) || 0), MIN_MINUTES, MAX_MINUTES);
    let setup = clamp(Math.round(total * 0.1), 1, 5);
    let review = clamp(Math.round(total * 0.15), 1, 10);
    let work = total - setup - review;
    if (work < n) {
      setup = 1;
      review = 1;
      work = Math.max(n, total - 2);
    }
    if (n === 0) {
      review += work;
      work = 0;
    }

    const blocks = [];
    let minute = 0;
    const push = (kind, label, minutes, stepId) => {
      blocks.push({ kind, label, minutes, stepId: stepId || null, startMin: minute, endMin: minute + minutes });
      minute += minutes;
    };

    push("setup", "Get your materials ready and set one focus goal.", setup);
    if (n) {
      const base = Math.floor(work / n);
      const extra = work % n;
      steps.forEach((step, i) => push("step", step.text, base + (i < extra ? 1 : 0), step.id));
    }
    push("review", "Check what you remember and note what to review next.", review);
    return { blocks, totalMinutes: minute };
  }

  /** Index of the block that contains `elapsedSeconds`, or -1 once finished. */
  function activeBlockIndex(blocks, elapsedSeconds) {
    for (let i = 0; i < blocks.length; i++) {
      if (elapsedSeconds < blocks[i].endMin * 60) return i;
    }
    return -1;
  }

  /* ── Text safety ───────────────────────────────────────────────── */
  function sanitizeText(value, max) {
    return String(value == null ? "" : value)
      .replace(/[\u0000-\u001f\u007f]+/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, max);
  }

  /* ── Share links ───────────────────────────────────────────────── */
  function toBase64Url(text) {
    const bytes = new TextEncoder().encode(text);
    let binary = "";
    bytes.forEach((b) => { binary += String.fromCharCode(b); });
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function fromBase64Url(text) {
    let b64 = String(text).replace(/-/g, "+").replace(/_/g, "/");
    while (b64.length % 4) b64 += "=";
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  function encodePlan(plan) {
    return toBase64Url(JSON.stringify(plan));
  }

  /** Validate untrusted share data; returns a clean plan object or null. */
  function decodePlan(encoded) {
    let raw;
    try {
      if (!encoded || encoded.length > 12000) return null;
      raw = JSON.parse(fromBase64Url(encoded));
    } catch (err) {
      return null;
    }
    if (!raw || typeof raw !== "object" || raw.v !== 1) return null;

    const steps = (Array.isArray(raw.st) ? raw.st : [])
      .slice(0, 8)
      .map((s) => sanitizeText(s, 300))
      .filter(Boolean);
    const method = sanitizeText(raw.n, 80);
    const subject = sanitizeText(raw.s, 60);
    const struggle = sanitizeText(raw.f, 80);
    if (!steps.length || !method || !subject || !struggle) return null;

    const minutes = Number(raw.m);
    const examDate = typeof raw.d === "string" && parseDayKey(raw.d) ? raw.d : "";
    let countdown = null;
    if (raw.cd && typeof raw.cd === "object" && Number.isInteger(raw.cd.dl)) {
      countdown = {
        daysAtShare: raw.cd.dl,
        headline: sanitizeText(raw.cd.h, 160),
        tips: (Array.isArray(raw.cd.t) ? raw.cd.t : []).slice(0, 5).map((t) => sanitizeText(t, 240)).filter(Boolean),
      };
    }

    return {
      subject,
      struggle,
      level: LEVELS.includes(raw.l) ? raw.l : "intermediate",
      minutes: Number.isFinite(minutes) ? clamp(Math.round(minutes), MIN_MINUTES, MAX_MINUTES) : 30,
      exam: sanitizeText(raw.e, 80),
      examDate,
      method,
      reason: sanitizeText(raw.r, 500),
      why: sanitizeText(raw.w, 700),
      timeNote: sanitizeText(raw.tn, 300),
      steps,
      alternatives: (Array.isArray(raw.a) ? raw.a : []).slice(0, 3).map((a) => ({
        method: sanitizeText(a && a.method, 80),
        description: sanitizeText(a && a.description, 300),
      })).filter((a) => a.method),
      countdown,
    };
  }

  /* ── Progress & ratings ────────────────────────────────────────── */
  function computeStreak(days, todayKey) {
    const set = new Set(days);
    let cursor = set.has(todayKey) ? todayKey : addDays(todayKey, -1);
    let streak = 0;
    while (cursor && set.has(cursor)) {
      streak++;
      cursor = addDays(cursor, -1);
    }
    return streak;
  }

  /** Last seven days (oldest first) of studied minutes and session counts. */
  function weekSummary(sessions, todayKey) {
    const days = [];
    for (let i = 6; i >= 0; i--) {
      const key = addDays(todayKey, -i);
      const inDay = sessions.filter((s) => s.day === key);
      days.push({
        key,
        label: WEEKDAYS[parseDayKey(key).getUTCDay()],
        minutes: inDay.reduce((sum, s) => sum + (Number(s.minutes) || 0), 0),
        sessions: inDay.length,
        isToday: i === 0,
      });
    }
    return {
      days,
      totalMinutes: days.reduce((sum, d) => sum + d.minutes, 0),
      totalSessions: days.reduce((sum, d) => sum + d.sessions, 0),
      activeDays: days.filter((d) => d.sessions > 0).length,
    };
  }

  /**
   * Rating statistics per method for one subject|challenge key.
   * Legacy helped/not-helped votes count as 5 and 1.
   */
  function methodStats(sessions, key, legacyRecord) {
    const stats = {};
    const add = (method, rating, isReal) => {
      const s = stats[method] || (stats[method] = { count: 0, sum: 0, avg: 0, last: null });
      s.count++;
      s.sum += rating;
      s.avg = s.sum / s.count;
      if (isReal) s.last = rating;
    };
    const legacy = legacyRecord && legacyRecord.methods;
    if (legacy && typeof legacy === "object") {
      Object.keys(legacy).forEach((method) => {
        const votes = legacy[method] || {};
        for (let i = 0; i < Math.min(Number(votes.helped) || 0, 20); i++) add(method, 5, false);
        for (let i = 0; i < Math.min(Number(votes.notHelped) || 0, 20); i++) add(method, 1, false);
      });
    }
    sessions.forEach((s) => {
      if (s.key === key && Number.isInteger(s.rating) && s.rating >= 1 && s.rating <= 5) add(s.method, s.rating, true);
    });
    return stats;
  }

  /** A method should be swapped after a clearly poor latest rating or a poor average. */
  function shouldSwitch(stat) {
    return !!stat && ((stat.last !== null && stat.last <= 2) || (stat.count >= 2 && stat.avg < 3));
  }

  /**
   * Decide what to try next. `alternatives` is [{ method, description, steps? }].
   * Returns { action: "keep" | "switch" | "tweak", method, alternative?, avg, count }.
   */
  function chooseNextMethod(stats, current, alternatives) {
    const cur = stats[current];
    if (!cur) return { action: "keep", method: current, avg: null, count: 0 };
    if (!shouldSwitch(cur)) {
      return {
        action: cur.avg >= 3.5 ? "keep" : "tweak",
        method: current,
        avg: cur.avg,
        count: cur.count,
      };
    }
    let best = null;
    let bestScore = -Infinity;
    (alternatives || []).forEach((alt) => {
      const s = stats[alt.method];
      if (shouldSwitch(s)) return;
      const score = s ? s.avg : 3.5; // untried methods get a neutral-positive prior
      if (score > bestScore) {
        best = alt;
        bestScore = score;
      }
    });
    if (!best) return { action: "tweak", method: current, avg: cur.avg, count: cur.count };
    return { action: "switch", method: best.method, alternative: best, avg: cur.avg, count: cur.count };
  }

  /* ── Reminders ─────────────────────────────────────────────────── */
  function reviewOffsets(daysLeft) {
    const all = [1, 3, 7];
    if (daysLeft === null || daysLeft === undefined) return all;
    return all.filter((o) => o < daysLeft);
  }

  function icsEscape(text) {
    return String(text).replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
  }

  /** All-day calendar events. `events` is [{ id, due, summary, description }]. */
  function buildICS(events, now) {
    const stamp = (now || new Date()).toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
    const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Study Buddy//Review reminders//EN", "CALSCALE:GREGORIAN"];
    events.forEach((event) => {
      const start = String(event.due).replace(/-/g, "");
      const end = String(addDays(event.due, 1)).replace(/-/g, "");
      lines.push(
        "BEGIN:VEVENT",
        `UID:${event.id}@study-buddy`,
        `DTSTAMP:${stamp}`,
        `DTSTART;VALUE=DATE:${start}`,
        `DTEND;VALUE=DATE:${end}`,
        `SUMMARY:${icsEscape(event.summary)}`,
        `DESCRIPTION:${icsEscape(event.description || "")}`,
        "END:VEVENT",
      );
    });
    lines.push("END:VCALENDAR");
    return lines.join("\r\n") + "\r\n";
  }

  return {
    MIN_MINUTES,
    MAX_MINUTES,
    PRESET_MINUTES,
    LEVELS,
    dayKey,
    parseDayKey,
    addDays,
    daysBetween,
    formatClock,
    formatMinutes,
    stepCap,
    buildSchedule,
    activeBlockIndex,
    sanitizeText,
    encodePlan,
    decodePlan,
    computeStreak,
    weekSummary,
    methodStats,
    shouldSwitch,
    chooseNextMethod,
    reviewOffsets,
    buildICS,
  };
});
