# Symptom Triage Helper: a rule-based expert system

A small web app that asks a few questions, one at a time, and says **how urgently to seek care**:
Emergency, Urgent, See a doctor soon, or Self-care at home.

> **Triage only. Not a diagnosis.** It gives general guidance, never names a condition, and can't replace
> a doctor, nurse or emergency services. In an emergency, call your local emergency number.
> Answers are not stored.

## Expert-system architecture (see `app.py`)

| Component | Where | What it does |
|---|---|---|
| Knowledge base | `QUESTIONS`, `RULES` | IF-THEN rules written from common triage guidance, in plain data |
| Working memory | `facts` | The answers given so far |
| Inference engine | `fire_rules()` | **Forward chaining**: every rule whose conditions all hold fires |
| Conflict resolution | `build_result()` | The **highest urgency wins**, so a danger sign is never outvoted |
| Question control | `next_step()` | Asks the next *relevant* question; **stops early** on an emergency |
| Explanation facility | `describe_rule()`, `rules_using()` | "Why am I asked this?" and "How did we reach this?" with the rules in IF-THEN form |

Safety choices: danger signs are asked first; ties and doubt resolve upward; every result shows a
disclaimer and an emergency-number reminder; the app offline still shows the emergency notice.

Full rule table: [RULES.md](RULES.md).

## Run

```bash
python app.py        # then open http://127.0.0.1:8000
python -m unittest test_app.py
```

The tests check knowledge-base consistency, every reachable question path (~2,000), and safety
properties: any danger sign gives an emergency, extra risk never lowers urgency, a young baby is never
triaged lower than an adult with the same answers, and results never name a diagnosis.

## Limitations (be honest about these in a report)

- The rules are hand-written from general guidance, not learned from data or clinically validated.
- It covers five problems (fever, cough, sore throat, headache, stomach upset); anything else is sent to a clinician.
- There is no uncertainty model (a classic extension is certainty factors) and no backward chaining.
- Emergency numbers differ by country, so the app names examples rather than one number.
