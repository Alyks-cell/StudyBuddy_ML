# Study Buddy rule catalog

## Rule form and precedence

Rules are condition–action entries. The engine evaluates them in this order:

1. **Subject rule:** `IF subject = S AND challenge = P THEN method = M, reason = R, steps = [..]`.
2. **General rule:** `IF challenge = P THEN method = M, reason = R, steps = [..]` when no subject rule exists.
3. **Starter rule:** `IF no rule matches THEN use a short active-recall plan` and label it **Starting point**.
4. **Time policy:** `IF time = 15 min THEN show 2 steps`; `30 min` and `60+ min` show up to 4 steps. Time changes plan scope and the time note; it does not currently select a different method.

“Strong match” means a subject-specific rule matched. “Good match” means a general challenge rule matched. These are rule-coverage labels, not probabilities or measured success rates. Feedback is stored in the student's browser. After two or more “not helpful” ratings for the same rule and method, the next plan promotes a backup method; the rule is not silently rewritten for other students.

## Subjects and typed-in subjects

Math, Science, Biology, Chemistry, Languages, Economics, History, English, Law, Programming and Other each have their own challenge list. For **Other**, the typed subject is matched by keyword to the closest family (for example "Organic Chemistry" → Chemistry, "Spanish" → Languages, "Statistics" → Math) so rules and challenge options stay relevant; unmatched subjects use the general list. The typed name is shown in the plan.

## Level policy

| Level | Extra challenges shown first | Hidden challenges | Plan change |
|---|---|---|---|
| Beginner | Understanding the basics; Not knowing what to study first | Connecting themes across eras; Connecting theory to experiments; Building projects | A warm-up step is added first |
| Intermediate | Filling gaps in what I know; Making things stick longer | none | none |
| Advanced | Applying ideas to unfamiliar problems; Exam speed & accuracy; Finding my last weak spots | Getting started | A harder "stretch" step is added last |

## Time policy

Minutes (a preset of 15/30/60 or any custom value from 5 to 480) set how many steps are shown:

| Minutes | Steps |
|---:|---:|
| under 10 | 1 |
| 10–19 | 2 |
| 20–29 | 3 |
| 30–44 | 4 |
| 45+ | 5 |

The session is laid out as setup (about 10%), one block per step, and a review (about 15%); skipping or reordering steps in the browser re-lays it out.

## Deadline policy

When a date is given, days left change the guidance and the review schedule:

| Days left | Guidance | Review offsets |
|---|---|---|
| 0 | Quick retrieval only; no new material | none |
| 1 | Triage step added; closed-notes testing; sleep | none |
| 2–3 | Prioritize weak topics; one full run-through | 1 |
| 4–7 | Daily rotation; practice test 2 days before | 1, 3 |
| 8–14 | 4–5 sessions a week; mixed practice in week two | 1, 3, 7 |
| 15+ | "Map the syllabus" step added; steady spacing | 1, 3, 7 |

Review reminders are never offered on or after the deadline.

## Ratings

After a session you rate it 1–5 (stored in this browser). A method is replaced by the best backup for that subject and challenge when the latest rating is 1–2, or when there are at least two ratings averaging below 3. Backups that have worked before outrank untried ones; backups that failed are skipped.

## Rule precedence and labels

1. **Subject rule** → "Strong match". 2. **General rule** → "Good match". 3. **Starter rule** → "Starting point". These are rule-coverage labels, not probabilities.

## Coverage check

`test_app.py` enumerates every subject × level × listed challenge at several durations, checks each returns a complete plan with an explanation, and checks that no listed challenge falls through to the starter rule. `test_logic.js` covers scheduling, share links, streaks, ratings and calendar export.
