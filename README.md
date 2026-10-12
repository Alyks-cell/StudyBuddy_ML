# Study Buddy — Expert System Study Method Recommender

A study method recommender powered by an **Expert System inference engine**. Built with vanilla HTML, modern CSS, JavaScript, and a zero-dependency Python backend using only the standard library.

---

## 🌟 Key Features

**Personalized plans**
- 11 subjects, including a typed-in "Other" matched to the closest subject family.
- Level (beginner / intermediate / advanced) changes the challenge options and adds a warm-up or stretch step.
- Any duration from 5 to 480 minutes; the step count and time breakdown scale to it.
- Optional exam or deadline: guidance and review schedule depend on the days left.
- "Why this method works for you" ties each recommendation to the subject, challenge and level.

**Doing and sticking**
- Timer that runs the plan block by block, highlights the active step, plays a soft chime, keeps accurate time in background tabs and shows the countdown in the tab title.
- Reorder, edit or skip steps; time and timer re-flow. Confetti when every step is done.
- Sessions, streaks, total time and a 7-day chart, saved in `localStorage`.
- 1–5 session rating drives which method is suggested next; spaced review reminders (tomorrow / 3 days / 7 days) with `.ics` calendar export.

**Sharing**: copy plan, share link (the plan is encoded in the URL hash; nothing is stored on a server), and Export as PDF through the browser's print dialog.

**Quality**: light/dark theme that follows the system with a manual toggle, skip link, keyboard and screen-reader support, 375px mobile layout, reduced-motion support.

See [RULES.md](RULES.md) for the rule tables and policies.

---

## 🚀 How to Run

1. Ensure **Python 3** is installed.
2. In this folder, launch the server:
   ```bash
   python app.py
   ```
3. Open your browser and navigate to:
   ```
   http://127.0.0.1:8000
   ```

## Rule coverage

Run the exhaustive coverage checks from this directory:

```bash
python -m unittest test_app.py
node --test test_logic.js
```

The Python suite checks every subject × level × challenge path and the request handlers; the Node suite checks the browser-side logic.

---

## 📐 Expert System Architecture

- **Knowledge Base (`RULES`, `GENERIC_RULES`)**: Stores condition-action pairs: `(Subject, Struggle) -> (Method, Reason, Steps[])`.
- **Inference Engine (`recommend()`)**: Uses ordered lookup: subject-and-challenge rule, general challenge rule, then a safe recall starter. Time policies limit the number of displayed steps.
- **Explanation Facility (`fit`, `reason`)**: Explains the matched challenge and distinguishes subject-specific matches from general fallbacks; labels are rule coverage, not probabilities.
- **Feedback adaptation**: Two or more negative ratings for a method promote an available backup for that same subject and challenge in that browser.
