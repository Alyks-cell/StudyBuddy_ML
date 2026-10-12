import unittest

import app

FIT_LABELS = {"Strong match", "Good match", "Starting point"}


class RecommendationCoverageTests(unittest.TestCase):
    def test_every_subject_level_challenge_time_path_returns_a_complete_plan(self):
        checked = 0
        for subject in app.SUBJECT_STRUGGLES:
            for level in app.LEVELS:
                for struggle in app.get_struggles(subject, level):
                    for minutes in (5, 15, 30, 60, 240):
                        with self.subTest(subject=subject, level=level, struggle=struggle, minutes=minutes):
                            result = app.recommend(subject, struggle, level=level, minutes=minutes)
                            self.assertTrue(result["method"].strip())
                            self.assertTrue(result["reason"].strip())
                            self.assertTrue(result["why"].strip())
                            self.assertTrue(result["steps"])
                            self.assertTrue(result["time_note"].strip())
                            self.assertIn(result["fit"]["label"], FIT_LABELS)
                            self.assertEqual(result["minutes"], minutes)
                            self.assertLessEqual(len(result["steps"]), app.max_steps_for(minutes))
                            self.assertLessEqual(len(result["alternatives"]), 2)
                            for alternative in result["alternatives"]:
                                self.assertTrue(alternative["why"].strip())
                            checked += 1
        self.assertGreater(checked, 500)

    def test_every_listed_challenge_has_a_rule_not_just_the_fallback(self):
        # A "Starting point" label is honest but means a listed challenge has no rule.
        for subject in app.SUBJECT_STRUGGLES:
            for level in app.LEVELS:
                for struggle in app.get_struggles(subject, level):
                    result = app.recommend(subject, struggle, level=level)
                    self.assertNotEqual(
                        result["fit"]["label"], "Starting point",
                        f"{subject}/{level}/{struggle} has no rule",
                    )

    def test_subject_rules_are_labeled_as_strong_matches(self):
        result = app.recommend("math", "memorizing formulas", "short")
        self.assertEqual(result["fit"]["label"], "Strong match")

    def test_generic_rules_are_labeled_as_good_matches(self):
        result = app.recommend("math", "preparing for a test", "medium")
        self.assertEqual(result["fit"]["label"], "Good match")

    def test_unknown_challenge_returns_an_honest_starting_point(self):
        result = app.recommend("math", "an unlisted challenge", "medium")
        self.assertTrue(result["method"])
        self.assertTrue(result["steps"])
        self.assertEqual(result["fit"]["label"], "Starting point")


class LevelTests(unittest.TestCase):
    def test_level_changes_the_challenge_options(self):
        beginner = app.get_struggles("math", "beginner")
        advanced = app.get_struggles("math", "advanced")
        self.assertIn("Understanding the basics", beginner)
        self.assertNotIn("Understanding the basics", advanced)
        self.assertIn("Exam speed & accuracy", advanced)
        self.assertNotIn("Getting started", advanced)

    def test_level_changes_the_steps(self):
        beginner = app.recommend("math", "memorizing formulas", level="beginner", minutes=60)
        intermediate = app.recommend("math", "memorizing formulas", level="intermediate", minutes=60)
        advanced = app.recommend("math", "memorizing formulas", level="advanced", minutes=60)
        self.assertTrue(beginner["steps"][0].startswith("Warm up:"))
        self.assertEqual(len(intermediate["steps"]), 4)
        self.assertTrue(advanced["steps"][-1].startswith("Stretch:"))

    def test_unknown_level_falls_back_to_intermediate(self):
        self.assertEqual(app.recommend("math", "memorizing formulas", level="wizard")["level"], "intermediate")


class TimeTests(unittest.TestCase):
    def test_custom_minutes_scale_the_step_count(self):
        short = app.recommend("math", "memorizing formulas", minutes=8)
        long_ = app.recommend("math", "memorizing formulas", minutes=90, level="advanced")
        self.assertEqual(len(short["steps"]), 1)
        self.assertEqual(len(long_["steps"]), 5)
        self.assertEqual(short["minutes"], 8)

    def test_minutes_are_clamped_and_bad_values_fall_back_to_the_preset(self):
        self.assertEqual(app.recommend("math", "memorizing formulas", minutes=1)["minutes"], app.MIN_MINUTES)
        self.assertEqual(app.recommend("math", "memorizing formulas", minutes=99999)["minutes"], app.MAX_MINUTES)
        self.assertEqual(app.recommend("math", "memorizing formulas", "short", minutes="abc")["minutes"], 15)
        self.assertEqual(app.recommend("math", "memorizing formulas", "long")["minutes"], 60)

    def test_preset_step_counts_match_the_old_behaviour(self):
        self.assertEqual(len(app.recommend("math", "memorizing formulas", "short")["steps"]), 2)
        self.assertEqual(len(app.recommend("math", "memorizing formulas", "medium")["steps"]), 4)


class DeadlineTests(unittest.TestCase):
    def test_no_deadline_means_no_countdown(self):
        self.assertIsNone(app.recommend("math", "memorizing formulas")["countdown"])

    def test_deadline_changes_guidance_by_days_left(self):
        modes = {d: app.recommend("math", "memorizing formulas", exam="Calculus final", days_left=d)["countdown"]["mode"]
                 for d in (0, 1, 3, 6, 10, 30)}
        self.assertEqual(modes, {0: "today", 1: "tomorrow", 3: "crunch", 6: "week", 10: "fortnight", 30: "long"})

    def test_review_offsets_never_land_on_or_after_the_deadline(self):
        for days in range(0, 40):
            countdown = app.recommend("math", "memorizing formulas", days_left=days)["countdown"]
            self.assertTrue(all(o < days for o in countdown["review_offsets"]), days)

    def test_close_deadline_adds_a_triage_step_and_far_deadline_a_map_step(self):
        near = app.recommend("math", "memorizing formulas", minutes=60, days_left=1)
        far = app.recommend("math", "memorizing formulas", minutes=60, days_left=30)
        self.assertTrue(near["steps"][0].startswith("Triage:"))
        self.assertTrue(far["steps"][0].startswith("Map the syllabus:"))

    def test_invalid_days_left_is_ignored(self):
        self.assertIsNone(app.recommend("math", "memorizing formulas", days_left=-3)["countdown"])
        self.assertIsNone(app.recommend("math", "memorizing formulas", days_left="soon")["countdown"])

    def test_exam_name_is_cleaned(self):
        result = app.recommend("math", "memorizing formulas", exam="  Final\n\texam   ", days_left=5)
        self.assertEqual(result["countdown"]["exam"], "Final exam")


class SubjectTests(unittest.TestCase):
    def test_new_subjects_are_available(self):
        for subject in ("languages", "economics", "biology", "chemistry", "law"):
            self.assertIn(subject, app.SUBJECT_STRUGGLES)

    def test_typed_subject_maps_to_the_closest_family(self):
        cases = {
            "Organic Chemistry": "chemistry",
            "Python": "programming",
            "Spanish": "languages",
            "Statistics": "math",
            "Contract law": "law",
            "Microeconomics": "economics",
            "Astronomy": "science",
            "Basket weaving": "other",
        }
        for typed, family in cases.items():
            with self.subTest(typed=typed):
                self.assertEqual(app.resolve_subject("Other", typed), (family, typed))

    def test_typed_subject_is_shown_and_plan_is_relevant(self):
        result = app.recommend("Other", "Solving calculations (moles, stoichiometry)", custom_subject="Organic Chemistry")
        self.assertEqual(result["subject"], "Organic Chemistry")
        self.assertEqual(result["fit"]["label"], "Strong match")
        self.assertIn("Organic Chemistry", result["why"])

    def test_typed_subject_changes_challenge_options(self):
        options = app.get_struggles("Other", "intermediate", "French")
        self.assertIn("Speaking & pronunciation", options)

    def test_typed_subject_is_length_limited_and_cleaned(self):
        subject, display = ("other", app.clean_text("x" * 500 + "\x00", 60))
        self.assertEqual(len(display), 60)
        self.assertEqual(app.resolve_subject(subject, "a" * 500)[1], "a" * 60)


class RequestHandlingTests(unittest.TestCase):
    def test_struggles_requires_a_subject(self):
        self.assertEqual(app.handle_struggles({})[0], 400)
        status, payload = app.handle_struggles({"subject": "Law", "level": "beginner"})
        self.assertEqual(status, 200)
        self.assertIn("Applying rules to facts", payload["struggles"])

    def test_recommend_requires_subject_and_struggle(self):
        self.assertEqual(app.handle_recommend({"subject": "Math"})[0], 400)
        status, payload = app.handle_recommend({
            "subject": "Math", "struggle": "Memorizing formulas", "level": "advanced",
            "minutes": 45, "exam": "Final", "days_left": 4,
        })
        self.assertEqual(status, 200)
        self.assertEqual(payload["minutes"], 45)
        self.assertEqual(payload["countdown"]["days_left"], 4)

    def test_handlers_survive_hostile_values(self):
        status, _ = app.handle_recommend({
            "subject": "Math", "struggle": "Memorizing formulas", "level": ["x"],
            "minutes": {"a": 1}, "days_left": [], "exam": 12345,
        })
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
