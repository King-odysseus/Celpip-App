"""Small original sets that close the full-length mock's exact-count gaps.

The full-length mock (Phase 11) assembles each Listening/Reading section to the
current official question count by combining several distinct reviewed sets.
Every existing Listening/Reading set has exactly 4 embedded questions, which
is enough to reach some official counts exactly (e.g. 8 = 4+4) but not others:
no combination of 4-question sets sums to 5, 6, 9, 10, or 11. These sets fill
exactly that gap — one or two small original sets per affected task type,
sized so ``mocks.services`` can hit the official count exactly by adding one
filler to a natural run of 4-question sets:

- Listening Daily Conversation (target 5) = 4 + this 1
- Listening Information (target 6) = 4 + this 2
- Listening News (target 5) = 4 + this 1
- Listening Viewpoints (target 6) = 4 + this 2
- Reading Correspondence (target 11) = 4 + 4 + this 3
- Reading Information (target 9) = 4 + 4 + this 1
- Reading Viewpoints (target 10) = 4 + 4 + this 2

All scenarios, transcripts, questions, and explanations are original to this
repository. The Listening entries follow the ``_set(...)`` shape consumed by
``seed_listening_content``; the Reading entries follow the plain-dict shape
consumed by ``seed_reading_content``.
"""


def c(text, correct, explanation):
    return {"text": text, "is_correct": correct, "explanation": explanation}


def _set(slug, task_type, title, topic, difficulty, level, intro, transcript, questions):
    # Filler prompts are original text-only additions used to reach the live
    # question counts. Reuse an existing bundled WAV for their media asset so
    # a fresh deployment does not require a separate audio-generation job.
    source_audio = {
        "listening_daily_conversation": "pottery-class-change",
        "listening_information": "river-trail-volunteer-orientation",
        "listening_news": "mobile-health-clinic-news",
        "listening_viewpoints": "vacant-lots-community-talk",
    }[task_type]
    return {
        "slug": slug,
        "task_type": task_type,
        "title": title,
        "topic": topic,
        "difficulty": difficulty,
        "estimated_level": level,
        "instructions": "Listen once and follow the conversation for meaning and purpose.",
        "intro": intro,
        "transcript": transcript,
        "source_slug": source_audio,
        "questions": questions,
    }


LISTENING_FILLER_SETS = [
    _set(
        "lost-umbrella-front-desk",
        "listening_daily_conversation",
        "Asking About a Lost Umbrella",
        "Everyday errands",
        1,
        5,
        "A resident asks the front desk about an umbrella left in the lobby.",
        "Priya: Hi, I think I left a green umbrella in the lobby yesterday evening. Has anyone turned one in?\nSam: Let me check the lost-and-found bin. Yes, we have a green umbrella here with a wooden handle.\nPriya: That's the one. Can I pick it up now, or do I need to show anything?",
        [
            {"stem": "Why does Priya visit the front desk?", "skill_focus": "gist", "evidence": "I think I left a green umbrella in the lobby yesterday evening.", "explanation": "She is asking about an item she believes she lost.", "choices": [c("To ask about a lost umbrella", True, "She describes losing an umbrella in the lobby."), c("To report a broken door", False, "No door problem is mentioned."), c("To complain about noise", False, "No noise complaint is made."), c("To buy a new umbrella", False, "She is asking about her own umbrella, not buying one.")]},
        ],
    ),
    _set(
        "returning-a-library-tablet",
        "listening_daily_conversation",
        "Returning a Library Tablet",
        "Everyday errands",
        1,
        5,
        "A visitor asks a librarian how to return a borrowed tablet.",
        "Owen: I borrowed one of your tablets last week. Where should I return it?\nClerk: You can drop it at this desk. Just make sure the charging cable is included.\nOwen: It is. Will you check that everything still works before I leave?",
        [
            {"stem": "What does Owen want to do?", "skill_focus": "gist", "evidence": "I borrowed one of your tablets last week. Where should I return it?", "explanation": "He is returning a borrowed tablet.", "choices": [c("Return a borrowed tablet", True, "He states he borrowed a tablet and asks where to return it."), c("Borrow a new laptop", False, "He already has the tablet and wants to return it."), c("Report a missing charger", False, "He confirms the cable is included, not missing."), c("Ask for a library card", False, "No library card is discussed.")]},
        ],
    ),
    _set(
        "power-outage-building-notice",
        "listening_information",
        "A Planned Power Outage Notice",
        "Building maintenance",
        1,
        5,
        "A building manager explains an upcoming scheduled power outage to a tenant.",
        "Manager: I wanted to let you know the building will have a planned power outage on Thursday from nine to eleven in the morning for electrical panel maintenance.\nTenant: Will the elevators still work during that time?\nManager: No, both elevators will be off, so please use the stairs if you need to leave during that window.\nTenant: Thanks for the warning. I will charge my devices the night before.",
        [
            {"stem": "Why is the power being turned off?", "skill_focus": "gist", "evidence": "for electrical panel maintenance", "explanation": "The outage is planned to allow maintenance work on the electrical panel.", "choices": [c("For electrical panel maintenance", True, "This is the stated reason."), c("Because of a storm", False, "No storm is mentioned."), c("To save energy costs", False, "Cost saving is not the stated reason."), c("Because of a fire inspection", False, "No inspection is mentioned.")]},
            {"stem": "What should the tenant do if leaving during the outage?", "skill_focus": "detail", "evidence": "please use the stairs if you need to leave during that window", "explanation": "The elevators will be off, so stairs are needed.", "choices": [c("Use the stairs", True, "This is the manager's instruction."), c("Wait for the elevator to restart", False, "The elevator will stay off the whole time."), c("Call the front desk for help", False, "No such instruction is given."), c("Use the parking garage exit", False, "No garage exit is mentioned.")]},
        ],
    ),
    _set(
        "gym-schedule-change",
        "listening_news",
        "A Gym Schedule Change Announcement",
        "Community facilities",
        1,
        5,
        "A short announcement informs members about a change to the gym's weekend hours.",
        "Announcer: Attention members, starting this weekend the gym will open one hour later, at nine instead of eight, to allow time for new equipment installation. Regular weekday hours are not affected, and the change will remain in place for the next three weekends only.",
        [
            {"stem": "What is changing about the gym's weekend hours?", "skill_focus": "gist", "evidence": "the gym will open one hour later, at nine instead of eight", "explanation": "The opening time is being pushed back by one hour on weekends.", "choices": [c("It will open one hour later", True, "This matches the announcement."), c("It will close one hour earlier", False, "Closing time is not mentioned."), c("It will be closed all weekend", False, "The gym is still open, just later."), c("It will open one hour earlier", False, "The change is later, not earlier.")]},
        ],
    ),
    _set(
        "should-parks-charge-entry-fees",
        "listening_viewpoints",
        "Should City Parks Charge Entry Fees?",
        "Civic issues",
        1,
        5,
        "Two neighbours briefly disagree about whether city parks should charge an entry fee.",
        "Tomas: I think a small entry fee for the big parks would help pay for maintenance and new benches.\nElena: I disagree. Parks should stay free so every family can use them, no matter their income.\nTomas: A one-dollar fee wouldn't stop most people, and the park really needs repairs.\nElena: Even a small fee can be a real barrier for larger families visiting often.",
        [
            {"stem": "What do Tomas and Elena disagree about?", "skill_focus": "gist", "evidence": "a small entry fee ... Parks should stay free", "explanation": "They disagree about whether parks should charge an entry fee.", "choices": [c("Whether parks should charge an entry fee", True, "This is the direct topic of disagreement."), c("Whether the park needs new benches", False, "Both seem to accept repairs are needed."), c("Whether the park should close early", False, "Closing time is not discussed."), c("Whether to build a new park", False, "A new park is not discussed.")]},
            {"stem": "Why does Elena oppose the fee?", "skill_focus": "detail", "evidence": "a real barrier for larger families visiting often", "explanation": "She is concerned the fee would be difficult for larger families.", "choices": [c("It could be a barrier for larger families", True, "This is her stated concern."), c("She thinks the park does not need repairs", False, "She does not comment on repairs."), c("She wants the park closed instead", False, "She wants it to stay open and free."), c("She prefers a different park design", False, "Design is not discussed.")]},
        ],
    ),
]

READING_FILLER_SETS = [
    {
        "slug": "gym-locker-key-deposit-notice",
        "task_type": "reading_correspondence",
        "title": "Gym Locker Key Deposit Notice",
        "topic": "Community recreation",
        "difficulty": 1,
        "estimated_level": 5,
        "instructions": "Read the email and answer the questions.",
        "stimulus": {
            "type": "email",
            "from": "Riverside Fitness Centre",
            "to": "Members",
            "subject": "New locker key deposit starting next month",
            "body": "Dear members,\n\nStarting next month, locker keys will require a five-dollar refundable deposit. Pay the deposit at the front desk when you collect a key, and return the key at the end of your visit to get your deposit back the same day.\n\nKeys not returned by closing time will be treated as lost, and the deposit will not be refunded. A replacement key costs fifteen dollars.\n\nThank you for helping us reduce lost keys.\n\nRiverside Fitness Centre",
        },
        "learning_notes": "Separate the normal same-day refund process from the lost-key exception.",
        "questions": [
            {
                "stem": "What is the main purpose of the email?",
                "skill_focus": "gist",
                "evidence": "locker keys will require a five-dollar refundable deposit",
                "explanation": "The email introduces a new refundable deposit for locker keys.",
                "choices": [
                    c("To announce a new locker key deposit", True, "This is the central change described."),
                    c("To close the gym for renovations", False, "No closure is mentioned."),
                    c("To raise membership fees", False, "Only the key deposit is mentioned."),
                    c("To remove lockers from the gym", False, "Lockers are staying, just requiring a deposit."),
                ],
            },
            {
                "stem": "When is the deposit refunded?",
                "skill_focus": "detail",
                "evidence": "return the key at the end of your visit to get your deposit back the same day",
                "explanation": "Returning the key the same day results in a same-day refund.",
                "choices": [
                    c("The same day, when the key is returned", True, "This matches the stated process."),
                    c("One week after the visit", False, "No week-long delay is mentioned."),
                    c("Only at the end of the month", False, "No monthly refund cycle is mentioned."),
                    c("Only if paid by credit card", False, "Payment method is not discussed.")]
            },
            {
                "stem": "What happens if a key is not returned by closing time?",
                "skill_focus": "inference",
                "evidence": "Keys not returned by closing time will be treated as lost, and the deposit will not be refunded.",
                "explanation": "A late key counts as lost and forfeits the deposit.",
                "choices": [
                    c("It is treated as lost and the deposit is kept", True, "This is stated directly."),
                    c("It can be returned the next day for a refund", False, "The notice does not offer a next-day option."),
                    c("The member is banned from the gym", False, "No ban is mentioned."),
                    c("A new key is issued for free", False, "A replacement costs fifteen dollars.")]
            },
        ],
    },
    {
        "slug": "recycling-bin-collection-note",
        "task_type": "reading_information",
        "title": "Recycling Bin Collection Note",
        "topic": "Municipal services",
        "difficulty": 1,
        "estimated_level": 4,
        "instructions": "Read the information and answer the question.",
        "stimulus": {
            "type": "article",
            "title": "Recycling collection moves to Wednesdays",
            "sections": [
                {
                    "heading": "New collection day",
                    "body": "Starting next month, recycling bins will be collected on Wednesdays instead of Mondays. Place bins at the curb by seven in the morning on collection day.",
                },
            ],
        },
        "learning_notes": "Locate the single changed detail: the new collection day.",
        "questions": [
            {
                "stem": "What is changing about recycling collection?",
                "skill_focus": "detail",
                "evidence": "recycling bins will be collected on Wednesdays instead of Mondays",
                "explanation": "The collection day is moving from Monday to Wednesday.",
                "choices": [
                    c("The collection day is moving to Wednesday", True, "This matches the notice exactly."),
                    c("Bins must be a new colour", False, "No colour change is mentioned."),
                    c("Collection is being cancelled", False, "Collection continues, only the day changes."),
                    c("The collection time is moving to noon", False, "The notice gives a morning time, not noon."),
                ],
            },
        ],
    },
    {
        "slug": "should-street-parking-be-free",
        "task_type": "reading_viewpoints",
        "title": "Should Downtown Street Parking Be Free?",
        "topic": "Civic spending",
        "difficulty": 1,
        "estimated_level": 5,
        "instructions": "Compare the viewpoints and answer the questions.",
        "stimulus": {
            "type": "viewpoints",
            "title": "Should downtown street parking be free on weekends?",
            "background": "The city council is deciding whether to remove weekend parking meters downtown.",
            "speakers": [
                {
                    "name": "Priya Nair",
                    "position": "Downtown shop owner",
                    "body": "I support free weekend parking. Shoppers avoid downtown when they have to pay for parking, and my sales are noticeably lower on weekends compared with the free mall lot nearby.",
                },
                {
                    "name": "Colin Hughes",
                    "position": "City budget committee member",
                    "body": "I am against it. Weekend meter revenue funds sidewalk repairs downtown, and removing it would mean either cutting that maintenance or raising other fees to cover the gap.",
                },
            ],
        },
        "learning_notes": "Separate the sales concern from the budget concern.",
        "questions": [
            {
                "stem": "Why does Priya support free weekend parking?",
                "skill_focus": "detail",
                "evidence": "my sales are noticeably lower on weekends compared with the free mall lot nearby",
                "explanation": "She connects paid parking to lower weekend sales at her shop.",
                "choices": [
                    c("She believes it would increase her weekend sales", True, "She directly links parking cost to lower sales."),
                    c("She wants to reduce traffic downtown", False, "Traffic is not her stated concern."),
                    c("She owns a parking garage downtown", False, "No garage ownership is mentioned."),
                    c("She wants meters removed on weekdays too", False, "She discusses weekends only."),
                ],
            },
            {
                "stem": "What is Colin's main concern about removing the fee?",
                "skill_focus": "inference",
                "evidence": "Weekend meter revenue funds sidewalk repairs downtown",
                "explanation": "He is concerned about losing funding for sidewalk maintenance.",
                "choices": [
                    c("Losing funding for sidewalk repairs", True, "This is the funding gap he names."),
                    c("Shoppers parking too far away", False, "Parking distance is not discussed."),
                    c("Meters being difficult to use", False, "Meter usability is not discussed."),
                    c("Weekend traffic congestion", False, "Congestion is not mentioned.")
                ],
            },
        ],
    },
]
