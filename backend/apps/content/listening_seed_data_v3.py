"""Advanced original Listening scripts for CELPIP levels 10-12."""


def c(text, correct, explanation):
    return {"text": text, "is_correct": correct, "explanation": explanation}


def _set(slug, task_type, title, topic, difficulty, level, intro, transcript, questions):
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
        "questions": questions,
    }


LISTENING_SETS = [
    _set(
        "project-budget-overrun",
        "listening_problem_solving",
        "Handling a Project Budget Overrun",
        "Project management",
        3,
        11,
        "Two project leads decide how to respond when a key supplier raises costs.",
        "Nadia: The supplier now says the custom materials will cost eighteen percent more than the estimate.\nKen: That pushes us over the project reserve by almost four thousand dollars. We need to either reduce scope or request more funding.\nNadia: Reducing the final testing phase would save three thousand, but it increases the risk that a defect reaches the client.\nKen: That is not a risk I want to accept. Could we use the standard material instead of the custom version?\nNadia: The standard material is cheaper, but it is less durable and the client specified a five-year warranty. The project architect would need to approve the change.\nKen: Then the safer path is to ask the client for a change order. We can present the supplier's updated quote and explain why the custom material remains necessary.\nNadia: Agreed. I will prepare a comparison showing the cost and warranty difference between the two materials.\nKen: I will call the client and request a meeting tomorrow morning. We should also pause the supplier order until the client responds.\nNadia: I will email the supplier to hold the order and confirm the revised quote is valid for seven days.",
        [
            {"stem": "What problem are Nadia and Ken trying to solve?", "skill_focus": "gist", "evidence": "The supplier now says the custom materials will cost eighteen percent more", "explanation": "They must handle an unplanned cost increase.", "choices": [c("A supplier has raised the cost", True, "This is the central issue."), c("The client rejected the design", False, "The client has not responded yet."), c("The project is finished", False, "The project is still active."), c("A team member resigned", False, "No resignation is mentioned.")]},
            {"stem": "Why does Ken reject reducing the testing phase?", "skill_focus": "detail", "evidence": "it increases the risk that a defect reaches the client", "explanation": "He wants to avoid delivery risk.", "choices": [c("It costs more", False, "It would save money."), c("It could let defects reach the client", True, "This is his concern."), c("It would delay the project", False, "The opposite is possible."), c("The client requested more testing", False, "The client's warranty is related but not a testing request.")]},
            {"stem": "What must happen before the standard material can be used?", "skill_focus": "detail", "evidence": "The project architect would need to approve the change", "explanation": "Approval is required for the substitution.", "choices": [c("The supplier must agree", False, "Supplier agreement is not the stated requirement."), c("The project architect must approve", True, "This is the stated condition."), c("The client must accept a lower warranty", False, "The warranty is a separate issue."), c("Testing must be reduced", False, "Testing reduction is the other option.")]},
            {"stem": "What is the final plan?", "skill_focus": "gist", "evidence": "ask the client for a change order ... pause the supplier order until the client responds", "explanation": "They will seek client approval before proceeding.", "choices": [c("Use the cheaper material now", False, "They did not choose that."), c("Ask the client for a change order and pause the order", True, "Both actions are part of the plan."), c("Cancel the project", False, "They plan to continue."), c("Use the project reserve without informing anyone", False, "They are informing the client.")]},
        ],
    ),
    _set(
        "lease-renewal-negotiation",
        "listening_daily_conversation",
        "Negotiating a Lease Renewal",
        "Housing and tenancy",
        3,
        10,
        "Two friends discuss how to respond to a rent increase.",
        "Elena: The landlord sent a renewal offer with a nine percent rent increase. My lease ends in sixty days.\nMarcus: Have you checked what similar units in the building are renting for now?\nElena: Yes, two comparable units were listed for about six percent more than my current rent. So the increase is above the market.\nMarcus: You could send a written response with those listings and ask for a smaller increase or a longer fixed term.\nElena: I am worried that negotiating could annoy the landlord. I have lived here for four years and would rather avoid conflict.\nMarcus: You can keep it respectful and factual. You are not refusing to renew; you are asking for terms that match the evidence.\nElena: That is true. I will also mention that I have never paid late and have taken care of the unit.\nMarcus: Ask for the reply by a specific date so you still have time to find another place if needed.\nElena: Good. I will request a seven-day response and keep a copy of the email.",
        [
            {"stem": "What is Elena's concern about the renewal?", "skill_focus": "gist", "evidence": "a nine percent rent increase", "explanation": "The landlord has proposed a higher rent.", "choices": [c("The lease is ending too soon", False, "She has sixty days."), c("The rent increase seems too high", True, "She compares it to similar units."), c("The landlord wants to sell", False, "No sale is mentioned."), c("The unit needs repairs", False, "No repairs are discussed.")]},
            {"stem": "Why does Elena believe the increase is above market?", "skill_focus": "detail", "evidence": "two comparable units were listed for about six percent more than my current rent", "explanation": "Comparable units suggest a lower market increase.", "choices": [c("Her landlord told her", False, "The landlord did not say this."), c("Comparable units show a lower increase", True, "This is her evidence."), c("The building is empty", False, "The building has comparable units."), c("Her rent has never increased", False, "No history is stated.")]},
            {"stem": "Why does Marcus suggest asking for a response date?", "skill_focus": "inference", "evidence": "so you still have time to find another place if needed", "explanation": "A deadline protects her time to consider alternatives.", "choices": [c("To pressure the landlord into accepting", False, "The purpose is not pressure."), c("To leave time to find another place", True, "This is Marcus's reason."), c("To delay the lease expiry", False, "The expiry is fixed."), c("To avoid paying rent", False, "No rent avoidance is intended.")]},
            {"stem": "What does Elena plan to do?", "skill_focus": "detail", "evidence": "I will request a seven-day response and keep a copy of the email", "explanation": "She will ask for a response deadline and keep evidence.", "choices": [c("Accept the increase", False, "She plans to negotiate."), c("Request a seven-day response", True, "This is her plan."), c("Move out immediately", False, "She still has time."), c("Refuse to pay rent", False, "She is not refusing payment.")]},
        ],
    ),
    _set(
        "cybersecurity-training",
        "listening_information",
        "Cybersecurity Policy Training",
        "Workplace security",
        3,
        11,
        "A security officer explains new rules for handling sensitive information.",
        "Speaker: Good afternoon. This training reviews three changes to our information-security policy. First, all sensitive files must now be stored in the approved cloud workspace, not on personal devices. If you need temporary local access, request an encrypted laptop through the service desk.\nSecond, multi-factor authentication is required for every account that can access client data. You will receive a prompt to enrol your phone or a hardware key. If you lose your device, report it within four hours so access can be suspended.\nThird, email attachments containing personal information must be sent through the secure file portal rather than as regular attachments. The portal records who opened each file and allows the sender to revoke access later.\nFinally, if you suspect a message is a phishing attempt, do not click any link. Forward the message to security and then delete it. Our team reviews every report, but we do not send individual replies unless more information is needed.",
        [
            {"stem": "What is the training mainly about?", "skill_focus": "gist", "evidence": "three changes to our information-security policy", "explanation": "The speaker is explaining new security requirements.", "choices": [c("New information-security rules", True, "All sections describe policy changes."), c("How to buy a laptop", False, "Laptop requests are only temporary access."), c("How to send personal emails", False, "Personal email is not the focus."), c("A phishing investigation", False, "Phishing is one part of the training.")]},
            {"stem": "Where must sensitive files be stored?", "skill_focus": "detail", "evidence": "approved cloud workspace, not on personal devices", "explanation": "Sensitive files belong in the approved cloud workspace.", "choices": [c("On personal phones", False, "Personal devices are prohibited."), c("In the approved cloud workspace", True, "This is the requirement."), c("On encrypted laptops only", False, "Encrypted laptops are only for temporary local access."), c("In email attachments", False, "Email is not the storage location.")]},
            {"stem": "Why should personal information be sent through the secure portal?", "skill_focus": "inference", "evidence": "records who opened each file and allows the sender to revoke access", "explanation": "The portal provides tracking and control.", "choices": [c("To track and revoke access", True, "These are the portal's stated benefits."), c("To make files load faster", False, "Speed is not mentioned."), c("To reduce email storage", False, "Storage is not the reason."), c("To automatically encrypt the laptop", False, "Laptop encryption is separate.")]},
            {"stem": "What should an employee do after reporting a suspected phishing email?", "skill_focus": "detail", "evidence": "Forward the message to security and then delete it", "explanation": "The email should be forwarded and deleted.", "choices": [c("Click the link to inspect it", False, "Clicking is explicitly discouraged."), c("Forward it and delete it", True, "Both actions are instructed."), c("Reply to the sender", False, "No reply is advised."), c("Wait for a personal reply", False, "Security may not reply individually.")]},
        ],
    ),
    _set(
        "regional-housing-reform",
        "listening_news",
        "A Regional Housing Reform Plan",
        "Housing policy",
        3,
        12,
        "A news report explains a regional plan to speed up housing construction.",
        "Newsreader: A regional council has approved a three-year plan intended to accelerate housing construction in areas near rapid transit. The plan allows six-storey residential buildings without a separate rezoning application in designated station areas. It also shortens the development-permit review period from twelve months to four months for projects that include below-market rental units.\nSupporters say the changes will increase the supply of homes near public transit and reduce the time developers spend waiting for approval. The plan includes a target of eight thousand new homes by the end of the period.\nSome neighbourhood groups have raised concerns that taller buildings may change the character of low-rise streets. In response, the plan requires a five-metre transition zone where new buildings meet existing single-family homes, along with wider sidewalks and a public consultation before construction begins.\nThe regional housing authority will publish quarterly progress reports and review the plan after eighteen months. If fewer than half of the target homes have been approved by then, the council will consider further changes.",
        [
            {"stem": "What is the main purpose of the plan?", "skill_focus": "purpose", "evidence": "accelerate housing construction in areas near rapid transit", "explanation": "The plan aims to speed up housing near transit.", "choices": [c("To accelerate transit-area housing", True, "This is the stated goal."), c("To reduce public transit service", False, "Transit is the location focus."), c("To stop new construction", False, "The opposite is intended."), c("To increase development fees", False, "No fee change is mentioned.")]},
            {"stem": "What must projects include to receive the faster review?", "skill_focus": "detail", "evidence": "projects that include below-market rental units", "explanation": "Faster review is tied to below-market rentals.", "choices": [c("A parking garage", False, "Parking is not mentioned."), c("Below-market rental units", True, "This is the condition."), c("A public plaza", False, "No plaza requirement is stated."), c("A six-storey height", False, "Height is a separate allowance.")]},
            {"stem": "Why is a transition zone required?", "skill_focus": "inference", "evidence": "taller buildings may change the character of low-rise streets", "explanation": "The zone addresses the visual and scale impact on existing homes.", "choices": [c("To reduce the impact on low-rise streets", True, "This responds to neighbourhood concerns."), c("To increase building height", False, "The zone is a design limit."), c("To remove sidewalks", False, "Sidewalks are widened."), c("To speed up approval", False, "The zone is an additional requirement.")]},
            {"stem": "What may trigger further council changes?", "skill_focus": "detail", "evidence": "If fewer than half of the target homes have been approved", "explanation": "The plan may change if approval progress is insufficient.", "choices": [c("Quarterly reports", False, "Reports are routine."), c("Fewer than half approved by eighteen months", True, "This is the review threshold."), c("Eight thousand homes", False, "That is the overall target."), c("Public consultation", False, "Consultation is required before construction.")]},
        ],
    ),
    _set(
        "hybrid-work-schedule",
        "listening_discussion",
        "Choosing a Hybrid Work Schedule",
        "Workplace policy",
        3,
        11,
        "Three employees discuss how to design a hybrid schedule for their department.",
        "Priya: We need to choose a hybrid model for the department. I suggest fixed Tuesday and Thursday office days so everyone knows when to expect in-person collaboration.\nOmar: Fixed days are simple, but they do not suit employees with caregiving responsibilities on those days. A flexible model lets people choose any two office days.\nLena: Flexibility helps individuals, but if everyone chooses different days, we may lose the teamwork benefit. We could require one common day and let people choose the second.\nOmar: That is a reasonable balance. I would add that teams with client-facing work can agree on a second common day if needed.\nPriya: I can support one fixed common day and one flexible day, provided managers track attendance fairly and do not judge flexibility differently.\nLena: We should also review the model after three months using meeting participation and project outcomes, not just office attendance.\nOmar: Agreed. I will draft the policy and include a clear process for requesting an exception.",
        [
            {"stem": "What are the employees deciding?", "skill_focus": "gist", "evidence": "We need to choose a hybrid model", "explanation": "They are designing a hybrid work schedule.", "choices": [c("How to structure hybrid office days", True, "This is the central topic."), c("Whether to close the office", False, "They are planning office use."), c("How to hire new staff", False, "No hiring is discussed."), c("How to reduce meeting time", False, "Meetings are a review measure.")]},
            {"stem": "What is Omar's objection to fixed days?", "skill_focus": "detail", "evidence": "they do not suit employees with caregiving responsibilities", "explanation": "Fixed days may not work for everyone.", "choices": [c("They cost more", False, "Cost is not mentioned."), c("They may not suit employees with caregiving duties", True, "This is Omar's concern."), c("They reduce teamwork", False, "Fixed days may help teamwork."), c("They are hard to schedule", False, "Fixed days are simple.")]},
            {"stem": "What compromise do they reach?", "skill_focus": "inference", "evidence": "one fixed common day and one flexible day", "explanation": "They combine a shared day with individual choice.", "choices": [c("All flexible days", False, "They keep one common day."), c("One common day plus one flexible day", True, "This is the compromise."), c("All fixed days", False, "They rejected that."), c("No office days", False, "They still require office days.")]},
            {"stem": "How does Lena suggest the model should be reviewed?", "skill_focus": "detail", "evidence": "using meeting participation and project outcomes, not just office attendance", "explanation": "The review should use participation and outcomes.", "choices": [c("By office attendance only", False, "She says not just attendance."), c("By meeting participation and project outcomes", True, "Both measures are named."), c("By manager preference", False, "Manager preference is not the measure."), c("By employee surveys only", False, "No survey is mentioned.")]},
        ],
    ),
    _set(
        "carbon-tax-debate",
        "listening_viewpoints",
        "Should the Carbon Tax Be Adjusted?",
        "Climate policy",
        3,
        12,
        "A researcher presents competing views on a carbon tax.",
        "Speaker: A proposed adjustment to the carbon tax has divided policy experts. The central question is not whether carbon pricing should exist, but how the cost and benefit should be distributed.\nEconomists who support the adjustment argue that a rising carbon price is the most efficient way to reduce emissions. They say it encourages businesses and households to choose lower-carbon options without the government prescribing exactly how. They also emphasize that most households receive a rebate.\nSmall-business groups are more cautious. They argue that the tax increases energy and transport costs before the rebate arrives, which can strain cash flow. They want a delay for businesses that are already investing in efficiency.\nLow-income advocacy groups raise a third concern. They say that rural households often depend on private vehicles and have fewer alternatives, so a uniform carbon price can feel unfair even with a rebate. They propose targeted support for rural and low-income residents.\nThe final recommendation is therefore to keep the tax but adjust the timing of rebates, protect cash-strapped businesses, and provide additional support to households with limited alternatives.",
        [
            {"stem": "What is the central issue in the talk?", "skill_focus": "gist", "evidence": "how the cost and benefit should be distributed", "explanation": "The debate is about fairness and distribution, not the tax itself.", "choices": [c("How carbon-tax costs and benefits are distributed", True, "This is the stated question."), c("Whether climate change is real", False, "The talk assumes carbon pricing."), c("How to remove the tax", False, "The recommendation keeps the tax."), c("How to increase fuel use", False, "The goal is lower-carbon choices.")]},
            {"stem": "Why do small businesses want a delay?", "skill_focus": "detail", "evidence": "the tax increases energy and transport costs before the rebate arrives", "explanation": "They need cash-flow relief.", "choices": [c("To avoid paying tax permanently", False, "They want a delay, not removal."), c("To reduce short-term cash-flow pressure", True, "This is the stated concern."), c("To receive a larger rebate", False, "No larger rebate is mentioned."), c("To switch to electric vehicles", False, "They are investing in efficiency, but that is not the requested delay.")]},
            {"stem": "Why do low-income groups say the tax can feel unfair?", "skill_focus": "inference", "evidence": "rural households often depend on private vehicles and have fewer alternatives", "explanation": "Limited alternatives make the cost harder to avoid.", "choices": [c("Rural households have fewer alternatives", True, "This is the stated equity concern."), c("Rebates are too large", False, "The rebate is not too large."), c("Businesses receive no support", False, "Business support is a separate concern."), c("The tax does not affect emissions", False, "The economists argue it does.")]},
            {"stem": "What does the speaker finally recommend?", "skill_focus": "purpose", "evidence": "keep the tax but adjust the timing of rebates, protect cash-strapped businesses, and provide additional support", "explanation": "The recommendation keeps pricing while addressing fairness.", "choices": [c("Keep the tax with fairness adjustments", True, "All three adjustments are named."), c("Remove the tax completely", False, "The speaker recommends keeping it."), c("Make the tax uniform with no support", False, "The opposite is recommended."), c("Apply it only to businesses", False, "Households remain affected.")]},
        ],
    ),
]
