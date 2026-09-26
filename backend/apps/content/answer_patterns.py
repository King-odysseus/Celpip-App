"""Answer patterns: a memorable structure for every Speaking and Writing task.

Each pattern is a mnemonic whose letters are the steps of a strong response,
with the phrases a learner can use for each step. The same data drives the
learner-facing pattern cards and drills and the grader's step-by-step check,
so what the app teaches is exactly what it looks for. Original teaching
material; not official CELPIP guidance.
"""
# ruff: noqa: E501

from __future__ import annotations


def _step(key: str, label: str, what: str, phrases: list[str]) -> dict:
    return {"key": key, "label": label, "what": what, "phrases": phrases}


ANSWER_PATTERNS: dict[str, dict] = {
    "speaking_advice": {
        "mnemonic": "CARE",
        "summary": "Show you care about their problem, then give three tips that each come with a reason.",
        "plan": "90 sec: Connect 10s · Advise 25s · Add 45s · Reassure 10s",
        "steps": [
            _step("connect", "Connect", "Speak to the person by name and show you understand their situation.", [
                "Hi Sam, I heard you're having a hard time with…",
                "I completely understand how stressful that must be.",
                "I've been in a similar situation, so here's what I'd do.",
            ]),
            _step("advise", "Advise", "Give your first and strongest tip, with a reason or example.", [
                "The first thing I'd suggest is…, because…",
                "If I were you, I would… That way, you could…",
                "For example, when my friend did this, she…",
            ]),
            _step("add", "Add", "Add two more tips, each with its own reason.", [
                "Another thing you could try is…, since…",
                "On top of that, it might help to…",
                "Finally, don't forget to…, which will…",
            ]),
            _step("reassure", "Reassure", "Finish with encouragement.", [
                "I'm sure you'll handle it well.",
                "Give these a try and let me know how it goes.",
                "Don't worry too much — things will work out.",
            ]),
        ],
    },
    "speaking_experience": {
        "mnemonic": "STORY",
        "summary": "Tell one real event from start to finish, then say how it felt and why it mattered.",
        "plan": "60 sec: Scene 10s · Turn of events 25s · Outcome 10s · Reaction + You learned 15s",
        "steps": [
            _step("scene", "Scene", "Set the scene: when, where, and who was there.", [
                "A couple of years ago, I was…",
                "It happened last winter, when my family and I…",
                "I remember one time at my old job when…",
            ]),
            _step("turn", "Turn of events", "Tell what happened in order, in the past tense.", [
                "At first…, but then…",
                "Suddenly, …",
                "After that, we decided to…",
            ]),
            _step("outcome", "Outcome", "Say how it ended.", [
                "In the end, …",
                "Luckily, everything turned out…",
                "As a result, …",
            ]),
            _step("reaction", "Reaction", "Say how you felt.", [
                "I felt really… because…",
                "I was so relieved when…",
                "Honestly, I was nervous at first, but…",
            ]),
            _step("you_learned", "You learned", "Explain why the experience mattered to you.", [
                "That experience taught me that…",
                "Since then, I always…",
                "It's something I'll never forget because…",
            ]),
        ],
    },
    "speaking_scene": {
        "mnemonic": "ZOOM",
        "summary": "Start wide, then move through the picture in order, from people's actions down to small details.",
        "plan": "60 sec: Zoom out 10s · Organize 15s · Observe actions 25s · Magnify 10s",
        "steps": [
            _step("zoom_out", "Zoom out", "Say where the scene is and what the overall mood is.", [
                "This picture shows a busy… on what looks like a sunny afternoon.",
                "It seems to be a… and everyone looks…",
                "Overall, the atmosphere is…",
            ]),
            _step("organize", "Organize", "Take the listener through the picture by location.", [
                "On the left side, …",
                "In the middle of the picture, …",
                "In the background / foreground, …",
            ]),
            _step("observe", "Observe actions", "Describe what people are doing and how they relate to each other.", [
                "A man in a blue jacket is… while…",
                "Next to her, two children are…",
                "It looks like they are… together.",
            ]),
            _step("magnify", "Magnify details", "Add a few precise details: colours, expressions, objects.", [
                "She's holding a small red…",
                "He looks a little… because…",
                "I can also see a… on the…",
            ]),
        ],
    },
    "speaking_predictions": {
        "mnemonic": "PEP × 3",
        "summary": "For three different people or things: point to them, give the clue you see, then predict.",
        "plan": "60 sec: three PEPs of about 17s each, then a 5s wrap-up",
        "steps": [
            _step("pep_1", "PEP 1", "Person → Evidence you can see → Prediction.", [
                "Looking at the man by the door, he's checking his watch, so he'll probably…",
                "Since the sky is getting dark, it's likely that…",
                "Judging by…, I think…",
            ]),
            _step("pep_2", "PEP 2", "A different person or thing, with its own clue and prediction.", [
                "As for the woman on the right, because…, she might…",
                "The child near the table looks…, so there's a good chance he'll…",
                "It seems as though… is about to…",
            ]),
            _step("pep_3", "PEP 3", "One more person or thing, using different future words.", [
                "I'd expect the… to… soon, because…",
                "Chances are that…",
                "Before long, …",
            ]),
            _step("wrap_up", "Wrap-up", "Sum up what will happen to the scene as a whole.", [
                "All in all, I think the next few minutes will be…",
                "Overall, it looks like everyone is going to…",
                "So, in a little while, the scene will probably…",
            ]),
        ],
    },
    "speaking_compare_persuade": {
        "mnemonic": "4 C's",
        "summary": "Choose, give their option credit, show why yours is better, and close warmly.",
        "plan": "60 sec: Choose 5s · Credit 10s · Contrast 35s · Close 10s",
        "steps": [
            _step("choose", "Choose", "Say clearly which option you think is better.", [
                "I really think we should go with…",
                "In my opinion, … is the better choice.",
                "I'd strongly recommend…",
            ]),
            _step("credit", "Credit", "Admit one real advantage of their option.", [
                "I can see why you like… — it does have…",
                "You're right that… is…",
                "That's a fair point about…",
            ]),
            _step("contrast", "Contrast", "Give two specific reasons, from the details, why your option is better.", [
                "However, … is much more… because…",
                "Also, unlike…, … offers…",
                "Another big advantage is that…",
            ]),
            _step("close", "Close", "End with a friendly push to agree.", [
                "So, what do you think? Shall we go with…?",
                "I really think you'll be happier with…",
                "Why don't we give… a try?",
            ]),
        ],
    },
    "speaking_difficult_situation": {
        "mnemonic": "DEAL",
        "summary": "Give the decision early, show you understand, back it up, and offer a way forward.",
        "plan": "60 sec: Decision 10s · Empathize 10s · Add reasons 30s · Lead forward 10s",
        "steps": [
            _step("decision", "Decision", "Tell the person your choice early and kindly.", [
                "I've thought about it carefully, and I've decided to…",
                "I wanted to let you know that I'm going to…",
                "This isn't easy to say, but…",
            ]),
            _step("empathize", "Empathize", "Show you understand how they feel.", [
                "I know this might be disappointing for you.",
                "I understand that you were hoping…",
                "I really appreciate…, so this was a hard decision.",
            ]),
            _step("add_reasons", "Add reasons", "Give two or three convincing reasons.", [
                "The main reason is that…",
                "Also, if I…, then…",
                "On top of that, …",
            ]),
            _step("lead_forward", "Lead forward", "Offer a solution or next step.", [
                "How about we… instead?",
                "To make it up to you, I could…",
                "Let's… so that…",
            ]),
        ],
    },
    "speaking_opinions": {
        "mnemonic": "PROVE",
        "summary": "Take a side straight away, prove it with two reasons, answer the other side, and finish strong.",
        "plan": "90 sec: Position 10s · Reason 25s · Other reason 25s · View of the other side 15s · End 10s",
        "steps": [
            _step("position", "Position", "Answer the question with a clear yes or no.", [
                "I strongly believe that…",
                "In my opinion, yes, …",
                "I don't think… should…, and here's why.",
            ]),
            _step("reason", "Reason", "Give your first reason with a specific example.", [
                "First of all, …. For example, …",
                "The main reason is that…",
                "In my own experience, …",
            ]),
            _step("other_reason", "Other reason", "Give a second reason with an example or result.", [
                "Another reason is that…",
                "On top of that, …, which means…",
                "This would also…",
            ]),
            _step("view_other_side", "View of the other side", "Mention what someone might say against you, then answer it.", [
                "Some people might argue that…, but…",
                "It's true that…; however, …",
                "Even though…, I still think…",
            ]),
            _step("end", "End", "Restate your position in one sentence.", [
                "So, overall, I firmly believe…",
                "That's why I think…",
                "For these reasons, …",
            ]),
        ],
    },
    "speaking_unusual": {
        "mnemonic": "CALL",
        "summary": "It's a phone call: say why you're calling, then describe it so they could draw it.",
        "plan": "60 sec: Call opener 10s · Appearance 20s · Location of parts 20s · Likeness + goodbye 10s",
        "steps": [
            _step("call_opener", "Call opener", "Greet them, say why you're calling, and name what's unusual.", [
                "Hi Alex, I'm calling because I just saw the strangest…",
                "You won't believe what I found at the store today.",
                "I have to tell you about this unusual…",
            ]),
            _step("appearance", "Appearance", "Describe its overall shape, size, material and colour.", [
                "It's about the size of a…, and it's made of…",
                "It's shaped like a… and it's bright…",
                "The whole thing is covered in…",
            ]),
            _step("location_of_parts", "Location of parts", "Say where each part is and what it does.", [
                "On the top, there's a…",
                "Attached to the side, there's…",
                "At the bottom, it has…, which lets you…",
            ]),
            _step("likeness", "Likeness", "Compare it to familiar things, then close the call.", [
                "It looks a bit like a… mixed with a…",
                "Imagine a… but with…",
                "Anyway, I think you'd love it — should I get one?",
            ]),
        ],
    },
    "writing_email": {
        "mnemonic": "DEAR",
        "summary": "Every email starts with 'Dear' — and so does the plan: greet, explain, answer every point, request.",
        "plan": "150–200 words: Direct greeting + Explain ~30 · Answer each point ~40 each · Request + sign-off ~25",
        "steps": [
            _step("direct_greeting", "Direct greeting", "Open with the right greeting for the reader.", [
                "Dear Mr. Patel, / Dear Ms. Chen, (formal)",
                "Hi Jordan, (friendly)",
                "To whom it may concern, (unknown reader)",
            ]),
            _step("explain", "Explain your purpose", "Say in one or two sentences why you're writing.", [
                "I am writing to express my concern about…",
                "I'm writing to let you know that…",
                "I am contacting you regarding…",
            ]),
            _step("answer_every_point", "Answer every point", "Give each requested point its own short paragraph with details.", [
                "Firstly, … / To begin with, …",
                "In addition, I would like to mention that…",
                "As for…, I would suggest…",
            ]),
            _step("request", "Request and sign off", "Close with a clear request or next step and a polite sign-off.", [
                "I would appreciate it if you could… by…",
                "Please let me know if…",
                "Thank you for your time. Sincerely, / Best regards,",
            ]),
        ],
    },
    "writing_survey": {
        "mnemonic": "PROVE",
        "summary": "The same PROVE pattern as Speaking Task 7: choose an option, prove it, answer the other option, and finish.",
        "plan": "150–200 words: Position ~20 · Reason ~50 · Other reason ~50 · View of the other option ~30 · End ~20",
        "steps": [
            _step("position", "Position", "Name your chosen option in the first sentence.", [
                "I believe Option A is the better choice because…",
                "In my view, the city should choose…",
                "I strongly prefer… for two main reasons.",
            ]),
            _step("reason", "Reason", "Develop your first reason with a detail or example.", [
                "First and foremost, …. For instance, …",
                "The most important reason is that…",
                "To illustrate, …",
            ]),
            _step("other_reason", "Other reason", "Develop a second reason and link it to the survey question.", [
                "Furthermore, …, which would…",
                "Another significant benefit is…",
                "This is especially important because…",
            ]),
            _step("view_other_side", "View of the other option", "Briefly admit a strength of the other option, then explain why yours is still better.", [
                "Admittedly, Option B would…; however, …",
                "While… has its merits, …",
                "Some may prefer…, but…",
            ]),
            _step("end", "End", "Restate your choice in one closing sentence.", [
                "For these reasons, I strongly support…",
                "Overall, … is clearly the better option.",
                "In conclusion, …",
            ]),
        ],
    },
}


def answer_pattern_for(task_type_code: str | None) -> dict | None:
    """Return the answer pattern for a task type, or ``None`` if it has none."""
    return ANSWER_PATTERNS.get(task_type_code or "")


def grading_pattern(task_type_code: str | None) -> dict | None:
    """The part of a pattern the grader needs: its name and what each step does."""
    pattern = answer_pattern_for(task_type_code)
    if pattern is None:
        return None
    return {
        "mnemonic": pattern["mnemonic"],
        "steps": [{"label": step["label"], "what": step["what"]} for step in pattern["steps"]],
    }
