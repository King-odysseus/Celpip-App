"""Second variant of full-part Listening simulation sets.

Each set is an entire official Listening part (one continuous original
recording, full official question count) and is a second, distinct scenario
from ``listening_official_parts.py`` so that repeated full-length mocks can
rotate to fresh content. Like the first variant, these are NOT stage-expanded
and are a preferred single-item building block of full-length mocks.
"""
# ruff: noqa: E501


def c(text, correct, explanation):
    return {"text": text, "is_correct": correct, "explanation": explanation}


LISTENING_OFFICIAL_SETS_V2 = [
    {
        "slug": "flooded-market-stall-relocation",
        "task_type": "listening_problem_solving",
        "title": "Relocating the Flooded Market",
        "topic": "Community event logistics",
        "difficulty": 2,
        "estimated_level": 7,
        "instructions": "Listen once to the whole conversation, then answer the eight questions about the market plan.",
        "intro": "Two coordinators of a weekly outdoor farmers' market decide what to do when heavy rain floods their usual riverside site the evening before market day.",
        "transcript": (
            "Dana: The city just texted that the riverside lot is flooded after tonight's storm, so we cannot set up there tomorrow morning. We have eighty vendors booked and the site inspection was scheduled for five a.m.\n"
            "Omar: Can we move to the community centre parking lot? Their lot is paved and higher, and the manager offered it to us last spring as an overflow site.\n"
            "Dana: He did, but the lot holds only sixty stalls, and twenty of our vendors run food trucks that need extra space between them for the health inspection.\n"
            "Omar: Then we split the market. The sixty stall-based vendors go to the centre lot, and we place the food trucks along the park street where the Saturday running race finishes, so they keep the lunch crowd.\n"
            "Dana: The race organizers close that street until one o'clock. If the trucks open at eleven, they get about two hours of runners, which is shorter than their usual service.\n"
            "Omar: Better to run a trimmed market than cancel entirely. Vendors lose a whole week of income if we cancel, and our regulars plan their weekend shopping around us.\n"
            "Dana: Agreed, but we have to message everyone tonight so they can reroute. I will send the new site map and the setup times, and ask each food truck to confirm by nine.\n"
            "Omar: Also confirm the centre lot manager is fine with the stall vendors doing an early load-in at six, before his own tenants arrive.\n"
            "Dana: I will call him now. And I will post the change on our website and social pages so shoppers do not drive to the flooded lot in the morning."
        ),
        "speaker_genders": {"Dana": "female", "Omar": "male"},
        "questions": [
            {"stem": "What problem are the coordinators solving?", "skill_focus": "gist", "evidence": "the riverside lot is flooded ... so we cannot set up there tomorrow", "explanation": "The usual market site is unusable, so they must arrange an alternative.", "choices": [c("Vendors did not pay their stall fees", False, "No payment problem is mentioned."), c("The market site is flooded and cannot be used", True, "The storm forces a change of location."), c("The city cancelled the market permanently", False, "Only tomorrow's site is affected."), c("Too few vendors booked this week", False, "They have eighty vendors booked.")]},
            {"stem": "Why cannot every vendor move to the community centre lot?", "skill_focus": "detail", "evidence": "the lot holds only sixty stalls, and twenty of our vendors run food trucks that need extra space", "explanation": "The lot is too small and the food trucks require spacing for the health inspection.", "choices": [c("The lot is flooded too", False, "The centre lot is paved and higher."), c("It holds only sixty stalls and trucks need extra space", True, "Both limits are stated."), c("The centre charges double the fee", False, "No fee change is mentioned."), c("The lot opens at noon", False, "Opening time is not the issue.")]},
            {"stem": "Where will the food trucks be placed?", "skill_focus": "detail", "evidence": "we place the food trucks along the park street where the Saturday running race finishes", "explanation": "The trucks go on the street by the race finish line.", "choices": [c("In the community centre lot", False, "The lot is for stall vendors."), c("Along the park street by the race finish", True, "This is the chosen location."), c("Back at the flooded riverside lot", False, "That site is unusable."), c("Inside the community centre hall", False, "No indoor placement is mentioned.")]},
            {"stem": "Why will the food trucks have a shorter service day?", "skill_focus": "inference", "evidence": "the race organizers close that street until one o'clock. If the trucks open at eleven, they get about two hours of runners", "explanation": "The street is closed to set up during the race, so trucks open later than usual.", "choices": [c("The street is closed by the race until one", True, "The closure shortens their serving window."), c("The trucks run out of fuel", False, "No fuel issue is mentioned."), c("The vendors arrive late", False, "Arrival time is not the cause."), c("The health inspection takes all day", False, "Inspection only affects spacing.")]},
            {"stem": "Why does Omar prefer a trimmed market over cancelling?", "skill_focus": "inference", "evidence": "Vendors lose a whole week of income if we cancel, and our regulars plan their weekend shopping around us", "explanation": "Cancelling would cost vendors their income and disappoint regular shoppers.", "choices": [c("Vendors would lose a week of income", True, "Income loss is the stated reason."), c("The city fines cancelled markets", False, "No fine is mentioned."), c("The trucks are already hired", False, "Hiring cost is not raised."), c("The weather will improve by noon", False, "Weather is not the deciding factor.")]},
            {"stem": "What must each food truck do by nine?", "skill_focus": "detail", "evidence": "ask each food truck to confirm by nine", "explanation": "Trucks must confirm their participation by nine that night.", "choices": [c("Confirm it will attend the new site", True, "Nine is the confirmation deadline."), c("Pay an extra fee", False, "No extra fee is required."), c("Return its health permit", False, "Permits are not collected."), c("Call the race organizers", False, "The coordinators handle the organizers.")]},
            {"stem": "Why is the six o'clock load-in at the centre lot arranged?", "skill_focus": "detail", "evidence": "fine with the stall vendors doing an early load-in at six, before his own tenants arrive", "explanation": "The early load-in finishes before the centre's own tenants need the lot.", "choices": [c("To finish before the centre's tenants arrive", True, "This is the stated reason."), c("To beat the morning traffic", False, "Traffic is not mentioned."), c("To avoid the health inspector", False, "Inspection is still required."), c("To set up before the race starts", False, "The trucks, not the stalls, are near the race.")]},
            {"stem": "What will Dana post for shoppers?", "skill_focus": "purpose", "evidence": "I will post the change on our website and social pages so shoppers do not drive to the flooded lot", "explanation": "She posts the new location so shoppers know not to go to the old site.", "choices": [c("The new market location", True, "The announcement directs shoppers to the right site."), c("A list of cancelled vendors", False, "No vendors are cancelled."), c("The race results", False, "Results are not her role."), c("The health inspection report", False, "The report is not posted to shoppers.")]},
        ],
    },
    {
        "slug": "borrowing-cargo-bike-airport",
        "task_type": "listening_daily_conversation",
        "title": "Borrowing the Cargo Bike",
        "topic": "Shared errands between friends",
        "difficulty": 1,
        "estimated_level": 5,
        "instructions": "Listen once to the conversation, then answer the five questions about the bike loan.",
        "intro": "Two roommates sort out whether one can borrow the other's electric cargo bike for an early flight to the airport.",
        "transcript": (
            "Alex: Have you decided how you are getting to the airport for your six a.m. flight? The earliest bus does not run until five thirty.\n"
            "Sam: I was hoping to borrow your cargo bike. It has the big front box, so I can carry my suitcase, and the battery should cover the ride.\n"
            "Alex: The range is about forty kilometres, and the airport path is twelve kilometres each way, so you have room to spare. The front box lock is a little sticky, so take my spare key in case it will not open.\n"
            "Sam: Will the battery still last if I carry a loaded suitcase? The manual says a heavy load shortens the range by about a third.\n"
            "Alex: Good point. Charge it fully tonight, and keep the pedal assist on the middle setting to save power. If you run low, there are charging stations at the big junction halfway.\n"
            "Sam: I will return the bike by noon so you can still use it for your afternoon ride. Thanks for lending it."
        ),
        "speaker_genders": {"Alex": "female", "Sam": "male"},
        "questions": [
            {"stem": "Why does Sam want to borrow the cargo bike?", "skill_focus": "gist", "evidence": "I was hoping to borrow your cargo bike ... carry my suitcase ... cover the ride", "explanation": "Sam needs a way to reach the airport early with his suitcase.", "choices": [c("To practice riding to work", False, "The trip is to the airport."), c("To carry a suitcase to the airport", True, "The big front box fits the suitcase."), c("To test the battery for Alex", False, "He is not testing it."), c("To deliver groceries", False, "No groceries are mentioned.")]},
            {"stem": "Why can Sam not take the bus?", "skill_focus": "detail", "evidence": "The earliest bus does not run until five thirty", "explanation": "The first bus is too late for a six a.m. flight.", "choices": [c("The bus fare is too high", False, "Fare is not mentioned."), c("The earliest bus runs at five thirty", True, "That is too late to make the flight."), c("The bus does not go to the airport", False, "It is a timing problem, not a route problem."), c("The bus is full", False, "No crowding is mentioned.")]},
            {"stem": "Why does Sam worry about the battery?", "skill_focus": "detail", "evidence": "a heavy load shortens the range by about a third", "explanation": "The manual warns that weight reduces how far the battery lasts.", "choices": [c("The battery is old", False, "Age is not mentioned."), c("A heavy load shortens the range", True, "The manual states this."), c("The charger is broken", False, "Charging works fine."), c("The ride is uphill", False, "No hills are mentioned.")]},
            {"stem": "What does Alex advise if Sam runs low on power?", "skill_focus": "detail", "evidence": "there are charging stations at the big junction halfway", "explanation": "Charging stations sit halfway along the route.", "choices": [c("Call for a pickup", False, "No pickup plan is given."), c("Use the charging stations at the halfway junction", True, "This is the stated fallback."), c("Take the next bus", False, "The bus problem was the timing."), c("Pedal without power the whole way", False, "The middle setting is advised, not no power.")]},
            {"stem": "What does Sam promise about returning the bike?", "skill_focus": "detail", "evidence": "I will return the bike by noon so you can still use it for your afternoon ride", "explanation": "Sam will have the bike back by noon for Alex's own ride.", "choices": [c("Return it by noon", True, "Noon is the promised return time."), c("Return it the next day", False, "He returns it the same day."), c("Fill the battery at home", False, "Charging is mentioned but not as a promise."), c("Buy a new lock", False, "He takes a spare key instead.")]},
        ],
    },
    {
        "slug": "pool-lesson-registration-message",
        "task_type": "listening_information",
        "title": "Pool Lesson Registration Message",
        "topic": "Recreation program changes",
        "difficulty": 2,
        "estimated_level": 6,
        "instructions": "Listen once to the recorded message, then answer the six questions about the changes it announces.",
        "intro": "A recorded message from a community pool's aquatics office explains how lesson registration is moving online and announces summer hiring.",
        "transcript": (
            "Maya: Hello, this is a recorded message from the Maple Leaf Pool aquatics office. We are changing how you register for our spring swimming lessons.\n"
            "Starting Monday, March ninth, all lesson bookings move to the new online portal at mapleleafpool dot ca slash lessons, and the front desk will no longer take lesson registrations by phone.\n"
            "If you are a returning family, log in with the email address we have on file and check the box to keep your lesson day and time from last term.\n"
            "The office will email a confirmation within one business day, and you have seven days to pay the lesson fee or your spot is released.\n"
            "We are also hiring lifeguards for the summer. Candidates must be at least sixteen, hold a current Bronze Cross award, and attend a free orientation on Saturday March fifteenth at ten in the morning.\n"
            "Please bring a resume and a government photo ID to the orientation. Returning guards do not need to reapply, but they must update their contact details in the staff portal.\n"
            "Finally, on Family Day weekend, admission is free for grandparents when they bring a member, and the café is offering a discount on hot chocolate."
        ),
        "speaker_genders": {"Maya": "female"},
        "questions": [
            {"stem": "What is the main purpose of the message?", "skill_focus": "gist", "evidence": "We are changing how you register for our spring swimming lessons ... also hiring lifeguards", "explanation": "The message announces the new online registration process and summer hiring.", "choices": [c("To cancel all swimming lessons", False, "Lessons continue, only registration changes."), c("To announce online registration and summer hiring", True, "These are the two topics."), c("To raise the pool membership fee", False, "No membership fee change is mentioned."), c("To close the pool for repair", False, "No closure is announced.")]},
            {"stem": "How will lesson registration work starting March 9?", "skill_focus": "detail", "evidence": "all lesson bookings move to the new online portal", "explanation": "Registrations go through the online portal from that date.", "choices": [c("By phone at the front desk", False, "Phone registration is being discontinued."), c("Through a new online portal", True, "This is the stated change."), c("By mail to the office", False, "Mail is not mentioned."), c("In person only on Saturdays", False, "No in-person-only rule is stated.")]},
            {"stem": "What must a returning family do to keep its usual lesson time?", "skill_focus": "detail", "evidence": "check the box to keep your lesson day and time from last term", "explanation": "Returning families select the option to carry over their previous slot.", "choices": [c("Call the front desk", False, "Phone registration is ending."), c("Log in and check the keep-your-slot box", True, "This is the required step."), c("Pay a higher fee", False, "No extra fee is mentioned."), c("Attend a new orientation", False, "Orientation is for lifeguard candidates.")]},
            {"stem": "How long does a family have to pay the lesson fee?", "skill_focus": "detail", "evidence": "you have seven days to pay the lesson fee or your spot is released", "explanation": "Payment is due within seven days of the confirmation.", "choices": [c("Seven days", True, "The spot is released after seven days."), c("One business day", False, "The confirmation comes within a business day."), c("Two weeks", False, "That is longer than stated."), c("Until the term starts", False, "Payment is due sooner.")]},
            {"stem": "What must a new lifeguard candidate bring to the orientation?", "skill_focus": "detail", "evidence": "bring a resume and a government photo ID to the orientation", "explanation": "Both documents are required at the orientation.", "choices": [c("A resume and a government photo ID", True, "Both are listed."), c("A first-aid certificate", False, "A first-aid award is not requested."), c("A reference letter", False, "No letter is mentioned."), c("A swimsuit", False, "No clothing item is specified.")]},
            {"stem": "Who receives free admission on Family Day weekend?", "skill_focus": "detail", "evidence": "admission is free for grandparents when they bring a member", "explanation": "The offer is for grandparents accompanied by a member.", "choices": [c("All children", False, "Children are not named."), c("Grandparents who bring a member", True, "This is the stated offer."), c("Anyone over sixty-five", False, "Age alone does not qualify."), c("Lifeguard candidates", False, "The offer is separate from hiring.")]},
        ],
    },
    {
        "slug": "harbour-commuter-ferry-launch",
        "task_type": "listening_news",
        "title": "Harbour Commuter Ferry Launch",
        "topic": "Public transit news",
        "difficulty": 2,
        "estimated_level": 6,
        "instructions": "Listen once to the news report, then answer the five questions about the new ferry route.",
        "intro": "A short local news report announces a new commuter ferry connecting the harbour to the downtown terminal.",
        "transcript": (
            "Leah: A new commuter ferry will begin running between the harbour and the downtown terminal on April sixth, cutting the crossing from thirty-five minutes to about twelve.\n"
            "The service will run every twenty minutes during weekday rush hours and every forty minutes at other times, and the ferry fare will match the bus fare for the first three months.\n"
            "The transit authority bought two used vessels for the route at a discount, but a councillor warned that the old terminals need about a million dollars in upgrades before they can handle the higher passenger flow.\n"
            "Riders will tap the same transit card used on the buses, and bicycles are allowed on board only outside rush hours.\n"
            "Construction at the downtown terminal will close one platform lane until the end of May, so the authority asks commuters to allow an extra ten minutes during the first weeks."
        ),
        "speaker_genders": {"Leah": "female"},
        "questions": [
            {"stem": "What is the main announcement?", "skill_focus": "gist", "evidence": "A new commuter ferry will begin running between the harbour and the downtown terminal", "explanation": "The report announces a new ferry route and its details.", "choices": [c("The harbour is closing", False, "No closure is announced."), c("A new commuter ferry route is starting", True, "This is the central news."), c("Bus fares are rising", False, "The ferry matches the bus fare."), c("The downtown terminal is closing", False, "Only one lane closes during construction.")]},
            {"stem": "How long will the crossing take on the new ferry?", "skill_focus": "detail", "evidence": "cutting the crossing from thirty-five minutes to about twelve", "explanation": "The trip drops to roughly twelve minutes.", "choices": [c("Twelve minutes", True, "This is the new crossing time."), c("Twenty minutes", False, "Twenty is the rush-hour frequency."), c("Thirty-five minutes", False, "That was the old crossing time."), c("Forty minutes", False, "Forty is the off-peak frequency.")]},
            {"stem": "How often does the ferry run during weekday rush hours?", "skill_focus": "detail", "evidence": "run every twenty minutes during weekday rush hours", "explanation": "Rush-hour service is every twenty minutes.", "choices": [c("Every ten minutes", False, "That is not the stated interval."), c("Every twenty minutes", True, "This matches the report."), c("Every thirty minutes", False, "The interval is twenty."), c("Every forty minutes", False, "Forty is the off-peak interval.")]},
            {"stem": "Why does the councillor warn about the terminals?", "skill_focus": "detail", "evidence": "the old terminals need about a million dollars in upgrades before they can handle the higher passenger flow", "explanation": "The terminals need upgrades to cope with more passengers.", "choices": [c("They need a million dollars in upgrades for passenger flow", True, "Capacity is the concern."), c("They are too far from the bus stops", False, "Location is not mentioned."), c("They cannot dock used vessels", False, "The vessels were bought at a discount."), c("They close at the end of May", False, "A platform lane closes, not the terminal.")]},
            {"stem": "When are bicycles allowed on the ferry?", "skill_focus": "detail", "evidence": "bicycles are allowed on board only outside rush hours", "explanation": "Bikes ride free of restriction only off-peak.", "choices": [c("Only outside rush hours", True, "Rush hours exclude bikes."), c("At any time", False, "There is a restriction."), c("Only on weekends", False, "Weekends are not named."), c("Never", False, "Bikes are allowed outside rush hours.")]},
        ],
    },
    {
        "slug": "extended-library-hours-debate",
        "task_type": "listening_discussion",
        "title": "Should the Library Stay Open Late?",
        "topic": "Public services and budget",
        "difficulty": 3,
        "estimated_level": 8,
        "instructions": "Listen once to the whole discussion, then answer the eight questions about the extended-hours plan.",
        "intro": "A library director and a city finance analyst weigh the costs and benefits of keeping two branches open until ten on weeknights.",
        "transcript": (
            "Julia: The survey we ran shows nearly a third of our members would use an evening opening, mostly students and shift workers who cannot come during the day.\n"
            "Marcus: Extending four weeknights until ten adds heating, lighting, and staffing for about two thousand extra hours a year. At current rates that is close to ninety thousand dollars.\n"
            "Julia: We could cut costs by moving some day staff to the evening instead of hiring new people, and volunteers already cover the welcome desk on weekends.\n"
            "Marcus: Volunteers cannot handle closing duties such as locking up and managing cash, so we still need paid evening supervisors on every night we stay open late.\n"
            "Julia: True. What about the branch that closes for renovation this fall? If we pilot the late hours at the other two branches first, we can test demand before spending on the busiest one.\n"
            "Marcus: A pilot is sensible, but if it runs only in summer, student traffic will look artificially high and could mislead the numbers.\n"
            "Julia: Then run the pilot from September through November to cover the school term, and compare usage against the same months last year.\n"
            "Marcus: Agreed. I will draft the budget note with the two-branch pilot cost and a decision point in December, and you can take it to the board next month."
        ),
        "speaker_genders": {"Julia": "female", "Marcus": "male"},
        "questions": [
            {"stem": "What are the speakers mainly deciding?", "skill_focus": "gist", "evidence": "If we pilot the late hours ... test demand before spending", "explanation": "They are weighing the cost of evening hours against how to test real demand.", "choices": [c("Whether to close a branch for renovation", False, "The renovation is only background."), c("How to offer late evening hours affordably", True, "Cost and a demand pilot organize the talk."), c("Which books to buy", False, "No book purchases are discussed."), c("How to hire more volunteers", False, "Volunteers are limited to the welcome desk.")]},
            {"stem": "Who does the survey say would use the evening hours?", "skill_focus": "detail", "evidence": "mostly students and shift workers who cannot come during the day", "explanation": "Students and shift workers are the main interested groups.", "choices": [c("Students and shift workers", True, "Both groups are named."), c("Retired residents only", False, "Retirees are not singled out."), c("Families with young children", False, "No family group is named."), c("Tourists", False, "Tourists are not mentioned.")]},
            {"stem": "About how much would the extended hours cost each year?", "skill_focus": "detail", "evidence": "about two thousand extra hours a year ... close to ninety thousand dollars", "explanation": "The added hours come to nearly ninety thousand dollars.", "choices": [c("Nine thousand dollars", False, "That is one-tenth of the estimate."), c("Ninety thousand dollars", True, "This matches the estimate."), c("Two hundred thousand dollars", False, "That is more than double."), c("One million dollars", False, "A million is not the library figure.")]},
            {"stem": "Why can volunteers not replace paid staff in the evening?", "skill_focus": "inference", "evidence": "Volunteers cannot handle closing duties such as locking up and managing cash", "explanation": "Closing procedures require responsibilities volunteers do not cover.", "choices": [c("Volunteers are not trained to close and handle cash", True, "These duties need paid supervisors."), c("Volunteers work only on weekends", False, "Volunteers already do weekend welcome shifts."), c("The library is closed to volunteers", False, "No such rule is stated."), c("Volunteers cost more", False, "Volunteers are unpaid.")]},
            {"stem": "Why does Marcus worry about a summer-only pilot?", "skill_focus": "inference", "evidence": "if it runs only in summer, student traffic will look artificially high", "explanation": "Summer student visits would overstate how popular the hours are.", "choices": [c("Summer numbers would not reflect the school year", True, "Student traffic peaks in summer and misleads."), c("The library is closed in summer", False, "The library stays open."), c("Staff take holidays in summer", False, "Staffing is not the concern."), c("The survey was done in winter", False, "Survey timing is not discussed.")]},
            {"stem": "When will the pilot run?", "skill_focus": "detail", "evidence": "run the pilot from September through November to cover the school term", "explanation": "The pilot spans the autumn school term.", "choices": [c("June through August", False, "A summer pilot was rejected."), c("September through November", True, "This is the chosen window."), c("December through February", False, "That is not the window."), c("All year long", False, "The pilot is limited.")]},
            {"stem": "What will the pilot's usage be compared against?", "skill_focus": "detail", "evidence": "compare usage against the same months last year", "explanation": "Marcus wants the pilot measured against the prior year's months.", "choices": [c("The same months last year", True, "This is the baseline."), c("The busiest branch", False, "The pilot excludes the busiest branch."), c("The summer numbers", False, "Summer is the misleading season."), c("Other cities' libraries", False, "No external comparison is mentioned.")]},
            {"stem": "What will Marcus draft for the board?", "skill_focus": "purpose", "evidence": "I will draft the budget note with the two-branch pilot cost and a decision point in December", "explanation": "He prepares the budget note that sets a December decision.", "choices": [c("A budget note with a December decision point", True, "This is the deliverable."), c("A new staffing schedule", False, "Staffing is only discussed, not drafted."), c("A renovation plan", False, "Renovation is background."), c("A survey questionnaire", False, "The survey already exists.")]},
        ],
    },
    {
        "slug": "plastic-bag-ban-debate",
        "task_type": "listening_viewpoints",
        "title": "Should Stores Ban Plastic Bags?",
        "topic": "Environment and cost of living",
        "difficulty": 2,
        "estimated_level": 7,
        "instructions": "Listen once to the conversation, then answer the six questions about the two viewpoints.",
        "intro": "Two residents give opposing views on a proposed ban on single-use plastic bags at local shops.",
        "transcript": (
            "Nina: I support a ban. Plastic bags end up as litter along the river and in the recycling stream, and most shoppers already carry reusable bags, so the change would not be a big inconvenience.\n"
            "Paul: I am not convinced. The affordable option for many customers is the free plastic bag, and a ban usually means paying about fifty cents for a paper one, which adds up for people on tight budgets.\n"
            "Nina: Stores can offer a small discount when you bring your own bag, and that rewards people without charging anyone. Several nearby towns do this and it works well.\n"
            "Paul: The discount only helps shoppers who can plan ahead. People buying on the way home from work or in an emergency do not carry a reusable bag, and they end up paying more.\n"
            "Nina: Then stores should keep cheap paper bags available and use the fee to fund free bag stations for food banks and community kitchens that serve people in need.\n"
            "Paul: I could accept a compromise that focuses on the worst litter first, like banning bags only along the riverfront, and reviewing the effect on prices before any wider ban."
        ),
        "speaker_genders": {"Nina": "female", "Paul": "male"},
        "questions": [
            {"stem": "What is the speakers' main disagreement?", "skill_focus": "gist", "evidence": "Nina weighs litter and convenience; Paul weighs cost for customers on tight budgets.", "explanation": "They disagree about whether the environmental gain justifies the cost the ban may put on shoppers.", "choices": [c("Whether paper bags are stronger", False, "Strength is not discussed."), c("Whether a plastic-bag ban is worth its effect on shoppers", True, "Each weighs a different outcome."), c("Whether stores should stay open late", False, "Store hours are not discussed."), c("Whether rivers need cleaning", False, "The river is only Nina's example.")]},
            {"stem": "Why does Nina support the ban?", "skill_focus": "detail", "evidence": "Plastic bags end up as litter along the river and in the recycling stream", "explanation": "She cites litter and recycling problems from the bags.", "choices": [c("Bags are cheap for stores", False, "Cost to stores is not her point."), c("Bags become litter and clog recycling", True, "Both effects are stated."), c("Plastic is expensive", False, "Price is not raised."), c("Most bags are already banned", False, "The ban is only proposed.")]},
            {"stem": "Why does Paul oppose the ban?", "skill_focus": "detail", "evidence": "a ban usually means paying about fifty cents for a paper one, which adds up for people on tight budgets", "explanation": "Paul fears the cost of paid paper bags for budget-conscious shoppers.", "choices": [c("It would raise costs for people on tight budgets", True, "The fifty-cent paper bag is his example."), c("Paper bags hurt the environment more", False, "He does not compare materials."), c("He owns a plastic-bag factory", False, "No business interest is mentioned."), c("Stores would lose money", False, "Store profit is not his concern.")]},
            {"stem": "What does Nina propose instead of a fee?", "skill_focus": "detail", "evidence": "Stores can offer a small discount when you bring your own bag", "explanation": "She suggests rewarding shoppers who bring reusable bags.", "choices": [c("A discount for bringing your own bag", True, "This is her alternative."), c("A deposit on every bag", False, "No deposit plan is given."), c("Free paper bags for everyone", False, "She keeps paper bags as a separate idea."), c("A charge for reusable bags", False, "Reusables are encouraged, not charged.")]},
            {"stem": "Why does Paul think the discount is unfair?", "skill_focus": "inference", "evidence": "People buying on the way home from work or in an emergency do not carry a reusable bag", "explanation": "Shoppers who do not plan ahead cannot earn the discount.", "choices": [c("It only helps shoppers who plan ahead", True, "Unplanned shoppers still pay more."), c("It raises the price of food", False, "Food prices are not discussed."), c("It rewards the wrong stores", False, "Store choice is not the issue."), c("It does not work in other towns", False, "Nina says nearby towns do it well.")]},
            {"stem": "What compromise does Paul offer?", "skill_focus": "detail", "evidence": "banning bags only along the riverfront, and reviewing the effect on prices before any wider ban", "explanation": "He would start with the riverfront and study price effects first.", "choices": [c("Ban bags only along the riverfront first", True, "A limited start is his compromise."), c("Ban all plastic immediately", False, "He opposes a wide ban."), c("Ban paper bags instead", False, "He does not propose banning paper."), c("Charge for reusable bags", False, "That is not proposed.")]},
        ],
    },
]
