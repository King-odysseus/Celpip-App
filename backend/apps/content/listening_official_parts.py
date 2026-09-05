"""Full-part Listening simulation sets.

Each set below is an entire official Listening part: one continuous original
recording whose question count matches the current CELPIP-General official count
for its task family (Problem Solving 8, Daily Conversation 5, Information 6,
News 5, Discussion 8, Viewpoints 6). They are deliberately NOT stage-expanded
and are the preferred building block of full-length mocks, so a mock part is a
single conversation/passage rather than several unrelated short sets spliced
together.
"""
# ruff: noqa: E501


def c(text, correct, explanation):
    return {"text": text, "is_correct": correct, "explanation": explanation}


LISTENING_OFFICIAL_SETS = [
    {
        "slug": "weekend-market-produce-shortage",
        "task_type": "listening_problem_solving",
        "title": "The Missing Produce Order",
        "topic": "Small business logistics",
        "difficulty": 2,
        "estimated_level": 7,
        "instructions": "Listen once to the whole conversation, then answer the eight questions about how the owners solve the problem.",
        "intro": "Two co-owners of a small market-and-café business work out what to do when a produce delivery falls through before their busiest weekend.",
        "transcript": (
            "Priya: The produce distributor just emailed that their main truck broke down and the load cannot reach us before Tuesday. We have the market stall and the café kitchen to run all weekend, and the cold room is nearly empty.\n"
            "Tom: How much are we actually short? We ordered twelve crates of vegetables for the weekend.\n"
            "Priya: They delivered only three. The rest is sitting in a depot two towns away until they can arrange transport.\n"
            "Tom: Can they put the rest onto a smaller van and meet us partway this afternoon? The market sets up at dawn Saturday.\n"
            "Priya: They said a smaller van could leave by early afternoon, but it can only carry half of what we ordered.\n"
            "Tom: Half is better than nothing, but the café kitchen planned its weekend brunch menu around those vegetables. We cannot let the kitchen run short.\n"
            "Priya: Then let's split the smaller van between the two sides as well: two crates for the market, the remainder for the café. And we top the market back up from the backup wholesaler we used during the spring flood.\n"
            "Tom: The backup wholesaler charges more and packs smaller boxes, so our market margin would nearly disappear on those extra crates.\n"
            "Priya: Keeping the stall open protects the regulars we promised fresh greens, and skipping a whole market day costs us our standing more than a thinner margin for one weekend.\n"
            "Tom: Fair. Before I call the backup, check whether the café can switch Friday's soup to a root-vegetable recipe from the freezer stock we already have.\n"
            "Priya: We froze carrots and parsnips last month. That covers Friday lunch without touching any fresh delivery.\n"
            "Tom: Perfect. Then the whole smaller-van load can be reserved for market crates, and the café can manage on its own until Tuesday.\n"
            "Priya: I will also ask the distributor for a credit on the missing crates, since they invoiced us for the full order up front.\n"
            "Tom: Good, and get that request in writing. If the backup does deliver, confirm we are only billed for what actually arrives this time."
        ),
        "speaker_genders": {"Priya": "female", "Tom": "male"},
        "questions": [
            {"stem": "Why will the produce order be late?", "skill_focus": "detail", "evidence": "the distributor's main truck broke down", "explanation": "The truck breakdown stopped the delivery until Tuesday.", "choices": [c("The distributor's truck broke down", True, "This is the stated cause."), c("The order was cancelled by mistake", False, "The order was not cancelled."), c("The market stall closed early", False, "The stall still opens Saturday."), c("The cold room is too small", False, "The cold room is empty but not broken.")]},
            {"stem": "How much of the original order actually arrived?", "skill_focus": "detail", "evidence": "They delivered only three [of twelve] crates.", "explanation": "Three of the twelve ordered crates were delivered.", "choices": [c("Three crates", True, "Only three crates arrived."), c("Six crates", False, "Six is the smaller van's capacity."), c("Twelve crates", False, "That is the full order."), c("Two crates", False, "Two crates is part of their split plan.")]},
            {"stem": "What does Tom suggest about Friday's lunch service?", "skill_focus": "inference", "evidence": "check whether the café can switch Friday's soup to a root-vegetable recipe from the freezer stock we already have", "explanation": "Tom proposes using frozen root vegetables so the café does not depend on the fresh order.", "choices": [c("Use frozen vegetables for the soup", True, "Freezer stock would cover Friday lunch."), c("Close the café on Friday", False, "Closing is never suggested."), c("Order soup from a competitor", False, "No outside order is mentioned."), c("Delay the menu until Tuesday", False, "The kitchen still runs before Tuesday.")]},
            {"stem": "Why does Priya worry about losing a day at the market?", "skill_focus": "inference", "evidence": "skipping a whole market day costs us our standing", "explanation": "Priya believes regulars rely on the stall and a missed day damages their reputation.", "choices": [c("Regular customers expect the stall to be open", True, "She fears losing standing with regulars."), c("The stall owes money to the city", False, "No fees or debts are mentioned."), c("Their permit expires this weekend", False, "Permits are not discussed."), c("The backup cannot deliver on time", False, "The backup can deliver this weekend.")]},
            {"stem": "What was the backup wholesaler used for before?", "skill_focus": "detail", "evidence": "the backup wholesaler we used during the spring flood", "explanation": "They last used the backup wholesaler during the spring flood.", "choices": [c("Spring flood supplies", True, "The flood is the prior occasion named."), c("Winter holiday orders", False, "Winter is not mentioned."), c("A farmers' market closure", False, "No market closure is described."), c("The café's grand opening", False, "The opening is not discussed.")]},
            {"stem": "What is Tom's main objection to the backup wholesaler?", "skill_focus": "detail", "evidence": "The backup wholesaler charges more and packs smaller boxes, so our market margin would nearly disappear", "explanation": "Higher prices and smaller boxes would shrink their profit on those crates.", "choices": [c("It charges more for smaller boxes", True, "Both points erode the margin."), c("It cannot deliver on Saturdays", False, "Delivery timing is not its drawback."), c("Its vegetables are poor quality", False, "Quality is never questioned."), c("It is too far away", False, "Distance is not raised.")]},
            {"stem": "How will the smaller-van delivery be divided in the final plan?", "skill_focus": "detail", "evidence": "the whole smaller-van load can be reserved for market crates", "explanation": "Once the café uses freezer stock, the van load goes entirely to the market.", "choices": [c("Entirely to the market stall", True, "The café will rely on freezer stock."), c("Half to each side", False, "That was the earlier, abandoned split."), c("Mostly to the café kitchen", False, "The café is covered by the freezer."), c("Only to the café", False, "The café is not the destination.")]},
            {"stem": "What does Priya plan to request from the distributor?", "skill_focus": "purpose", "evidence": "ask the distributor for a credit on the missing crates, since they invoiced us for the full order", "explanation": "They were billed for the full order, so she wants a credit for what never arrived.", "choices": [c("A refund or credit for the missing crates", True, "She wants the invoice corrected."), c("A bigger delivery next week", False, "Next week's size is not discussed."), c("A loaner truck", False, "They do not ask for a truck."), c("A discount on frozen stock", False, "Frozen stock is their own.")]},
        ],
    },
    {
        "slug": "helping-maya-move-sunday",
        "task_type": "listening_daily_conversation",
        "title": "Helping Maya Move",
        "topic": "Neighbours helping out",
        "difficulty": 1,
        "estimated_level": 5,
        "instructions": "Listen once to the conversation, then answer the five questions about the moving plan.",
        "intro": "Two friends sort out the details of helping their neighbour Maya move apartments this Sunday.",
        "transcript": (
            "Evan: Did Maya confirm the move for Sunday? She texted that the elevator in her new building is booked for nine, so we need to start loading early.\n"
            "Leila: Yes, nine works. But her brother who was going to drive the truck texted that his van is being repaired, so we have no vehicle for the furniture.\n"
            "Evan: I can rent a small moving truck tonight and return it Sunday evening. Maya offered to split the rental cost, and I checked—a basic van is cheaper than a full-size truck.\n"
            "Leila: A basic van might not fit her sofa. I remember it is the long one she brought from her parents' place.\n"
            "Evan: Good point. Let me book the full-size truck instead, and we can ask whether the rental company includes a furniture dolly.\n"
            "Leila: They usually do, but I will bring my own hand truck just in case, since the hallway is narrow and the boxes are heavy.\n"
            "Evan: Also, Maya said the new elevator can only be used for moves between nine and one, so we should finish the big items by then.\n"
            "Leila: Then we should start at eight instead of nine to be safe, and Maya can meet the building manager at the new place at eight thirty to unlock the move route.\n"
            "Evan: Let me call her and set the earlier time, and I will confirm the truck. We can pick up coffee on the way for everyone.\n"
            "Leila: Perfect. I will text the others and ask them to be at Maya's old place by eight."
        ),
        "speaker_genders": {"Evan": "male", "Leila": "female"},
        "questions": [
            {"stem": "Why was the original start time changed to eight?", "skill_focus": "inference", "evidence": "the new elevator can only be used for moves between nine and one, so we should finish the big items by then", "explanation": "Starting at eight gives them time to move the large items before the elevator stops being available at one.", "choices": [c("The elevator is reserved only until the afternoon", True, "The nine-to-one limit forces an earlier start."), c("The truck is only available in the morning", False, "The truck is rented for the whole day."), c("Maya must leave by noon", False, "Maya is not leaving that day."), c("The building closes at eight", False, "The building does not close.")]},
            {"stem": "Why does Leila want to check the size of the rented truck?", "skill_focus": "detail", "evidence": "A basic van might not fit her sofa. I remember it is the long one", "explanation": "The sofa is long, so Leila doubts a basic van can carry it.", "choices": [c("Maya's sofa is very long", True, "The long sofa may not fit a basic van."), c("The truck driver is inexperienced", False, "Driving ability is not discussed."), c("Fuel is expensive for large trucks", False, "Fuel cost is never raised."), c("The building has a low garage", False, "Garage height is not mentioned.")]},
            {"stem": "What will Leila bring in case the rental company has no dolly?", "skill_focus": "detail", "evidence": "I will bring my own hand truck just in case", "explanation": "Leila plans to bring her own hand truck as a backup.", "choices": [c("Her own hand truck", True, "She brings it just in case."), c("Extra packing boxes", False, "Boxes are not her job."), c("A tool kit", False, "Tools are not mentioned."), c("Her car keys", False, "She will not drive that day.")]},
            {"stem": "Why does the furniture need to be moved before one o'clock?", "skill_focus": "detail", "evidence": "the new elevator can only be used for moves between nine and one", "explanation": "The building limits move access to that window.", "choices": [c("The elevator is only for moves until one", True, "The move window ends at one."), c("Maya's lease begins at one", False, "Her lease start is not stated."), c("The new tenants arrive at one", False, "No new tenants are mentioned."), c("The truck must be returned at one", False, "The truck is returned Sunday evening.")]},
            {"stem": "What will Maya do at eight thirty?", "skill_focus": "detail", "evidence": "Maya can meet the building manager at the new place at eight thirty to unlock the move route", "explanation": "She meets the manager so the move route can be opened.", "choices": [c("Meet the building manager", True, "She unlocks the move route with the manager."), c("Return the rented truck", False, "Evan returns the truck later."), c("Buy coffee for the group", False, "Evan suggests buying coffee on the way."), c("Book the elevator", False, "The elevator was already booked for nine.")]},
        ],
    },
    {
        "slug": "library-summer-reading-program",
        "task_type": "listening_information",
        "title": "Summer Reading Program Kickoff",
        "topic": "Community library programs",
        "difficulty": 1,
        "estimated_level": 6,
        "instructions": "Listen once to the librarian's announcement, then answer the six questions about the program details.",
        "intro": "A branch librarian explains the details of the library's summer reading program for children and families.",
        "transcript": (
            "Librarian: Good morning, everyone, and welcome to the kickoff for this year's Summer Reading program. The program is free for children aged four to twelve and runs for eight weeks, from the first Monday of July until the last Saturday of August.\n"
            "Registration opens online tomorrow at nine, and you can also sign up in person at the front desk from Saturday. Please register your child yourself rather than having them register alone, because we need a parent or guardian to agree to the photo permission form.\n"
            "Each child receives a reading log. For every five books they finish, they earn a stamp, and six stamps win a prize from our treasure box. Audiobooks count toward the total, but eBooks and graphic novels count as well, as long as the child records the title in the log.\n"
            "We also run free story time every Wednesday morning in the children's corner, and a weekly craft activity on Fridays. These sessions are first come, first served, so arrive ten minutes early to take a spot.\n"
            "Please note two rules. First, bring the reading log to the desk each time you collect a stamp; we cannot add stamps without it. Second, prizes must be collected by the end of September, or the points simply expire.\n"
            "Teens aged thirteen to seventeen can volunteer as reading buddies, and they will receive a certificate of community service hours at the end of the summer. If your older child is interested, they should talk to me after the announcement.\n"
            "Finally, if you have any questions, email the children's desk or call the library between ten and six on weekdays. We look forward to a great summer of reading!"
        ),
        "speaker_genders": {"Librarian": "female"},
        "questions": [
            {"stem": "What must a parent do when registering a child?", "skill_focus": "purpose", "evidence": "we need a parent or guardian to agree to the photo permission form", "explanation": "The form requires a parent or guardian's consent.", "choices": [c("Agree to the photo permission form", True, "Parental consent is required."), c("Pay a registration fee", False, "The program is free."), c("Buy a reading log", False, "Logs are provided."), c("Choose a prize in advance", False, "Prizes are earned later.")]},
            {"stem": "Which items count toward a child's reading total?", "skill_focus": "detail", "evidence": "Audiobooks count toward the total, but eBooks and graphic novels count as well", "explanation": "Audiobooks, eBooks, and graphic novels all count when recorded.", "choices": [c("Audiobooks and graphic novels", True, "All three formats count."), c("Only printed books", False, "Printed books are not the only format."), c("Only chapter books", False, "No chapter-length rule is given."), c("Newspapers and magazines", False, "Periodicals are not mentioned.")]},
            {"stem": "How does a child earn a prize?", "skill_focus": "detail", "evidence": "six stamps win a prize from our treasure box", "explanation": "Six stamps, earned for reading books, win a prize.", "choices": [c("By collecting six stamps", True, "Six stamps earn a treasure-box prize."), c("By attending story time", False, "Story time is separate."), c("By volunteering as a buddy", False, "Volunteering gives teens a certificate."), c("By registering online first", False, "Registration is a requirement, not a prize.")]},
            {"stem": "Why should families arrive early for the craft activity?", "skill_focus": "inference", "evidence": "These sessions are first come, first served, so arrive ten minutes early to take a spot", "explanation": "Places are limited and given in arrival order.", "choices": [c("Spaces are limited", True, "First come, first served means early arrival matters."), c("The craft costs extra", False, "The sessions are free."), c("Parents must sign a form", False, "The form is for registration only."), c("The library closes at noon", False, "Closing time is not stated.")]},
            {"stem": "What happens to stamps that are not redeemed for prizes in time?", "skill_focus": "detail", "evidence": "prizes must be collected by the end of September, or the points simply expire", "explanation": "Unredeemed points expire after September.", "choices": [c("The points expire", True, "Unused points are lost after September."), c("They carry into next summer", False, "They do not roll over."), c("They become donation points", False, "No donation conversion is mentioned."), c("They are refunded as money", False, "There is no refund.")]},
            {"stem": "What do teen volunteers receive?", "skill_focus": "detail", "evidence": "they will receive a certificate of community service hours", "explanation": "Teen reading buddies earn a community-service certificate.", "choices": [c("A community service certificate", True, "This is what the teens receive."), c("A cash payment", False, "Volunteering is unpaid."), c("Free library cards", False, "Library cards are not part of the reward."), c("A treasure-box prize", False, "Prizes are for child readers.")]},
        ],
    },
    {
        "slug": "bike-library-launch-news",
        "task_type": "listening_news",
        "title": "Community Bike Library Launches",
        "topic": "Community news",
        "difficulty": 2,
        "estimated_level": 6,
        "instructions": "Listen once to the news report, then answer the five questions about the story.",
        "intro": "A newsreader reports on the opening of a lending program for bicycles.",
        "transcript": (
            "Newsreader: Residents can now borrow bicycles the way they borrow library books, as the city's first community bike library opened this morning in Riverside Plaza.\n"
            "The pilot fleet of sixty bikes was collected through a spring donation drive and repaired by volunteers at the neighbourhood workshop. Anyone with a valid library card can borrow a bike free of charge for up to three days, and helmets are included with every rental.\n"
            "Organizers say the program is meant for short trips and errands rather than long tours, and they ask borrowers to return bikes with the batteries charged if they took an electric model. A small number of electric bikes were added after a local charity donated funds for them.\n"
            "The plaza location will operate from seven in the morning until nine at night during the summer. City staff will staff a repair stand on weekends to keep the fleet rideable.\n"
            "The program's coordinator, Dana Whitfield, said the launch exceeded expectations, with more than two hundred people already on the waitlist for popular models. If demand holds, the city plans to open two more locations, in the east and north ends, before the fall.\n"
            "For now, bikes must be returned to the same plaza where they were borrowed, because the city has not yet installed return docks at the future locations."
        ),
        "speaker_genders": {"Newsreader": "female", "Coordinator": "female"},
        "questions": [
            {"stem": "What is the main purpose of the community bike library?", "skill_focus": "gist", "evidence": "Residents can now borrow bicycles the way they borrow library books", "explanation": "The program lets cardholders borrow bikes for short trips.", "choices": [c("Let people borrow bikes for short trips", True, "Borrowing is the point of the program."), c("Sell bikes at a discount", False, "The bikes are borrowed, not sold."), c("Train bike mechanics", False, "Repairs are done by volunteers, not taught."), c("Organize racing events", False, "Racing is never mentioned.")]},
            {"stem": "How were the sixty bikes obtained?", "skill_focus": "detail", "evidence": "collected through a spring donation drive and repaired by volunteers", "explanation": "The fleet came from donations repaired by volunteers.", "choices": [c("Donated and repaired by volunteers", True, "This is how the fleet was built."), c("Purchased by the city", False, "The city did not buy them."), c("Leased from a bike shop", False, "No lease is described."), c("Seized from abandoned lots", False, "No seizure is described.")]},
            {"stem": "Who funded the electric bikes?", "skill_focus": "detail", "evidence": "a small number of electric bikes were added after a local charity donated funds", "explanation": "A local charity donated the money for electric bikes.", "choices": [c("A local charity", True, "Charity funds paid for the electric bikes."), c("The federal government", False, "No government grant is named."), c("The bike workshop", False, "The workshop repaired bikes."), c("Library fines", False, "Fines are not a funding source here.")]},
            {"stem": "Why must bikes be returned to Riverside Plaza?", "skill_focus": "inference", "evidence": "the city has not yet installed return docks at the future locations", "explanation": "Return docks exist only at the plaza so far, so bikes cannot be left elsewhere.", "choices": [c("Return docks only exist there", True, "Other locations have no docks yet."), c("The plaza is the only legal parking", False, "Parking rules are not stated."), c("Bikes cannot cross city lines", False, "No such rule exists."), c("The east location is under repair", False, "The east location is not open.")]},
            {"stem": "What does the coordinator say about the launch?", "skill_focus": "detail", "evidence": "the launch exceeded expectations, with more than two hundred people already on the waitlist", "explanation": "Demand was higher than expected, shown by the long waitlist.", "choices": [c("Demand exceeded expectations", True, "Over two hundred people are waitlisted."), c("Fewer people came than expected", False, "The opposite is reported."), c("The plaza will close early", False, "Hours were just announced."), c("Electric bikes were cancelled", False, "Electric bikes were added.")]},
        ],
    },
    {
        "slug": "night-bus-extension-meeting",
        "task_type": "listening_discussion",
        "title": "Should the Night Bus Run Later?",
        "topic": "Public transit service",
        "difficulty": 2,
        "estimated_level": 8,
        "instructions": "Listen once to the public meeting, then answer the eight questions about the speakers' views and the decision.",
        "intro": "Residents and a transit planner discuss whether to extend the last bus on Route 12 so evening workers can get home.",
        "transcript": (
            "Chair: Thank you all for coming. Tonight we are considering whether the last Route 12 bus should run past its current eleven o'clock finish, so I will open the floor.\n"
            "Ms. Okafor: I work the evening shift at the hospital, and my shift ends at eleven thirty. Right now I wait forty minutes for a connection that may never come, and taxi fare eats half my pay. A bus until twelve thirty would change my life.\n"
            "Mr. Li: I agree the service gap is real. Many of my co-workers at the warehouse finish between eleven and midnight. But I worry the extra hours will mostly serve empty buses on other nights, and that cost will come from somewhere.\n"
            "Ms. Grant: I am the transit planner. Extending service by ninety minutes would cost about four hundred thousand dollars a year, and our own survey shows about two hundred riders would use the late buses on a typical night, not enough to cover the cost by far.\n"
            "Mr. Li: Two hundred riders is not nothing, but I would rather see that money improve the daytime frequency that thousands of people rely on every day.\n"
            "Ms. Okafor: Daytime frequency matters, but people who work nights cannot simply change jobs. If the bus stops at eleven, I am effectively locked out of the housing I can afford near the hospital.\n"
            "Student: For what it is worth, the late library and evening classes in this area end around ten, so students are mostly covered already. The clearest need really is the shift workers.\n"
            "Ms. Grant: Then perhaps a targeted solution: run the extended service only on the nights with the highest demand, which our data shows are Friday and Saturday, and only for a trial period of three months, with a review after.\n"
            "Ms. Okafor: A trial on just two nights still leaves me stranded five nights a week. Could we at least add one later bus on weeknights even if it means a smaller vehicle?\n"
            "Ms. Grant: A smaller vehicle on a trial would reduce the cost while we collect ridership data. If weekday use proves real, we can scale the service up at the next budget review.\n"
            "Chair: Then let me propose this: a three-month trial of a later bus on Friday and Saturday nights, plus one late weekday bus operated with a smaller vehicle, with a full report back to this committee in the fall. All in favour?\n"
            "Several voices: Aye.\n"
            "Chair: The motion carries."
        ),
        "speaker_genders": {"Chair": "female", "Ms. Okafor": "female", "Mr. Li": "male", "Ms. Grant": "female", "Student": "male"},
        "questions": [
            {"stem": "What is the meeting discussing?", "skill_focus": "gist", "evidence": "whether the last Route 12 bus should run past its current eleven o'clock finish", "explanation": "The topic is extending the last Route 12 bus.", "choices": [c("Running the last bus later", True, "The late service is the question."), c("Building a new bus station", False, "No station is discussed."), c("Raising bus fares", False, "Fares are not on the agenda."), c("Adding a daytime express route", False, "Daytime frequency is raised by one speaker, not the topic.")]},
            {"stem": "Why does Ms. Okafor need a later bus?", "skill_focus": "detail", "evidence": "my shift ends at eleven thirty", "explanation": "Her shift ends after the last bus, so she struggles to get home.", "choices": [c("Her shift ends after the last bus", True, "She finishes at eleven thirty."), c("She cannot afford a transit pass", False, "Cost of the pass is not mentioned."), c("She lives outside the city", False, "No such detail is given."), c("The bus stop is unsafe", False, "Safety is not her point.")]},
            {"stem": "What is Mr. Li's main concern about the proposal?", "skill_focus": "purpose", "evidence": "the extra hours will mostly serve empty buses on other nights, and that cost will come from somewhere", "explanation": "Mr. Li worries the money could be better spent elsewhere, such as daytime frequency.", "choices": [c("Late buses may be mostly empty", True, "He fears low use and misused funds."), c("The buses are too old", False, "Vehicle age is not discussed."), c("Drivers refuse night shifts", False, "No staffing concern is raised."), c("Students need the bus more", False, "The student says students are mostly covered.")]},
            {"stem": "What does the transit planner's survey show about late ridership?", "skill_focus": "detail", "evidence": "about two hundred riders would use the late buses on a typical night, not enough to cover the cost", "explanation": "The survey projects around two hundred riders a night.", "choices": [c("About two hundred riders a night", True, "That is the survey estimate."), c("About two thousand riders", False, "The estimate is far lower."), c("No riders at all", False, "Some ridership is projected."), c("Only weekend riders", False, "The figure is for a typical night.")]},
            {"stem": "What reason does the student give for supporting a targeted service?", "skill_focus": "inference", "evidence": "the late library and evening classes in this area end around ten, so students are mostly covered already", "explanation": "Because students are already served, the student thinks the added service should target shift workers.", "choices": [c("Students do not need the late bus", True, "Classes end before the current last bus."), c("Students prefer to walk", False, "No walking preference is given."), c("The library should close later", False, "The student suggests no such change."), c("Students cause the delay", False, "No blame is placed on students.")]},
            {"stem": "How does Ms. Okafor respond to the two-night trial?", "skill_focus": "inference", "evidence": "A trial on just two nights still leaves me stranded five nights a week", "explanation": "She works most nights, so a weekend-only trial does not help her.", "choices": [c("It does not cover her work nights", True, "She is stranded five nights a week."), c("It costs too much", False, "Cost is Mr. Li and Ms. Grant's concern."), c("It is too long a trial", False, "She wants more nights, not a shorter trial."), c("It ignores students", False, "Students are already covered.")]},
            {"stem": "What compromise does Ms. Grant offer to make a weekday late bus affordable?", "skill_focus": "detail", "evidence": "A smaller vehicle on a trial would reduce the cost", "explanation": "A smaller weekday vehicle cuts the cost of the trial.", "choices": [c("Using a smaller vehicle", True, "Smaller vehicles reduce the trial cost."), c("Charging a premium fare", False, "No fare change is proposed."), c("Cancelling daytime service", False, "Daytime service is not cancelled."), c("Asking employers to pay", False, "Employer shuttles are not discussed here.")]},
            {"stem": "What is the final decision of the meeting?", "skill_focus": "detail", "evidence": "a three-month trial of a later bus on Friday and Saturday nights, plus one late weekday bus operated with a smaller vehicle", "explanation": "The committee approved a three-month trial covering weekends and one late weekday bus.", "choices": [c("A three-month trial of extended nights", True, "The motion to trial the service carried."), c("Full permanent late service", False, "Only a trial was approved."), c("No change to the schedule", False, "The motion carried, so service changes."), c("A fare increase to pay for it", False, "No fare increase was approved.")]},
        ],
    },
    {
        "slug": "car-free-shopping-street-debate",
        "task_type": "listening_viewpoints",
        "title": "Turning Main Street Into a Walking Zone",
        "topic": "Downtown planning",
        "difficulty": 2,
        "estimated_level": 8,
        "instructions": "Listen once to the prepared talk, then answer the six questions about the proposal and the perspectives presented.",
        "intro": "A community liaison presents a proposal to close part of Main Street to cars, followed by the perspectives of a shopkeeper, a transit advocate, and an accessibility advocate.",
        "transcript": (
            "Liaison: Our city is asking residents to consider closing the four-block core of Main Street to private cars on summer weekends, turning it into a walking and dining zone. Today I will set out the proposal and the views that have reached us.\n"
            "The proposal would run from the Victoria Day weekend through Labour Day, from Friday evening to Sunday night, and delivery trucks would still be allowed in the early morning.\n"
            "Shopkeepers who support the idea point to the success of a one-month trial two years ago, when foot traffic on the street rose by forty percent and several stores reported record sales on Saturday afternoons.\n"
            "Opposing shopkeepers worry that customers who drive will simply go to the suburban mall, and that the loss of on-street parking will hurt the pharmacy and the grocery store, whose older customers often arrive by car.\n"
            "The transit advocate notes that the trial did bring more riders to the number eight and number twelve buses, but she cautions that weekend bus frequency is still only every twenty minutes, so a car-free street must be paired with better service or people will stay home.\n"
            "The accessibility advocate raises a different concern: closing the street to cars does not remove the need for drop-off. She asks for clearly marked accessible parking bays at both ends and a pickup point at the curb, so people with mobility aids are not left with a long walk.\n"
            "Weighing these views, my office proposes a compromise: close the street on Saturdays and Sundays only, keep two accessible bays at each end, run a shuttle between the main parking garage and the zone, and evaluate ridership and sales before deciding whether to continue next year."
        ),
        "speaker_genders": {"Liaison": "female", "Transit advocate": "female", "Accessibility advocate": "female"},
        "questions": [
            {"stem": "What is the central proposal being discussed?", "skill_focus": "gist", "evidence": "closing the four-block core of Main Street to private cars on summer weekends", "explanation": "The proposal is to make Main Street's core car-free on summer weekends.", "choices": [c("Close Main Street's core to cars on weekends", True, "This is the proposal under discussion."), c("Build a new parking garage", False, "A garage is only mentioned as a shuttle link."), c("Lengthen the summer bus hours", False, "Bus frequency, not hours, is raised."), c("Widen the sidewalks permanently", False, "Widening is not proposed.")]},
            {"stem": "Which group reports higher foot traffic from the earlier trial?", "skill_focus": "detail", "evidence": "foot traffic on the street rose by forty percent", "explanation": "Supporting shopkeepers cite the forty percent rise in foot traffic.", "choices": [c("Supporting shopkeepers", True, "They report the rise in foot traffic."), c("The transit advocate", False, "She reports ridership, not foot traffic."), c("The accessibility advocate", False, "Her point is about drop-offs."), c("The bus drivers", False, "Drivers are not cited.")]},
            {"stem": "Why do some shopkeepers oppose the plan?", "skill_focus": "purpose", "evidence": "customers who drive will simply go to the suburban mall", "explanation": "They fear losing drivers to the mall and parking-dependent customers.", "choices": [c("Drivers may go to the mall instead", True, "They worry car customers will be lost."), c("The street will become too crowded", False, "Crowding is not their worry."), c("Deliveries will stop entirely", False, "Morning deliveries remain allowed."), c("Rent will increase", False, "Rent is not mentioned.")]},
            {"stem": "What condition does the transit advocate attach to supporting a car-free street?", "skill_focus": "inference", "evidence": "a car-free street must be paired with better service or people will stay home", "explanation": "She supports the idea only if bus frequency improves, because current weekend service is sparse.", "choices": [c("Better weekend bus frequency", True, "She links success to better service."), c("Free parking for shoppers", False, "Free parking is not her point."), c("Longer delivery windows", False, "Deliveries are not her concern."), c("A larger trial area", False, "She does not ask to expand the area.")]},
            {"stem": "What does the accessibility advocate say the plan must include?", "skill_focus": "detail", "evidence": "clearly marked accessible parking bays at both ends and a pickup point at the curb", "explanation": "She wants accessible bays and a curb pickup point so people with mobility aids are not stranded.", "choices": [c("Accessible bays and a curb pickup point", True, "Both are her explicit asks."), c("A children's play area", False, "Play areas are not mentioned."), c("More bike racks", False, "Bike racks are not raised."), c("Free entry to museums", False, "Museums are not mentioned.")]},
            {"stem": "What does the liaison's office propose for the compromise?", "skill_focus": "detail", "evidence": "close the street on Saturdays and Sundays only, keep two accessible bays at each end, run a shuttle ... and evaluate ridership and sales", "explanation": "The compromise is a weekend-only closure with accessible bays, a shuttle, and an evaluation.", "choices": [c("A weekend-only zone with a shuttle and a review", True, "This is the proposed compromise."), c("Keeping cars on all weekdays", False, "Weekdays are not part of the proposal at all."), c("A permanent full summer closure", False, "The compromise is weekend-only."), c("Moving the street to the mall", False, "Moving the street is nonsensical and not stated.")]},
        ],
    },
]
