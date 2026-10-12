from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import re

ROOT = Path(__file__).parent

# ---------------------------------------------------------------------------
# Expert System Knowledge Base
# ---------------------------------------------------------------------------
# Each rule maps (subject family, struggle) -> recommendation with method,
# reason, and actionable steps. Subject-specific rules override generic ones.
# Level, time and deadline modifiers then adapt the plan around the rule.
# ---------------------------------------------------------------------------

LEVELS = ("beginner", "intermediate", "advanced")
DEFAULT_LEVEL = "intermediate"
MIN_MINUTES = 5
MAX_MINUTES = 480

# Which struggles are relevant per subject
SUBJECT_STRUGGLES = {
    "math": [
        "Memorizing formulas",
        "Solving word problems",
        "Understanding concepts",
        "Showing work / steps",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "science": [
        "Memorizing terms & definitions",
        "Understanding concepts",
        "Connecting theory to experiments",
        "Interpreting graphs & data",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "biology": [
        "Memorizing terms & definitions",
        "Understanding processes & pathways",
        "Labeling & redrawing diagrams",
        "Interpreting graphs & data",
        "Understanding concepts",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "chemistry": [
        "Memorizing terms & definitions",
        "Solving calculations (moles, stoichiometry)",
        "Understanding reaction mechanisms",
        "Understanding concepts",
        "Interpreting graphs & data",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "languages": [
        "Building vocabulary",
        "Speaking & pronunciation",
        "Listening comprehension",
        "Grammar & verb forms",
        "Writing in the language",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "economics": [
        "Understanding concepts",
        "Interpreting graphs & models",
        "Applying theory to real cases",
        "Remembering key terms & formulas",
        "Solving problems",
        "Writing essays",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "history": [
        "Remembering dates & events",
        "Understanding cause & effect",
        "Writing essays",
        "Connecting themes across eras",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "english": [
        "Writing essays",
        "Understanding literature",
        "Grammar & sentence structure",
        "Building vocabulary",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "law": [
        "Remembering cases & statutes",
        "Reading cases & statutes",
        "Applying rules to facts",
        "Understanding concepts",
        "Writing essays",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "programming": [
        "Understanding concepts",
        "Debugging code",
        "Solving problems",
        "Remembering syntax",
        "Building projects",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
    "other": [
        "Understanding concepts",
        "Remembering facts",
        "Writing essays",
        "Preparing for a test",
        "Staying focused",
        "Getting started",
    ],
}

# Challenges that only make sense at a given level. They are shown first so the
# level choice visibly changes the options, and they have their own generic rules.
LEVEL_EXTRA_STRUGGLES = {
    "beginner": ["Understanding the basics", "Not knowing what to study first"],
    "intermediate": ["Filling gaps in what I know", "Making things stick longer"],
    "advanced": [
        "Applying ideas to unfamiliar problems",
        "Exam speed & accuracy",
        "Finding my last weak spots",
    ],
}

# Challenges that are rarely the right focus at a given level.
LEVEL_HIDDEN_STRUGGLES = {
    "beginner": {
        "connecting themes across eras",
        "connecting theory to experiments",
        "building projects",
    },
    "intermediate": set(),
    "advanced": {"getting started"},
}

_LEVEL_EXTRA_KEYS = {s.lower() for items in LEVEL_EXTRA_STRUGGLES.values() for s in items}

# Typed-in subjects ("Other") are mapped to the closest known subject family so
# the plan stays relevant. Order matters: the first family that matches wins.
SUBJECT_KEYWORDS = [
    ("programming", r"python|java|javascript|typescript|coding|programming|computer science|c\+\+|c#|sql|html|css|software|algorithm|data structure|react|rust|golang|web dev|machine learning"),
    ("chemistry", r"chem|organic|stoichiometr|biochem"),
    ("biology", r"bio|anatomy|physiolog|ecolog|genetic|zoolog|botan|microbio|medic|nursing|neuro|pharmac"),
    ("math", r"math|algebra|calculus|geometr|trigonometr|statistic|probabilit|arithmetic|linear|discrete|numeric"),
    ("science", r"physic|astronom|geolog|earth science|environmental|science|engineering"),
    ("languages", r"spanish|french|german|italian|japanese|chinese|mandarin|korean|arabic|latin|russian|portuguese|hindi|dutch|swedish|greek|language|esl|vocab"),
    ("economics", r"econom|financ|accounting|business|marketing|commerce|management"),
    ("law", r"law|legal|jurisprud|contract|tort|constitution|bar exam|criminal|statut"),
    ("history", r"histor|politic|geograph|archaeolog|civics|government|anthropolog|sociolog"),
    ("english", r"english|literature|writing|poetry|essay|composition|rhetoric|linguistic|novel"),
]

# ---- Rules ----------------------------------------------------------------

_TERM_FLASHCARDS = (
    "Term–Example Flashcards",
    "Connecting a term to a real example helps you remember what it means and when it applies.",
    [
        "Write the term on one side of a card, the definition + a real example on the other.",
        "Quiz yourself: see the term, recall the definition and example.",
        "Sort cards into 'got it' and 'missed it' piles.",
        "Repeat the missed pile until you clear it.",
    ],
)

_GRAPH_NARRATION = (
    "Graph Narration",
    "Describing a graph in plain language forces you to understand what the data is showing.",
    [
        "Read the title, axis labels, and units first.",
        "Describe the overall trend in one sentence (rising, falling, steady).",
        "Identify any outliers or turning points.",
        "Write one sentence connecting the trend to the concept you are studying.",
    ],
)

# (subject, struggle) -> (method, reason, steps[])
# Specific rules take priority; generic struggle rules are the fallback.
RULES = {
    # ── Math ───────────────────────────────────────────────────────────────
    ("math", "memorizing formulas"): (
        "Formula Deconstruction",
        "Breaking a formula into named parts and practicing it in context builds both understanding and recall.",
        [
            "Write the formula and label what each symbol means.",
            "Solve five practice problems without looking at the formula or solution.",
            "Check your answers and note which formulas or steps you forgot.",
            "Retry the missed problems from memory, then explain when the formula applies.",
        ],
    ),
    ("math", "solving word problems"): (
        "Translate → Plan → Solve",
        "Word problems are hard because they hide the math in language. Translating first removes that barrier.",
        [
            "Read the problem and underline the key numbers and what you're asked to find.",
            "Rewrite the problem as a math equation or expression.",
            "Solve the equation step by step.",
            "Check: does your answer make sense in the original context?",
        ],
    ),
    ("math", "understanding concepts"): (
        "Concept Mapping",
        "Math concepts connect to each other. Mapping them reveals the logic you're missing.",
        [
            "Read the definition or theorem in your textbook.",
            "In your own words, explain what it means and when you'd use it.",
            "Draw a simple diagram or example that illustrates the idea.",
            "Connect it to a concept you already understand.",
        ],
    ),
    ("math", "showing work / steps"): (
        "Narrated Solution Practice",
        "Writing out every step forces your brain to make the implicit reasoning explicit.",
        [
            "Pick a practice problem and write each step on a new line.",
            "Next to each step, write a short reason why you did it.",
            "Compare your steps to a textbook solution — did you skip anything?",
            "Redo the problem, this time filling in any missing steps.",
        ],
    ),

    # ── Science ────────────────────────────────────────────────────────────
    ("science", "memorizing terms & definitions"): _TERM_FLASHCARDS,
    ("science", "connecting theory to experiments"): (
        "Hypothesis–Evidence Bridge",
        "Linking what you expected to happen with what actually happened makes lab work meaningful.",
        [
            "State the theory or principle the experiment tests.",
            "Write your hypothesis — what should happen if the theory is true?",
            "Summarize your actual observations or data in one sentence.",
            "Explain whether the data supports or contradicts the hypothesis and why.",
        ],
    ),
    ("science", "interpreting graphs & data"): _GRAPH_NARRATION,

    # ── Biology ────────────────────────────────────────────────────────────
    ("biology", "understanding processes & pathways"): (
        "Process Chain Retelling",
        "Processes like respiration or protein synthesis are sequences. Retelling them link by link shows where the chain breaks.",
        [
            "List the stages of the process in order, with the input and output of each.",
            "Cover the list and retell the process aloud as a short story.",
            "Check against your notes and mark any stage you skipped or swapped.",
            "Add one sentence per stage about why it matters to the next stage.",
        ],
    ),
    ("biology", "labeling & redrawing diagrams"): (
        "Blank Diagram Redraw",
        "Redrawing a diagram from memory tests recall of both the parts and how they connect.",
        [
            "Study the diagram for two minutes, naming each part aloud.",
            "Cover it and redraw the diagram from memory on a blank page.",
            "Label every part, then compare with the original and mark what you missed.",
            "Redraw only the parts you missed, then label them again.",
        ],
    ),

    # ── Chemistry ──────────────────────────────────────────────────────────
    ("chemistry", "solving calculations (moles, stoichiometry)"): (
        "Unit-Tracked Worked Calculations",
        "Carrying units through every line catches most calculation errors and shows what each step is converting.",
        [
            "Write what you are given and what you need, with units.",
            "Write the chain of conversions (for example grams → moles → moles of product → grams) before any numbers.",
            "Calculate step by step, carrying units on every line and cancelling them as you go.",
            "Sanity-check the size and units of the answer, then redo one similar problem without notes.",
        ],
    ),
    ("chemistry", "understanding reaction mechanisms"): (
        "Mechanism Storyboard",
        "Mechanisms are stories about electrons. Drawing each step as a frame makes the logic visible instead of memorized.",
        [
            "Draw the reactants and mark where electrons are rich and where they are poor.",
            "Draw one arrow at a time showing where the electrons move, one frame per step.",
            "Cover your frames and redraw the full mechanism from the reactants.",
            "Explain in one sentence why each step happens before the next one.",
        ],
    ),

    # ── Languages ──────────────────────────────────────────────────────────
    ("languages", "building vocabulary"): (
        "Sentence-Mined Flashcards",
        "Words learned inside a sentence are easier to recall and use than words learned in isolation.",
        [
            "Pick 8 words you met in a real text or dialogue and copy the sentence each came from.",
            "On each card put the word on one side and the sentence (with the word hidden) on the other.",
            "Recall the meaning, then say a new sentence of your own aloud using the word.",
            "Re-test only the missed cards tomorrow.",
        ],
    ),
    ("languages", "speaking & pronunciation"): (
        "Shadow → Record → Compare",
        "Imitating a native speaker and hearing yourself back makes the gaps in your pronunciation audible.",
        [
            "Choose a 30-second audio clip and read its transcript once.",
            "Play it in short chunks and repeat each chunk immediately, matching rhythm and sounds.",
            "Record yourself reading the same text, then listen to both versions back to back.",
            "Note two sounds or stress patterns to fix and re-record just those lines.",
        ],
    ),
    ("languages", "listening comprehension"): (
        "Listen → Transcribe → Check",
        "Writing down what you hear forces your ear to process every word, not just the gist.",
        [
            "Pick a short clip (30–60 seconds) and listen once for the overall meaning.",
            "Replay in short chunks and write down exactly what you hear.",
            "Compare with the transcript and mark words you misheard or did not know.",
            "Listen once more without the transcript and note what you now catch.",
        ],
    ),
    ("languages", "grammar & verb forms"): (
        "Pattern Notice → Produce",
        "Seeing a pattern in real sentences and then producing your own builds intuition faster than memorizing rules.",
        [
            "Collect five example sentences that use the grammar point.",
            "Underline what changes in each and write the pattern as a one-line rule.",
            "Write five new sentences about your own life using the pattern.",
            "Check them against a reference and fix any errors, noting the rule.",
        ],
    ),
    ("languages", "writing in the language"): (
        "Short Write → Self-Correct",
        "A short text that you correct yourself builds accuracy because you must notice errors, not just receive them.",
        [
            "Write 5–6 sentences on a simple topic without a dictionary.",
            "Read them aloud and mark anything that sounds wrong or that you avoided.",
            "Look up the marked words and rules, then rewrite the passage.",
            "Keep a short list of your most frequent mistakes to check next time.",
        ],
    ),

    # ── Economics ──────────────────────────────────────────────────────────
    ("economics", "interpreting graphs & models"): (
        "Draw → Shift → Explain",
        "Drawing a model and shifting a curve yourself shows cause and effect, which memorizing the picture does not.",
        [
            "Draw the model (for example supply and demand) from memory with labeled axes.",
            "Pick one change (a tax, a new technology, a rise in income) and shift the right curve.",
            "Mark the new equilibrium and write what happened to price and quantity, and why.",
            "Repeat with a different change and compare the two outcomes.",
        ],
    ),
    ("economics", "applying theory to real cases"): (
        "Case → Model → Prediction",
        "Applying a model to a concrete news story turns abstract theory into something you can reason with.",
        [
            "Pick a short news story or real-world example.",
            "Name the economic concept or model that best fits it and why.",
            "Predict what the model says should happen next.",
            "Note where reality differs from the model and give one reason.",
        ],
    ),
    ("economics", "remembering key terms & formulas"): (
        "Definition + Diagram Cards",
        "Pairing a definition with a small sketch or example gives you two routes back to the idea.",
        [
            "Make a card for each term: definition on one side, a mini diagram or example on the other.",
            "Quiz yourself: see the term, recall the definition and sketch the example.",
            "Sort into 'know' and 'missed' piles.",
            "Repeat the missed pile until you clear it, then test the formulas by writing them from memory.",
        ],
    ),

    # ── History ────────────────────────────────────────────────────────────
    ("history", "remembering dates & events"): (
        "Timeline Story Building",
        "Putting events in sequence and linking cause/effect turns isolated dates into a story.",
        [
            "Pick 5–8 key events and arrange them on a timeline.",
            "For each event, write: what happened, what caused it, and what changed after.",
            "Cover the timeline and try to recreate it from memory.",
            "Check your version — add back anything you forgot.",
        ],
    ),
    ("history", "understanding cause & effect"): (
        "Because → Therefore Chain",
        "Tracing a chain of causes shows how events lead into each other instead of seeming random.",
        [
            "Make a timeline of five key events in this topic.",
            "For each event, write one cause and one effect.",
            "Cover your notes and quiz yourself on what caused each event and what followed.",
            "Check your answers and explain the strongest cause-and-effect link in your own words.",
        ],
    ),
    ("history", "connecting themes across eras"): (
        "Theme Comparison Table",
        "A table makes it easy to spot how the same theme (power, economy, culture) played out differently.",
        [
            "Choose a theme (e.g., democracy, trade, conflict).",
            "Create a simple table with one column per era or region.",
            "Fill in how the theme appeared in each era with a specific example.",
            "Write one sentence about what changed over time and why.",
        ],
    ),

    # ── English ────────────────────────────────────────────────────────────
    ("english", "understanding literature"): (
        "Close Reading + Annotation",
        "Marking up a passage forces you to slow down and notice the author's choices.",
        [
            "Pick a short passage (1–2 paragraphs).",
            "Read it once for the overall meaning.",
            "Read again and underline key words, imagery, or tone shifts.",
            "Write 2–3 sentences: what is the author doing here and why?",
        ],
    ),
    ("english", "grammar & sentence structure"): (
        "Error Hunt + Rewrite",
        "Finding and fixing grammar errors in context builds intuition faster than memorizing rules.",
        [
            "Take a paragraph from your own writing.",
            "Read each sentence aloud — mark anything that sounds off.",
            "Look up the specific grammar rule for each issue.",
            "Rewrite the sentences correctly and note the rule you applied.",
        ],
    ),
    ("english", "building vocabulary"): (
        "Context–Use–Review Cycle",
        "Using a new word in your own sentence cements it far better than just reading a definition.",
        [
            "Pick 5 new words from your reading.",
            "Write each word's definition in your own words.",
            "Use each word in a sentence about something in your life.",
            "Review your sentences the next day — can you recall the meanings?",
        ],
    ),

    # ── Law ────────────────────────────────────────────────────────────────
    ("law", "remembering cases & statutes"): (
        "Case Brief Cards",
        "A one-card brief with the same fields for every case makes cases comparable and quick to retrieve.",
        [
            "For each case write a card with: facts, issue, rule, holding, and reasoning in one line each.",
            "Cover the card and recall the holding and the reasoning from the case name alone.",
            "Check, and mark any field you could not recall.",
            "Retry the marked cards and say which other case each one is closest to.",
        ],
    ),
    ("law", "reading cases & statutes"): (
        "Skim → Read → Brief",
        "Knowing what you are looking for before reading dense text keeps you from getting lost in it.",
        [
            "Skim the headings, the first and last paragraphs, and any holding to learn what the text is about.",
            "Read it through once, marking the facts, the legal question and the court's answer.",
            "Write a three-sentence brief from memory: facts, rule, outcome.",
            "Re-read only the parts that did not fit your brief and fix it.",
        ],
    ),
    ("law", "applying rules to facts"): (
        "IRAC Drill",
        "Structuring an answer as Issue, Rule, Application, Conclusion makes you apply the rule rather than just state it.",
        [
            "Read a fact pattern and write the issue as a single question.",
            "State the rule, including its elements, in your own words.",
            "Apply each element to the facts in turn, noting facts that cut both ways.",
            "Write a one-line conclusion, then compare with a model answer and note anything missed.",
        ],
    ),

    # ── Programming ────────────────────────────────────────────────────────
    ("programming", "understanding concepts"): (
        "Code → Explain → Modify",
        "Running code and explaining what it does line-by-line builds real comprehension.",
        [
            "Find or write a small code example that uses the concept.",
            "Add a comment to every line explaining what it does.",
            "Predict what happens if you change one part, then test it.",
            "Summarize the concept in your own words based on what you learned.",
        ],
    ),
    ("programming", "debugging code"): (
        "Isolate → Reproduce → Fix",
        "Systematic debugging beats random guessing every time.",
        [
            "Read the error message carefully — note the line number and error type.",
            "Create the smallest possible code that reproduces the bug.",
            "Add print statements or use a debugger to trace variable values.",
            "Fix the issue, then explain why the bug happened to avoid it next time.",
        ],
    ),
    ("programming", "solving problems"): (
        "Pseudocode First",
        "Planning in plain language before coding prevents getting lost in syntax.",
        [
            "Read the problem and restate it in one sentence.",
            "List the inputs, outputs, and any constraints.",
            "Write step-by-step pseudocode in plain language.",
            "Translate each pseudocode step into real code one at a time.",
        ],
    ),
    ("programming", "remembering syntax"): (
        "Cheat Sheet + Drill",
        "Building your own reference and using it actively is more effective than memorizing.",
        [
            "Create a one-page cheat sheet of the syntax you keep forgetting.",
            "Write 3 small code snippets that use that syntax.",
            "Try to write them again tomorrow without looking.",
            "Update your cheat sheet with anything you missed.",
        ],
    ),
    ("programming", "building projects"): (
        "Feature Slice Approach",
        "Breaking a project into tiny vertical slices makes it less overwhelming.",
        [
            "Write a one-sentence description of the simplest possible version.",
            "List 3–5 features, ordered from essential to nice-to-have.",
            "Build only the first feature until it works end-to-end.",
            "Commit, then move to the next feature.",
        ],
    ),
}

# Generic fallback rules (keyed by struggle only)
GENERIC_RULES = {
    "understanding concepts": (
        "Read → Recall → Check",
        "Explaining from memory reveals which parts you truly understand.",
        [
            "Read a short section of your material.",
            "Close your notes and explain the idea in plain language.",
            "Check your notes and fill in any gaps you missed.",
            "Repeat with the next section.",
        ],
    ),
    "remembering facts": (
        "Active Recall Flashcards",
        "Retrieving information from memory strengthens it more than rereading.",
        [
            "Turn key facts into question-and-answer cards.",
            "Quiz yourself — don't flip until you've tried to answer.",
            "Sort into 'know' and 'don't know' piles.",
            "Repeat the 'don't know' pile until you clear it.",
        ],
    ),
    "memorizing terms & definitions": _TERM_FLASHCARDS,
    "interpreting graphs & data": _GRAPH_NARRATION,
    "writing essays": (
        "Thesis → Outline → Draft",
        "Planning the argument first gives your writing a clear structure.",
        [
            "Write a one-sentence thesis that states your main claim.",
            "List 2–3 supporting points with evidence for each.",
            "Outline each paragraph: claim → evidence → explanation.",
            "Draft one paragraph at a time from your outline.",
        ],
    ),
    "preparing for a test": (
        "Self-Test & Target Review",
        "A quick self-test reveals what you know so you can focus review where it matters most.",
        [
            "Try a short closed-notes practice quiz.",
            "Mark every question you weren't confident about.",
            "Review the material for those weak topics.",
            "Retake a similar quiz and compare your results.",
        ],
    ),
    "staying focused": (
        "Single-Task Sprint",
        "A single clear task with a defined endpoint makes it easier to begin and stay engaged.",
        [
            "Pick one specific task (e.g., 'solve problems 1–5').",
            "Put away your phone and close unrelated tabs.",
            "Work on that single task until the timer ends.",
            "Take a short break, then decide your next task.",
        ],
    ),
    "getting started": (
        "Two-Minute Launch",
        "Starting with a tiny action lowers the effort it takes to begin.",
        [
            "Open your material and set a 2-minute timer.",
            "Do the smallest useful thing: read one paragraph or answer one question.",
            "When the timer ends, decide whether to continue or take a break.",
            "Most of the time, you'll keep going — starting is the hardest part.",
        ],
    ),
    "solving problems": (
        "Worked Example → Solo Attempt",
        "Studying a solution first, then trying independently, bridges the gap between knowing and doing.",
        [
            "Study a worked solution step by step.",
            "Cover the solution and attempt a similar problem.",
            "Compare your solution to the reference.",
            "Note any steps you missed and retry.",
        ],
    ),

    # ── Level-specific challenges ──────────────────────────────────────────
    "understanding the basics": (
        "Define → Example → Restate",
        "When the basics are new, a plain definition plus one concrete example gives you something solid to hang later ideas on.",
        [
            "Pick one core idea and write its definition from your material.",
            "Find or write one simple, concrete example of it.",
            "Close your notes and restate the idea and the example in your own words.",
            "Check, fix anything off, then do the same with the next core idea.",
        ],
    ),
    "not knowing what to study first": (
        "Topic Map → Core First",
        "Seeing the whole topic on one page shows which ideas the rest depend on, so you know where to begin.",
        [
            "List every topic or heading in your material on one page.",
            "Circle the 3 that the others seem to depend on.",
            "Rank those 3 from most to least basic and pick the first.",
            "Spend the rest of the session on just that one, using a short recall check at the end.",
        ],
    ),
    "filling gaps in what i know": (
        "Blank-Page Brain Dump",
        "Writing everything you remember without help exposes the exact gaps, so review time goes where it is needed.",
        [
            "On a blank page, write everything you remember about one topic for a few minutes.",
            "Open your notes and add what you missed in a different color.",
            "List the three biggest gaps as questions.",
            "Answer those questions from your material, then try the brain dump again.",
        ],
    ),
    "making things stick longer": (
        "Spaced Retrieval Round",
        "Recalling something after a delay, rather than straight after reading it, is what makes it last.",
        [
            "Pick material you studied at least a day ago and write 6 questions about it.",
            "Answer them from memory without looking.",
            "Check your answers and mark any that were wrong or slow.",
            "Plan when you will quiz yourself on the marked ones again.",
        ],
    ),
    "applying ideas to unfamiliar problems": (
        "Vary → Solve → Explain Why",
        "Solving problems that look different from the ones you practiced is what builds flexible, transferable skill.",
        [
            "Take a problem you can already solve and change its context or constraints.",
            "Solve the new version without notes.",
            "Write down what stayed the same and what you had to adapt, and why.",
            "Repeat with a problem from a different topic that needs the same idea.",
        ],
    ),
    "exam speed & accuracy": (
        "Timed Mixed Practice",
        "Practicing under realistic time pressure with mixed topics trains the retrieval and decision speed an exam asks for.",
        [
            "Select a set of mixed questions and set a timer slightly tighter than the exam allows.",
            "Work through them without notes, skipping any that stall you for more than a minute.",
            "Mark each answer as right, wrong or guessed.",
            "For each wrong or guessed one, write the cause: knowledge, misread or rushed.",
        ],
    ),
    "finding my last weak spots": (
        "Error Log Review",
        "Tracking the specific mistakes you keep making shows the few patterns that are costing you the most.",
        [
            "Collect your recent mistakes from practice questions or past work.",
            "Group them by cause (concept, careless, misread, memory).",
            "Pick the biggest group and write one rule or check that would have prevented it.",
            "Do three fresh questions using that rule and see if the mistake disappears.",
        ],
    ),
}

# Time presets (kept for backward compatibility with the old three-button UI).
TIME_MODIFIERS = {
    "short": {"label": "~15 minutes", "minutes": 15, "max_steps": 2},
    "medium": {"label": "~30 minutes", "minutes": 30, "max_steps": 4},
    "long": {"label": "60+ minutes", "minutes": 60, "max_steps": 5},
}

ALTERNATIVE_METHODS = {
    "Spaced Repetition": {
        "description": "Review the same ideas again after a short delay to strengthen long-term recall.",
        "steps": ["Turn the key ideas into questions.", "Try to answer each question from memory.", "Check your notes and mark missed answers.", "Review missed questions tomorrow, then again in a few days."],
    },
    "Active Recall": {
        "description": "Close your notes and retrieve the answer from memory before checking it.",
        "steps": ["Choose one small topic or idea.", "Close your notes and write what you remember.", "Check your notes and correct missing details.", "Repeat with a new question, then revisit missed parts later."],
    },
    "Feynman Technique": {
        "description": "Explain the idea in plain language, then revisit any part you cannot explain.",
        "steps": ["Choose one idea you want to understand.", "Explain it aloud in plain language without notes.", "Check your notes for gaps or jargon you could not explain.", "Rewrite the explanation simply and try again."],
    },
    "Cornell Notes": {
        "description": "Turn your notes into cue questions and use them to quiz yourself later.",
        "steps": ["Divide a page into notes, cue questions, and summary areas.", "Write concise notes while studying.", "Add recall questions in the cue column and summarize the page.", "Cover the notes and answer the cue questions from memory."],
    },
    "Pomodoro": {
        "description": "Focus on one task for a timed sprint, then take a short break.",
        "steps": ["Choose one specific task and define what done means.", "Set a timer for a focused work sprint.", "Work only on that task until the timer ends.", "Take a short break and decide the next task."],
    },
}

METHOD_ALTERNATIVES = {
    "active recall": ["Spaced Repetition", "Feynman Technique"],
    "spaced repetition": ["Active Recall", "Cornell Notes"],
    "feynman technique": ["Active Recall", "Cornell Notes"],
    "cornell notes": ["Active Recall", "Spaced Repetition"],
    "pomodoro": ["Active Recall", "Spaced Repetition"],
}

# ---- Why it works ---------------------------------------------------------
# Every method is tied to the learning principle that makes it work, so the
# explanation can say why it fits *this* subject and challenge.

PRINCIPLES = {
    "retrieval": "pulling answers out of memory (retrieval practice) strengthens recall far more than rereading, and shows you exactly what is still shaky",
    "explain": "explaining an idea in your own words (self-explanation) forces you to connect it to what you already know and exposes gaps you cannot see while reading",
    "worked": "studying a worked example before trying one yourself keeps the mental load low enough to learn the pattern, then practice makes it yours",
    "organize": "organizing information into a map, table or timeline makes the relationships visible, which is what you need to remember and apply it",
    "start": "a tiny, concrete first action removes the effort of starting, and momentum usually carries you into real work",
    "spacing": "revisiting material after a delay (spaced practice) is what turns short-term familiarity into long-term memory",
    "produce": "producing the answer yourself, rather than recognizing it, is what trains the skill you will actually need to use",
}

METHOD_PRINCIPLE = {
    "formula deconstruction": "retrieval",
    "translate → plan → solve": "worked",
    "concept mapping": "organize",
    "narrated solution practice": "explain",
    "term–example flashcards": "retrieval",
    "hypothesis–evidence bridge": "explain",
    "graph narration": "explain",
    "process chain retelling": "retrieval",
    "blank diagram redraw": "retrieval",
    "unit-tracked worked calculations": "worked",
    "mechanism storyboard": "organize",
    "sentence-mined flashcards": "retrieval",
    "shadow → record → compare": "produce",
    "listen → transcribe → check": "produce",
    "pattern notice → produce": "produce",
    "short write → self-correct": "produce",
    "draw → shift → explain": "organize",
    "case → model → prediction": "explain",
    "definition + diagram cards": "retrieval",
    "timeline story building": "organize",
    "because → therefore chain": "organize",
    "theme comparison table": "organize",
    "close reading + annotation": "explain",
    "error hunt + rewrite": "produce",
    "context–use–review cycle": "produce",
    "case brief cards": "retrieval",
    "skim → read → brief": "organize",
    "irac drill": "produce",
    "code → explain → modify": "explain",
    "isolate → reproduce → fix": "worked",
    "pseudocode first": "organize",
    "cheat sheet + drill": "retrieval",
    "feature slice approach": "organize",
    "read → recall → check": "retrieval",
    "active recall flashcards": "retrieval",
    "thesis → outline → draft": "organize",
    "self-test & target review": "retrieval",
    "single-task sprint": "start",
    "two-minute launch": "start",
    "worked example → solo attempt": "worked",
    "define → example → restate": "explain",
    "topic map → core first": "organize",
    "blank-page brain dump": "retrieval",
    "spaced retrieval round": "spacing",
    "vary → solve → explain why": "produce",
    "timed mixed practice": "retrieval",
    "error log review": "organize",
    "active recall check": "retrieval",
    "spaced repetition": "spacing",
    "active recall": "retrieval",
    "feynman technique": "explain",
    "cornell notes": "organize",
    "pomodoro": "start",
}

LEVEL_WHY = {
    "beginner": "As a beginner you get a short warm-up first, so you meet a simple example before you practice.",
    "intermediate": "At an intermediate level the aim is to find and close the gaps rather than re-learn the basics.",
    "advanced": "At an advanced level the plan ends with a harder stretch task, because easy practice no longer teaches you much.",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean_text(value, limit=80):
    """Collapse whitespace, drop control characters and cap the length."""
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].strip()


def normalize_level(level):
    level = str(level or "").strip().lower()
    return level if level in LEVELS else DEFAULT_LEVEL


def resolve_subject(subject, custom_subject=None):
    """Return (family, display name) for a chosen or typed-in subject."""
    key = clean_text(subject, 60).lower()
    custom = clean_text(custom_subject, 60)
    if key in SUBJECT_STRUGGLES and key != "other":
        return key, key.title()
    typed = custom or (key if key and key != "other" else "")
    if not typed:
        return "other", "Other"
    lowered = typed.lower()
    for family, pattern in SUBJECT_KEYWORDS:
        for token in pattern.split("|"):
            # Short tokens must start a word ("law" is not "outlaw"); longer
            # ones may appear inside a word ("microeconomics" contains "econom").
            if re.search((r"\b" if len(token) <= 4 else "") + token, lowered):
                return family, typed
    return "other", typed


def get_struggles(subject, level=DEFAULT_LEVEL, custom_subject=None):
    """Return the list of struggles relevant to a subject and level."""
    family, _ = resolve_subject(subject, custom_subject)
    level = normalize_level(level)
    hidden = LEVEL_HIDDEN_STRUGGLES[level]
    base = [s for s in SUBJECT_STRUGGLES[family] if s.lower() not in hidden]
    return LEVEL_EXTRA_STRUGGLES[level] + base


def resolve_minutes(time_available="medium", minutes=None):
    """Prefer an explicit minute count; otherwise map the preset."""
    if minutes is not None and minutes != "":
        try:
            value = int(round(float(minutes)))
            return max(MIN_MINUTES, min(MAX_MINUTES, value))
        except (TypeError, ValueError, OverflowError):
            pass
    preset = TIME_MODIFIERS.get(str(time_available).strip().lower(), TIME_MODIFIERS["medium"])
    return preset["minutes"]


def format_minutes(minutes):
    if minutes < 60:
        return f"{minutes} min"
    hours, rest = divmod(minutes, 60)
    return f"{hours} h" if rest == 0 else f"{hours} h {rest} min"


def max_steps_for(minutes):
    if minutes < 10:
        return 1
    if minutes < 20:
        return 2
    if minutes < 30:
        return 3
    if minutes < 45:
        return 4
    return 5


def time_note_for(minutes):
    if minutes < 10:
        return "With under 10 minutes, do just one small, concrete task. Even a very short session builds momentum."
    if minutes < 20:
        return "With limited time, focus on the first 2 steps. Even a short session builds momentum."
    if minutes < 30:
        return "You have time for the core of the method. Keep the last few minutes for checking what you remember."
    if minutes < 45:
        return "You have enough time to complete the full method. Take a short break if needed."
    if minutes < 90:
        return "Great — you can complete the full method and repeat it with a second topic or problem set."
    return "This is a long block. Take a 5–10 minute break every 45–50 minutes so the later steps still get your full attention."


def apply_level(steps, level, display, struggle):
    """Add a warm-up for beginners or a stretch task for advanced learners."""
    steps = list(steps)
    if struggle in _LEVEL_EXTRA_KEYS:
        return steps
    material = f"your {display} material" if display != "Other" else "your material"
    if level == "beginner":
        steps.insert(
            0,
            f"Warm up: skim {material} and pick one simple example or definition to start from. Keep your notes open for your first attempt.",
        )
    elif level == "advanced":
        steps.append(
            "Stretch: redo a harder or timed item without any notes, and write down what you would do differently."
        )
    return steps


def deadline_guidance(days_left, exam):
    """Describe how the plan changes for the number of days left."""
    if days_left is None:
        return None
    label = exam or "your deadline"
    if days_left == 0:
        headline = f"{label} is today."
        tips = [
            "Use this session only for quick retrieval of the highest-value topics; skip new material.",
            "Fix the two or three things you are least sure of, then stop and rest.",
            "Do a final quick recall check shortly before you go in.",
        ]
        offsets, mode = [], "today"
    elif days_left == 1:
        headline = f"{label} is tomorrow."
        tips = [
            "Focus on the topics most likely to come up and your known weak spots; do not start anything new.",
            "Test yourself closed-notes rather than rereading.",
            "Finish early and sleep: memory consolidates overnight.",
        ]
        offsets, mode = [], "tomorrow"
    elif days_left <= 3:
        headline = f"{days_left} days until {label}."
        tips = [
            "Prioritize weak topics: spend most of your time where you lose the most marks.",
            "Do one full closed-notes practice run the day before the last day.",
            "Re-test yesterday's missed items at the start of each session.",
        ]
        offsets, mode = [1], "crunch"
    elif days_left <= 7:
        headline = f"{days_left} days until {label}."
        tips = [
            "Aim for one focused session a day, rotating through topics.",
            "Take a practice test about 2 days before and use it to choose what to review.",
            "Revisit each topic at least twice before the deadline.",
        ]
        offsets, mode = [1, 3], "week"
    elif days_left <= 14:
        headline = f"{days_left} days until {label}."
        tips = [
            "Plan 4–5 sessions a week and give each topic a first pass in the first half.",
            "Use the second half for mixed practice and past papers.",
            "Space your reviews: tomorrow, in 3 days, then in 7.",
        ]
        offsets, mode = [1, 3, 7], "fortnight"
    else:
        headline = f"{days_left} days until {label}."
        tips = [
            "You have a long runway: 3–4 short sessions a week beat occasional marathons.",
            "Map the whole syllabus first, then work through it topic by topic.",
            "Add a weekly self-test and review anything that slips.",
        ]
        offsets, mode = [1, 3, 7], "long"
    # Reviews that would land on or after the deadline are not useful.
    offsets = [o for o in offsets if o < days_left]
    return {
        "days_left": days_left,
        "exam": exam,
        "mode": mode,
        "headline": headline,
        "tips": tips,
        "review_offsets": offsets,
    }


def deadline_step(days_left):
    """An extra first step that reflects how close the deadline is, or None."""
    if days_left is None:
        return None
    if days_left <= 1:
        return "Triage: list the 3 topics you are least sure of that are most likely to come up, and work only on those."
    if days_left >= 15:
        return "Map the syllabus: list every topic and mark each green, amber or red; today work on one red topic."
    return None


def why_it_works(method, subject, struggle, level, days_left=None):
    """Short explanation of why a method fits this subject and challenge."""
    principle = PRINCIPLES[METHOD_PRINCIPLE.get(method.lower(), "retrieval")]
    where = f"in {subject}" if subject != "Other" else "in your subject"
    text = (
        f"{method} suits {struggle.lower()} {where} because {principle}."
    )
    if level in LEVEL_WHY:
        text += " " + LEVEL_WHY[level]
    if days_left is not None:
        if days_left <= 1:
            text += " With so little time left, it concentrates your effort on retrieval instead of new input."
        elif days_left <= 7:
            text += " With under a week to go, it keeps each session pointed at what you can still improve."
        else:
            text += " With time on your side, you can repeat it and let spacing do its work."
    return text


def build_alternatives(method, subject, struggle, level, days_left):
    names = METHOD_ALTERNATIVES.get(method.lower(), ["Active Recall", "Spaced Repetition"])
    results = []
    for name in names:
        if method.lower().startswith(name.lower()):
            continue
        info = ALTERNATIVE_METHODS[name]
        results.append({
            "method": name,
            **info,
            "why": why_it_works(name, subject, struggle, None, None),
        })
    return results[:2]


# ---------------------------------------------------------------------------
# Inference engine
# ---------------------------------------------------------------------------

def recommend(subject, struggle, time_available="medium", level=DEFAULT_LEVEL,
              minutes=None, custom_subject=None, exam=None, days_left=None):
    """Return a study recommendation using the expert system rules."""
    family, display = resolve_subject(subject, custom_subject)
    struggle = clean_text(struggle, 80).lower()
    level = normalize_level(level)
    total_minutes = resolve_minutes(time_available, minutes)
    exam = clean_text(exam, 80) or None
    if days_left is not None:
        try:
            days_left = int(days_left)
        except (TypeError, ValueError):
            days_left = None
        else:
            if days_left < 0 or days_left > 3650:
                days_left = None

    # 1. Try subject-specific rule
    result = RULES.get((family, struggle))
    fired_rule = f"{family} + {struggle}" if result else None

    # 2. Fall back to generic struggle rule
    if not result:
        result = GENERIC_RULES.get(struggle)
        fired_rule = f"generic: {struggle}" if result else None

    # 3. Ultimate fallback
    if not result:
        result = (
            "Active Recall Check",
            "A short recall attempt helps you find a clear next step instead of rereading everything.",
            [
                "Pick one small part of the topic.",
                "Try to explain it from memory.",
                "Check your notes and fill in the gaps.",
                "Repeat with the next part.",
            ],
        )
        fired_rule = "default fallback"

    method, reason, base_steps = result
    cap = max_steps_for(total_minutes)

    steps = apply_level(base_steps, level, display, struggle)
    extra = deadline_step(days_left)
    if extra:
        if len(steps) < cap:
            steps.insert(0, extra)
        elif steps and steps[0].startswith("Warm up:"):
            steps[0] = extra
    steps = steps[:cap]

    struggle_title = struggle.title()
    countdown = deadline_guidance(days_left, exam)

    if fired_rule == "default fallback":
        fit = {"label": "Starting point", "basis": "No specific rule matched; using a general recall plan"}
    elif fired_rule.startswith("generic:"):
        fit = {"label": "Good match", "basis": "A general study rule matched this challenge"}
    else:
        fit = {"label": "Strong match", "basis": "A subject-specific rule matched"}

    return {
        "method": method,
        "reason": reason,
        "why": why_it_works(method, display, struggle_title, level, days_left),
        "alternatives": build_alternatives(method, display, struggle_title, level, days_left),
        "steps": steps,
        "minutes": total_minutes,
        "time_note": time_note_for(total_minutes),
        "time_label": format_minutes(total_minutes),
        "level": level,
        "countdown": countdown,
        "rule_used": fired_rule,
        "fit": fit,
        "subject": display,
        "subject_family": family,
        "struggle": struggle_title,
    }


# ---------------------------------------------------------------------------
# Request handling shared by the local server and the Vercel function
# ---------------------------------------------------------------------------

def _optional_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def handle_struggles(data):
    subject = clean_text(data.get("subject", ""), 60)
    custom = clean_text(data.get("custom_subject", ""), 60)
    if not subject and not custom:
        return 400, "Choose a subject"
    return 200, {"struggles": get_struggles(subject, data.get("level"), custom)}


def handle_recommend(data):
    subject = clean_text(data.get("subject", ""), 60)
    custom = clean_text(data.get("custom_subject", ""), 60)
    struggle = clean_text(data.get("struggle", ""), 80)
    if not (subject or custom) or not struggle:
        return 400, "Choose a subject and study challenge"
    return 200, recommend(
        subject,
        struggle,
        str(data.get("time", "medium")),
        level=data.get("level"),
        minutes=data.get("minutes"),
        custom_subject=custom,
        exam=data.get("exam"),
        days_left=_optional_int(data.get("days_left")),
    )


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
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        super().end_headers()

    def do_POST(self):
        if self.path == "/struggles":
            handler = handle_struggles
        elif self.path == "/recommend":
            handler = handle_recommend
        else:
            self.send_error(404)
            return
        data = self._read_json()
        if data is None:
            self.send_error(400, "Please send valid JSON")
            return
        status, payload = handler(data)
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
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), AppHandler)
    print("Study Buddy is running at http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
