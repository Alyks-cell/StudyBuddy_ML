// Run with: node --test test_logic.js
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("./static/logic.js");

const steps = (n) => Array.from({ length: n }, (_, i) => ({ id: `s${i}`, text: `Step ${i + 1}` }));

test("schedule fills the requested time exactly with at least a minute per step", () => {
  for (const minutes of [5, 8, 10, 15, 25, 30, 45, 60, 90, 240, 480]) {
    for (const n of [0, 1, 2, 3, 4, 5]) {
      const { blocks, totalMinutes } = L.buildSchedule(steps(n), minutes);
      // Impossible combinations (more steps than minutes) may overrun; the server never sends them.
      if (n <= minutes - 2) assert.equal(totalMinutes, minutes, `${minutes} min, ${n} steps`);
      else assert.ok(totalMinutes >= minutes);
      assert.equal(blocks.length, n + 2);
      assert.equal(blocks[0].startMin, 0);
      blocks.forEach((b, i) => {
        assert.ok(b.minutes >= 1);
        if (i) assert.equal(b.startMin, blocks[i - 1].endMin);
      });
      assert.equal(blocks.at(-1).endMin, totalMinutes);
    }
  }
});

test("step cap matches the server's max_steps_for", () => {
  const cases = [[5, 1], [9, 1], [10, 2], [19, 2], [20, 3], [29, 3], [30, 4], [44, 4], [45, 5], [480, 5]];
  cases.forEach(([minutes, cap]) => assert.equal(L.stepCap(minutes), cap, `${minutes} min`));
});

test("schedule scales with the time entered", () => {
  const short = L.buildSchedule(steps(2), 15);
  const long = L.buildSchedule(steps(2), 120);
  assert.ok(long.blocks[1].minutes > short.blocks[1].minutes * 4);
});

test("schedule still works when there are more steps than spare minutes", () => {
  const { blocks, totalMinutes } = L.buildSchedule(steps(5), 5);
  assert.ok(blocks.every((b) => b.minutes >= 1));
  assert.equal(totalMinutes, blocks.reduce((sum, b) => sum + b.minutes, 0));
});

test("active block follows elapsed time and ends at -1", () => {
  const { blocks } = L.buildSchedule(steps(2), 30);
  assert.equal(L.activeBlockIndex(blocks, 0), 0);
  assert.equal(L.activeBlockIndex(blocks, blocks[0].endMin * 60 - 1), 0);
  assert.equal(L.activeBlockIndex(blocks, blocks[0].endMin * 60), 1);
  assert.equal(L.activeBlockIndex(blocks, 30 * 60), -1);
});

test("clock formatting", () => {
  assert.equal(L.formatClock(0), "00:00");
  assert.equal(L.formatClock(65), "01:05");
  assert.equal(L.formatClock(59.2), "01:00");
  assert.equal(L.formatClock(3600), "1:00:00");
  assert.equal(L.formatMinutes(90), "1 h 30 min");
});

test("day arithmetic is calendar-based and DST safe", () => {
  assert.equal(L.addDays("2026-03-08", 1), "2026-03-09");
  assert.equal(L.addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(L.daysBetween("2026-10-12", "2026-10-19"), 7);
  assert.equal(L.daysBetween("2026-10-12", "2026-10-12"), 0);
  assert.equal(L.parseDayKey("2026-02-31"), null);
  assert.equal(L.parseDayKey("nope"), null);
});

test("share links round-trip, including non-ASCII text", () => {
  const plan = {
    v: 1, s: "Français — 日本語", f: "Building vocabulary", l: "advanced", m: 45, e: "Exam", d: "2026-11-01",
    n: "Method → Name", r: "reason", w: "why", st: ["one", "two ✓"], a: [{ method: "Active Recall", description: "d" }],
    cd: { dl: 7, h: "7 days", t: ["a", "b"] },
  };
  const out = L.decodePlan(L.encodePlan(plan));
  assert.equal(out.subject, "Français — 日本語");
  assert.deepEqual(out.steps, ["one", "two ✓"]);
  assert.equal(out.level, "advanced");
  assert.equal(out.minutes, 45);
  assert.equal(out.examDate, "2026-11-01");
  assert.equal(out.countdown.daysAtShare, 7);
});

test("share links reject garbage and sanitize hostile content", () => {
  assert.equal(L.decodePlan("not base64 !!"), null);
  assert.equal(L.decodePlan(""), null);
  assert.equal(L.decodePlan(L.encodePlan({ v: 2 })), null);
  assert.equal(L.decodePlan(L.encodePlan({ v: 1, s: "x", f: "y", n: "m", st: [] })), null);
  const out = L.decodePlan(L.encodePlan({
    v: 1, s: "<img src=x onerror=1>", f: "f", n: "m", m: 99999, l: "wizard", d: "2026-99-99",
    st: ["a\u0000b", "x".repeat(1000), ...Array(20).fill("s")],
  }));
  assert.equal(out.minutes, L.MAX_MINUTES);
  assert.equal(out.level, "intermediate");
  assert.equal(out.examDate, "");
  assert.equal(out.steps.length, 8);
  assert.equal(out.steps[0], "a b");
  assert.equal(out.steps[1].length, 300);
});

test("streak counts consecutive days ending today or yesterday", () => {
  assert.equal(L.computeStreak([], "2026-10-12"), 0);
  assert.equal(L.computeStreak(["2026-10-12"], "2026-10-12"), 1);
  assert.equal(L.computeStreak(["2026-10-11", "2026-10-10"], "2026-10-12"), 2);
  assert.equal(L.computeStreak(["2026-10-09", "2026-10-10"], "2026-10-12"), 0);
  assert.equal(L.computeStreak(["2026-10-12", "2026-10-10", "2026-10-11", "2026-10-08"], "2026-10-12"), 3);
});

test("week summary totals the last seven days only", () => {
  const sessions = [
    { day: "2026-10-12", minutes: 30 },
    { day: "2026-10-12", minutes: 15 },
    { day: "2026-10-08", minutes: 20 },
    { day: "2026-10-05", minutes: 99 }, // outside the window
  ];
  const week = L.weekSummary(sessions, "2026-10-12");
  assert.equal(week.days.length, 7);
  assert.equal(week.days.at(-1).minutes, 45);
  assert.equal(week.days.at(-1).isToday, true);
  assert.equal(week.totalMinutes, 65);
  assert.equal(week.totalSessions, 3);
  assert.equal(week.activeDays, 2);
});

test("ratings pick the next method", () => {
  const alternatives = [{ method: "Active Recall" }, { method: "Spaced Repetition" }];
  const sess = (method, rating, key = "math|x") => ({ key, method, rating });

  // Good rating: keep.
  let stats = L.methodStats([sess("A", 5)], "math|x");
  assert.equal(L.chooseNextMethod(stats, "A", alternatives).action, "keep");

  // Poor latest rating: switch to the first untried alternative.
  stats = L.methodStats([sess("A", 1)], "math|x");
  let next = L.chooseNextMethod(stats, "A", alternatives);
  assert.equal(next.action, "switch");
  assert.equal(next.method, "Active Recall");

  // Prefer an alternative that has worked before over an untried one.
  stats = L.methodStats([sess("A", 2), sess("Spaced Repetition", 5)], "math|x");
  next = L.chooseNextMethod(stats, "A", alternatives);
  assert.equal(next.method, "Spaced Repetition");

  // Skip alternatives that have already failed.
  stats = L.methodStats([sess("A", 1), sess("Active Recall", 1)], "math|x");
  next = L.chooseNextMethod(stats, "A", alternatives);
  assert.equal(next.method, "Spaced Repetition");

  // Ratings for other subject/challenge pairs are ignored.
  stats = L.methodStats([sess("A", 1, "bio|y")], "math|x");
  assert.equal(L.chooseNextMethod(stats, "A", alternatives).action, "keep");

  // Neutral rating: tweak, do not switch.
  stats = L.methodStats([sess("A", 3)], "math|x");
  assert.equal(L.chooseNextMethod(stats, "A", alternatives).action, "tweak");
});

test("legacy helped / not-helped votes still count", () => {
  const stats = L.methodStats([], "k", { methods: { A: { helped: 0, notHelped: 2 } } });
  assert.equal(stats.A.count, 2);
  assert.equal(L.shouldSwitch(stats.A), true);
});

test("review offsets stop before the deadline", () => {
  assert.deepEqual(L.reviewOffsets(null), [1, 3, 7]);
  assert.deepEqual(L.reviewOffsets(30), [1, 3, 7]);
  assert.deepEqual(L.reviewOffsets(5), [1, 3]);
  assert.deepEqual(L.reviewOffsets(1), []);
  assert.deepEqual(L.reviewOffsets(0), []);
});

test("calendar export is valid all-day events with escaping", () => {
  const ics = L.buildICS(
    [{ id: "a1", due: "2026-10-13", summary: "Review: A; B", description: "Line1\nLine2, ok" }],
    new Date("2026-10-12T10:00:00Z"),
  );
  assert.match(ics, /^BEGIN:VCALENDAR\r\n/);
  assert.match(ics, /DTSTART;VALUE=DATE:20261013\r\n/);
  assert.match(ics, /DTEND;VALUE=DATE:20261014\r\n/);
  assert.match(ics, /SUMMARY:Review: A\\; B\r\n/);
  assert.match(ics, /DESCRIPTION:Line1\\nLine2\\, ok\r\n/);
  assert.match(ics, /DTSTAMP:20261012T100000Z\r\n/);
  assert.ok(ics.endsWith("END:VCALENDAR\r\n"));
});
