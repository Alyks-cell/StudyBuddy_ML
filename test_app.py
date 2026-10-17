import itertools
import unittest

import app

SAFE_FLAGS = ["none"]
DANGER_FLAGS = [o["value"] for o in app.QUESTION_BY_ID["redflags"]["options"] if o["value"] != "none"]


def option_values(qid):
    return [o["value"] for o in app.QUESTION_BY_ID[qid]["options"]]


def answer_choices(question):
    """Representative answers: each option alone, plus one pair for multi-select."""
    values = option_values(question["id"])
    if question["type"] == "single":
        return values
    real = [v for v in values if v != "none"]
    choices = [["none"]] + [[v] for v in real]
    if len(real) >= 2:
        choices.append(real[:2])
    return choices


def walk(facts=None):
    """Yield (facts, result) for every consultation path (excluding danger-sign answers)."""
    facts = dict(facts or {})
    step = app.next_step(facts)
    if step["done"]:
        yield facts, step["result"]
        return
    question = step["question"]
    for choice in answer_choices(app.QUESTION_BY_ID[question["id"]]):
        if question["id"] == "redflags" and choice != ["none"]:
            continue  # danger-sign branches are tested separately
        yield from walk({**facts, question["id"]: choice})


class KnowledgeBaseTests(unittest.TestCase):
    def test_rule_ids_are_unique(self):
        ids = [r["id"] for r in app.RULES]
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_condition_references_a_real_question_and_option(self):
        for rule in app.RULES:
            self.assertIn(rule["level"], app.LEVELS, rule["id"])
            self.assertTrue(rule["reason"].strip(), rule["id"])
            self.assertTrue(rule["if"], rule["id"])
            for fact, op, value in rule["if"]:
                self.assertIn(fact, app.QUESTION_BY_ID, f"{rule['id']}: {fact}")
                self.assertIn(op, {"is", "in", "has", "lacks"}, rule["id"])
                valid = set(option_values(fact))
                for v in (value if isinstance(value, list) else [value]):
                    self.assertIn(v, valid, f"{rule['id']}: {fact}={v}")
                if op in ("has", "lacks"):
                    self.assertEqual(app.QUESTION_BY_ID[fact]["type"], "multi", rule["id"])
                else:
                    self.assertEqual(app.QUESTION_BY_ID[fact]["type"], "single", rule["id"])

    def test_every_question_is_used_by_some_rule(self):
        for q in app.QUESTIONS:
            self.assertTrue(app.rules_using(q["id"]), f"{q['id']} is asked but no rule uses it")

    def test_every_complaint_has_a_baseline_rule(self):
        for complaint in option_values("complaint"):
            facts = {"complaint": complaint}
            self.assertTrue(any(r["level"] <= 2 for r in app.fire_rules(facts)), complaint)

    def test_every_danger_flag_has_its_own_emergency_rule(self):
        for flag in DANGER_FLAGS:
            fired = app.fire_rules({"redflags": [flag]})
            self.assertTrue(fired and all(r["level"] == 4 for r in fired), flag)


class SafetyTests(unittest.TestCase):
    def test_any_danger_sign_ends_the_consultation_at_once_as_an_emergency(self):
        for flag in DANGER_FLAGS:
            step = app.next_step({"redflags": [flag]})
            self.assertTrue(step["done"], flag)
            self.assertEqual(step["result"]["level"], 4, flag)

    def test_self_harm_result_includes_crisis_support(self):
        result = app.next_step({"redflags": ["selfharm"]})["result"]
        self.assertTrue(any("988" in line and "crisis" in line for line in result["advice"]))

    def test_fever_in_a_young_baby_is_an_emergency(self):
        facts = {"redflags": ["none"], "age": "baby_u3m", "complaint": "fever", "risk": "no", "temp": "t38"}
        self.assertEqual(app.next_step(facts)["result"]["level"], 4)

    def test_thunderclap_headache_and_fever_with_stiff_neck_are_emergencies(self):
        base = {"redflags": ["none"], "age": "adult", "complaint": "headache", "risk": "no"}
        self.assertEqual(app.next_step({**base, "ha_onset": "thunder"})["result"]["level"], 4)
        self.assertEqual(app.next_step({**base, "ha_onset": "gradual", "ha_sx": ["neck"]})["result"]["level"], 4)

    def test_mild_adult_problems_are_self_care(self):
        mild = {
            "fever": {"temp": "t38", "fever_days": "d0", "fever_sx": ["none"]},
            "cough": {"cough_breath": "normal", "cough_days": "lt1w", "cough_sx": ["none"]},
            "throat": {"throat_sx": ["none"], "throat_days": "lt1w"},
            "headache": {"ha_onset": "gradual", "ha_sx": ["none"], "ha_known": "yes"},
            "stomach": {"gi_sx": ["none"], "gi_fluids": "yes", "gi_days": "lt2"},
        }
        for complaint, extra in mild.items():
            facts = {"redflags": ["none"], "age": "adult", "complaint": complaint, "risk": "no", **extra}
            result = app.next_step(facts)["result"]
            self.assertEqual(result["level"], 1, complaint)
            self.assertTrue(result["advice"], complaint)
            self.assertTrue(result["watch_for"], complaint)

    def test_highest_urgency_wins_over_milder_findings(self):
        facts = {"redflags": ["none"], "age": "adult", "complaint": "fever", "risk": "no",
                 "temp": "t40", "fever_days": "d3p", "fever_sx": ["urine"]}
        result = app.next_step(facts)["result"]
        self.assertEqual(result["level"], 3)
        self.assertTrue(result["also_noted"])
        self.assertTrue(all(r["level"] == 3 for r in result["reasons"]))

    def test_unsupported_complaint_is_sent_to_a_clinician(self):
        facts = {"redflags": ["none"], "age": "adult", "complaint": "other", "risk": "no"}
        step = app.next_step(facts)
        self.assertTrue(step["done"])
        self.assertEqual(step["result"]["level"], 2)
        self.assertEqual(step["result"]["reasons"][0]["id"], "X1")

    def test_result_never_names_a_diagnosis(self):
        banned = ["diagnos" + "ed with", "you have appendicitis", "meningitis", "pneumonia", "covid", "cancer"]
        text = " ".join(r["reason"] for r in app.RULES).lower()
        for word in banned:
            self.assertNotIn(word, text)


class ExhaustivePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.paths = list(walk())

    def test_every_path_terminates_with_a_valid_result(self):
        self.assertGreater(len(self.paths), 1000)
        for facts, result in self.paths:
            self.assertIn(result["level"], app.LEVELS)
            self.assertTrue(result["reasons"], facts)
            self.assertTrue(result["trace"], facts)
            self.assertTrue(result["answers"], facts)
            self.assertLessEqual(len(facts), 8, facts)

    def test_self_care_is_never_returned_with_a_warning_finding(self):
        for facts, result in self.paths:
            if result["level"] == 1:
                self.assertEqual(result["also_noted"], [], facts)

    def test_higher_risk_never_lowers_the_urgency(self):
        by_key = {}
        for facts, result in self.paths:
            key = tuple(sorted((k, str(v)) for k, v in facts.items() if k != "risk"))
            by_key.setdefault(key, {})[facts["risk"]] = result["level"]
        compared = 0
        for key, levels in by_key.items():
            if "yes" in levels and "no" in levels:
                self.assertGreaterEqual(levels["yes"], levels["no"], key)
                compared += 1
        self.assertGreater(compared, 100)

    def test_older_or_younger_age_never_lowers_urgency_for_the_same_answers_vs_adult(self):
        by_key = {}
        for facts, result in self.paths:
            key = tuple(sorted((k, str(v)) for k, v in facts.items() if k != "age"))
            by_key.setdefault(key, {})[facts["age"]] = result["level"]
        for key, levels in by_key.items():
            if "adult" in levels and "baby_u3m" in levels:
                self.assertGreaterEqual(levels["baby_u3m"], levels["adult"], key)


class EngineBehaviourTests(unittest.TestCase):
    def test_first_question_is_the_danger_check(self):
        step = app.next_step({})
        self.assertFalse(step["done"])
        self.assertEqual(step["question"]["id"], "redflags")
        self.assertTrue(step["question"]["why"])
        self.assertTrue(step["question"]["used_by"])

    def test_only_relevant_questions_are_asked_after_the_complaint(self):
        facts = {"redflags": ["none"], "age": "adult", "complaint": "headache", "risk": "no"}
        asked = []
        while True:
            step = app.next_step(facts)
            if step["done"]:
                break
            asked.append(step["question"]["id"])
            q = app.QUESTION_BY_ID[step["question"]["id"]]
            facts[q["id"]] = ["none"] if q["type"] == "multi" else option_values(q["id"])[-1]
        self.assertEqual(asked, ["ha_onset", "ha_sx", "ha_known"])

    def test_progress_counts_answered_and_remaining(self):
        step = app.next_step({"redflags": ["none"], "age": "adult", "complaint": "fever", "risk": "no"})
        self.assertEqual(step["progress"], {"answered": 4, "total": 7})

    def test_trace_is_written_in_if_then_form(self):
        facts = {"redflags": ["chest"]}
        trace = app.next_step(facts)["result"]["trace"][0]
        self.assertEqual(trace["id"], "RF2")
        self.assertTrue(trace["if"][0].startswith("Danger signs includes"))
        self.assertIn("heart", trace["then"])


class ValidationTests(unittest.TestCase):
    def test_rejects_bad_input(self):
        bad = [
            {"nonsense": "x"},
            {"age": "ancient"},
            {"age": ["adult"]},
            {"redflags": "none"},
            {"redflags": []},
            {"redflags": ["none", "chest"]},
            {"redflags": ["chest", "chest"]},
            {"redflags": ["bogus"]},
            {"age": 5},
        ]
        for facts in bad:
            with self.subTest(facts=facts):
                self.assertEqual(app.handle_triage({"facts": facts})[0], 400)
        self.assertEqual(app.handle_triage({"facts": []})[0], 400)

    def test_empty_request_starts_the_consultation(self):
        status, payload = app.handle_triage({})
        self.assertEqual(status, 200)
        self.assertFalse(payload["done"])


if __name__ == "__main__":
    unittest.main()
