"""Symptom Triage Helper: a rule-based expert system.

It gives general triage guidance only (how urgently to seek care). It never
names a diagnosis and is not a substitute for a clinician or emergency services.

Architecture
------------
* Knowledge base ... QUESTIONS (what can be asked) and RULES (IF conditions THEN urgency).
* Working memory .. `facts`, the user's answers so far (a dict).
* Inference engine  forward chaining: every rule whose conditions all hold fires.
                    Conflict resolution: the highest urgency among fired rules wins.
* Question control  asks the next applicable unanswered question, and stops early
                    as soon as an emergency rule fires.
* Explanation ..... "why am I asked this?" (which rules use the answer) and
                    "how was this concluded?" (the rules that fired, in IF-THEN form).
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Urgency levels
# ---------------------------------------------------------------------------

LEVELS = {
    4: {"key": "emergency", "label": "Emergency", "action": "Call your local emergency number now."},
    3: {"key": "urgent", "label": "Urgent", "action": "Get medical care today."},
    2: {"key": "soon", "label": "See a doctor soon", "action": "Book an appointment within 1–3 days."},
    1: {"key": "selfcare", "label": "Self-care at home", "action": "You can probably look after this at home."},
}

DISCLAIMER = (
    "This tool gives general guidance only. It is not a diagnosis and does not replace a doctor, "
    "nurse or emergency services. If you think it is an emergency, call your local emergency number "
    "(for example 911, 999 or 112) instead of using this checker."
)

# ---------------------------------------------------------------------------
# Knowledge base: questions
# ---------------------------------------------------------------------------
# type "single": pick one. type "multi": pick any; "none" is exclusive.
# `complaint`: the question is only asked for that main problem.

def _q(qid, short, text, qtype, options, why, complaint=None):
    return {
        "id": qid, "short": short, "text": text, "type": qtype,
        "options": [{"value": v, "label": label} for v, label in options],
        "why": why, "complaint": complaint,
    }


QUESTIONS = [
    _q("redflags", "Danger signs", "Right now, do you have any of these?", "multi", [
        ("breathing", "Severe trouble breathing, or can't speak a full sentence"),
        ("chest", "Chest pain, pressure or tightness"),
        ("blue", "Blue or grey lips or face"),
        ("faint", "Fainted, can't be woken, or sudden confusion"),
        ("stroke", "Sudden face drooping, arm or leg weakness, or slurred speech"),
        ("bleeding", "Heavy bleeding that won't stop with firm pressure"),
        ("seizure", "A seizure (fit) now or just now"),
        ("allergy", "Swelling of lips, face or tongue, or throat tightness after a sting, food or medicine"),
        ("selfharm", "Thoughts of harming yourself or someone else"),
        ("none", "None of these"),
    ], "Some problems are dangerous whatever else is going on, so they are checked first. "
       "If you choose any of them, the questions stop and you are told what to do straight away."),

    _q("age", "Age group", "How old is the person who needs advice?", "single", [
        ("baby_u3m", "Under 3 months"),
        ("baby", "3 to 11 months"),
        ("child", "1 to 12 years"),
        ("adult", "13 to 64 years"),
        ("senior", "65 or older"),
    ], "Age changes how serious the same symptom is. For example, a fever in a very young baby "
       "is treated far more cautiously than in an adult."),

    _q("complaint", "Main problem", "What is the main problem?", "single", [
        ("fever", "Fever, or feeling feverish"),
        ("cough", "Cough or a breathing problem"),
        ("throat", "Sore throat or cold"),
        ("headache", "Headache"),
        ("stomach", "Stomach upset (vomiting, diarrhea, belly pain)"),
        ("other", "Something else"),
    ], "The main problem decides which follow-up questions are relevant, so you are not asked about "
       "things that don't apply."),

    _q("risk", "Higher-risk condition",
       "Does any of this apply? A long-term illness (heart, lung, kidney, diabetes), a weakened "
       "immune system (for example chemotherapy, steroids or a transplant), or pregnancy.",
       "single", [("yes", "Yes"), ("no", "No")],
       "Some conditions make infections and other problems riskier, so the same symptoms may need "
       "care sooner."),

    # ── Fever ──────────────────────────────────────────────────────────────
    _q("temp", "Highest temperature", "What is the highest temperature so far?", "single", [
        ("under38", "Under 38 °C (100.4 °F)"),
        ("t38", "38 to 38.9 °C (100.4 to 102 °F)"),
        ("t39", "39 to 39.9 °C (102.1 to 103.8 °F)"),
        ("t40", "40 °C (104 °F) or higher"),
        ("unknown", "Not measured, but feels hot"),
    ], "How high the fever is helps judge how seriously the body is reacting.", "fever"),
    _q("fever_days", "Fever length", "How long has the fever lasted?", "single", [
        ("d0", "Less than 1 day"),
        ("d1_3", "1 to 3 days"),
        ("d3p", "More than 3 days"),
    ], "A fever that lasts is more likely to need a check than one that has just started.", "fever"),
    _q("fever_sx", "Fever warning signs", "Any of these with the fever?", "multi", [
        ("stiff", "Stiff neck, or pain when looking at bright light"),
        ("rash", "A rash that does not fade when a glass is pressed on it"),
        ("drowsy", "Very drowsy, floppy or hard to wake"),
        ("vomit", "Repeated vomiting, can't keep fluids down"),
        ("urine", "Pain or burning when passing urine"),
        ("none", "None of these"),
    ], "These signs can mean a fever is more than a simple infection, so they raise the urgency.", "fever"),

    # ── Cough / breathing ──────────────────────────────────────────────────
    _q("cough_breath", "Breathing", "How is your breathing?", "single", [
        ("normal", "Normal"),
        ("exert", "A bit short of breath when active or climbing stairs"),
        ("rest", "Short of breath even at rest or while talking"),
    ], "Breathlessness is one of the strongest signs that a cough needs attention.", "cough"),
    _q("cough_days", "Cough length", "How long have you had the cough?", "single", [
        ("lt1w", "Under 1 week"),
        ("w1_3", "1 to 3 weeks"),
        ("w3p", "More than 3 weeks"),
    ], "Most coughs from colds fade within about 3 weeks. A longer cough should be checked.", "cough"),
    _q("cough_sx", "Cough warning signs", "Any of these?", "multi", [
        ("blood", "Coughing up blood"),
        ("wheeze", "Wheezing or a whistling sound when breathing"),
        ("fever", "Fever of 38 °C (100.4 °F) or higher"),
        ("chestpain", "Chest pain when breathing in or coughing"),
        ("none", "None of these"),
    ], "These signs change how urgently a cough should be looked at.", "cough"),

    # ── Sore throat / cold ─────────────────────────────────────────────────
    _q("throat_sx", "Throat warning signs", "Any of these?", "multi", [
        ("drool", "Can't swallow your own saliva, or drooling"),
        ("muffled", "Muffled voice, or can't open your mouth fully"),
        ("fever", "High fever (38.5 °C / 101.3 °F or more) and no cough"),
        ("patches", "White patches or pus on the tonsils"),
        ("none", "None of these"),
    ], "A few throat symptoms point to problems that need a clinician, not just rest.", "throat"),
    _q("throat_days", "Throat length", "How long has the sore throat lasted?", "single", [
        ("lt1w", "Less than a week"),
        ("w1p", "A week or more"),
    ], "Sore throats from colds usually settle within a week.", "throat"),

    # ── Headache ───────────────────────────────────────────────────────────
    _q("ha_onset", "Headache start", "How did the headache start?", "single", [
        ("thunder", "Suddenly: the worst headache of my life, peaking within a minute"),
        ("gradual", "Gradually, over hours or days"),
    ], "A sudden, severe 'thunderclap' headache is treated as an emergency.", "headache"),
    _q("ha_sx", "Headache warning signs", "Any of these?", "multi", [
        ("injury", "It started after a blow to the head"),
        ("vision", "Vision changes: blurred, double or lost vision"),
        ("vomit", "Repeated vomiting"),
        ("neck", "Fever and a stiff neck"),
        ("worse", "Pain getting steadily worse over days or weeks, or waking me at night"),
        ("none", "None of these"),
    ], "These are the headache features that doctors want to see sooner rather than later.", "headache"),
    _q("ha_known", "Familiar headache", "Have you had headaches like this before?", "single", [
        ("yes", "Yes, similar to before"),
        ("no", "No, this feels new or different"),
    ], "A new kind of headache is judged differently from one you already know.", "headache"),

    # ── Stomach ────────────────────────────────────────────────────────────
    _q("gi_sx", "Stomach warning signs", "Any of these?", "multi", [
        ("bloodgi", "Vomiting blood, or black or bloody stools"),
        ("hard", "A very swollen, hard or rigid belly"),
        ("severe", "Severe belly pain that is constant or getting worse"),
        ("rlq", "Pain low on the right side of the belly, with fever"),
        ("dehyd", "Dehydration: very dry mouth, little or no urine in 8 hours, dizzy when standing"),
        ("none", "None of these"),
    ], "These signs separate a common stomach upset from something needing care.", "stomach"),
    _q("gi_fluids", "Keeping fluids down", "Can you keep fluids down?", "single", [
        ("yes", "Yes"),
        ("no", "No, I vomit most fluids"),
    ], "Not being able to keep fluids down leads to dehydration, especially in the young and old.", "stomach"),
    _q("gi_days", "Stomach length", "How long have the symptoms lasted?", "single", [
        ("lt2", "Less than 2 days"),
        ("d2_7", "2 to 7 days"),
        ("d7p", "More than 7 days"),
    ], "Most stomach upsets pass within a couple of days.", "stomach"),
]

QUESTION_BY_ID = {q["id"]: q for q in QUESTIONS}

# ---------------------------------------------------------------------------
# Knowledge base: rules
# ---------------------------------------------------------------------------
# A rule is: id, level, if (list of conditions, ALL must hold), reason.
# A condition is (fact, operator, value):
#   "is"    answer equals value
#   "in"    answer is one of the values
#   "has"   a multi-answer contains any of the values
#   "lacks" a multi-answer contains none of the values
# Every complaint has a level-1 baseline rule, so there is always a conclusion.

YOUNG = ["baby_u3m", "baby", "child"]
BABIES = ["baby_u3m", "baby"]
GROWN = ["adult", "senior"]
FEVER_38 = ["t38", "t39", "t40", "unknown"]


def _r(rid, level, conditions, reason):
    return {"id": rid, "level": level, "if": conditions, "reason": reason}


RULES = [
    # ── Danger signs (any age, any problem) ────────────────────────────────
    _r("RF1", 4, [("redflags", "has", ["breathing"])], "Severe trouble breathing can become life-threatening quickly."),
    _r("RF2", 4, [("redflags", "has", ["chest"])], "Chest pain, pressure or tightness can be a sign of a heart problem and needs emergency assessment."),
    _r("RF3", 4, [("redflags", "has", ["blue"])], "Blue or grey lips or face can mean the body is not getting enough oxygen."),
    _r("RF4", 4, [("redflags", "has", ["faint"])], "Fainting, being unable to wake, or sudden confusion needs emergency help."),
    _r("RF5", 4, [("redflags", "has", ["stroke"])], "Sudden face drooping, limb weakness or slurred speech can be signs of a stroke. Minutes matter."),
    _r("RF6", 4, [("redflags", "has", ["bleeding"])], "Heavy bleeding that will not stop with firm pressure needs emergency help."),
    _r("RF7", 4, [("redflags", "has", ["seizure"])], "A seizure needs emergency assessment, especially a first one or one lasting over 5 minutes."),
    _r("RF8", 4, [("redflags", "has", ["allergy"])], "Swelling of the lips, face or tongue, or throat tightness, can be a severe allergic reaction."),
    _r("RF9", 4, [("redflags", "has", ["selfharm"])], "You may be at risk of harm. Please contact emergency services or a crisis line now; you do not have to face this alone."),

    # ── Fever ──────────────────────────────────────────────────────────────
    _r("F1", 4, [("complaint", "is", "fever"), ("age", "is", "baby_u3m"), ("temp", "in", FEVER_38)],
       "A fever of 38 °C or more in a baby under 3 months needs an emergency assessment, even if the baby looks well."),
    _r("F2", 3, [("complaint", "is", "fever"), ("age", "is", "baby_u3m")],
       "Any sign of fever in a baby under 3 months should be checked by a clinician today."),
    _r("F3", 3, [("complaint", "is", "fever"), ("age", "is", "baby"), ("temp", "in", ["t39", "t40", "unknown"])],
       "A high or unmeasured fever in a baby aged 3 to 11 months should be checked today."),
    _r("F4", 2, [("complaint", "is", "fever"), ("age", "is", "baby"), ("temp", "is", "t38")],
       "A fever in a baby aged 3 to 11 months should be checked by a doctor soon."),
    _r("F5", 4, [("complaint", "is", "fever"), ("fever_sx", "has", ["stiff", "rash"])],
       "A stiff neck, light sensitivity or a rash that does not fade, together with fever, can be signs of a serious infection that needs emergency care."),
    _r("F6", 4, [("complaint", "is", "fever"), ("age", "in", YOUNG), ("fever_sx", "has", ["drowsy"])],
       "A feverish child or baby who is very drowsy, floppy or hard to wake needs emergency care."),
    _r("F7", 3, [("complaint", "is", "fever"), ("age", "in", GROWN), ("fever_sx", "has", ["drowsy"])],
       "Being very drowsy with a fever should be assessed by a clinician today."),
    _r("F8", 3, [("complaint", "is", "fever"), ("temp", "is", "t40")],
       "A temperature of 40 °C or higher should be assessed today."),
    _r("F9", 3, [("complaint", "is", "fever"), ("fever_sx", "has", ["vomit"]), ("age", "in", YOUNG + ["senior"])],
       "Repeated vomiting with a fever risks dehydration, which is more dangerous in the very young and the elderly."),
    _r("F10", 2, [("complaint", "is", "fever"), ("fever_sx", "has", ["vomit"]), ("age", "is", "adult")],
       "Repeated vomiting with a fever can lead to dehydration and should be checked soon."),
    _r("F11", 3, [("complaint", "is", "fever"), ("risk", "is", "yes"), ("temp", "in", FEVER_38)],
       "A fever with a long-term illness, a weakened immune system or pregnancy should be assessed today."),
    _r("F12", 3, [("complaint", "is", "fever"), ("age", "is", "senior"), ("temp", "in", ["t39", "t40"])],
       "A high fever in someone aged 65 or older should be assessed today."),
    _r("F13", 2, [("complaint", "is", "fever"), ("age", "is", "senior"), ("temp", "is", "t38")],
       "A fever in someone aged 65 or older should be checked soon."),
    _r("F14", 2, [("complaint", "is", "fever"), ("age", "is", "child"), ("temp", "in", ["t39", "t40"])],
       "A high fever in a child should be checked by a doctor soon if it does not settle."),
    _r("F15", 2, [("complaint", "is", "fever"), ("fever_days", "is", "d3p")],
       "A fever lasting more than 3 days should be checked."),
    _r("F16", 2, [("complaint", "is", "fever"), ("fever_sx", "has", ["urine"])],
       "Pain or burning when passing urine with a fever can mean an infection that needs treatment."),
    _r("F0", 1, [("complaint", "is", "fever")],
       "Fever on its own is common with infections and often settles with rest and fluids."),

    # ── Cough / breathing ──────────────────────────────────────────────────
    _r("C1", 3, [("complaint", "is", "cough"), ("cough_breath", "is", "rest")],
       "Being short of breath at rest or while talking should be assessed today."),
    _r("C2", 3, [("complaint", "is", "cough"), ("cough_sx", "has", ["blood"])],
       "Coughing up blood should be assessed today."),
    _r("C3", 3, [("complaint", "is", "cough"), ("age", "in", YOUNG), ("cough_sx", "has", ["wheeze"])],
       "Wheezing in a baby or child should be assessed today."),
    _r("C4", 2, [("complaint", "is", "cough"), ("age", "in", GROWN), ("cough_sx", "has", ["wheeze"])],
       "Wheezing should be checked by a doctor soon."),
    _r("C5", 3, [("complaint", "is", "cough"), ("age", "is", "baby_u3m")],
       "A cough in a baby under 3 months should be checked today."),
    _r("C6", 3, [("complaint", "is", "cough"), ("age", "is", "baby"), ("cough_breath", "in", ["exert", "rest"])],
       "Breathing difficulty with a cough in a baby should be checked today."),
    _r("C7", 2, [("complaint", "is", "cough"), ("cough_breath", "is", "exert")],
       "Being short of breath when active should be checked soon."),
    _r("C8", 2, [("complaint", "is", "cough"), ("cough_days", "is", "w3p")],
       "A cough lasting more than 3 weeks should be checked."),
    _r("C9", 3, [("complaint", "is", "cough"), ("risk", "is", "yes"), ("cough_sx", "has", ["fever"])],
       "A cough with fever and a long-term illness, weakened immune system or pregnancy should be assessed today."),
    _r("C10", 2, [("complaint", "is", "cough"), ("cough_sx", "has", ["chestpain"])],
       "Chest pain when breathing or coughing should be checked soon."),
    _r("C11", 2, [("complaint", "is", "cough"), ("cough_sx", "has", ["fever"]), ("cough_days", "in", ["w1_3", "w3p"])],
       "A cough with fever lasting over a week should be checked."),
    _r("C0", 1, [("complaint", "is", "cough")],
       "Most coughs come from colds and clear up on their own within about 3 weeks."),

    # ── Sore throat / cold ─────────────────────────────────────────────────
    _r("S1", 4, [("complaint", "is", "throat"), ("throat_sx", "has", ["drool"])],
       "Being unable to swallow saliva, or drooling, can mean the airway is at risk and needs emergency care."),
    _r("S2", 3, [("complaint", "is", "throat"), ("throat_sx", "has", ["muffled"])],
       "A muffled voice or being unable to open the mouth fully should be assessed today."),
    _r("S3", 3, [("complaint", "is", "throat"), ("risk", "is", "yes"), ("throat_sx", "has", ["fever"])],
       "A high fever with a sore throat and a higher-risk condition should be assessed today."),
    _r("S4", 2, [("complaint", "is", "throat"), ("throat_sx", "has", ["fever"])],
       "A high fever with a sore throat and no cough should be checked soon."),
    _r("S5", 2, [("complaint", "is", "throat"), ("throat_sx", "has", ["patches"])],
       "White patches or pus on the tonsils should be checked soon."),
    _r("S6", 2, [("complaint", "is", "throat"), ("throat_days", "is", "w1p")],
       "A sore throat lasting a week or more should be checked."),
    _r("S0", 1, [("complaint", "is", "throat")],
       "Most sore throats come from colds and settle within a week."),

    # ── Headache ───────────────────────────────────────────────────────────
    _r("H1", 4, [("complaint", "is", "headache"), ("ha_onset", "is", "thunder")],
       "A sudden, severe 'worst ever' headache needs emergency assessment."),
    _r("H2", 4, [("complaint", "is", "headache"), ("ha_sx", "has", ["neck"])],
       "A headache with fever and a stiff neck can be a sign of a serious infection and needs emergency care."),
    _r("H3", 3, [("complaint", "is", "headache"), ("ha_sx", "has", ["injury"])],
       "A headache after a blow to the head should be assessed today."),
    _r("H4", 3, [("complaint", "is", "headache"), ("ha_sx", "has", ["vision"])],
       "A headache with vision changes should be assessed today."),
    _r("H5", 3, [("complaint", "is", "headache"), ("ha_sx", "has", ["vomit"])],
       "A headache with repeated vomiting should be assessed today."),
    _r("H6", 2, [("complaint", "is", "headache"), ("ha_sx", "has", ["worse"])],
       "A headache that keeps getting worse, or wakes you at night, should be checked soon."),
    _r("H7", 2, [("complaint", "is", "headache"), ("ha_known", "is", "no"), ("age", "is", "senior")],
       "A new kind of headache at 65 or older should be checked soon."),
    _r("H8", 2, [("complaint", "is", "headache"), ("ha_known", "is", "no"), ("risk", "is", "yes")],
       "A new kind of headache with a higher-risk condition should be checked soon."),
    _r("H0", 1, [("complaint", "is", "headache")],
       "Most headaches are tension-type or migraine-type and ease with rest, fluids and pain relief."),

    # ── Stomach upset ──────────────────────────────────────────────────────
    _r("G1", 4, [("complaint", "is", "stomach"), ("gi_sx", "has", ["bloodgi"])],
       "Vomiting blood, or black or bloody stools, can mean serious bleeding and needs emergency care."),
    _r("G2", 4, [("complaint", "is", "stomach"), ("gi_sx", "has", ["hard"])],
       "A very swollen, hard belly needs emergency assessment."),
    _r("G3", 3, [("complaint", "is", "stomach"), ("gi_sx", "has", ["severe"])],
       "Severe belly pain that is constant or getting worse should be assessed today."),
    _r("G4", 3, [("complaint", "is", "stomach"), ("gi_sx", "has", ["rlq"])],
       "Pain low on the right side with fever should be assessed today."),
    _r("G5", 3, [("complaint", "is", "stomach"), ("gi_sx", "has", ["dehyd"])],
       "Signs of dehydration should be assessed today."),
    _r("G6", 3, [("complaint", "is", "stomach"), ("gi_fluids", "is", "no"), ("age", "in", YOUNG + ["senior"])],
       "Not keeping fluids down risks dehydration, which is more dangerous in the very young and the elderly."),
    _r("G7", 3, [("complaint", "is", "stomach"), ("gi_fluids", "is", "no"), ("risk", "is", "yes")],
       "Not keeping fluids down with a higher-risk condition should be assessed today."),
    _r("G8", 2, [("complaint", "is", "stomach"), ("gi_fluids", "is", "no"), ("age", "is", "adult")],
       "Not keeping fluids down should be checked soon."),
    _r("G9", 3, [("complaint", "is", "stomach"), ("age", "is", "baby_u3m")],
       "Vomiting, diarrhea or belly pain in a baby under 3 months should be checked today."),
    _r("G10", 2, [("complaint", "is", "stomach"), ("gi_days", "is", "d7p")],
       "Stomach symptoms lasting more than a week should be checked."),
    _r("G11", 2, [("complaint", "is", "stomach"), ("gi_days", "is", "d2_7"), ("age", "in", ["baby", "child", "senior"])],
       "Stomach symptoms lasting more than 2 days in a baby, child or older adult should be checked."),
    _r("G0", 1, [("complaint", "is", "stomach")],
       "Most stomach upsets pass within a couple of days with fluids and rest."),

    # ── Not covered ────────────────────────────────────────────────────────
    _r("X1", 2, [("complaint", "is", "other")],
       "This checker only covers fever, cough, sore throat, headache and stomach upset. For anything else, talk to a doctor or nurse."),
]

RULE_BY_ID = {r["id"]: r for r in RULES}

# ---------------------------------------------------------------------------
# Advice shown with the result
# ---------------------------------------------------------------------------

ADVICE = {
    4: [
        "Call your local emergency number now (for example 911, 999 or 112).",
        "Do not drive yourself. Stay with the person and unlock the door if you can.",
        "Follow the instructions of the call-taker, and do not eat or drink unless told to.",
    ],
    3: [
        "Get medical care today: a same-day appointment, an urgent-care clinic, or your local nurse or health advice line.",
        "If it gets worse, or you cannot be seen soon, go to emergency care.",
        "Take a list of medicines and, if you can, someone to go with you.",
    ],
    2: [
        "Book an appointment with a doctor or clinic within 1 to 3 days.",
        "Meanwhile rest, drink fluids, and note how symptoms change.",
        "If any warning sign below appears, get care sooner.",
    ],
}

SELFHARM_ADVICE = (
    "If you or someone else may be in danger of self-harm, call your local emergency number. "
    "In the US you can also call or text 988 for crisis support; elsewhere, contact your local crisis line."
)

SELF_CARE = {
    "fever": [
        "Rest and drink plenty of fluids.",
        "Wear light clothing and keep the room comfortable, not cold.",
        "Paracetamol (acetaminophen) or ibuprofen can ease discomfort. Follow the label for the person's age, and never give aspirin to anyone under 16.",
    ],
    "cough": [
        "Rest and drink warm fluids. Honey in a warm drink can soothe a cough (not for babies under 1).",
        "Keep away from smoke.",
        "Most coughs from colds fade within about 3 weeks.",
    ],
    "throat": [
        "Drink warm fluids and rest your voice.",
        "Adults can gargle warm salt water or use throat lozenges (not for young children).",
        "Pain relief can help: follow the label for the person's age.",
    ],
    "headache": [
        "Rest in a quiet, dim room and drink water.",
        "Eat regular meals, and try to keep a regular sleep pattern.",
        "Pain relief can help: follow the label, and avoid using it on most days of the week.",
    ],
    "stomach": [
        "Sip fluids little and often. An oral rehydration solution is best if you have one.",
        "Eat small, plain meals once you feel hungry.",
        "Rest and wash your hands often to avoid passing it on.",
    ],
}

WATCH_FOR = {
    "fever": [
        "A temperature of 40 °C (104 °F) or higher",
        "Fever lasting more than 3 days",
        "A stiff neck, a rash that does not fade, or being very drowsy",
        "Trouble breathing, or not keeping fluids down",
    ],
    "cough": [
        "Breathlessness at rest, or blue lips",
        "Coughing up blood",
        "A cough lasting more than 3 weeks",
        "Chest pain or a high fever",
    ],
    "throat": [
        "Not being able to swallow saliva, or drooling",
        "A muffled voice or being unable to open your mouth",
        "A high fever, or white patches on the tonsils",
        "Symptoms lasting more than a week",
    ],
    "headache": [
        "A sudden, severe headache unlike any before",
        "Fever with a stiff neck",
        "Vision changes, weakness, or repeated vomiting",
        "Pain that keeps getting worse",
    ],
    "stomach": [
        "Vomiting blood, or black or bloody stools",
        "Severe or worsening belly pain, or a hard belly",
        "Signs of dehydration, or not keeping fluids down",
        "Symptoms lasting more than a week",
    ],
}

# ---------------------------------------------------------------------------
# Inference engine
# ---------------------------------------------------------------------------


def label_of(qid, value):
    for option in QUESTION_BY_ID[qid]["options"]:
        if option["value"] == value:
            return option["label"]
    return str(value)


def match(condition, facts):
    """True if a single condition holds. Unanswered facts never match."""
    fact, op, value = condition
    answer = facts.get(fact)
    if answer is None:
        return False
    if op == "is":
        return answer == value
    if op == "in":
        return answer in value
    if op == "has":
        return isinstance(answer, list) and any(v in answer for v in value)
    if op == "lacks":
        return isinstance(answer, list) and not any(v in answer for v in value)
    raise ValueError(f"unknown operator {op}")


def fire_rules(facts):
    """Forward chaining: every rule whose conditions all hold fires."""
    return [rule for rule in RULES if all(match(c, facts) for c in rule["if"])]


def describe_condition(condition):
    fact, op, value = condition
    short = QUESTION_BY_ID[fact]["short"]
    names = [label_of(fact, v) for v in (value if isinstance(value, list) else [value])]
    if op == "is":
        return f"{short} is “{names[0]}”"
    if op == "in":
        return f"{short} is one of: " + "; ".join(f"“{n}”" for n in names)
    if op == "has":
        return f"{short} includes: " + "; ".join(f"“{n}”" for n in names) + " (any)"
    return f"{short} includes none of: " + "; ".join(f"“{n}”" for n in names)


def describe_rule(rule):
    return {
        "id": rule["id"],
        "level": rule["level"],
        "level_label": LEVELS[rule["level"]]["label"],
        "if": [describe_condition(c) for c in rule["if"]],
        "then": rule["reason"],
    }


def rules_using(qid):
    return sorted({r["id"] for r in RULES for c in r["if"] if c[0] == qid})


def applies(question, facts):
    wanted = question["complaint"]
    return wanted is None or facts.get("complaint") == wanted


def unanswered(facts):
    return [q for q in QUESTIONS if q["id"] not in facts and applies(q, facts)]


def validate_facts(raw):
    """Check untrusted answers against the question definitions."""
    if not isinstance(raw, dict):
        raise ValueError("facts must be an object")
    facts = {}
    for qid, answer in raw.items():
        question = QUESTION_BY_ID.get(qid)
        if question is None:
            raise ValueError(f"unknown question: {qid}")
        values = {o["value"] for o in question["options"]}
        if question["type"] == "single":
            if not isinstance(answer, str) or answer not in values:
                raise ValueError(f"invalid answer for {qid}")
            facts[qid] = answer
        else:
            if (not isinstance(answer, list) or not answer or len(answer) > len(values)
                    or not all(isinstance(a, str) and a in values for a in answer)
                    or len(set(answer)) != len(answer)):
                raise ValueError(f"invalid answer for {qid}")
            if "none" in answer and len(answer) > 1:
                raise ValueError(f"'none' cannot be combined for {qid}")
            facts[qid] = list(answer)
    return facts


def build_result(facts, fired):
    top = max((r["level"] for r in fired), default=2)
    level = LEVELS[top]
    top_rules = sorted((r for r in fired if r["level"] == top), key=lambda r: r["id"])
    others = sorted((r for r in fired if r["level"] < top and r["level"] > 1), key=lambda r: (-r["level"], r["id"]))
    complaint = facts.get("complaint")

    if top == 1:
        advice = list(SELF_CARE.get(complaint, []))
    else:
        advice = list(ADVICE[top])
    if "selfharm" in facts.get("redflags", []):
        advice.insert(0, SELFHARM_ADVICE)

    answers = []
    for q in QUESTIONS:
        if q["id"] in facts:
            answer = facts[q["id"]]
            values = answer if isinstance(answer, list) else [answer]
            answers.append({"question": q["short"], "answer": "; ".join(label_of(q["id"], v) for v in values)})

    return {
        "level": top,
        "key": level["key"],
        "label": level["label"],
        "action": level["action"],
        "reasons": [describe_rule(r) for r in top_rules],
        "also_noted": [describe_rule(r) for r in others],
        "advice": advice,
        "watch_for": WATCH_FOR.get(complaint, []) if top <= 2 else [],
        "trace": [describe_rule(r) for r in sorted(fired, key=lambda r: (-r["level"], r["id"]))],
        "answers": answers,
        "questions_asked": len(facts),
        "resolution": (
            "Several rules can fire at once. The highest urgency among them decides the result, "
            "so a danger sign is never outvoted by milder findings."
        ),
        "disclaimer": DISCLAIMER,
    }


def next_step(raw_facts):
    """One turn of the consultation: the next question, or the final result."""
    facts = validate_facts(raw_facts)
    fired = fire_rules(facts)
    # Stop early on an emergency: asking more questions would only delay help.
    if any(r["level"] == 4 for r in fired):
        return {"done": True, "result": build_result(facts, fired)}
    pending = unanswered(facts)
    if not pending:
        return {"done": True, "result": build_result(facts, fired)}

    question = pending[0]
    return {
        "done": False,
        "question": {
            "id": question["id"],
            "text": question["text"],
            "type": question["type"],
            "options": question["options"],
            "why": question["why"],
            "used_by": rules_using(question["id"]),
        },
        "progress": {"answered": len(facts), "total": len(facts) + len(pending)},
    }


# ---------------------------------------------------------------------------
# Request handling shared by the local server and the Vercel function
# ---------------------------------------------------------------------------


def handle_triage(data):
    try:
        return 200, next_step(data.get("facts", {}))
    except ValueError as err:
        return 400, str(err)


PUBLIC_FILES = {"/", "/index.html", "/robots.txt", "/sw.js", "/manifest.webmanifest"}


class AppHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
        ".js": "text/javascript",
        ".svg": "image/svg+xml",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _is_public(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        return path in PUBLIC_FILES or (path.startswith("/static/") and ".." not in path)

    def do_GET(self):
        # Only serve the site itself, never source files or the .git folder.
        if not self._is_public():
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if not self._is_public():
            self.send_error(404)
            return
        super().do_HEAD()

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        super().end_headers()

    def do_POST(self):
        if self.path != "/triage":
            self.send_error(404)
            return
        data = self._read_json()
        if data is None:
            self.send_error(400, "Please send valid JSON")
            return
        status, payload = handle_triage(data)
        if status != 200:
            self.send_error(status, payload)
            return
        self._send_json(payload)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0 or length > 20000:
                raise ValueError
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError
            return data
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            return None

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # Request lines only; answers are in the POST body and are never logged.
        super().log_message(fmt, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), AppHandler)
    print("Symptom Triage Helper is running at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
