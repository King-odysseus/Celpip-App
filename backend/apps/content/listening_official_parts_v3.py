"""Third variant of full-part Listening simulation sets.

Each set is an entire official Listening part (one continuous original
recording, full official question count) and is a third, distinct scenario
from ``listening_official_parts.py`` and ``listening_official_parts_v2.py`` so
that repeated full-length mocks keep rotating to fresh content instead of
recycling the same two scripts. Like the first two variants, these are NOT
stage-expanded and are a preferred single-item building block of full-length
mocks.

Each set names a ``source_slug`` from an existing official-size part in the
same task family. ``seed_listening_content`` copies that WAV as a temporary
placeholder recording when this slug's own audio has not been generated yet,
so the item is playable immediately; ``regenerate_listening_audio --only-local``
then synthesizes the real script into its own audio on the next deploy that
enables it, without any manual step.
"""
# ruff: noqa: E501


def c(text, correct, explanation):
    return {"text": text, "is_correct": correct, "explanation": explanation}


LISTENING_OFFICIAL_SETS_V3 = [
    {
        "slug": "childcare-centre-heating-failure",
        "task_type": "listening_problem_solving",
        "title": "Keeping the Childcare Centre Warm",
        "topic": "Small business logistics",
        "difficulty": 2,
        "estimated_level": 7,
        "instructions": "Listen once to the whole conversation, then answer the eight questions about how the directors solve the problem.",
        "intro": "Two co-directors of a childcare centre work out where to keep the children warm when the furnace fails during a cold snap.",
        "source_slug": "weekend-market-produce-shortage",
        "transcript": (
            "Farah: Ben, it's Farah. The furnace repair company just called — the part for our heating system will not arrive until tomorrow afternoon, and the forecast says minus fifteen tonight. We cannot keep the toddlers here without heat.\n"
            "Ben: Hi Farah. Can we move today's group to the community centre next door? I know they have an activity room free until three.\n"
            "Farah: I already called them. The activity room is free, but it only fits twenty children comfortably, and we have thirty-two registered today.\n"
            "Ben: Could we split the group? Send the toddlers, who need the warmest room, to the community centre, and keep the older preschoolers here with the space heaters from the storage closet.\n"
            "Farah: The space heaters would keep one classroom warm enough for a few hours, but the fire code limits us to two heaters running at once in that room.\n"
            "Ben: Then let's put the preschoolers in the two rooms that share a wall with the boiler room — those stay warmest even with the main heat off, and run one heater in each.\n"
            "Farah: That works for this afternoon. I will call the toddlers' parents now so they know about the temporary move, and confirm the community centre allows drop-off directly at their front desk.\n"
            "Ben: I will text the preschool parents that pickup stays here as normal, just in the two east-side rooms instead of the usual ones.\n"
            "Farah: Good. I will also ask the community centre if we can leave a staff member's number posted at their desk in case a toddler's parent goes to our building first by mistake.\n"
            "Ben: I'll print a sign for our front door pointing anyone who arrives here toward the community centre entrance.\n"
            "Farah: Once the part comes in tomorrow, we will need the whole afternoon with no children present so the technician can finish safely.\n"
            "Ben: I'll ask the board to approve a half-day closure tomorrow afternoon so the repair can happen without interruption."
        ),
        "speaker_genders": {"Farah": "female", "Ben": "male"},
        "questions": [
            {"stem": "Why can the childcare centre not operate normally today?", "skill_focus": "detail", "evidence": "the part for our heating system will not arrive until tomorrow afternoon, and the forecast says minus fifteen", "explanation": "The furnace part is delayed during forecast extreme cold.", "choices": [c("The heating repair is delayed during extreme cold", True, "Both facts together make the building unsafe for children."), c("The building was damaged by a storm", False, "No storm damage is mentioned."), c("A staff shortage closed the centre", False, "Staffing is not the stated problem."), c("The water supply was shut off", False, "Water is not mentioned.")]},
            {"stem": "Why can all thirty-two children not move to the community centre?", "skill_focus": "detail", "evidence": "it only fits twenty children comfortably, and we have thirty-two registered today", "explanation": "The activity room's capacity is smaller than today's enrollment.", "choices": [c("The room only fits twenty children", True, "This is the stated capacity limit."), c("The community centre is closed today", False, "It is open until three."), c("The centre charges an extra fee", False, "No fee is mentioned."), c("Parents refused the move", False, "Parents are only informed, not asked to refuse.")]},
            {"stem": "Which children are sent to the community centre?", "skill_focus": "detail", "evidence": "Send the toddlers, who need the warmest room, to the community centre", "explanation": "The toddlers go because they need the warmest space.", "choices": [c("The toddlers", True, "They need the warmest room."), c("The preschoolers", False, "The preschoolers stay at the centre."), c("Both groups equally split", False, "The toddlers go as a whole group."), c("Only the staff", False, "The move concerns the children, not staff alone.")]},
            {"stem": "Why can't the preschool room simply run more heaters?", "skill_focus": "detail", "evidence": "the fire code limits us to two heaters running at once in that room", "explanation": "Fire code caps the number of heaters permitted per room.", "choices": [c("Fire code limits the room to two heaters", True, "This is the stated restriction."), c("The heaters are broken", False, "The heaters work but are limited in number."), c("There is no electrical outlet", False, "Outlets are not mentioned as a problem."), c("The preschoolers object to heaters", False, "The children's preference is not discussed.")]},
            {"stem": "Why are the two east-side rooms chosen for the preschoolers?", "skill_focus": "inference", "evidence": "those stay warmest even with the main heat off", "explanation": "Sharing a wall with the boiler room keeps them warmer without the main heat.", "choices": [c("They share a wall with the boiler room", True, "That keeps them warmest despite no heat."), c("They have the most space heaters already", False, "Heaters are added, not already present."), c("They are farthest from the front door", False, "Distance from the door is not the reason given."), c("They were recently renovated", False, "No renovation is mentioned.")]},
            {"stem": "What does Farah confirm with the community centre?", "skill_focus": "detail", "evidence": "confirm the community centre allows drop-off directly at their front desk", "explanation": "She checks that drop-off can happen at their front desk.", "choices": [c("That drop-off can happen at their front desk", True, "This is the stated confirmation."), c("That they will provide lunch", False, "Food is not discussed."), c("That they will waive a rental fee", False, "No fee is mentioned."), c("That they have extra staff available", False, "Staffing at the centre is not discussed.")]},
            {"stem": "Why does Ben print a sign for the front door?", "skill_focus": "purpose", "evidence": "pointing anyone who arrives here toward the community centre entrance", "explanation": "The sign redirects anyone who mistakenly comes to the childcare centre.", "choices": [c("To redirect arriving parents to the community centre", True, "This matches the sign's stated purpose."), c("To announce the centre is closed permanently", False, "The closure is temporary, for one day."), c("To advertise the community centre's programs", False, "Advertising is not the intent."), c("To list today's snow-day cancellations", False, "No cancellation is announced.")]},
            {"stem": "What does the board need to approve for tomorrow?", "skill_focus": "detail", "evidence": "approve a half-day closure tomorrow afternoon so the repair can happen without interruption", "explanation": "A half-day closure lets the technician finish safely without children present.", "choices": [c("A half-day closure tomorrow afternoon", True, "This is the stated request."), c("A full week of closure", False, "Only a half-day is requested."), c("A new furnace purchase", False, "Only a repair is discussed, not replacement."), c("A change in the pickup schedule", False, "Pickup for today, not tomorrow, is being changed.")]},
        ],
    },
    {
        "slug": "surprise-party-venue-change",
        "task_type": "listening_daily_conversation",
        "title": "Changing the Surprise Party Venue",
        "topic": "Friends organizing an event",
        "difficulty": 1,
        "estimated_level": 5,
        "instructions": "Listen once to the conversation, then answer the five questions about the new party plan.",
        "intro": "Two friends scramble to find a new venue for a surprise fortieth-birthday party after their original venue floods.",
        "source_slug": "helping-maya-move-sunday",
        "transcript": (
            "Renee: Marcus, it's Renee. Bad news — the community hall just called to say a pipe burst in their kitchen, so we cannot use it Saturday for Dana's surprise party.\n"
            "Marcus: Oh no. How many people did we confirm? I think it was around forty.\n"
            "Renee: Forty-two, actually, plus the cake and the small dance floor we rented.\n"
            "Marcus: My cousin has a backyard that could fit that many if the weather holds, but the forecast shows a thirty percent chance of rain.\n"
            "Renee: That's risky for a surprise — if it rains, guests get soaked right as Dana walks in. Do you know anywhere with a covered patio?\n"
            "Marcus: The bowling alley on Fifth Street has a private party room with a covered outdoor section attached. I can call them this afternoon.\n"
            "Renee: Perfect, and ask if they can still fit the dance floor rental inside, since the party room might be smaller than the hall.\n"
            "Marcus: I will also check if they allow outside catering, since we already ordered food from Dana's favourite restaurant.\n"
            "Renee: Good thinking. If they don't, we may need to switch to their in-house menu instead.\n"
            "Marcus: I'll message everyone the new address once it's confirmed, and remind them to still arrive fifteen minutes early so we're all hidden before Dana gets there."
        ),
        "speaker_genders": {"Renee": "female", "Marcus": "male"},
        "questions": [
            {"stem": "Why do Renee and Marcus need a new venue?", "skill_focus": "gist", "evidence": "a pipe burst in their kitchen, so we cannot use it Saturday", "explanation": "A burst pipe made the community hall unusable.", "choices": [c("A pipe burst at the community hall", True, "This is the stated cause."), c("The hall double-booked the date", False, "No double booking is mentioned."), c("Dana found out about the party", False, "The party is still a surprise."), c("The hall raised its rental price", False, "Price is not discussed.")]},
            {"stem": "How many guests are confirmed?", "skill_focus": "detail", "evidence": "Forty-two, actually", "explanation": "Renee corrects the number to forty-two.", "choices": [c("Forty-two", True, "This is the corrected number."), c("Forty", False, "That was Marcus's rough guess."), c("Thirty", False, "This number is not mentioned."), c("Fifty", False, "This number is not mentioned.")]},
            {"stem": "Why does Renee hesitate about using the backyard?", "skill_focus": "inference", "evidence": "if it rains, guests get soaked right as Dana walks in", "explanation": "Rain could ruin the surprise reveal outdoors.", "choices": [c("Rain could ruin the surprise outdoors", True, "She fears guests getting soaked during the reveal."), c("The backyard is too small", False, "Size is not her concern; weather is."), c("Marcus's cousin refused to help", False, "The cousin offers the yard willingly."), c("The backyard has no parking", False, "Parking is not discussed.")]},
            {"stem": "What does Marcus need to check about the bowling alley?", "skill_focus": "detail", "evidence": "ask if they can still fit the dance floor rental inside ... check if they allow outside catering", "explanation": "He must confirm the dance floor fits and whether outside food is allowed.", "choices": [c("Whether the dance floor fits and outside catering is allowed", True, "Both checks are mentioned."), c("Whether they have a birthday discount", False, "No discount is mentioned."), c("Whether they are open on Sundays", False, "Sunday hours are not discussed."), c("Whether they can move the party to next month", False, "Rescheduling is not discussed.")]},
            {"stem": "What does Marcus remind guests to do?", "skill_focus": "detail", "evidence": "remind them to still arrive fifteen minutes early so we're all hidden before Dana gets there", "explanation": "Guests should arrive early to stay hidden before the surprise.", "choices": [c("Arrive fifteen minutes early to stay hidden", True, "This matches his final reminder."), c("Bring their own food", False, "Catering is being arranged separately."), c("Wear a specific colour", False, "No dress code is mentioned."), c("Park at the community hall", False, "The venue has changed away from the hall.")]},
        ],
    },
    {
        "slug": "soft-plastics-recycling-update",
        "task_type": "listening_information",
        "title": "A New Soft-Plastics Recycling Program",
        "topic": "Municipal waste services",
        "difficulty": 1,
        "estimated_level": 6,
        "intro": "A city waste-management coordinator explains a new three-bin sorting program starting next month.",
        "source_slug": "library-summer-reading-program",
        "instructions": "Listen once to the coordinator's announcement, then answer the six questions about the program details.",
        "transcript": (
            "Coordinator: Good afternoon, I'm Devon Okafor with the city's waste management office, here to explain the new three-bin sorting program starting next month.\n"
            "Every household will receive a new grey bin for soft plastics — bags, wrap, and pouches — which currently cannot go in the regular blue recycling bin. Soft plastics placed in the blue bin will no longer be collected after the change.\n"
            "The blue bin continues to take rigid recyclables: bottles, cans, cardboard, and paper, but items must be rinsed; a greasy pizza box, for example, still belongs in the green organics bin, not the blue one.\n"
            "Collection day is not changing. All three bins go out on your regular day, but the grey bin will be picked up every other week rather than weekly, alternating with yard waste.\n"
            "Residents in apartment buildings with shared bins will receive the new grey bin from their building manager, not directly from the city, so please contact your manager if it has not arrived by the start date.\n"
            "A staffed drop-off depot at the old fairgrounds will also accept large volumes of soft plastic for anyone who does not want to wait for their first collection.\n"
            "Finally, a full sorting guide will be mailed to every address two weeks before the program begins, and the same guide will be posted on the city website."
        ),
        "speaker_genders": {"Coordinator": "male"},
        "questions": [
            {"stem": "What is the announcement mainly about?", "skill_focus": "gist", "evidence": "the new three-bin sorting program starting next month", "explanation": "The coordinator introduces a new soft-plastics bin and sorting rules.", "choices": [c("A new bin and sorting rules for soft plastics", True, "This is the program being explained."), c("A fee increase for garbage collection", False, "No fee change is mentioned."), c("The closure of the recycling depot", False, "The depot is opening a new drop-off role, not closing."), c("A ban on plastic packaging in stores", False, "No store-level ban is discussed.")]},
            {"stem": "What happens to soft plastics placed in the blue bin after the change?", "skill_focus": "detail", "evidence": "Soft plastics placed in the blue bin will no longer be collected after the change.", "explanation": "They will not be picked up once the new program starts.", "choices": [c("They will no longer be collected", True, "This is stated directly."), c("They will be collected as usual", False, "The opposite is stated."), c("They will be collected monthly", False, "No such schedule is mentioned for the blue bin."), c("They will require a special sticker", False, "No sticker requirement is mentioned.")]},
            {"stem": "What must happen to items before they go in the blue bin?", "skill_focus": "detail", "evidence": "items must be rinsed", "explanation": "Rigid recyclables need to be rinsed first.", "choices": [c("They must be rinsed", True, "This is the stated requirement."), c("They must be flattened", False, "Flattening is not mentioned."), c("They must be labelled", False, "Labelling is not mentioned."), c("They must be bagged separately", False, "Bagging is not mentioned.")]},
            {"stem": "How often is the new grey bin collected?", "skill_focus": "detail", "evidence": "the grey bin will be picked up every other week rather than weekly, alternating with yard waste", "explanation": "It alternates biweekly with yard waste pickup.", "choices": [c("Every other week", True, "This matches the announcement."), c("Every week", False, "Weekly pickup applies to the blue bin, not grey."), c("Once a month", False, "The interval given is every other week."), c("Only on request", False, "No on-request system is described.")]},
            {"stem": "How do apartment residents get their grey bin?", "skill_focus": "detail", "evidence": "will receive the new grey bin from their building manager, not directly from the city", "explanation": "Building managers distribute the bins for shared buildings.", "choices": [c("From their building manager", True, "This is the stated distribution method."), c("By picking it up at city hall", False, "No pickup location like this is named for apartments."), c("It is mailed directly to each unit", False, "It comes through the manager, not by mail."), c("They must purchase one", False, "No purchase is required.")]},
            {"stem": "Where can residents drop off large volumes of soft plastic immediately?", "skill_focus": "detail", "evidence": "A staffed drop-off depot at the old fairgrounds", "explanation": "The fairgrounds depot accepts large volumes right away.", "choices": [c("The depot at the old fairgrounds", True, "This matches the announcement."), c("Any fire station", False, "Fire stations are not mentioned."), c("The city hall lobby", False, "City hall is not named as a drop-off site."), c("Their own blue bin", False, "The blue bin does not take soft plastics.")]},
        ],
    },
    {
        "slug": "solar-charging-station-launch",
        "task_type": "listening_news",
        "title": "City Unveils Solar Charging Station",
        "topic": "Public infrastructure news",
        "difficulty": 2,
        "estimated_level": 6,
        "intro": "A newsreader reports on the launch of the city's first solar-powered phone charging station.",
        "source_slug": "bike-library-launch-news",
        "instructions": "Listen once to the news report, then answer the five questions about the story.",
        "transcript": (
            "Newsreader: I'm Julia Sato with Riverside News. The city unveiled its first solar-powered phone charging station in Riverside Park this morning, the first of six planned across the city this year.\n"
            "The station stores power in a battery pack during the day and can charge devices even after sunset, though output is reduced by about half once the battery is more than three-quarters drained.\n"
            "City officials say the eighteen-thousand-dollar project was funded mostly by a provincial green-infrastructure grant, with the remainder covered by park department funds.\n"
            "The station includes six USB ports and two wireless charging pads, and a small display shows the current battery level so people are not surprised by slower charging late in the day.\n"
            "The next station is expected to open at the downtown transit hub within two months, chosen because of its high foot traffic, and officials say locations after that will be picked based on public suggestions submitted through the city's website."
        ),
        "speaker_genders": {"Newsreader": "female"},
        "questions": [
            {"stem": "What is the main announcement in this report?", "skill_focus": "gist", "evidence": "unveiled its first solar-powered phone charging station in Riverside Park", "explanation": "The report covers the launch of a new charging station.", "choices": [c("A new solar-powered charging station opened", True, "This is the central news."), c("A power outage hit Riverside Park", False, "No outage is reported."), c("The city banned public phone charging", False, "The opposite is happening."), c("A new solar farm was approved", False, "No large farm is discussed, only a small station.")]},
            {"stem": "How many stations are planned across the city this year?", "skill_focus": "detail", "evidence": "the first of six planned across the city this year", "explanation": "Six stations are planned in total.", "choices": [c("Six", True, "This matches the report."), c("Two", False, "That is not the stated total."), c("Ten", False, "That is not the stated total."), c("One", False, "One has opened, but six are planned overall.")]},
            {"stem": "What happens to charging output late in the day?", "skill_focus": "detail", "evidence": "output is reduced by about half once the battery is more than three-quarters drained", "explanation": "Output drops once the battery is mostly drained.", "choices": [c("It is reduced by about half", True, "This matches the report."), c("It stops completely", False, "It is reduced, not stopped."), c("It increases at night", False, "The opposite occurs."), c("It stays exactly the same", False, "A reduction is described.")]},
            {"stem": "How was the project mainly funded?", "skill_focus": "detail", "evidence": "funded mostly by a provincial green-infrastructure grant, with the remainder covered by park department funds", "explanation": "A provincial grant covered most of the cost.", "choices": [c("A provincial green-infrastructure grant", True, "This funded most of the project."), c("A private company sponsorship", False, "No sponsorship is mentioned."), c("Money raised by park visitors", False, "No fundraising by visitors is mentioned."), c("A federal transit subsidy", False, "The grant is provincial, not federal, and unrelated to transit.")]},
            {"stem": "Why was the downtown transit hub chosen for the next station?", "skill_focus": "inference", "evidence": "chosen because of its high foot traffic", "explanation": "High foot traffic makes it a useful location.", "choices": [c("It has high foot traffic", True, "This is the stated reason."), c("It already has solar panels installed", False, "No existing panels are mentioned."), c("It is the cheapest available site", False, "Cost is not the stated reason."), c("Residents voted against other sites", False, "No such vote is mentioned for this station.")]},
        ],
    },
    {
        "slug": "early-swim-session-meeting",
        "task_type": "listening_discussion",
        "title": "Should the Pool Add an Early Swim Session?",
        "topic": "Public recreation service",
        "difficulty": 2,
        "estimated_level": 8,
        "intro": "Residents and a pool supervisor discuss whether to add an early adults-only lane-swim session before work hours.",
        "source_slug": "night-bus-extension-meeting",
        "instructions": "Listen once to the public meeting, then answer the eight questions about the speakers' views and the decision.",
        "transcript": (
            "Chair: Thank you for coming. Tonight we are discussing whether to add a seven-to-eight a.m. adults-only lane-swim session at the Fairview Pool, so I will open the floor.\n"
            "Mr. Haddad: I'm Sam Haddad, and I swim for exercise before work. Right now the pool opens at eight, and I lose valuable time getting to my job downtown. An earlier adults-only hour would let me swim and still make it to work.\n"
            "Ms. Bianchi: I'm the pool's aquatics supervisor. Opening an hour earlier means paying a lifeguard and a front-desk staff member for that extra hour, roughly six thousand dollars a year.\n"
            "Mr. Haddad: Could a smaller number of guaranteed swimmers offset some of that with a modest early-bird fee?\n"
            "Ms. Bianchi: Possibly, but our morning survey found only about fifteen people interested, which would not cover the added staffing cost through fees alone.\n"
            "Ms. Renner: I represent parents whose children have early swim lessons on weekends, and I worry that opening earlier on weekdays sets an expectation that weekend hours should also expand, which would cost even more.\n"
            "Mr. Haddad: This proposal is only about weekdays, though — I'm not asking for earlier weekend hours.\n"
            "Chair: Could we trial this on just two weekdays first, say Tuesday and Thursday, before deciding on the rest of the week?\n"
            "Ms. Bianchi: A two-day trial would only cost about twenty-four hundred dollars for three months, which is easier to justify while we gather better attendance numbers.\n"
            "Ms. Renner: I could accept a small trial, as long as it does not automatically expand to weekends without another public discussion.\n"
            "Chair: Then let me propose a three-month Tuesday and Thursday adults-only early swim trial, reviewed at the next quarterly meeting, with no change to weekend hours. All in favour?\n"
            "Several voices: Aye.\n"
            "Chair: The motion carries."
        ),
        "speaker_genders": {"Chair": "female", "Mr. Haddad": "male", "Ms. Bianchi": "female", "Ms. Renner": "female"},
        "questions": [
            {"stem": "What is the meeting deciding?", "skill_focus": "gist", "evidence": "whether to add a seven-to-eight a.m. adults-only lane-swim session", "explanation": "The topic is adding an early swim session.", "choices": [c("Whether to add an early adults-only swim session", True, "This is the proposal under discussion."), c("Whether to close the pool for repairs", False, "No closure is discussed."), c("Whether to raise pool membership fees", False, "Fees are only mentioned as a possible offset."), c("Whether to add a new children's program", False, "The proposal concerns adult swimmers.")]},
            {"stem": "Why does Mr. Haddad want the earlier hour?", "skill_focus": "detail", "evidence": "I lose valuable time getting to my job downtown", "explanation": "An earlier session would let him swim and still reach work on time.", "choices": [c("So he can swim and still get to work on time", True, "This is his stated reason."), c("Because the pool is too crowded during the day", False, "Crowding is not mentioned."), c("Because his doctor recommended morning exercise", False, "No medical reason is given."), c("Because weekend sessions are full", False, "Weekend availability is not his concern.")]},
            {"stem": "What is the estimated cost of opening an hour earlier every weekday?", "skill_focus": "detail", "evidence": "roughly six thousand dollars a year", "explanation": "Extra staffing costs about six thousand dollars annually.", "choices": [c("About six thousand dollars a year", True, "This matches Ms. Bianchi's estimate."), c("About six hundred dollars a year", False, "This is far lower than stated."), c("About sixty thousand dollars a year", False, "This is far higher than stated."), c("There is no extra cost", False, "Extra staffing cost is explicitly mentioned.")]},
            {"stem": "What did the morning survey find?", "skill_focus": "detail", "evidence": "our morning survey found only about fifteen people interested", "explanation": "Only about fifteen people showed interest.", "choices": [c("About fifteen people were interested", True, "This matches the survey result."), c("Over a hundred people were interested", False, "Interest was much lower."), c("No one responded to the survey", False, "Fifteen people did respond with interest."), c("Only children were interested", False, "The survey concerns adult swimmers.")]},
            {"stem": "Why does Ms. Renner worry about the proposal?", "skill_focus": "inference", "evidence": "sets an expectation that weekend hours should also expand, which would cost even more", "explanation": "She fears it will lead to pressure for costlier weekend expansion.", "choices": [c("It might lead to demands for earlier weekend hours too", True, "This is her stated concern."), c("It would reduce lifeguard safety", False, "Safety is not her stated concern."), c("It would cancel children's swim lessons", False, "Lessons are not said to be cancelled."), c("It would raise everyone's membership fees", False, "Fees are not her stated worry.")]},
            {"stem": "What does Mr. Haddad clarify about his request?", "skill_focus": "detail", "evidence": "This proposal is only about weekdays, though — I'm not asking for earlier weekend hours.", "explanation": "He confirms the request applies only to weekdays.", "choices": [c("It applies only to weekdays", True, "He directly clarifies this."), c("It includes weekends too", False, "He explicitly excludes weekends."), c("It applies only to holidays", False, "Holidays are not mentioned."), c("It requires closing the pool on Sundays", False, "No such closure is proposed.")]},
            {"stem": "What is the cost of the two-day trial?", "skill_focus": "detail", "evidence": "A two-day trial would only cost about twenty-four hundred dollars for three months", "explanation": "The smaller trial costs about twenty-four hundred dollars over three months.", "choices": [c("About twenty-four hundred dollars for three months", True, "This matches Ms. Bianchi's figure."), c("About six thousand dollars for three months", False, "That figure is the full weekday cost estimate."), c("Nothing, since volunteers would staff it", False, "Staffing cost is still involved."), c("About twenty-four hundred dollars per week", False, "The figure covers three months, not one week.")]},
            {"stem": "What is the final decision of the meeting?", "skill_focus": "detail", "evidence": "a three-month Tuesday and Thursday adults-only early swim trial, reviewed at the next quarterly meeting, with no change to weekend hours", "explanation": "A limited weekday trial was approved with a scheduled review.", "choices": [c("A three-month Tuesday/Thursday trial with a review", True, "This matches the motion that carried."), c("Full daily early hours starting immediately", False, "Only a two-day trial was approved."), c("No change to the schedule at all", False, "The motion carried, so a trial begins."), c("Expanded weekend hours", False, "Weekend hours are explicitly unchanged.")]},
        ],
    },
    {
        "slug": "food-trucks-in-parks-debate",
        "task_type": "listening_viewpoints",
        "title": "Should Food Trucks Operate in City Parks?",
        "topic": "Parks and small business policy",
        "difficulty": 2,
        "estimated_level": 8,
        "intro": "A parks department liaison presents a proposal to allow licensed food trucks in city parks on weekends, along with the perspectives that have been gathered.",
        "source_slug": "car-free-shopping-street-debate",
        "instructions": "Listen once to the prepared talk, then answer the six questions about the proposal and the perspectives presented.",
        "transcript": (
            "Liaison: I'm the parks department's community liaison. The city is considering allowing licensed food trucks to operate in three major parks on weekends starting this summer. Today I will explain the proposal and the views we've gathered.\n"
            "The pilot would allow up to four food trucks per park on Saturdays and Sundays, from eleven a.m. to seven p.m., each paying a daily permit fee that funds park maintenance.\n"
            "Food truck operators support the plan. They say park locations reach families who might not otherwise try their food, and the extra revenue from summer weekends is significant for a seasonal business.\n"
            "Nearby restaurant owners are divided. Some worry that food trucks parked just outside their property line will draw away lunch customers who would otherwise dine in. Others note that food trucks tend to bring in visitors who then browse nearby shops afterward.\n"
            "The parks advocate group raises a different concern: increased trash and grease runoff near play areas, and asks that trucks be required to provide their own waste bins and be located at least fifty metres from playgrounds.\n"
            "Weighing these views, my office proposes limiting trucks to three of the six weekend hours during peak family time, requiring each truck to supply its own waste bin, and keeping a fifty-metre buffer from playgrounds, with a review after the first summer season."
        ),
        "speaker_genders": {"Liaison": "female"},
        "questions": [
            {"stem": "What is the central proposal being discussed?", "skill_focus": "gist", "evidence": "allowing licensed food trucks to operate in three major parks on weekends", "explanation": "The proposal is to allow food trucks in parks on weekends.", "choices": [c("Allowing food trucks in city parks on weekends", True, "This is the proposal under discussion."), c("Banning all food sales in parks", False, "The opposite is proposed."), c("Building permanent restaurant buildings in parks", False, "Trucks, not buildings, are proposed."), c("Closing parks on weekends for maintenance", False, "Maintenance is only funded by permit fees, not the reason for closure.")]},
            {"stem": "How many food trucks are allowed per park under the pilot?", "skill_focus": "detail", "evidence": "up to four food trucks per park", "explanation": "The pilot caps each park at four trucks.", "choices": [c("Up to four", True, "This matches the proposal."), c("Up to ten", False, "This is higher than stated."), c("Exactly one", False, "The cap is higher than one."), c("As many as apply", False, "A specific cap of four is set.")]},
            {"stem": "Why do food truck operators support the plan?", "skill_focus": "detail", "evidence": "reach families who might not otherwise try their food, and the extra revenue ... is significant", "explanation": "They gain new customers and important seasonal revenue.", "choices": [c("It reaches new customers and adds revenue", True, "Both benefits are stated."), c("It removes their need for a business licence", False, "Licensing is not addressed this way."), c("It guarantees a fixed daily income", False, "No guaranteed income is mentioned."), c("It lets them avoid paying any fees", False, "A daily permit fee is required.")]},
            {"stem": "Why are some restaurant owners concerned about the proposal?", "skill_focus": "inference", "evidence": "food trucks parked just outside their property line will draw away lunch customers", "explanation": "They fear losing lunch customers to nearby trucks.", "choices": [c("They fear losing lunch customers to nearby trucks", True, "This is their stated worry."), c("They believe food trucks are unsanitary", False, "Sanitation is not raised by restaurant owners."), c("They want to operate food trucks themselves", False, "This is not mentioned."), c("They oppose parks having any vendors historically", False, "No such history is mentioned.")]},
            {"stem": "What safety or cleanliness concern does the parks advocate group raise?", "skill_focus": "detail", "evidence": "increased trash and grease runoff near play areas", "explanation": "They worry about waste and runoff near playgrounds.", "choices": [c("Trash and grease runoff near play areas", True, "This is their stated concern."), c("Noise from food truck generators", False, "Noise is not mentioned."), c("Traffic congestion on nearby streets", False, "Traffic is not mentioned."), c("Food trucks blocking emergency vehicle access", False, "Emergency access is not mentioned.")]},
            {"stem": "What does the compromise require of each truck?", "skill_focus": "detail", "evidence": "requiring each truck to supply its own waste bin ... keeping a fifty-metre buffer from playgrounds", "explanation": "Trucks must supply waste bins and stay away from playgrounds.", "choices": [c("Supply its own waste bin and stay fifty metres from playgrounds", True, "Both conditions are stated."), c("Operate only on weekday mornings", False, "The pilot is for weekends."), c("Donate a portion of profits to the city", False, "No profit-sharing is mentioned."), c("Hire a city-approved security guard", False, "Security staffing is not mentioned.")]},
        ],
    },
]
