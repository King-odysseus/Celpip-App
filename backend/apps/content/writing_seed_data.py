"""Original Writing prompts drafted for independent editorial review.

CELPIP-General Writing has two tasks: Writing an Email and Responding to Survey
Questions. Every prompt below is an original Canadian-context scenario written
for this repository. No official CELPIP prompt, sample response, or paid bank
was used. Structured prompt data lives in each set's ``stimulus`` and is frozen
into a session snapshot at start time.
"""
# ruff: noqa: E501

# Practice defaults from the current public format facts. These are learner-facing
# suggestions, not official per-task limits: the platform never claims a short
# practice set reproduces the official timing or scoring scale.
EMAIL_DURATION_SECONDS = 27 * 60
SURVEY_DURATION_SECONDS = 26 * 60
TARGET_WORDS = {"min": 150, "max": 200}


WRITING_TASK_TYPES = [
    {
        "code": "writing_email",
        "skill": "writing",
        "title": "Writing an Email",
        "part_number": 1,
        "description": "Read a short situation and write a complete email that responds appropriately to the reader and purpose.",
        "strategy": [
            "Identify the reader and choose a matching level of formality.",
            "Address every requested point so the task is fully covered.",
            "Open with your purpose, organize the body in short paragraphs, and close politely.",
        ],
        "common_mistakes": [
            "Leaving one requested point unanswered.",
            "Mismatching tone, such as writing casually to a landlord or manager.",
            "Writing far below or above the suggested length instead of developing ideas.",
        ],
    },
    {
        "code": "writing_survey",
        "skill": "writing",
        "title": "Responding to Survey Questions",
        "part_number": 2,
        "description": "Read a survey situation, choose one of the offered options, and write a clear response that explains and supports your choice.",
        "strategy": [
            "State your chosen option clearly in the first sentence.",
            "Give two or three specific reasons and develop each one.",
            "Acknowledge the other option briefly to show balanced thinking, then restate your choice.",
        ],
        "common_mistakes": [
            "Describing both options without ever committing to one.",
            "Listing reasons without explaining or supporting them.",
            "Forgetting to connect the reasons back to the survey question.",
        ],
    },
]


WRITING_SETS = [
    # ---- Writing an Email ---------------------------------------------------
    {
        "slug": "email-noisy-renovation",
        "task_type": "writing_email",
        "title": "Email About Ongoing Renovation Noise",
        "topic": "Housing and tenancy",
        "difficulty": 1,
        "estimated_level": 6,
        "instructions": "Read the situation and write an email of about 150 to 200 words.",
        "stimulus": {
            "type": "writing_prompt",
            "task_kind": "email",
            "scenario": "Renovations in the apartment above yours have been running early in the morning and late into the evening for the past two weeks. It is disturbing your sleep and your ability to work from home. You have decided to email the building manager, Ms. Alvarez.",
            "audience": "Your building manager (semi-formal)",
            "requested_points": [
                "Explain the problem and when the noise happens.",
                "Describe how it is affecting you.",
                "Suggest what you would like the manager to do.",
            ],
            "target_words": TARGET_WORDS,
            "suggested_duration_seconds": EMAIL_DURATION_SECONDS,
            "guidance": [
                "Keep the tone polite and firm; you want cooperation, not conflict.",
                "State clear, reasonable quiet hours in your suggestion.",
            ],
        },
        "learning_notes": "Notice how a firm but respectful tone increases the chance of a helpful reply. Each requested point should be visible in your email; a marker often checks that all three are answered before assessing style.",
    },
    {
        "slug": "email-volunteer-schedule-change",
        "task_type": "writing_email",
        "title": "Email Requesting a Volunteer Schedule Change",
        "topic": "Community volunteering",
        "difficulty": 2,
        "estimated_level": 8,
        "instructions": "Read the situation and write an email of about 150 to 200 words.",
        "stimulus": {
            "type": "writing_prompt",
            "task_kind": "email",
            "scenario": "You volunteer every Saturday morning at a community food bank. Starting next month, a new part-time job means you can no longer work Saturday mornings, but you still want to volunteer. Write to the volunteer coordinator, Mr. Okoye.",
            "audience": "Your volunteer coordinator (semi-formal)",
            "requested_points": [
                "Explain why you can no longer keep your current shift.",
                "Say how much you value volunteering and want to continue.",
                "Propose an alternative time and ask how to arrange it.",
            ],
            "target_words": TARGET_WORDS,
            "suggested_duration_seconds": EMAIL_DURATION_SECONDS,
            "guidance": [
                "Lead with appreciation before explaining the change.",
                "Offer a concrete alternative rather than asking the reader to solve the problem for you.",
            ],
        },
        "learning_notes": "Requests are easier to grant when the writer sounds committed and offers a solution. Watch that your proposed alternative is specific (a day and a time), not just 'sometime later'.",
    },
    {
        "slug": "email-online-order-problem",
        "task_type": "writing_email",
        "title": "Email About a Damaged Online Order",
        "topic": "Consumer situations",
        "difficulty": 2,
        "estimated_level": 7,
        "instructions": "Read the situation and write an email of about 150 to 200 words.",
        "stimulus": {
            "type": "writing_prompt",
            "task_kind": "email",
            "scenario": "Two weeks ago you ordered a winter jacket from a Canadian online store. It arrived yesterday, but the zipper is broken and the colour is not what you ordered. Write to the store's customer service team.",
            "audience": "A company's customer-service team (formal)",
            "requested_points": [
                "Give the order details and describe both problems.",
                "Explain what solution you expect (replacement or refund).",
                "State a reasonable deadline and how you can be contacted.",
            ],
            "target_words": TARGET_WORDS,
            "suggested_duration_seconds": EMAIL_DURATION_SECONDS,
            "guidance": [
                "Include concrete details such as an order number to sound credible.",
                "Be assertive about the outcome you want while remaining courteous.",
            ],
        },
        "learning_notes": "Complaint emails work best when they are specific and calm. A marker looks for a clear statement of the problem, the requested remedy, and a professional closing rather than emotional language.",
    },
    # ---- Responding to Survey Questions ------------------------------------
    {
        "slug": "survey-library-weekend-hours",
        "task_type": "writing_survey",
        "title": "Survey: Extending Public Library Hours",
        "topic": "Community services",
        "difficulty": 1,
        "estimated_level": 6,
        "instructions": "Read the survey and write a response of about 150 to 200 words. Choose one option and explain your choice.",
        "stimulus": {
            "type": "writing_prompt",
            "task_kind": "survey",
            "scenario": "Your city library has extra funding and is surveying residents about how to use it. The library can either extend its weekend opening hours or expand its collection of books and digital resources. It cannot do both this year.",
            "survey_question": "Which option should the library choose?",
            "options": [
                {"key": "extended_hours", "label": "Extend weekend opening hours"},
                {"key": "larger_collection", "label": "Expand the book and digital collection"},
            ],
            "requested_points": [
                "State which option you prefer.",
                "Give specific reasons for your choice.",
                "Explain why your choice is better than the other option.",
            ],
            "target_words": TARGET_WORDS,
            "suggested_duration_seconds": SURVEY_DURATION_SECONDS,
            "guidance": [
                "Commit clearly to one option in your first sentence.",
                "Use everyday examples of how residents would benefit.",
            ],
        },
        "learning_notes": "A strong survey response takes a clear position and stays with it. Compare briefly with the other option to show judgement, but do not spend equal space defending both.",
    },
    {
        "slug": "survey-remote-work-policy",
        "task_type": "writing_survey",
        "title": "Survey: Remote or In-Office Work",
        "topic": "Workplace policy",
        "difficulty": 2,
        "estimated_level": 8,
        "instructions": "Read the survey and write a response of about 150 to 200 words. Choose one option and explain your choice.",
        "stimulus": {
            "type": "writing_prompt",
            "task_kind": "survey",
            "scenario": "Your employer is reviewing its work policy and has asked staff for their views. The company is deciding between letting employees work mainly from home or requiring most staff to return to the office for the majority of the week.",
            "survey_question": "Which policy should the company adopt?",
            "options": [
                {"key": "mostly_remote", "label": "Allow employees to work mainly from home"},
                {"key": "mostly_office", "label": "Require staff to work mainly in the office"},
            ],
            "requested_points": [
                "State which policy you support.",
                "Give reasons based on productivity, cost, or wellbeing.",
                "Respond to a likely concern about your choice.",
            ],
            "target_words": TARGET_WORDS,
            "suggested_duration_seconds": SURVEY_DURATION_SECONDS,
            "guidance": [
                "Use reasons an employer would care about, not only personal preference.",
                "Naming and answering one objection strengthens your argument.",
            ],
        },
        "learning_notes": "Workplace-topic surveys reward reasons that consider more than one perspective. Addressing an objection ('some worry that...') shows the range of thinking that raises Content and Coherence.",
    },
    {
        "slug": "survey-city-transit-vs-bike-lanes",
        "task_type": "writing_survey",
        "title": "Survey: Transit Funding or Bike Lanes",
        "topic": "Urban planning",
        "difficulty": 3,
        "estimated_level": 9,
        "instructions": "Read the survey and write a response of about 150 to 200 words. Choose one option and explain your choice.",
        "stimulus": {
            "type": "writing_prompt",
            "task_kind": "survey",
            "scenario": "Your city has a limited transportation budget for the coming year and is consulting residents. The money can be spent either on improving bus and train service or on building a connected network of protected bike lanes.",
            "survey_question": "How should the city spend the transportation budget?",
            "options": [
                {"key": "public_transit", "label": "Improve bus and train service"},
                {"key": "bike_lanes", "label": "Build protected bike lanes"},
            ],
            "requested_points": [
                "State which option you would choose.",
                "Support your choice with reasons about access, cost, or the environment.",
                "Explain the trade-off you are willing to accept.",
            ],
            "target_words": TARGET_WORDS,
            "suggested_duration_seconds": SURVEY_DURATION_SECONDS,
            "guidance": [
                "Think about who benefits most from each option.",
                "Acknowledging the trade-off makes your position more convincing, not weaker.",
            ],
        },
        "learning_notes": "Higher-level survey responses weigh costs and benefits explicitly. Naming the trade-off you accept demonstrates the coherent reasoning assessors look for at stronger levels.",
    },
]
