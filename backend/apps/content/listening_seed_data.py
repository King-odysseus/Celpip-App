"""Original Listening practice scripts drafted for independent review."""
# ruff: noqa: E501


def c(text, correct, explanation):
    return {"text": text, "is_correct": correct, "explanation": explanation}


LISTENING_TASK_TYPES = [
    {
        "code": "listening_problem_solving",
        "skill": "listening",
        "title": "Listening to Problem Solving",
        "part_number": 1,
        "description": "Follow people as they identify a practical problem, compare options, and agree on action.",
        "strategy": ["Set up notes for problem, options, and decision.", "Track who suggests each solution.", "Listen for corrections and the final choice."],
        "common_mistakes": ["Choosing the first idea instead of the accepted plan.", "Missing a condition attached to an option."],
    },
    {
        "code": "listening_daily_conversation",
        "skill": "listening",
        "title": "Listening to a Daily Life Conversation",
        "part_number": 2,
        "description": "Understand an informal conversation about an ordinary Canadian situation.",
        "strategy": ["Note the relationship and setting.", "Track changes in plans.", "Use tone to infer feelings and purpose."],
        "common_mistakes": ["Remembering a cancelled plan as the final plan.", "Ignoring tone when the words sound neutral."],
    },
    {
        "code": "listening_information",
        "skill": "listening",
        "title": "Listening for Information",
        "part_number": 3,
        "description": "Organize facts and instructions from an informative talk.",
        "strategy": ["Create headings before listening.", "Use abbreviations for dates, rules, and exceptions.", "Notice sequence markers such as first and finally."],
        "common_mistakes": ["Writing every word instead of key facts.", "Confusing an example with a requirement."],
    },
    {
        "code": "listening_news",
        "skill": "listening",
        "title": "Listening to a News Item",
        "part_number": 4,
        "description": "Identify the who, what, when, where, why, and outcome in a factual report.",
        "strategy": ["Use the introduction to predict the topic.", "Record names and roles clearly.", "Separate the event from reactions to it."],
        "common_mistakes": ["Mixing up a witness and an organizer.", "Selecting a true detail that does not complete the sentence."],
    },
    {
        "code": "listening_discussion",
        "skill": "listening",
        "title": "Listening to a Discussion",
        "part_number": 5,
        "description": "Distinguish several speakers' opinions, reasons, and points of agreement.",
        "strategy": ["Make one note column per speaker.", "Mark agreement and disagreement.", "Connect reasons to the correct speaker."],
        "common_mistakes": ["Assigning one speaker's reason to another.", "Treating partial agreement as complete support."],
    },
    {
        "code": "listening_viewpoints",
        "skill": "listening",
        "title": "Listening for Viewpoints",
        "part_number": 6,
        "description": "Follow a prepared talk that presents an issue, perspectives, and proposed responses.",
        "strategy": ["Identify the central issue first.", "List each stakeholder and viewpoint.", "Listen for contrasts, consequences, and the speaker's conclusion."],
        "common_mistakes": ["Assuming every viewpoint is the speaker's own.", "Missing how a proposal responds to a concern."],
    },
]


LISTENING_SETS = [
    {
        "slug": "apartment-heating-plan",
        "task_type": "listening_problem_solving",
        "title": "The Apartment Heating Problem",
        "topic": "Housing maintenance",
        "difficulty": 1,
        "estimated_level": 5,
        "instructions": "Listen once and follow how the neighbours solve their heating problem.",
        "intro": "Two neighbours discuss a cold apartment before speaking with the building manager.",
        "transcript": "Nadia: Is your apartment unusually cold too, Colin? Mine has been at sixteen degrees since last night, even though the thermostat is set to twenty-one.\nColin: Yes. I almost bought a space heater this morning, but the building notice says portable heaters can overload the older outlets.\nNadia: Good point. I called the maintenance line, but the recording said non-emergency requests may take two days.\nColin: This affects the whole floor, so perhaps it counts as urgent. We could each submit a request so they know it is not one broken thermostat.\nNadia: Or we could go downstairs and ask the building manager directly. I saw Mr. Chen in the office ten minutes ago.\nColin: Let's do that first. If he has already called a technician, separate requests will just create duplicates.\nNadia: Agreed. I'll bring a photo of my thermostat reading. Could you check the hallway radiator on the way?\nColin: Sure. If that radiator is cold too, it will show that the problem is probably the central boiler.\nNadia: And if the repair takes a while, we can ask whether the building has safe loaner heaters.\nColin: That sounds better than buying one we may not be allowed to use. Let's speak to Mr. Chen now, then update the other neighbours in our floor's message group.",
        "questions": [
            {"stem": "What problem are Nadia and Colin trying to solve?", "skill_focus": "gist", "evidence": "Both apartments are unusually cold despite the thermostat setting.", "explanation": "The conversation focuses on a heating failure affecting their floor.", "choices": [c("Their apartments are too cold", True, "This is the central problem."), c("Their message group is not working", False, "The group is only used for an update."), c("They need permission to move", False, "Moving is never discussed."), c("Their water has been turned off", False, "Water is not mentioned.")]},
            {"stem": "Why do they decide to visit the manager before filing requests?", "skill_focus": "inference", "evidence": "Colin says separate requests may create duplicates if a technician has already been called.", "explanation": "They want to learn whether action is already underway.", "choices": [c("To avoid duplicate maintenance requests", True, "This is Colin's stated reason."), c("To borrow the manager's phone", False, "They already called the line."), c("To complain about their neighbours", False, "They plan to inform neighbours."), c("To pay for a new boiler", False, "They do not offer to buy equipment.")]},
            {"stem": "What will Colin check on the way downstairs?", "skill_focus": "detail", "evidence": "Nadia asks him to check the hallway radiator.", "explanation": "The radiator may show whether the central boiler is affected.", "choices": [c("The older outlets", False, "They discuss outlet safety but do not inspect them."), c("The maintenance recording", False, "Nadia already heard it."), c("The hallway radiator", True, "Nadia requests this directly."), c("The neighbours' thermostats", False, "He is asked about a shared radiator.")]},
        ],
    },
    {
        "slug": "pottery-class-change",
        "task_type": "listening_daily_conversation",
        "title": "A Change to Pottery Class",
        "topic": "Community recreation",
        "difficulty": 1,
        "estimated_level": 6,
        "instructions": "Listen once to the conversation about a community-centre class.",
        "intro": "Friends talk after receiving a message about their evening pottery course.",
        "transcript": "Evan: Did you see the message from the community centre? Thursday's pottery class has moved to Friday because the instructor is ill.\nLeila: I saw it. Friday is difficult because my cousin arrives from Calgary at seven. I promised to pick her up at the station.\nEvan: The class starts at six, so you would have to leave halfway through. Could your cousin take the bus?\nLeila: She has two large suitcases, and she has never visited us before. I don't want her searching for the right stop after a long trip.\nEvan: Fair enough. The message says we can attend Saturday morning instead, but we need to tell the centre by noon tomorrow.\nLeila: Saturday would work. I usually volunteer at the food bank, but my shift is in the afternoon this week. What about you?\nEvan: I coach my daughter's soccer team at ten. However, I can go to the Friday class and take notes about the glazing demonstration for you.\nLeila: Thanks, but I would rather see the demonstration myself. I'll switch to Saturday and email the centre tonight.\nEvan: Good plan. Maybe ask whether your unfinished bowl will be moved to the Saturday studio.\nLeila: I nearly forgot about that. I'll include it in the email. Let me know how Friday goes, and we can compare our bowls next week.",
        "questions": [
            {"stem": "Why was the original class moved?", "skill_focus": "detail", "evidence": "Evan says the instructor is ill.", "explanation": "The instructor's illness caused the schedule change.", "choices": [c("The studio is being painted", False, "No renovation is mentioned."), c("The instructor is ill", True, "Evan states this at the beginning."), c("Too few students registered", False, "Registration numbers are not discussed."), c("Friday has better weather", False, "Weather is irrelevant.")]},
            {"stem": "Why does Leila reject the idea that her cousin take the bus?", "skill_focus": "inference", "evidence": "Her cousin has large luggage and has never visited before.", "explanation": "Leila believes the trip would be difficult for a first-time visitor with luggage.", "choices": [c("The buses stop before seven", False, "No service time is given."), c("Her cousin dislikes public transit", False, "No preference is stated."), c("The station is closed", False, "The cousin is arriving there."), c("Her cousin has luggage and does not know the route", True, "Both concerns are explicit.")]},
            {"stem": "What will Leila ask about in her email?", "skill_focus": "detail", "evidence": "Evan reminds her to ask whether her unfinished bowl will be moved.", "explanation": "She plans to include the bowl question with her schedule change.", "choices": [c("Moving her unfinished bowl", True, "This is the final detail they discuss."), c("Joining the soccer team", False, "Evan coaches the team."), c("Changing her food-bank shift", False, "Her existing shift already works."), c("Collecting her cousin on Saturday", False, "Her cousin arrives Friday.")]},
        ],
    },
    {
        "slug": "river-trail-volunteer-orientation",
        "task_type": "listening_information",
        "title": "River Trail Volunteer Orientation",
        "topic": "Environmental volunteering",
        "difficulty": 2,
        "estimated_level": 7,
        "instructions": "Listen once to an orientation talk and organize the practical details.",
        "intro": "A coordinator welcomes volunteers to a riverside cleanup event.",
        "transcript": "Coordinator: Welcome to the Mill Creek trail cleanup. Before we divide into teams, I will explain today's plan. Everyone should sign the attendance sheet beside the blue tent, even if you registered online. That lets us confirm who is on the trail in an emergency.\nWe have three work areas. Team One will collect litter between the parking lot and the footbridge. Team Two will remove small branches from the path beyond the bridge. Only trained city staff may cut large fallen trees, so mark those locations on your map and leave them alone. Team Three will record damaged signs and railings.\nGloves, litter grabbers, and bright safety vests are available at the equipment table. Please keep your vest on until you sign out. Refillable water containers are welcome, and a filling station is beside the tent. Do not drink from the trail's taps because they are used only for landscaping.\nAt eleven thirty, bring full litter bags to the gravel area near the parking lot. Do not leave them beside public garbage bins. We will finish at noon and serve sandwiches, fruit, and hot drinks. If you listed a food allergy when registering, your labelled lunch will be at the coordinator's table. Finally, if you find broken glass or a needle, do not pick it up. Stand nearby and call the phone number printed on your map so a safety volunteer can respond.",
        "questions": [
            {"stem": "Why must everyone sign the attendance sheet?", "skill_focus": "purpose", "evidence": "The sheet confirms who is on the trail in an emergency.", "explanation": "The coordinator needs an accurate safety record.", "choices": [c("To choose a lunch", False, "Allergy lunches were arranged during registration."), c("To record who is present for safety", True, "This purpose is stated directly."), c("To borrow a refillable bottle", False, "Volunteers bring their own bottles."), c("To request a different team leader", False, "Leaders are not discussed.")]},
            {"stem": "What should volunteers do when they see a large fallen tree?", "skill_focus": "detail", "evidence": "They should mark it on the map and leave it for trained staff.", "explanation": "Volunteers are not authorized to cut large trees.", "choices": [c("Cut it into small branches", False, "Only trained city staff may cut it."), c("Move it beside a garbage bin", False, "That instruction concerns neither trees nor debris."), c("Mark its location and leave it", True, "These are the exact instructions."), c("Ask Team Three to repair it", False, "Team Three records signs and railings.")]},
            {"stem": "Where should full litter bags be taken?", "skill_focus": "detail", "evidence": "The coordinator names the gravel area near the parking lot.", "explanation": "Public bins are explicitly the wrong location.", "choices": [c("The gravel area near the parking lot", True, "This is the collection point."), c("Beside the public garbage bins", False, "The speaker says not to leave them there."), c("Beyond the footbridge", False, "That is Team Two's work area."), c("The water-filling station", False, "That station is for drinking water.")]},
        ],
    },
    {
        "slug": "mobile-health-clinic-news",
        "task_type": "listening_news",
        "title": "A Mobile Health Clinic for Pine County",
        "topic": "Rural health services",
        "difficulty": 2,
        "estimated_level": 8,
        "instructions": "Listen once to the news report, noting people, dates, reasons, and outcomes.",
        "intro": "A local radio report describes a new regional service.",
        "transcript": "Newsreader: Residents of three Pine County communities will soon be able to visit a mobile health clinic without travelling to the regional hospital. The specially equipped bus begins its weekly route on September ninth. It will stop in Glenora on Mondays, West Pine on Wednesdays, and Lake Junction on Fridays.\nThe service will offer routine checks, vaccinations, and follow-up appointments for patients managing long-term conditions. It will not provide emergency treatment. County health director Dr. Amina Yusuf says distance has caused some residents to postpone basic care, particularly in winter. The bus is intended to bring preventive services closer to home while reducing pressure on the hospital's busy outpatient department.\nThe project began after a six-month pilot last year. During that pilot, a smaller van visited Glenora twice a month. Appointment attendance rose by twenty-three percent, but staff found that the van lacked private space and could not carry enough equipment. The new bus contains two examination rooms and a wheelchair lift.\nAppointments can be booked by phone beginning next Tuesday. A limited number of same-day spaces will also be available at each stop. Mayor Lucas Grant welcomed the service but said reliable rural internet is still needed because some specialist appointments take place by video. The county will review the route after four months and may add a fourth community if demand is strong.",
        "questions": [
            {"stem": "The mobile clinic was introduced mainly to", "skill_focus": "purpose", "evidence": "Distance caused delayed basic care, and the bus brings preventive services closer.", "explanation": "Its main purpose is to improve access to routine care in distant communities.", "choices": [c("replace the regional hospital", False, "It reduces pressure but does not replace the hospital."), c("provide emergency treatment", False, "Emergency treatment is explicitly excluded."), c("improve access to routine health services", True, "This summarizes the reason for the route."), c("test rural internet speeds", False, "Internet is a separate remaining concern.")]},
            {"stem": "The smaller pilot van was inadequate because it", "skill_focus": "detail", "evidence": "It lacked private space and could not carry enough equipment.", "explanation": "The new bus addresses both limitations.", "choices": [c("could not operate in winter", False, "Winter access is a concern, but this is not stated about the van."), c("had too little space and equipment capacity", True, "Both problems are explicit."), c("visited too many communities", False, "It visited only Glenora."), c("required online booking", False, "Booking details concern the new service.")]},
            {"stem": "What may happen after the four-month review?", "skill_focus": "detail", "evidence": "The county may add a fourth community if demand is strong.", "explanation": "Expansion depends on use of the initial route.", "choices": [c("The hospital will close", False, "No closure is proposed."), c("All appointments will become virtual", False, "Only some specialist visits use video."), c("The pilot van will return", False, "The report does not propose this."), c("Another community may join the route", True, "This is the possible outcome of the review.")]},
        ],
    },
    {
        "slug": "regional-transit-pass-discussion",
        "task_type": "listening_discussion",
        "title": "Choosing a Regional Transit Pass",
        "topic": "Workplace commuting",
        "difficulty": 3,
        "estimated_level": 9,
        "instructions": "Listen once and keep each speaker's position and reasons separate.",
        "intro": "Three members of a workplace committee discuss a proposed employee transit benefit.",
        "transcript": "Marisol: We need to recommend one transit benefit for next year's budget. The simplest choice is a monthly pass for every employee. It is predictable for payroll and encourages people to leave their cars at home.\nGraham: That works for daily commuters, but nearly half our staff work from home two or three days a week. A full monthly pass may cost more than the trips they actually take. I prefer a reloadable card with a fixed employer credit.\nSophie: A credit is flexible, although employees who travel from the outer suburbs pay higher fares. Giving everyone the same dollar amount could benefit people with short trips more.\nMarisol: True, but the monthly pass has the same problem. Some employees can walk to work and would receive something they rarely use.\nGraham: What if employees choose between a monthly pass and an equivalent credit?\nSophie: Choice sounds fair, but it creates more administration. Human Resources would have to track changes, lost cards, and different renewal dates. I suggest a three-month trial of the fixed credit. We could measure how many employees use it and whether commuting patterns change.\nMarisol: I can support a trial, provided we survey staff who live beyond the central fare zone. If the credit covers only part of their normal trip, we need to know.\nGraham: Agreed. We should also ask payroll whether unused credit can carry forward. That would help hybrid workers save it for weeks when they travel more.\nSophie: Then our recommendation is a trial credit, followed by a usage review and an equity survey. If the results show major differences, we can adjust the amount or reconsider the monthly pass.",
        "questions": [
            {"stem": "Why does Graham oppose giving everyone a monthly pass?", "skill_focus": "inference", "evidence": "Many employees work remotely and may make too few trips to justify the pass.", "explanation": "He sees the pass as poor value for hybrid workers.", "choices": [c("Payroll cannot process passes", False, "Marisol says passes are predictable for payroll."), c("Hybrid workers may not use it enough", True, "This is Graham's main concern."), c("The pass excludes outer suburbs", False, "Sophie raises fare-zone fairness more generally."), c("Employees prefer driving", False, "No survey result says this.")]},
            {"stem": "What concern does Sophie raise about a fixed credit?", "skill_focus": "detail", "evidence": "Outer-suburb employees pay more, so an equal credit may favour shorter trips.", "explanation": "She questions whether the benefit would be equitable.", "choices": [c("It may be less valuable to people with costly trips", True, "This captures her equity concern."), c("It cannot be loaded onto a card", False, "The proposal uses a reloadable card."), c("It will make everyone commute daily", False, "No such effect is predicted."), c("It is illegal outside the central zone", False, "Legality is not discussed.")]},
            {"stem": "What do all three speakers finally support?", "skill_focus": "gist", "evidence": "They agree on a trial credit, usage review, and equity survey.", "explanation": "The final recommendation is a measured trial rather than a permanent choice.", "choices": [c("A permanent monthly pass", False, "They postpone that decision."), c("No transit benefit", False, "All support testing a benefit."), c("A trial credit followed by evaluation", True, "This is their shared conclusion."), c("Free parking for hybrid workers", False, "Parking is never proposed.")]},
        ],
    },
    {
        "slug": "vacant-lots-community-talk",
        "task_type": "listening_viewpoints",
        "title": "What Should the City Do with Vacant Lots?",
        "topic": "Urban land use",
        "difficulty": 3,
        "estimated_level": 10,
        "instructions": "Listen once to the prepared talk and distinguish the competing viewpoints.",
        "intro": "A planning researcher presents perspectives on temporary uses for vacant city land.",
        "transcript": "Speaker: Our city owns fourteen vacant lots awaiting long-term development. Some may remain empty for five years, and council is considering temporary community uses. The debate is not simply between action and inaction; it concerns cost, access, and who carries responsibility.\nNeighbourhood associations favour community gardens. They argue that gardens provide fresh food, strengthen social ties, and discourage illegal dumping. Their proposals rely heavily on volunteers, however. Groups in areas with fewer volunteers worry that the most organized neighbourhoods would receive the greatest benefit.\nSeveral youth organizations prefer small recreation spaces with basketball courts and seating. They say young people need free places that do not require registration. Nearby residents support that goal but raise concerns about evening noise and ongoing maintenance. Better lighting and posted closing hours could address some concerns, although both add costs.\nA third proposal comes from local artists, who want outdoor studios and rotating markets. They believe temporary creative spaces could attract visitors to overlooked commercial streets. Critics respond that markets may serve occasional visitors more than residents who need daily amenities.\nIn my view, council should not choose one model for every lot. It should publish clear criteria, guarantee basic city funding, and invite each neighbourhood to select from several approved designs. Success should be measured not only by attendance but also by whether different ages, incomes, and mobility levels can participate. Temporary projects are valuable precisely because they can be adjusted. A two-year review would allow the city to expand what works and replace what does not.",
        "questions": [
            {"stem": "Why are some groups cautious about relying on volunteers?", "skill_focus": "inference", "evidence": "Neighbourhoods with fewer volunteers fear organized areas will receive more benefit.", "explanation": "Volunteer capacity is uneven and could create unequal access.", "choices": [c("Volunteers are not allowed on city land", False, "No prohibition exists."), c("Volunteer-based projects may favour better-organized areas", True, "This is the stated equity concern."), c("Volunteers only support recreation spaces", False, "They are discussed mainly for gardens."), c("The city has too many volunteers", False, "The concern is insufficient capacity in some areas.")]},
            {"stem": "What objection is raised to outdoor markets?", "skill_focus": "detail", "evidence": "Critics say markets may serve occasional visitors more than residents needing daily amenities.", "explanation": "The objection concerns whom the markets primarily benefit.", "choices": [c("They require permanent buildings", False, "They are proposed as temporary outdoor uses."), c("Artists refuse to welcome visitors", False, "Artists hope to attract visitors."), c("They may not meet residents' everyday needs", True, "This paraphrases the criticism."), c("They create more traffic than basketball courts", False, "That comparison is not made.")]},
            {"stem": "What approach does the speaker ultimately recommend?", "skill_focus": "purpose", "evidence": "The speaker proposes clear criteria, basic funding, local choice, inclusive measures, and review.", "explanation": "The recommendation combines neighbourhood choice with city support and evaluation.", "choices": [c("Use the same garden design on every lot", False, "The speaker rejects one model for every lot."), c("Leave every lot empty until permanent development", False, "The talk supports useful temporary projects."), c("Let private businesses control all decisions", False, "Council and neighbourhoods retain roles."), c("Offer supported local choices and review the results", True, "This summarizes the final proposal.")]},
        ],
    },
]
